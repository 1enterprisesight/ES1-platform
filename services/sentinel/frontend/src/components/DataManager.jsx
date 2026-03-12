import { useState, useEffect, useRef } from "react";
import { fetchDatasets, uploadDataset, deleteDataset, reloadDatasets, validateJoin, saveJoinConfig, activateData } from "../api.js";

const MAX_FILES = 3;

export default function DataManager({ onReload, workspaceId, dataStatus, onDataStatusChange }) {
  const [open, setOpen] = useState(false);
  const [datasets, setDatasets] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [reloading, setReloading] = useState(false);
  const [activating, setActivating] = useState(false);
  const [error, setError] = useState(null);
  const [joinCandidates, setJoinCandidates] = useState(null);
  const fileRef = useRef(null);
  const panelRef = useRef(null);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e) => {
      if (panelRef.current && !panelRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  // Linking state
  const [confirmedLinks, setConfirmedLinks] = useState([]);
  const [savedLinks, setSavedLinks] = useState([]);  // What's persisted on server
  const [linkEditor, setLinkEditor] = useState(null);
  const [validationResult, setValidationResult] = useState(null);
  const [validating, setValidating] = useState(false);
  const [savingLinks, setSavingLinks] = useState(false);

  // Auto-open when data isn't activated (user needs to set up data)
  useEffect(() => {
    if (dataStatus && !dataStatus.data_activated) setOpen(true);
  }, [dataStatus?.data_activated]);

  useEffect(() => {
    if (open) loadData();
  }, [open]);

  // Seed confirmed links from data status
  useEffect(() => {
    if (dataStatus?.links?.length > 0) {
      setConfirmedLinks(dataStatus.links);
      setSavedLinks(dataStatus.links);
    }
  }, [dataStatus?.links]);

  const loadData = async () => {
    try {
      const d = await fetchDatasets();
      setDatasets(d.datasets || []);
      if (d.join_candidates) setJoinCandidates(d.join_candidates);
      if (d.data_status && onDataStatusChange) onDataStatusChange(d.data_status);
    } catch (e) {
      console.error("Failed to fetch datasets:", e);
    }
  };

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      await uploadDataset(file);
      await loadData();
    } catch (err) {
      setError(err.message);
      setTimeout(() => setError(null), 5000);
    }
    setUploading(false);
    if (fileRef.current) fileRef.current.value = "";
  };

  const handleDelete = async (id) => {
    try {
      await deleteDataset(id);
      await loadData();
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

  const handleActivate = async () => {
    setActivating(true);
    setError(null);
    try {
      const result = await activateData(workspaceId);
      if (result.data_status && onDataStatusChange) onDataStatusChange(result.data_status);
      if (result.data_status?.data_activated) setOpen(false);
    } catch (err) {
      setError(err.message);
      setTimeout(() => setError(null), 5000);
    }
    setActivating(false);
  };

  // --- Linking helpers ---
  const normalize = (s) => s.toLowerCase().replace(/[^a-z0-9]/g, "_").replace(/^_+|_+$/g, "");

  const getTableColumns = (tableName) => {
    const ds = datasets.find((d) =>
      d.table_name === tableName || d.name === tableName || normalize(d.name) === tableName
    );
    if (!ds) return [];
    const cols = typeof ds.columns === "string" ? JSON.parse(ds.columns) : ds.columns;
    return Array.isArray(cols) ? cols : [];
  };

  const startLink = (leftTable, rightTable) => {
    let leftCol = "", rightCol = "";
    // Pre-fill from candidates
    if (joinCandidates?.all_candidates) {
      const match = joinCandidates.all_candidates.find(
        (c) => (c.left_table === leftTable && c.right_table === rightTable) ||
               (c.left_table === rightTable && c.right_table === leftTable)
      );
      if (match) {
        leftCol = match.left_table === leftTable ? match.left_column : match.right_column;
        rightCol = match.left_table === leftTable ? match.right_column : match.left_column;
      }
    }
    if (!leftCol && joinCandidates) {
      if (joinCandidates.left_table === leftTable && joinCandidates.right_table === rightTable) {
        leftCol = joinCandidates.left_column; rightCol = joinCandidates.right_column;
      } else if (joinCandidates.left_table === rightTable && joinCandidates.right_table === leftTable) {
        leftCol = joinCandidates.right_column; rightCol = joinCandidates.left_column;
      }
    }
    setLinkEditor({ leftTable, rightTable, leftCol, rightCol });
    setValidationResult(null);
    setError(null);
  };

  const handleValidateLink = async () => {
    if (!linkEditor) return;
    setValidating(true); setError(null); setValidationResult(null);
    try {
      const result = await validateJoin(workspaceId, {
        left_table: linkEditor.leftTable, right_table: linkEditor.rightTable,
        left_column: linkEditor.leftCol, right_column: linkEditor.rightCol,
      });
      setValidationResult(result);
    } catch (e) { setError(e.message); }
    setValidating(false);
  };

  const handleConfirmLink = () => {
    if (!linkEditor || !validationResult) return;
    const newLink = {
      left_table: linkEditor.leftTable, right_table: linkEditor.rightTable,
      left_column: linkEditor.leftCol, right_column: linkEditor.rightCol,
    };
    setConfirmedLinks((prev) => {
      const filtered = prev.filter((l) => !(
        (l.left_table === newLink.left_table && l.right_table === newLink.right_table) ||
        (l.left_table === newLink.right_table && l.right_table === newLink.left_table)
      ));
      return [...filtered, newLink];
    });
    setLinkEditor(null); setValidationResult(null);
  };

  const linksChanged = () => {
    if (confirmedLinks.length !== savedLinks.length) return true;
    return confirmedLinks.some((link, i) => {
      const saved = savedLinks[i];
      if (!saved) return true;
      return link.left_table !== saved.left_table || link.right_table !== saved.right_table ||
             link.left_column !== saved.left_column || link.right_column !== saved.right_column;
    });
  };

  const handleSaveLinks = async () => {
    if (confirmedLinks.length === 0) return;
    setSavingLinks(true); setError(null);
    try {
      const result = await saveJoinConfig(workspaceId, confirmedLinks);
      if (result.data_status && onDataStatusChange) onDataStatusChange(result.data_status);
      const newLinks = result.links || confirmedLinks;
      setConfirmedLinks(newLinks);
      setSavedLinks(newLinks);
    } catch (e) {
      setError(e.message);
      setTimeout(() => setError(null), 5000);
    }
    setSavingLinks(false);
  };

  const removeLink = (index) => setConfirmedLinks((prev) => prev.filter((_, i) => i !== index));

  const formatSize = (bytes) => {
    if (!bytes) return "";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // Derived state
  const tables = dataStatus?.tables || [];
  const tableCount = tables.length;
  const linksNeeded = Math.max(0, tableCount - 1);
  const canActivate = dataStatus?.can_activate || false;
  const dataActivated = dataStatus?.data_activated || false;
  const needsLinking = tableCount >= 2;

  const getUnlinkedPairs = () => {
    if (tableCount < 2) return [];
    const pairs = [];
    for (let i = 0; i < tables.length; i++) {
      for (let j = i + 1; j < tables.length; j++) {
        const hasLink = confirmedLinks.some((l) =>
          (l.left_table === tables[i] && l.right_table === tables[j]) ||
          (l.left_table === tables[j] && l.right_table === tables[i])
        );
        if (!hasLink) pairs.push([tables[i], tables[j]]);
      }
    }
    return pairs;
  };
  const unlinkedPairs = getUnlinkedPairs();

  return (
    <div ref={panelRef} style={{ position: "relative", flexShrink: 0 }}>
      <button
        onClick={(e) => { e.stopPropagation(); setOpen((p) => !p); }}
        style={{
          display: "flex", alignItems: "center", gap: 6, padding: "4px 10px", borderRadius: 5,
          border: `1px solid ${open ? "rgba(52,211,153,0.5)" : !dataActivated ? "rgba(251,191,36,0.4)" : "rgba(52,211,153,0.25)"}`,
          background: open ? "rgba(52,211,153,0.1)" : !dataActivated ? "rgba(251,191,36,0.08)" : "rgba(52,211,153,0.04)",
          color: open ? "rgba(52,211,153,1)" : !dataActivated ? "rgba(251,191,36,1)" : "rgba(52,211,153,0.85)",
          fontSize: 10, fontWeight: 600, cursor: "pointer", transition: "all .15s",
          fontFamily: "'JetBrains Mono',monospace",
        }}
        onMouseEnter={(e) => { if (!open) { e.currentTarget.style.borderColor = !dataActivated ? "rgba(251,191,36,0.5)" : "rgba(52,211,153,0.4)"; e.currentTarget.style.color = !dataActivated ? "rgba(251,191,36,1)" : "rgba(52,211,153,1)"; e.currentTarget.style.background = !dataActivated ? "rgba(251,191,36,0.1)" : "rgba(52,211,153,0.08)"; }}}
        onMouseLeave={(e) => { if (!open) { e.currentTarget.style.borderColor = !dataActivated ? "rgba(251,191,36,0.4)" : "rgba(52,211,153,0.25)"; e.currentTarget.style.color = !dataActivated ? "rgba(251,191,36,1)" : "rgba(52,211,153,0.85)"; e.currentTarget.style.background = !dataActivated ? "rgba(251,191,36,0.08)" : "rgba(52,211,153,0.04)"; }}}
      >
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" /><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
        </svg>
        Data
        {!dataActivated && <span style={{ fontSize: 8, opacity: 0.7 }}>(setup)</span>}
        <svg width="8" height="8" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" style={{ transform: open ? "rotate(180deg)" : "rotate(0)", transition: "transform 0.15s" }}>
          <path d="M3 4.5L6 7.5L9 4.5" />
        </svg>
      </button>

      {open && (
        <div onClick={(e) => e.stopPropagation()} style={{
          position: "absolute", top: "100%", left: 0, marginTop: 6, zIndex: 100,
          background: "#0f1117", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8,
          padding: "14px 16px", minWidth: 360, maxWidth: 420, boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
        }}>
          {/* Header: title + upload + file count */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{ fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "rgba(255,255,255,0.3)", fontFamily: "'JetBrains Mono',monospace" }}>
                Datasets
              </div>
              <span style={{ fontSize: 8, color: "rgba(255,255,255,0.15)", fontFamily: "'JetBrains Mono',monospace" }}>
                {tableCount}/{MAX_FILES}
              </span>
            </div>
            <div style={{ display: "flex", gap: 6 }}>
              {tableCount < MAX_FILES && (
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
              )}
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

          {/* Error */}
          {error && (
            <div style={{
              padding: "6px 10px", marginBottom: 10, borderRadius: 5,
              background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.2)",
              color: "rgba(239,68,68,0.7)", fontSize: 10, lineHeight: 1.4,
            }}>{error}</div>
          )}

          {/* File limit warning */}
          {tableCount >= MAX_FILES && (
            <div style={{
              padding: "5px 8px", marginBottom: 10, borderRadius: 4,
              background: "rgba(251,191,36,0.04)", border: "1px solid rgba(251,191,36,0.12)",
              color: "rgba(251,191,36,0.6)", fontSize: 9,
            }}>Maximum {MAX_FILES} files reached. Delete a file to upload another.</div>
          )}

          {/* Dataset list */}
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
                      {ds.row_count?.toLocaleString()} rows · {typeof ds.columns === "string" ? JSON.parse(ds.columns).length : Array.isArray(ds.columns) ? ds.columns.length : ds.columns} cols{ds.file_size ? ` · ${formatSize(ds.file_size)}` : ""}
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

          {/* --- Linking section (2+ tables) --- */}
          {needsLinking && (
            <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid rgba(255,255,255,0.05)" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
                <div style={{ fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "rgba(129,140,248,0.5)", fontFamily: "'JetBrains Mono',monospace" }}>
                  Table Links
                </div>
                <span style={{ fontSize: 8, color: "rgba(255,255,255,0.15)", fontFamily: "'JetBrains Mono',monospace" }}>
                  {confirmedLinks.length}/{linksNeeded} needed
                </span>
              </div>

              {/* Confirmed links */}
              {confirmedLinks.map((link, i) => (
                <div key={i} style={{
                  display: "flex", alignItems: "center", gap: 6, padding: "6px 8px", marginBottom: 4,
                  background: "rgba(52,211,153,0.04)", border: "1px solid rgba(52,211,153,0.12)",
                  borderRadius: 5,
                }}>
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="rgba(52,211,153,0.6)" strokeWidth="2.5" strokeLinecap="round"><polyline points="20 6 9 17 4 12" /></svg>
                  <div style={{ flex: 1, fontSize: 9, color: "rgba(255,255,255,0.45)", lineHeight: 1.4 }}>
                    <strong style={{ color: "rgba(255,255,255,0.6)" }}>{link.left_table}</strong>
                    <code style={{ background: "rgba(255,255,255,0.05)", padding: "0 3px", borderRadius: 2, fontSize: 8, margin: "0 2px" }}>{link.left_column}</code>
                    {" = "}
                    <strong style={{ color: "rgba(255,255,255,0.6)" }}>{link.right_table}</strong>
                    <code style={{ background: "rgba(255,255,255,0.05)", padding: "0 3px", borderRadius: 2, fontSize: 8, margin: "0 2px" }}>{link.right_column}</code>
                  </div>
                  <button onClick={() => removeLink(i)} style={{
                    background: "none", border: "none", color: "rgba(255,255,255,0.12)", cursor: "pointer", padding: 1, transition: "color 0.15s",
                  }}
                    onMouseEnter={(e) => { e.currentTarget.style.color = "rgba(239,68,68,0.5)"; }}
                    onMouseLeave={(e) => { e.currentTarget.style.color = "rgba(255,255,255,0.12)"; }}
                  >
                    <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
                  </button>
                </div>
              ))}

              {/* Unlinked pairs */}
              {unlinkedPairs.map(([t1, t2], i) => !linkEditor && (
                <button key={i} onClick={() => startLink(t1, t2)} style={{
                  display: "flex", alignItems: "center", gap: 6, padding: "6px 8px", marginBottom: 4, width: "100%",
                  background: "rgba(129,140,248,0.03)", border: "1px dashed rgba(129,140,248,0.18)",
                  borderRadius: 5, cursor: "pointer", transition: "all 0.15s", textAlign: "left",
                }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(129,140,248,0.07)"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = "rgba(129,140,248,0.03)"; }}
                >
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="rgba(129,140,248,0.4)" strokeWidth="2" strokeLinecap="round"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
                  <span style={{ fontSize: 9, color: "rgba(129,140,248,0.5)" }}>
                    Link <strong style={{ color: "rgba(129,140,248,0.7)" }}>{t1}</strong> and <strong style={{ color: "rgba(129,140,248,0.7)" }}>{t2}</strong>
                  </span>
                </button>
              ))}

              {/* Link editor */}
              {linkEditor && (
                <div style={{
                  padding: "10px 12px", borderRadius: 6, marginBottom: 4,
                  background: "rgba(129,140,248,0.04)", border: "1px solid rgba(129,140,248,0.15)",
                }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
                    <span style={{ fontSize: 9, fontWeight: 600, color: "rgba(129,140,248,0.6)" }}>
                      {linkEditor.leftTable} &rarr; {linkEditor.rightTable}
                    </span>
                    <button onClick={() => { setLinkEditor(null); setValidationResult(null); }} style={{
                      background: "none", border: "none", color: "rgba(255,255,255,0.2)", cursor: "pointer", padding: 1, fontSize: 13, lineHeight: 1,
                    }}>&times;</button>
                  </div>

                  <div style={{ display: "flex", gap: 6, marginBottom: 8 }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 8, color: "rgba(255,255,255,0.2)", marginBottom: 3 }}>{linkEditor.leftTable}</div>
                      <select value={linkEditor.leftCol} onChange={(e) => setLinkEditor((p) => ({ ...p, leftCol: e.target.value }))} style={{
                        width: "100%", padding: "5px 6px", borderRadius: 4, fontSize: 9,
                        background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.1)",
                        color: "rgba(255,255,255,0.6)", outline: "none",
                      }}>
                        <option value="">Select column...</option>
                        {getTableColumns(linkEditor.leftTable).map((col) => <option key={col} value={col}>{col}</option>)}
                      </select>
                    </div>
                    <div style={{ display: "flex", alignItems: "flex-end", paddingBottom: 5, color: "rgba(255,255,255,0.15)", fontSize: 10 }}>=</div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 8, color: "rgba(255,255,255,0.2)", marginBottom: 3 }}>{linkEditor.rightTable}</div>
                      <select value={linkEditor.rightCol} onChange={(e) => setLinkEditor((p) => ({ ...p, rightCol: e.target.value }))} style={{
                        width: "100%", padding: "5px 6px", borderRadius: 4, fontSize: 9,
                        background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.1)",
                        color: "rgba(255,255,255,0.6)", outline: "none",
                      }}>
                        <option value="">Select column...</option>
                        {getTableColumns(linkEditor.rightTable).map((col) => <option key={col} value={col}>{col}</option>)}
                      </select>
                    </div>
                  </div>

                  {/* Validation result */}
                  {validationResult && (
                    <div style={{
                      padding: "6px 8px", marginBottom: 6, borderRadius: 4,
                      background: validationResult.valid ? "rgba(52,211,153,0.05)" : "rgba(251,191,36,0.05)",
                      border: `1px solid ${validationResult.valid ? "rgba(52,211,153,0.12)" : "rgba(251,191,36,0.12)"}`,
                      fontSize: 8, color: "rgba(255,255,255,0.45)", lineHeight: 1.6,
                    }}>
                      <div style={{ fontWeight: 600, color: validationResult.valid ? "rgba(52,211,153,0.7)" : "rgba(251,191,36,0.7)", marginBottom: 2 }}>
                        {validationResult.valid ? "Join looks good" : "Review recommended"}
                      </div>
                      {validationResult.matched_rows != null && <div>Matched: {validationResult.matched_rows.toLocaleString()} rows</div>}
                      {validationResult.left_orphans > 0 && <div style={{ color: "rgba(251,191,36,0.6)" }}>Unmatched left: {validationResult.left_orphans.toLocaleString()}</div>}
                      {validationResult.right_orphans > 0 && <div style={{ color: "rgba(251,191,36,0.6)" }}>Unmatched right: {validationResult.right_orphans.toLocaleString()}</div>}
                    </div>
                  )}

                  <div style={{ display: "flex", gap: 4 }}>
                    {!validationResult && (
                      <button onClick={handleValidateLink} disabled={validating || !linkEditor.leftCol || !linkEditor.rightCol} style={{
                        flex: 1, padding: "5px 0", borderRadius: 4, fontSize: 8, fontWeight: 600,
                        background: "rgba(129,140,248,0.08)", border: "1px solid rgba(129,140,248,0.2)",
                        color: (!linkEditor.leftCol || !linkEditor.rightCol) ? "rgba(129,140,248,0.3)" : "rgba(129,140,248,0.7)",
                        cursor: (validating || !linkEditor.leftCol || !linkEditor.rightCol) ? "default" : "pointer",
                      }}>{validating ? "Testing..." : "Test Join"}</button>
                    )}
                    {validationResult?.valid && (
                      <button onClick={handleConfirmLink} style={{
                        flex: 1, padding: "5px 0", borderRadius: 4, fontSize: 8, fontWeight: 600,
                        background: "rgba(52,211,153,0.08)", border: "1px solid rgba(52,211,153,0.2)",
                        color: "rgba(52,211,153,0.7)", cursor: "pointer",
                      }}>Confirm Link</button>
                    )}
                    {validationResult && !validationResult.valid && (
                      <>
                        <button onClick={handleValidateLink} disabled={validating} style={{
                          flex: 1, padding: "5px 0", borderRadius: 4, fontSize: 8, fontWeight: 600,
                          background: "rgba(251,191,36,0.08)", border: "1px solid rgba(251,191,36,0.2)",
                          color: "rgba(251,191,36,0.7)", cursor: validating ? "wait" : "pointer",
                        }}>{validating ? "Testing..." : "Re-test"}</button>
                        <button onClick={handleConfirmLink} style={{
                          padding: "5px 8px", borderRadius: 4, fontSize: 8, fontWeight: 600,
                          background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)",
                          color: "rgba(255,255,255,0.3)", cursor: "pointer",
                        }}>Confirm Anyway</button>
                      </>
                    )}
                  </div>
                </div>
              )}

              {/* Save links — only when links have been added/changed */}
              {confirmedLinks.length > 0 && confirmedLinks.length >= linksNeeded && linksChanged() && (
                <button onClick={handleSaveLinks} disabled={savingLinks} style={{
                  width: "100%", padding: "6px 0", borderRadius: 5, fontSize: 9, fontWeight: 600, marginTop: 4,
                  background: "rgba(129,140,248,0.08)", border: "1px solid rgba(129,140,248,0.2)",
                  color: "rgba(129,140,248,0.7)", cursor: savingLinks ? "wait" : "pointer",
                }}>{savingLinks ? "Saving..." : "Save Links"}</button>
              )}
            </div>
          )}

          {/* --- Activate button (when not yet activated) --- */}
          {!dataActivated && tableCount > 0 && (
            <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid rgba(255,255,255,0.05)" }}>
              {!canActivate && needsLinking && (
                <div style={{ fontSize: 9, color: "rgba(255,255,255,0.2)", marginBottom: 8, lineHeight: 1.5 }}>
                  Link all tables before activating. {dataStatus?.links_needed || 0} more link(s) needed.
                </div>
              )}
              {canActivate && (
                <div style={{ fontSize: 9, color: "rgba(255,255,255,0.2)", marginBottom: 8, lineHeight: 1.5 }}>
                  Data is ready. Activate to start the SENTINEL agent.
                </div>
              )}
              <button onClick={handleActivate} disabled={!canActivate || activating} style={{
                width: "100%", padding: "8px 0", borderRadius: 5, fontSize: 10, fontWeight: 700,
                letterSpacing: "0.04em", fontFamily: "'JetBrains Mono',monospace",
                background: canActivate ? (activating ? "rgba(52,211,153,0.06)" : "rgba(52,211,153,0.1)") : "rgba(255,255,255,0.02)",
                border: `1px solid ${canActivate ? "rgba(52,211,153,0.25)" : "rgba(255,255,255,0.05)"}`,
                color: canActivate ? (activating ? "rgba(52,211,153,0.5)" : "rgba(52,211,153,0.8)") : "rgba(255,255,255,0.12)",
                cursor: canActivate && !activating ? "pointer" : "default",
                transition: "all 0.2s",
              }}>{activating ? "Activating..." : "Activate Workspace"}</button>
            </div>
          )}

          {/* Status indicator when activated */}
          {dataActivated && (
            <div style={{
              marginTop: 10, padding: "6px 8px", borderRadius: 4,
              background: "rgba(52,211,153,0.04)", border: "1px solid rgba(52,211,153,0.1)",
              fontSize: 9, color: "rgba(52,211,153,0.5)", display: "flex", alignItems: "center", gap: 6,
            }}>
              <div style={{ width: 5, height: 5, borderRadius: "50%", background: "rgba(52,211,153,0.6)" }} />
              Data activated — agent running
            </div>
          )}
        </div>
      )}
    </div>
  );
}
