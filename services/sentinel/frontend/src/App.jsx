import { useState, useEffect, useRef, useCallback, Component } from "react";
import useSSE from "./hooks/useSSE.js";
import { fetchSilos, moveTile, fetchInteractions, askQuestion, fetchSiloHints, rediscoverSilos, fetchRowConfig, saveRowConfig, fetchMe, logout, getDataStatus, activateWorkspace } from "./api.js";
import LoginPage from "./pages/LoginPage.jsx";

function formatAge(createdAt) {
  if (!createdAt) return "just now";
  const seconds = Math.floor(Date.now() / 1000 - createdAt);
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}
import ScrollRow from "./components/ScrollRow.jsx";
import FeedCard from "./components/FeedCard.jsx";
import FeedLiveCard from "./components/FeedLiveCard.jsx";
import ExpandedCard from "./components/ExpandedCard.jsx";
import DataManager from "./components/DataManager.jsx";
import WorkspaceSwitcher from "./components/WorkspaceSwitcher.jsx";
import AdminPanel from "./components/AdminPanel.jsx";

const MAX_CARDS = 200;

const SAVED_ROW = { id: "resolved", label: "Saved Interactions", icon: "✓", bright: false };

const DEFAULT_ROWS = [
  { id: "row1", label: "Needs Attention", icon: "▲", bright: true, description: "Anomalies, outliers, significant deviations from expected patterns, urgent issues requiring action" },
  { id: "row2", label: "Monitoring", icon: "●", bright: false, description: "Emerging trends, recurring patterns, metrics to watch, gradual shifts worth tracking" },
];

const DEFAULT_ALPHA = {
  id: "alpha", label: "Cross-Theme", color: "#ffffff",
  bg: "rgba(255,255,255,0.08)", border: "rgba(255,255,255,0.45)",
};

const USER_QUESTION_SILO = {
  id: "user_question", label: "Your Question", color: "#34d399",
  bg: "rgba(52,211,153,0.08)", border: "rgba(52,211,153,0.25)",
};


class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError() {
    return { hasError: true };
  }
  componentDidCatch(error, info) {
    console.error("ErrorBoundary caught:", error, info);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ minHeight: "100vh", background: "#07080b", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div style={{ textAlign: "center", color: "rgba(255,255,255,0.5)", fontFamily: "'DM Sans',sans-serif" }}>
            <div style={{ fontSize: 18, fontWeight: 600, marginBottom: 12 }}>Something went wrong</div>
            <button onClick={() => window.location.reload()} style={{
              padding: "8px 20px", borderRadius: 6, border: "1px solid rgba(52,211,153,0.3)",
              background: "rgba(52,211,153,0.08)", color: "rgba(52,211,153,0.8)",
              fontSize: 13, cursor: "pointer", fontFamily: "'DM Sans',sans-serif",
            }}>Reload</button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}


