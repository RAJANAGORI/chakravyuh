"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Bot, User, Loader2, Send, Sparkles, Lock } from "lucide-react";
import { ChatEmptyIllustration } from "@/components/chat-empty-illustration";
import { useToast } from "@/hooks/use-toast";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { getApiBase } from "@/lib/api-base";
import { getApiAuthHeaders } from "@/lib/api-auth";
import { GUIDED_THREAT_PROMPTS } from "@/lib/guided-prompts";

// Code attribution (for provenance / authorship proof):
// Raja Nagori <raja.nagori@owasp.org>

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

interface ChatInterfaceProps {
  disabled: boolean;
  analysisId: string | null;
  resetTrigger?: number;
}

const queryCache = new Map<string, { answer: string; timestamp: number }>();
const CACHE_TTL = 30000;

const PROMPT_STAGGER = [
  "animate-fade-in-up",
  "animate-fade-in-up-delay-1",
  "animate-fade-in-up-delay-2",
  "animate-fade-in-up-delay-3",
  "animate-fade-in-up-delay-4",
  "animate-fade-in-up-delay-5",
] as const;

const __code_written_by = "Raja Nagori <raja.nagori@owasp.org>";

export function ChatInterface({
  disabled,
  analysisId,
  resetTrigger,
}: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();

  const cleanMarkdown = (content: string) => {
    return content
      .replace(/```markdown\n/g, "")
      .replace(/```\n/g, "")
      .replace(/```/g, "")
      .trim();
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Non-functional watermark: keep authorship string in the bundle without runtime behavior.
  useEffect(() => {
    void __code_written_by;
  }, []);

  useEffect(() => {
    if (resetTrigger && resetTrigger > 0) {
      setMessages([]);
      setInput("");
    }
  }, [resetTrigger]);

  const cacheKeyFor = (q: string) =>
    `${analysisId ?? ""}::${q.toLowerCase().trim()}`;

  const sendMessage = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || isLoading || disabled) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: trimmed,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const ck = cacheKeyFor(trimmed);
      const cached = queryCache.get(ck);
      const now = Date.now();

      let data: { answer?: string };
      if (cached && now - cached.timestamp < CACHE_TTL) {
        data = { answer: cached.answer };
      } else {
        const response = await fetch(`${getApiBase()}/ask`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...getApiAuthHeaders(),
          },
          body: JSON.stringify({
            q: trimmed,
            analysis_id: analysisId || undefined,
            structured: false,
            k: 3,
          }),
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        data = await response.json();
        queryCache.set(ck, {
          answer: data.answer || "Sorry, I couldn't process your request.",
          timestamp: now,
        });
        if (queryCache.size > 50) {
          const oldestKey = Array.from(queryCache.keys())[0];
          queryCache.delete(oldestKey);
        }
      }

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.answer || "Sorry, I couldn't process your request.",
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error("Error:", error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "Sorry, I encountered an error. Please try again.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
      toast({
        title: "Error",
        description: "Failed to get response. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await sendMessage(input);
  };

  return (
    <div className="relative h-full min-h-0 overflow-hidden rounded-3xl glass-panel">
      {disabled && (
        <div
          className="absolute inset-0 z-20 flex flex-col items-center justify-center gap-3 bg-background/75 px-6 text-center backdrop-blur-md"
          role="status"
          aria-live="polite"
        >
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary ring-1 ring-primary/25">
            <Lock className="h-7 w-7" />
          </div>
          <p className="max-w-xs text-sm font-medium text-foreground">
            Finish your session build
          </p>
          <p className="max-w-sm text-xs text-muted-foreground">
            Add text documents and at least one architecture diagram. Chat unlocks when the
            backend marks the session ready.
          </p>
        </div>
      )}
      <div className="flex h-full flex-col">
      <div className="flex-shrink-0 space-y-3 border-b border-border/70 bg-gradient-to-r from-indigo-50/90 via-violet-50/70 to-teal-50/50 p-4">
        <h3 className="flex items-center gap-2 font-semibold text-foreground">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-white/80 text-primary shadow-sm ring-1 ring-border/60">
            <Bot className="h-5 w-5" />
          </span>
          Security Analysis Chat (CIA AAA)
        </h3>
        <div className="flex flex-wrap gap-2">
          {GUIDED_THREAT_PROMPTS.map((p, i) => (
            <Button
              key={p.id}
              type="button"
              variant="secondary"
              size="sm"
              className={`h-8 rounded-full border-border/80 bg-white/90 text-xs shadow-sm transition-transform hover:-translate-y-px hover:shadow ${
                PROMPT_STAGGER[Math.min(i, PROMPT_STAGGER.length - 1)]
              }`}
              disabled={disabled || isLoading}
              onClick={() => setInput((prev) => (prev ? `${prev}\n\n${p.prompt}` : p.prompt))}
            >
              {p.label}
            </Button>
          ))}
        </div>
        <div className="flex items-center gap-2 rounded-xl border border-border/80 bg-card/90 px-3 py-2 text-xs text-muted-foreground shadow-sm">
          <Sparkles className="h-3.5 w-3.5 shrink-0 text-primary" />
          Guided prompts insert into the composer; answers use your uploaded session only.
        </div>
      </div>
      <div className="flex min-h-0 flex-1 flex-col">
        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto bg-gradient-to-b from-background via-background/95 to-muted/30 p-4">
          {messages.length === 0 && (
            <div className="animate-message-in flex flex-col items-center px-2 py-6 text-center sm:py-10">
              <ChatEmptyIllustration className="mb-6" />
              <h4 className="text-lg font-bold tracking-tight text-foreground md:text-xl">
                Your analysis floor is ready
              </h4>
              <p className="mt-2 max-w-md text-sm text-muted-foreground">
                When the session is prepared, ask about trust boundaries, data flows, and control
                gaps—or tap a guided prompt to structure CIA & AAA coverage.
              </p>
              <ul className="mt-6 flex flex-col gap-2 text-left text-xs text-muted-foreground sm:max-w-md">
                <li className="flex gap-2 rounded-lg border border-border/60 bg-card/80 px-3 py-2">
                  <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-teal-600" />
                  Use natural language or the chips above to seed the composer.
                </li>
                <li className="flex gap-2 rounded-lg border border-border/60 bg-card/80 px-3 py-2">
                  <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-violet-600" />
                  Shift+Enter for a new line; Enter sends.
                </li>
              </ul>
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={`animate-message-in flex gap-3 ${
                message.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              {message.role === "assistant" && (
                <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                  <Bot className="h-4 w-4 text-primary" />
                </div>
              )}

              <div
                className={`max-w-[90%] rounded-2xl px-6 py-4 shadow-sm ${
                  message.role === "user"
                    ? "ml-8 border border-indigo-200 bg-indigo-100 text-foreground"
                    : "bg-muted/70 mr-8 border border-border/70"
                }`}
              >
                <div className="text-sm break-words max-w-none">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    skipHtml={false}
                    components={{
                      table: ({ children }) => (
                        <div className="overflow-x-auto my-6 rounded-lg border border-border">
                          <table className="min-w-full border-collapse">{children}</table>
                        </div>
                      ),
                      thead: ({ children }) => (
                        <thead className="bg-muted/50">{children}</thead>
                      ),
                      tbody: ({ children }) => (
                        <tbody className="divide-y divide-border">{children}</tbody>
                      ),
                      tr: ({ children }) => (
                        <tr className="hover:bg-muted/30 transition-colors">{children}</tr>
                      ),
                      th: ({ children }) => (
                        <th className="px-4 py-3 text-left text-sm font-semibold text-foreground bg-muted/50 border-b border-border">
                          {children}
                        </th>
                      ),
                      td: ({ children }) => (
                        <td className="px-4 py-3 text-sm text-foreground border-b border-border">
                          {children}
                        </td>
                      ),
                      h1: ({ children }) => (
                        <h1 className="text-2xl font-bold mb-4 text-foreground">{children}</h1>
                      ),
                      h2: ({ children }) => (
                        <h2 className="text-xl font-semibold mb-3 text-foreground">{children}</h2>
                      ),
                      h3: ({ children }) => (
                        <h3 className="text-lg font-semibold mb-2 text-foreground">{children}</h3>
                      ),
                      p: ({ children }) => (
                        <p className="mb-3 text-foreground leading-relaxed">{children}</p>
                      ),
                      ul: ({ children }) => (
                        <ul className="list-disc list-inside mb-4 space-y-1 text-foreground">
                          {children}
                        </ul>
                      ),
                      ol: ({ children }) => (
                        <ol className="list-decimal list-inside mb-4 space-y-1 text-foreground">
                          {children}
                        </ol>
                      ),
                      li: ({ children }) => (
                        <li className="text-foreground leading-relaxed">{children}</li>
                      ),
                      strong: ({ children }) => (
                        <strong className="font-semibold text-foreground">{children}</strong>
                      ),
                      em: ({ children }) => (
                        <em className="italic text-foreground">{children}</em>
                      ),
                      code: ({ children }) => (
                        <code className="bg-muted px-2 py-1 rounded text-sm font-mono text-foreground">
                          {children}
                        </code>
                      ),
                      pre: ({ children }) => (
                        <pre className="bg-muted p-4 rounded-lg overflow-x-auto mb-4 text-sm font-mono text-foreground">
                          {children}
                        </pre>
                      ),
                      blockquote: ({ children }) => (
                        <blockquote className="border-l-4 border-primary pl-4 italic mb-4 text-muted-foreground">
                          {children}
                        </blockquote>
                      ),
                    }}
                  >
                    {cleanMarkdown(message.content)}
                  </ReactMarkdown>
                </div>
                <div className="text-xs opacity-70 mt-1">
                  {message.timestamp.toLocaleTimeString()}
                </div>
              </div>

              {message.role === "user" && (
                <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
                  <User className="h-4 w-4 text-primary-foreground" />
                </div>
              )}
            </div>
          ))}

          {isLoading && (
            <div className="animate-message-in flex gap-3 justify-start">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
                <Bot className="h-4 w-4 text-primary" />
              </div>
              <div className="mr-8 max-w-[min(100%,28rem)] rounded-2xl border border-border/70 bg-muted/60 px-5 py-4 shadow-sm">
                <div className="mb-3 flex items-center gap-2 text-sm font-medium text-foreground">
                  <Loader2 className="h-4 w-4 animate-spin text-primary" />
                  Analyzing your architecture…
                </div>
                <div className="space-y-2">
                  <div className="relative h-2.5 overflow-hidden rounded-full bg-muted">
                    <div className="shimmer-bg absolute inset-0" />
                  </div>
                  <div className="relative h-2.5 w-[80%] overflow-hidden rounded-full bg-muted">
                    <div className="shimmer-bg absolute inset-0" />
                  </div>
                  <div className="relative h-2.5 w-[55%] overflow-hidden rounded-full bg-muted">
                    <div className="shimmer-bg absolute inset-0" />
                  </div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="flex-shrink-0 border-t border-border/70 bg-card/90 p-5 shadow-[0_-8px_30px_-18px_hsl(230_40%_30%/0.12)]">
          <form onSubmit={handleSubmit} className="flex gap-3">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about security risks, CIA AAA threat modeling, or use guided prompts above..."
              className="flex-1 min-h-[80px] max-h-[140px] resize-none border-border/80 bg-background text-base shadow-inner"
              disabled={disabled || isLoading}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void handleSubmit(e);
                }
              }}
              autoFocus
            />
            <Button
              type="submit"
              disabled={!input.trim() || isLoading || disabled}
              className="self-end px-6 py-3 shadow-md"
              size="lg"
            >
              <Send className="h-5 w-5" />
            </Button>
          </form>
        </div>
      </div>
      </div>
    </div>
  );
}
