"use client";

import { useState } from "react";
import type { EvidenceItem } from "./components/types";
import RaceBriefPanel from "./components/RaceBriefPanel";
import ControlsPanel from "./components/ControlsPanel";
import EvidencePanel from "./components/EvidencePanel";
import VoicePanel from "./components/VoicePanel";

export default function Home() {
  const [sessionId, setSessionId] = useState("replay_aus_2024_r");
  const [focusDriver, setFocusDriver] = useState("NOR");
  const [running, setRunning] = useState(false);
  const [evidence, setEvidence] = useState<EvidenceItem[]>([]);

  const addEvidence = (item: EvidenceItem) =>
    setEvidence((prev) => [item, ...prev].slice(0, 15));

  return (
    <main className="app-grid">
      <RaceBriefPanel sessionId={sessionId} focusDriver={focusDriver} running={running} />
      <div className="center-col">
        <VoicePanel sessionId={sessionId} focusDriver={focusDriver} running={running} />
        <EvidencePanel evidence={evidence} />
      </div>
      <ControlsPanel
        sessionId={sessionId} setSessionId={setSessionId}
        focusDriver={focusDriver} setFocusDriver={setFocusDriver}
        running={running} setRunning={setRunning}
        addEvidence={addEvidence}
      />
    </main>
  );
}

