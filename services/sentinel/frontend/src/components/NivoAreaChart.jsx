import { ResponsiveLine } from '@nivo/line';
import { buildNivoTheme } from './nivoTheme.js';

const spark = {
  rising: [12, 15, 14, 22, 28, 35, 42, 55, 61, 72],
  declining: [68, 62, 58, 51, 47, 40, 35, 28, 22, 18],
  volatile: [30, 52, 25, 61, 28, 55, 32, 70, 38, 65],
  stable: [40, 42, 39, 41, 40, 42, 41, 39, 40, 41],
  spike: [20, 22, 21, 23, 22, 58, 72, 65, 50, 42],
  plateau: [15, 28, 42, 55, 60, 61, 60, 62, 61, 60],
};

function formatTick(v) {
  if (v >= 1000000) return (v / 1000000).toFixed(1) + "M";
  if (v >= 1000) return (v / 1000).toFixed(1) + "k";
  return v;
}

export default function NivoAreaChart({ dataKey, data, color, label }) {
  const raw = (data && data.length >= 2) ? data : (spark[dataKey] || spark.stable);

  const nivoData = [{
    id: label || dataKey || "metric",
    data: raw.map((v, i) => ({ x: i + 1, y: v })),
  }];

  const theme = buildNivoTheme(color);

  return (
    <div style={{ height: 200 }}>
      <ResponsiveLine
        data={nivoData}
        theme={theme}
        margin={{ top: 10, right: 16, bottom: 32, left: 48 }}
        xScale={{ type: "point" }}
        yScale={{ type: "linear", min: "auto", max: "auto", stacked: false }}
        curve="monotoneX"
        colors={[color]}
        lineWidth={2}
        enablePoints={false}
        enableArea={true}
        areaOpacity={0.15}
        defs={[{
          id: "areaGradient",
          type: "linearGradient",
          colors: [
            { offset: 0, color, opacity: 0.25 },
            { offset: 100, color, opacity: 0 },
          ],
        }]}
        fill={[{ match: "*", id: "areaGradient" }]}
        enableGridX={false}
        gridYValues={3}
        axisLeft={{
          tickSize: 0,
          tickPadding: 8,
          tickValues: 3,
          format: formatTick,
        }}
        axisBottom={{
          tickSize: 0,
          tickPadding: 6,
          tickValues: raw.length <= 10
            ? raw.map((_, i) => i + 1)
            : [1, Math.ceil(raw.length / 2), raw.length],
        }}
        axisTop={null}
        axisRight={null}
        enableCrosshair={true}
        crosshairType="x"
        useMesh={true}
        tooltip={({ point }) => (
          <div style={{
            background: "#0c0e14",
            border: `1px solid ${color}44`,
            borderRadius: 8,
            padding: "8px 12px",
            fontFamily: "'DM Sans',sans-serif",
            fontSize: 12,
            color: "rgba(255,255,255,0.7)",
            boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
          }}>
            <span style={{ color, fontWeight: 700, fontFamily: "'JetBrains Mono',monospace" }}>{formatTick(point.data.yFormatted)}</span>
            <span style={{ marginLeft: 8, color: "rgba(255,255,255,0.3)", fontSize: 10 }}>pt {point.data.x}</span>
          </div>
        )}
        motionConfig="gentle"
        animate={true}
      />
    </div>
  );
}