function SentinelApp({ user, onLogout, workspace, onWorkspaceSwitch, initialDataStatus, initialSilos, initialTiles }) {
  const [silos, setSilos] = useState(initialSilos?.length > 0 ? initialSilos : [DEFAULT_ALPHA]);
  const [activeSilos, setActiveSilos] = useState(new Set(initialSilos?.length > 0 ? initialSilos.map(s => s.id) : ["alpha"]));
  const [cards, setCards] = useState(initialTiles?.length > 0 ? initialTiles.slice(0, MAX_CARDS).map(t => ({ ...t, age: formatAge(t.created_at) })) : []);
  const [sel, setSel] = useState(null);
  const [on, setOn] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [typingColor, setTypingColor] = useState("#34d399");
  const [liveCard, setLiveCard] = useState(null);
  const [liveRow, setLiveRow] = useState(null);
  const [chatOpen, setChatOpen] = useState(false);
  const [viewMode, setViewMode] = useState("compact");
  const [interactions, setInteractions] = useState({});
  const [dataActivated, setDataActivated] = useState(initialDataStatus?.data_activated ?? true);
  const [dataStatus, setDataStatus] = useState(initialDataStatus || null);

  const [adminOpen, setAdminOpen] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const [chatAsking, setChatAsking] = useState(false);
  const [hintsOpen, setHintsOpen] = useState(false);
  const [hintsInput, setHintsInput] = useState("");
  const [hintsLoading, setHintsLoading] = useState(false);
  const [dynamicRows, setDynamicRows] = useState(DEFAULT_ROWS);
  const [rowEditorOpen, setRowEditorOpen] = useState(false);
  const [rowEditing, setRowEditing] = useState(null); // {index, label, description}
  const [rowSaving, setRowSaving] = useState(false);
  const compact = viewMode === "compact";
  const ROWS = [...dynamicRows, SAVED_ROW];
  const chatInputRef = useRef(null);
  const liveSettleTimer = useRef(null);
  const liveCardRef = useRef(null);

  // Keep liveCardRef in sync
  liveCardRef.current = liveCard;

  // Fetch silos and interactions on mount
  useEffect(() => {
    setOn(true);
    fetchSilos()
      .then((data) => {
        if (data.length > 0) {
          setSilos(data);
          setActiveSilos(new Set(data.map((s) => s.id)));
        }
      })
      .catch((e) => console.error("Failed to fetch silos:", e));
    fetchInteractions()
      .then((data) => setInteractions(data || {}))
      .catch((e) => console.error("Failed to fetch interactions:", e));
    fetchSiloHints()
      .then((data) => { if (data.hints?.length > 0) setHintsInput(data.hints.join(", ")); })
      .catch(() => {});
    fetchRowConfig()
      .then((data) => { if (data.rows?.length === 2) setDynamicRows(data.rows); })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (chatOpen && chatInputRef.current) setTimeout(() => chatInputRef.current?.focus(), 350);
  }, [chatOpen]);

  const getSilo = useCallback(
    (id) => {
      if (id === "user_question") return USER_QUESTION_SILO;
      return silos.find((s) => s.id === id) || DEFAULT_ALPHA;
    },
    [silos]
  );

  // Use ref for silos so SSE handlers always see latest
  const silosRef = useRef(silos);
  silosRef.current = silos;

  // SSE handlers — stable references (no deps that change)
  const handleInitialTiles = useCallback((tiles) => {
    if (tiles.length > 0) setCards(tiles.slice(0, MAX_CARDS).map(t => ({ ...t, age: formatAge(t.created_at) })));
    setLiveCard(null);
    setLiveRow(null);
    setIsTyping(false);
  }, []);

  const handleNewTile = useCallback((tile) => {
    const silo = silosRef.current.find((s) => s.id === tile.silo) || DEFAULT_ALPHA;
    setTypingColor(silo.color);
    setIsTyping(true);
    setLiveCard(tile);
    setLiveRow(tile.column);
  }, []);

  const handleStatus = useCallback((status, data) => {
    if (status === "thinking") {
      const silo = silosRef.current.find((s) => s.id === data.silo);
      if (silo) setTypingColor(silo.color);
      setIsTyping(true);
    } else if (status === "idle") {
      setIsTyping(false);
    }
  }, []);

  // Re-fetch silos when backend signals discovery is complete
  const handleSilosReady = useCallback(() => {
    fetchSilos()
      .then((data) => {
        if (data.length > 0) {
          setSilos(data);
          setActiveSilos(new Set(data.map((s) => s.id)));
        }
      })
      .catch((e) => console.error("Failed to fetch silos on ready:", e));
  }, []);

  useSSE({
    workspaceId: workspace?.id,
    onInitialTiles: handleInitialTiles,
    onNewTile: handleNewTile,
    onStatus: handleStatus,
    onSilosReady: handleSilosReady,
  });

  const onLiveComplete = useCallback(() => {
    // Clear previous settle timer to avoid stale closure
    if (liveSettleTimer.current) clearTimeout(liveSettleTimer.current);
    liveSettleTimer.current = setTimeout(() => {
      const card = liveCardRef.current;
      setIsTyping(false);
      setLiveCard(null);
      setLiveRow(null);
      if (card) {
        setCards((prev) => {
          // Deduplicate: don't add if already present
          if (prev.some((c) => c.id === card.id)) return prev;
          const next = [{ ...card, age: formatAge(card.created_at) }, ...prev];
          return next.slice(0, MAX_CARDS);
        });
      }
    }, 800);
  }, []);

  const toggle = (id) =>
    setActiveSilos((p) => {
      const n = new Set(p);
      if (n.has(id)) {
        if (n.size > 1) n.delete(id);
      } else n.add(id);
      return n;
    });

  // Normalize legacy column names to current row IDs
  const normalizeColumn = useCallback((col) => {
    const validIds = new Set(dynamicRows.map(r => r.id));
    validIds.add("resolved");
    if (validIds.has(col)) return col;
    if (col === "action" || col === "watching") return dynamicRows[0]?.id || "row1";
    if (col === "informational") return dynamicRows[1]?.id || "row2";
    return dynamicRows[1]?.id || "row2";
  }, [dynamicRows]);

  const filtered = cards.filter((c) => activeSilos.has(c.silo) || c.silo === "user_question");

  const move = async (id, col) => {
    setCards((p) => p.map((c) => (c.id === id ? { ...c, column: col } : c)));
    setSel((p) => (p?.id === id ? { ...p, column: col } : p));
    try {
      await moveTile(id, col);
    } catch (e) {
      console.error("Failed to move tile:", e);
    }
  };

  // Header chat submit
  const [chatError, setChatError] = useState(null);
  const handleChatAsk = async () => {
    const q = chatInput.trim();
    if (!q || chatAsking) return;
    setChatAsking(true);
    setChatInput("");
    setChatError(null);
    try {
      const res = await askQuestion(q, null, true);
      if (res.tile) {
        setCards((prev) => {
          if (prev.some((c) => c.id === res.tile.id)) return prev;
          return [res.tile, ...prev].slice(0, MAX_CARDS);
        });
      }
    } catch (e) {
      console.error("Chat ask failed:", e);
      setChatError("Failed to get answer. Try again.");
      setTimeout(() => setChatError(null), 4000);
    }
    setChatAsking(false);
  };

  // Callback for ExpandedCard to merge interaction updates (null = deleted)
  const handleInteract = useCallback((tileId, updatedInteraction) => {
    setInteractions((prev) => {
      if (updatedInteraction === null) {
        const next = { ...prev };
        delete next[String(tileId)];
        return next;
      }
      return { ...prev, [String(tileId)]: updatedInteraction };
    });
  }, []);

  // Build cards for the "resolved" / Saved Interactions row:
  // Include tiles with column==="resolved" PLUS tiles with |interest_score| >= 1.0
  const getSavedCards = () => {
    const resolvedCards = filtered.filter((c) => normalizeColumn(c.column) === "resolved");
    const scoredCards = filtered.filter((c) => {
      if (normalizeColumn(c.column) === "resolved") return false; // already included
      const inter = interactions[String(c.id)];
      return inter && Math.abs(inter.interest_score) >= 1.0;
    });
    // Sort scored cards by absolute score descending
    scoredCards.sort((a, b) => {
      const sa = Math.abs(interactions[String(a.id)]?.interest_score || 0);
      const sb = Math.abs(interactions[String(b.id)]?.interest_score || 0);
      return sb - sa;
    });
    return [...resolvedCards, ...scoredCards];
  };

  return (
    <div onClick={() => { setHintsOpen(false); setRowEditorOpen(false); }} style={{ minHeight: "100vh", background: "#07080b", color: "#fff", fontFamily: "'DM Sans',sans-serif", opacity: on ? 1 : 0, transition: "opacity 0.4s" }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet" />
      <style>{`html, body { background: #07080b !important; margin: 0; } @keyframes p{0%,100%{opacity:1}50%{opacity:.25}} @keyframes sentinelPulse{0%{opacity:0.4;transform:scale(0.8)}100%{opacity:1;transform:scale(1.2)}}`}</style>

      <div style={{ position: "sticky", top: 0, zIndex: 50, background: "rgba(7,8,11,0.93)", backdropFilter: "blur(14px)", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
        <div style={{ padding: "11px 24px", display: "flex", alignItems: "center", gap: 12 }}>
          {/* SENTINEL branding */}
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginRight: 2, minWidth: 120 }}>
            <div style={{
              width: 8, height: 8, borderRadius: "50%",
              background: isTyping ? typingColor : "#34d399",
              boxShadow: isTyping
                ? `0 0 14px ${typingColor}aa, 0 0 30px ${typingColor}44`
                : "0 0 5px rgba(52,211,153,0.35)",
              animation: isTyping ? "sentinelPulse 0.15s ease-in-out infinite alternate" : "p 2.5s infinite",
              transition: "background 0.3s, box-shadow 0.3s",
            }} />
            <span style={{
              fontSize: 14, fontWeight: 700, letterSpacing: "0.06em",
              color: isTyping ? typingColor : "rgba(255,255,255,0.85)",
              fontFamily: "'JetBrains Mono',monospace",
              transition: "color 0.3s",
              textShadow: isTyping ? `0 0 10px ${typingColor}55` : "none",
            }}>SENTINEL</span>
            <button onClick={() => setChatOpen((p) => !p)} style={{
              background: "transparent", border: "none", borderRadius: 7,
              width: 24, height: 24, cursor: "pointer",
              display: dataActivated ? "flex" : "none", alignItems: "center", justifyContent: "center",
              transition: "all 0.2s ease", flexShrink: 0, padding: 0,
            }}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke={chatOpen ? "rgba(52,211,153,0.9)" : "rgba(255,255,255,0.7)"} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ transition: "stroke 0.2s" }}>
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
            </button>
          </div>

          {/* Dataset Manager */}
          <DataManager workspaceId={workspace?.id} dataStatus={dataStatus} onDataStatusChange={(status) => {
            setDataStatus(status);
            if (status.data_activated && !dataActivated) {
              setDataActivated(true);
              if (onWorkspaceSwitch) onWorkspaceSwitch({ workspace, data_status: status });
            }
          }} onReload={() => {
            fetchSilos().then((data) => { if (data.length > 0) { setSilos(data); setActiveSilos(new Set(data.map((s) => s.id))); } }).catch(() => {});
          }} />

          {/* Workspace Switcher */}
          <WorkspaceSwitcher activeWorkspace={workspace} onSwitch={(data) => {
            if (onWorkspaceSwitch) onWorkspaceSwitch(data);
          }} />

          <div style={{ flex: 1, display: "flex", alignItems: "center", visibility: dataActivated ? "visible" : "hidden" }}>
            <div style={{
              overflow: "hidden",
              width: chatOpen ? "100%" : 0,
              opacity: chatOpen ? 1 : 0,
              transition: "width 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.25s ease",
            }}>
              <div style={{ display: "flex", alignItems: "center", background: chatAsking ? "rgba(52,211,153,0.06)" : "rgba(255,255,255,0.04)", border: `1px solid ${chatAsking ? "rgba(52,211,153,0.3)" : "rgba(255,255,255,0.15)"}`, borderRadius: 7, padding: "0 11px", whiteSpace: "nowrap", transition: "all 0.2s" }}>
                <input
                  ref={chatInputRef}
                  value={chatInput}
                  onChange={e => setChatInput(e.target.value)}
                  onKeyDown={e => { if (e.key === "Enter") handleChatAsk(); }}
                  placeholder={chatError || (chatAsking ? "Thinking..." : "Ask about your data...")}
                  disabled={chatAsking}
                  style={{ flex: 1, background: "transparent", border: "none", color: chatError ? "rgba(220,100,100,0.8)" : chatAsking ? "rgba(52,211,153,0.7)" : "rgba(255,255,255,0.75)", fontSize: 11.5, padding: "8px 0", outline: "none", fontFamily: "'DM Sans',sans-serif", minWidth: 0 }}
                />
                {chatAsking ? (
                  <div style={{ width: 5, height: 5, borderRadius: "50%", background: "#34d399", animation: "p 0.8s infinite", flexShrink: 0 }} />
                ) : (
                  <span onClick={handleChatAsk} style={{ color: chatInput.trim() ? "rgba(52,211,153,0.8)" : "rgba(255,255,255,0.35)", fontSize: 13, cursor: chatInput.trim() ? "pointer" : "default", flexShrink: 0, transition: "color 0.15s" }}>↗</span>
                )}
              </div>
            </div>
          </div>

          <div style={{ display: dataActivated ? "flex" : "none", gap: 4, flexShrink: 0, alignItems: "center" }}>
            {silos.map((si) => {
              const a = activeSilos.has(si.id);
              const al = si.id === "alpha";
              return (
                <button key={si.id} onClick={() => toggle(si.id)} style={{
                  display: "flex", alignItems: "center", gap: 5, padding: "4px 10px", borderRadius: 5,
                  border: `1px solid ${a ? (al ? "rgba(255,255,255,0.3)" : si.border) : "rgba(255,255,255,0.1)"}`,
                  background: a ? (al ? "rgba(255,255,255,0.06)" : si.bg) : "rgba(255,255,255,0.02)",
                  color: a ? (al ? "#ffffff" : si.color) : "rgba(255,255,255,0.45)",
                  fontSize: 10, fontWeight: al ? 700 : 600, cursor: "pointer", transition: "all .15s", fontFamily: "'DM Sans',sans-serif",
                  textDecoration: a ? "none" : "line-through",
                  textDecorationColor: "rgba(255,255,255,0.15)",
                }}>
                  <div style={{ width: 5, height: 5, borderRadius: "50%", background: a ? si.color : "rgba(255,255,255,0.2)", transition: "all .15s", boxShadow: a && al ? "0 0 6px rgba(255,255,255,0.5)" : "none" }} />
                  {si.label}
                </button>
              );
            })}
            {/* Silo grouping hints editor */}
            <div style={{ position: "relative" }}>
              <button onClick={(e) => { e.stopPropagation(); setHintsOpen(p => !p); }} style={{
                display: "flex", alignItems: "center", justifyContent: "center",
                width: 24, height: 24, borderRadius: 5, flexShrink: 0,
                border: `1px solid ${hintsOpen ? "rgba(255,255,255,0.35)" : "rgba(255,255,255,0.18)"}`,
                background: hintsOpen ? "rgba(255,255,255,0.08)" : "rgba(255,255,255,0.04)",
                color: hintsOpen ? "rgba(255,255,255,0.9)" : "rgba(255,255,255,0.7)",
                cursor: "pointer", transition: "all .15s", padding: 0,
              }}
                onMouseEnter={e => { e.currentTarget.style.color = "rgba(255,255,255,0.95)"; e.currentTarget.style.borderColor = "rgba(255,255,255,0.35)"; e.currentTarget.style.background = "rgba(255,255,255,0.08)"; }}
                onMouseLeave={e => { if (!hintsOpen) { e.currentTarget.style.color = "rgba(255,255,255,0.7)"; e.currentTarget.style.borderColor = "rgba(255,255,255,0.18)"; e.currentTarget.style.background = "rgba(255,255,255,0.04)"; }}}
                title="Configure silo grouping"
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <line x1="4" y1="21" x2="4" y2="14" /><line x1="4" y1="10" x2="4" y2="3" />
                  <line x1="12" y1="21" x2="12" y2="12" /><line x1="12" y1="8" x2="12" y2="3" />
                  <line x1="20" y1="21" x2="20" y2="16" /><line x1="20" y1="12" x2="20" y2="3" />
                  <line x1="1" y1="14" x2="7" y2="14" /><line x1="9" y1="8" x2="15" y2="8" /><line x1="17" y1="16" x2="23" y2="16" />
                </svg>
              </button>
              {hintsOpen && (
                <div onClick={e => e.stopPropagation()} style={{
                  position: "absolute", top: "100%", right: 0, marginTop: 6, zIndex: 100,
                  background: "#0f1117", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8,
                  padding: "14px 16px", width: 300, boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
                }}>
                  <div style={{ fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "rgba(255,255,255,0.3)", marginBottom: 8, fontFamily: "'JetBrains Mono',monospace" }}>Silo Grouping Themes</div>
                  <div style={{ fontSize: 10, color: "rgba(255,255,255,0.25)", marginBottom: 10, lineHeight: 1.5, fontFamily: "'DM Sans',sans-serif" }}>
                    Enter comma-separated themes to guide how the AI organizes your data. Leave empty for automatic grouping.
                  </div>
                  <input
                    value={hintsInput}
                    onChange={e => setHintsInput(e.target.value)}
                    onKeyDown={e => { if (e.key === "Enter") document.getElementById("hints-apply-btn")?.click(); }}
                    placeholder="e.g. revenue trends, customer risk, growth"
                    disabled={hintsLoading}
                    style={{
                      width: "100%", boxSizing: "border-box", background: "rgba(255,255,255,0.03)",
                      border: "1px solid rgba(255,255,255,0.08)", borderRadius: 6,
                      padding: "8px 10px", color: "rgba(255,255,255,0.6)", fontSize: 11,
                      fontFamily: "'DM Sans',sans-serif", outline: "none", marginBottom: 10,
                    }}
                  />
                  <div style={{ display: "flex", gap: 8 }}>
                    <button id="hints-apply-btn" disabled={hintsLoading} onClick={async () => {
                      setHintsLoading(true);
                      try {
                        const hints = hintsInput.split(",").map(h => h.trim()).filter(Boolean);
                        const res = await rediscoverSilos(hints);
                        if (res.silos?.length > 0) {
                          setSilos(res.silos);
                          setActiveSilos(new Set(res.silos.map(s => s.id)));
                        }
                        setHintsOpen(false);
                      } catch (e) {
                        console.error("Rediscovery failed:", e);
                      }
                      setHintsLoading(false);
                    }} style={{
                      flex: 1, padding: "7px 0", borderRadius: 6,
                      background: hintsLoading ? "rgba(52,211,153,0.04)" : "rgba(52,211,153,0.08)",
                      border: "1px solid rgba(52,211,153,0.2)",
                      color: "rgba(52,211,153,0.7)", fontSize: 10, fontWeight: 600,
                      cursor: hintsLoading ? "wait" : "pointer",
                      fontFamily: "'DM Sans',sans-serif", transition: "all 0.15s",
                    }}
                      onMouseEnter={e => { if (!hintsLoading) { e.currentTarget.style.background = "rgba(52,211,153,0.15)"; }}}
                      onMouseLeave={e => { e.currentTarget.style.background = hintsLoading ? "rgba(52,211,153,0.04)" : "rgba(52,211,153,0.08)"; }}
                    >{hintsLoading ? "Regrouping..." : "Apply & Regroup"}</button>
                    <button disabled={hintsLoading} onClick={async () => {
                      setHintsInput("");
                      setHintsLoading(true);
                      try {
                        const res = await rediscoverSilos([]);
                        if (res.silos?.length > 0) {
                          setSilos(res.silos);
                          setActiveSilos(new Set(res.silos.map(s => s.id)));
                        }
                        setHintsOpen(false);
                      } catch (e) {
                        console.error("Rediscovery failed:", e);
                      }
                      setHintsLoading(false);
                    }} style={{
                      padding: "7px 12px", borderRadius: 6,
                      background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)",
                      color: "rgba(255,255,255,0.3)", fontSize: 10, fontWeight: 600,
                      cursor: hintsLoading ? "wait" : "pointer",
                      fontFamily: "'DM Sans',sans-serif", transition: "all 0.15s",
                    }}
                      onMouseEnter={e => { if (!hintsLoading) { e.currentTarget.style.borderColor = "rgba(255,255,255,0.15)"; e.currentTarget.style.color = "rgba(255,255,255,0.5)"; }}}
                      onMouseLeave={e => { e.currentTarget.style.borderColor = "rgba(255,255,255,0.06)"; e.currentTarget.style.color = "rgba(255,255,255,0.3)"; }}
                    >Auto</button>
                  </div>
                </div>
              )}
            </div>
          </div>

          <button onClick={() => setViewMode((m) => m === "compact" ? "classic" : m === "classic" ? "feed" : "compact")} style={{
            display: dataActivated ? "flex" : "none", alignItems: "center", justifyContent: "center",
            width: 28, height: 28, borderRadius: 5, flexShrink: 0,
            border: "1px solid rgba(255,255,255,0.18)", background: "rgba(255,255,255,0.04)",
            color: "rgba(255,255,255,0.7)", cursor: "pointer", transition: "all .15s", marginLeft: 4,
          }}
            onMouseEnter={(e) => { e.currentTarget.style.borderColor = "rgba(255,255,255,0.35)"; e.currentTarget.style.color = "rgba(255,255,255,0.95)"; e.currentTarget.style.background = "rgba(255,255,255,0.08)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = "rgba(255,255,255,0.18)"; e.currentTarget.style.color = "rgba(255,255,255,0.7)"; e.currentTarget.style.background = "rgba(255,255,255,0.04)"; }}
          >
            <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
              {viewMode === "compact" ? (
                <><rect x="1" y="1" width="14" height="3.5" rx="1" /><rect x="1" y="6.25" width="14" height="3.5" rx="1" /><rect x="1" y="11.5" width="14" height="3.5" rx="1" /></>
              ) : viewMode === "classic" ? (
                <><rect x="1" y="1" width="14" height="6" rx="1.5" /><rect x="1" y="9" width="14" height="6" rx="1.5" /></>
              ) : (
                <><rect x="3" y="1" width="10" height="4" rx="1" /><rect x="3" y="6.5" width="10" height="4" rx="1" /><rect x="3" y="12" width="10" height="3" rx="1" /></>
              )}
            </svg>
          </button>

          {/* Admin panel (admin only) */}
          {user?.role === "admin" && (
            <button onClick={() => setAdminOpen(true)} style={{
              display: "flex", alignItems: "center", gap: 5, padding: "4px 10px", borderRadius: 5,
              border: "1px solid rgba(192,132,252,0.35)", background: "rgba(192,132,252,0.06)",
              color: "rgba(192,132,252,0.9)", fontSize: 10, fontWeight: 600,
              cursor: "pointer", transition: "all .15s", fontFamily: "'DM Sans',sans-serif", flexShrink: 0,
            }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = "rgba(192,132,252,0.5)"; e.currentTarget.style.color = "rgba(192,132,252,1)"; e.currentTarget.style.background = "rgba(192,132,252,0.1)"; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = "rgba(192,132,252,0.35)"; e.currentTarget.style.color = "rgba(192,132,252,0.9)"; e.currentTarget.style.background = "rgba(192,132,252,0.06)"; }}
            >
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" />
                <path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" />
              </svg>
              Admin
            </button>
          )}

          {/* User / Logout */}
          <button onClick={onLogout} title={user?.email} style={{
            display: "flex", alignItems: "center", gap: 5, padding: "4px 10px", borderRadius: 5,
            border: "1px solid rgba(255,255,255,0.15)", background: "rgba(255,255,255,0.03)",
            color: "rgba(255,255,255,0.65)", fontSize: 10, fontWeight: 500,
            cursor: "pointer", transition: "all .15s", fontFamily: "'DM Sans',sans-serif", flexShrink: 0,
          }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = "rgba(255,255,255,0.3)"; e.currentTarget.style.color = "rgba(255,255,255,0.9)"; e.currentTarget.style.background = "rgba(255,255,255,0.06)"; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = "rgba(255,255,255,0.15)"; e.currentTarget.style.color = "rgba(255,255,255,0.65)"; e.currentTarget.style.background = "rgba(255,255,255,0.03)"; }}
          >
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" />
            </svg>
            Logout
          </button>

          {/* Row config editor */}
          {dataActivated && <div style={{ position: "relative" }}>
            <button onClick={(e) => { e.stopPropagation(); setRowEditorOpen(p => !p); if (!rowEditing) setRowEditing(dynamicRows.map(r => ({ label: r.label, description: r.description }))); }} style={{
              display: "flex", alignItems: "center", justifyContent: "center",
              width: 28, height: 28, borderRadius: 5, flexShrink: 0,
              border: `1px solid ${rowEditorOpen ? "rgba(255,255,255,0.35)" : "rgba(255,255,255,0.18)"}`,
              background: rowEditorOpen ? "rgba(255,255,255,0.08)" : "rgba(255,255,255,0.04)",
              color: rowEditorOpen ? "rgba(255,255,255,0.9)" : "rgba(255,255,255,0.7)",
              cursor: "pointer", transition: "all .15s",
            }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = "rgba(255,255,255,0.35)"; e.currentTarget.style.color = "rgba(255,255,255,0.95)"; e.currentTarget.style.background = "rgba(255,255,255,0.08)"; }}
              onMouseLeave={e => { if (!rowEditorOpen) { e.currentTarget.style.borderColor = "rgba(255,255,255,0.18)"; e.currentTarget.style.color = "rgba(255,255,255,0.7)"; e.currentTarget.style.background = "rgba(255,255,255,0.04)"; }}}
              title="Configure row categories"
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 20h9" /><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
              </svg>
            </button>
            {rowEditorOpen && rowEditing && (
              <div onClick={e => e.stopPropagation()} style={{
                position: "absolute", top: "100%", right: 0, marginTop: 6, zIndex: 100,
                background: "#0f1117", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8,
                padding: "14px 16px", width: 340, boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
              }}>
                <div style={{ fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "rgba(255,255,255,0.3)", marginBottom: 12, fontFamily: "'JetBrains Mono',monospace" }}>Row Categories</div>
                <div style={{ fontSize: 10, color: "rgba(255,255,255,0.25)", marginBottom: 12, lineHeight: 1.5, fontFamily: "'DM Sans',sans-serif" }}>
                  Define what goes in each row. The AI uses your descriptions to classify findings.
                </div>
                {rowEditing.map((r, i) => (
                  <div key={i} style={{ marginBottom: i === 0 ? 14 : 0, padding: "10px 12px", background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.04)", borderRadius: 6 }}>
                    <div style={{ fontSize: 9, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", color: "rgba(255,255,255,0.2)", marginBottom: 6, fontFamily: "'JetBrains Mono',monospace" }}>Row {i + 1}</div>
                    <input
                      value={r.label}
                      onChange={e => setRowEditing(prev => prev.map((x, j) => j === i ? { ...x, label: e.target.value } : x))}
                      placeholder="Row label"
                      style={{ width: "100%", boxSizing: "border-box", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 5, padding: "6px 8px", color: "rgba(255,255,255,0.7)", fontSize: 12, fontWeight: 600, fontFamily: "'DM Sans',sans-serif", outline: "none", marginBottom: 6 }}
                    />
                    <textarea
                      value={r.description}
                      onChange={e => setRowEditing(prev => prev.map((x, j) => j === i ? { ...x, description: e.target.value } : x))}
                      placeholder="Describe what findings belong here..."
                      rows={2}
                      style={{ width: "100%", boxSizing: "border-box", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 5, padding: "6px 8px", color: "rgba(255,255,255,0.5)", fontSize: 10, fontFamily: "'DM Sans',sans-serif", outline: "none", resize: "vertical", lineHeight: 1.5 }}
                    />
                  </div>
                ))}
                <button disabled={rowSaving} onClick={async () => {
                  setRowSaving(true);
                  try {
                    const res = await saveRowConfig(rowEditing);
                    if (res.rows?.length === 2) setDynamicRows(res.rows);
                    setRowEditorOpen(false);
                  } catch (e) { console.error("Failed to save row config:", e); }
                  setRowSaving(false);
                }} style={{
                  marginTop: 12, width: "100%", padding: "7px 0", borderRadius: 6,
                  background: rowSaving ? "rgba(52,211,153,0.04)" : "rgba(52,211,153,0.08)",
                  border: "1px solid rgba(52,211,153,0.2)",
                  color: "rgba(52,211,153,0.7)", fontSize: 10, fontWeight: 600,
                  cursor: rowSaving ? "wait" : "pointer",
                  fontFamily: "'DM Sans',sans-serif", transition: "all 0.15s",
                }}
                  onMouseEnter={e => { if (!rowSaving) e.currentTarget.style.background = "rgba(52,211,153,0.15)"; }}
                  onMouseLeave={e => { e.currentTarget.style.background = rowSaving ? "rgba(52,211,153,0.04)" : "rgba(52,211,153,0.08)"; }}
                >{rowSaving ? "Saving..." : "Save"}</button>
              </div>
            )}
          </div>}
        </div>
      </div>

      {!dataActivated ? (
        <div style={{
          display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
          minHeight: "calc(100vh - 80px)", padding: "40px 24px", textAlign: "center",
        }}>
          <div style={{
            width: 10, height: 10, borderRadius: "50%", background: "rgba(251,191,36,0.6)",
            marginBottom: 20, boxShadow: "0 0 16px rgba(251,191,36,0.2)",
            animation: "p 2.5s infinite",
          }} />
          <div style={{
            fontSize: 14, fontWeight: 600, color: "rgba(255,255,255,0.5)",
            fontFamily: "'DM Sans',sans-serif", marginBottom: 8,
          }}>Workspace needs data</div>
          <div style={{
            fontSize: 11, color: "rgba(255,255,255,0.25)", lineHeight: 1.6,
            maxWidth: 320,
          }}>
            Use the <strong style={{ color: "rgba(251,191,36,0.6)" }}>Data</strong> tab above to upload CSV files
            {dataStatus?.table_count >= 2 ? ", link your tables," : ""} and activate the workspace.
          </div>
        </div>
      ) : viewMode === "feed" ? (
        <div style={{ paddingTop: 20, paddingBottom: 40, maxWidth: 560, margin: "0 auto", display: "flex", flexDirection: "column", gap: 12, padding: "20px 24px 40px" }}>
          {liveCard && <FeedLiveCard card={liveCard} silo={getSilo(liveCard.silo)} onComplete={onLiveComplete} rows={dynamicRows} />}
          {ROWS.map((r) => {
            const rowCards = r.id === "resolved" ? getSavedCards() : filtered.filter((c) => normalizeColumn(c.column) === r.id);
            if (rowCards.length === 0) return null;
            return rowCards.map((c) => <FeedCard key={c.id} card={c} silo={getSilo(c.silo)} onClick={setSel} interaction={interactions[String(c.id)]} showScore={r.id === "resolved"} rows={dynamicRows} />);
          })}
        </div>
      ) : (
        <div style={{ paddingTop: 6, paddingBottom: 40 }}>
          {ROWS.map((r, i) => (
            <ScrollRow
              key={r.id}
              row={r}
              zIndex={ROWS.length - i}
              compact={compact}
              cards={r.id === "resolved" ? getSavedCards() : filtered.filter((c) => normalizeColumn(c.column) === r.id)}
              getSilo={getSilo}
              onCardClick={setSel}
              liveCard={r.id === (liveRow ? normalizeColumn(liveRow) : null) ? liveCard : null}
              onLiveComplete={onLiveComplete}
              interactions={interactions}
              showScore={r.id === "resolved"}
            />
          ))}
        </div>
      )}

      {sel && <ExpandedCard card={sel} silos={silos} getSilo={getSilo} onClose={() => setSel(null)} onMove={move} interaction={interactions[String(sel.id)]} onInteract={handleInteract} onRemoveTile={(id) => setCards(prev => prev.filter(c => c.id !== id))} rows={dynamicRows} />}
      {adminOpen && <AdminPanel onClose={() => setAdminOpen(false)} />}
    </div>
  );
}


