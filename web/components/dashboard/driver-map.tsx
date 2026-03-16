"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { MapPin } from "lucide-react"

interface DriverLocation {
  driver_number: number
  driver_code?: string
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

const getTeamColor = (code?: string) => {
  if (!code) return "#ffffff";
  const c = code.toUpperCase();
  if (["VER", "PER"].includes(c)) return "#3671C6"; // Red Bull
  if (["LEC", "SAI", "BEA"].includes(c)) return "#E8002D"; // Ferrari
  if (["NOR", "PIA"].includes(c)) return "#FF8000"; // McLaren
  if (["HAM", "RUS"].includes(c)) return "#27F4D2"; // Mercedes
  if (["ALO", "STR"].includes(c)) return "#229971"; // Aston Martin
  if (["GAS", "OCO"].includes(c)) return "#0093cc"; // Alpine
  if (["ALB", "SAR", "COL"].includes(c)) return "#37BEDD"; // Williams
  if (["RIC", "TSU", "LAW"].includes(c)) return "#6692FF"; // VCARB
  if (["BOT", "ZHO"].includes(c)) return "#52E252"; // Sauber
  if (["MAG", "HUL"].includes(c)) return "#B6BABD"; // Haas
  return "#ffffff";
}

export function DriverMap({ sessionId, running, focusDriverCode }: DriverMapProps) {
  const [locations, setLocations] = useState<DriverLocation[]>([])
  const [trackLayout, setTrackLayout] = useState<{x: number, y: number}[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    if (!sessionId) return

    // Fetch track outline map - re-fetch if session or running state changes
    fetch(`/api/proxy/admin/live/track-layout?session_key=${sessionId}`)
      .then(res => res.json())
      .then(data => {
        if (active && data.layout && data.layout.length > 0) {
          setTrackLayout(data.layout)
          console.log(`Loaded track layout for ${sessionId}: ${data.layout.length} points`)
        }
      })
      .catch(err => console.error("Track layout fetch error:", err))

    if (!running) return

    const poll = async () => {
      try {
        const res = await fetch(`/api/proxy/admin/live/locations?session_key=${sessionId}`);
        if (!res.ok) throw new Error("Failed to fetch locations")
        const data = await res.json()
        if (active && data.locations) {
          setLocations(data.locations)
          setError(null)
          
          // Self-healing: if track layout is empty but we have locations, try fetching layout again once
          if (trackLayout.length === 0) {
              fetch(`/api/proxy/admin/live/track-layout?session_key=${sessionId}`)
                .then(r => r.json())
                .then(d => { if (active && d.layout) setTrackLayout(d.layout) })
          }
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
  }, [sessionId, running, trackLayout.length])

  // Stabilize map bounds so the map doesn't drift as cars move
  const [mapBounds, setMapBounds] = useState({ minX: -5000, maxX: 5000, minY: -5000, maxY: 5000 })
  const [boundsLocked, setBoundsLocked] = useState(false)

  useEffect(() => {
    const padding = 2000 // Generous padding for labels/dots
    if (trackLayout.length > 0) {
      const bX = trackLayout.map(l => l.x)
      const bY = trackLayout.map(l => l.y)
      setMapBounds({
        minX: Math.min(...bX) - padding,
        maxX: Math.max(...bX) + padding,
        minY: Math.min(...bY) - padding,
        maxY: Math.max(...bY) + padding
      })
      setBoundsLocked(true)
    } else if (locations.length > 0 && !boundsLocked) {
      // Fallback: lock to the bounding box of the first batch of telemetry
      const bX = locations.map(l => l.x)
      const bY = locations.map(l => l.y)
      setMapBounds({
        minX: Math.min(...bX) - (padding * 2),
        maxX: Math.max(...bX) + (padding * 2),
        minY: Math.min(...bY) - (padding * 2),
        maxY: Math.max(...bY) + (padding * 2)
      })
      setBoundsLocked(true)
    }
  }, [trackLayout, locations, boundsLocked])

  const { minX, maxX, minY, maxY } = mapBounds
  const width = Math.max(maxX - minX, 1000)
  const height = Math.max(maxY - minY, 1000)

  return (
    <Card className="flex h-full flex-col border-border/50 bg-card/80 backdrop-blur-sm overflow-hidden">
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
              {trackLayout.length > 0 ? (
                <polyline 
                  points={trackLayout.map(p => `${p.x},${p.y}`).join(" ")}
                  stroke="rgba(255, 255, 255, 0.15)" 
                  strokeWidth={width * 0.005} 
                  fill="none" 
                  strokeLinejoin="round"
                />
              ) : (
                <ellipse 
                  cx="5000" 
                  cy="5000" 
                  rx="4000" 
                  ry="2000" 
                  stroke="rgba(255, 255, 255, 0.05)" 
                  strokeWidth="150" 
                  fill="none" 
                />
              )}
              {locations.map((loc: DriverLocation) => {
                const isFocus = loc.driver_code ? focusDriverCode === loc.driver_code : focusDriverCode?.includes(loc.driver_number.toString())
                const domKey = loc.driver_code || loc.driver_number
                return (
                  <g key={domKey}>
                    <circle
                      cx={loc.x}
                      cy={loc.y}
                      r={isFocus ? width * 0.02 : width * 0.012}
                      fill={getTeamColor(loc.driver_code)}
                      stroke={isFocus ? "#fbbf24" : "none"}
                      strokeWidth={isFocus ? width * 0.005 : 0}
                      className="transition-all duration-300"
                    />
                    <text
                      x={loc.x}
                      y={loc.y}
                      dy={width * 0.04}
                      dx={width * 0.015}
                      fontSize={width * 0.035}
                      fill={isFocus ? "#fbbf24" : "#e4e4e7"}
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
