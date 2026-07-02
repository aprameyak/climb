import type { DetectedHold, HoldPosition } from '@/types';

export function normalizedToPixel(
  pos: HoldPosition,
  containerWidth: number,
  containerHeight: number
): { x: number; y: number } {
  return {
    x: pos.x * containerWidth,
    y: pos.y * containerHeight,
  };
}

export function pixelToNormalized(
  x: number,
  y: number,
  containerWidth: number,
  containerHeight: number
): HoldPosition {
  return {
    x: x / containerWidth,
    y: y / containerHeight,
    z_estimate: 0,
  };
}

export function polygonToPath(
  polygon: [number, number][],
  containerWidth: number,
  containerHeight: number
): string {
  if (polygon.length === 0) return '';
  const points = polygon.map(([x, y]) => [
    x * containerWidth,
    y * containerHeight,
  ]);
  const d = points
    .map(([px, py], i) => `${i === 0 ? 'M' : 'L'}${px.toFixed(1)},${py.toFixed(1)}`)
    .join(' ');
  return `${d} Z`;
}

export function polygonToKonvaPoints(
  polygon: [number, number][],
  containerWidth: number,
  containerHeight: number
): number[] {
  const flat: number[] = [];
  for (const [x, y] of polygon) {
    flat.push(x * containerWidth, y * containerHeight);
  }
  return flat;
}

export function calculateCentroid(points: [number, number][]): [number, number] {
  if (points.length === 0) return [0, 0];
  const sumX = points.reduce((s, [x]) => s + x, 0);
  const sumY = points.reduce((s, [, y]) => s + y, 0);
  return [sumX / points.length, sumY / points.length];
}

export function distanceBetweenHolds(a: DetectedHold, b: DetectedHold): number {
  const dx = a.center.x - b.center.x;
  const dy = a.center.y - b.center.y;
  return Math.sqrt(dx * dx + dy * dy);
}

export function getHoldAtPoint(
  holds: DetectedHold[],
  clickX: number,
  clickY: number,
  containerWidth: number,
  containerHeight: number,
  tolerance: number = 20
): DetectedHold | null {
  const normX = clickX / containerWidth;
  const normY = clickY / containerHeight;

  // Check if point is inside any hold polygon
  for (const hold of holds) {
    if (isPointInPolygon(normX, normY, hold.polygon)) {
      return hold;
    }
  }

  // Fall back to nearest hold center within tolerance
  let nearest: DetectedHold | null = null;
  let minDist = Infinity;

  for (const hold of holds) {
    const px = hold.center.x * containerWidth;
    const py = hold.center.y * containerHeight;
    const dist = Math.sqrt((px - clickX) ** 2 + (py - clickY) ** 2);
    if (dist < minDist && dist <= tolerance) {
      minDist = dist;
      nearest = hold;
    }
  }

  return nearest;
}

function isPointInPolygon(
  x: number,
  y: number,
  polygon: [number, number][]
): boolean {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const xi = polygon[i][0];
    const yi = polygon[i][1];
    const xj = polygon[j][0];
    const yj = polygon[j][1];

    const intersect =
      yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi;
    if (intersect) inside = !inside;
  }
  return inside;
}

export function angleToRotation(degrees: number): string {
  return `rotate(${degrees}deg)`;
}

export function holdBboxToPixelRect(
  bbox: [number, number, number, number],
  containerWidth: number,
  containerHeight: number
): { x: number; y: number; width: number; height: number } {
  const [bx, by, bw, bh] = bbox;
  return {
    x: bx * containerWidth,
    y: by * containerHeight,
    width: bw * containerWidth,
    height: bh * containerHeight,
  };
}

export function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

export function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}
