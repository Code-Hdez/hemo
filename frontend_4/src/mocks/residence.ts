import type { AnalysisResult, EpidemiologyPoint, Pet, PetInput, Severity } from "../domain/types";

const PRIVATE_GRID_DEGREES = 0.02;
const PUBLIC_GRID_DEGREES = 0.03;
const MIN_PUBLIC_REPORTS = 3;
const MIN_PUBLIC_PETS = 3;
const DR_BOUNDS = { minLat: 17.45, maxLat: 20.1, minLng: -72.1, maxLng: -68 };

const residenceCatalog = {
  "do-stgo-santiago": { label: "Santiago", lat: 19.46, lng: -70.69, precision: "grid_2km" },
  "do-dn-santo-domingo": {
    label: "Distrito Nacional",
    lat: 18.49,
    lng: -69.93,
    precision: "municipality",
  },
  "do-lav-la-vega": { label: "La Vega", lat: 19.22, lng: -70.53, precision: "municipality" },
  "do-pop-puerto-plata": {
    label: "Puerto Plata",
    lat: 19.79,
    lng: -70.69,
    precision: "municipality",
  },
} as const;

type ResidenceFields = Pick<
  Pet,
  | "residence_zone_code"
  | "residence_label"
  | "residence_lat"
  | "residence_lng"
  | "residence_precision"
  | "residence_consent"
>;

interface AggregatedZone {
  zoneCode: string;
  label: string;
  lat: number;
  lng: number;
  reportIds: Set<string>;
  petIds: Set<string>;
  findingCounts: Map<string, number>;
  severityCounts: Map<Severity, number>;
}

function stableHash(value: string): number {
  let hash = 2_166_136_261;
  for (const character of value) {
    hash ^= character.charCodeAt(0);
    hash = Math.imul(hash, 16_777_619);
  }
  return hash >>> 0;
}

function codePart(value: number): string {
  return value >= 0 ? `p${value}` : `m${Math.abs(value)}`;
}

function publicSuffix(value: string): string {
  return stableHash(value).toString(16).slice(-4).padStart(4, "0").toUpperCase();
}

function gridCenter(
  lat: number,
  lng: number,
  grid: number,
): {
  lat: number;
  lng: number;
  latIndex: number;
  lngIndex: number;
} {
  const latIndex = Math.floor(lat / grid);
  const lngIndex = Math.floor(lng / grid);
  return {
    lat: Number(((latIndex + 0.5) * grid).toFixed(5)),
    lng: Number(((lngIndex + 0.5) * grid).toFixed(5)),
    latIndex,
    lngIndex,
  };
}

function isWithinDominicanRepublic(lat: number, lng: number): boolean {
  return (
    Number.isFinite(lat) &&
    Number.isFinite(lng) &&
    lat >= DR_BOUNDS.minLat &&
    lat <= DR_BOUNDS.maxLat &&
    lng >= DR_BOUNDS.minLng &&
    lng <= DR_BOUNDS.maxLng
  );
}

function locationName(label: string | undefined): string {
  return label?.split(" - zona ")[0].trim() || "República Dominicana";
}

function emptyResidence(): ResidenceFields {
  return {
    residence_zone_code: undefined,
    residence_label: undefined,
    residence_lat: undefined,
    residence_lng: undefined,
    residence_precision: undefined,
    residence_consent: false,
  };
}

export function sanitizeMockResidence(payload: PetInput): ResidenceFields {
  if (!payload.residence_consent) return emptyResidence();

  if (
    typeof payload.residence_lat === "number" &&
    typeof payload.residence_lng === "number" &&
    isWithinDominicanRepublic(payload.residence_lat, payload.residence_lng)
  ) {
    const cell = gridCenter(payload.residence_lat, payload.residence_lng, PRIVATE_GRID_DEGREES);
    const zoneCode = `do-grid-${codePart(cell.latIndex)}-${codePart(cell.lngIndex)}`;
    const label = `${nearestCatalogName(cell.lat, cell.lng)} - zona ${publicSuffix(zoneCode)}`;
    return {
      residence_zone_code: zoneCode,
      residence_label: label,
      residence_lat: cell.lat,
      residence_lng: cell.lng,
      residence_precision: "grid_2km",
      residence_consent: true,
    };
  }

  const catalogEntry = payload.residence_zone_code
    ? residenceCatalog[payload.residence_zone_code as keyof typeof residenceCatalog]
    : undefined;
  if (!catalogEntry) return emptyResidence();

  return {
    residence_zone_code: payload.residence_zone_code,
    residence_label: catalogEntry.label,
    residence_lat: catalogEntry.lat,
    residence_lng: catalogEntry.lng,
    residence_precision: catalogEntry.precision,
    residence_consent: true,
  };
}

function nearestCatalogName(lat: number, lng: number): string {
  const entries = Object.values(residenceCatalog);
  const nearest = entries.reduce((best, candidate) => {
    const bestDistance = (best.lat - lat) ** 2 + (best.lng - lng) ** 2;
    const nextDistance = (candidate.lat - lat) ** 2 + (candidate.lng - lng) ** 2;
    return nextDistance < bestDistance ? candidate : best;
  });
  return nearest.label;
}

