"use client";

import { useState } from "react";
import type { EvidenceItem } from "./types";
import { createSession, startReplay, stopReplay, projectPitRejoin, estimateUndercut } from "./api";

interface Props {
    sessionId: string;
    setSessionId: (v: string) => void;
    focusDriver: string;
    setFocusDriver: (v: string) => void;
    running: boolean;
    setRunning: (v: boolean) => void;
    addEvidence: (e: EvidenceItem) => void;
}

export default function ControlsPanel({
    sessionId, setSessionId, focusDriver, setFocusDriver,
    running, setRunning, addEvidence,
}: Props) {
    const [ndjson, setNdjson] = useState("data/replay/aus_2024_r.ndjson");
    const [tickMs, setTickMs] = useState(1000);
    const [pitDriver, setPitDriver] = useState("NOR");
    const [attacker, setAttacker] = useState("NOR");
    const [defender, setDefender] = useState("PIA");
    const [horizon, setHorizon] = useState(2);
    const [status, setStatus] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    const showStatus = (msg: string) => { setStatus(msg); setTimeout(() => setStatus(null), 3000); };

    const handleCreate = async () => {
        try { await createSession(sessionId); showStatus("Session created"); }
        catch (e: unknown) { showStatus(`Error: ${e instanceof Error ? e.message : e}`); }
    };

    const handleStart = async () => {
        setLoading(true);
        try {
            await createSession(sessionId).catch(() => { });
            await startReplay({ sessionId, ndjsonPath: ndjson, tickMs, loop: true });
            setRunning(true); showStatus("Replay started");
        } catch (e: unknown) { showStatus(`Error: ${e instanceof Error ? e.message : e}`); }
        setLoading(false);
    };

    const handleStop = async () => {
        try { await stopReplay(sessionId); setRunning(false); showStatus("Replay stopped"); }
        catch (e: unknown) { showStatus(`Error: ${e instanceof Error ? e.message : e}`); }
    };

    const handlePitRejoin = async () => {
        try {
            const data = await projectPitRejoin(sessionId, pitDriver);
            addEvidence({
                id: `pr-${Date.now()}`, type: "pit_rejoin",
                timestamp: data.timestamp_utc, data, driver: pitDriver,
            });
        } catch (e: unknown) { showStatus(`Error: ${e instanceof Error ? e.message : e}`); }
    };

    const handleUndercut = async () => {
        try {
            const data = await estimateUndercut(sessionId, attacker, defender, horizon);
            addEvidence({
                id: `uc-${Date.now()}`, type: "undercut",
                timestamp: data.timestamp_utc, data, attacker, defender,
            });
        } catch (e: unknown) { showStatus(`Error: ${e instanceof Error ? e.message : e}`); }
    };

    return (
        <div className="panel controls-panel">
            <h2 className="panel-title">Controls</h2>

            {status && <div className="status-toast">{status}</div>}

            {/* Session */}
            <fieldset className="ctrl-group">
                <legend>Session</legend>
                <input value={sessionId} onChange={(e) => setSessionId(e.target.value)} placeholder="Session ID" />
                <button onClick={handleCreate} className="btn-secondary">Create</button>
            </fieldset>

            {/* Replay */}
            <fieldset className="ctrl-group">
                <legend>Replay</legend>
                <input value={ndjson} onChange={(e) => setNdjson(e.target.value)} placeholder="NDJSON path" />
                <div className="row">
                    <label>Tick (ms) <input type="number" value={tickMs} onChange={(e) => setTickMs(Number(e.target.value))} className="num-input" /></label>
                </div>
                <div className="row">
                    {!running ? (
                        <button onClick={handleStart} disabled={loading} className="btn-primary">
                            {loading ? "Starting…" : "▶ Start Replay"}
                        </button>
                    ) : (
                        <button onClick={handleStop} className="btn-danger">■ Stop</button>
                    )}
                </div>
            </fieldset>

            {/* Focus driver */}
            <fieldset className="ctrl-group">
                <legend>Focus Driver</legend>
                <input value={focusDriver} onChange={(e) => setFocusDriver(e.target.value.toUpperCase())} maxLength={3} placeholder="e.g. NOR" />
            </fieldset>

            {/* Pit Rejoin */}
            <fieldset className="ctrl-group">
                <legend>Pit Rejoin</legend>
                <input value={pitDriver} onChange={(e) => setPitDriver(e.target.value.toUpperCase())} maxLength={3} placeholder="Driver" />
                <button onClick={handlePitRejoin} disabled={!running} className="btn-primary">Run Pit Rejoin</button>
            </fieldset>

            {/* Undercut */}
            <fieldset className="ctrl-group">
                <legend>Undercut</legend>
                <div className="row">
                    <input value={attacker} onChange={(e) => setAttacker(e.target.value.toUpperCase())} maxLength={3} placeholder="Attacker" />
                    <span className="dim">vs</span>
                    <input value={defender} onChange={(e) => setDefender(e.target.value.toUpperCase())} maxLength={3} placeholder="Defender" />
                </div>
                <label>Horizon <input type="number" value={horizon} onChange={(e) => setHorizon(Number(e.target.value))} className="num-input" min={1} max={20} /></label>
                <button onClick={handleUndercut} disabled={!running} className="btn-primary">Run Undercut</button>
            </fieldset>
        </div>
    );
}
