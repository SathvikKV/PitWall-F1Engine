"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import { cn } from "@/lib/utils"
import { Layers } from "lucide-react"

type ConfidenceLevel = "HIGH" | "MEDIUM" | "LOW"

interface StrategyRecommendation {
  id: string
  type: "strategy"
  driverCode: string
  confidence: ConfidenceLevel
  action: "PIT_NOW" | "STAY_OUT" | "BOX_NEXT_LAP"
  reasons: string[]
  lap: number
  timestamp: string
  rawData: Record<string, unknown>
}

interface UndercutAnalysis {
  id: string
  type: "undercut"
  attacker: string
  defender: string
  expectedGain: number
  horizonLaps: number
  lap: number
  timestamp: string
  rawData: Record<string, unknown>
}

interface PitRejoin {
  id: string
  type: "pit_rejoin"
  driverCode: string
  projectedPosition: string
  gapAhead: string
  gapBehind: string
  lap: number
  timestamp: string
  rawData: Record<string, unknown>
}

type EvidenceCard = StrategyRecommendation | UndercutAnalysis | PitRejoin

interface EvidenceCardsPanelProps {
  cards: EvidenceCard[]
}

const confidenceColors = {
  HIGH: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  MEDIUM: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  LOW: "bg-red-500/20 text-red-400 border-red-500/30",
}

const actionDisplay = {
  PIT_NOW: { icon: "🔴", text: "Pit Now", color: "text-red-400" },
  STAY_OUT: { icon: "🟢", text: "Stay Out", color: "text-emerald-400" },
  BOX_NEXT_LAP: { icon: "🟡", text: "Box Next Lap", color: "text-yellow-400" },
}

