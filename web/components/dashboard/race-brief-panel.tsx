"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { cn } from "@/lib/utils"

interface Driver {
  position: number
  code: string
  gap: string
  tire: {
    compound: "SOFT" | "MEDIUM" | "HARD" | "INTER" | "WET"
    age: number
  }
}

interface FocusDriverStats {
  code: string
  position: number
  gapAhead: string
  gapBehind: string
  lastLap: string
}

interface RaceBriefPanelProps {
  lap: number
  totalLaps: number
  trackStatus: "GREEN" | "YELLOW" | "RED" | "SC" | "VSC"
  timestamp: string
  drivers: Driver[]
  focusDriver: FocusDriverStats | null
  focusDriverCode: string
}

const tireColors = {
  SOFT: "bg-red-500",
  MEDIUM: "bg-yellow-500",
  HARD: "bg-white",
  INTER: "bg-green-500",
  WET: "bg-blue-500",
}

const tireTextColors = {
  SOFT: "text-red-400",
  MEDIUM: "text-yellow-400",
  HARD: "text-zinc-200",
  INTER: "text-green-400",
  WET: "text-blue-400",
}

const statusColors = {
  GREEN: "bg-emerald-500 shadow-emerald-500/50",
  YELLOW: "bg-yellow-500 shadow-yellow-500/50",
  RED: "bg-red-500 shadow-red-500/50",
  SC: "bg-yellow-500 shadow-yellow-500/50",
  VSC: "bg-yellow-500 shadow-yellow-500/50",
}

const statusText = {
  GREEN: "Green Flag",
  YELLOW: "Yellow Flag",
  RED: "Red Flag",
  SC: "Safety Car",
  VSC: "Virtual SC",
}

export function RaceBriefPanel({
  lap,
  totalLaps,
  trackStatus,
  timestamp,
  drivers,
  focusDriver,
  focusDriverCode,
}: RaceBriefPanelProps) {
  return (
    <div className="flex h-full flex-col gap-4">
      {/* Header Section */}
      <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg font-semibold tracking-tight">
              Race Brief
            </CardTitle>
            <span className="font-mono text-xs text-muted-foreground">
              {timestamp}
            </span>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="flex items-center gap-6">
            <div className="flex items-baseline gap-2">
              <span className="font-mono text-3xl font-bold tracking-tighter">
                Lap {lap}
              </span>
              <span className="font-mono text-sm text-muted-foreground">
                / {totalLaps}
              </span>
            </div>
            <Badge
              variant="outline"
              className="flex items-center gap-2 border-border/50 bg-secondary/50 px-3 py-1.5"
            >
              <span
                className={cn(
                  "h-2.5 w-2.5 rounded-full shadow-[0_0_8px]",
                  statusColors[trackStatus]
                )}
              />
              <span className="font-medium">{statusText[trackStatus]}</span>
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Drivers Table */}
      <Card className="flex-1 border-border/50 bg-card/80 backdrop-blur-sm flex flex-col min-h-0">
        <CardHeader className="pb-3 shrink-0">
          <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
            DRIVER TIMINGS
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-0 flex-1 overflow-y-auto">
          <Table>
            <TableHeader>
              <TableRow className="border-border/30 hover:bg-transparent">
                <TableHead className="w-12 font-mono text-xs text-muted-foreground">
                  POS
                </TableHead>
                <TableHead className="font-mono text-xs text-muted-foreground">
                  DRIVER
                </TableHead>
                <TableHead className="text-right font-mono text-xs text-muted-foreground">
                  GAP
                </TableHead>
                <TableHead className="text-right font-mono text-xs text-muted-foreground">
                  TIRE
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {drivers.map((driver) => (
                <TableRow
                  key={driver.code}
                  className={cn(
                    "border-border/30 transition-colors",
                    driver.code === focusDriverCode &&
                      "bg-primary/10 hover:bg-primary/15"
                  )}
                >
                  <TableCell className="font-mono text-base font-bold">
                    P{driver.position}
                  </TableCell>
                  <TableCell
                    className={cn(
                      "font-mono text-base font-semibold tracking-wide",
                      driver.code === focusDriverCode && "text-primary"
                    )}
                  >
                    {driver.code}
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm">
                    {driver.gap}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <span
                        className={cn(
                          "h-2 w-2 rounded-full",
                          tireColors[driver.tire.compound]
                        )}
                      />
                      <span
                        className={cn(
                          "font-mono text-sm",
                          tireTextColors[driver.tire.compound]
                        )}
                      >
                        {driver.tire.compound.slice(0, 1)} ({driver.tire.age})
                      </span>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Focus Driver Stats */}
      {focusDriver && (
        <Card className="border-primary/30 bg-card/80 backdrop-blur-sm">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                FOCUS DRIVER
              </CardTitle>
              <Badge className="bg-primary/20 text-primary hover:bg-primary/30">
                {focusDriver.code}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Position</p>
                <p className="font-mono text-2xl font-bold">
                  P{focusDriver.position}
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Last Lap</p>
                <p className="font-mono text-2xl font-bold text-emerald-400">
                  {focusDriver.lastLap}
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Gap Ahead</p>
                <p className="font-mono text-lg font-semibold text-red-400">
                  {focusDriver.gapAhead}
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Gap Behind</p>
                <p className="font-mono text-lg font-semibold text-emerald-400">
                  +{focusDriver.gapBehind}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
