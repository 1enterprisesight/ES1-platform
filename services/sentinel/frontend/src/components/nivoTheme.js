export function buildNivoTheme(accentColor) {
  return {
    background: "transparent",
    text: {
      fontSize: 11,
      fill: "rgba(255,255,255,0.4)",
      fontFamily: "'JetBrains Mono',monospace",
    },
    axis: {
      ticks: {
        text: {
          fontSize: 10,
          fill: "rgba(255,255,255,0.3)",
          fontFamily: "'JetBrains Mono',monospace",
        },
        line: { stroke: "rgba(255,255,255,0.06)" },
      },
      legend: {
        text: {
          fontSize: 11,
          fill: "rgba(255,255,255,0.3)",
          fontFamily: "'JetBrains Mono',monospace",
        },
      },
    },
    grid: {
      line: {
        stroke: "rgba(255,255,255,0.06)",
        strokeDasharray: "3 3",
      },
    },
    crosshair: {
      line: {
        stroke: accentColor,
        strokeOpacity: 0.5,
        strokeWidth: 1,
      },
    },
    tooltip: {
      container: {
        background: "#0c0e14",
        border: `1px solid ${accentColor}44`,
        borderRadius: 8,
        fontSize: 12,
        fontFamily: "'DM Sans',sans-serif",
        color: "rgba(255,255,255,0.7)",
        padding: "8px 12px",
        boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
      },
    },
  };
}
