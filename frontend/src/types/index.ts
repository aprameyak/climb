// ============================================================
// Core type definitions matching the backend Pydantic models
// ============================================================

export type HoldType =
  | 'jug' | 'positive_edge' | 'incut' | 'flat_edge' | 'crimp'
  | 'micro_crimp' | 'pocket' | 'mono' | 'pocket_2f' | 'pocket_3f'
  | 'sloper' | 'pinch' | 'rail' | 'horn' | 'sidepull' | 'undercling'
  | 'gaston' | 'volume' | 'screw_on' | 'chip' | 'foot_chip' | 'smear'
  | 'macro' | 'dual_texture' | 'unknown';

export type GripDirection =
  | 'pull_down' | 'pull_left' | 'pull_right' | 'undercling'
  | 'pinch' | 'compress' | 'slap' | 'palm';

export type RouteMarkerType = 'start' | 'finish' | 'intermediate' | 'none';

export interface HoldPosition {
  x: number;
  y: number;
  z_estimate: number;
}

export interface SurfaceNormal {
  dx: number;
  dy: number;
  dz: number;
}

export interface HoldUsability {
  left_hand: boolean;
  right_hand: boolean;
  left_foot: boolean;
  right_foot: boolean;
  quality_lh: number;
  quality_rh: number;
  quality_lf: number;
  quality_rf: number;
}

export interface DetectedHold {
  id: string;
  polygon: [number, number][];
  center: HoldPosition;
  orientation_degrees: number;
  estimated_depth_cm: number;
  surface_normal: SurfaceNormal;
  hold_type: HoldType;
  grip_direction: GripDirection;
  estimated_difficulty: number;
  estimated_friction: number;
  usability: HoldUsability;
  usable_hand_positions: HoldPosition[];
  usable_foot_positions: HoldPosition[];
  confidence: number;
  bbox: [number, number, number, number];
  color_rgb: [number, number, number] | null;
  is_start: boolean;
  is_finish: boolean;
  route_id: string | null;
  marker_type: RouteMarkerType;
}

export type WallAngle =
  | 'slab_70' | 'slab_80' | 'vertical'
  | 'overhang_5' | 'overhang_10' | 'overhang_15' | 'overhang_20'
  | 'overhang_25' | 'overhang_30' | 'overhang_35' | 'overhang_40'
  | 'overhang_45' | 'roof';

export type BoardType = 'moonboard' | 'kilter' | 'tension' | 'spray' | 'gym' | 'unknown';

export interface WallGeometry {
  angle_degrees: number;
  wall_type: WallAngle;
  height_m: number;
  width_m: number;
  has_volumes: boolean;
  confidence: number;
}

export type MoveType =
  | 'static' | 'deadpoint' | 'controlled_dyno' | 'full_dyno'
  | 'hand_bump' | 'hand_match' | 'foot_match' | 'drop_knee'
  | 'backstep' | 'inside_flag' | 'outside_flag' | 'reverse_flag'
  | 'heel_hook' | 'toe_hook' | 'bicycle' | 'scum' | 'kneebar'
  | 'rock_over' | 'high_step' | 'mantle' | 'compression' | 'stem'
  | 'bridge' | 'cross_through' | 'cross_over' | 'palm_press'
  | 'campus_move' | 'cut_loose' | 'swing_control' | 'hip_twist'
  | 'hip_drive' | 'shoulder_rotation' | 'lockoff';

export type BetaType =
  | 'shortest' | 'tall_climber' | 'static' | 'dynamic'
  | 'competition' | 'energy_efficient' | 'high_percentage' | 'low_power';

export type ExperienceLevel =
  | 'beginner' | 'intermediate' | 'advanced' | 'expert' | 'elite';

export type ClimbingStyle =
  | 'static' | 'dynamic' | 'balanced' | 'powerful'
  | 'technical' | 'slopey' | 'crimpy' | 'compression';

export type HandDominance = 'left' | 'right' | 'ambidextrous';

export interface Injury {
  body_part: string;
  severity: number;
  movement_restrictions: string[];
  notes: string;
}

