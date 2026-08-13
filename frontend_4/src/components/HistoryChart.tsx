import {
  CategoryScale,
  Chart,
  Filler,
  Legend,
  LinearScale,
  LineController,
  LineElement,
  type Plugin,
  PointElement,
  Tooltip,
} from "chart.js";
import { useEffect, useRef } from "react";
import { useTheme } from "../app/ThemeContext";
import type { AnalysisResult, LabValue } from "../domain/types";

Chart.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  LineController,
  Filler,
  Tooltip,
  Legend,
);

export const historyMetricGroups = [
  {
    title: "Salud plaquetaria",
    description: "Seguimiento del conteo de plaquetas a lo largo de los hemogramas disponibles.",
    metrics: [{ key: "PLT", label: "Plaquetas", unit: "K/µL", color: "#9c6bcc" }],
  },
  {
    title: "Oxigenación y serie roja",
    description: "Valores que ayudan a contextualizar la serie roja y el transporte de oxígeno.",
    metrics: [
      { key: "RBC", label: "Eritrocitos", unit: "M/µL", color: "#c95d5d" },
      { key: "HGB", label: "Hemoglobina", unit: "g/dL", color: "#b7791f" },
      { key: "HCT", label: "Hematocrito", unit: "%", color: "#2f855a" },
    ],
  },
  {
    title: "Defensas e inflamación",
    description:
      "Conteo total de leucocitos, interpretado siempre junto con el contexto veterinario.",
    metrics: [{ key: "WBC", label: "Leucocitos", unit: "K/µL", color: "#227c9d" }],
  },
] as const;

export type HistoryMetric = (typeof historyMetricGroups)[number]["metrics"][number];

function valueFor(analysis: AnalysisResult, key: string): LabValue | undefined {
  return analysis.lab_values.find((value) => value.name === key);
}

function statusLabel(status: LabValue["status"] | undefined): string {
  if (status === "low") return "bajo";
  if (status === "high") return "alto";
  if (status === "critical") return "crítico";
  if (status === "not_evaluable") return "sin rango evaluable";
  return "dentro de rango";
}

function latestReferenceRange(
  analyses: AnalysisResult[],
  key: string,
): { min: number; max: number } | null {
  for (const analysis of [...analyses].sort((a, b) => b.created_at.localeCompare(a.created_at))) {
    const value = valueFor(analysis, key);
    if (
      value &&
      value.ref_min !== null &&
      value.ref_max !== null &&
      Number.isFinite(value.ref_min) &&
      Number.isFinite(value.ref_max)
    ) {
      return { min: value.ref_min, max: value.ref_max };
    }
  }
  return null;
}

function referenceRangePlugin(
  range: { min: number; max: number } | null,
  theme: "light" | "dark",
): Plugin<"line"> {
  return {
    id: "history-reference-range",
    beforeDatasetsDraw(chart) {
      if (!range) return;
      const y = chart.scales.y;
      const top = y.getPixelForValue(range.max);
      const bottom = y.getPixelForValue(range.min);
      const { ctx, chartArea } = chart;
      ctx.save();
      ctx.fillStyle = theme === "dark" ? "rgba(133, 201, 165, 0.16)" : "rgba(47, 118, 85, 0.10)";
      ctx.fillRect(chartArea.left, top, chartArea.right - chartArea.left, bottom - top);
      ctx.strokeStyle = theme === "dark" ? "rgba(133, 201, 165, 0.55)" : "rgba(47, 118, 85, 0.42)";
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(chartArea.left, top);
      ctx.lineTo(chartArea.right, top);
      ctx.moveTo(chartArea.left, bottom);
      ctx.lineTo(chartArea.right, bottom);
      ctx.stroke();
      ctx.restore();
    },
  };
}

export function HistoryChart({
  analyses,
  metric,
}: {
  analyses: AnalysisResult[];
  metric: HistoryMetric;
}): React.JSX.Element {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { resolved } = useTheme();

  useEffect(() => {
    if (!canvasRef.current) return;
    const sorted = [...analyses].sort((a, b) => a.created_at.localeCompare(b.created_at));
    const referenceRange = latestReferenceRange(sorted, metric.key);
    const metricValues = sorted.map((analysis) => {
      const value = valueFor(analysis, metric.key);
      const parsed = Number(value?.value);
      return Number.isFinite(parsed) ? parsed : null;
    });
    const visibleValues = metricValues.filter((value): value is number => value !== null);
    const suggestedMin = referenceRange
      ? Math.min(referenceRange.min, ...visibleValues)
      : undefined;
    const suggestedMax = referenceRange
      ? Math.max(referenceRange.max, ...visibleValues)
      : undefined;
    const styles = getComputedStyle(document.documentElement);
    const text = styles.getPropertyValue("--text-muted").trim();
    const line = styles.getPropertyValue("--border").trim();
    const chart = new Chart(canvasRef.current, {
      type: "line",
      data: {
        labels: sorted.map((analysis) =>
          new Intl.DateTimeFormat("es-DO", { month: "short", year: "2-digit" }).format(
            new Date(analysis.created_at),
          ),
        ),
        datasets: [
          {
            label: metric.label,
            data: metricValues,
            borderColor: metric.color,
            backgroundColor: `${metric.color}18`,
            pointBackgroundColor: metric.color,
            pointBorderColor: styles.getPropertyValue("--surface").trim(),
            pointBorderWidth: 2,
            pointRadius: 4,
            pointHoverRadius: 5,
            borderWidth: 2,
            tension: 0.25,
            fill: true,
            spanGaps: true,
          },
        ],
      },
      plugins: [referenceRangePlugin(referenceRange, resolved)],
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { intersect: false, mode: "index" },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (context) => {
                const value = valueFor(sorted[context.dataIndex], metric.key);
                return `${metric.label}: ${context.formattedValue} ${metric.unit} · ${statusLabel(value?.status)}`;
              },
            },
          },
        },
        scales: {
          x: {
            grid: { color: line },
            ticks: { color: text },
          },
          y: {
            grid: { color: line },
            ticks: { color: text },
            title: { display: true, text: metric.unit, color: text },
            suggestedMin,
            suggestedMax,
          },
        },
      },
    });
    return () => chart.destroy();
  }, [analyses, metric, resolved]);

  return (
    <div
      className="history-chart history-chart--metric"
      role="img"
      aria-label={`Evolución de ${metric.label}`}
    >
      <canvas ref={canvasRef} />
    </div>
  );
}
