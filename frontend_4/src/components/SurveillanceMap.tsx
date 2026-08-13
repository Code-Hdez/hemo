import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef, useState } from "react";
import type { EpidemiologyPoint } from "../domain/types";
import {
  type GeographicCircleFeature,
  type GeographicCircleProperties,
  geographicCircle,
} from "./mapGeometry";
import { dominicanRepublicCenter, osmMapStyle } from "./mapStyle";

const colors = {
  low: "#2f7ca6",
  moderate: "#c58a1a",
  high: "#c24f4f",
};

const sourceId = "surveillance-zones";
const fillLayerId = "surveillance-zones-fill";
const lineLayerId = "surveillance-zones-line";

function zoneRadiusMeters(point: EpidemiologyPoint): number {
  const population = Math.max(1, point.pet_count ?? point.report_count ?? point.count);
  if (point.intensity_level === "high") {
    return Math.max(1200, Math.min(1800, 1050 + Math.sqrt(population) * 210));
  }
  if (point.intensity_level === "moderate") {
    return Math.max(850, Math.min(1200, 720 + Math.sqrt(population) * 150));
  }
  return Math.max(450, Math.min(750, 420 + Math.sqrt(population) * 110));
}

function zoneFeatures(points: EpidemiologyPoint[]): GeographicCircleFeature[] {
  return points.map((point) => {
    const intensity = point.intensity_level ?? "low";
    const color = colors[intensity];
    return geographicCircle(point.lng, point.lat, zoneRadiusMeters(point), {
      id: point.zone_code ?? `${point.lat}-${point.lng}`,
      label: point.zone_label ?? point.location_name,
      finding: point.finding,
      reportCount: point.report_count ?? point.count,
      petCount: point.pet_count ?? 0,
      color,
      fillOpacity: intensity === "high" ? 0.3 : 0.23,
    });
  });
}

function zoneCollection(points: EpidemiologyPoint[]) {
  return { type: "FeatureCollection" as const, features: zoneFeatures(points) };
}

function popupContent(properties: GeographicCircleProperties): HTMLDivElement {
  const content = document.createElement("div");
  const zone = document.createElement("strong");
  const finding = document.createElement("p");
  const totals = document.createElement("small");
  zone.textContent = properties.label;
  finding.textContent = properties.finding;
  totals.textContent = `${properties.reportCount} reportes · ${properties.petCount} mascotas`;
  content.append(zone, finding, totals);
  return content;
}

function updateZones(map: maplibregl.Map, points: EpidemiologyPoint[]): void {
  const data = zoneCollection(points);
  const source = map.getSource(sourceId) as maplibregl.GeoJSONSource | undefined;
  if (source) {
    source.setData(data);
    return;
  }

  map.addSource(sourceId, { type: "geojson", data });
  map.addLayer({
    id: fillLayerId,
    type: "fill",
    source: sourceId,
    paint: {
      "fill-color": ["get", "color"],
      "fill-opacity": ["get", "fillOpacity"],
    },
  });
  map.addLayer({
    id: lineLayerId,
    type: "line",
    source: sourceId,
    paint: {
      "line-color": ["get", "color"],
      "line-width": 2,
      "line-opacity": 0.78,
    },
  });
}

export function SurveillanceMap({ points }: { points: EpidemiologyPoint[] }): React.JSX.Element {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const interactionsBoundRef = useRef(false);
  const [mapError, setMapError] = useState("");

  useEffect(() => {
    if (!containerRef.current) return;
    let map: maplibregl.Map;
    try {
      map = new maplibregl.Map({
        container: containerRef.current,
        style: osmMapStyle,
        center: dominicanRepublicCenter,
        zoom: 6.6,
        attributionControl: false,
      });
    } catch {
      setMapError(
        "El mapa no está disponible en este dispositivo. Consulta la tabla de zonas debajo.",
      );
      return;
    }
    mapRef.current = map;
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");

    return () => {
      popupRef.current = null;
      mapRef.current = null;
      interactionsBoundRef.current = false;
      map.remove();
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const sync = () => {
      updateZones(map, points);
      if (interactionsBoundRef.current) return;
      interactionsBoundRef.current = true;
      map.on("click", fillLayerId, (event) => {
        const properties = event.features?.[0]?.properties as
          | GeographicCircleProperties
          | undefined;
        if (!properties) return;
        popupRef.current?.remove();
        popupRef.current = new maplibregl.Popup({ offset: 10 })
          .setLngLat(event.lngLat)
          .setDOMContent(popupContent(properties))
          .addTo(map);
      });
      map.on("mouseenter", fillLayerId, () => {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", fillLayerId, () => {
        map.getCanvas().style.cursor = "";
      });
    };
    if (map.isStyleLoaded()) sync();
    else map.once("load", sync);
  }, [points]);

  if (mapError) return <output className="surveillance-map map-fallback">{mapError}</output>;

  return (
    <section
      className="surveillance-map"
      ref={containerRef}
      aria-label="Mapa de señales agregadas"
    />
  );
}
