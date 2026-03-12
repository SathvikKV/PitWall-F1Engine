/**
 * Browser audio utilities for Gemini Live API.
 *
 * - MicCapture: captures microphone → PCM 16-bit 16kHz mono → base64
 * - AudioPlayer: plays PCM 16-bit 24kHz mono from base64 chunks
 */

/* ── Mic capture ──────────────────────────────────────────────────────── */

export class MicCapture {
    private stream: MediaStream | null = null;
    private ctx: AudioContext | null = null;
    private processor: ScriptProcessorNode | null = null;
    private source: MediaStreamAudioSourceNode | null = null;

    async start(onChunk: (b64: string) => void) {
        this.stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                sampleRate: 16000, channelCount: 1, echoCancellation: true,
                noiseSuppression: true, autoGainControl: true
            },
        });

        this.ctx = new AudioContext({ sampleRate: 16000 });
        this.source = this.ctx.createMediaStreamSource(this.stream);

        // ScriptProcessor for raw PCM access (deprecated but universally supported)
        this.processor = this.ctx.createScriptProcessor(4096, 1, 1);
        this.processor.onaudioprocess = (e) => {
            const float32 = e.inputBuffer.getChannelData(0);
            const int16 = float32ToInt16(float32);
            const b64 = arrayBufferToBase64(int16.buffer as ArrayBuffer);
            onChunk(b64);
        };

        this.source.connect(this.processor);
        this.processor.connect(this.ctx.destination);
    }

    stop() {
        this.processor?.disconnect();
        this.source?.disconnect();
        this.ctx?.close();
        this.stream?.getTracks().forEach((t) => t.stop());
        this.processor = null;
        this.source = null;
        this.ctx = null;
        this.stream = null;
    }
}

function float32ToInt16(f32: Float32Array): Int16Array {
    const out = new Int16Array(f32.length);
    for (let i = 0; i < f32.length; i++) {
        const s = Math.max(-1, Math.min(1, f32[i]));
        out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return out;
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
    const bytes = new Uint8Array(buffer);
    let binary = "";
    for (let i = 0; i < bytes.byteLength; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
}

/* ── Audio player ─────────────────────────────────────────────────────── */

export class AudioPlayer {
    private ctx: AudioContext | null = null;
    private nextTime = 0;

    play(pcmBase64: string) {
        if (!this.ctx) this.ctx = new AudioContext({ sampleRate: 24000 });
        const ctx = this.ctx;

        const binary = atob(pcmBase64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
        const int16 = new Int16Array(bytes.buffer);

        // Convert to float32 for Web Audio API
        const float32 = new Float32Array(int16.length);
        for (let i = 0; i < int16.length; i++) {
            float32[i] = int16[i] / 32768;
        }

        const buf = ctx.createBuffer(1, float32.length, 24000);
        buf.copyToChannel(float32, 0);

        const src = ctx.createBufferSource();
        src.buffer = buf;
        src.connect(ctx.destination);

        // Schedule seamlessly
        const when = Math.max(ctx.currentTime, this.nextTime);
        src.start(when);
        this.nextTime = when + buf.duration;
    }

    stop() {
        this.nextTime = 0;
        if (this.ctx) {
            this.ctx.close();
            this.ctx = null;
        }
    }
}
