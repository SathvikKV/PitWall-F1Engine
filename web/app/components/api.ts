/* ── Backend API integration layer ── */

const BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8080";

async function request<T>(path: string, opts: RequestInit = {}): Promise<T> {
    const res = await fetch(`${BASE}${path}`, {
        headers: { "Content-Type": "application/json", ...opts.headers as Record<string, string> },
        ...opts,
    });
    if (!res.ok) {
        const body = await res.json().catch(() => null);
        const msg =
            body?.detail?.message || body?.detail?.error || body?.detail || res.statusText;
        throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
    }
    return res.json();
}

/* ── Admin ─────────────────────────────────────────────────────────────── */

export function createSession(sessionId: string) {
    return request("/admin/session/create", {
        method: "POST",
        body: JSON.stringify({ session_id: sessionId }),
    });
}

export function startReplay(opts: {
    sessionId: string;
    ndjsonPath: string;
    tickMs: number;
    loop: boolean;
}) {
    return request("/admin/replay/start", {
        method: "POST",
        body: JSON.stringify({
            session_id: opts.sessionId,
            ndjson_path: opts.ndjsonPath,
            tick_ms: opts.tickMs,
            loop: opts.loop,
        }),
    });
}

export function stopReplay(sessionId: string) {
    return request("/admin/replay/stop", {
        method: "POST",
        body: JSON.stringify({ session_id: sessionId }),
    });
}

/* ── Agent ─────────────────────────────────────────────────────────────── */

import type { RaceBrief, PitRejoinResult, UndercutResult } from "./types";

export function getRaceBrief(sessionId: string, focusDriver?: string) {
    return request<RaceBrief>("/agent/race_brief", {
        method: "POST",
        body: JSON.stringify({
            session_id: sessionId,
            focus_driver: focusDriver || null,
        }),
    });
}

/* ── Tools ─────────────────────────────────────────────────────────────── */

export function projectPitRejoin(sessionId: string, driverCode: string) {
    return request<PitRejoinResult>("/tools/project_pit_rejoin", {
        method: "POST",
        body: JSON.stringify({ session_id: sessionId, driver_code: driverCode }),
    });
}

export function estimateUndercut(
    sessionId: string,
    attacker: string,
    defender: string,
    horizonLaps: number,
) {
    return request<UndercutResult>("/tools/estimate_undercut", {
        method: "POST",
        body: JSON.stringify({
            session_id: sessionId,
            attacker,
            defender,
            horizon_laps: horizonLaps,
        }),
    });
}
