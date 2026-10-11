"use client";

import { Pause, Play } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { formatDuration } from "@/lib/format";

/** Minimal player to listen back to the device recording before sending it. */
export function AudioPlayer({ src, fallbackDuration }: { src: string; fallbackDuration: number }) {
  const ref = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [time, setTime] = useState(0);
  const [duration, setDuration] = useState(fallbackDuration);

  useEffect(() => {
    const a = ref.current;
    if (!a) return;
    const onTime = () => setTime(a.currentTime);
    const onMeta = () => {
      if (Number.isFinite(a.duration) && a.duration > 0) setDuration(a.duration);
    };
    const onEnd = () => {
      setPlaying(false);
      setTime(0);
    };
    a.addEventListener("timeupdate", onTime);
    a.addEventListener("loadedmetadata", onMeta);
    a.addEventListener("ended", onEnd);
    a.addEventListener("pause", () => setPlaying(false));
    a.addEventListener("play", () => setPlaying(true));
    return () => {
      a.removeEventListener("timeupdate", onTime);
      a.removeEventListener("loadedmetadata", onMeta);
      a.removeEventListener("ended", onEnd);
    };
  }, []);

  const toggle = () => {
    const a = ref.current;
    if (!a) return;
    if (a.paused) a.play().catch(() => setPlaying(false));
    else a.pause();
  };

  const pct = duration > 0 ? Math.min(100, (time / duration) * 100) : 0;

  return (
    <div className="player">
      <audio ref={ref} src={src} preload="metadata" />
      <button type="button" className="player-btn" onClick={toggle} aria-label={playing ? "Mettre en pause la réécoute" : "Réécouter l'enregistrement"}>
        {playing ? <Pause size={20} strokeWidth={1.75} aria-hidden /> : <Play size={20} strokeWidth={1.75} aria-hidden />}
      </button>
      <div
        className="player-track"
        role="progressbar"
        aria-label="Progression de la réécoute"
        aria-valuemin={0}
        aria-valuemax={Math.round(duration)}
        aria-valuenow={Math.round(time)}
        aria-valuetext={`${formatDuration(time)} sur ${formatDuration(duration)}`}
      >
        <div className="player-fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="player-time">{formatDuration(playing || time > 0 ? time : duration)}</span>
    </div>
  );
}
