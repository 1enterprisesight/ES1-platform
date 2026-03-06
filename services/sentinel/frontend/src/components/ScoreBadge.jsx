export default function ScoreBadge({ score }) {
  if (typeof score !== 'number' || score === 0) return null;
  const positive = score > 0;
  return (
    <span style={{
      fontSize: 9,
      fontWeight: 600,
      fontFamily: "'JetBrains Mono',monospace",
      color: positive ? "rgba(100,220,100,0.85)" : "rgba(220,100,100,0.85)",
      background: positive ? "rgba(100,220,100,0.08)" : "rgba(220,100,100,0.08)",
      border: `1px solid ${positive ? "rgba(100,220,100,0.2)" : "rgba(220,100,100,0.2)"}`,
      borderRadius: 4,
      padding: "1px 5px",
      lineHeight: 1.4,
    }}>
      {positive ? "+" : ""}{score.toFixed(1)}
    </span>
  );
}
