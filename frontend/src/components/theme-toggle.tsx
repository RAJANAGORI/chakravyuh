"use client"

import * as React from "react"
import { Monitor, Moon, Sun } from "lucide-react"
import { useTheme } from "next-themes"

import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

export function ThemeToggle() {
  const { theme, setTheme, resolvedTheme } = useTheme()
  const [mounted, setMounted] = React.useState(false)

  React.useEffect(() => {
    setMounted(true)
  }, [])

  const Icon = !mounted ? Sun : resolvedTheme === "dark" ? Moon : Sun

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="icon"
          className="shrink-0 border-border/80 bg-card/80 text-foreground shadow-sm"
          aria-label="Choose appearance: light, dark, or match system"
        >
          <Icon className="h-[1.15rem] w-[1.15rem]" aria-hidden />
          <span className="sr-only">Theme menu</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="text-xs font-normal leading-snug text-muted-foreground">
          Appearance — light for bright spaces, dark in low light, or System to match your device
          (often the calmest default).
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuRadioGroup
          value={mounted ? (theme ?? "system") : "system"}
          onValueChange={setTheme}
        >
          <DropdownMenuRadioItem value="light" className="gap-2">
            <Sun className="h-4 w-4 shrink-0 text-amber-500" aria-hidden />
            <div className="flex flex-col gap-0.5">
              <span className="font-medium leading-none">Light</span>
              <span className="text-xs font-normal text-muted-foreground">
                Daytime / high ambient light
              </span>
            </div>
          </DropdownMenuRadioItem>
          <DropdownMenuRadioItem value="dark" className="gap-2">
            <Moon className="h-4 w-4 shrink-0 text-indigo-400" aria-hidden />
            <div className="flex flex-col gap-0.5">
              <span className="font-medium leading-none">Dark</span>
              <span className="text-xs font-normal text-muted-foreground">
                Low light, less glare
              </span>
            </div>
          </DropdownMenuRadioItem>
          <DropdownMenuRadioItem value="system" className="gap-2">
            <Monitor className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
            <div className="flex flex-col gap-0.5">
              <span className="font-medium leading-none">System</span>
              <span className="text-xs font-normal text-muted-foreground">
                Match device — recommended
              </span>
            </div>
          </DropdownMenuRadioItem>
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
