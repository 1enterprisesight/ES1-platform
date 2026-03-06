from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path

from app.config import AGENT_CYCLE_SECONDS
from app.db import run_query, get_table_info, get_data_profile
from app.llm import generate, generate_json
from app.profiler import get_silos
from app.tiles import Tile, tile_store, interaction_store
from app.row_config import get_row_config, get_row_prompt_context

logger = logging.getLogger(__name__)

_task: asyncio.Task | None = None
_running = False

# Load prompt templates
_prompts_dir = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    return (_prompts_dir / name).read_text()


def _normalize_column(col: str) -> str:
    """Map any column value to a valid row ID. Handles legacy names and LLM drift."""
    rows = get_row_config()
    valid = {r["id"] for r in rows} | {"resolved"}
    if col in valid:
        return col
    # Map legacy hardcoded names
    if col in ("action", "watching"):
        return rows[0]["id"]
    if col in ("informational",):
        return rows[1]["id"]
    # Default to row2
    return rows[1]["id"]


def start_agent():
    global _task, _running
    _running = True
    _task = asyncio.get_event_loop().create_task(_agent_loop())


def stop_agent():
    global _running, _task
    _running = False
    if _task:
        _task.cancel()
        _task = None


def is_agent_active() -> bool:
    """True when the agent loop is running AND not paused (has connected clients)."""
    return _running and tile_store.has_subscribers()


