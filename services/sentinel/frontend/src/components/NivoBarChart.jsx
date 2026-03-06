import { ResponsiveBar } from '@nivo/bar';
import { buildNivoTheme } from './nivoTheme.js';

export default function NivoBarChart({ chart, color }) {
  if (!chart?.bars || chart.bars.length === 0) return null;

  const barData = chart.bars
    .filter(bar => bar && bar.label != null && bar.value != null)
    .map(bar => ({
      label: bar.label,
      value: bar.value,
      max: bar.max || 0,
      pct: bar.max > 0 ? Math.round((bar.value / bar.max) * 100) : 0,
    })).reverse(); // reverse so first item appears at top

  if (barData.length === 0) return null;

  const theme = buildNivoTheme(color);
  const height = barData.length * 38 + 8;

  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{
        fontSize: 9, textTransform: "uppercase", letterSpacing: "0.07em",
        color: "rgba(255,255,255,0.25)", fontFamily: "'JetBrains Mono',monospace",
        marginBottom: 10,
      }}>{chart.title}</div>
      <div style={{ height }}>
        <ResponsiveBar
          data={barData}
          keys={["value"]}
          indexBy="label"
          layout="horizontal"
          theme={theme}
          margin={{ top: 0, right: 80, bottom: 0, left: 80 }}
          padding={0.35}
          colors={[color + "88"]}
          borderRadius={3}
          enableGridX={false}
          enableGridY={false}
          axisTop={null}
          axisRight={null}
          axisBottom={null}
          axisLeft={{
            tickSize: 0,
            tickPadding: 8,
          }}
          enableLabel={false}
          defs={[{
            id: "barGradient",
            type: "linearGradient",
            colors: [
              { offset: 0, color, opacity: 0.3 },
              { offset: 100, color, opacity: 0.6 },
            ],
          }]}
          fill={[{ match: "*", id: "barGradient" }]}
          layers={[
            "grid",
            "axes",
            "bars",
            ({ bars }) => bars.map(bar => {
              const d = bar.data.data;
              return (
                <g key={bar.key} transform={`translate(${bar.x + bar.width + 8}, ${bar.y + bar.height / 2})`}>
                  <text
                    dominantBaseline="central"
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      fill: color,
                      fontFamily: "'JetBrains Mono',monospace",
                    }}
                  >{d.value.toLocaleString()}</text>
                  <text
                    x={45}
                    dominantBaseline="central"
                    style={{
                      fontSize: 9,
                      fill: "rgba(255,255,255,0.2)",
                      fontFamily: "'JetBrains Mono',monospace",
                    }}
                  >{d.pct}%</text>
                </g>
              );
            }),
          ]}
          tooltip={({ data: d }) => (
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
              <div style={{ fontWeight: 700, marginBottom: 4 }}>{d.label}</div>
              <div><span style={{ color, fontFamily: "'JetBrains Mono',monospace" }}>{d.value.toLocaleString()}</span> / {d.max.toLocaleString()} <span style={{ color: "rgba(255,255,255,0.3)" }}>({d.pct}%)</span></div>
            </div>
          )}
          motionConfig="gentle"
          animate={true}
        />
      </div>
    </div>
  );
}
