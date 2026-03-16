"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"
import { Mic, MicOff, Phone, PhoneOff, Wrench } from "lucide-react"

type ConnectionStatus = "disconnected" | "connecting" | "connected"

interface TranscriptEntry {
  id: string
  type: "user" | "model" | "status" | "tool"
  content: string
  timestamp: string
  toolName?: string
}

interface VoiceAgentPanelProps {
  connectionStatus: ConnectionStatus
  isMicActive: boolean
  transcript: TranscriptEntry[]
  onConnect: () => void
  onDisconnect: () => void
  onToggleMic: () => void
}

const statusColors = {
  disconnected: "bg-red-500 shadow-red-500/50",
  connecting: "bg-yellow-500 shadow-yellow-500/50 animate-pulse",
  connected: "bg-emerald-500 shadow-emerald-500/50",
}

const statusText = {
  disconnected: "Disconnected",
  connecting: "Connecting...",
  connected: "Connected",
}

export function VoiceAgentPanel({
  connectionStatus,
  isMicActive,
  transcript,
  onConnect,
  onDisconnect,
  onToggleMic,
}: VoiceAgentPanelProps) {
  return (
    <Card className="flex h-full flex-col border-border/50 bg-card/80 backdrop-blur-sm">
      {/* Connection Header */}
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span
              className={cn(
                "h-3 w-3 rounded-full shadow-[0_0_10px]",
                statusColors[connectionStatus]
              )}
            />
            <CardTitle className="text-lg font-semibold tracking-tight">
              Voice Agent
            </CardTitle>
          </div>
          <span className="text-sm text-muted-foreground">
            {statusText[connectionStatus]}
          </span>
        </div>
      </CardHeader>

      {/* Action Buttons */}
      <CardContent className="pb-3 pt-0">
        <div className="flex gap-2">
          {connectionStatus === "disconnected" ? (
            <Button
              onClick={onConnect}
              className="flex-1 bg-emerald-600 text-white hover:bg-emerald-500"
            >
              <Phone className="mr-2 h-4 w-4" />
              Connect Voice
            </Button>
          ) : (
            <>
              <Button
                onClick={onToggleMic}
                variant={isMicActive ? "destructive" : "default"}
                className={cn(
                  "flex-1",
                  isMicActive &&
                    "bg-red-600 text-white shadow-[0_0_15px_rgba(239,68,68,0.4)] hover:bg-red-500"
                )}
              >
                {isMicActive ? (
                  <>
                    <MicOff className="mr-2 h-4 w-4" />
                    Mute
                  </>
                ) : (
                  <>
                    <Mic className="mr-2 h-4 w-4" />
                    Start Mic
                  </>
                )}
              </Button>
              <Button
                onClick={onDisconnect}
                variant="outline"
                className="border-border/50 bg-secondary/50"
              >
                <PhoneOff className="mr-2 h-4 w-4" />
                Disconnect
              </Button>
            </>
          )}
        </div>
      </CardContent>

      {/* Transcript Log */}
      <CardContent className="flex flex-1 flex-col overflow-hidden pt-0">
        <div className="mb-2 text-xs font-medium text-muted-foreground">
          TRANSCRIPT
        </div>
        <ScrollArea className="flex-1 rounded-md border border-border/30 bg-zinc-950/50 p-3">
          <div className="space-y-2 font-mono text-sm">
            {transcript.length === 0 ? (
              <p className="text-center text-muted-foreground">
                Waiting for activity...
              </p>
            ) : (
              transcript.map((entry) => (
                <TranscriptItem key={entry.id} entry={entry} />
              ))
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}

function TranscriptItem({ entry }: { entry: TranscriptEntry }) {
  const typeStyles = {
    user: "border-l-blue-500 bg-blue-500/5",
    model: "border-l-emerald-500 bg-emerald-500/5",
    status: "border-l-yellow-500 bg-yellow-500/5",
    tool: "border-l-purple-500 bg-purple-500/5",
  }

  const typeLabels = {
    user: "YOU",
    model: "AI",
    status: "SYS",
    tool: "TOOL",
  }

  return (
    <div
      className={cn(
        "rounded-r border-l-2 px-3 py-2 transition-colors",
        typeStyles[entry.type]
      )}
    >
      <div className="mb-1 flex items-center justify-between">
        <span
          className={cn(
            "text-xs font-bold",
            entry.type === "user" && "text-blue-400",
            entry.type === "model" && "text-emerald-400",
            entry.type === "status" && "text-yellow-400",
            entry.type === "tool" && "text-purple-400"
          )}
        >
          {entry.type === "tool" && entry.toolName ? (
            <span className="flex items-center gap-1">
              <Wrench className="h-3 w-3" />
              {entry.toolName}
            </span>
          ) : (
            typeLabels[entry.type]
          )}
        </span>
        <span className="text-xs text-muted-foreground">{entry.timestamp}</span>
      </div>
      <p className="text-sm leading-relaxed text-foreground/90">
        {entry.content}
      </p>
    </div>
  )
}
