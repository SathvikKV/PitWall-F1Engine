"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  Play,
  Square,
  Plus,
  Settings,
  Zap,
  Brain,
  ArrowRightLeft,
  Timer,
  Radio,
} from "lucide-react"

type SessionType = "RACE" | "PRACTICE" | "QUALIFYING" | null

interface ControlsPanelProps {
  // Replay Controls
  replayPath: string
  onReplayPathChange: (value: string) => void
  playbackSpeed: number
  onPlaybackSpeedChange: (value: number) => void
  isReplaying: boolean
  onToggleReplay: () => void
  // Focus Driver
  focusDriverCode: string
  onFocusDriverChange: (value: string) => void
  // Tool Forms
  onRunPitRejoin: (driver: string) => void
  onRunUndercut: (attacker: string, defender: string, horizon: number) => void
  onRunStrategy: (driver: string) => void
  // Live Mode
  liveSessionKey: string
  onLiveSessionKeyChange: (value: string) => void
  isLiveMode: boolean
  onToggleLiveMode: () => void
  detectedSessionType: SessionType
  onJumpToLap: (lap: number) => void
}

export function ControlsPanel({
  replayPath,
  onReplayPathChange,
  playbackSpeed,
  onPlaybackSpeedChange,
  isReplaying,
  onToggleReplay,
  focusDriverCode,
  onFocusDriverChange,
  onRunPitRejoin,
  onRunUndercut,
  onRunStrategy,
  liveSessionKey,
  onLiveSessionKeyChange,
  isLiveMode,
  onToggleLiveMode,
  detectedSessionType,
  onJumpToLap,
}: ControlsPanelProps) {
  return (
    <ScrollArea className="h-full pr-2">
      <div className="flex flex-col gap-4">
        {/* Replay Controls */}
        <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <Timer className="h-4 w-4" />
              REPLAY CONTROLS
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 pt-0">
            <div className="space-y-1.5">
              <label className="text-xs text-muted-foreground">NDJSON Path</label>
              <Select value={replayPath} onValueChange={onReplayPathChange}>
                <SelectTrigger className="h-9 border-border/50 bg-zinc-950/50 font-mono text-sm">
                  <SelectValue placeholder="Select replay..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="data/replay/aus_2024_r.ndjson">aus_2024_r.ndjson</SelectItem>
                  <SelectItem value="data/replay/china_2024_r.ndjson">china_2024_r.ndjson</SelectItem>
                  <SelectItem value="data/replay/aus_2025_r.ndjson">aus_2025_r.ndjson</SelectItem>
                  <SelectItem value="data/replay/aus_2026_r.ndjson">aus_2026_r.ndjson</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs text-muted-foreground">
                Playback Speed (x)
              </label>
              <Input
                type="number"
                value={playbackSpeed}
                onChange={(e) => onPlaybackSpeedChange(Number(e.target.value))}
                min={0.1}
                max={100}
                step={0.1}
                className="h-9 border-border/50 bg-zinc-950/50 font-mono text-sm"
              />
            </div>
            <Button
              onClick={onToggleReplay}
              variant={isReplaying ? "destructive" : "default"}
              className={cn("w-full", isReplaying && "bg-red-600 hover:bg-red-500")}
            >
              {isReplaying ? (
                <>
                  <Square className="mr-2 h-4 w-4" />
                  Stop Replay
                </>
              ) : (
                <>
                  <Play className="mr-2 h-4 w-4" />
                  Start Replay
                </>
              )}
            </Button>

            {isReplaying && (
              <div className="flex flex-col gap-1.5 pt-1 border-t border-border/20">
                <label className="text-xs text-muted-foreground">Jump to Lap</label>
                <form 
                  onSubmit={(e) => {
                    e.preventDefault();
                    const formData = new FormData(e.currentTarget);
                    const lap = Number(formData.get("lap"));
                    if (lap > 0) onJumpToLap(lap);
                  }}
                  className="flex gap-2"
                >
                  <Input
                    name="lap"
                    type="number"
                    placeholder="Lap #"
                    className="h-8 border-border/50 bg-zinc-950/50 font-mono text-sm"
                  />
                  <Button type="submit" size="sm" variant="secondary" className="h-8 shrink-0">
                    Jump
                  </Button>
                </form>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Focus Driver */}
        <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <Zap className="h-4 w-4" />
              FOCUS DRIVER
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <Input
              value={focusDriverCode}
              onChange={(e) =>
                onFocusDriverChange(e.target.value.toUpperCase().slice(0, 3))
              }
              placeholder="NOR"
              maxLength={3}
              className="h-9 border-border/50 bg-zinc-950/50 text-center font-mono text-lg font-bold uppercase tracking-widest"
            />
          </CardContent>
        </Card>

        {/* Manual Tool Forms */}
        <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              MANUAL TOOLS
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 pt-0">
            {/* Pit Rejoin Tool */}
            <ToolFieldset
              title="Pit Rejoin"
              icon={<ArrowRightLeft className="h-3.5 w-3.5" />}
            >
              <PitRejoinForm onSubmit={onRunPitRejoin} />
            </ToolFieldset>

            {/* Undercut Tool */}
            <ToolFieldset
              title="Undercut"
              icon={<ArrowRightLeft className="h-3.5 w-3.5" />}
            >
              <UndercutForm onSubmit={onRunUndercut} />
            </ToolFieldset>

            {/* Strategy Tool */}
            <ToolFieldset
              title="Strategy"
              icon={<Brain className="h-3.5 w-3.5" />}
            >
              <StrategyForm onSubmit={onRunStrategy} />
            </ToolFieldset>
          </CardContent>
        </Card>

        {/* Live Mode */}
        <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <Radio className="h-4 w-4" />
                LIVE MODE
              </CardTitle>
              {detectedSessionType && (
                <Badge
                  variant="outline"
                  className={cn(
                    "font-mono text-xs",
                    detectedSessionType === "RACE" &&
                      "border-red-500/30 bg-red-500/10 text-red-400",
                    detectedSessionType === "QUALIFYING" &&
                      "border-yellow-500/30 bg-yellow-500/10 text-yellow-400",
                    detectedSessionType === "PRACTICE" &&
                      "border-blue-500/30 bg-blue-500/10 text-blue-400"
                  )}
                >
                  {detectedSessionType}
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-3 pt-0">
            <div className="space-y-1.5">
              <label className="text-xs text-muted-foreground">Session Key</label>
              <Input
                value={liveSessionKey}
                onChange={(e) => onLiveSessionKeyChange(e.target.value)}
                placeholder="live-key-xxx"
                className="h-9 border-border/50 bg-zinc-950/50 font-mono text-sm"
              />
            </div>
            <Button
              onClick={onToggleLiveMode}
              variant={isLiveMode ? "destructive" : "default"}
              className={cn(
                "w-full",
                isLiveMode
                  ? "bg-red-600 hover:bg-red-500"
                  : "bg-emerald-600 hover:bg-emerald-500"
              )}
            >
              {isLiveMode ? (
                <>
                  <Square className="mr-2 h-4 w-4" />
                  Stop Live Mode
                </>
              ) : (
                <>
                  <Radio className="mr-2 h-4 w-4" />
                  Start Live Mode
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      </div>
    </ScrollArea>
  )
}

function ToolFieldset({
  title,
  icon,
  children,
}: {
  title: string
  icon: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <fieldset className="space-y-2 rounded-lg border border-border/30 bg-zinc-950/30 p-3">
      <legend className="flex items-center gap-1.5 px-1 text-xs font-medium text-muted-foreground">
        {icon}
        {title}
      </legend>
      {children}
    </fieldset>
  )
}

function PitRejoinForm({ onSubmit }: { onSubmit: (driver: string) => void }) {
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    const driver = formData.get("driver") as string
    if (driver) {
      onSubmit(driver.toUpperCase())
      e.currentTarget.reset()
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <Input
        name="driver"
        placeholder="NOR"
        maxLength={3}
        className="h-8 border-border/30 bg-zinc-950/50 text-center font-mono text-sm uppercase"
      />
      <Button type="submit" size="sm" variant="secondary" className="shrink-0">
        Run
      </Button>
    </form>
  )
}

function UndercutForm({
  onSubmit,
}: {
  onSubmit: (attacker: string, defender: string, horizon: number) => void
}) {
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    const attacker = formData.get("attacker") as string
    const defender = formData.get("defender") as string
    const horizon = Number(formData.get("horizon")) || 5
    if (attacker && defender) {
      onSubmit(attacker.toUpperCase(), defender.toUpperCase(), horizon)
      e.currentTarget.reset()
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      <div className="flex gap-2">
        <Input
          name="attacker"
          placeholder="ATK"
          maxLength={3}
          className="h-8 border-border/30 bg-zinc-950/50 text-center font-mono text-sm uppercase"
        />
        <Input
          name="defender"
          placeholder="DEF"
          maxLength={3}
          className="h-8 border-border/30 bg-zinc-950/50 text-center font-mono text-sm uppercase"
        />
        <Input
          name="horizon"
          type="number"
          placeholder="5"
          defaultValue={5}
          min={1}
          max={20}
          className="h-8 w-16 border-border/30 bg-zinc-950/50 text-center font-mono text-sm"
        />
      </div>
      <Button type="submit" size="sm" variant="secondary" className="w-full">
        Run Undercut
      </Button>
    </form>
  )
}

function StrategyForm({ onSubmit }: { onSubmit: (driver: string) => void }) {
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    const driver = formData.get("driver") as string
    if (driver) {
      onSubmit(driver.toUpperCase())
      e.currentTarget.reset()
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <Input
        name="driver"
        placeholder="NOR"
        maxLength={3}
        className="h-8 border-border/30 bg-zinc-950/50 text-center font-mono text-sm uppercase"
      />
      <Button
        type="submit"
        size="sm"
        className="shrink-0 bg-primary/90 hover:bg-primary"
      >
        <Brain className="mr-1 h-3.5 w-3.5" />
        Recommend
      </Button>
    </form>
  )
}
