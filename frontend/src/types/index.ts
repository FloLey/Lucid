export type Alignment = 'left' | 'center' | 'right';
export type CellStatus = 'pending' | 'generating' | 'complete' | 'failed';
/** Two-character corner identifier used by the drag-resize handle system. */
export type Corner = 'tl' | 'tr' | 'bl' | 'br';

export interface BoxStyle {
  x_pct: number;
  y_pct: number;
  w_pct: number;
  h_pct: number;
  padding_pct: number;
}

export interface StrokeStyle {
  enabled: boolean;
  width_px: number;
  color: string;
}

export interface ShadowStyle {
  enabled: boolean;
  dx: number;
  dy: number;
  blur: number;
  color: string;
}

export interface TextStyle {
  font_family: string;
  font_weight: number;
  font_size_px: number;
  body_font_size_px: number;
  text_color: string;
  alignment: Alignment;
  title_box: BoxStyle;
  body_box: BoxStyle;
  line_spacing: number;
  stroke: StrokeStyle;
  shadow: ShadowStyle;
  max_lines: number;
  text_enabled: boolean;
}

export interface SlideText {
  title: string | null;
  body: string;
}

export interface Slide {
  index: number;
  text: SlideText;
  image_prompt: string | null;
  background_image_url: string | null;
  style: TextStyle;
  final_image_url: string | null;
}

export interface StyleProposal {
  index: number;
  description: string;  // Common visual style prompt (used for preview and prepended to all slides)
  preview_image: string | null;
}

export interface ChatMessage {
  role: 'user' | 'model';
  content: string;
  grounded?: boolean;
}

export interface Project {
  project_id: string;
  name: string;
  name_manually_set: boolean;
  slide_count: number;
  created_at: string;
  updated_at: string;
  current_stage: number;
  project_config: ProjectConfig;
  chat_history: ChatMessage[];
  research_instructions: string | null;
  draft_text: string;
  num_slides: number | null;
  include_titles: boolean;
  additional_instructions: string | null;
  language: string;
  style_proposals: StyleProposal[];
  selected_style_proposal_index: number | null;
  image_style_instructions: string | null;
  shared_prompt_prefix: string | null;
  slides: Slide[];
  thumbnail_url: string | null;
}

export interface ProjectCard {
  project_id: string;
  name: string;
  current_stage: number;
  slide_count: number;
  thumbnail_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface StageInstructionsConfig {
  stage1: string | null;
  stage_style: string | null;
  stage2: string | null;
  stage3: string | null;
}

export interface GlobalDefaultsConfig {
  num_slides: number | null;
  language: string;
  include_titles: boolean;
  words_per_slide: string | null;
}

export interface ImageConfig {
  width: number;
  height: number;
  aspect_ratio: string;
}

export interface StyleConfig {
  default_font_family: string;
  default_font_weight: number;
  default_font_size_px: number;
  default_text_color: string;
  default_alignment: string;
  default_text_enabled: boolean;
  default_stroke_enabled: boolean;
  default_stroke_width_px: number;
  default_stroke_color: string;
}

export interface AppConfig {
  // Note: Prompts are NOT in config - they're in .prompt files
  // Use /api/prompts endpoints to edit them
  stage_instructions: StageInstructionsConfig;
  global_defaults: GlobalDefaultsConfig;
  image: ImageConfig;
  style: StyleConfig;
}

export interface ProjectConfig {
  stage_instructions: StageInstructionsConfig;
  global_defaults: GlobalDefaultsConfig;
  image: ImageConfig;
  style: StyleConfig;
  prompts: Record<string, string>;
}

export interface TemplateData {
  id: string;
  name: string;
  default_slide_count: number;
  config: ProjectConfig;
  created_at: string;
}

// ─── Concept Matrix Types ────────────────────────────────────────────────

export interface MatrixCell {
  id: string;
  project_id: string;
  row: number;
  col: number;
  // Diagonal cell fields (row === col)
  label: string | null;
  definition: string | null;
  row_descriptor: string | null;
  col_descriptor: string | null;
  // Off-diagonal cell fields
  concept: string | null;
  explanation: string | null;
  // Optional image
  image_url: string | null;
  // Status
  cell_status: CellStatus;
  cell_error: string | null;
  attempts: number;
}

export interface MatrixProject {
  id: string;
  name: string;
  theme: string;
  n: number;
  /** Non-zero only for description mode non-square matrices; otherwise use n. */
  n_rows: number;
  n_cols: number;
  /** Row/column axis labels for description mode. Empty array for theme mode. */
  row_labels: string[];
  col_labels: string[];
  language: string;
  style_mode: string;
  include_images: boolean;
  input_mode: 'theme' | 'description';
  description: string | null;
  status: CellStatus;
  error_message: string | null;
  cells: MatrixCell[];
  created_at: string;
  updated_at: string;
}

export interface MatrixProjectCard {
  id: string;
  name: string;
  theme: string;
  n: number;
  n_rows: number;
  n_cols: number;
  status: CellStatus;
  include_images: boolean;
  created_at: string;
  updated_at: string;
}

export interface MatrixSettings {
  text_model: string;
  image_model: string;
  diagonal_temperature: number;
  axes_temperature: number;
  cell_temperature: number;
  validation_temperature: number;
  max_concurrency: number;
  max_retries: number;
}

// SSE event union
export type MatrixSSEEvent =
  | { type: 'diagonal'; project_id: string; index: number; label: string; definition: string }
  | { type: 'axes'; project_id: string; row: number; col: number; row_descriptor: string; col_descriptor: string }
  | { type: 'cell'; project_id: string; row: number; col: number; concept: string; explanation: string }
  | { type: 'cell_failed'; project_id: string; row: number; col: number; error: string }
  | { type: 'validation'; project_id: string; failures: Array<{ row: number; col: number }> }
  | { type: 'labels'; project_id: string; row_labels: string[]; col_labels: string[] }
  | { type: 'image'; project_id: string; row: number; col: number; image_url: string }
  | { type: 'progress'; project_id: string; generated: number; total: number }
  | { type: 'done'; project_id: string }
  | { type: 'error'; project_id: string; message: string }
  | { type: 'heartbeat'; project_id: string }
  | { type: 'snapshot'; project_id: string; matrix: MatrixProject };


export interface CommitInfo {
  version: string;
  commit_hash: string | null;
  commit_short: string | null;
  commit_date: string | null;
}
