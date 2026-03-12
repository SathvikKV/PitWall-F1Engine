"use client";

import { useEffect, useState } from "react";
import type { RaceBrief } from "./types";
import { getRaceBrief } from "./api";

interface Props {
    sessionId: string;
    focusDriver: string;
    running: boolean;
}

export default function RaceBriefPanel({ sessionId, focusDriver, running }: Props) {
    const [brief, setBrief] = useState<RaceBrief | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!running) return;
        let active = true;
        const poll = async () => {
            try {
                const b = await getRaceBrief(sessionId, focusDriver || undefined);
                if (active) { setBrief(b); setError(null); }
            } catch (e: unknown) {
                if (active) setError(e instanceof Error ? e.message : String(e));
            }
        };
        poll();
        const id = setInterval(poll, 1500);
        return () => { active = false; clearInterval(id); };
    }, [sessionId, focusDriver, running]);

    const flagColor = (flag: string) => {
        switch (flag) {
            case "GREEN": return "var(--green)";
            case "YELLOW": return "var(--yellow)";
            case "RED": return "var(--red)";
            default: return "var(--text-dim)";
        }
    };

    return (
        <div className="panel">
            <h2 className="panel-title">
                <span className="dot" style={{ background: running ? "var(--green)" : "var(--text-dim)" }} />
                Race Brief
            </h2>

            {error && <div className="error-box">{error}</div>}

            {!brief && !error && (
                <p className="dim">Waiting for replay data…</p>
            )}

            {brief && (
                <>
                    {/* Header bar */}
                    <div className="brief-header">
                        <span className="badge">Lap {brief.lap ?? "—"}</span>
                        <span className="badge" style={{ color: flagColor(brief.track_status?.flag) }}>
                            ● {brief.track_status?.flag ?? "—"}
                        </span>
                        <span className="dim ts">{brief.timestamp_utc?.slice(11, 19) ?? ""}</span>
                    </div>

                    {/* Top 5 */}
                    <h3 className="sub-title">Top 5</h3>
                    <table className="mini-table">
                        <thead>
                            <tr><th>P</th><th>Driver</th><th>Gap</th><th>Tire</th></tr>
                        </thead>
                        <tbody>
                            {brief.top5.map((d) => (
                                <tr key={d.driver_code} className={d.driver_code === focusDriver ? "highlight-row" : ""}>
                                    <td>{d.position}</td>
                                    <td className="mono">{d.driver_code}</td>
                                    <td>{d.gap_to_leader != null ? `+${d.gap_to_leader.toFixed(1)}` : "—"}</td>
                                    <td className="dim">{d.tire_compound ?? "—"}{d.tire_age != null ? ` (${d.tire_age})` : ""}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>

                    {/* Focus driver */}
                    {brief.focus && (
                        <>
                            <h3 className="sub-title">Focus: {brief.focus.driver_code}</h3>
                            <div className="focus-grid">
                                <div><span className="label">Position</span><span className="value">P{brief.focus.position}</span></div>
                                <div><span className="label">Gap Ahead</span><span className="value">{brief.focus.gap_ahead?.toFixed(1) ?? "—"}s</span></div>
                                <div><span className="label">Gap Behind</span><span className="value">{brief.focus.gap_behind?.toFixed(1) ?? "—"}s</span></div>
                                <div><span className="label">Last Lap</span><span className="value">{brief.focus.last_lap_time?.toFixed(1) ?? "—"}s</span></div>
                            </div>
                        </>
                    )}
                </>
            )}
        </div>
    );
}
