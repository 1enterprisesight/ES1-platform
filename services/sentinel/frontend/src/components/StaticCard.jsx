import { useState } from 'react';
import ScoreBadge from './ScoreBadge.jsx';

export default function StaticCard({ card, silo, onClick, elRef, compact, interaction, showScore }) {
  const s = silo;
  const res = card.column === "resolved";
  const isAlpha = card.silo === "alpha";
  const [hov, setHov] = useState(false);
  const hasUp = interaction?.thumbs_up > 0;
  const hasDown = interaction?.thumbs_down > 0;

  const thumbsIndicator = (hasUp || hasDown) && (
    <span style={{
      fontSize: 10,
      color: hasUp ? (isAlpha ? "rgba(255,255,255,0.5)" : s.color) : "rgba(255,255,255,0.15)",
      opacity: hasUp ? 0.8 : 0.4,
      marginLeft: 4,
      fontFamily: "'JetBrains Mono',monospace",
    }}>
      {hasUp ? "▲" : "▼"}
    </span>
  );

  if (!compact) {
    return (
      <div ref={elRef} onClick={() => onClick(card)} style={{
        flex: "0 0 auto", width: 270, height: 140,
        background: isAlpha ? "rgba(255,255,255,0.07)" : s.bg,
        border: `1px solid ${isAlpha ? "rgba(255,255,255,0.5)" : s.border}`,
        borderRadius: 10, padding: "14px 16px", cursor: "pointer",
        opacity: res ? 0.4 : 1, transition: "all 0.2s ease",
        display: "flex", flexDirection: "column", overflow: "hidden",
        boxShadow: isAlpha ? "0 0 12px rgba(255,255,255,0.06)" : "none",
        position: "relative",
      }}
        onMouseEnter={e => { if (!res) { e.currentTarget.style.borderColor = isAlpha ? "rgba(255,255,255,0.7)" : s.color + "66"; e.currentTarget.style.background = isAlpha ? "rgba(255,255,255,0.11)" : s.bg.replace("0.08", "0.14"); }}}
        onMouseLeave={e => { e.currentTarget.style.borderColor = isAlpha ? "rgba(255,255,255,0.5)" : s.border; e.currentTarget.style.background = isAlpha ? "rgba(255,255,255,0.07)" : s.bg; }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8, flexShrink: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: s.color, boxShadow: isAlpha ? "0 0 8px rgba(255,255,255,0.5)" : "none" }} />
            <span style={{ fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: isAlpha ? "#ffffff" : s.color, fontFamily: "'JetBrains Mono',monospace" }}>{s.label}</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            {showScore && interaction && <ScoreBadge score={interaction.interest_score} />}
            {thumbsIndicator}
            <span style={{ fontSize: 9, color: "rgba(255,255,255,0.15)", fontFamily: "'JetBrains Mono',monospace" }}>{card.age}</span>
          </div>
        </div>
        <div style={{ fontSize: 13.5, fontWeight: 700, color: isAlpha ? "#ffffff" : "rgba(255,255,255,0.85)", marginBottom: 6, lineHeight: 1.3, fontFamily: "'DM Sans',sans-serif", flexShrink: 0 }}>{card.title}</div>
        <div style={{ fontSize: 11, color: "rgba(255,255,255,0.33)", lineHeight: 1.45, fontFamily: "'DM Sans',sans-serif", flex: 1, overflow: "hidden", display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical" }}>{card.summary}</div>
      </div>
    );
  }

  return (
    <div ref={elRef} style={{ flex: "0 0 auto", width: 270, height: 105, position: "relative" }}>
      <div onClick={() => onClick(card)} style={{
        position: "absolute", top: 0, left: 0, width: 270, height: hov ? 130 : 105, boxSizing: "border-box",
        background: hov
          ? (isAlpha ? "linear-gradient(rgba(200,200,220,0.14),rgba(200,200,220,0.10)),#0d0e12" : `linear-gradient(${s.bg.replace("0.08", "0.18")},${s.bg.replace("0.08", "0.12")}),#0d0e12`)
          : (isAlpha ? "rgba(255,255,255,0.07)" : s.bg),
        border: `1px solid ${hov ? (isAlpha ? "rgba(255,255,255,0.55)" : s.color + "66") : (isAlpha ? "rgba(255,255,255,0.5)" : s.border)}`,
        borderRadius: 10, padding: "14px 16px", cursor: "pointer",
        opacity: res ? (hov ? 0.85 : 0.4) : 1, transition: "all 0.25s cubic-bezier(0.4, 0, 0.2, 1)",
        display: "flex", flexDirection: "column", overflow: "hidden",
        transform: hov ? "scale(1.02)" : "scale(1)",
        boxShadow: hov
          ? `0 8px 32px rgba(0,0,0,0.7), 0 2px 12px rgba(0,0,0,0.5), 0 0 1px ${isAlpha ? "rgba(255,255,255,0.3)" : s.color + "44"}`
          : (isAlpha ? "0 0 12px rgba(255,255,255,0.06)" : "none"),
        zIndex: hov ? 10 : 1,
      }}
        onMouseEnter={() => setHov(true)}
        onMouseLeave={() => setHov(false)}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8, flexShrink: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: s.color, boxShadow: isAlpha ? "0 0 8px rgba(255,255,255,0.5)" : "none" }} />
            <span style={{ fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: isAlpha ? "#ffffff" : s.color, fontFamily: "'JetBrains Mono',monospace" }}>{s.label}</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            {showScore && interaction && <ScoreBadge score={interaction.interest_score} />}
            {thumbsIndicator}
            <span style={{ fontSize: 9, color: hov ? "rgba(255,255,255,0.3)" : "rgba(255,255,255,0.15)", fontFamily: "'JetBrains Mono',monospace", transition: "color 0.2s" }}>{card.age}</span>
          </div>
        </div>
        <div style={{ fontSize: 13.5, fontWeight: 700, color: isAlpha ? "#ffffff" : (hov ? "rgba(255,255,255,0.95)" : "rgba(255,255,255,0.85)"), marginBottom: 6, lineHeight: 1.3, fontFamily: "'DM Sans',sans-serif", flexShrink: 0, transition: "color 0.2s" }}>{card.title}</div>
        <div style={{ fontSize: 11, color: "rgba(255,255,255,0.6)", lineHeight: 1.45, fontFamily: "'DM Sans',sans-serif", opacity: hov ? 1 : 0, transition: "opacity 0.2s ease 0.08s", flex: 1, overflow: "hidden", display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical" }}>{card.summary}</div>
      </div>
    </div>
  );
}
