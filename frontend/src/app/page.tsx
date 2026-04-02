"use client";

import { useState } from "react";
import { Header } from "@/components/layout/header";
import { LlmStatusBanner } from "@/components/llm-status-banner";
import { ERDUpload } from "@/components/erd-upload";
import { ChatInterface } from "@/components/chat-interface";
import { Sparkles, Shield, MessageSquareText } from "lucide-react";

export default function Home() {
  const [sessionReady, setSessionReady] = useState(false);
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const resetTrigger = 0;
  return (
    <div className="relative z-10 flex min-h-screen flex-col bg-background text-foreground">
      <Header />
      <LlmStatusBanner />
      <main className="flex min-h-0 w-full flex-grow flex-col">
        <div className="w-full max-w-none box-border px-4 py-6 sm:px-5 md:px-6 lg:px-8 lg:py-8 flex-1 flex flex-col min-h-0">
          <div className="mb-6 animate-fade-in-up rounded-3xl glass-panel px-6 py-6 md:px-8 md:py-7">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="max-w-2xl">
                <p className="mb-2 inline-flex animate-fade-in-up-delay-1 items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
                  <Sparkles className="h-3.5 w-3.5" />
                  Modern Threat Intelligence Interface
                </p>
                <h2 className="animate-fade-in-up-delay-2 text-2xl font-extrabold tracking-tight md:text-4xl">
                  <span className="hero-gradient-text">Design-aware</span> security analysis for
                  real architecture
                </h2>
                <p className="animate-fade-in-up-delay-3 mt-3 text-sm text-muted-foreground md:text-base">
                  Build your session with ERDs and architecture diagrams, then interrogate risk
                  posture using structured CIA + AAA prompts with clean, readable output.
                </p>
              </div>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div className="animate-fade-in-up-delay-3 rounded-xl border border-border/80 bg-card/80 px-3 py-2 text-center shadow-sm transition-transform hover:-translate-y-0.5">
                  <Shield className="mx-auto mb-1 h-4 w-4 text-primary" />
                  Upload
                </div>
                <div className="animate-fade-in-up-delay-4 rounded-xl border border-border/80 bg-card/80 px-3 py-2 text-center shadow-sm transition-transform hover:-translate-y-0.5">
                  <Sparkles className="mx-auto mb-1 h-4 w-4 text-primary" />
                  Analyze
                </div>
                <div className="animate-fade-in-up-delay-5 rounded-xl border border-border/80 bg-card/80 px-3 py-2 text-center shadow-sm transition-transform hover:-translate-y-0.5">
                  <MessageSquareText className="mx-auto mb-1 h-4 w-4 text-primary" />
                  Chat
                </div>
              </div>
            </div>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6 lg:gap-6 xl:gap-8 flex-1 min-h-0 items-stretch w-full min-w-0">
            {/* Left: uploads & session */}
            <section
              aria-label="Documents and diagrams"
              className="flex min-h-0 min-w-0 flex-col animate-fade-in-up-delay-2 lg:max-h-[calc(100dvh-7rem)] lg:overflow-y-auto lg:pr-1"
            >
              <ERDUpload
                onSessionReady={setSessionReady}
                onAnalysisIdChange={setAnalysisId}
                resetTrigger={resetTrigger}
              />
            </section>

            {/* Right: analysis chat */}
            <section
              aria-label="Security analysis chat"
              className="flex h-[min(800px,calc(100dvh-8rem))] min-h-0 min-w-0 flex-col animate-fade-in-up-delay-3 lg:h-[calc(100dvh-7rem)] lg:max-h-[calc(100dvh-7rem)]"
            >
              <ChatInterface
                disabled={!sessionReady}
                analysisId={analysisId}
                resetTrigger={resetTrigger}
              />
            </section>
          </div>
        </div>
      </main>
    </div>
  );
}
