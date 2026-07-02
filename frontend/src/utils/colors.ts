import type { BetaType, HoldType, MoveType } from '@/types';

// Limb colors — used consistently across all visualizations
export const LIMB_COLORS = {
  lh: '#3b82f6', // blue — left hand
  rh: '#ef4444', // red — right hand
  lf: '#22c55e', // green — left foot
  rf: '#f97316', // orange — right foot
  com: '#eab308', // yellow — center of mass
} as const;

// Hold type colors
const HOLD_TYPE_COLORS: Record<HoldType, string> = {
  jug: '#22c55e',
  positive_edge: '#4ade80',
  incut: '#86efac',
  flat_edge: '#facc15',
  crimp: '#f97316',
  micro_crimp: '#ef4444',
  pocket: '#8b5cf6',
  mono: '#dc2626',
  pocket_2f: '#a78bfa',
  pocket_3f: '#7c3aed',
  sloper: '#06b6d4',
  pinch: '#0891b2',
  rail: '#64748b',
  horn: '#15803d',
  sidepull: '#d97706',
  undercling: '#c2410c',
  gaston: '#9333ea',
  volume: '#475569',
  screw_on: '#78716c',
  chip: '#b45309',
  foot_chip: '#92400e',
  smear: '#374151',
  macro: '#1d4ed8',
  dual_texture: '#be123c',
  unknown: '#6b7280',
};

export function holdTypeToColor(type: HoldType): string {
  return HOLD_TYPE_COLORS[type] ?? '#6b7280';
}

export function betaTypeToLabel(type: BetaType): string {
  const labels: Record<BetaType, string> = {
    shortest: 'Shortest',
    tall_climber: 'Tall Climber',
    static: 'Static',
    dynamic: 'Dynamic',
    competition: 'Competition',
    energy_efficient: 'Energy Efficient',
    high_percentage: 'High %',
    low_power: 'Low Power',
  };
  return labels[type] ?? type;
}

export function moveTypeToLabel(type: MoveType): string {
  return type
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

export function confidenceToColor(confidence: number): string {
  if (confidence >= 0.8) return '#22c55e'; // green
  if (confidence >= 0.6) return '#facc15'; // yellow
  if (confidence >= 0.4) return '#f97316'; // orange
  return '#ef4444'; // red
}

export function confidenceToLabel(confidence: number): string {
  if (confidence >= 0.8) return 'High';
  if (confidence >= 0.6) return 'Medium';
  if (confidence >= 0.4) return 'Low';
  return 'Very Low';
}

export function gradeVToFont(v: number): string {
  const table: Record<number, string> = {
    0: '4',
    1: '4+/5a',
    2: '5a/5b',
    3: '5b/5c',
    4: '5c/6a',
    5: '6a+',
    6: '6b',
    7: '6b+/6c',
    8: '6c+/7a',
    9: '7a+',
    10: '7b',
    11: '7b+',
    12: '7c',
    13: '7c+',
    14: '8a',
    15: '8a+',
    16: '8b',
    17: '8b+',
  };
  return table[v] ?? `V${v}`;
}

export function difficultyToColor(difficulty: number): string {
  // 0-1 scale to color
  if (difficulty <= 0.2) return '#22c55e';
  if (difficulty <= 0.4) return '#84cc16';
  if (difficulty <= 0.6) return '#facc15';
  if (difficulty <= 0.8) return '#f97316';
  return '#ef4444';
}

export function intensityToLabel(intensity: number): string {
  if (intensity >= 0.8) return 'Extreme';
  if (intensity >= 0.6) return 'High';
  if (intensity >= 0.4) return 'Moderate';
  if (intensity >= 0.2) return 'Low';
  return 'Minimal';
}

export function wallAngleToDescription(degrees: number): string {
  if (degrees < -10) return 'Slab';
  if (degrees < 5) return 'Vertical';
  if (degrees < 20) return 'Slight Overhang';
  if (degrees < 35) return 'Moderate Overhang';
  if (degrees < 55) return 'Steep Overhang';
  return 'Roof';
}