export interface ClimberProfile {
  id: string;
  name: string;
  height_cm: number;
  weight_kg: number;
  wingspan_cm: number;
  ape_index: number;
  arm_length_cm: number;
  forearm_length_cm: number;
  leg_length_cm: number;
  torso_length_cm: number;
  shoulder_mobility_deg: number;
  hip_mobility_deg: number;
  ankle_dorsiflexion_deg: number;
  hamstring_flexibility_score: number;
  core_strength_score: number;
  finger_strength_score: number;
  pinch_strength_score: number;
  crimp_strength_score: number;
  sloper_ability_score: number;
  dynamic_comfort_score: number;
  preferred_style: ClimbingStyle;
  experience_level: ExperienceLevel;
  indoor_grade_v: number;
  injuries: Injury[];
  hand_dominance: HandDominance;
  foot_dominance: HandDominance;
  fear_of_dynamic: number;
  max_comfortable_reach_cm: number;
}

export interface LimbPosition {
  hold_id: string | null;
  position: HoldPosition | null;
  is_on_wall: boolean;
  flag_type: string | null;
}

export interface BodyPosition {
  left_hand: LimbPosition;
  right_hand: LimbPosition;
  left_foot: LimbPosition;
  right_foot: LimbPosition;
  hips_position: HoldPosition | null;
  torso_rotation_deg: number;
  head_direction: string;
  weight_distribution: Record<string, number>;
  center_of_mass: HoldPosition;
}

export interface ClimbingMove {
  move_number: number;
  description: string;
  move_types: MoveType[];
  body_position: BodyPosition;
  difficulty_rating: number;
  confidence: number;
  reasoning: string;
  common_mistakes: string[];
  alternative_options: string[];
  energy_cost: number;
  risk_level: number;
  physics_note: string | null;
  is_crux: boolean;
}

export interface BetaSolution {
  id: string;
  beta_type: BetaType;
  climber_profile_id: string;
  route_id: string;
  moves: ClimbingMove[];
  total_energy_cost: number;
  expected_flash_probability: number;
  expected_send_probability: number;
  overall_confidence: number;
  crux_move_numbers: number[];
  notes: string;
  generated_at: string;
  generation_warnings: string[];
}

export interface DifficultyAnalysis {
  grade_v_estimate: number;
  grade_font_estimate: string;
  crux_description: string;
  power_intensity: number;
  finger_intensity: number;
  core_intensity: number;
  coordination_intensity: number;
  balance_intensity: number;
  mobility_intensity: number;
  risk_level: number;
  flash_probability: number;
  send_probability: number;
  confidence: number;
}

export interface VisionPipelineResult {
  image_path: string;
  wall_detected: boolean;
  wall_geometry: WallGeometry | null;
  holds: DetectedHold[];
  route_candidates: ClimbingRoute[];
  active_route: ClimbingRoute | null;
  processing_time_ms: number;
  overall_confidence: number;
  warnings: string[];
  requires_additional_images: boolean;
  confidence_breakdown: Record<string, number>;
  image_quality: Record<string, number>;
}

export interface ClimbingRoute {
  id: string;
  name: string;
  grade_v: number | null;
  grade_font: string | null;
  wall_geometry: WallGeometry;
  holds: DetectedHold[];
  route_graph: unknown | null;
  start_holds: string[];
  finish_holds: string[];
  route_color: string | null;
  confidence: number;
  board_type: BoardType;
  image_paths: string[];
}

export interface AnalysisRequest {
  image_paths: string[];
  climber_profile_id: string | null;
  board_type: BoardType;
  notes: string | null;
  beta_types_requested: string[];
}

export interface AnalysisResult {
  id: string;
  request: AnalysisRequest;
  vision_result: VisionPipelineResult;
  betas: BetaSolution[];
  difficulty: DifficultyAnalysis | null;
  created_at: string;
  climber_profile_id: string | null;
}

export interface AnalysisSummary {
  id: string;
  created_at: string;
  grade_estimate: number | null;
  grade_font: string | null;
  overall_confidence: number;
  hold_count: number;
  beta_count: number;
  image_path: string;
}
