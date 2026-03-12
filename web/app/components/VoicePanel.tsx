"use client";

import { useRef, useState, useCallback } from "react";
import { PitWallLiveClient } from "./live/liveClient";
import { MicCapture, AudioPlayer } from "./live/audio";

interface Props {
    sessionId: string;
    focusDriver: string;
    running: boolean;
}

interface LogEntry {
    id: number;
    time: string;
    text: string;
    type: "status" | "model" | "user" | "tool" | "error";
}

let logId = 0;

export default function VoicePanel({ sessionId, focusDriver, running }: Props) {
    const [status, setStatus] = useState("disconnected");
    const [micActive, setMicActive] = useState(false);
    const [logs, setLogs] = useState<LogEntry[]>([]);

    const clientRef = useRef<PitWallLiveClient | null>(null);
    const micRef = useRef<MicCapture | null>(null);
    const playerRef = useRef<AudioPlayer | null>(null);

    const addLog = useCallback((text: string, type: LogEntry["type"]) => {
        setLogs((prev) =>
            [{ id: ++logId, time: new Date().toLocaleTimeString(), text, type }, ...prev].slice(0, 30)
        );
    }, []);

    const handleConnect = async () => {
        if (!running) { addLog("Start replay first!", "error"); return; }
        try {
            const player = new AudioPlayer();
            playerRef.current = player;

            const client = new PitWallLiveClient(
                {
                    onAudio: (b64) => player.play(b64),
                    onTranscript: (text, role) => addLog(text, role === "model" ? "model" : "user"),
                    onToolCall: (name, args) => addLog(`🔧 ${name}(${JSON.stringify(args).slice(0, 80)})`, "tool"),
                    onStatus: (s) => { setStatus(s); addLog(s, "status"); },
                    onError: (err) => addLog(err, "error"),
                },
                sessionId,
                focusDriver,
            );
            await client.connect();
            clientRef.current = client;
        } catch (e) {
            addLog(`Connection failed: ${e instanceof Error ? e.message : e}`, "error");
        }
    };

    const handleDisconnect = () => {
        micRef.current?.stop(); micRef.current = null; setMicActive(false);
        playerRef.current?.stop(); playerRef.current = null;
        clientRef.current?.disconnect(); clientRef.current = null;
        setStatus("disconnected");
    };

    const handleMicToggle = async () => {
        if (micActive) {
            micRef.current?.stop(); micRef.current = null; setMicActive(false);
            addLog("Mic off", "status");
            return;
        }
        try {
            const mic = new MicCapture();
            await mic.start((b64) => clientRef.current?.sendAudio(b64));
            micRef.current = mic;
            setMicActive(true);
            addLog("Mic on — speak now", "status");
        } catch (e) {
            addLog(`Mic error: ${e instanceof Error ? e.message : e}`, "error");
        }
    };

    const connected = status === "connected" || status === "tool_calling";
    const statusColor = connected ? "var(--green)"
        : status === "connecting" || status === "minting_token" ? "var(--yellow)"
            : "var(--text-dim)";

    return (
        <div className="voice-panel">
            <div className="voice-header">
                <span className="dot" style={{ background: statusColor }} />
                <span className="voice-title">Voice Agent</span>
                <span className="voice-status">{status}</span>
            </div>

            <div className="voice-buttons">
                {!connected ? (
                    <button onClick={handleConnect} className="btn-primary" disabled={!running || status === "connecting"}>
                        {status === "connecting" || status === "minting_token" ? "Connecting…" : "🎙 Connect Voice"}
                    </button>
                ) : (
                    <>
                        <button onClick={handleMicToggle} className={micActive ? "btn-danger" : "btn-primary"}>
                            {micActive ? "⏹ Mute" : "🎤 Start Mic"}
                        </button>
                        <button onClick={handleDisconnect} className="btn-secondary">Disconnect</button>
                    </>
                )}
            </div>

            <div className="voice-log">
                {logs.map((l) => (
                    <div key={l.id} className={`log-entry log-${l.type}`}>
                        <span className="log-time">{l.time}</span>
                        <span className="log-text">{l.text}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}
