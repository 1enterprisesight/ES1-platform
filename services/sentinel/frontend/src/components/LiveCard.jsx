import { useState, useEffect } from 'react';
import TypewriterText from './TypewriterText.jsx';

export default function LiveCard({ card, silo, onComplete, expandReady, compact }) {
  const s = silo;
  const isAlpha = card.silo === "alpha";
  const [phase, setPhase] = useState("scale");
  const [titleDone, setTitleDone] = useState(false);

  useEffect(() => {
    if (expandReady) {
      const t = setTimeout(() => setPhase("title"), 300);
      return () => clearTimeout(t);
    }
  }, [expandReady]);

  return (
    <div style={{
      flex: "0 0 auto", width: 270, height: compact ? 105 : 140,
      background: isAlpha ? "rgba(255,255,255,0.07)" : s.bg,
      border: `1px solid ${isAlpha ? "rgba(255,255,255,0.6)" : s.color + "66"}`,
      borderRadius: 10, padding: "14px 16px",
      display: "flex", flexDirection: "column", overflow: "hidden",
      boxShadow: isAlpha
        ? "0 0 25px rgba(255,255,255,0.12), 0 0 60px rgba(255,255,255,0.04)"
        : `0 0 25px ${s.color}20, 0 0 60px ${s.color}08`,
      transform: (!expandReady || phase === "scale") ? "scale(0)" : "scale(1)",
      opacity: (!expandReady || phase === "scale") ? 0 : 1,
      transition: "transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.2s ease",
      transformOrigin: "center center",
    }}>
      <div style={{
        display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8, flexShrink: 0,
        opacity: (!expandReady || phase === "scale") ? 0 : 1, transition: "opacity 0.2s ease 0.1s",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <div style={{ width: 6, height: 6, borderRadius: "50%", background: s.color, boxShadow: isAlpha ? "0 0 10px rgba(255,255,255,0.6)" : `0 0 10px ${s.color}88` }} />
          <span style={{ fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: isAlpha ? "#ffffff" : s.color, fontFamily: "'JetBrains Mono',monospace" }}>{s.label}</span>
        </div>
        <span style={{ fontSize: 9, color: "rgba(255,255,255,0.3)", fontFamily: "'JetBrains Mono',monospace" }}>just now</span>
      </div>
      <div style={{ marginBottom: 6, flexShrink: 0 }}>
        <TypewriterText
          text={card.title}
          speed={30}
          started={expandReady && phase !== "scale"}
          onComplete={compact ? () => { setPhase("done"); if (onComplete) onComplete(); } : () => { setTitleDone(true); setPhase("summary"); }}
          style={{ fontSize: 13.5, fontWeight: 700, color: isAlpha ? "#ffffff" : "rgba(255,255,255,0.9)", lineHeight: "1.3", fontFamily: "'DM Sans',sans-serif", display: "block" }}
        />
      </div>
      {!compact ? (
        <div style={{ flex: 1, overflow: "hidden" }}>
          <TypewriterText
            text={card.summary}
            speed={12}
            started={titleDone}
            onComplete={() => { setPhase("done"); if (onComplete) onComplete(); }}
            style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", lineHeight: "1.45", fontFamily: "'DM Sans',sans-serif", display: "block" }}
          />
        </div>
      ) : (
        <div style={{ flex: 1 }} />
      )}
    </div>
  );
}