function publicPosition(lat: number, lng: number, zoneCode: string): { lat: number; lng: number } {
  const hash = stableHash(zoneCode);
  const maxOffset = PUBLIC_GRID_DEGREES * 0.2;
  const latOffset = (((hash & 0xffff) / 0xffff) * 2 - 1) * maxOffset;
  const lngOffset = ((((hash >>> 16) & 0xffff) / 0xffff) * 2 - 1) * maxOffset;
  return {
    lat: Number((lat + latOffset).toFixed(5)),
    lng: Number((lng + lngOffset).toFixed(5)),
  };
}

function topCount(counts: Map<string, number>): string {
  return (
    [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))[0]?.[0] ??
    "Hallazgos registrados"
  );
}

function topSeverity(counts: Map<Severity, number>): Severity {
  const rank: Record<Severity, number> = { info: 1, warn: 2, danger: 3 };
  return (
    [...counts.entries()].sort((a, b) => rank[b[0]] - rank[a[0]] || b[1] - a[1])[0]?.[0] ?? "info"
  );
}

function intensityFor(
  zone: AggregatedZone,
): Pick<EpidemiologyPoint, "intensity_level" | "intensity_score"> {
  const reportCount = zone.reportIds.size;
  const petCount = zone.petIds.size;
  const severityTotal = [...zone.severityCounts.values()].reduce((sum, count) => sum + count, 0);
  const dangerShare =
    severityTotal > 0 ? (zone.severityCounts.get("danger") ?? 0) / severityTotal : 0;
  const intensityScore = Number(
    (reportCount * 0.45 + petCount * 0.45 + dangerShare * 4).toFixed(2),
  );
  if (petCount >= 8 || (petCount >= 6 && dangerShare >= 0.5)) {
    return { intensity_level: "high", intensity_score: intensityScore };
  }
  if (
    petCount >= 5 ||
    (petCount >= 4 && reportCount >= 10) ||
    (petCount >= 4 && dangerShare >= 0.5)
  ) {
    return { intensity_level: "moderate", intensity_score: intensityScore };
  }
  return { intensity_level: "low", intensity_score: intensityScore };
}

export function buildMockPublicPoints(
  pets: Pet[],
  analyses: AnalysisResult[],
  periodDays: number,
): EpidemiologyPoint[] {
  const cutoff = Date.now() - periodDays * 24 * 60 * 60 * 1000;
  const petsById = new Map(pets.map((pet) => [pet.id, pet]));
  const grouped = new Map<string, AggregatedZone>();

  for (const analysis of analyses) {
    if (new Date(analysis.created_at).getTime() < cutoff) continue;
    if (!analysis.pet_id) continue;
    const pet = petsById.get(analysis.pet_id);
    if (
      !pet?.residence_consent ||
      typeof pet.residence_lat !== "number" ||
      typeof pet.residence_lng !== "number"
    ) {
      continue;
    }

    const cell = gridCenter(pet.residence_lat, pet.residence_lng, PUBLIC_GRID_DEGREES);
    const zoneCode = `do-public-grid-${codePart(cell.latIndex)}-${codePart(cell.lngIndex)}`;
    const zone = grouped.get(zoneCode) ?? {
      zoneCode,
      label: `${locationName(pet.residence_label ?? undefined)} - zona ${publicSuffix(zoneCode)}`,
      lat: cell.lat,
      lng: cell.lng,
      reportIds: new Set<string>(),
      petIds: new Set<string>(),
      findingCounts: new Map<string, number>(),
      severityCounts: new Map<Severity, number>(),
    };
    zone.reportIds.add(analysis.id);
    zone.petIds.add(pet.id);
    for (const finding of analysis.findings) {
      zone.findingCounts.set(finding.label, (zone.findingCounts.get(finding.label) ?? 0) + 1);
      zone.severityCounts.set(
        finding.severity,
        (zone.severityCounts.get(finding.severity) ?? 0) + 1,
      );
    }
    grouped.set(zoneCode, zone);
  }

  return [...grouped.values()]
    .filter(
      (zone) => zone.reportIds.size >= MIN_PUBLIC_REPORTS && zone.petIds.size >= MIN_PUBLIC_PETS,
    )
    .map((zone) => {
      const position = publicPosition(zone.lat, zone.lng, zone.zoneCode);
      const intensity = intensityFor(zone);
      return {
        zone_code: zone.zoneCode,
        zone_label: zone.label,
        lat: position.lat,
        lng: position.lng,
        finding: topCount(zone.findingCounts),
        count: zone.reportIds.size,
        report_count: zone.reportIds.size,
        pet_count: zone.petIds.size,
        severity: topSeverity(zone.severityCounts),
        location_name: zone.label,
        ...intensity,
      };
    })
    .sort((a, b) => b.report_count - a.report_count || a.zone_label.localeCompare(b.zone_label));
}
