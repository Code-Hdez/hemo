import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef, useState } from "react";
import { osmMapStyle, residencePickerCenter } from "./mapStyle";

export interface ResidencePosition {
  lat: number;
  lng: number;
}

interface ResidenceMapPickerProps {
  value: ResidencePosition | null;
  onChange: (position: ResidencePosition) => void;
}

function roundCoordinate(value: number): number {
  return Number(value.toFixed(6));
}

function createMarkerElement(): HTMLSpanElement {
  const element = document.createElement("span");
  element.className = "residence-map-pin";
  element.setAttribute("aria-hidden", "true");
  return element;
}

export function ResidenceMapPicker({
  value,
  onChange,
}: ResidenceMapPickerProps): React.JSX.Element {
  const containerRef = useRef<HTMLElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markerRef = useRef<maplibregl.Marker | null>(null);
  const onChangeRef = useRef(onChange);
  const hasCenteredOnValueRef = useRef(false);
  const [mapError, setMapError] = useState("");

  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  useEffect(() => {
    if (!containerRef.current) return;

    let map: maplibregl.Map;
    try {
      map = new maplibregl.Map({
        container: containerRef.current,
        style: osmMapStyle,
        center: residencePickerCenter,
        zoom: 11.5,
        attributionControl: false,
      });
    } catch {
      setMapError(
        "El mapa no está disponible en este dispositivo. Usa el selector de zona aproximada.",
      );
      return;
    }
    mapRef.current = map;
    map.on("error", (e) => {
      const isWebGL =
        e.error?.message?.toLowerCase().includes("webgl") ||
        (e as { sourceId?: string }).sourceId === undefined;
      if (isWebGL || !mapRef.current) {
        setMapError(
          "El mapa no está disponible en este dispositivo. Usa el selector de zona aproximada.",
        );
        map.remove();
        mapRef.current = null;
      }
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");
    map.on("click", (event) => {
      onChangeRef.current({
        lat: roundCoordinate(event.lngLat.lat),
        lng: roundCoordinate(event.lngLat.lng),
      });
    });

    return () => {
      markerRef.current = null;
      mapRef.current = null;
      map.remove();
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const syncMarker = () => {
      if (!value) {
        markerRef.current?.remove();
        markerRef.current = null;
        return;
      }

      const coordinates: [number, number] = [value.lng, value.lat];
      if (!markerRef.current) {
        markerRef.current = new maplibregl.Marker({ element: createMarkerElement() })
          .setLngLat(coordinates)
          .addTo(map);
      } else {
        markerRef.current.setLngLat(coordinates);
      }

      if (!hasCenteredOnValueRef.current) {
        map.jumpTo({ center: coordinates, zoom: Math.max(map.getZoom(), 13) });
        hasCenteredOnValueRef.current = true;
      }
    };

    if (map.isStyleLoaded()) syncMarker();
    else map.once("load", syncMarker);
  }, [value]);

  return mapError ? (
    <output className="map-fallback">{mapError}</output>
  ) : (
    <section
      className="residence-map-picker"
      ref={containerRef}
      aria-label="Mapa para seleccionar una ubicación aproximada de residencia"
    />
  );
}