async def _agent_loop():
    cycle = 0
    past_titles: list[str] = []

    # Wait a moment for startup to complete
    await asyncio.sleep(3)

    while _running:
        try:
            # Pause when no browsers are connected — avoids burning Vertex AI calls
            if not tile_store.has_subscribers():
                if cycle > 0:
                    logger.info("No clients connected, pausing agent")
                await asyncio.sleep(5)
                continue

            silos = get_silos()
            if len(silos) < 2:
                await asyncio.sleep(5)
                continue

            # Pick silo: ~33% alpha / ~33% interest-driven / ~33% exploration rotation
            non_alpha = [s for s in silos if s["id"] != "alpha"]
            silo_scores = interaction_store.get_silo_scores()

            if cycle % 3 == 0 and cycle > 0:
                # Alpha cross-silo cycle
                current_silo = silos[0]
            elif cycle % 3 == 1 and silo_scores:
                # Interest-driven: pick silo with highest cumulative interest score
                best_silo_id = max(silo_scores, key=silo_scores.get)
                match = [s for s in non_alpha if s["id"] == best_silo_id]
                current_silo = match[0] if match else (non_alpha[0] if non_alpha else silos[0])
                logger.info(f"Interest-driven silo selection: {current_silo['label']} (score={silo_scores.get(best_silo_id, 0):.1f})")
            else:
                # Exploration rotation
                idx = (cycle // 1) % len(non_alpha) if non_alpha else 0
                current_silo = non_alpha[idx] if non_alpha else silos[0]

            logger.info(f"Agent cycle {cycle}: silo={current_silo['label']}")
            tile_store.broadcast_status("agent_thinking", silo=current_silo["id"])

            # Step 1: Generate an analytical question (with interest signals)
            table_info = get_table_info()
            interest_context = _build_interest_context()
            question = await _generate_question(current_silo, table_info, past_titles, interest_context)
            logger.info(f"Question: {question}")

            # Step 2: Generate SQL
            sql = await _generate_sql(question, table_info)
            logger.info(f"SQL: {sql[:200]}")

            # Step 3: Execute query (with one retry)
            try:
                results = run_query(sql)
            except Exception as e:
                logger.warning(f"Query failed, retrying: {e}")
                sql = await _fix_sql(sql, str(e), table_info)
                results = run_query(sql)

            if not results:
                logger.info("Empty results, skipping")
                tile_store.broadcast_status("agent_idle")
                cycle += 1
                await asyncio.sleep(AGENT_CYCLE_SECONDS)
                continue

            # Step 4: Evaluate — always create a tile, let the LLM pick the lane
            evaluation = await _evaluate_finding(question, results, current_silo)

            # Step 5: Create tile
            tile_data = await _create_tile(question, results, current_silo, evaluation)

            # Extract numeric chart data from query results
            chart_data = _extract_chart_data(results, tile_data)

            tile = Tile(
                silo=current_silo["id"],
                title=tile_data.get("title", question[:80]),
                summary=tile_data.get("summary", ""),
                detail=tile_data.get("detail", ""),
                column=_normalize_column(tile_data.get("column", "row2")),
                chart=tile_data.get("chart"),
                chartData=chart_data,
                chartLabel=tile_data.get("chartLabel"),
                metric=tile_data.get("metric"),
                metricSub=tile_data.get("metricSub"),
                sources=tile_data.get("sources", [current_silo["label"]]),
                suggestedQuestions=tile_data.get("suggestedQuestions"),
            )

            await tile_store.add_tile(tile)
            past_titles.append(tile.title)
            if len(past_titles) > 30:
                past_titles = past_titles[-20:]

            logger.info(f"Tile created: {tile.title}")

            # Drill-down: if this silo has a high-interest tile, generate a follow-up
            drilldown = [
                d for d in interaction_store.get_drilldown_candidates()
                if d.tile_silo == current_silo["id"]
            ]
            if drilldown:
                top = max(drilldown, key=lambda d: d.interest_score)
                logger.info(f"Drill-down triggered for '{top.tile_title}' (score={top.interest_score})")
                await _generate_drilldown(top, current_silo, table_info, past_titles)

            tile_store.broadcast_status("agent_idle")

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Agent cycle error: {e}", exc_info=True)
            tile_store.broadcast_status("agent_idle")
            # Back off on repeated failures (auth issues, network, etc.)
            await asyncio.sleep(min(AGENT_CYCLE_SECONDS * 2, 60))

        cycle += 1
        await asyncio.sleep(AGENT_CYCLE_SECONDS)


def _build_interest_context() -> str:
    """Build prompt context from user interaction signals."""
    liked = interaction_store.get_top_liked(5)
    disliked = interaction_store.get_disliked()

    lines = []
    if liked:
        lines.append("USER INTEREST — dig deeper into these topics:")
        for i in liked:
            qs = ""
            if i.followup_questions:
                qs = f" (user asked: {'; '.join(i.followup_questions[:3])})"
            lines.append(f"  - {i.tile_title} [silo={i.tile_silo}, score={i.interest_score}]{qs}")
    if disliked:
        lines.append("USER DISINTEREST — avoid these topics:")
        for i in disliked:
            lines.append(f"  - {i.tile_title} [silo={i.tile_silo}, score={i.interest_score}]")

    return "\n".join(lines) if lines else ""


async def _generate_drilldown(interaction, silo: dict, table_info: dict, past_titles: list[str]):
    """Generate a deeper follow-up tile for a high-interest interaction."""
    try:
        data_profile = get_data_profile()

        followup_hint = ""
        if interaction.followup_questions:
            followup_hint = "The user has asked these follow-up questions — use them as inspiration:\n" + "\n".join(
                f"  - {q}" for q in interaction.followup_questions[:5]
            )

        prompt = f"""You are a data analyst. A previous finding was very interesting to the user:

Title: {interaction.tile_title}
Summary: {interaction.tile_summary}
Silo: {silo['label']}

{followup_hint}

Data profile:
{data_profile}

Generate ONE deeper follow-up analytical question that builds on this finding. Drill into the specifics, look for root causes, or explore related dimensions.

Return ONLY the question text, nothing else."""

        question = await generate(prompt, temperature=0.7)
        logger.info(f"Drill-down question: {question}")

        sql = await _generate_sql(question, table_info)
        try:
            results = run_query(sql)
        except Exception as e:
            logger.warning(f"Drill-down query failed: {e}")
            sql = await _fix_sql(sql, str(e), table_info)
            results = run_query(sql)

        if not results:
            return

        evaluation = await _evaluate_finding(question, results, silo)
        tile_data = await _create_tile(question, results, silo, evaluation)
        chart_data = _extract_chart_data(results, tile_data)

        tile = Tile(
            silo=silo["id"],
            title=tile_data.get("title", question[:80]),
            summary=tile_data.get("summary", ""),
            detail=tile_data.get("detail", ""),
            column=_normalize_column(tile_data.get("column", "row2")),
            chart=tile_data.get("chart"),
            chartData=chart_data,
            chartLabel=tile_data.get("chartLabel"),
            metric=tile_data.get("metric"),
            metricSub=tile_data.get("metricSub"),
            sources=tile_data.get("sources", [silo["label"]]),
            suggestedQuestions=tile_data.get("suggestedQuestions"),
        )

        await tile_store.add_tile(tile)
        past_titles.append(tile.title)
        logger.info(f"Drill-down tile created: {tile.title}")

    except Exception as e:
        logger.error(f"Drill-down failed: {e}", exc_info=True)


async def _generate_question(silo: dict, table_info: dict, past_titles: list[str], interest_context: str = "") -> str:
    system = _load_prompt("agent_system.txt")
    data_profile = get_data_profile()

    past = "\n".join(f"- {t}" for t in past_titles[-10:]) if past_titles else "None yet"

    silo_context = ""
    if silo["id"] == "alpha":
        silo_context = "Generate a CROSS-SILO question that correlates data from BOTH tables (feature_usage and performance). Use the join key: feature_usage.\"Doctor ID\" = performance.\"Doctor ID\"."
    else:
        col = silo.get("source_column", "")
        tbl = silo.get("source_table", "")
        silo_context = f'Focus on the "{col}" dimension from the {tbl} table. Look for patterns, anomalies, or trends within this dimension.'

    interest_block = ""
    if interest_context:
        interest_block = f"""
User engagement signals (prioritize these):
{interest_context}
"""

    prompt = f"""{system}

Here is a detailed profile of the data (column types, distinct values, distributions, and sample rows):

{data_profile}

{silo_context}
{interest_block}
Previously generated findings (avoid repeating):
{past}

Generate ONE specific analytical question about the Invisalign data that could reveal an interesting insight. The question should be answerable with a single SQL query. Use actual column names and values from the profile above.

Return ONLY the question text, nothing else."""

    return await generate(prompt, temperature=0.8)


async def _generate_sql(question: str, table_info: dict) -> str:
    data_profile = get_data_profile()

    prompt = f"""Write a DuckDB SQL query to answer this question:

{question}

Here is a detailed profile of the data (column types, distinct values, distributions, and sample rows):

{data_profile}

Rules:
- Use double quotes for column names with spaces or special characters
- Use DuckDB syntax (e.g., strftime, date functions)
- Limit results to 20 rows max
- Return meaningful aggregations, not raw rows
- Handle NULLs gracefully
- Use ONLY actual column names shown in the profile above
- Keep queries CONCISE — avoid unnecessary CTEs and subqueries
- Do NOT add comments in the SQL

Return ONLY the SQL query, no explanation, no markdown fences, no comments."""

    sql = await generate(prompt, temperature=0.2)
    # Strip markdown code fences if present
    sql = sql.strip()
    if sql.startswith("```"):
        lines = sql.split("\n")
        sql = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return sql.strip()


async def _fix_sql(sql: str, error: str, table_info: dict) -> str:
    tables_desc = ""
    for table, cols in table_info.items():
        col_names = ", ".join(f'"{c["name"]}" ({c["type"]})' for c in cols)
        tables_desc += f"\n{table}: {col_names}\n"

    prompt = f"""This DuckDB SQL query failed:

```sql
{sql}
```

Error: {error}

Available tables:
{tables_desc}

Fix the query. Return ONLY the corrected SQL, no explanation."""

    fixed = await generate(prompt, temperature=0.1)
    fixed = fixed.strip()
    if fixed.startswith("```"):
        lines = fixed.split("\n")
        fixed = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return fixed.strip()


async def _evaluate_finding(question: str, results: list[dict], silo: dict) -> dict:
    results_preview = json.dumps(results[:10], default=str, indent=2)
    row_context = get_row_prompt_context()
    rows = get_row_config()
    row_ids = "|".join(r["id"] for r in rows)

    prompt = f"""Evaluate this data finding for a dashboard:

Question: {question}
Silo: {silo['label']}

Query results (first 10 rows):
{results_preview}

Dashboard rows (pick the best fit):
{row_context}

Is this finding interesting enough to show on a dashboard? Consider:
- Does it reveal a non-obvious pattern?
- Are the numbers significant?
- Would a business user care?

Return JSON: {{"interesting": true/false, "reason": "brief explanation", "priority": "{row_ids}"}}"""

    try:
        result = await generate_json(prompt, temperature=0.3)
        # Normalize old column names to new row IDs
        priority = result.get("priority", rows[1]["id"])
        valid_ids = {r["id"] for r in rows}
        if priority not in valid_ids:
            # Map legacy names
            if priority in ("action", "watching"):
                priority = rows[0]["id"]
            else:
                priority = rows[1]["id"]
            result["priority"] = priority
        return result
    except Exception:
        return {"interesting": True, "priority": rows[1]["id"]}


async def _create_tile(question: str, results: list[dict], silo: dict, evaluation: dict) -> dict:
    rows = get_row_config()
    row_context = get_row_prompt_context()
    row_ids = "|".join(f'"{r["id"]}"' for r in rows)
    results_preview = json.dumps(results[:15], default=str, indent=2)

    prompt = f"""Create a dashboard tile from this finding. Return JSON with these fields:
- title: Short, specific headline (max 80 chars). Reference actual data values.
- summary: 1-2 sentence explanation with key numbers.
- detail: 2-3 paragraph deep analysis with context and recommended actions.
- column: Which row this belongs in — one of {row_ids}. Choose based on:
{row_context}
- chart: Sparkline pattern — one of "rising", "declining", "volatile", "stable", "spike", "plateau", or null.
- chartLabel: Short label for the sparkline (e.g. "Order volume").
- metric: Key number as string (e.g. "+22%", "1,335", "$240K").
- metricSub: Metric context (e.g. "above model", "customers", "projected loss").
- sources: Array of source labels (the silo names involved).
- suggestedQuestions: Array of 3-4 follow-up questions a user might ask.

Question analyzed: {question}
Silo: {silo['label']}
Priority suggestion: {evaluation.get('priority', rows[1]['id'])}

Query results:
{results_preview}

Return the tile as a JSON object."""

    try:
        return await generate_json(prompt, temperature=0.5)
    except Exception as e:
        logger.error(f"Tile creation failed: {e}")
        return {
            "title": question[:80],
            "summary": f"Found {len(results)} results.",
            "detail": f"Query returned {len(results)} rows of data.",
            "column": evaluation.get("priority", "informational"),
            "sources": [silo["label"]],
        }


def _extract_chart_data(results: list[dict], tile_data: dict) -> list[float] | None:
    """Try to extract a numeric series from query results for the sparkline chart."""
    if not results or len(results) < 2:
        return None

    # Look for numeric columns in the results
    numeric_cols = []
    for key, val in results[0].items():
        if isinstance(val, (int, float)):
            numeric_cols.append(key)

    if not numeric_cols:
        return None

    # Prefer columns that look like the main metric (rate, count, percentage, etc.)
    metric_keywords = ["rate", "count", "avg", "sum", "total", "percent", "ratio", "pct"]
    best_col = numeric_cols[0]
    for col in numeric_cols:
        if any(kw in col.lower() for kw in metric_keywords):
            best_col = col
            break

    # Extract the values
    values = []
    for row in results[:20]:
        v = row.get(best_col)
        if v is not None and isinstance(v, (int, float)):
            values.append(float(v))

    if len(values) < 2:
        return None

    return values
