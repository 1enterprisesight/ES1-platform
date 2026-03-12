"""Workspace-scoped agent loop.

Each active workspace gets its own agent loop that generates insight tiles.
Loops start when a workspace has SSE subscribers and stop when all leave.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time

from app.config import AGENT_CYCLE_SECONDS
from app.db import run_query, get_workspace_table_info, get_data_profile, is_workspace_loaded, load_workspace_datasets
from app.llm import generate, generate_json
from app.profiler import get_silos
from app.tiles import Tile, get_tile_store, get_all_workspace_interactions
from app.row_config import get_row_config, get_row_prompt_context

logger = logging.getLogger(__name__)

# Per-workspace agent tasks
_tasks: dict[str, asyncio.Task] = {}
_running: dict[str, bool] = {}


def _normalize_column(col: str) -> str:
    """Map any column value to a valid row ID."""
    rows = get_row_config()
    valid = {r["id"] for r in rows} | {"resolved"}
    if col in valid:
        return col
    if col in ("action", "watching"):
        return rows[0]["id"]
    if col in ("informational",):
        return rows[1]["id"]
    return rows[1]["id"]


def start_agent(workspace_id: str):
    """Start the agent loop for a workspace."""
    if workspace_id in _running and _running[workspace_id]:
        return
    _running[workspace_id] = True
    _tasks[workspace_id] = asyncio.get_event_loop().create_task(
        _agent_loop(workspace_id)
    )
    logger.info(f"Agent started for workspace {workspace_id}")


def stop_agent(workspace_id: str = ""):
    """Stop agent for a workspace, or all agents if no workspace given."""
    if workspace_id:
        _running[workspace_id] = False
        task = _tasks.pop(workspace_id, None)
        if task:
            task.cancel()
    else:
        for ws_id in list(_running.keys()):
            _running[ws_id] = False
        for ws_id, task in list(_tasks.items()):
            task.cancel()
        _tasks.clear()


def is_agent_active(workspace_id: str = "") -> bool:
    """True when agent is running for a workspace."""
    if workspace_id:
        return _running.get(workspace_id, False)
    return any(_running.values())


async def _check_data_activated(workspace_id: str) -> tuple[bool, list]:
    """Check if workspace data is activated and return join config.

    Returns (is_activated, join_links).
    """
    from app.database import get_pool
    import uuid as _uuid
    pool = get_pool()
    settings_raw = await pool.fetchval(
        "SELECT settings FROM sentinel.workspaces WHERE id = $1",
        _uuid.UUID(workspace_id),
    )
    if not settings_raw:
        return False, []
    settings = json.loads(settings_raw) if isinstance(settings_raw, str) else settings_raw
    activated = settings.get("data_activated", False)
    join_config = settings.get("join_config", [])
    if isinstance(join_config, dict):
        join_config = [join_config] if join_config else []
    return activated, join_config


def _build_join_context(join_links: list) -> str:
    """Build a prompt section describing the table join relationships."""
    if not join_links:
        return ""
    lines = ["Table relationships (use these for JOINs):"]
    for link in join_links:
        lines.append(
            f'  {link["left_table"]}."{link["left_column"]}" = '
            f'{link["right_table"]}."{link["right_column"]}"'
        )
    return "\n".join(lines)


async def _agent_loop(workspace_id: str):
    tile_store = get_tile_store(workspace_id)
    cycle = 0
    past_titles: list[str] = [t.title for t in tile_store.tiles]
    dataset_context = ""
    join_context = ""

    await asyncio.sleep(3)

    # Load stored dataset profiles (workspace-scoped)
    from app.dataset_profiler import get_stored_profiles, format_profiles_for_prompt
    try:
        profiles = await get_stored_profiles(workspace_id=workspace_id)
        dataset_context = format_profiles_for_prompt(profiles)
        if profiles:
            logger.info(f"Loaded {len(profiles)} dataset profile(s) for workspace {workspace_id}")
    except Exception as e:
        logger.warning(f"Could not load dataset profiles: {e}")

    while _running.get(workspace_id, False):
        try:
            if not dataset_context and cycle in (2, 5):
                try:
                    profiles = await get_stored_profiles(workspace_id=workspace_id)
                    dataset_context = format_profiles_for_prompt(profiles)
                except Exception:
                    pass

            # Pause when no browsers are connected
            if not tile_store.has_subscribers():
                if cycle > 0:
                    logger.info(f"No clients for workspace {workspace_id}, pausing agent")
                await asyncio.sleep(5)
                continue

            # Pause until workspace data is activated
            activated, join_links = await _check_data_activated(workspace_id)
            if not activated:
                tile_store.broadcast_status("data_not_ready")
                await asyncio.sleep(5)
                continue
            join_context = _build_join_context(join_links)

            # Ensure workspace data is loaded into DuckDB
            if not is_workspace_loaded(workspace_id):
                from app.database import get_pool
                import uuid as _uuid
                pool = get_pool()
                ds_rows = await pool.fetch(
                    "SELECT name, csv_data FROM sentinel.datasets WHERE workspace_id = $1 ORDER BY uploaded_at",
                    _uuid.UUID(workspace_id),
                )
                if ds_rows:
                    load_workspace_datasets(workspace_id, [(r["name"], bytes(r["csv_data"])) for r in ds_rows])
                    logger.info(f"Agent loaded {len(ds_rows)} dataset(s) into DuckDB for workspace {workspace_id}")

            silos = get_silos(workspace_id)
            if len(silos) < 2:
                # Silos missing — trigger discovery if we have data
                from app.profiler import discover_silos, is_discovery_done
                if not is_discovery_done(workspace_id):
                    logger.info(f"No silos for workspace {workspace_id}, triggering discovery")
                    try:
                        await discover_silos(workspace_id)
                        silos = get_silos(workspace_id)
                    except Exception as e:
                        logger.warning(f"Agent silo discovery failed: {e}")
                if len(silos) < 2:
                    await asyncio.sleep(5)
                    continue

            non_alpha = [s for s in silos if s["id"] != "alpha"]
            all_interactions = get_all_workspace_interactions(workspace_id)
            silo_scores: dict[str, float] = {}
            for inter in all_interactions:
                if inter.tile_silo:
                    silo_scores[inter.tile_silo] = silo_scores.get(inter.tile_silo, 0.0) + inter.interest_score

            if cycle % 3 == 0 and cycle > 0:
                current_silo = silos[0]
            elif cycle % 3 == 1 and silo_scores:
                best_silo_id = max(silo_scores, key=silo_scores.get)
                match = [s for s in non_alpha if s["id"] == best_silo_id]
                current_silo = match[0] if match else (non_alpha[0] if non_alpha else silos[0])
            else:
                idx = (cycle // 1) % len(non_alpha) if non_alpha else 0
                current_silo = non_alpha[idx] if non_alpha else silos[0]

            logger.info(f"Agent cycle {cycle} for workspace {workspace_id}: silo={current_silo['label']}")
            tile_store.broadcast_status("agent_thinking", silo=current_silo["id"])

            table_info = get_workspace_table_info(workspace_id)
            interest_context = _build_interest_context(all_interactions)
            question = await _generate_question(current_silo, table_info, past_titles, interest_context, dataset_context, join_context)
            logger.info(f"Question: {question}")

            sql = await _generate_sql(question, table_info, workspace_id, join_context)
            logger.info(f"SQL: {sql[:200]}")

            try:
                results = run_query(sql, workspace_id=workspace_id)
            except Exception as e:
                logger.warning(f"Query failed, retrying: {e}")
                sql = await _fix_sql(sql, str(e), table_info)
                results = run_query(sql, workspace_id=workspace_id)

            if not results:
                logger.info("Empty results, skipping")
                tile_store.broadcast_status("agent_idle")
                cycle += 1
                await asyncio.sleep(AGENT_CYCLE_SECONDS)
                continue

            evaluation = await _evaluate_finding(question, results, current_silo)
            tile_data = await _create_tile(question, results, current_silo, evaluation)
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

            # Drill-down for high-interest tiles (aggregated across all users)
            drilldown = [
                d for d in all_interactions
                if d.interest_score >= 3.0 and d.tile_silo == current_silo["id"]
            ]
            if drilldown:
                top = max(drilldown, key=lambda d: d.interest_score)
                logger.info(f"Drill-down triggered for '{top.tile_title}' (score={top.interest_score})")
                await _generate_drilldown(top, current_silo, table_info, past_titles, workspace_id, tile_store)

            tile_store.broadcast_status("agent_idle")

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Agent cycle error for workspace {workspace_id}: {e}", exc_info=True)
            tile_store.broadcast_status("agent_idle")
            await asyncio.sleep(min(AGENT_CYCLE_SECONDS * 2, 60))

        cycle += 1
        await asyncio.sleep(AGENT_CYCLE_SECONDS)


def _build_interest_context(interactions: list) -> str:
    positive = [i for i in interactions if i.interest_score > 0]
    liked = sorted(positive, key=lambda i: i.interest_score, reverse=True)[:5]
    disliked = [i for i in interactions if i.interest_score < 0]

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


async def _generate_drilldown(interaction, silo: dict, table_info: dict,
                               past_titles: list[str], workspace_id: str, tile_store):
    try:
        data_profile = get_data_profile(workspace_id)

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

Generate ONE deeper follow-up analytical question that builds on this finding.

Return ONLY the question text, nothing else."""

        question = await generate(prompt, temperature=0.7)
        sql = await _generate_sql(question, table_info, workspace_id)
        try:
            results = run_query(sql, workspace_id=workspace_id)
        except Exception as e:
            logger.warning(f"Drill-down query failed: {e}")
            sql = await _fix_sql(sql, str(e), table_info)
            results = run_query(sql, workspace_id=workspace_id)

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


