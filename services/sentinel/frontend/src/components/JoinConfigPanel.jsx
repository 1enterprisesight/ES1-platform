import { useState } from "react";
import { validateJoin, saveJoinConfig } from "../api.js";

export default function JoinConfigPanel({ workspaceId, suggestion, onConfirmed, onDismiss }) {
  const [validating, setValidating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [validation, setValidation] = useState(null);
  const [error, setError] = useState(null);

  // suggestion shape from backend _suggest_join:
  // { left_table, right_table, left_column, right_column, types_match, all_candidates }
  const { left_table, right_table, left_column, right_column } = suggestion;

  const handleValidate = async () => {
    setValidating(true);
    setError(null);
    setValidation(null);
    try {
      const result = await validateJoin(workspaceId, {
        left_table, right_table, left_column, right_column,
      });
      setValidation(result);
    } catch (e) {
      setError(e.message);
    }
    setValidating(false);
  };

  const handleConfirm = async () => {
    setSaving(true);
    setError(null);
    try {
      await saveJoinConfig(workspaceId, [
        { left_table, right_table, left_column, right_column },
      ]);
      if (onConfirmed) onConfirmed();
    } catch (e) {
      setError(e.message);
    }
    setSaving(false);
  };

  return (
    <div style={{
      marginTop: 12, padding: "12px 14px", borderRadius: 7,
      background: "rgba(129,140,248,0.04)", border: "1px solid rgba(129,140,248,0.15)",
    }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
        <div style={{
          fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em",
          color: "rgba(129,140,248,0.6)", fontFamily: "'JetBrains Mono',monospace",
        }}>Link Detected</div>
        <button onClick={onDismiss} style={{
          background: "none", border: "none", color: "rgba(255,255,255,0.2)",
          cursor: "pointer", padding: 2, fontSize: 14, lineHeight: 1,
        }}>&times;</button>
      </div>

      <div style={{ fontSize: 10, color: "rgba(255,255,255,0.5)", lineHeight: 1.6, marginBottom: 10, fontFamily: "'DM Sans',sans-serif" }}>
        <strong style={{ color: "rgba(255,255,255,0.7)" }}>{left_table}</strong>
        {" and "}
        <strong style={{ color: "rgba(255,255,255,0.7)" }}>{right_table}</strong>
        {" can be linked via "}
        <code style={{ background: "rgba(255,255,255,0.06)", padding: "1px 4px", borderRadius: 3, fontSize: 9 }}>
          {left_column}{left_column !== right_column ? ` = ${right_column}` : ""}
        </code>
      </div>

      {error && (
        <div style={{
          padding: "5px 8px", marginBottom: 8, borderRadius: 4,
          background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.15)",
          color: "rgba(239,68,68,0.7)", fontSize: 9,
        }}>{error}</div>
      )}

      {validation && (
        <div style={{
          padding: "8px 10px", marginBottom: 8, borderRadius: 5,
          background: validation.valid ? "rgba(52,211,153,0.06)" : "rgba(251,191,36,0.06)",
          border: `1px solid ${validation.valid ? "rgba(52,211,153,0.15)" : "rgba(251,191,36,0.15)"}`,
          fontSize: 9, color: "rgba(255,255,255,0.5)", lineHeight: 1.6,
        }}>
          <div style={{ fontWeight: 600, color: validation.valid ? "rgba(52,211,153,0.8)" : "rgba(251,191,36,0.8)", marginBottom: 4 }}>
            {validation.valid ? "Join looks good" : "Review recommended"}
          </div>
          {validation.left_total != null && <div>{left_table}: {validation.left_total.toLocaleString()} rows</div>}
          {validation.right_total != null && <div>{right_table}: {validation.right_total.toLocaleString()} rows</div>}
          {validation.matched_rows != null && <div>Matched: {validation.matched_rows.toLocaleString()}</div>}
          {validation.left_orphans != null && validation.left_orphans > 0 && (
            <div style={{ color: "rgba(251,191,36,0.7)" }}>Left unmatched: {validation.left_orphans.toLocaleString()}</div>
          )}
          {validation.right_orphans != null && validation.right_orphans > 0 && (
            <div style={{ color: "rgba(251,191,36,0.7)" }}>Right unmatched: {validation.right_orphans.toLocaleString()}</div>
          )}
        </div>
      )}

      <div style={{ display: "flex", gap: 6 }}>
        {!validation && (
          <button onClick={handleValidate} disabled={validating} style={{
            flex: 1, padding: "6px 0", borderRadius: 5, fontSize: 9, fontWeight: 600,
            background: "rgba(129,140,248,0.08)", border: "1px solid rgba(129,140,248,0.2)",
            color: "rgba(129,140,248,0.7)", cursor: validating ? "wait" : "pointer",
            fontFamily: "'DM Sans',sans-serif", transition: "all 0.15s",
          }}>{validating ? "Validating..." : "Test Join"}</button>
        )}
        {validation?.valid && (
          <button onClick={handleConfirm} disabled={saving} style={{
            flex: 1, padding: "6px 0", borderRadius: 5, fontSize: 9, fontWeight: 600,
            background: "rgba(52,211,153,0.08)", border: "1px solid rgba(52,211,153,0.2)",
            color: "rgba(52,211,153,0.7)", cursor: saving ? "wait" : "pointer",
            fontFamily: "'DM Sans',sans-serif", transition: "all 0.15s",
          }}>{saving ? "Saving..." : "Confirm Link"}</button>
        )}
        {validation && !validation.valid && (
          <button onClick={handleValidate} disabled={validating} style={{
            flex: 1, padding: "6px 0", borderRadius: 5, fontSize: 9, fontWeight: 600,
            background: "rgba(251,191,36,0.08)", border: "1px solid rgba(251,191,36,0.2)",
            color: "rgba(251,191,36,0.7)", cursor: validating ? "wait" : "pointer",
            fontFamily: "'DM Sans',sans-serif", transition: "all 0.15s",
          }}>{validating ? "Validating..." : "Re-test"}</button>
        )}
        {validation && !validation.valid && (
          <button onClick={handleConfirm} disabled={saving} style={{
            padding: "6px 10px", borderRadius: 5, fontSize: 9, fontWeight: 600,
            background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)",
            color: "rgba(255,255,255,0.35)", cursor: saving ? "wait" : "pointer",
            fontFamily: "'DM Sans',sans-serif", transition: "all 0.15s",
          }}>{saving ? "Saving..." : "Confirm Anyway"}</button>
        )}
      </div>
    </div>
  );
}
