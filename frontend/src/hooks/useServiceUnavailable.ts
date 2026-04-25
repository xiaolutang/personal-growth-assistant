import { useState, useCallback } from "react";
import { ApiError } from "@/lib/errors";

interface UseServiceUnavailableReturn {
  serviceUnavailable: boolean;
  /** 包装 async fetch，503 时自动设置 serviceUnavailable=true，非 503 错误原样抛出 */
  runWith503: (fn: () => Promise<void>) => Promise<void>;
  /** 手动重试：清除 503 状态并重新执行 */
  retry: (fn: () => Promise<void>) => void;
}

export function useServiceUnavailable(): UseServiceUnavailableReturn {
  const [serviceUnavailable, setServiceUnavailable] = useState(false);

  const runWith503 = useCallback(async (fn: () => Promise<void>) => {
    try {
      await fn();
      setServiceUnavailable(false);
    } catch (error) {
      if (error instanceof ApiError && error.isServiceUnavailable) {
        setServiceUnavailable(true);
      } else {
        throw error;
      }
    }
  }, []);

  const retry = useCallback((fn: () => Promise<void>) => {
    setServiceUnavailable(false);
    runWith503(fn);
  }, [runWith503]);

  return { serviceUnavailable, runWith503, retry };
}
