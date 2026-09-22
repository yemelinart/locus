import { useEffect, useRef, useState } from "react";
import type { Job } from "./types";

export function clockTime(seconds: number) {
  const whole = Math.max(0, Math.floor(seconds));
  const h = Math.floor(whole / 3600);
  const m = Math.floor((whole % 3600) / 60);
  const s = whole % 60;
  return [...(h ? [h] : []), m, s]
    .map((n) => String(n).padStart(2, "0"))
    .join(":");
}

export default function useResearchClock(job: Job) {
  const anchor = useRef({
    id: job.id,
    status: job.status,
    seconds: job.active_seconds,
    at: performance.now(),
  });
  const [elapsed, setElapsed] = useState(job.active_seconds);
  useEffect(() => {
    const now = performance.now();
    const previous = anchor.current;
    const continuing =
      previous.id === job.id &&
      previous.status === "running" &&
      job.status === "running";
    const projected = previous.seconds + (now - previous.at) / 1000;
    const seconds = continuing
      ? Math.max(job.active_seconds, projected)
      : job.active_seconds;
    anchor.current = { id: job.id, status: job.status, seconds, at: now };
    setElapsed(seconds);
  }, [job.id, job.status, job.active_seconds]);
  useEffect(() => {
    if (job.status !== "running") return;
    const timer = window.setInterval(() => {
      const current = anchor.current;
      setElapsed(current.seconds + (performance.now() - current.at) / 1000);
    }, 250);
    return () => clearInterval(timer);
  }, [job.id, job.status]);
  return elapsed;
}
