export interface GeographicCircleProperties {
  color: string;
  fillOpacity: number;
  id: string;
  label: string;
  finding: string;
  reportCount: number;
  petCount: number;
}

export interface GeographicCircleFeature {
  type: "Feature";
  properties: GeographicCircleProperties;
  geometry: {
    type: "Polygon";
    coordinates: number[][][];
  };
}

const EARTH_RADIUS_METERS = 6_371_008.8;

export function geographicCircle(
  longitude: number,
  latitude: number,
  radiusMeters: number,
  properties: GeographicCircleProperties,
  steps = 48,
): GeographicCircleFeature {
  const angularDistance = radiusMeters / EARTH_RADIUS_METERS;
  const latitudeRadians = (latitude * Math.PI) / 180;
  const coordinates: number[][] = [];

  for (let step = 0; step <= steps; step += 1) {
    const bearing = (step / steps) * Math.PI * 2;
    const pointLatitude = Math.asin(
      Math.sin(latitudeRadians) * Math.cos(angularDistance) +
        Math.cos(latitudeRadians) * Math.sin(angularDistance) * Math.cos(bearing),
    );
    const pointLongitude =
      (longitude * Math.PI) / 180 +
      Math.atan2(
        Math.sin(bearing) * Math.sin(angularDistance) * Math.cos(latitudeRadians),
        Math.cos(angularDistance) - Math.sin(latitudeRadians) * Math.sin(pointLatitude),
      );
    coordinates.push([(pointLongitude * 180) / Math.PI, (pointLatitude * 180) / Math.PI]);
  }

  return {
    type: "Feature",
    properties,
    geometry: { type: "Polygon", coordinates: [coordinates] },
  };
}
