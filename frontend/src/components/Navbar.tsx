"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BookOpen, FlaskConical, LogOut } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/hooks";
import { Button } from "@/components/ui/button";

const NAV_ITEMS = [
  { href: "/", label: "Prompts", icon: BookOpen },
  { href: "/playground", label: "Playground", icon: FlaskConical },
] as const;

export default function Navbar() {
  const pathname = usePathname();
  const { user, signOut } = useAuth();

  return (
    <nav className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-14 items-center">
        <Link href="/" className="mr-8 flex items-center space-x-2">
          <span className="text-xl font-bold text-primary">PromptVault</span>
        </Link>

        <div className="flex items-center space-x-6 text-sm font-medium">
          {NAV_ITEMS.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-1.5 transition-colors hover:text-foreground/80",
                (href === "/" ? pathname === "/" : pathname.startsWith(href))
                  ? "text-foreground"
                  : "text-foreground/60",
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          ))}
        </div>

        <div className="ml-auto flex items-center gap-2">
          {user && (
            <>
              <span className="text-xs text-muted-foreground">{user.email}</span>
              <Button variant="ghost" size="icon" aria-label="Sign out" onClick={() => void signOut()}>
                <LogOut className="h-4 w-4" />
              </Button>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