def _build_system_prompt(table_info: dict, dataset_context: str = "", join_context: str = "") -> str:
    tables_desc = []
    for i, (table, cols) in enumerate(table_info.items(), 1):
        col_names = ", ".join(c["name"] for c in cols)
        tables_desc.append(f"{i}. {table} — Columns: {col_names}")
    tables_text = "\n".join(tables_desc)

    profile_block = ""
    if dataset_context:
        profile_block = f"""

Dataset context (semantic understanding of the data):
{dataset_context}
"""

    join_block = ""
    if join_context:
        join_block = f"""

{join_context}
When querying across tables, always use these defined join keys.
"""

    return f"""You are SENTINEL, an AI analyst monitoring data loaded into a dashboard.
You generate insights by querying these datasets:

{tables_text}
{profile_block}{join_block}
Your job: find non-obvious patterns, anomalies, trends, and correlations.
Write DuckDB-compatible SQL. Use double quotes for column names with spaces/special chars.
Be specific — cite actual numbers and values from the data."""


async def _generate_question(silo: dict, table_info: dict, past_titles: list[str],
                              interest_context: str = "", dataset_context: str = "",
                              join_context: str = "") -> str:
    system = _build_system_prompt(table_info, dataset_context, join_context)
    # Note: get_data_profile needs workspace_id but we don't have it here
    # The table_info is already workspace-scoped, so the profile is implicit
    data_profile = ""
    # Build a mini-profile from table_info
    for table, cols in table_info.items():
        col_names = ", ".join(f'"{c["name"]}" ({c["type"]})' for c in cols)
        data_profile += f"\n{table}: {col_names}\n"

    past = "\n".join(f"- {t}" for t in past_titles[-10:]) if past_titles else "None yet"

    silo_context = ""
    tables = list(table_info.keys())
    if silo["id"] == "alpha":
        if len(tables) > 1:
            silo_context = f"Generate a CROSS-THEME question that correlates data across multiple tables ({', '.join(tables)})."
        else:
            silo_context = f"Generate a broad question about overall patterns in the {tables[0]} table."
    else:
        description = silo.get("description", "")
        label = silo.get("label", silo["id"])
        if description:
            silo_context = f'Analytical theme: "{label}" — {description}'
        else:
            silo_context = f'Focus on the analytical theme: "{label}".'

    interest_block = ""
    if interest_context:
        interest_block = f"""
User engagement signals:
{interest_context}
"""

    prompt = f"""{system}

{silo_context}
{interest_block}
Previously generated findings (avoid repeating):
{past}

Generate ONE specific analytical question about the data. Return ONLY the question text."""

    return await generate(prompt, temperature=0.8)