export default function App() {
  const [user, setUser] = useState(null);
  const [workspace, setWorkspace] = useState(null);
  const [dataStatus, setDataStatus] = useState(null);
  const [initialSilos, setInitialSilos] = useState(null);
  const [initialTiles, setInitialTiles] = useState(null);
  const [checking, setChecking] = useState(true);
  // Key to force SentinelApp remount on workspace switch
  const [wsKey, setWsKey] = useState(0);

  useEffect(() => {
    fetchMe()
      .then(async (data) => {
        if (data?.user) setUser(data.user);
        if (data?.workspace) {
          setWorkspace(data.workspace);
          // Activate workspace to load tiles/silos from PG into memory
          try {
            const wsData = await activateWorkspace(data.workspace.id);
            if (wsData.data_status) setDataStatus(wsData.data_status);
            if (wsData.silos?.length > 0) setInitialSilos(wsData.silos);
            if (wsData.tiles?.length > 0) setInitialTiles(wsData.tiles);
          } catch (e) {
            console.error("Failed to activate workspace:", e);
            // Fallback: at least get data status
            try {
              const status = await getDataStatus(data.workspace.id);
              setDataStatus(status);
            } catch {} // eslint-disable-line no-empty
          }
        }
      })
      .catch(() => {})
      .finally(() => setChecking(false));
  }, []);

  const handleLogin = async (loginUser, loginWorkspace) => {
    setUser(loginUser);
    if (loginWorkspace) {
      setWorkspace(loginWorkspace);
      try {
        const wsData = await activateWorkspace(loginWorkspace.id);
        if (wsData.data_status) setDataStatus(wsData.data_status);
        if (wsData.silos?.length > 0) setInitialSilos(wsData.silos);
        if (wsData.tiles?.length > 0) setInitialTiles(wsData.tiles);
      } catch (e) {
        console.error("Failed to activate workspace on login:", e);
      }
    }
  };

  const handleLogout = async () => {
    try { await logout(); } catch (e) { console.error("Logout failed:", e); }
    setUser(null);
    setWorkspace(null);
    setDataStatus(null);
  };

  const handleWorkspaceSwitch = (data) => {
    if (data.workspace) setWorkspace(data.workspace);
    if (data.data_status) setDataStatus(data.data_status);
    if (data.silos?.length > 0) setInitialSilos(data.silos);
    else setInitialSilos(null);
    if (data.tiles?.length > 0) setInitialTiles(data.tiles);
    else setInitialTiles(null);
    // Force remount of SentinelApp to reload everything
    setWsKey((k) => k + 1);
  };

  if (checking) {
    return (
      <div style={{ minHeight: "100vh", background: "#07080b", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#34d399", animation: "p 1.2s infinite" }} />
        <style>{`html, body { background: #07080b !important; margin: 0; } @keyframes p{0%,100%{opacity:1}50%{opacity:.25}}`}</style>
      </div>
    );
  }

  if (!user) {
    return <LoginPage onLogin={handleLogin} />;
  }

  return (
    <ErrorBoundary>
      <SentinelApp key={wsKey} user={user} onLogout={handleLogout} workspace={workspace} onWorkspaceSwitch={handleWorkspaceSwitch} initialDataStatus={dataStatus} initialSilos={initialSilos} initialTiles={initialTiles} />
    </ErrorBoundary>
  );
}
