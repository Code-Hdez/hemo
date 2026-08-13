export function formatActivityPeriod(period: string): string {
  const week = /^(\d{4})-W(\d{1,2})$/.exec(period);
  if (week) return `Semana ${Number(week[2])} de ${week[1]}`;

  const month = /^(\d{4})-(\d{2})$/.exec(period);
  if (month) {
    const date = new Date(Date.UTC(Number(month[1]), Number(month[2]) - 1, 1));
    const label = new Intl.DateTimeFormat("es-DO", {
      month: "long",
      year: "numeric",
      timeZone: "UTC",
    }).format(date);
    return label.charAt(0).toUpperCase() + label.slice(1);
  }

  return period;
}

export function formatActivityCount(count: number): string {
  return `${count} ${count === 1 ? "hemograma" : "hemogramas"}`;
}

export function intensityLabel(level: "low" | "moderate" | "high" | null | undefined): string {
  if (level === "high") return "Más registros";
  if (level === "moderate") return "Varios registros";
  return "Pocos registros";
}
