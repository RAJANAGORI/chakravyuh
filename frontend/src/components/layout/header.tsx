import Image from 'next/image';

export function Header() {
  return (
    <header className="animate-fade-in-up sticky top-0 z-20 border-b border-border/60 bg-background/70 backdrop-blur-2xl">
      <div className="w-full max-w-none box-border px-4 sm:px-5 md:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center overflow-hidden rounded-xl bg-gradient-to-br from-blue-500/15 to-violet-500/15 ring-1 ring-primary/30">
              <Image
                src="/assets/image.png"
                alt="Chakravyuh"
                width={24}
                height={24}
                className="h-6 w-6 object-contain"
                priority
              />
            </div>
            <h1 className="text-2xl font-extrabold tracking-tight text-foreground">
              Chakravyuh
            </h1>
          </div>
          <div className="hidden items-center gap-2 rounded-full border border-border/80 bg-card/80 px-3 py-1.5 text-xs text-muted-foreground md:flex">
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
            AI Security Workspace
          </div>
        </div>
      </div>
    </header>
  );
}
