"use client";

import { useState, useEffect, useRef } from "react";
import { Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { getApiBase } from "@/lib/api-base";

type Status = { ok: boolean; message: string } | null;

export function LlmStatusBanner() {
  const [status, setStatus] = useState<Status>(null);
  const [showReady, setShowReady] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    let cancelled = false;

    const check = async () => {
      try {
        const url = `${getApiBase()}/health?t=${Date.now()}`;
        const res = await fetch(url, { method: "GET", mode: "cors", credentials: "include" });
        if (!res.ok) {
          setStatus((s) =>
            s === null ? { ok: false, message: "Checking API…" } : s
          );
          return;
        }
        const data = await res.json();
        if (cancelled) return;
        const dbOk = data.components?.database?.status === "healthy";
        const llmOk = data.components?.llm?.status === "healthy";
        const ok = data.status === "ok" && dbOk && llmOk;
        setStatus({
          ok,
          message: ok
            ? "API, database, and LLM are ready."
            : data.components?.llm?.message || data.components?.database?.message || "Degraded",
        });
        if (ok) {
          setShowReady(true);
          if (pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
          }
          window.setTimeout(() => setShowReady(false), 4000);
        }
      } catch {
        if (!cancelled)
          setStatus((s) =>
            s === null ? { ok: false, message: "Connecting to backend…" } : s
          );
      }
    };

    check();
    pollRef.current = setInterval(check, 8000);

    return () => {
      cancelled = true;
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  if (status === null) return null;

  if (status.ok && showReady) {
    return (
      <div className="animate-fade-in-up mx-4 mt-4 flex items-center justify-center gap-2 rounded-xl border border-emerald-300 bg-emerald-50 px-4 py-2 text-sm text-emerald-700 shadow-sm sm:mx-5 md:mx-6 lg:mx-8">
        <CheckCircle2 className="h-4 w-4 shrink-0" />
        <span>Backend ready. Upload your ERD PDF and architecture diagram to start.</span>
      </div>
    );
  }

  if (status.ok) return null;

  return (
    <div className="animate-fade-in-up mx-4 mt-4 flex items-center justify-center gap-3 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800 shadow-sm sm:mx-5 md:mx-6 lg:mx-8">
      {status.message.includes("Connecting") ? (
        <Loader2 className="h-4 w-4 shrink-0 animate-spin" />
      ) : (
        <AlertCircle className="h-4 w-4 shrink-0" />
      )}
      <span>{status.message || "Waiting for API…"}</span>
    </div>
  );
}
