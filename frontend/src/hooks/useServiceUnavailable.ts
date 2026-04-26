import { useState, useCallback } from "react";
import { ApiError } from "@/lib/errors";

interface UseServiceUnavailableReturn {
  serviceUnavailable: boolean;
  /** 包装 async fetch，503 时自动设置 serviceUnavailable=true，非 503 错误原样抛出 */
  runWith503: (fn: () => Promise<void>) => Promise<void>;
  /** 手动重试：清除 503 状态并重新执行（不重复包装 runWith503，避免双重嵌套覆盖状态） */
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
    // 不包装 runWith503：调用者应在 fn 内部自行处理 503（通过 runWith503）
    // 避免 retry + 内部 runWith503 双重嵌套导致状态被覆盖
    fn();
  }, []);

  return { serviceUnavailable, runWith503, retry };
}
