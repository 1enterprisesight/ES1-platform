import { useState, useEffect, useRef } from "react";
import { fetchDatasets, uploadDataset, deleteDataset, validateJoin, saveJoinConfig, activateData, getDataStatus } from "../api.js";

const MAX_FILES = 3;

export default function DataSetupView({ workspaceId, initialDataStatus, onActivated }) {
  const [datasets, setDatasets] = useState([]);
  const [dataStatus, setDataStatus] = useState(initialDataStatus || null);
  const [uploading, setUploading] = useState(false);
  const [activating, setActivating] = useState(false);
  const [error, setError] = useState(null);
  const [joinCandidates, setJoinCandidates] = useState(null);
  const fileRef = useRef(null);

  // Link configuration state
  const [pendingLinks, setPendingLinks] = useState([]); // links user has configured
  const [linkEditor, setLinkEditor] = useState(null); // { leftTable, rightTable, leftCol, rightCol }
  const [validationResult, setValidationResult] = useState(null);
  const [validating, setValidating] = useState(false);
  const [savingLinks, setSavingLinks] = useState(false);

  useEffect(() => {
    loadData();
  }, [workspaceId]);

  const loadData = async () => {
    try {
      const d = await fetchDatasets();
      setDatasets(d.datasets || []);
      if (d.data_status) setDataStatus(d.data_status);
      if (d.join_candidates) setJoinCandidates(d.join_candidates);
      // Load existing confirmed links from data_status
      if (d.data_status?.links?.length > 0) {
        setPendingLinks(d.data_status.links);
      }
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
      await loadData(); // refresh everything
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
      setTimeout(() => setError(null), 5000);
    }
  };

  const handleActivate = async () => {
    setActivating(true);
    setError(null);
    try {
      const result = await activateData(workspaceId);
      setDataStatus(result.data_status);
      if (result.data_status?.data_activated && onActivated) {
        onActivated();
      }
    } catch (err) {
      setError(err.message);
      setTimeout(() => setError(null), 5000);
    }
    setActivating(false);
  };

  // Start linking two tables
  const startLink = (leftTable, rightTable) => {
    // Pre-fill with candidate suggestion if available
    let leftCol = "";
    let rightCol = "";
    if (joinCandidates?.all_candidates) {
      const match = joinCandidates.all_candidates.find(
        (c) => (c.left_table === leftTable && c.right_table === rightTable) ||
               (c.left_table === rightTable && c.right_table === leftTable)
      );
      if (match) {
        if (match.left_table === leftTable) {
          leftCol = match.left_column;
          rightCol = match.right_column;
        } else {
          leftCol = match.right_column;
          rightCol = match.left_column;
        }
      }
    }
    // Also check top-level suggestion
    if (!leftCol && joinCandidates) {
      if (joinCandidates.left_table === leftTable && joinCandidates.right_table === rightTable) {
        leftCol = joinCandidates.left_column;
        rightCol = joinCandidates.right_column;
      } else if (joinCandidates.left_table === rightTable && joinCandidates.right_table === leftTable) {
        leftCol = joinCandidates.right_column;
        rightCol = joinCandidates.left_column;
      }
    }
    setLinkEditor({ leftTable, rightTable, leftCol, rightCol });
    setValidationResult(null);
    setError(null);
  };

  const handleValidateLink = async () => {
    if (!linkEditor) return;
    setValidating(true);
    setError(null);
    setValidationResult(null);
    try {
      const result = await validateJoin(workspaceId, {
        left_table: linkEditor.leftTable,
        right_table: linkEditor.rightTable,
        left_column: linkEditor.leftCol,
        right_column: linkEditor.rightCol,
      });
      setValidationResult(result);
    } catch (e) {
      setError(e.message);
    }
    setValidating(false);
  };

  const handleConfirmLink = () => {
    if (!linkEditor || !validationResult) return;
    const newLink = {
      left_table: linkEditor.leftTable,
      right_table: linkEditor.rightTable,
      left_column: linkEditor.leftCol,
      right_column: linkEditor.rightCol,
    };
    // Replace existing link between these tables or add new
    setPendingLinks((prev) => {
      const filtered = prev.filter(
        (l) => !(
          (l.left_table === newLink.left_table && l.right_table === newLink.right_table) ||
          (l.left_table === newLink.right_table && l.right_table === newLink.left_table)
        )
      );
      return [...filtered, newLink];
    });
    setLinkEditor(null);
    setValidationResult(null);
  };

  const handleSaveLinks = async () => {
    if (pendingLinks.length === 0) return;
    setSavingLinks(true);
    setError(null);
    try {
      const result = await saveJoinConfig(workspaceId, pendingLinks);
      if (result.data_status) setDataStatus(result.data_status);
      setPendingLinks(result.links || pendingLinks);
    } catch (e) {
      setError(e.message);
      setTimeout(() => setError(null), 5000);
    }
    setSavingLinks(false);
  };

  const removeLink = (index) => {
    setPendingLinks((prev) => prev.filter((_, i) => i !== index));
  };

  const tables = dataStatus?.tables || [];
  const tableCount = tables.length;
  const linksNeeded = Math.max(0, tableCount - 1);
  const canActivate = dataStatus?.can_activate || false;
  const dataActivated = dataStatus?.data_activated || false;

  // Get columns for a table from datasets
  // Table names are lowercased/sanitized versions of dataset names
  const getTableColumns = (tableName) => {
    const normalize = (s) => s.toLowerCase().replace(/[^a-z0-9]/g, "_").replace(/^_+|_+$/g, "");
    const ds = datasets.find((d) =>
      d.table_name === tableName ||
      d.name === tableName ||
      normalize(d.name) === tableName
    );
    if (!ds) return [];
    const cols = typeof ds.columns === "string" ? JSON.parse(ds.columns) : ds.columns;
    return Array.isArray(cols) ? cols : [];
  };

  // Determine which table pairs still need links
  const getUnlinkedPairs = () => {
    if (tableCount < 2) return [];
    const pairs = [];
    for (let i = 0; i < tables.length; i++) {
      for (let j = i + 1; j < tables.length; j++) {
        const hasLink = pendingLinks.some(
          (l) => (l.left_table === tables[i] && l.right_table === tables[j]) ||
                 (l.left_table === tables[j] && l.right_table === tables[i])
        );
        if (!hasLink) pairs.push([tables[i], tables[j]]);
      }
    }
    return pairs;
  };

  const formatSize = (bytes) => {
    if (!bytes) return "";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const unlinkedPairs = getUnlinkedPairs();

  return (
    <div style={{
      display: "flex", flexDirection: "column", alignItems: "center",
      padding: "60px 24px", minHeight: "calc(100vh - 60px)",
    }}>
      <div style={{ maxWidth: 520, width: "100%" }}>
        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: 40 }}>
          <div style={{
            width: 12, height: 12, borderRadius: "50%", background: "#34d399",
            margin: "0 auto 16px", boxShadow: "0 0 20px rgba(52,211,153,0.3)",
            animation: "p 2.5s infinite",
          }} />
          <div style={{
            fontSize: 18, fontWeight: 700, letterSpacing: "0.06em",
            color: "rgba(255,255,255,0.8)", fontFamily: "'JetBrains Mono',monospace",
            marginBottom: 8,
          }}>DATA SETUP</div>
          <div style={{
            fontSize: 12, color: "rgba(255,255,255,0.3)", lineHeight: 1.6,
            fontFamily: "'DM Sans',sans-serif",
          }}>
            Upload your data files, link tables if needed, then activate to start the agent.
          </div>
        </div>

        {/* Error */}
        {error && (
          <div style={{
            padding: "8px 12px", marginBottom: 16, borderRadius: 6,
            background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.2)",
            color: "rgba(239,68,68,0.7)", fontSize: 11, lineHeight: 1.5,
          }}>{error}</div>
        )}

        {/* Step 1: Upload Files */}
        <div style={{
          padding: "16px 18px", borderRadius: 8,
          background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)",
          marginBottom: 16,
        }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{
                width: 20, height: 20, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center",
                background: tableCount > 0 ? "rgba(52,211,153,0.15)" : "rgba(255,255,255,0.06)",
                color: tableCount > 0 ? "rgba(52,211,153,0.8)" : "rgba(255,255,255,0.3)",
                fontSize: 10, fontWeight: 700, fontFamily: "'JetBrains Mono',monospace",
              }}>1</div>
              <span style={{ fontSize: 12, fontWeight: 600, color: "rgba(255,255,255,0.6)" }}>Upload CSV Files</span>
            </div>
            <span style={{ fontSize: 9, color: "rgba(255,255,255,0.2)", fontFamily: "'JetBrains Mono',monospace" }}>
              {tableCount}/{MAX_FILES} files
            </span>
          </div>

          {/* File list */}
          {datasets.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 12 }}>
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
                    <div style={{ fontSize: 11, fontWeight: 600, color: "rgba(255,255,255,0.7)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {ds.name}
                    </div>
                    <div style={{ fontSize: 9, color: "rgba(255,255,255,0.25)", fontFamily: "'JetBrains Mono',monospace", marginTop: 2 }}>
                      {ds.row_count?.toLocaleString()} rows
                      {" · "}
                      {(typeof ds.columns === "string" ? JSON.parse(ds.columns).length : Array.isArray(ds.columns) ? ds.columns.length : ds.columns)} cols
                      {ds.file_size ? ` · ${formatSize(ds.file_size)}` : ""}
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

          {/* Upload button */}
          {tableCount < MAX_FILES && (
            <label style={{
              display: "inline-flex", alignItems: "center", gap: 6, padding: "6px 14px", borderRadius: 5,
              background: "rgba(52,211,153,0.08)", border: "1px solid rgba(52,211,153,0.2)",
              color: "rgba(52,211,153,0.7)", fontSize: 10, fontWeight: 600,
              cursor: uploading ? "wait" : "pointer",
            }}>
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" />
              </svg>
              {uploading ? "Uploading..." : "Upload CSV"}
              <input ref={fileRef} type="file" accept=".csv" onChange={handleUpload} disabled={uploading} style={{ display: "none" }} />
            </label>
          )}
          {tableCount >= MAX_FILES && (
            <div style={{ fontSize: 10, color: "rgba(251,191,36,0.6)", fontFamily: "'DM Sans',sans-serif" }}>
              Maximum {MAX_FILES} files reached. Delete a file to upload another.
            </div>
          )}
        </div>

        {/* Step 2: Link Tables (only if 2+ tables) */}
        {tableCount >= 2 && (
          <div style={{
            padding: "16px 18px", borderRadius: 8,
            background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)",
            marginBottom: 16,
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
              <div style={{
                width: 20, height: 20, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center",
                background: canActivate ? "rgba(52,211,153,0.15)" : "rgba(129,140,248,0.15)",
                color: canActivate ? "rgba(52,211,153,0.8)" : "rgba(129,140,248,0.8)",
                fontSize: 10, fontWeight: 700, fontFamily: "'JetBrains Mono',monospace",
              }}>2</div>
              <span style={{ fontSize: 12, fontWeight: 600, color: "rgba(255,255,255,0.6)" }}>Link Tables</span>
              <span style={{ fontSize: 9, color: "rgba(255,255,255,0.2)", fontFamily: "'JetBrains Mono',monospace", marginLeft: "auto" }}>
                {pendingLinks.length}/{linksNeeded} links
              </span>
            </div>

            <div style={{ fontSize: 10, color: "rgba(255,255,255,0.3)", marginBottom: 12, lineHeight: 1.6 }}>
              Connect your tables by specifying join columns. All tables must be linked before activation.
            </div>

            {/* Confirmed links */}
            {pendingLinks.length > 0 && (
              <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 12 }}>
                {pendingLinks.map((link, i) => (
                  <div key={i} style={{
                    display: "flex", alignItems: "center", gap: 8, padding: "8px 10px",
                    background: "rgba(52,211,153,0.04)", border: "1px solid rgba(52,211,153,0.12)",
                    borderRadius: 6,
                  }}>
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="rgba(52,211,153,0.6)" strokeWidth="2" strokeLinecap="round">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                    <div style={{ flex: 1, fontSize: 10, color: "rgba(255,255,255,0.5)" }}>
                      <strong style={{ color: "rgba(255,255,255,0.7)" }}>{link.left_table}</strong>
                      <code style={{ background: "rgba(255,255,255,0.06)", padding: "1px 4px", borderRadius: 3, fontSize: 9, margin: "0 4px" }}>
                        {link.left_column}
                      </code>
                      =
                      <strong style={{ color: "rgba(255,255,255,0.7)", marginLeft: 4 }}>{link.right_table}</strong>
                      <code style={{ background: "rgba(255,255,255,0.06)", padding: "1px 4px", borderRadius: 3, fontSize: 9, margin: "0 4px" }}>
                        {link.right_column}
                      </code>
                    </div>
                    <button onClick={() => removeLink(i)} style={{
                      background: "none", border: "none", color: "rgba(255,255,255,0.15)",
                      cursor: "pointer", padding: 2, transition: "color 0.15s",
                    }}
                      onMouseEnter={(e) => { e.currentTarget.style.color = "rgba(239,68,68,0.5)"; }}
                      onMouseLeave={(e) => { e.currentTarget.style.color = "rgba(255,255,255,0.15)"; }}
                    >
                      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                        <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Unlinked pairs — click to start linking */}
            {unlinkedPairs.length > 0 && !linkEditor && (
              <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 12 }}>
                {unlinkedPairs.map(([t1, t2], i) => (
                  <button key={i} onClick={() => startLink(t1, t2)} style={{
                    display: "flex", alignItems: "center", gap: 8, padding: "8px 10px",
                    background: "rgba(129,140,248,0.04)", border: "1px dashed rgba(129,140,248,0.2)",
                    borderRadius: 6, cursor: "pointer", transition: "all 0.15s", width: "100%",
                    textAlign: "left",
                  }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(129,140,248,0.08)"; e.currentTarget.style.borderColor = "rgba(129,140,248,0.3)"; }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = "rgba(129,140,248,0.04)"; e.currentTarget.style.borderColor = "rgba(129,140,248,0.2)"; }}
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="rgba(129,140,248,0.5)" strokeWidth="2" strokeLinecap="round">
                      <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
                    </svg>
                    <span style={{ fontSize: 10, color: "rgba(129,140,248,0.6)" }}>
                      Link <strong style={{ color: "rgba(129,140,248,0.8)" }}>{t1}</strong> and <strong style={{ color: "rgba(129,140,248,0.8)" }}>{t2}</strong>
                    </span>
                  </button>
                ))}
              </div>
            )}

            {/* Link editor — configure join columns */}
            {linkEditor && (
              <div style={{
                padding: "12px 14px", borderRadius: 7, marginBottom: 12,
                background: "rgba(129,140,248,0.04)", border: "1px solid rgba(129,140,248,0.15)",
              }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
                  <span style={{ fontSize: 10, fontWeight: 600, color: "rgba(129,140,248,0.7)" }}>
                    {linkEditor.leftTable} &rarr; {linkEditor.rightTable}
                  </span>
                  <button onClick={() => { setLinkEditor(null); setValidationResult(null); }} style={{
                    background: "none", border: "none", color: "rgba(255,255,255,0.2)", cursor: "pointer", padding: 2, fontSize: 14, lineHeight: 1,
                  }}>&times;</button>
                </div>

                <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 9, color: "rgba(255,255,255,0.25)", marginBottom: 4 }}>{linkEditor.leftTable} column</div>
                    <select
                      value={linkEditor.leftCol}
                      onChange={(e) => setLinkEditor((p) => ({ ...p, leftCol: e.target.value }))}
                      style={{
                        width: "100%", padding: "6px 8px", borderRadius: 5, fontSize: 10,
                        background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.1)",
                        color: "rgba(255,255,255,0.6)", fontFamily: "'DM Sans',sans-serif", outline: "none",
                      }}
                    >
                      <option value="">Select column...</option>
                      {getTableColumns(linkEditor.leftTable).map((col) => (
                        <option key={col} value={col}>{col}</option>
                      ))}
                    </select>
                  </div>
                  <div style={{ display: "flex", alignItems: "flex-end", paddingBottom: 6, color: "rgba(255,255,255,0.2)", fontSize: 11 }}>=</div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 9, color: "rgba(255,255,255,0.25)", marginBottom: 4 }}>{linkEditor.rightTable} column</div>
                    <select
                      value={linkEditor.rightCol}
                      onChange={(e) => setLinkEditor((p) => ({ ...p, rightCol: e.target.value }))}
                      style={{
                        width: "100%", padding: "6px 8px", borderRadius: 5, fontSize: 10,
                        background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.1)",
                        color: "rgba(255,255,255,0.6)", fontFamily: "'DM Sans',sans-serif", outline: "none",
                      }}
                    >
                      <option value="">Select column...</option>
                      {getTableColumns(linkEditor.rightTable).map((col) => (
                        <option key={col} value={col}>{col}</option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Validation result */}
                {validationResult && (
                  <div style={{
                    padding: "8px 10px", marginBottom: 8, borderRadius: 5,
                    background: validationResult.valid ? "rgba(52,211,153,0.06)" : "rgba(251,191,36,0.06)",
                    border: `1px solid ${validationResult.valid ? "rgba(52,211,153,0.15)" : "rgba(251,191,36,0.15)"}`,
                    fontSize: 9, color: "rgba(255,255,255,0.5)", lineHeight: 1.6,
                  }}>
                    <div style={{ fontWeight: 600, color: validationResult.valid ? "rgba(52,211,153,0.8)" : "rgba(251,191,36,0.8)", marginBottom: 4 }}>
                      {validationResult.valid ? "Join looks good" : "Review recommended"}
                    </div>
                    {validationResult.matched_rows != null && <div>Matched: {validationResult.matched_rows.toLocaleString()} rows</div>}
                    {validationResult.left_orphans > 0 && (
                      <div style={{ color: "rgba(251,191,36,0.7)" }}>Unmatched in {linkEditor.leftTable}: {validationResult.left_orphans.toLocaleString()}</div>
                    )}
                    {validationResult.right_orphans > 0 && (
                      <div style={{ color: "rgba(251,191,36,0.7)" }}>Unmatched in {linkEditor.rightTable}: {validationResult.right_orphans.toLocaleString()}</div>
                    )}
                  </div>
                )}

                <div style={{ display: "flex", gap: 6 }}>
                  {!validationResult && (
                    <button onClick={handleValidateLink} disabled={validating || !linkEditor.leftCol || !linkEditor.rightCol} style={{
                      flex: 1, padding: "6px 0", borderRadius: 5, fontSize: 9, fontWeight: 600,
                      background: "rgba(129,140,248,0.08)", border: "1px solid rgba(129,140,248,0.2)",
                      color: (!linkEditor.leftCol || !linkEditor.rightCol) ? "rgba(129,140,248,0.3)" : "rgba(129,140,248,0.7)",
                      cursor: (validating || !linkEditor.leftCol || !linkEditor.rightCol) ? "default" : "pointer",
                      transition: "all 0.15s",
                    }}>{validating ? "Testing..." : "Test Join"}</button>
                  )}
                  {validationResult?.valid && (
                    <button onClick={handleConfirmLink} style={{
                      flex: 1, padding: "6px 0", borderRadius: 5, fontSize: 9, fontWeight: 600,
                      background: "rgba(52,211,153,0.08)", border: "1px solid rgba(52,211,153,0.2)",
                      color: "rgba(52,211,153,0.7)", cursor: "pointer", transition: "all 0.15s",
                    }}>Confirm Link</button>
                  )}
                  {validationResult && !validationResult.valid && (
                    <>
                      <button onClick={handleValidateLink} disabled={validating} style={{
                        flex: 1, padding: "6px 0", borderRadius: 5, fontSize: 9, fontWeight: 600,
                        background: "rgba(251,191,36,0.08)", border: "1px solid rgba(251,191,36,0.2)",
                        color: "rgba(251,191,36,0.7)", cursor: validating ? "wait" : "pointer",
                        transition: "all 0.15s",
                      }}>{validating ? "Testing..." : "Re-test"}</button>
                      <button onClick={handleConfirmLink} style={{
                        padding: "6px 10px", borderRadius: 5, fontSize: 9, fontWeight: 600,
                        background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)",
                        color: "rgba(255,255,255,0.35)", cursor: "pointer", transition: "all 0.15s",
                      }}>Confirm Anyway</button>
                    </>
                  )}
                </div>
              </div>
            )}

            {/* Save links button */}
            {pendingLinks.length > 0 && pendingLinks.length >= linksNeeded && (
              <button onClick={handleSaveLinks} disabled={savingLinks} style={{
                width: "100%", padding: "8px 0", borderRadius: 6, fontSize: 10, fontWeight: 600,
                background: savingLinks ? "rgba(129,140,248,0.04)" : "rgba(129,140,248,0.08)",
                border: "1px solid rgba(129,140,248,0.2)",
                color: "rgba(129,140,248,0.7)", cursor: savingLinks ? "wait" : "pointer",
                transition: "all 0.15s",
              }}>{savingLinks ? "Saving links..." : "Save All Links"}</button>
            )}
          </div>
        )}

        {/* Step 3: Activate */}
        <div style={{
          padding: "16px 18px", borderRadius: 8,
          background: canActivate && !dataActivated ? "rgba(52,211,153,0.03)" : "rgba(255,255,255,0.02)",
          border: `1px solid ${canActivate && !dataActivated ? "rgba(52,211,153,0.1)" : "rgba(255,255,255,0.05)"}`,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
            <div style={{
              width: 20, height: 20, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center",
              background: dataActivated ? "rgba(52,211,153,0.15)" : "rgba(255,255,255,0.06)",
              color: dataActivated ? "rgba(52,211,153,0.8)" : "rgba(255,255,255,0.3)",
              fontSize: 10, fontWeight: 700, fontFamily: "'JetBrains Mono',monospace",
            }}>{tableCount >= 2 ? "3" : "2"}</div>
            <span style={{ fontSize: 12, fontWeight: 600, color: "rgba(255,255,255,0.6)" }}>Activate</span>
          </div>

          {!canActivate && tableCount === 0 && (
            <div style={{ fontSize: 10, color: "rgba(255,255,255,0.25)", marginBottom: 12, lineHeight: 1.6 }}>
              Upload at least one CSV file to get started.
            </div>
          )}
          {!canActivate && tableCount >= 2 && (
            <div style={{ fontSize: 10, color: "rgba(255,255,255,0.25)", marginBottom: 12, lineHeight: 1.6 }}>
              Link all tables before activating. {dataStatus?.links_needed || 0} more link(s) needed.
            </div>
          )}
          {canActivate && !dataActivated && (
            <div style={{ fontSize: 10, color: "rgba(255,255,255,0.25)", marginBottom: 12, lineHeight: 1.6 }}>
              Your data is ready. Activate to start the SENTINEL agent.
            </div>
          )}

          <button
            onClick={handleActivate}
            disabled={!canActivate || dataActivated || activating}
            style={{
              width: "100%", padding: "10px 0", borderRadius: 6, fontSize: 11, fontWeight: 700,
              letterSpacing: "0.04em", fontFamily: "'JetBrains Mono',monospace",
              background: canActivate && !dataActivated
                ? (activating ? "rgba(52,211,153,0.08)" : "rgba(52,211,153,0.12)")
                : "rgba(255,255,255,0.03)",
              border: `1px solid ${canActivate && !dataActivated ? "rgba(52,211,153,0.3)" : "rgba(255,255,255,0.06)"}`,
              color: canActivate && !dataActivated
                ? (activating ? "rgba(52,211,153,0.5)" : "rgba(52,211,153,0.9)")
                : "rgba(255,255,255,0.15)",
              cursor: canActivate && !dataActivated && !activating ? "pointer" : "default",
              transition: "all 0.2s",
            }}
          >
            {activating ? "Activating..." : dataActivated ? "Activated" : "Activate Workspace"}
          </button>
        </div>
      </div>
    </div>
  );
}
