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
  text_color: string;
  alignment: 'left' | 'center' | 'right';
  box: BoxStyle;
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

export interface Session {
  session_id: string;
  created_at: string;
  updated_at: string;
  current_stage: number;
  draft_text: string;
  num_slides: number;
  include_titles: boolean;
  additional_instructions: string | null;
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
