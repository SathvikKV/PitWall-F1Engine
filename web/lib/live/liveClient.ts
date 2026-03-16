/**
 * Gemini Live API client for browser.
 *
 * Uses @google/genai SDK with ephemeral tokens for secure client-side
 * WebSocket connections. Handles audio streaming, function calling, and
 * interruption events.
 */

import { GoogleGenAI, Modality } from "@google/genai";

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8080";
const MODEL = "gemini-2.5-flash-native-audio-latest";

/* ── Types ─────────────────────────────────────────────────────────────── */

export interface ToolDef {
    name: string;
    description: string;
    input_schema: Record<string, unknown>;
}

export interface LiveCallbacks {
    onAudio: (pcm16b64: string) => void;
    onTranscript: (text: string, role: "model" | "user") => void;
    onToolCall: (name: string, args: Record<string, unknown>) => void;
    onToolResult: (name: string, args: Record<string, unknown>, result: unknown) => void;
    onStatus: (status: string) => void;
    onError: (err: string) => void;
}

/* ── Tool routing ──────────────────────────────────────────────────────── */

const TOOL_TO_ENDPOINT: Record<string, string> = {
    resolve_driver: "/tools/resolve_driver",
    get_race_context: "/tools/get_race_context",
    project_pit_rejoin: "/tools/project_pit_rejoin",
    estimate_undercut: "/tools/estimate_undercut",
    recommend_strategy: "/tools/recommend_strategy",
};

async function callBackendTool(name: string, args: Record<string, unknown>): Promise<unknown> {
    const path = TOOL_TO_ENDPOINT[name];
    if (!path) return { error: `Unknown tool: ${name}` };
    const res = await fetch(`${BACKEND}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(args),
    });
    return res.json();
}

/* ── Live client class ─────────────────────────────────────────────────── */

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type LiveSession = any;

export class PitWallLiveClient {
    private session: LiveSession | null = null;
    private cb: LiveCallbacks;
    private sessionId: string;
    private focusDriver: string;
    private heartbeatId: ReturnType<typeof setInterval> | null = null;

    constructor(cb: LiveCallbacks, sessionId: string, focusDriver: string) {
        this.cb = cb;
        this.sessionId = sessionId;
        this.focusDriver = focusDriver;
    }

    async connect() {
        this.cb.onStatus("minting_token");

        // 1. Mint ephemeral token
        const tokenRes = await fetch(`${BACKEND}/agent/ephemeral_token`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ttl_seconds: 900, session_id: this.sessionId }),
        });
        if (!tokenRes.ok) throw new Error("Failed to get ephemeral token");
        const { token } = await tokenRes.json();

        // 2. Fetch tool definitions + system prompt
        const [toolsRes, promptRes] = await Promise.all([
            fetch(`${BACKEND}/agent/tools`),
            fetch(`${BACKEND}/agent/system_prompt`),
        ]);
        const { tools: rawTools } = await toolsRes.json();
        const { prompt: systemPrompt } = await promptRes.json();

        // 3. Convert tools to Gemini function declarations
        const functionDeclarations = rawTools.map((t: ToolDef) => ({
            name: t.name,
            description: t.description,
            parameters: t.input_schema,
        }));

        // 4. Connect to Gemini Live
        this.cb.onStatus("connecting");
        const ai = new GoogleGenAI({
            apiKey: token,
            apiVersion: "v1alpha",
            httpOptions: { apiVersion: "v1alpha" },
        } as any);
        const self = this;

        // Debug: log what the SDK sees
        console.log("[PitWall] SDK apiVersion check:", {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            sdkApiVersion: (ai as any).apiVersion,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            clientApiVersion: (ai as any).apiClient?.getApiVersion?.(),
            model: MODEL,
        });
        this.session = await ai.live.connect({
            model: MODEL,
            config: {
                responseModalities: [Modality.AUDIO],
                systemInstruction: systemPrompt,
                tools: [{ functionDeclarations }],
            },
            callbacks: {
                onopen() { self.cb.onStatus("connected"); },
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                onmessage(message: any) { self.handleMessage(message); },
                onerror(e: any) {
                    const msg = e?.message || e?.reason || (e instanceof Event ? `WebSocket error (type=${e.type})` : String(e));
                    self.cb.onError(msg);
                },
                onclose(e: any) {
                    const code = e?.code ?? "?";
                    const reason = e?.reason ?? "";
                    self.cb.onError(`closed: code=${code} reason=${reason}`);
                    self.cb.onStatus("disconnected");
                },
            },
        });

        // 5. Start race brief heartbeat
        this.startHeartbeat();
    }

    private handleMessage(msg: Record<string, unknown>) {
        // Tool call
        const toolCall = msg.toolCall as { functionCalls?: Array<{ id: string; name: string; args: Record<string, unknown> }> } | undefined;
        if (toolCall?.functionCalls) {
            this.handleToolCalls(toolCall.functionCalls);
            return;
        }

        // Server content
        const sc = msg.serverContent as {
            interrupted?: boolean;
            modelTurn?: { parts?: Array<{ text?: string; inlineData?: { data: string } }> };
            turnComplete?: boolean;
        } | undefined;

        if (sc?.interrupted) {
            this.cb.onStatus("interrupted");
            return;
        }

        if (sc?.modelTurn?.parts) {
            for (const part of sc.modelTurn.parts) {
                if (part.inlineData?.data) {
                    this.cb.onAudio(part.inlineData.data);
                }
                if (part.text) {
                    this.cb.onTranscript(part.text, "model");
                }
            }
        }
    }

    private async handleToolCalls(calls: Array<{ id: string; name: string; args: Record<string, unknown> }>) {
        this.cb.onStatus("tool_calling");
        const functionResponses = [];

        for (const fc of calls) {
            this.cb.onToolCall(fc.name, fc.args);
            // Always inject the real session_id (model may hallucinate a placeholder)
            const args = { ...fc.args, session_id: this.sessionId };
            const result = await callBackendTool(fc.name, args);
            this.cb.onToolResult(fc.name, args, result);
            functionResponses.push({
                id: fc.id,
                name: fc.name,
                response: { result },
            });
        }

        if (this.session) {
            this.session.sendToolResponse({ functionResponses });
        }
        this.cb.onStatus("connected");
    }

    sendAudio(pcm16b64: string) {
        if (!this.session) return;
        this.session.sendRealtimeInput({
            audio: { data: pcm16b64, mimeType: "audio/pcm;rate=16000" },
        });
    }

    private startHeartbeat() {
        this.heartbeatId = setInterval(async () => {
            if (!this.session) return;
            try {
                const res = await fetch(`${BACKEND}/agent/race_brief`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ session_id: this.sessionId, focus_driver: this.focusDriver }),
                });
                if (!res.ok) return;
                const brief = await res.json();
                const ctx = `[SILENT_SYSTEM_UPDATE] Lap ${brief.lap}, flag ${brief.track_status?.flag}. ` +
                    `Top: ${brief.top5?.map((d: { driver_code: string; gap_to_leader: number }) => `${d.driver_code} +${d.gap_to_leader}s`).join(", ") ?? "n/a"}`;
                this.session.sendClientContent({
                    turns: [{ role: "user", parts: [{ text: ctx }] }],
                });
            } catch { /* ignore failures */ }
        }, 12000);
    }

    disconnect() {
        if (this.heartbeatId) { clearInterval(this.heartbeatId); this.heartbeatId = null; }
        if (this.session) { this.session.close(); this.session = null; }
        this.cb.onStatus("disconnected");
    }
}
