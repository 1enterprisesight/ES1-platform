import { useState, useEffect } from 'react';
import TypewriterText from './TypewriterText.jsx';

const SAVED_ROW = { id: "resolved", label: "Saved Interactions", icon: "✓", bright: false };

export default function FeedLiveCard({ card, silo, onComplete, rows }) {
  const s = silo;
  const isAlpha = card.silo === "alpha";
  const allRows = [...(rows || []), SAVED_ROW];
  const rowLabel = allRows.find(r => r.id === card.column)?.label || "";
  const rowBright = allRows.find(r => r.id === card.column)?.bright;
  const [show, setShow] = useState(false);
  const [titleDone, setTitleDone] = useState(false);
  useEffect(() => { requestAnimationFrame(() => requestAnimationFrame(() => setShow(true))); }, []);
  return (
    <div style={{
      width: "100%", padding: "20px 24px",
      background: isAlpha ? "rgba(255,255,255,0.06)" : s.bg,
      border: `1px solid ${isAlpha ? "rgba(255,255,255,0.5)" : s.color + "55"}`,
      borderRadius: 12,
      boxShadow: isAlpha
        ? "0 0 25px rgba(255,255,255,0.08)"
        : `0 0 25px ${s.color}15`,
      opacity: show ? 1 : 0, transform: show ? "translateY(0)" : "translateY(-20px)",
      transition: "opacity 0.4s ease, transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1)",
      maxHeight: show ? 300 : 0, overflow: "hidden",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: s.color, boxShadow: `0 0 10px ${s.color}88` }} />
            <span style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: isAlpha ? "#fff" : s.color, fontFamily: "'JetBrains Mono',monospace" }}>{s.label}</span>
          </div>
          <span style={{ fontSize: 9, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", padding: "2px 7px", borderRadius: 4, background: rowBright ? "rgba(255,255,255,0.08)" : "rgba(255,255,255,0.03)", color: rowBright ? "rgba(255,255,255,0.55)" : "rgba(255,255,255,0.2)", fontFamily: "'JetBrains Mono',monospace" }}>{rowLabel}</span>
        </div>
        <span style={{ fontSize: 10, color: "rgba(255,255,255,0.3)", fontFamily: "'JetBrains Mono',monospace" }}>just now</span>
      </div>
      <div style={{ marginBottom: 8 }}>
        <TypewriterText text={card.title} speed={30} started={show} onComplete={() => setTitleDone(true)}
          style={{ fontSize: 16, fontWeight: 700, color: isAlpha ? "#fff" : "rgba(255,255,255,0.9)", lineHeight: "1.35", fontFamily: "'DM Sans',sans-serif", display: "block" }} />
      </div>
      <div>
        <TypewriterText text={card.summary} speed={10} started={titleDone} onComplete={onComplete}
          style={{ fontSize: 12.5, color: "rgba(255,255,255,0.4)", lineHeight: "1.55", fontFamily: "'DM Sans',sans-serif", display: "block" }} />
      </div>
    </div>
  );
}
