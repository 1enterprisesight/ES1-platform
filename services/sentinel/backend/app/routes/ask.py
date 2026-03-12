"""Ask endpoint — workspace-scoped question answering."""
import json
import logging
from typing import Optional, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import require_user, SessionInfo
from app.db import run_query, get_workspace_table_info, is_workspace_loaded, load_workspace_datasets
from app.database import get_pool
from app.llm import generate, generate_json, get_langfuse
from app.tiles import Tile, get_tile_store, get_interaction_store

logger = logging.getLogger(__name__)
router = APIRouter()


class AskRequest(BaseModel):
    question: str = Field(..., max_length=500)
    tile_context: Optional[Dict] = None
    create_tile: bool = False


class AskResponse(BaseModel):
    answer: str
    sql: Optional[str] = None
    data: Optional[List[Dict]] = None
    tile: Optional[Dict] = None


async def _ensure_workspace_loaded(workspace_id: str):
    """Load workspace datasets into DuckDB if not already present (e.g. after restart)."""
    if is_workspace_loaded(workspace_id):
        return
    import uuid as _uuid
    pool = get_pool()
    ds_rows = await pool.fetch(
        "SELECT name, csv_data FROM sentinel.datasets WHERE workspace_id = $1 ORDER BY uploaded_at",
        _uuid.UUID(workspace_id),
    )
    if ds_rows:
        load_workspace_datasets(workspace_id, [(r["name"], bytes(r["csv_data"])) for r in ds_rows])
        logger.info(f"Auto-loaded {len(ds_rows)} dataset(s) into DuckDB for workspace {workspace_id}")


@router.post("/ask", response_model=AskResponse)
async def ask(body: AskRequest, session: SessionInfo = Depends(require_user)):
    workspace_id = session.workspace_id
    if not workspace_id:
        raise HTTPException(status_code=400, detail="No active workspace")

    await _ensure_workspace_loaded(workspace_id)
    table_info = get_workspace_table_info(workspace_id)
    tables_desc = ""
    for table, cols in table_info.items():
        col_names = ", ".join(f'"{c["name"]}" ({c["type"]})' for c in cols)
        tables_desc += f"\n{table}: {col_names}\n"

    # Langfuse trace for user question
    lf = get_langfuse()
    trace = None
    if lf:
        try:
            trace = lf.trace(
                name=f"User Question — {body.question[:60]}",
                session_id=f"workspace-{workspace_id}",
                user_id=session.user.id,
                metadata={
                    "workspace_id": workspace_id,
                    "question": body.question,
                    "has_tile_context": body.tile_context is not None,
                    "create_tile": body.create_tile,
                },
                tags=["user-question"],
            )
        except Exception:
            pass

    context = ""
    if body.tile_context:
        context = f"""This question is a follow-up to a dashboard finding:
Title: {body.tile_context.get('title', '')}
Summary: {body.tile_context.get('summary', '')}
Detail: {body.tile_context.get('detail', '')}

"""

    # Generate SQL
    sql_prompt = f"""{context}User question: {body.question}

Available tables:
{tables_desc}

Write a DuckDB SQL query to answer this question. Use double quotes for column names with spaces.
Limit to 20 rows. Return ONLY the SQL query."""

    try:
        sql = await generate(sql_prompt, temperature=0.2, parent=trace, generation_name="generate-sql")
        sql = sql.strip()
        if sql.startswith("```"):
            lines = sql.split("\n")
            sql = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        sql = sql.strip()

        if trace:
            try:
                sql_span = trace.span(name="execute-sql", input=sql[:300])
            except Exception:
                sql_span = None
        else:
            sql_span = None

        results = run_query(sql, workspace_id=workspace_id)

        if sql_span:
            try:
                sql_span.end(output={"row_count": len(results)})
            except Exception:
                pass

        # Synthesize answer
        answer_prompt = f"""{context}User question: {body.question}

Query results:
{json.dumps(results[:15], default=str, indent=2)}

Provide a clear, concise answer based on the data. Reference specific numbers.
Keep it to 2-3 sentences."""

        answer = await generate(answer_prompt, temperature=0.4, parent=trace, generation_name="synthesize-answer")

        tile_data = None
        if body.create_tile:
            tile_store = get_tile_store(workspace_id)
            interaction_store = get_interaction_store(workspace_id, session.user.id)

            # Build bar chart from query results if data has a label+numeric pattern
            bar_charts = None
            if results and len(results) > 0 and len(results) <= 20:
                cols = list(results[0].keys())
                label_col = None
                value_cols = []
                for col in cols:
                    sample = results[0][col]
                    if isinstance(sample, (int, float)) and not label_col:
                        value_cols.append(col)
                    elif isinstance(sample, str) and label_col is None:
                        label_col = col
                    elif isinstance(sample, (int, float)):
                        value_cols.append(col)
                if label_col and value_cols:
                    from app.tiles import BarChart, BarData
                    charts = []
                    for vc in value_cols[:3]:
                        vals = [float(r.get(vc, 0)) for r in results]
                        max_val = max(vals) if vals else 1
                        bars = [BarData(label=str(r.get(label_col, "")), value=float(r.get(vc, 0)), max=max_val) for r in results]
                        charts.append(BarChart(title=vc, bars=bars))
                    bar_charts = charts if charts else None

            # Build metric from first result row
            metric_val = None
            metric_sub = None
            if results and len(results) > 0:
                cols = list(results[0].keys())
                for col in cols:
                    v = results[0][col]
                    if isinstance(v, (int, float)):
                        metric_val = f"{v:,.0f}" if isinstance(v, (int, float)) and v > 100 else str(v)
                        metric_sub = col
                        break

            tile = Tile(
                silo="user_question",
                column="resolved",
                title=body.question,
                summary=answer.strip(),
                detail=f"{answer.strip()}\n\n---\nSQL: {sql}",
                sources=["User Question"],
                barCharts=bar_charts,
                metric=metric_val,
                metricSub=metric_sub,
            )
            await tile_store.add_tile(tile)
            tile_data = tile.model_dump()

            await interaction_store.record(tile.id, {
                "tile_title": tile.title,
                "tile_silo": "user_question",
                "tile_summary": answer.strip(),
                "expanded": True,
                "followup_questions": [body.question],
                "thumbs_up": 1,
            })

        if trace:
            try:
                trace.update(output=answer[:300], metadata={
                    "outcome": "answered",
                    "result_rows": len(results),
                    "tile_created": body.create_tile,
                })
            except Exception:
                pass

        return AskResponse(answer=answer, sql=sql, data=results[:15], tile=tile_data)

    except Exception as e:
        logger.error(f"Ask failed: {e}", exc_info=True)
        if trace:
            try:
                trace.update(level="ERROR", status_message=str(e))
            except Exception:
                pass
        raise HTTPException(500, "Failed to process your question. Please try again.")
