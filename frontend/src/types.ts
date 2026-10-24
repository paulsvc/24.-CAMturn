export interface Stock {
  od_mm: number
  id_mm: number
  z_start_mm: number
  z_end_mm: number
}

export interface TurnedFace {
  face_id: string
  index: number
  face_type: string
  z_min: number
  z_max: number
  dia_min_mm: number
  dia_max_mm: number
  length_mm: number
  points: [number, number][]
}

export interface LatheTool {
  tool_id: number
  name: string
  insert_shape: string
  inscribed_circle_mm: number
  thickness_mm: number
  nose_radius_mm: number
  cutting_edge_length_mm: number
  clearance_angle_deg: number
  lead_angle_deg: number
  orientation: number
  max_doc_mm: number
  tip_width_mm: number
  hand: string
}

export interface MotionCmd {
  mode: string
  x?: number
  z?: number
  i?: number
  k?: number
  f?: number
  raw_params?: Record<string, any>
}

export interface OperationNode {
  op_id: string
  name: string
  op_type: string
  tool_id: number
  enabled: boolean
  geometry_scope: string
  assigned_face_id?: string | null
  bound_z_start_mm?: number | null
  bound_z_end_mm?: number | null
  css_m_min: number
  max_rpm: number
  rpm: number
  feed_mm_rev: number
  doc_mm: number
  finish_allowance_mm: number
  retract_mm: number
  comp_mode: string
  stepover_z_mm: number
  pitch_mm: number
  major_dia_mm: number
  thread_z_start_mm: number
  thread_z_end_mm: number
  target_z_mm: number
  target_x_radius_mm: number
  peck_depth_mm: number
  warning_message?: string | null
  command_count: number
  commands: MotionCmd[]
}

export interface GCodeIssue {
  line: number
  code: string
  severity: string
  message: string
  raw_line: string
}

export interface VerificationReport {
  is_valid: boolean
  total_lines: number
  rapid_count: number
  linear_count: number
  arc_count: number
  cycle_count: number
  max_arc_radius_error_mm: number
  max_part_gouge_mm: number
  bounding_box: number[]
  error_count: number
  warning_count: number
  issues: GCodeIssue[]
}

export interface ProjectState {
  name: string
  stock: Stock
  contour_points: [number, number][]
  faces: TurnedFace[]
  operations: OperationNode[]
  tools: LatheTool[]
  is_diameter_mode: boolean
  post_dialect: string
  gcode_text: string
  verification?: VerificationReport | null
}

export interface SimulationWaypoint {
  step_index: number
  op_index: number
  op_name: string
  mode: string
  z: number
  x: number
  x_dia: number
  i?: number | null
  k?: number | null
  f?: number | null
  tool_id: number
  comment?: string | null
}

export interface MeshData {
  vertices: number[]
  normals: number[]
  indices: number[]
}
