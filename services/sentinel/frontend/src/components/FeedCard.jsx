import ScoreBadge from './ScoreBadge.jsx';

export default function FeedCard({ card, silo, onClick, interaction, showScore, rows }) {
  const ROWS = [...(rows || []), { id: "resolved", label: "Saved Interactions", icon: "✓", bright: false }];
  const s = silo;
  const isAlpha = card.silo === "alpha";
  const res = card.column === "resolved";
  const rowLabel = ROWS.find(r => r.id === card.column)?.label || "";
  const rowBright = ROWS.find(r => r.id === card.column)?.bright;
  const hasUp = interaction?.thumbs_up > 0;
  const hasDown = interaction?.thumbs_down > 0;
  return (
    <div onClick={() => onClick(card)} style={{
      width: "100%", padding: "20px 24px", cursor: "pointer",
      background: isAlpha ? "rgba(255,255,255,0.06)" : s.bg,
      border: `1px solid ${isAlpha ? "rgba(255,255,255,0.35)" : s.border}`,
      borderRadius: 12, opacity: res ? 0.5 : 1,
      transition: "all 0.2s ease",
      boxShadow: isAlpha ? "0 0 12px rgba(255,255,255,0.04)" : "none",
    }}
      onMouseEnter={e => { e.currentTarget.style.borderColor = isAlpha ? "rgba(255,255,255,0.55)" : s.color + "55"; e.currentTarget.style.transform = "translateY(-1px)"; e.currentTarget.style.boxShadow = `0 4px 20px rgba(0,0,0,0.4), 0 0 1px ${s.color}33`; }}
      onMouseLeave={e => { e.currentTarget.style.borderColor = isAlpha ? "rgba(255,255,255,0.35)" : s.border; e.currentTarget.style.transform = "translateY(0)"; e.currentTarget.style.boxShadow = isAlpha ? "0 0 12px rgba(255,255,255,0.04)" : "none"; }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: s.color, boxShadow: isAlpha ? "0 0 8px rgba(255,255,255,0.5)" : "none" }} />
            <span style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: isAlpha ? "#fff" : s.color, fontFamily: "'JetBrains Mono',monospace" }}>{s.label}</span>
          </div>
          <span style={{ fontSize: 9, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", padding: "2px 7px", borderRadius: 4, background: rowBright ? "rgba(255,255,255,0.08)" : "rgba(255,255,255,0.03)", color: rowBright ? "rgba(255,255,255,0.55)" : "rgba(255,255,255,0.2)", fontFamily: "'JetBrains Mono',monospace" }}>{rowLabel}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          {showScore && interaction && <ScoreBadge score={interaction.interest_score} />}
          {(hasUp || hasDown) && (
            <span style={{
              fontSize: 10,
              color: hasUp ? (isAlpha ? "rgba(255,255,255,0.5)" : s.color) : "rgba(255,255,255,0.15)",
              opacity: hasUp ? 0.8 : 0.4,
              fontFamily: "'JetBrains Mono',monospace",
            }}>
              {hasUp ? "▲" : "▼"}
            </span>
          )}
          <span style={{ fontSize: 10, color: "rgba(255,255,255,0.15)", fontFamily: "'JetBrains Mono',monospace" }}>{card.age}</span>
        </div>
      </div>
      <div style={{ fontSize: 16, fontWeight: 700, color: isAlpha ? "#fff" : "rgba(255,255,255,0.88)", lineHeight: 1.35, marginBottom: 8, fontFamily: "'DM Sans',sans-serif" }}>{card.title}</div>
      <div style={{ fontSize: 12.5, color: "rgba(255,255,255,0.4)", lineHeight: 1.55, marginBottom: card.metric ? 14 : 0, fontFamily: "'DM Sans',sans-serif" }}>{card.summary}</div>
      {card.metric && (
        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: s.color, fontFamily: "'DM Sans',sans-serif" }}>{card.metric}</div>
            <div style={{ fontSize: 9, color: "rgba(255,255,255,0.2)", textTransform: "uppercase", fontFamily: "'JetBrains Mono',monospace" }}>{card.metricSub}</div>
          </div>
        </div>
      )}
    </div>
  );
}
