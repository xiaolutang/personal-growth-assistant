import { useState, useEffect } from "react";
import { getMorningDigest, type MorningDigestResponse } from "@/services/api";

export function useMorningDigest() {
  const [data, setData] = useState<MorningDigestResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getMorningDigest()
      .then((d) => { if (!cancelled) setData(d); })
      .catch(() => { if (!cancelled) setError(true); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  return { data, loading, error };
}
