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
  alignment: 'left' | 'center' | 'right';
  title_box: BoxStyle;
  body_box: BoxStyle;
  line_spacing: number;
  stroke: StrokeStyle;
  shadow: ShadowStyle;
  max_lines: number;
}

export interface SlideText {
  title: string | null;
  body: string;
}

export interface Slide {
  index: number;
  text: SlideText;
  image_prompt: string | null;
  image_data: string | null;
  style: TextStyle;
  final_image: string | null;
}

export interface StyleProposal {
  index: number;
  description: string;  // Common visual style prompt (used for preview and prepended to all slides)
  preview_image: string | null;
}

export interface Session {
  session_id: string;
  created_at: string;
  updated_at: string;
  current_stage: number;
  draft_text: string;
  num_slides: number;
  include_titles: boolean;
  additional_instructions: string | null;
  language: string;
  style_proposals: StyleProposal[];
  selected_style_proposal_index: number | null;
  image_style_instructions: string | null;
  shared_prompt_prefix: string | null;
  slides: Slide[];
}

export interface ApiResponse<T> {
  session?: T;
  error?: string;
}

export interface ChatResponse {
  success: boolean;
  response: string;
  tool_called: string | null;
  session: Session | null;
}

// SSE chat event types
export type ChatEvent =
  | { event: 'thinking'; text: string }
  | { event: 'text'; text: string }
  | { event: 'tool_call'; name: string; args: Record<string, unknown> }
  | { event: 'tool_result'; name: string; result: Record<string, unknown> }
  | { event: 'error'; message: string }
  | { event: 'done'; session: Session | null; has_writes: boolean };

// Chat message types for the UI
export interface ChatMessage {
  id: string;
  type: 'user' | 'text' | 'thinking' | 'tool_call' | 'tool_result' | 'error';
  content: string;
  toolName?: string;
  toolArgs?: Record<string, unknown>;
  toolResult?: Record<string, unknown>;
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
