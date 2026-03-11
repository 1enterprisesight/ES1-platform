import { useState, useEffect, useRef } from "react";
import { fetchDatasets, uploadDataset, deleteDataset, reloadDatasets } from "../api.js";
import JoinConfigPanel from "./JoinConfigPanel.jsx";

export default function DataManager({ onReload, workspaceId }) {
  const [open, setOpen] = useState(false);
  const [datasets, setDatasets] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [reloading, setReloading] = useState(false);
  const [error, setError] = useState(null);
  const [joinSuggestion, setJoinSuggestion] = useState(null);
  const fileRef = useRef(null);

  useEffect(() => {
    if (open) {
      fetchDatasets()
        .then((d) => {
          setDatasets(d.datasets || []);
          if (d.join_candidates) setJoinSuggestion(d.join_candidates);
          else if (d.join_suggestion) setJoinSuggestion(d.join_suggestion);
        })
        .catch((e) => console.error("Failed to fetch datasets:", e));
    }
  }, [open]);

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const result = await uploadDataset(file);
      // result may contain { dataset: {...}, join_suggestion: {...} } or just the dataset
      const ds = result.dataset || result;
      setDatasets((prev) => [ds, ...prev]);
      // Show join suggestion if the backend detected linkable columns
      if (result.join_suggestion) {
        setJoinSuggestion(result.join_suggestion);
      }
    } catch (err) {
      setError(err.message);
      setTimeout(() => setError(null), 4000);
    }
    setUploading(false);
    if (fileRef.current) fileRef.current.value = "";
  };

  const handleDelete = async (id) => {
    try {
      await deleteDataset(id);
      setDatasets((prev) => prev.filter((d) => d.id !== id));
    } catch (err) {
      setError(err.message);
      setTimeout(() => setError(null), 4000);
    }
  };

  const handleReload = async () => {
    setReloading(true);
    setError(null);
    try {
      await reloadDatasets();
      if (onReload) onReload();
    } catch (err) {
      setError(err.message);
      setTimeout(() => setError(null), 4000);
    }
    setReloading(false);
  };

  const formatSize = (bytes) => {
    if (!bytes) return "—";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div style={{ position: "relative", flexShrink: 0 }}>
      <button
        onClick={(e) => { e.stopPropagation(); setOpen((p) => !p); }}
        style={{
          display: "flex", alignItems: "center", gap: 6, padding: "4px 10px", borderRadius: 5,
          border: `1px solid ${open ? "rgba(52,211,153,0.3)" : "rgba(255,255,255,0.06)"}`,
          background: open ? "rgba(52,211,153,0.06)" : "rgba(255,255,255,0.02)",
          color: open ? "rgba(52,211,153,0.8)" : "rgba(255,255,255,0.35)",
          fontSize: 10, fontWeight: 600, cursor: "pointer", transition: "all .15s",
          fontFamily: "'JetBrains Mono',monospace",
        }}
        onMouseEnter={(e) => { if (!open) { e.currentTarget.style.borderColor = "rgba(255,255,255,0.15)"; e.currentTarget.style.color = "rgba(255,255,255,0.5)"; }}}
        onMouseLeave={(e) => { if (!open) { e.currentTarget.style.borderColor = "rgba(255,255,255,0.06)"; e.currentTarget.style.color = "rgba(255,255,255,0.35)"; }}}
      >
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" /><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
        </svg>
        Data
        <svg width="8" height="8" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" style={{ transform: open ? "rotate(180deg)" : "rotate(0)", transition: "transform 0.15s" }}>
          <path d="M3 4.5L6 7.5L9 4.5" />
        </svg>
      </button>

      {open && (
        <div onClick={(e) => e.stopPropagation()} style={{
          position: "absolute", top: "100%", left: 0, marginTop: 6, zIndex: 100,
          background: "#0f1117", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8,
          padding: "14px 16px", minWidth: 320, boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
        }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
            <div style={{ fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "rgba(255,255,255,0.3)", fontFamily: "'JetBrains Mono',monospace" }}>
              Datasets
            </div>
            <div style={{ display: "flex", gap: 6 }}>
              <label style={{
                display: "flex", alignItems: "center", gap: 4, padding: "3px 8px", borderRadius: 4,
                background: "rgba(52,211,153,0.08)", border: "1px solid rgba(52,211,153,0.2)",
                color: "rgba(52,211,153,0.7)", fontSize: 9, fontWeight: 600,
                cursor: uploading ? "wait" : "pointer", fontFamily: "'DM Sans',sans-serif",
              }}>
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" />
                </svg>
                {uploading ? "Uploading..." : "Upload CSV"}
                <input ref={fileRef} type="file" accept=".csv" onChange={handleUpload} disabled={uploading} style={{ display: "none" }} />
              </label>
              {datasets.length > 0 && (
                <button onClick={handleReload} disabled={reloading} style={{
                  display: "flex", alignItems: "center", gap: 4, padding: "3px 8px", borderRadius: 4,
                  background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)",
                  color: "rgba(255,255,255,0.4)", fontSize: 9, fontWeight: 600,
                  cursor: reloading ? "wait" : "pointer", fontFamily: "'DM Sans',sans-serif",
                }}>
                  {reloading ? "Reloading..." : "Reload All"}
                </button>
              )}
            </div>
          </div>

          {error && (
            <div style={{
              padding: "6px 10px", marginBottom: 10, borderRadius: 5,
              background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.2)",
              color: "rgba(239,68,68,0.7)", fontSize: 10, lineHeight: 1.4,
            }}>{error}</div>
          )}

          {datasets.length === 0 ? (
            <div style={{ fontSize: 11, color: "rgba(255,255,255,0.2)", textAlign: "center", padding: "16px 0", fontFamily: "'DM Sans',sans-serif" }}>
              No datasets uploaded yet. Upload a CSV to get started.
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {datasets.map((ds) => (
                <div key={ds.id} style={{
                  display: "flex", alignItems: "center", gap: 10, padding: "8px 10px",
                  background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.04)",
                  borderRadius: 6,
                }}>
                  <div style={{
                    width: 6, height: 6, borderRadius: "50%", flexShrink: 0,
                    background: "#34d399", boxShadow: "0 0 6px rgba(52,211,153,0.4)",
                  }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 11, fontWeight: 600, color: "rgba(255,255,255,0.7)", fontFamily: "'DM Sans',sans-serif", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {ds.name}
                    </div>
                    <div style={{ fontSize: 9, color: "rgba(255,255,255,0.25)", fontFamily: "'JetBrains Mono',monospace", marginTop: 2 }}>
                      {ds.row_count?.toLocaleString()} rows · {typeof ds.columns === "string" ? JSON.parse(ds.columns).length : Array.isArray(ds.columns) ? ds.columns.length : ds.columns} cols · {formatSize(ds.file_size)}
                    </div>
                  </div>
                  <button onClick={() => handleDelete(ds.id)} style={{
                    background: "none", border: "none", color: "rgba(255,255,255,0.15)",
                    cursor: "pointer", padding: 4, flexShrink: 0, transition: "color 0.15s",
                  }}
                    onMouseEnter={(e) => { e.currentTarget.style.color = "rgba(239,68,68,0.6)"; }}
                    onMouseLeave={(e) => { e.currentTarget.style.color = "rgba(255,255,255,0.15)"; }}
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                      <polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Join config panel — shown when a join suggestion is available */}
          {joinSuggestion && workspaceId && (
            <JoinConfigPanel
              workspaceId={workspaceId}
              suggestion={joinSuggestion}
              onConfirmed={() => { setJoinSuggestion(null); if (onReload) onReload(); }}
              onDismiss={() => setJoinSuggestion(null)}
            />
          )}
        </div>
      )}
    </div>
  );
}
