import { useState, useEffect, useCallback } from "react";

const USAGE_KEY = "pwa-usage-count";
const DISMISSED_KEY = "pwa-banner-dismissed";
const DISMISS_DURATION = 7 * 24 * 60 * 60 * 1000; // 7 days in ms

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

export function usePWAInstall() {
  const [deferredPrompt, setDeferredPrompt] =
    useState<BeforeInstallPromptEvent | null>(null);
  const [canInstall, setCanInstall] = useState(false);
  const [usageCount, setUsageCount] = useState(() => {
    try {
      return Number(localStorage.getItem(USAGE_KEY)) || 0;
    } catch {
      return 0;
    }
  });

  // Listen for beforeinstallprompt
  useEffect(() => {
    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
      setCanInstall(true);
    };
    window.addEventListener("beforeinstallprompt", handler);
    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  // Listen for appinstalled
  useEffect(() => {
    const handler = () => {
      setCanInstall(false);
      setDeferredPrompt(null);
    };
    window.addEventListener("appinstalled", handler);
    return () => window.removeEventListener("appinstalled", handler);
  }, []);

  // Listen for usage updates from other hook instances / tabs
  useEffect(() => {
    const onCustom = () => {
      try { setUsageCount(Number(localStorage.getItem(USAGE_KEY)) || 0); } catch {}
    };
    const onStorage = (e: StorageEvent) => {
      if (e.key === USAGE_KEY) {
        setUsageCount(Number(e.newValue) || 0);
      }
    };
    window.addEventListener("pwa-usage-updated", onCustom);
    window.addEventListener("storage", onStorage);
    return () => {
      window.removeEventListener("pwa-usage-updated", onCustom);
      window.removeEventListener("storage", onStorage);
    };
  }, []);

  const incrementUsageCount = useCallback(() => {
    try {
      const next = (Number(localStorage.getItem(USAGE_KEY)) || 0) + 1;
      localStorage.setItem(USAGE_KEY, String(next));
      setUsageCount(next);
      window.dispatchEvent(new CustomEvent("pwa-usage-updated"));
    } catch {}
  }, []);

  async function promptInstall() {
    if (!deferredPrompt) return;
    await deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === "accepted") {
      setCanInstall(false);
    }
    setDeferredPrompt(null);
  }

  // Banner logic: canInstall && usageCount >= 3 && not recently dismissed
  const showBanner = canInstall && usageCount >= 3 && (() => {
    try {
      const dismissed = localStorage.getItem(DISMISSED_KEY);
      if (!dismissed) return true;
      return Date.now() - Number(dismissed) > DISMISS_DURATION;
    } catch {
      return true;
    }
  })();

  const dismissBanner = useCallback(() => {
    try {
      localStorage.setItem(DISMISSED_KEY, String(Date.now()));
    } catch {}
  }, []);

  return { canInstall, promptInstall, usageCount, incrementUsageCount, showBanner, dismissBanner };
}
