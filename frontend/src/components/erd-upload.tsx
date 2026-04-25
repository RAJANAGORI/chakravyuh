"use client";

import { useCallback, useState, useEffect } from "react";
import { useDropzone } from "react-dropzone";
import {
  UploadCloud,
  File as FileIcon,
  LucideGitBranch,
  Upload,
  CheckCircle,
  Loader2,
  ImageIcon,
  PlusCircle,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { getApiBase } from "@/lib/api-base";
import { getApiAuthHeaders } from "@/lib/api-auth";

export type UploadSlotStatus = "idle" | "processing" | "completed" | "error";

interface ERDUploadProps {
  onSessionReady: (ready: boolean) => void;
  onAnalysisIdChange?: (id: string | null) => void;
  resetTrigger?: number;
}

export function ERDUpload({
  onSessionReady,
  onAnalysisIdChange,
  resetTrigger,
}: ERDUploadProps) {
  const [primaryErdFile, setPrimaryErdFile] = useState<File | null>(null);
  const [textQueue, setTextQueue] = useState<File[]>([]);
  const [diagramQueue, setDiagramQueue] = useState<File[]>([]);
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const [primaryErdStatus, setPrimaryErdStatus] = useState<UploadSlotStatus>("idle");
  const [batchTextStatus, setBatchTextStatus] = useState<UploadSlotStatus>("idle");
  const [batchDiagramStatus, setBatchDiagramStatus] = useState<UploadSlotStatus>("idle");
  const [primaryProgress, setPrimaryProgress] = useState(0);
  const [batchProgress, setBatchProgress] = useState(0);
  const [primaryError, setPrimaryError] = useState<string | undefined>();
  const [batchTextError, setBatchTextError] = useState<string | undefined>();
  const [batchDiagramError, setBatchDiagramError] = useState<string | undefined>();
  const [isBusy, setIsBusy] = useState(false);
  const { toast } = useToast();

  const maxSize = 50 * 1024 * 1024;
  const base = getApiBase();

  useEffect(() => {
    onAnalysisIdChange?.(analysisId);
  }, [analysisId, onAnalysisIdChange]);

  const refreshReady = useCallback(
    async (aid: string | null) => {
      if (!aid) {
        onSessionReady(false);
        return;
      }
      try {
        const r = await fetch(
          `${base}/api/analysis-status?analysis_id=${encodeURIComponent(aid)}`,
          { headers: { ...getApiAuthHeaders() } }
        );
        const j = await r.json();
        onSessionReady(!!j.ready_for_chat);
      } catch {
        onSessionReady(false);
      }
    },
    [base, onSessionReady]
  );

  const onDropPrimaryPdf = useCallback(
    (files: File[]) => {
      const f = files[0];
      if (!f) return;
      if (f.size > maxSize) {
        toast({
          title: "File Too Large",
          description: "Maximum file size is 50MB.",
          variant: "destructive",
        });
        return;
      }
      if (!f.name.toLowerCase().endsWith(".pdf")) {
        toast({
          title: "Invalid file",
          description: "Primary ERD must be a PDF.",
          variant: "destructive",
        });
        return;
      }
      setPrimaryErdFile(f);
      setPrimaryErdStatus("idle");
      setPrimaryError(undefined);
      onSessionReady(false);
    },
    [toast, onSessionReady, maxSize]
  );

  const onDropTextMany = useCallback(
    (files: File[]) => {
      const allowed = [".pdf", ".json", ".txt"];
      const next: File[] = [];
      for (const f of files) {
        if (f.size > maxSize) continue;
        const low = f.name.toLowerCase();
        if (!allowed.some((ext) => low.endsWith(ext))) continue;
        next.push(f);
      }
      if (next.length === 0) {
        toast({
          title: "No valid files",
          description: "Add PDF, JSON, or TXT (max 50MB each).",
          variant: "destructive",
        });
        return;
      }
      setTextQueue((prev) => {
        const names = new Set(prev.map((p) => p.name));
        const merged = [...prev];
        for (const f of next) {
          if (!names.has(f.name)) {
            names.add(f.name);
            merged.push(f);
          }
        }
        return merged;
      });
      onSessionReady(false);
    },
    [toast, onSessionReady, maxSize]
  );

  const onDropDiagramMany = useCallback(
    (files: File[]) => {
      const allowed = [".png", ".jpg", ".jpeg", ".pdf", ".webp"];
      const next: File[] = [];
      for (const f of files) {
        if (f.size > maxSize) continue;
        const low = f.name.toLowerCase();
        if (!allowed.some((ext) => low.endsWith(ext))) continue;
        next.push(f);
      }
      if (next.length === 0) {
        toast({
          title: "No valid files",
          description: "Add PNG, JPG, WebP, or PDF.",
          variant: "destructive",
        });
        return;
      }
      setDiagramQueue((prev) => {
        const names = new Set(prev.map((p) => p.name));
        const merged = [...prev];
        for (const f of next) {
          if (!names.has(f.name)) {
            names.add(f.name);
            merged.push(f);
          }
        }
        return merged;
      });
      if (analysisId) onSessionReady(false);
    },
    [toast, onSessionReady, analysisId, maxSize]
  );

  const primaryDrop = useDropzone({
    onDrop: onDropPrimaryPdf,
    accept: { "application/pdf": [".pdf"] },
    maxFiles: 1,
    disabled: isBusy,
  });

  const textManyDrop = useDropzone({
    onDrop: onDropTextMany,
    accept: {
      "application/pdf": [".pdf"],
      "application/json": [".json"],
      "text/plain": [".txt"],
    },
    multiple: true,
    disabled: isBusy || !analysisId,
  });

  const diagramManyDrop = useDropzone({
    onDrop: onDropDiagramMany,
    accept: {
      "image/png": [".png"],
      "image/jpeg": [".jpg", ".jpeg"],
      "image/webp": [".webp"],
      "application/pdf": [".pdf"],
    },
    multiple: true,
    disabled: isBusy || !analysisId,
  });

  useEffect(() => {
    if (resetTrigger && resetTrigger > 0) {
      setPrimaryErdFile(null);
      setTextQueue([]);
      setDiagramQueue([]);
      setAnalysisId(null);
      setPrimaryErdStatus("idle");
      setBatchTextStatus("idle");
      setBatchDiagramStatus("idle");
      setPrimaryProgress(0);
      setBatchProgress(0);
      setPrimaryError(undefined);
      setBatchTextError(undefined);
      setBatchDiagramError(undefined);
      onSessionReady(false);
    }
  }, [resetTrigger, onSessionReady]);

  const createEmptySession = async () => {
    setIsBusy(true);
    try {
      const r = await fetch(`${base}/api/create-analysis-session`, {
        method: "POST",
        headers: { ...getApiAuthHeaders() },
      });
      if (!r.ok) throw new Error(await r.text());
      const j = await r.json();
      const aid = j.analysis_id as string;
      setAnalysisId(aid);
      onSessionReady(false);
      toast({ title: "Session created", description: "Add text files and diagrams." });
    } catch (e) {
      toast({
        title: "Failed to create session",
        description: e instanceof Error ? e.message : "Error",
        variant: "destructive",
      });
    } finally {
      setIsBusy(false);
    }
  };

  const processPrimaryErd = async () => {
    if (!primaryErdFile) return;
    setIsBusy(true);
    setPrimaryErdStatus("processing");
    setPrimaryProgress(10);
    setPrimaryError(undefined);
    try {
      const saveRes = await fetch(`${base}/api/save-original-erd`, {
        method: "POST",
        body: primaryErdFile,
        headers: {
          "X-Filename": primaryErdFile.name,
          ...getApiAuthHeaders(),
        },
        mode: "cors",
        credentials: "include",
      });
      if (!saveRes.ok) {
        const t = await saveRes.text();
        throw new Error(`Save failed: ${saveRes.status} ${t}`);
      }
      const formData = new FormData();
      formData.append("file", primaryErdFile);
      formData.append("filename", primaryErdFile.name);
      if (analysisId) formData.append("analysis_id", analysisId);
      const progressInterval = setInterval(() => {
        setPrimaryProgress((p) => Math.min(p + 8, 88));
      }, 400);
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10 * 60 * 1000);
      let response: Response;
      try {
        response = await fetch(`${base}/api/process-erd`, {
          method: "POST",
          body: formData,
          headers: { ...getApiAuthHeaders() },
          mode: "cors",
          credentials: "include",
          signal: controller.signal,
        });
      } finally {
        clearTimeout(timeoutId);
        clearInterval(progressInterval);
      }
      if (!response.ok) {
        let msg = response.statusText;
        try {
          const errBody = await response.json();
          if (errBody?.detail) msg = String(errBody.detail);
        } catch {
          /* ignore */
        }
        throw new Error(msg);
      }
      const result = await response.json();
      const aid = result.analysis_id as string | undefined;
      if (aid) setAnalysisId(aid);
      setPrimaryErdStatus("completed");
      setPrimaryProgress(100);
      if (aid) await refreshReady(aid);
      else onSessionReady(false);
      toast({
        title: "Primary ERD extracted",
        description: "Add more documents and architecture diagrams as needed.",
      });
    } catch (e) {
      const message =
        e instanceof Error
          ? e.name === "AbortError"
            ? "Request timed out."
            : e.message
          : "Unknown error";
      setPrimaryErdStatus("error");
      setPrimaryError(message);
      toast({ title: "ERD extraction failed", description: message, variant: "destructive" });
    } finally {
      setIsBusy(false);
    }
  };

  const sessionHasTextDocs = async (aid: string): Promise<boolean> => {
    const r = await fetch(
      `${base}/api/session-documents?analysis_id=${encodeURIComponent(aid)}`,
      { headers: { ...getApiAuthHeaders() } }
    );
    if (!r.ok) return false;
    const j = await r.json();
    const docs = j.documents as { kind: string }[];
    return docs.some(
      (d) => d.kind === "erd_text" || d.kind === "supporting_text"
    );
  };

  const processTextQueue = async () => {
    if (!analysisId || textQueue.length === 0) {
      toast({
        title: "Missing session or files",
        description: "Create a session or extract primary ERD, then add files to the queue.",
        variant: "destructive",
      });
      return;
    }
    setIsBusy(true);
    setBatchTextStatus("processing");
    setBatchProgress(0);
    setBatchTextError(undefined);
    try {
      let hasText = await sessionHasTextDocs(analysisId);
      const total = textQueue.length;
      for (let i = 0; i < total; i++) {
        const f = textQueue[i];
        const docRole = !hasText && i === 0 ? "erd_text" : "supporting";
        const formData = new FormData();
        formData.append("file", f);
        formData.append("filename", f.name);
        formData.append("analysis_id", analysisId);
        formData.append("doc_role", docRole);
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10 * 60 * 1000);
        const response = await fetch(`${base}/api/append-text-document`, {
          method: "POST",
          body: formData,
          headers: { ...getApiAuthHeaders() },
          mode: "cors",
          credentials: "include",
          signal: controller.signal,
        });
        clearTimeout(timeoutId);
        if (!response.ok) {
          let msg = response.statusText;
          try {
            const errBody = await response.json();
            if (errBody?.detail) msg = String(errBody.detail);
          } catch {
            /* ignore */
          }
          throw new Error(msg);
        }
        hasText = true;
        setBatchProgress(Math.round(((i + 1) / total) * 100));
      }
      setTextQueue([]);
      setBatchTextStatus("completed");
      await refreshReady(analysisId);
      toast({ title: "Text documents processed", description: `${total} file(s) added.` });
    } catch (e) {
      const message =
        e instanceof Error
          ? e.name === "AbortError"
            ? "Request timed out."
            : e.message
          : "Unknown error";
      setBatchTextStatus("error");
      setBatchTextError(message);
      toast({
        title: "Text batch failed",
        description: message,
        variant: "destructive",
      });
    } finally {
      setIsBusy(false);
    }
  };

  const processDiagramQueue = async () => {
    if (!analysisId || diagramQueue.length === 0) {
      toast({
        title: "Missing session or diagrams",
        description: "Set analysis session first, then queue diagram files.",
        variant: "destructive",
      });
      return;
    }
    setIsBusy(true);
    setBatchDiagramStatus("processing");
    setBatchProgress(0);
    setBatchDiagramError(undefined);
    try {
      const total = diagramQueue.length;
      for (let i = 0; i < total; i++) {
        const f = diagramQueue[i];
        const formData = new FormData();
        formData.append("file", f);
        formData.append("filename", f.name);
        formData.append("analysis_id", analysisId);
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10 * 60 * 1000);
        const response = await fetch(`${base}/api/append-architecture-diagram`, {
          method: "POST",
          body: formData,
          headers: { ...getApiAuthHeaders() },
          mode: "cors",
          credentials: "include",
          signal: controller.signal,
        });
        clearTimeout(timeoutId);
        if (!response.ok) {
          let msg = response.statusText;
          try {
            const errBody = await response.json();
            if (errBody?.detail) msg = String(errBody.detail);
          } catch {
            /* ignore */
          }
          throw new Error(msg);
        }
        setBatchProgress(Math.round(((i + 1) / total) * 100));
      }
      setDiagramQueue([]);
      setBatchDiagramStatus("completed");
      await refreshReady(analysisId);
      toast({
        title: "Diagrams analyzed",
        description: `${total} diagram(s) processed. You can chat when text + diagrams exist.`,
      });
    } catch (e) {
      const message =
        e instanceof Error
          ? e.name === "AbortError"
            ? "Request timed out."
            : e.message
          : "Unknown error";
      setBatchDiagramStatus("error");
      setBatchDiagramError(message);
      toast({
        title: "Diagram batch failed",
        description: message,
        variant: "destructive",
      });
    } finally {
      setIsBusy(false);
    }
  };

  /** Legacy single-diagram path (replaces all diagram_vision rows) */
  const processSingleDiagramLegacy = async (file: File) => {
    if (!analysisId) return;
    setIsBusy(true);
    setBatchDiagramStatus("processing");
    setBatchProgress(10);
    setBatchDiagramError(undefined);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("filename", file.name);
      formData.append("analysis_id", analysisId);
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10 * 60 * 1000);
      const response = await fetch(`${base}/api/process-architecture-diagram`, {
        method: "POST",
        body: formData,
        headers: { ...getApiAuthHeaders() },
        mode: "cors",
        credentials: "include",
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      if (!response.ok) {
        let msg = response.statusText;
        try {
          const errBody = await response.json();
          if (errBody?.detail) msg = String(errBody.detail);
        } catch {
          /* ignore */
        }
        throw new Error(msg);
      }
      setBatchDiagramStatus("completed");
      setBatchProgress(100);
      setDiagramQueue((q) => q.filter((x) => x.name !== file.name));
      await refreshReady(analysisId);
      toast({
        title: "Architecture diagram analyzed",
        description: "Diagram summary stored (replaced previous diagrams).",
      });
    } catch (e) {
      const message =
        e instanceof Error
          ? e.name === "AbortError"
            ? "Request timed out."
            : e.message
          : "Unknown error";
      setBatchDiagramStatus("error");
      setBatchDiagramError(message);
      toast({
        title: "Diagram failed",
        description: message,
        variant: "destructive",
      });
    } finally {
      setIsBusy(false);
    }
  };

  const badge = (s: UploadSlotStatus) => {
    switch (s) {
      case "idle":
        return <Badge variant="secondary">Pending</Badge>;
      case "processing":
        return <Badge variant="default">Processing…</Badge>;
      case "completed":
        return (
          <Badge variant="default" className="bg-green-500">
            Done
          </Badge>
        );
      case "error":
        return <Badge variant="destructive">Error</Badge>;
    }
  };

  const removeFromTextQueue = (name: string) => {
    setTextQueue((q) => q.filter((f) => f.name !== name));
  };

  const removeFromDiagramQueue = (name: string) => {
    setDiagramQueue((q) => q.filter((f) => f.name !== name));
  };

  return (
    <Card className="flex h-full flex-col rounded-3xl glass-panel animate-fade-in-up">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-xl">
          <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/15 to-teal-500/10 text-primary ring-1 ring-primary/20">
            <LucideGitBranch className="h-5 w-5" />
          </span>
          Session Builder
        </CardTitle>
        <CardDescription>
          Follow the 3-step flow: initialize session, add text context, then add architecture
          diagrams.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6 overflow-y-auto min-h-0 pr-1">
        <div className="flex flex-wrap items-center gap-2 rounded-2xl border border-border/70 bg-card/70 p-3 shadow-sm animate-fade-in-up-delay-1">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={createEmptySession}
            disabled={isBusy}
          >
            <PlusCircle className="h-4 w-4 mr-2" />
            New empty session
          </Button>
          {analysisId && (
            <p className="text-xs text-muted-foreground break-all flex-1 min-w-[12rem]">
              Session: {analysisId}
            </p>
          )}
        </div>

        <div className="space-y-3 rounded-2xl border-b border-border/70 bg-background/60 p-4 pb-6 animate-fade-in-up-delay-2">
          <h4 className="flex items-center gap-2 text-sm font-medium">
            <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-primary/15 text-xs font-bold text-primary">
              1
            </span>
            <FileIcon className="h-4 w-4" /> Primary ERD (optional)
          </h4>
          <p className="text-xs text-muted-foreground">
            Single PDF replaces all text documents for this session with this extraction (legacy
            path). Or use “New empty session” and process only the multi-file queue.
          </p>
          <div
            {...primaryDrop.getRootProps()}
            className={`flex flex-col items-center justify-center p-6 border-2 border-dashed rounded-xl cursor-pointer transition-all ${
              primaryDrop.isDragActive ? "border-primary bg-accent/70" : "border-border hover:border-primary/50 hover:bg-accent/40"
            }`}
          >
            <input {...primaryDrop.getInputProps()} />
            <UploadCloud className="h-10 w-10 text-muted-foreground" />
            <p className="mt-2 text-sm text-muted-foreground">
              <span className="font-semibold text-primary">PDF</span> — primary ERD
            </p>
            {primaryErdFile && (
              <p className="text-xs mt-2 text-muted-foreground">{primaryErdFile.name}</p>
            )}
          </div>
          <div className="flex items-center justify-between gap-2 flex-wrap">
            {badge(primaryErdStatus)}
            <Button
              size="sm"
              onClick={processPrimaryErd}
              disabled={!primaryErdFile || isBusy || primaryErdStatus === "processing"}
            >
              {primaryErdStatus === "processing" ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Upload className="h-4 w-4 mr-2" />
              )}
              Extract primary ERD
            </Button>
          </div>
          {primaryErdStatus === "processing" && (
            <>
              <Progress value={primaryProgress} className="h-2" />
              <p className="text-xs text-muted-foreground">Extracting text…</p>
            </>
          )}
          {primaryError && <p className="text-sm text-red-500">{primaryError}</p>}
        </div>

        <div className="space-y-3 rounded-2xl border-b border-border/70 bg-background/60 p-4 pb-6 animate-fade-in-up-delay-3">
          <h4 className="flex items-center gap-2 text-sm font-medium">
            <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-primary/15 text-xs font-bold text-primary">
              2
            </span>
            Additional text documents (queue)
          </h4>
          <p className="text-xs font-medium text-muted-foreground">Upload context files (PDF, JSON, TXT)</p>
          <div
            {...textManyDrop.getRootProps()}
            className={`flex flex-col items-center justify-center p-6 border-2 border-dashed rounded-xl transition-all ${
              !analysisId
                ? "opacity-50 cursor-not-allowed"
                : `cursor-pointer ${textManyDrop.isDragActive ? "border-primary bg-accent/70" : "border-border hover:border-primary/50 hover:bg-accent/40"}`
            }`}
          >
            <input {...textManyDrop.getInputProps()} />
            <UploadCloud className="h-8 w-8 text-muted-foreground" />
            <p className="mt-2 text-sm text-muted-foreground text-center">
              PDF, JSON, or TXT — multiple files
            </p>
            {!analysisId && (
              <p className="text-xs text-amber-600 mt-2">Create a session or extract primary ERD first.</p>
            )}
          </div>
          {textQueue.length > 0 && (
            <ul className="text-xs space-y-1 border border-border/70 rounded-xl p-2 max-h-32 overflow-y-auto bg-muted/30">
              {textQueue.map((f) => (
                <li key={f.name} className="flex justify-between gap-2 items-center">
                  <span className="truncate">{f.name}</span>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-6 px-2"
                    onClick={() => removeFromTextQueue(f.name)}
                    disabled={isBusy}
                  >
                    Remove
                  </Button>
                </li>
              ))}
            </ul>
          )}
          <div className="flex items-center justify-between gap-2 flex-wrap">
            {badge(batchTextStatus)}
            <Button
              size="sm"
              onClick={processTextQueue}
              disabled={!analysisId || textQueue.length === 0 || isBusy || batchTextStatus === "processing"}
            >
              {batchTextStatus === "processing" ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Upload className="h-4 w-4 mr-2" />
              )}
              Process text queue (append)
            </Button>
          </div>
          {batchTextStatus === "processing" && (
            <Progress value={batchProgress} className="h-2" />
          )}
          {batchTextError && <p className="text-sm text-red-500">{batchTextError}</p>}
        </div>

        <div className="space-y-3 rounded-2xl bg-background/60 p-4 animate-fade-in-up-delay-4">
          <h4 className="flex items-center gap-2 text-sm font-medium">
            <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-primary/15 text-xs font-bold text-primary">
              3
            </span>
            <ImageIcon className="h-4 w-4" /> Architecture diagrams (queue)
          </h4>
          <div
            {...diagramManyDrop.getRootProps()}
            className={`flex flex-col items-center justify-center p-6 border-2 border-dashed rounded-xl transition-all ${
              !analysisId
                ? "opacity-50 cursor-not-allowed"
                : `cursor-pointer ${diagramManyDrop.isDragActive ? "border-primary bg-accent/70" : "border-border hover:border-primary/50 hover:bg-accent/40"}`
            }`}
          >
            <input {...diagramManyDrop.getInputProps()} />
            <UploadCloud className="h-8 w-8 text-muted-foreground" />
            <p className="mt-2 text-sm text-muted-foreground text-center">
              PNG, JPG, WebP, or PDF — multiple files
            </p>
            {!analysisId && (
              <p className="text-xs text-amber-600 mt-2">Complete session / text step first.</p>
            )}
          </div>
          {diagramQueue.length > 0 && (
            <ul className="text-xs space-y-1 border border-border/70 rounded-xl p-2 max-h-32 overflow-y-auto bg-muted/30">
              {diagramQueue.map((f) => (
                <li key={f.name} className="flex justify-between gap-2 items-center">
                  <span className="truncate">{f.name}</span>
                  <div className="flex gap-1 shrink-0">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="h-6 px-2 text-[10px]"
                      onClick={() => processSingleDiagramLegacy(f)}
                      disabled={isBusy || !analysisId}
                    >
                      Replace all
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="h-6 px-2"
                      onClick={() => removeFromDiagramQueue(f.name)}
                      disabled={isBusy}
                    >
                      Remove
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
          <div className="flex items-center justify-between gap-2 flex-wrap">
            {badge(batchDiagramStatus)}
            <Button
              size="sm"
              onClick={processDiagramQueue}
              disabled={
                !analysisId || diagramQueue.length === 0 || isBusy || batchDiagramStatus === "processing"
              }
            >
              {batchDiagramStatus === "processing" ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Upload className="h-4 w-4 mr-2" />
              )}
              Process diagram queue (append)
            </Button>
          </div>
          {batchDiagramStatus === "processing" && (
            <Progress value={batchProgress} className="h-2" />
          )}
          {batchDiagramError && <p className="text-sm text-red-500">{batchDiagramError}</p>}
          {batchDiagramStatus === "completed" && (
            <p className="text-sm text-green-600 flex items-center gap-1">
              <CheckCircle className="h-4 w-4" /> Last diagram batch finished — chat when ready
              (needs text + diagram).
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
