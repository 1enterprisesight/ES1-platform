export default function HorizontalBarChart({ chart, color }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ fontSize: 9, textTransform: "uppercase", letterSpacing: "0.07em", color: "rgba(255,255,255,0.25)", fontFamily: "'JetBrains Mono',monospace", marginBottom: 10 }}>{chart.title}</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {chart.bars.map(bar => {
          const pct = bar.max > 0 ? Math.round((bar.value / bar.max) * 100) : 0;
          return (
            <div key={bar.label} style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 11, color: "rgba(255,255,255,0.5)", fontFamily: "'DM Sans',sans-serif", width: 80, textAlign: "right", flexShrink: 0 }}>{bar.label}</span>
              <div style={{ flex: 1, height: 22, background: "rgba(255,255,255,0.03)", borderRadius: 4, overflow: "hidden", position: "relative" }}>
                <div style={{
                  height: "100%",
                  width: `${pct}%`,
                  background: `linear-gradient(90deg, ${color}33, ${color}66)`,
                  borderRadius: 4,
                  transition: "width 0.8s cubic-bezier(0.4, 0, 0.2, 1)",
                }} />
              </div>
              <span style={{ fontSize: 11, fontWeight: 700, color: color, fontFamily: "'JetBrains Mono',monospace", width: 50, flexShrink: 0 }}>{bar.value.toLocaleString()}</span>
              <span style={{ fontSize: 9, color: "rgba(255,255,255,0.2)", fontFamily: "'JetBrains Mono',monospace", width: 32, flexShrink: 0 }}>{pct}%</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
