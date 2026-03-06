const spark = {
  rising: [12, 15, 14, 22, 28, 35, 42, 55, 61, 72],
  declining: [68, 62, 58, 51, 47, 40, 35, 28, 22, 18],
  volatile: [30, 52, 25, 61, 28, 55, 32, 70, 38, 65],
  stable: [40, 42, 39, 41, 40, 42, 41, 39, 40, 41],
  spike: [20, 22, 21, 23, 22, 58, 72, 65, 50, 42],
  plateau: [15, 28, 42, 55, 60, 61, 60, 62, 61, 60],
};

export default function Spark({ dataKey, data, color }) {
  const d = (data && data.length >= 2) ? data : (spark[dataKey] || spark.stable);
  const max = Math.max(...d), min = Math.min(...d), r = max - min || 1;
  const p = 2, w = 100, h = 30;
  const pts = d.map((v, i) => `${p + (i / (d.length - 1)) * (w - p * 2)},${h - p - ((v - min) / r) * (h - p * 2)}`).join(" ");
  const gid = `sg${dataKey || 'custom'}${color.replace(/[^a-z0-9]/gi, "")}${data ? 'd' : ''}`;

  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} style={{ display: "block" }}>
      <defs><linearGradient id={gid} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={color} stopOpacity="0.25" /><stop offset="100%" stopColor={color} stopOpacity="0" /></linearGradient></defs>
      <polygon points={pts + ` ${w - p},${h} ${p},${h}`} fill={`url(#${gid})`} />
      <polyline points={pts} fill="none" stroke={color} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" opacity="0.85" />
    </svg>
  );
}
