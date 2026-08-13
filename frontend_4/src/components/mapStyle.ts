import type { StyleSpecification } from "maplibre-gl";

export const dominicanRepublicCenter: [number, number] = [-70.16, 18.92];
export const residencePickerCenter: [number, number] = [-70.697, 19.4517];

const mapTileUrl =
  import.meta.env.VITE_MAP_TILE_URL ?? "https://tile.openstreetmap.org/{z}/{x}/{y}.png";

export const osmMapStyle: StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: [mapTileUrl],
      tileSize: 256,
      attribution: "© OpenStreetMap",
    },
  },
  layers: [{ id: "osm", type: "raster", source: "osm" }],
};
