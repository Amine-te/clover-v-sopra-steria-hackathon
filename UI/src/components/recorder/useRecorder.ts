"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Real microphone capture with the MediaRecorder API, with explicit
 * permission states. Audio stays in memory on the device.
 */

export type RecorderStatus = "idle" | "requesting" | "recording" | "paused" | "stopped" | "denied" | "unsupported" | "error";

export const MAX_RECORDING_S = 180;

export interface RecorderResult {
  blob: Blob;
  url: string;
  durationS: number;
}

export function useRecorder() {
  const [status, setStatus] = useState<RecorderStatus>("idle");
  const [elapsed, setElapsed] = useState(0);
  const [levels, setLevels] = useState<number[]>(() => Array(28).fill(0.08));
  const [result, setResult] = useState<RecorderResult | null>(null);

  const mediaRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const ctxRef = useRef<AudioContext | null>(null);
  const rafRef = useRef<number | null>(null);
  const tickRef = useRef<number | null>(null);
  const startedRef = useRef(0);
  const accumulatedRef = useRef(0);
  const discardRef = useRef(false);

  const supported =
    typeof window !== "undefined" &&
    typeof navigator !== "undefined" &&
    !!navigator.mediaDevices?.getUserMedia &&
    typeof window.MediaRecorder !== "undefined";

  const cleanupStream = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    if (tickRef.current) window.clearInterval(tickRef.current);
    rafRef.current = null;
    tickRef.current = null;
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    ctxRef.current?.close().catch(() => undefined);
    ctxRef.current = null;
  }, []);

  useEffect(() => () => cleanupStream(), [cleanupStream]);

  const currentElapsed = () =>
    accumulatedRef.current + (startedRef.current ? (performance.now() - startedRef.current) / 1000 : 0);

  const stop = useCallback(() => {
    const m = mediaRef.current;
    if (m && m.state !== "inactive") m.stop();
  }, []);

  const start = useCallback(async () => {
    if (!supported) {
      setStatus("unsupported");
      return;
    }
    setStatus("requesting");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
      streamRef.current = stream;
      chunksRef.current = [];
      discardRef.current = false;
      accumulatedRef.current = 0;
      setResult(null);

      const recorder = new MediaRecorder(stream);
      mediaRef.current = recorder;
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        const durationS = Math.round(currentElapsed());
        startedRef.current = 0;
        cleanupStream();
        if (discardRef.current) {
          setStatus("idle");
          setElapsed(0);
          return;
        }
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        setResult({ blob, url: URL.createObjectURL(blob), durationS });
        setElapsed(durationS);
        setStatus("stopped");
      };

      // Live level meter (visual feedback only, nothing is analysed).
      try {
        const AC = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
        const ctx = new AC();
        ctxRef.current = ctx;
        const analyser = ctx.createAnalyser();
        analyser.fftSize = 256;
        ctx.createMediaStreamSource(stream).connect(analyser);
        const data = new Uint8Array(analyser.frequencyBinCount);
        let last = 0;
        const loop = (t: number) => {
          rafRef.current = requestAnimationFrame(loop);
          if (t - last < 90) return;
          last = t;
          analyser.getByteTimeDomainData(data);
          let peak = 0;
          for (let i = 0; i < data.length; i++) peak = Math.max(peak, Math.abs(data[i] - 128) / 128);
          setLevels((prev) => [...prev.slice(1), Math.min(1, 0.08 + peak * 1.8)]);
        };
        rafRef.current = requestAnimationFrame(loop);
      } catch {
        /* level meter is optional */
      }

      recorder.start(250);
      startedRef.current = performance.now();
      setElapsed(0);
      setStatus("recording");
      tickRef.current = window.setInterval(() => {
        const e = currentElapsed();
        setElapsed(e);
        if (e >= MAX_RECORDING_S) stop();
      }, 250);
    } catch (err) {
      cleanupStream();
      const name = (err as DOMException)?.name;
      setStatus(name === "NotAllowedError" || name === "SecurityError" ? "denied" : "error");
    }
  }, [supported, cleanupStream, stop]);

  const pause = useCallback(() => {
    const m = mediaRef.current;
    if (m && m.state === "recording") {
      m.pause();
      accumulatedRef.current = currentElapsed();
      startedRef.current = 0;
      setStatus("paused");
    }
  }, []);

  const resume = useCallback(() => {
    const m = mediaRef.current;
    if (m && m.state === "paused") {
      m.resume();
      startedRef.current = performance.now();
      setStatus("recording");
    }
  }, []);

  const cancel = useCallback(() => {
    const m = mediaRef.current;
    if (m && m.state !== "inactive") {
      discardRef.current = true;
      m.stop();
    } else {
      cleanupStream();
      setStatus("idle");
      setElapsed(0);
    }
    setResult((r) => {
      if (r) URL.revokeObjectURL(r.url);
      return null;
    });
    setLevels(Array(28).fill(0.08));
  }, [cleanupStream]);

  const reset = useCallback(() => {
    setResult(null);
    setStatus("idle");
    setElapsed(0);
    setLevels(Array(28).fill(0.08));
  }, []);

  return { status, elapsed, levels, result, supported, start, stop, pause, resume, cancel, reset };
}
