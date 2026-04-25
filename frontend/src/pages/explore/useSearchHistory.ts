import { useState, useCallback } from "react";
import { getSearchHistory, removeFromSearchHistory } from "./utils";

export function useSearchHistory() {
  const [searchHistory, setSearchHistory] = useState<string[]>(getSearchHistory());

  const refresh = useCallback(() => {
    setSearchHistory(getSearchHistory());
  }, []);

  const removeHistory = useCallback((query: string) => {
    removeFromSearchHistory(query);
    setSearchHistory(getSearchHistory());
  }, []);

  return { searchHistory, removeHistory, refresh };
}
