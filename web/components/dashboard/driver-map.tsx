"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { MapPin } from "lucide-react"

interface DriverLocation {
  driver_number: number
  x: number
  y: number
  z: number
  date: string
}

interface DriverMapProps {
  sessionId: string
  running: boolean
  focusDriverCode?: string
}

export function DriverMap({ sessionId, running, focusDriverCode }: DriverMapProps) {
  const [locations, setLocations] = useState<DriverLocation[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!running || !sessionId) return
    let active = true

    const poll = async () => {
      try {
        const res = await fetch(`http://localhost:8080/admin/live/locations?session_key=${sessionId === "latest" ? "latest" : "latest"}`); // We use session_key=latest or we could map sessionId to session_key. FastF1 backend defaults to latest.
        if (!res.ok) throw new Error("Failed to fetch locations")
        const data = await res.json()
        if (active && data.locations) {
          setLocations(data.locations)
          setError(null)
        }
      } catch (err: any) {
        if (active) setError(err.message)
      }
    }

    poll()
    const id = setInterval(poll, 1000)
    return () => {
      active = false
      clearInterval(id)
    }
  }, [sessionId, running])

  // Normalization for track map drawing
  // F1 tracks roughly fit in 10000x10000 range. We auto-scale to an SVG viewBox
  const padding = 500
  let minX = 0, maxX = 10000, minY = 0, maxY = 10000
  
  if (locations.length > 0) {
    minX = Math.min(...locations.map((l: DriverLocation) => l.x)) - padding
    maxX = Math.max(...locations.map((l: DriverLocation) => l.x)) + padding
    minY = Math.min(...locations.map((l: DriverLocation) => l.y)) - padding
    maxY = Math.max(...locations.map((l: DriverLocation) => l.y)) + padding
  }

  const width = Math.max(maxX - minX, 1000)
  const height = Math.max(maxY - minY, 1000)

  return (
    <Card className="flex h-full flex-col border-border/50 bg-card/80 backdrop-blur-sm">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-red-500/20">
            <MapPin className="h-4 w-4 text-red-500" />
          </div>
          <CardTitle className="text-lg font-semibold tracking-tight">
            Track Map
          </CardTitle>
          {error && <span className="text-xs text-red-400 ml-auto">{error}</span>}
        </div>
      </CardHeader>
      <CardContent className="flex-1 relative pb-4 overflow-hidden">
        <div className="w-full h-full bg-zinc-950/50 rounded-lg relative overflow-hidden flex items-center justify-center p-4">
          {locations.length === 0 ? (
            <div className="text-sm text-muted-foreground w-full text-center">
              Waiting for telemetry...
            </div>
          ) : (
            <svg
              viewBox={`${minX} ${minY} ${width} ${height}`}
              className="w-full h-full object-contain"
              style={{ transform: "scaleY(-1)" }} // SVG coordinates vs F1 coordinates usually differ in Y
            >
              {locations.map((loc: DriverLocation) => {
                const isFocus = focusDriverCode?.includes(loc.driver_number.toString()) // rudimentary check
                return (
                  <g key={loc.driver_number}>
                    <circle
                      cx={loc.x}
                      cy={loc.y}
                      r={isFocus ? width * 0.03 : width * 0.015}
                      fill={isFocus ? "#3b82f6" : "#ffffff"}
                      className="transition-all duration-300"
                    />
                    <text
                      x={loc.x}
                      y={loc.y}
                      dy={width * 0.05}
                      dx={width * 0.02}
                      fontSize={width * 0.05}
                      fill={isFocus ? "#3b82f6" : "#aaaaaa"}
                      style={{ transform: `scaleY(-1) translate(0, ${loc.y * -2}px)` }} // counter-scale text
                    >
                      {loc.driver_number}
                    </text>
                  </g>
                )
              })}
            </svg>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
