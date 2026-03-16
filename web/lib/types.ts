/* ── TypeScript types shared across the web app ── */

export interface TrackStatus {
  sc: boolean | null;
  vsc: boolean | null;
  flag: string;
}

export interface TireState {
  compound: string | null;
  age: number | null;
}

export interface DriverState {
  driver_code: string;
  position: number | null;
  gap_to_leader: number | null;
  gap_ahead: number | null;
  gap_behind: number | null;
  tire: TireState | null;
  last_lap_time: number | null;
}

export interface BaseDriver {
  position: number;
  driver_code: string;
  gap_to_leader: number | null;
  tire_compound: string | null;
  tire_age: number | null;
}

export interface FocusDriver {
  driver_code: string;
  position: number | null;
  gap_ahead: number | null;
  gap_behind: number | null;
  tire_compound: string | null;
  tire_age: number | null;
  last_lap_time: number | null;
}

export interface RaceBrief {
  timestamp_utc: string;
  lap: number | null;
  track_status: TrackStatus;
  drivers: BaseDriver[];
  focus: FocusDriver | null;
  source: string;
  mode?: string;
  ingest_ts_utc?: string;
}

export interface PitRejoinAssumptions {
  pit_lane_loss_s: number | null;
  traffic_loss_s: number | null;
}

export interface PitRejoinResult {
  projected_position: number | null;
  gap_ahead_s: number | null;
  gap_behind_s: number | null;
  assumptions: PitRejoinAssumptions;
  confidence: string;
  timestamp_utc: string;
  source: string;
  lap?: number | null;
  mode?: string;
  snapshot_ingest_ts_utc?: string;
}

export interface UndercutAssumptions {
  pit_loss_s: number | null;
  new_tire_delta_s_per_lap: number | null;
  attacker_pace_median_s: number | null;
  defender_pace_median_s: number | null;
}

export interface UndercutResult {
  expected_gain_s: number | null;
  horizon_laps: number | null;
  assumptions: UndercutAssumptions | null;
  confidence: string;
  timestamp_utc: string;
  source: string;
  lap?: number | null;
  mode?: string;
  snapshot_ingest_ts_utc?: string;
}

export interface RecommendStrategyResult {
  recommended_action: string;
  reasons: string[];
  supporting_evidence: Record<string, unknown>;
  confidence: string;
  timestamp_utc: string;
  source: string;
  lap?: number | null;
  mode?: string;
  snapshot_ingest_ts_utc?: string;
  source_ts_utc?: string;
}

export type EvidenceItem =
  | { id: string; type: "pit_rejoin";          timestamp: string; data: PitRejoinResult;          driver: string }
  | { id: string; type: "undercut";             timestamp: string; data: UndercutResult;            attacker: string; defender: string }
  | { id: string; type: "recommend_strategy";   timestamp: string; data: RecommendStrategyResult;  driver: string }
  | { id: string; type: "fact";                 timestamp: string; toolName: string; summary: string; rawData: Record<string, unknown> };