async def _generate_sql(question: str, table_info: dict, workspace_id: str = "",
                         join_context: str = "") -> str:
    tables_desc = ""
    for table, cols in table_info.items():
        col_names = ", ".join(f'"{c["name"]}" ({c["type"]})' for c in cols)
        tables_desc += f"\n{table}: {col_names}\n"

    join_block = ""
    if join_context:
        join_block = f"""
{join_context}
- When querying across tables, use ONLY these defined join keys
"""

    prompt = f"""Write a DuckDB SQL query to answer this question:

{question}

Available tables:
{tables_desc}
{join_block}
Rules:
- Use double quotes for column names with spaces or special characters
- Use DuckDB syntax
- Limit results to 20 rows max
- Return meaningful aggregations, not raw rows
- Handle NULLs gracefully
- Keep queries CONCISE
- Do NOT add comments in the SQL
- For ANY date/time columns, ALWAYS use TRY_CAST(col AS DATE) or TRY_CAST(col AS TIMESTAMP) instead of direct casts — data may have mixed or inconsistent date formats
- Never use strptime or strftime with a fixed format string — use TRY_CAST which auto-detects formats

Return ONLY the SQL query, no explanation, no markdown fences."""

    sql = await generate(prompt, temperature=0.2)
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

Fix the query. For date parsing errors, use TRY_CAST(col AS DATE) instead of CAST or strptime — it auto-detects formats.
Return ONLY the corrected SQL, no explanation."""

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

Return JSON: {{"interesting": true/false, "reason": "brief explanation", "priority": "{row_ids}"}}"""

    try:
        result = await generate_json(prompt, temperature=0.3)
        priority = result.get("priority", rows[1]["id"])
        valid_ids = {r["id"] for r in rows}
        if priority not in valid_ids:
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
- title: Short, specific headline (max 80 chars).
- summary: 1-2 sentence explanation with key numbers.
- detail: 2-3 paragraph deep analysis.
- column: One of {row_ids}.
{row_context}
- chart: Sparkline pattern — "rising", "declining", "volatile", "stable", "spike", "plateau", or null.
- chartLabel: Short label for the sparkline.
- metric: Key number as string.
- metricSub: Metric context.
- sources: Array of source labels.
- suggestedQuestions: Array of 3-4 follow-up questions.

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
    if not results or len(results) < 2:
        return None

    numeric_cols = []
    for key, val in results[0].items():
        if isinstance(val, (int, float)):
            numeric_cols.append(key)

    if not numeric_cols:
        return None

    metric_keywords = ["rate", "count", "avg", "sum", "total", "percent", "ratio", "pct"]
    best_col = numeric_cols[0]
    for col in numeric_cols:
        if any(kw in col.lower() for kw in metric_keywords):
            best_col = col
            break

    values = []
    for row in results[:20]:
        v = row.get(best_col)
        if v is not None and isinstance(v, (int, float)):
            values.append(float(v))

    return values if len(values) >= 2 else None
