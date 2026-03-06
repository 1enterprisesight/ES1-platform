import { useState, useRef, useCallback } from 'react';
import NivoAreaChart from './NivoAreaChart.jsx';
import NivoBarChart from './NivoBarChart.jsx';
import { askQuestion, recordInteraction, resetTileInteraction } from '../api.js';

const SAVED_ROW = { id: "resolved", label: "Saved Interactions", icon: "✓", bright: false };

const WEIGHT_INFO = [
  { label: "Thumbs up", value: "+2.0" },
  { label: "Thumbs down", value: "-2.0" },
  { label: "Expanded", value: "+0.5" },
  { label: "View time (30s max)", value: "+1.0" },
  { label: "Follow-up question", value: "+1.0" },
];

export default function ExpandedCard({ card, silos, getSilo, onClose, onMove, interaction, onInteract, onRemoveTile, rows }) {
  const ROWS = [...(rows || []), SAVED_ROW];
  const s = getSilo(card.silo);
  const isAlpha = card.silo === "alpha";
  const [phase, setPhase] = useState("enter");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [asking, setAsking] = useState(false);
  const [scoreOpen, setScoreOpen] = useState(false);
  // Initialize thumbs from persisted interaction data
  const [thumbs, setThumbs] = useState(() => {
    if (interaction?.thumbs_up > 0) return "up";
    if (interaction?.thumbs_down > 0) return "down";
    return null;
  });

  // Track expand duration
  const openTime = useRef(Date.now());
  // Collect follow-up questions asked during this session
  const askedQuestions = useRef([]);

  const sendInteraction = useCallback((extra = {}) => {
    const duration = (Date.now() - openTime.current) / 1000;
    const data = {
      tile_title: card.title,
      tile_silo: card.silo,
      tile_summary: card.summary,
      expanded: true,
      expand_duration_s: Math.round(duration * 10) / 10,
      followup_questions: askedQuestions.current,
      thumbs_up: 0,
      thumbs_down: 0,
      ...extra,
    };
    recordInteraction(card.id, data)
      .then((updated) => { if (onInteract) onInteract(card.id, updated); })
      .catch(() => {});
  }, [card, onInteract]);

  const close = () => {
    sendInteraction();
    setPhase("exit");
    setTimeout(onClose, 280);
  };

  const handleAsk = async (q) => {
    const text = q || question;
    if (!text.trim()) return;
    askedQuestions.current.push(text.trim());
    setAsking(true);
    setAnswer(null);
    try {
      const res = await askQuestion(text, {
        title: card.title,
        summary: card.summary,
        detail: card.detail,
      });
      setAnswer(res);
    } catch (e) {
      setAnswer({ answer: `Error: ${e.message}`, sql: null, data: null });
    }
    setAsking(false);
  };

  return (
    <div onClick={close} style={{
      position: "fixed", top: 0, left: 0, right: 0, bottom: 0, zIndex: 200,
      display: "flex", alignItems: "center", justifyContent: "center",
      background: phase === "enter" ? "rgba(0,0,0,0.7)" : "rgba(0,0,0,0)",
      transition: "background 0.3s ease", padding: 24,
    }}>
      <div onClick={e => e.stopPropagation()} style={{
        width: "100%", maxWidth: 720, maxHeight: "90vh", overflowY: "auto",
        background: "#0c0e14",
        border: `1px solid ${isAlpha ? "rgba(255,255,255,0.5)" : s.border}`,
        borderRadius: 14,
        transform: phase === "enter" ? "scale(1)" : "scale(0.92)",
        opacity: phase === "enter" ? 1 : 0,
        transition: "all 0.28s cubic-bezier(0.4, 0, 0.2, 1)",
        animation: "expandIn 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
        scrollbarWidth: "none",
        boxShadow: isAlpha ? "0 0 40px rgba(255,255,255,0.08)" : `0 0 40px ${s.color}10`,
      }}>
        <style>{`@keyframes expandIn{from{transform:scale(0.85);opacity:0}to{transform:scale(1);opacity:1}}`}</style>
        <div style={{ padding: "24px 28px 20px", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 14 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
              <div style={{ width: 7, height: 7, borderRadius: "50%", background: s.color, boxShadow: isAlpha ? "0 0 10px rgba(255,255,255,0.5)" : `0 0 8px ${s.color}44` }} />
              <span style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: isAlpha ? "#ffffff" : s.color, fontFamily: "'JetBrains Mono',monospace" }}>{s.label}</span>
              <span style={{ fontSize: 9, color: "rgba(255,255,255,0.15)", fontFamily: "'JetBrains Mono',monospace" }}>·</span>
              <span style={{ fontSize: 9, color: "rgba(255,255,255,0.2)", fontFamily: "'JetBrains Mono',monospace" }}>{ROWS.find(r => r.id === card.column)?.label}</span>
              <span style={{ fontSize: 9, color: "rgba(255,255,255,0.15)", fontFamily: "'JetBrains Mono',monospace" }}>·</span>
              <span style={{ fontSize: 9, color: "rgba(255,255,255,0.15)", fontFamily: "'JetBrains Mono',monospace" }}>{card.age}</span>
            </div>
            <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
              <button onClick={() => { setThumbs(thumbs === "up" ? null : "up"); sendInteraction({ thumbs_up: thumbs === "up" ? 0 : 1 }); }}
                style={{ background: thumbs === "up" ? "rgba(100,220,100,0.12)" : "rgba(255,255,255,0.04)", border: `1px solid ${thumbs === "up" ? "rgba(100,220,100,0.3)" : "rgba(255,255,255,0.06)"}`, color: thumbs === "up" ? "rgba(100,220,100,0.8)" : "rgba(255,255,255,0.2)", width: 28, height: 28, borderRadius: 6, cursor: "pointer", fontSize: 12, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, transition: "all 0.15s" }}
                title="Useful finding">&#9650;</button>
              <button onClick={() => { setThumbs(thumbs === "down" ? null : "down"); sendInteraction({ thumbs_down: thumbs === "down" ? 0 : 1 }); }}
                style={{ background: thumbs === "down" ? "rgba(220,100,100,0.12)" : "rgba(255,255,255,0.04)", border: `1px solid ${thumbs === "down" ? "rgba(220,100,100,0.3)" : "rgba(255,255,255,0.06)"}`, color: thumbs === "down" ? "rgba(220,100,100,0.8)" : "rgba(255,255,255,0.2)", width: 28, height: 28, borderRadius: 6, cursor: "pointer", fontSize: 12, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, transition: "all 0.15s" }}
                title="Not useful">&#9660;</button>
              <button onClick={close} style={{ background: "rgba(255,255,255,0.04)", border: "none", color: "rgba(255,255,255,0.3)", width: 28, height: 28, borderRadius: 6, cursor: "pointer", fontSize: 13, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, marginLeft: 2 }}>✕</button>
            </div>
          </div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: isAlpha ? "#ffffff" : "rgba(255,255,255,0.9)", lineHeight: 1.3, fontFamily: "'DM Sans',sans-serif", margin: 0 }}>{card.title}</h1>
        </div>
        <div style={{ padding: "24px 28px" }}>
          {(card.chart || card.chartData) && (
            <div style={{ background: isAlpha ? "rgba(255,255,255,0.04)" : s.bg, border: `1px solid ${isAlpha ? "rgba(255,255,255,0.12)" : s.border}`, borderRadius: 10, padding: "16px 20px", marginBottom: 24 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <span style={{ fontSize: 9, textTransform: "uppercase", letterSpacing: "0.07em", color: "rgba(255,255,255,0.25)", fontFamily: "'JetBrains Mono',monospace" }}>{card.chartLabel}</span>
                <div><span style={{ fontSize: 22, fontWeight: 700, color: isAlpha ? "#ffffff" : s.color, fontFamily: "'JetBrains Mono',monospace" }}>{card.metric}</span><span style={{ fontSize: 9, color: "rgba(255,255,255,0.2)", marginLeft: 8, fontFamily: "'JetBrains Mono',monospace", textTransform: "uppercase" }}>{card.metricSub}</span></div>
              </div>
              <NivoAreaChart dataKey={card.chart} data={card.chartData} color={isAlpha ? "#ffffff" : s.color} label={card.chartLabel} />
            </div>
          )}
          {card.barCharts && (
            <div style={{ background: isAlpha ? "rgba(255,255,255,0.04)" : s.bg, border: `1px solid ${isAlpha ? "rgba(255,255,255,0.12)" : s.border}`, borderRadius: 10, padding: "16px 20px", marginBottom: 24 }}>
              {card.metric && (
                <div style={{ display: "flex", justifyContent: "flex-end", alignItems: "baseline", marginBottom: 14 }}>
                  <span style={{ fontSize: 22, fontWeight: 700, color: isAlpha ? "#ffffff" : s.color, fontFamily: "'JetBrains Mono',monospace" }}>{card.metric}</span>
                  {card.metricSub && <span style={{ fontSize: 9, color: "rgba(255,255,255,0.2)", marginLeft: 8, fontFamily: "'JetBrains Mono',monospace", textTransform: "uppercase" }}>{card.metricSub}</span>}
                </div>
              )}
              {card.barCharts.map((bc, i) => (
                <NivoBarChart key={i} chart={bc} color={isAlpha ? "#ffffff" : s.color} />
              ))}
            </div>
          )}
          <div style={{ fontSize: 14, color: "rgba(255,255,255,0.55)", lineHeight: 1.8, fontFamily: "'DM Sans',sans-serif", marginBottom: 28, whiteSpace: "pre-line" }}>{card.detail}</div>
          <div style={{ display: "flex", gap: 24, flexWrap: "wrap", marginBottom: 24 }}>
            <div>
              <div style={{ fontSize: 9, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.07em", color: "rgba(255,255,255,0.15)", marginBottom: 8, fontFamily: "'JetBrains Mono',monospace" }}>Sources</div>
              <div style={{ display: "flex", gap: 5 }}>
                {(card.sources || []).map(src => {
                  const si = silos.find(x => x.label === src);
                  return <span key={src} style={{ fontSize: 10, padding: "4px 10px", borderRadius: 5, background: si ? si.bg : "rgba(255,255,255,0.03)", border: `1px solid ${si ? si.border : "rgba(255,255,255,0.05)"}`, color: si ? si.color : "rgba(255,255,255,0.35)", fontFamily: "'JetBrains Mono',monospace" }}>● {src}</span>;
                })}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 9, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.07em", color: "rgba(255,255,255,0.15)", marginBottom: 8, fontFamily: "'JetBrains Mono',monospace" }}>Move to</div>
              <div style={{ display: "flex", gap: 5 }}>
                {ROWS.map(r => (<button key={r.id} onClick={() => onMove(card.id, r.id)} disabled={r.id === card.column} style={{ fontSize: 10, padding: "4px 10px", borderRadius: 5, background: r.id === card.column ? "rgba(255,255,255,0.06)" : "rgba(255,255,255,0.02)", border: `1px solid rgba(255,255,255,${r.id === card.column ? 0.12 : 0.04})`, color: `rgba(255,255,255,${r.id === card.column ? 0.5 : 0.2})`, cursor: r.id === card.column ? "default" : "pointer", fontFamily: "'DM Sans',sans-serif", fontWeight: 600 }}>{r.label}</button>))}
              </div>
            </div>
          </div>

          {/* Interaction score panel */}
          {interaction && (
            <div style={{ marginBottom: 24 }}>
              <div onClick={() => setScoreOpen(p => !p)} style={{ display: "inline-flex", alignItems: "center", gap: 6, cursor: "pointer", padding: "5px 10px", borderRadius: 6, background: scoreOpen ? "rgba(255,255,255,0.04)" : "transparent", transition: "background 0.15s" }}>
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke={scoreOpen ? "rgba(255,255,255,0.4)" : "rgba(255,255,255,0.15)"} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ transition: "stroke 0.15s" }}>
                  <circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
                </svg>
                <span style={{ fontSize: 9, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.07em", color: scoreOpen ? "rgba(255,255,255,0.4)" : "rgba(255,255,255,0.15)", fontFamily: "'JetBrains Mono',monospace", transition: "color 0.15s" }}>
                  Score: {interaction.interest_score?.toFixed(1) || "0.0"}
                </span>
                <svg width="8" height="8" viewBox="0 0 12 12" fill="none" stroke={scoreOpen ? "rgba(255,255,255,0.3)" : "rgba(255,255,255,0.1)"} strokeWidth="2" strokeLinecap="round" style={{ transform: scoreOpen ? "rotate(180deg)" : "rotate(0)", transition: "all 0.15s" }}>
                  <path d="M3 4.5L6 7.5L9 4.5" />
                </svg>
              </div>
              {scoreOpen && (
                <div style={{ marginTop: 8, padding: "12px 16px", background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.04)", borderRadius: 8 }}>
                  <div style={{ display: "flex", gap: 24, marginBottom: 10 }}>
                    <div style={{ display: "flex", gap: 12 }}>
                      <span style={{ fontSize: 10, color: "rgba(255,255,255,0.3)", fontFamily: "'JetBrains Mono',monospace" }}>&#9650; {interaction.thumbs_up || 0}</span>
                      <span style={{ fontSize: 10, color: "rgba(255,255,255,0.3)", fontFamily: "'JetBrains Mono',monospace" }}>&#9660; {interaction.thumbs_down || 0}</span>
                      <span style={{ fontSize: 10, color: "rgba(255,255,255,0.3)", fontFamily: "'JetBrains Mono',monospace" }}>View: {(interaction.expand_duration_s || 0).toFixed(0)}s</span>
                      <span style={{ fontSize: 10, color: "rgba(255,255,255,0.3)", fontFamily: "'JetBrains Mono',monospace" }}>Q: {(interaction.followup_questions || []).length}</span>
                    </div>
                  </div>
                  <div style={{ marginBottom: 10 }}>
                    {WEIGHT_INFO.map((w) => (
                      <div key={w.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "2px 0" }}>
                        <span style={{ fontSize: 9, color: "rgba(255,255,255,0.25)", fontFamily: "'DM Sans',sans-serif" }}>{w.label}</span>
                        <span style={{ fontSize: 9, fontWeight: 600, color: "rgba(255,255,255,0.35)", fontFamily: "'JetBrains Mono',monospace" }}>{w.value}</span>
                      </div>
                    ))}
                  </div>
                  <button onClick={async () => {
                    try {
                      const res = await resetTileInteraction(card.id);
                      if (onInteract) onInteract(card.id, null);
                      if (res.tile_removed && onRemoveTile) {
                        onRemoveTile(card.id);
                        onClose();
                        return;
                      }
                      setThumbs(null);
                      setScoreOpen(false);
                    } catch (e) { console.error("Failed to reset:", e); }
                  }} style={{
                    width: "100%", padding: "6px 0", borderRadius: 5,
                    background: "rgba(220,100,100,0.06)", border: "1px solid rgba(220,100,100,0.15)",
                    color: "rgba(220,100,100,0.6)", fontSize: 9, fontWeight: 600, cursor: "pointer",
                    fontFamily: "'DM Sans',sans-serif", transition: "all 0.15s",
                  }}
                    onMouseEnter={e => { e.currentTarget.style.background = "rgba(220,100,100,0.12)"; e.currentTarget.style.borderColor = "rgba(220,100,100,0.3)"; }}
                    onMouseLeave={e => { e.currentTarget.style.background = "rgba(220,100,100,0.06)"; e.currentTarget.style.borderColor = "rgba(220,100,100,0.15)"; }}
                  >Reset This Interaction</button>
                </div>
              )}
            </div>
          )}

          {/* Follow-up questions */}
          <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.04)", borderRadius: 10, padding: 16 }}>
            <div style={{ fontSize: 9, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.07em", color: "rgba(255,255,255,0.15)", marginBottom: 8, fontFamily: "'JetBrains Mono',monospace" }}>Investigate this finding</div>
            <div style={{ display: "flex", gap: 8 }}>
              <input
                value={question}
                onChange={e => setQuestion(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') handleAsk(); }}
                placeholder="Ask a follow-up question..."
                style={{ flex: 1, background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 7, padding: "10px 14px", color: "rgba(255,255,255,0.6)", fontSize: 13, fontFamily: "'DM Sans',sans-serif", outline: "none" }}
              />
              <button onClick={() => handleAsk()} disabled={asking} style={{ background: isAlpha ? "rgba(255,255,255,0.12)" : s.bg, border: `1px solid ${isAlpha ? "rgba(255,255,255,0.25)" : s.border}`, borderRadius: 7, width: 38, height: 38, cursor: asking ? "wait" : "pointer", color: isAlpha ? "#ffffff" : s.color, fontSize: 14, display: "flex", alignItems: "center", justifyContent: "center" }}>
                {asking ? "…" : "↗"}
              </button>
            </div>
            {card.suggestedQuestions && card.suggestedQuestions.length > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 10 }}>
                {card.suggestedQuestions.map((q, i) => (
                  <button key={i} onClick={() => { setQuestion(q); handleAsk(q); }} style={{ fontSize: 10, padding: "5px 10px", borderRadius: 5, background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", color: "rgba(255,255,255,0.35)", cursor: "pointer", fontFamily: "'DM Sans',sans-serif", textAlign: "left", lineHeight: 1.4, transition: "all 0.15s" }}
                    onMouseEnter={e => { e.currentTarget.style.borderColor = isAlpha ? "rgba(255,255,255,0.2)" : s.border; e.currentTarget.style.color = isAlpha ? "rgba(255,255,255,0.6)" : s.color; }}
                    onMouseLeave={e => { e.currentTarget.style.borderColor = "rgba(255,255,255,0.06)"; e.currentTarget.style.color = "rgba(255,255,255,0.35)"; }}
                  >{q}</button>
                ))}
              </div>
            )}
            {/* Answer display */}
            {answer && (
              <div style={{ marginTop: 14, padding: "14px 16px", background: "rgba(255,255,255,0.02)", border: `1px solid ${isAlpha ? "rgba(255,255,255,0.1)" : s.border}`, borderRadius: 8 }}>
                <div style={{ fontSize: 13, color: "rgba(255,255,255,0.6)", lineHeight: 1.7, fontFamily: "'DM Sans',sans-serif", whiteSpace: "pre-line" }}>{answer.answer}</div>
                {answer.sql && (
                  <details style={{ marginTop: 10 }}>
                    <summary style={{ fontSize: 10, color: "rgba(255,255,255,0.2)", cursor: "pointer", fontFamily: "'JetBrains Mono',monospace" }}>View SQL</summary>
                    <pre style={{ fontSize: 10, color: "rgba(255,255,255,0.3)", background: "rgba(0,0,0,0.3)", padding: 10, borderRadius: 6, overflow: "auto", marginTop: 6 }}>{answer.sql}</pre>
                  </details>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
