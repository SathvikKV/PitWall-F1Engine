"use client";

import { useState } from "react";
import type { EvidenceItem, PitRejoinResult, UndercutResult } from "./types";

function isPitRejoin(data: PitRejoinResult | UndercutResult): data is PitRejoinResult {
    return "projected_position" in data;
}

function EvidenceCard({ item }: { item: EvidenceItem }) {
    const [open, setOpen] = useState(false);
    const data = item.data;

    return (
        <div className={`evidence-card ${item.type}`}>
            <div className="card-header" onClick={() => setOpen(!open)}>
                <span className="card-type">{item.type === "pit_rejoin" ? "🏁 Pit Rejoin" : "⚡ Undercut"}</span>
                <span className="card-driver">
                    {item.type === "pit_rejoin" ? item.driver : `${item.attacker} vs ${item.defender}`}
                </span>
                <span className={`card-confidence ${data.confidence}`}>{data.confidence}</span>
                <span className="card-chevron">{open ? "▾" : "▸"}</span>
            </div>

            <div className="card-body">
                {isPitRejoin(data) ? (
                    <div className="result-grid">
                        <div><span className="label">Position</span><span className="value big">P{data.projected_position ?? "—"}</span></div>
                        <div><span className="label">Gap Ahead</span><span className="value">{data.gap_ahead_s?.toFixed(1) ?? "—"}s</span></div>
                        <div><span className="label">Gap Behind</span><span className="value">{data.gap_behind_s?.toFixed(1) ?? "—"}s</span></div>
                    </div>
                ) : (
                    <div className="result-grid">
                        <div>
                            <span className="label">Expected Gain</span>
                            <span className={`value big ${(data.expected_gain_s ?? 0) > 0 ? "positive" : "negative"}`}>
                                {data.expected_gain_s != null ? `${data.expected_gain_s > 0 ? "+" : ""}${data.expected_gain_s.toFixed(2)}s` : "—"}
                            </span>
                        </div>
                        <div><span className="label">Horizon</span><span className="value">{data.horizon_laps} laps</span></div>
                    </div>
                )}
            </div>

            {open && (
                <div className="card-details">
                    <h4>Assumptions</h4>
                    <pre>{JSON.stringify(isPitRejoin(data) ? data.assumptions : data.assumptions, null, 2)}</pre>
                    <div className="meta-row">
                        <span className="dim">{data.mode ? `[${data.mode}]` : ""} L{data.lap ?? "—"}</span>
                        <span className="dim">{data.timestamp_utc?.slice(11, 19)}</span>
                        <span className="dim">source: {data.source}</span>
                    </div>
                </div>
            )}
        </div>
    );
}

interface Props {
    evidence: EvidenceItem[];
}

export default function EvidencePanel({ evidence }: Props) {
    return (
        <div className="panel">
            <h2 className="panel-title">Evidence Cards</h2>
            {evidence.length === 0 && <p className="dim">Run a tool to see results here.</p>}
            <div className="evidence-list">
                {evidence.map((item) => (
                    <EvidenceCard key={item.id} item={item} />
                ))}
            </div>
        </div>
    );
}
