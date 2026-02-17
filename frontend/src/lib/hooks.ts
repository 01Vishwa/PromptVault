// src/lib/hooks.ts
// ── Shared React hooks ──────────────────────────────────────────────
"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createClient } from "./supabase";
import type { Session, User } from "@supabase/supabase-js";

// ── Auth hook ────────────────────────────────────────────────────────

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  // createBrowserClient returns a singleton — safe to call in render
  const supabase = useMemo(() => createClient(), []);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session: s } }) => {
      setSession(s);
      setUser(s?.user ?? null);
      setLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, s) => {
      setSession(s);
      setUser(s?.user ?? null);
    });

    return () => subscription.unsubscribe();
  }, [supabase]);

  const signIn = useCallback(
    (email: string, password: string) =>
      supabase.auth.signInWithPassword({ email, password }),
    [supabase],
  );

  const signUp = useCallback(
    (email: string, password: string) =>
      supabase.auth.signUp({ email, password }),
    [supabase],
  );

  const signOut = useCallback(() => supabase.auth.signOut(), [supabase]);

  return { user, session, loading, signIn, signUp, signOut };
}

// ── Generic async data hook ──────────────────────────────────────────

export function useAsync<T>(
  fetcher: (() => Promise<T>) | null,
  deps: unknown[] = [],
) {
  const [data, setData] = useState<T | undefined>();
  const [error, setError] = useState<Error | undefined>();
  const [loading, setLoading] = useState(false);

  // Stable ref for deps to avoid spread-into-deps-array anti-pattern
  const depsRef = useRef(deps);
  depsRef.current = deps;

  const refetch = useCallback(async () => {
    if (!fetcher) return;
    setLoading(true);
    setError(undefined);
    try {
      const result = await fetcher();
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e : new Error(String(e)));
    } finally {
      setLoading(false);
    }
  }, [fetcher]);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  return { data, error, loading, refetch };
}

// ── Debounce hook ────────────────────────────────────────────────────

export function useDebounce<T>(value: T, delayMs: number = 300): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);

  return debounced;
}

