"use client"

import { useState, useCallback, useEffect, useRef } from "react"
import { RaceBriefPanel } from "@/components/dashboard/race-brief-panel"
import { VoiceAgentPanel } from "@/components/dashboard/voice-agent-panel"
import { EvidenceCardsPanel } from "@/components/dashboard/evidence-cards-panel"
import { ControlsPanel } from "@/components/dashboard/controls-panel"
import { DriverMap } from "@/components/dashboard/driver-map"
import { Flag } from "lucide-react"

import {
  getRaceBrief,
  createSession,
  startReplay,
  stopReplay,
  startLive,
  stopLive,
  projectPitRejoin,
  estimateUndercut,
  recommendStrategy
} from "@/lib/api"
import { PitWallLiveClient } from "@/lib/live/liveClient"
import { MicCapture, AudioPlayer } from "@/lib/live/audio"
import type { EvidenceItem, RecommendStrategyResult, PitRejoinResult, UndercutResult, RaceBrief } from "@/lib/types"

export default function F1StrategyDashboard() {
  // Connection state
  const [connectionStatus, setConnectionStatus] = useState<"disconnected" | "connecting" | "connected">("disconnected")
  const [isMicActive, setIsMicActive] = useState(false)
  const [transcript, setTranscript] = useState<{id:string, type:"status"|"user"|"model"|"tool", content:string, timestamp:string, toolName?:string}[]>([])

  // Tools state
  const clientRef = useRef<PitWallLiveClient | null>(null)
  const micRef = useRef<MicCapture | null>(null)
  const playerRef = useRef<AudioPlayer | null>(null)
  let logId = useRef(0)

  // Control state
  const [sessionId, setSessionId] = useState("replay_aus_2024_r")
  const [replayPath, setReplayPath] = useState("data/replay/aus_2024_r.ndjson")
  const [tickSpeed, setTickSpeed] = useState(1000)
  const [isReplaying, setIsReplaying] = useState(false)
  const [focusDriverCode, setFocusDriverCode] = useState("NOR")
  const [liveSessionKey, setLiveSessionKey] = useState("latest")
  const [isLiveMode, setIsLiveMode] = useState(false)
  const [detectedSessionType, setDetectedSessionType] = useState<"RACE" | "PRACTICE" | "QUALIFYING" | null>(null)

  // Evidence cards state
  const [evidenceCards, setEvidenceCards] = useState<EvidenceItem[]>([])

  // Race Brief state
  const [brief, setBrief] = useState<RaceBrief | null>(null)
  const [running, setRunning] = useState(false) // Replay or Live is running

  useEffect(() => {
    setRunning(isReplaying || isLiveMode);
  }, [isReplaying, isLiveMode]);

  // Polling for Race Brief
  useEffect(() => {
    if (!running) return
    let active = true
    const poll = async () => {
      try {
        const b = await getRaceBrief(sessionId, focusDriverCode || undefined)
        if (active) setBrief(b)
      } catch (e) {
        console.error("Failed to fetch race brief", e)
      }
    }
    poll()
    const id = setInterval(poll, 1500)
    return () => { active = false; clearInterval(id) }
  }, [sessionId, focusDriverCode, running])


  const addLog = useCallback((content: string, type: "status" | "user" | "model" | "tool", toolName?: string) => {
    setTranscript((prev) => [
      ...prev,
      { id: Date.now().toString() + "-" + (logId.current++), type, content, timestamp: new Date().toLocaleTimeString("en-GB"), toolName },
    ].slice(-50))
  }, [])

  const addEvidence = useCallback((card: EvidenceItem) => {
    setEvidenceCards(prev => [card, ...prev].slice(0, 50));
  }, []);

  // Callbacks
  const handleConnect = useCallback(async () => {
    if (!running) {
        addLog("Start replay or live mode first!", "status")
        return
    }
    setConnectionStatus("connecting")
    try {
        const player = new AudioPlayer()
        playerRef.current = player

        const client = new PitWallLiveClient(
            {
                onAudio: (b64) => player.play(b64),
                onTranscript: (text, role) => addLog(text, role === "model" ? "model" : "user"),
                onToolCall: (name, args) => addLog(`Running ${name}`, "tool", name),
                onToolResult: (name: string, args: Record<string, unknown>, result: unknown) => {
                    const res = result as Record<string, unknown>
                    const ts = res.timestamp_utc as string | undefined
                    if (name === "recommend_strategy") {
                        addEvidence({
                            id: `rs-voice-${Date.now()}`, type: "recommend_strategy", timestamp: ts ?? new Date().toISOString(),
                            data: res as unknown as RecommendStrategyResult, driver: (args.driver_code as string | undefined) ?? "?",
                        } as any)
                    } else if (name === "project_pit_rejoin") {
                        addEvidence({
                            id: `pr-voice-${Date.now()}`, type: "pit_rejoin", timestamp: ts ?? new Date().toISOString(),
                            data: res as unknown as PitRejoinResult, driver: (args.driver_code as string | undefined) ?? "?",
                        } as any)
                    } else if (name === "estimate_undercut") {
                        addEvidence({
                            id: `uc-voice-${Date.now()}`, type: "undercut", timestamp: ts ?? new Date().toISOString(),
                            data: res as unknown as UndercutResult, attacker: (args.attacker as string | undefined) ?? "?", defender: (args.defender as string | undefined) ?? "?",
                        } as any)
                    }
                },
                onStatus: (s) => {
                    setConnectionStatus(s === "connected" ? "connected" : s === "connecting" ? "connecting" : "disconnected")
                    addLog(s, "status")
                },
                onError: (err) => {
                    setConnectionStatus("disconnected")
                    addLog(err, "status")
                },
            },
            sessionId,
            focusDriverCode,
        )
        await client.connect()
        clientRef.current = client
    } catch (e) {
        setConnectionStatus("disconnected")
        addLog(`Connection failed: ${e instanceof Error ? e.message : e}`, "status")
    }
  }, [running, sessionId, focusDriverCode, addLog, addEvidence])

  const handleDisconnect = useCallback(() => {
    micRef.current?.stop()
    micRef.current = null
    setIsMicActive(false)
    playerRef.current?.stop()
    playerRef.current = null
    clientRef.current?.disconnect()
    clientRef.current = null
    setConnectionStatus("disconnected")
    addLog("Disconnected", "status")
  }, [addLog])

  const handleToggleMic = useCallback(async () => {
    if (isMicActive) {
      micRef.current?.stop()
      micRef.current = null
      setIsMicActive(false)
      addLog("Microphone muted", "status")
      return
    }
    try {
        const mic = new MicCapture()
        await mic.start((b64) => clientRef.current?.sendAudio(b64))
        micRef.current = mic
        setIsMicActive(true)
        addLog("Microphone enabled — speak now", "status")
    } catch (e) {
        addLog(`Mic error: ${e instanceof Error ? e.message : e}`, "status")
    }
  }, [isMicActive, addLog])

  const handleCreateSession = useCallback(async () => {
    try {
      await createSession(sessionId)
      addLog("Session created", "status")
    } catch(e) {
      addLog(`Failed to create session`, "status")
    }
  }, [sessionId, addLog])

  const handleToggleReplay = useCallback(async () => {
    if (isReplaying) {
      await stopReplay(sessionId)
      setIsReplaying(false)
    } else {
      await startReplay({ sessionId, ndjsonPath: replayPath, tickMs, loop: true })
      setIsReplaying(true)
    }
  }, [isReplaying, sessionId, replayPath, tickSpeed])

  const handleToggleLiveMode = useCallback(async () => {
    if (isLiveMode) {
      await stopLive(sessionId)
      setIsLiveMode(false)
    } else {
      await startLive(sessionId, liveSessionKey)
      setIsLiveMode(true)
      setTimeout(async () => {
          try {
              const st = await fetch(`http://localhost:8080/admin/live/status?session_id=${encodeURIComponent(sessionId)}`).then(r => r.json())
              if (st.session_type) setDetectedSessionType(st.session_type)
          } catch { /* ignore */ }
      }, 3000)
    }
  }, [isLiveMode, sessionId, liveSessionKey])

  const handleRunPitRejoin = useCallback(async (driver: string) => {
    try {
      const data = await projectPitRejoin(sessionId, driver)
      addEvidence({
          id: `pr-${Date.now()}`, type: "pit_rejoin",
          timestamp: data.timestamp_utc, data, driver,
      } as any)
    } catch (e) { console.error(e) }
  }, [sessionId, addEvidence])

  const handleRunUndercut = useCallback(async (attacker: string, defender: string, horizon: number) => {
    try {
      const data = await estimateUndercut(sessionId, attacker, defender, horizon)
      addEvidence({
          id: `uc-${Date.now()}`, type: "undercut",
          timestamp: data.timestamp_utc, data, attacker, defender,
      } as any)
    } catch (e) { console.error(e) }
  }, [sessionId, addEvidence])

  const handleRunStrategy = useCallback(async (driver: string) => {
    try {
      const data = await recommendStrategy(sessionId, driver)
      addEvidence({
          id: `rs-${Date.now()}`, type: "recommend_strategy",
          timestamp: data.timestamp_utc, data, driver,
      } as any)
    } catch (e) { console.error(e) }
  }, [sessionId, addEvidence])

  // Map API driver formats to what the UI expects
  const uiDrivers = brief ? brief.top5.map(d => ({
    position: d.position,
    code: d.driver_code,
    gap: d.gap_to_leader !== null ? `+${d.gap_to_leader.toFixed(1)}s` : "LEADER",
    tire: { compound: (d.tire_compound || "UNKNOWN") as "SOFT"|"MEDIUM"|"HARD"|"INTERMEDIATE"|"WET"|"UNKNOWN", age: d.tire_age || 0 }
  })) : []

  const uiFocusDriver = brief?.focus ? {
    code: brief.focus.driver_code,
    position: brief.focus.position,
    gapAhead: brief.focus.gap_ahead ? `-${brief.focus.gap_ahead.toFixed(1)}s` : "-",
    gapBehind: brief.focus.gap_behind ? `+${brief.focus.gap_behind.toFixed(1)}s` : "-",
    lastLap: brief.focus.last_lap_time ? brief.focus.last_lap_time.toFixed(3) : "-",
  } : null

  // Process evidence cards to match UI format
  // The UI EvidenceCardsPanel component expects certain props, we'll map them
  const mappedEvidenceCards = evidenceCards.map(c => {
    if (c.type === "strategy") {
      const data = c.data as RecommendStrategyResult
      return {
        id: c.id,
        type: "strategy" as const,
        driverCode: (c as any).driver,
        confidence: data.confidence as any,
        action: data.recommended_action as any,
        reasons: data.reasons,
        lap: brief?.lap || 0,
        timestamp: new Date(data.timestamp_utc).toLocaleTimeString("en-GB"),
        rawData: {},
      }
    } else if (c.type === "pit_rejoin") {
      const data = c.data as PitRejoinResult
      return {
        id: c.id,
        type: "pit_rejoin" as const,
        driverCode: (c as any).driver,
        projectedPosition: `P${data.projected_position}`,
        gapAhead: `${data.gap_ahead_s > 0 ? "+" : ""}${data.gap_ahead_s.toFixed(1)}s`,
        gapBehind: `${data.gap_behind_s > 0 ? "+" : ""}${data.gap_behind_s.toFixed(1)}s`,
        lap: brief?.lap || 0,
        timestamp: new Date(data.timestamp_utc).toLocaleTimeString("en-GB"),
        rawData: {},
      }
    } else if (c.type === "undercut") {
      const data = c.data as UndercutResult
      return {
        id: c.id,
        type: "undercut" as const,
        attacker: (c as any).attacker,
        defender: (c as any).defender,
        expectedGain: data.expected_gain_s,
        horizonLaps: data.horizon_laps,
        lap: brief?.lap || 0,
        timestamp: new Date(data.timestamp_utc).toLocaleTimeString("en-GB"),
        rawData: {},
      }
    }
    // fallback just in case
    return {} as any
  })

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-background">
      {/* Header */}
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-border/50 bg-card/50 px-6 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/20">
            <Flag className="h-4 w-4 text-primary" />
          </div>
          <h1 className="text-lg font-bold tracking-tight">F1 Strategy Dashboard</h1>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 rounded-full bg-secondary/50 px-3 py-1.5 font-mono text-xs">
            <span className={`h-2 w-2 rounded-full ${running ? "animate-pulse bg-red-500" : "bg-zinc-500"}`} />
            {isLiveMode ? "LIVE" : "REPLAY"}
          </div>
          <span className="font-mono text-sm text-muted-foreground">
            {brief?.timestamp_utc ? brief.timestamp_utc.slice(11, 19) : new Date().toLocaleTimeString("en-GB")} UTC
          </span>
        </div>
      </header>

      {/* Main Grid */}
      <main className="grid flex-1 grid-cols-1 gap-4 overflow-hidden p-4 lg:grid-cols-[320px_1fr_320px]">
        {/* Left Column - Race Brief */}
        <section className="overflow-hidden">
          <RaceBriefPanel
            lap={brief?.lap || 0}
            totalLaps={57}
            trackStatus={(brief?.track_status?.flag as any) || "GREEN"}
            timestamp={brief?.timestamp_utc ? brief.timestamp_utc.slice(11, 19) + " UTC" : "—"}
            drivers={uiDrivers}
            focusDriver={uiFocusDriver}
            focusDriverCode={focusDriverCode}
          />
        </section>

        {/* Center Column - Voice Agent + Map + Evidence */}
        <section className="flex flex-col gap-4 overflow-hidden">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 h-[50%] min-h-[320px]">
            <VoiceAgentPanel
              connectionStatus={connectionStatus}
              isMicActive={isMicActive}
              transcript={transcript}
              onConnect={handleConnect}
              onDisconnect={handleDisconnect}
              onToggleMic={handleToggleMic}
            />
            <DriverMap 
              sessionId={isLiveMode ? liveSessionKey : sessionId} 
              running={running} 
              focusDriverCode={focusDriverCode} 
            />
          </div>
          <div className="flex-1 overflow-hidden">
            <EvidenceCardsPanel cards={mappedEvidenceCards} />
          </div>
        </section>

        {/* Right Column - Controls */}
        <section className="overflow-hidden">
          <ControlsPanel
            sessionId={sessionId}
            onSessionIdChange={setSessionId}
            onCreateSession={handleCreateSession}
            replayPath={replayPath}
            onReplayPathChange={setReplayPath}
            tickSpeed={tickSpeed}
            onTickSpeedChange={setTickSpeed}
            isReplaying={isReplaying}
            onToggleReplay={handleToggleReplay}
            focusDriverCode={focusDriverCode}
            onFocusDriverChange={setFocusDriverCode}
            onRunPitRejoin={handleRunPitRejoin}
            onRunUndercut={handleRunUndercut}
            onRunStrategy={handleRunStrategy}
            liveSessionKey={liveSessionKey}
            onLiveSessionKeyChange={setLiveSessionKey}
            isLiveMode={isLiveMode}
            onToggleLiveMode={handleToggleLiveMode}
            detectedSessionType={detectedSessionType}
          />
        </section>
      </main>
    </div>
  )
}