export function EvidenceCardsPanel({ cards }: EvidenceCardsPanelProps) {
  if (cards.length === 0) {
    return (
      <Card className="flex h-full flex-col border-border/50 bg-card/80 backdrop-blur-sm">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg font-semibold tracking-tight">
            <Layers className="h-5 w-5 text-muted-foreground" />
            Evidence Cards
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-1 items-center justify-center">
          <p className="text-center text-muted-foreground">
            Run a tool to see results here.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="flex h-full flex-col border-border/50 bg-card/80 backdrop-blur-sm">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg font-semibold tracking-tight">
            <Layers className="h-5 w-5 text-muted-foreground" />
            Evidence Cards
          </CardTitle>
          <Badge variant="outline" className="border-border/50 font-mono">
            {cards.length}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="flex-1 overflow-hidden pt-0">
        <ScrollArea className="h-full pr-2">
          <Accordion type="multiple" className="space-y-3">
            {cards.map((card) => (
              <EvidenceCardItem key={card.id} card={card} />
            ))}
          </Accordion>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}

function EvidenceCardItem({ card }: { card: EvidenceCard }) {
  switch (card.type) {
    case "strategy":
      return <StrategyCard card={card} />
    case "undercut":
      return <UndercutCard card={card} />
    case "pit_rejoin":
      return <PitRejoinCard card={card} />
  }
}

function StrategyCard({ card }: { card: StrategyRecommendation }) {
  const action = actionDisplay[card.action]
  return (
    <AccordionItem
      value={card.id}
      className="overflow-hidden rounded-lg border border-border/30 bg-zinc-900/50"
    >
      <AccordionTrigger className="px-4 py-3 hover:no-underline [&[data-state=open]]:border-b [&[data-state=open]]:border-border/30">
        <div className="flex w-full items-center justify-between pr-2">
          <div className="flex items-center gap-3">
            <span className="font-mono text-base font-bold text-foreground">
              {card.driverCode}
            </span>
            <span className="text-sm text-muted-foreground">Strategy Rec</span>
          </div>
          <Badge
            variant="outline"
            className={cn("text-xs", confidenceColors[card.confidence])}
          >
            {card.confidence}
          </Badge>
        </div>
      </AccordionTrigger>
      <AccordionContent className="px-4 pb-4 pt-3">
        <div className="space-y-4">
          <div className={cn("text-2xl font-bold", action.color)}>
            {action.icon} {action.text}
          </div>
          <ul className="space-y-1.5 text-sm">
            {card.reasons.map((reason, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-muted-foreground">•</span>
                <span className="text-foreground/80">{reason}</span>
              </li>
            ))}
          </ul>
          <RawDataSection data={card.rawData} lap={card.lap} timestamp={card.timestamp} />
        </div>
      </AccordionContent>
    </AccordionItem>
  )
}

function UndercutCard({ card }: { card: UndercutAnalysis }) {
  const isPositive = card.expectedGain > 0
  return (
    <AccordionItem
      value={card.id}
      className="overflow-hidden rounded-lg border border-border/30 bg-zinc-900/50"
    >
      <AccordionTrigger className="px-4 py-3 hover:no-underline [&[data-state=open]]:border-b [&[data-state=open]]:border-border/30">
        <div className="flex w-full items-center justify-between pr-2">
          <div className="flex items-center gap-3">
            <span className="font-mono text-base font-bold text-foreground">
              {card.attacker}
            </span>
            <span className="text-muted-foreground">vs</span>
            <span className="font-mono text-base font-bold text-foreground">
              {card.defender}
            </span>
            <span className="text-sm text-muted-foreground">Undercut</span>
          </div>
        </div>
      </AccordionTrigger>
      <AccordionContent className="px-4 pb-4 pt-3">
        <div className="space-y-4">
          <div className="flex items-baseline gap-4">
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">Expected Gain</p>
              <p
                className={cn(
                  "font-mono text-3xl font-bold",
                  isPositive ? "text-emerald-400" : "text-red-400"
                )}
              >
                {isPositive ? "+" : ""}
                {card.expectedGain.toFixed(1)}s
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">Horizon</p>
              <p className="font-mono text-lg font-semibold text-foreground">
                {card.horizonLaps} laps
              </p>
            </div>
          </div>
          <RawDataSection data={card.rawData} lap={card.lap} timestamp={card.timestamp} />
        </div>
      </AccordionContent>
    </AccordionItem>
  )
}

function PitRejoinCard({ card }: { card: PitRejoin }) {
  return (
    <AccordionItem
      value={card.id}
      className="overflow-hidden rounded-lg border border-border/30 bg-zinc-900/50"
    >
      <AccordionTrigger className="px-4 py-3 hover:no-underline [&[data-state=open]]:border-b [&[data-state=open]]:border-border/30">
        <div className="flex w-full items-center justify-between pr-2">
          <div className="flex items-center gap-3">
            <span className="font-mono text-base font-bold text-foreground">
              {card.driverCode}
            </span>
            <span className="text-sm text-muted-foreground">Pit Rejoin</span>
          </div>
        </div>
      </AccordionTrigger>
      <AccordionContent className="px-4 pb-4 pt-3">
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">Projected Pos</p>
              <p className="font-mono text-2xl font-bold text-foreground">
                {card.projectedPosition}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">Gap Ahead</p>
              <p className="font-mono text-lg font-semibold text-red-400">
                {card.gapAhead}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">Gap Behind</p>
              <p className="font-mono text-lg font-semibold text-emerald-400">
                +{card.gapBehind}
              </p>
            </div>
          </div>
          <RawDataSection data={card.rawData} lap={card.lap} timestamp={card.timestamp} />
        </div>
      </AccordionContent>
    </AccordionItem>
  )
}

function RawDataSection({
  data,
  lap,
  timestamp,
}: {
  data: Record<string, unknown>
  lap: number
  timestamp: string
}) {
  return (
    <div className="space-y-2 rounded-md border border-border/20 bg-zinc-950/50 p-3">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>Lap {lap}</span>
        <span className="font-mono">{timestamp}</span>
      </div>
      <pre className="overflow-x-auto font-mono text-xs text-muted-foreground">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  )
}
