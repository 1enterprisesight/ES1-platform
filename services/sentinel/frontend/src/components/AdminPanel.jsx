import { useState, useEffect } from "react";
import { fetchUsers, updateUserStatus, updateUserRole, deleteUser } from "../api.js";

const STATUS_COLORS = {
  active: { color: "#34d399", bg: "rgba(52,211,153,0.08)", border: "rgba(52,211,153,0.2)" },
  verified: { color: "#60a5fa", bg: "rgba(96,165,250,0.08)", border: "rgba(96,165,250,0.2)" },
  pending: { color: "#fbbf24", bg: "rgba(251,191,36,0.08)", border: "rgba(251,191,36,0.2)" },
  disabled: { color: "#ef4444", bg: "rgba(239,68,68,0.08)", border: "rgba(239,68,68,0.2)" },
};

const ROLE_COLORS = {
  admin: { color: "#c084fc", bg: "rgba(192,132,252,0.08)", border: "rgba(192,132,252,0.2)" },
  user: { color: "rgba(255,255,255,0.4)", bg: "rgba(255,255,255,0.03)", border: "rgba(255,255,255,0.08)" },
};

export default function AdminPanel({ onClose }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchUsers();
      setUsers(data.users || []);
    } catch (e) {
      setError(e.message);
    }
    setLoading(false);
  };

  const handleStatusChange = async (userId, newStatus) => {
    setActionLoading(userId);
    try {
      const data = await updateUserStatus(userId, newStatus);
      setUsers((prev) => prev.map((u) => (u.id === userId ? data.user : u)));
    } catch (e) {
      setError(e.message);
    }
    setActionLoading(null);
  };

  const handleRoleChange = async (userId, newRole) => {
    setActionLoading(userId);
    try {
      const data = await updateUserRole(userId, newRole);
      setUsers((prev) => prev.map((u) => (u.id === userId ? data.user : u)));
    } catch (e) {
      setError(e.message);
    }
    setActionLoading(null);
  };

  const handleDelete = async (userId) => {
    setActionLoading(userId);
    try {
      await deleteUser(userId);
      setUsers((prev) => prev.filter((u) => u.id !== userId));
      setConfirmDelete(null);
    } catch (e) {
      setError(e.message);
    }
    setActionLoading(null);
  };

  const statusOptions = ["active", "verified", "pending", "disabled"];
  const roleOptions = ["user", "admin"];

  return (
    <div onClick={onClose} style={{
      position: "fixed", inset: 0, zIndex: 200,
      background: "rgba(0,0,0,0.7)", backdropFilter: "blur(6px)",
      display: "flex", alignItems: "center", justifyContent: "center",
      fontFamily: "'DM Sans',sans-serif",
    }}>
      <div onClick={(e) => e.stopPropagation()} style={{
        background: "#0f1117", border: "1px solid rgba(255,255,255,0.1)",
        borderRadius: 12, width: 640, maxWidth: "90vw", maxHeight: "80vh",
        display: "flex", flexDirection: "column",
        boxShadow: "0 16px 64px rgba(0,0,0,0.8)",
      }}>
        {/* Header */}
        <div style={{
          padding: "16px 20px", borderBottom: "1px solid rgba(255,255,255,0.06)",
          display: "flex", alignItems: "center", justifyContent: "space-between",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="rgba(192,132,252,0.6)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
              <path d="M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
            <span style={{
              fontSize: 11, fontWeight: 700, letterSpacing: "0.06em",
              color: "rgba(255,255,255,0.6)", fontFamily: "'JetBrains Mono',monospace",
              textTransform: "uppercase",
            }}>User Management</span>
            <span style={{
              fontSize: 10, color: "rgba(255,255,255,0.2)", marginLeft: 4,
            }}>{users.length} user{users.length !== 1 ? "s" : ""}</span>
          </div>
          <button onClick={onClose} style={{
            background: "none", border: "none", color: "rgba(255,255,255,0.3)",
            fontSize: 18, cursor: "pointer", padding: "0 4px", lineHeight: 1,
          }}>&times;</button>
        </div>

        {/* Error */}
        {error && (
          <div style={{
            margin: "12px 20px 0", padding: "8px 12px", borderRadius: 6,
            background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.2)",
            color: "rgba(239,68,68,0.8)", fontSize: 11,
            display: "flex", justifyContent: "space-between", alignItems: "center",
          }}>
            {error}
            <button onClick={() => setError(null)} style={{
              background: "none", border: "none", color: "rgba(239,68,68,0.5)",
              cursor: "pointer", fontSize: 14, padding: 0,
            }}>&times;</button>
          </div>
        )}

        {/* User list */}
        <div style={{ flex: 1, overflow: "auto", padding: "12px 20px 20px" }}>
          {loading ? (
            <div style={{ textAlign: "center", padding: 40, color: "rgba(255,255,255,0.2)", fontSize: 12 }}>
              Loading users...
            </div>
          ) : users.length === 0 ? (
            <div style={{ textAlign: "center", padding: 40, color: "rgba(255,255,255,0.2)", fontSize: 12 }}>
              No users found
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {users.map((u) => {
                const sc = STATUS_COLORS[u.status] || STATUS_COLORS.pending;
                const rc = ROLE_COLORS[u.role] || ROLE_COLORS.user;
                const isLoading = actionLoading === u.id;
                return (
                  <div key={u.id} style={{
                    padding: "12px 14px", borderRadius: 8,
                    background: "rgba(255,255,255,0.02)",
                    border: "1px solid rgba(255,255,255,0.04)",
                    opacity: isLoading ? 0.5 : 1, transition: "opacity 0.15s",
                  }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
                        <span style={{
                          fontSize: 12, fontWeight: 600, color: "rgba(255,255,255,0.7)",
                          overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                        }}>
                          {u.display_name || u.email.split("@")[0]}
                        </span>
                        <span style={{
                          fontSize: 10, color: "rgba(255,255,255,0.25)",
                          overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                        }}>{u.email}</span>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 6, flexShrink: 0 }}>
                        {/* Status badge */}
                        <span style={{
                          fontSize: 9, fontWeight: 600, padding: "2px 8px", borderRadius: 4,
                          background: sc.bg, border: `1px solid ${sc.border}`, color: sc.color,
                          textTransform: "uppercase", letterSpacing: "0.04em",
                        }}>{u.status}</span>
                        {/* Role badge */}
                        <span style={{
                          fontSize: 9, fontWeight: 600, padding: "2px 8px", borderRadius: 4,
                          background: rc.bg, border: `1px solid ${rc.border}`, color: rc.color,
                          textTransform: "uppercase", letterSpacing: "0.04em",
                        }}>{u.role}</span>
                      </div>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                      {/* Status actions */}
                      {statusOptions.filter((s) => s !== u.status).map((s) => (
                        <button key={s} disabled={isLoading} onClick={() => handleStatusChange(u.id, s)} style={{
                          padding: "3px 8px", borderRadius: 4, fontSize: 9, fontWeight: 500,
                          background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)",
                          color: STATUS_COLORS[s]?.color || "rgba(255,255,255,0.4)",
                          cursor: isLoading ? "wait" : "pointer", fontFamily: "'DM Sans',sans-serif",
                          transition: "all 0.15s",
                        }}
                          onMouseEnter={(e) => { e.currentTarget.style.borderColor = STATUS_COLORS[s]?.border || "rgba(255,255,255,0.15)"; }}
                          onMouseLeave={(e) => { e.currentTarget.style.borderColor = "rgba(255,255,255,0.06)"; }}
                        >
                          {s === "active" ? "Approve" : s === "disabled" ? "Disable" : s.charAt(0).toUpperCase() + s.slice(1)}
                        </button>
                      ))}
                      {/* Role toggle */}
                      {roleOptions.filter((r) => r !== u.role).map((r) => (
                        <button key={r} disabled={isLoading} onClick={() => handleRoleChange(u.id, r)} style={{
                          padding: "3px 8px", borderRadius: 4, fontSize: 9, fontWeight: 500,
                          background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)",
                          color: ROLE_COLORS[r]?.color || "rgba(255,255,255,0.4)",
                          cursor: isLoading ? "wait" : "pointer", fontFamily: "'DM Sans',sans-serif",
                          transition: "all 0.15s",
                        }}
                          onMouseEnter={(e) => { e.currentTarget.style.borderColor = ROLE_COLORS[r]?.border || "rgba(255,255,255,0.15)"; }}
                          onMouseLeave={(e) => { e.currentTarget.style.borderColor = "rgba(255,255,255,0.06)"; }}
                        >
                          Make {r}
                        </button>
                      ))}
                      {/* Delete */}
                      <div style={{ marginLeft: "auto" }}>
                        {confirmDelete === u.id ? (
                          <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
                            <span style={{ fontSize: 9, color: "rgba(239,68,68,0.6)", marginRight: 4 }}>Delete?</span>
                            <button disabled={isLoading} onClick={() => handleDelete(u.id)} style={{
                              padding: "3px 8px", borderRadius: 4, fontSize: 9, fontWeight: 600,
                              background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)",
                              color: "rgba(239,68,68,0.8)", cursor: isLoading ? "wait" : "pointer",
                              fontFamily: "'DM Sans',sans-serif",
                            }}>Yes</button>
                            <button onClick={() => setConfirmDelete(null)} style={{
                              padding: "3px 8px", borderRadius: 4, fontSize: 9, fontWeight: 500,
                              background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)",
                              color: "rgba(255,255,255,0.3)", cursor: "pointer",
                              fontFamily: "'DM Sans',sans-serif",
                            }}>No</button>
                          </div>
                        ) : (
                          <button onClick={() => setConfirmDelete(u.id)} disabled={isLoading} style={{
                            padding: "3px 8px", borderRadius: 4, fontSize: 9, fontWeight: 500,
                            background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.04)",
                            color: "rgba(255,255,255,0.15)", cursor: isLoading ? "wait" : "pointer",
                            fontFamily: "'DM Sans',sans-serif", transition: "all 0.15s",
                          }}
                            onMouseEnter={(e) => { e.currentTarget.style.color = "rgba(239,68,68,0.6)"; e.currentTarget.style.borderColor = "rgba(239,68,68,0.2)"; }}
                            onMouseLeave={(e) => { e.currentTarget.style.color = "rgba(255,255,255,0.15)"; e.currentTarget.style.borderColor = "rgba(255,255,255,0.04)"; }}
                          >Delete</button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
