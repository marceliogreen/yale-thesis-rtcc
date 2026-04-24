// Study 1 types
export interface ClearanceRecord {
  city: string;
  year: number;
  homicides_reported: number;
  homicides_cleared: number;
  clearance_rate: number;
  rtcc_year: number;
  post_rtcc: boolean;
  population?: number;
}

export interface EventStudyCoeff {
  city: string;
  rtcc_year: number;
  relative_time: number;
  coefficient: number;
  std_error: number;
  ci_lower: number;
  ci_upper: number;
  p_value: number;
}

export interface ItsMleResult {
  city: string;
  alpha: number;
  beta_1_pre_trend: number;
  beta_2_level_change: number;
  beta_3_trend_change: number;
  se_beta_2: number;
  p_beta_2: number;
  r_squared: number;
}

export interface PsmDidResult {
  specification: string;
  att: number;
  se: number;
  ci_lower: number;
  ci_upper: number;
  p_value: number;
  n_treated: number;
  n_control: number;
}

export interface ShapImportance {
  feature: string;
  importance: number;
  direction?: 'positive' | 'negative' | 'neutral';
}

export interface RobustnessSpec {
  specification: string;
  estimate: number;
  se: number;
  ci_lower: number;
  ci_upper: number;
  p_value: number;
  category: string;
}

export interface PrePostSummary {
  city: string;
  state: string;
  rtcc_year: number;
  population: number;
  pre_clearance: number;
  post_clearance: number;
  change_pp: number;
  pre_homicides: number;
  post_homicides: number;
}

export interface TreatmentCity {
  city: string;
  state: string;
  rtcc_year: number;
  population: number;
  data_source: string;
  verification_sources: string[];
}

// Study 2 types
export interface DfrProgram {
  city: string;
  state: string;
  program: string;
  launch_date: string;
  vendor: string;
  fleet_size: number;
  total_flights: number;
  total_missions: number;
  avg_response_time_min: number;
  success_rate: number;
}

export interface CognitiveDimension {
  dimension: string;
  key_theory: string;
  key_author: string;
  chula_vista_finding: string;
  elizabeth_finding: string;
  cincinnati_finding: string;
  cross_city_assessment: string;
  data_quality: 'strong' | 'moderate' | 'limited' | 'pending';
  prediction_supported: boolean;
}

export interface BenchmarkMapping {
  prediction_id: number;
  prediction_text: string;
  cognitive_dimension: string;
  testable: boolean;
  status: 'supported' | 'refuted' | 'pending' | 'untestable';
  evidence: string;
}

// Dashboard types
export interface KeyFinding {
  label: string;
  value: string;
  significance: string;
  description: string;
  color: 'red' | 'orange' | 'green' | 'blue';
}
