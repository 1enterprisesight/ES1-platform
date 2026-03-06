import { useState, useEffect, useRef } from "react";
import { fetchWorkspaces, createWorkspace, deleteWorkspace, activateWorkspace } from "../api.js";

export default function WorkspaceSwitcher({ activeWorkspace, onSwitch }) {
  const [open, setOpen] = useState(false);
  const [workspaces, setWorkspaces] = useState([]);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const inputRef = useRef(null);

  useEffect(() => {
    if (open) {
      fetchWorkspaces()
        .then((d) => setWorkspaces(d.workspaces || []))
        .catch((e) => console.error("Failed to fetch workspaces:", e));
    }
  }, [open]);

  useEffect(() => {
    if (creating && inputRef.current) inputRef.current.focus();
  }, [creating]);

  const handleCreate = async () => {
    const name = newName.trim();
    if (!name) return;
    try {
      const ws = await createWorkspace(name);
      setWorkspaces((prev) => [ws, ...prev]);
      setNewName("");
      setCreating(false);
    } catch (e) {
      console.error("Failed to create workspace:", e);
    }
  };

  const handleDelete = async (id) => {
    try {
      await deleteWorkspace(id);
      setWorkspaces((prev) => prev.filter((w) => w.id !== id));
    } catch (e) {
      console.error("Failed to delete workspace:", e);
    }
  };

  const handleSwitch = async (ws) => {
    if (ws.id === activeWorkspace?.id) { setOpen(false); return; }
    try {
      const data = await activateWorkspace(ws.id);
      setOpen(false);
      if (onSwitch) onSwitch(data);
    } catch (e) {
      console.error("Failed to switch workspace:", e);
    }
  };

  const label = activeWorkspace?.name || "Workspace";

  return (
    <div style={{ position: "relative", flexShrink: 0 }}>
      <button
        onClick={(e) => { e.stopPropagation(); setOpen((p) => !p); }}
        style={{
          display: "flex", alignItems: "center", gap: 5, padding: "4px 10px", borderRadius: 5,
          border: `1px solid ${open ? "rgba(129,140,248,0.3)" : "rgba(255,255,255,0.06)"}`,
          background: open ? "rgba(129,140,248,0.06)" : "rgba(255,255,255,0.02)",
          color: open ? "rgba(129,140,248,0.8)" : "rgba(255,255,255,0.35)",
          fontSize: 10, fontWeight: 600, cursor: "pointer", transition: "all .15s",
          fontFamily: "'JetBrains Mono',monospace", maxWidth: 140, overflow: "hidden",
        }}
        onMouseEnter={(e) => { if (!open) { e.currentTarget.style.borderColor = "rgba(255,255,255,0.15)"; e.currentTarget.style.color = "rgba(255,255,255,0.5)"; }}}
        onMouseLeave={(e) => { if (!open) { e.currentTarget.style.borderColor = "rgba(255,255,255,0.06)"; e.currentTarget.style.color = "rgba(255,255,255,0.35)"; }}}
      >
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="2" y="3" width="20" height="14" rx="2" ry="2" /><line x1="8" y1="21" x2="16" y2="21" /><line x1="12" y1="17" x2="12" y2="21" />
        </svg>
        <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{label}</span>
        <svg width="8" height="8" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" style={{ transform: open ? "rotate(180deg)" : "rotate(0)", transition: "transform 0.15s", flexShrink: 0 }}>
          <path d="M3 4.5L6 7.5L9 4.5" />
        </svg>
      </button>

      {open && (
        <div onClick={(e) => e.stopPropagation()} style={{
          position: "absolute", top: "100%", left: 0, marginTop: 6, zIndex: 100,
          background: "#0f1117", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8,
          padding: "14px 16px", minWidth: 240, boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
        }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
            <div style={{ fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "rgba(255,255,255,0.3)", fontFamily: "'JetBrains Mono',monospace" }}>
              Workspaces
            </div>
            <button onClick={() => setCreating(true)} style={{
              display: "flex", alignItems: "center", gap: 3, padding: "3px 8px", borderRadius: 4,
              background: "rgba(129,140,248,0.08)", border: "1px solid rgba(129,140,248,0.2)",
              color: "rgba(129,140,248,0.7)", fontSize: 9, fontWeight: 600,
              cursor: "pointer", fontFamily: "'DM Sans',sans-serif",
            }}>+ New</button>
          </div>

          {creating && (
            <div style={{ display: "flex", gap: 6, marginBottom: 10 }}>
              <input
                ref={inputRef}
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") handleCreate(); if (e.key === "Escape") setCreating(false); }}
                placeholder="Workspace name"
                style={{
                  flex: 1, padding: "5px 8px", borderRadius: 5, fontSize: 11,
                  background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.1)",
                  color: "rgba(255,255,255,0.7)", fontFamily: "'DM Sans',sans-serif", outline: "none",
                }}
              />
              <button onClick={handleCreate} style={{
                padding: "5px 10px", borderRadius: 5, fontSize: 10, fontWeight: 600,
                background: "rgba(129,140,248,0.1)", border: "1px solid rgba(129,140,248,0.25)",
                color: "rgba(129,140,248,0.7)", cursor: "pointer", fontFamily: "'DM Sans',sans-serif",
              }}>Add</button>
            </div>
          )}

          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {workspaces.map((ws) => {
              const isActive = ws.id === activeWorkspace?.id;
              return (
                <div key={ws.id} onClick={() => handleSwitch(ws)} style={{
                  display: "flex", alignItems: "center", gap: 8, padding: "7px 10px",
                  background: isActive ? "rgba(129,140,248,0.08)" : "rgba(255,255,255,0.02)",
                  border: `1px solid ${isActive ? "rgba(129,140,248,0.2)" : "rgba(255,255,255,0.04)"}`,
                  borderRadius: 6, cursor: "pointer", transition: "all 0.15s",
                }}
                  onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.background = "rgba(255,255,255,0.04)"; }}
                  onMouseLeave={(e) => { if (!isActive) e.currentTarget.style.background = "rgba(255,255,255,0.02)"; }}
                >
                  <div style={{
                    width: 6, height: 6, borderRadius: "50%", flexShrink: 0,
                    background: isActive ? "#818cf8" : "rgba(255,255,255,0.1)",
                    boxShadow: isActive ? "0 0 6px rgba(129,140,248,0.4)" : "none",
                  }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontSize: 11, fontWeight: isActive ? 600 : 500,
                      color: isActive ? "rgba(129,140,248,0.9)" : "rgba(255,255,255,0.6)",
                      fontFamily: "'DM Sans',sans-serif",
                      overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                    }}>{ws.name}</div>
                  </div>
                  {!isActive && workspaces.length > 1 && (
                    <button onClick={(e) => { e.stopPropagation(); handleDelete(ws.id); }} style={{
                      background: "none", border: "none", color: "rgba(255,255,255,0.1)",
                      cursor: "pointer", padding: 2, flexShrink: 0, transition: "color 0.15s",
                    }}
                      onMouseEnter={(e) => { e.currentTarget.style.color = "rgba(239,68,68,0.5)"; }}
                      onMouseLeave={(e) => { e.currentTarget.style.color = "rgba(255,255,255,0.1)"; }}
                    >
                      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                        <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                      </svg>
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
