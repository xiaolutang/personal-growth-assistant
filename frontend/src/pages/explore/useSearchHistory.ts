import { useState, useCallback } from "react";
import { getSearchHistory, addToSearchHistory, removeFromSearchHistory } from "./utils";

export function useSearchHistory() {
  const [searchHistory, setSearchHistory] = useState<string[]>(getSearchHistory());

  const addHistory = useCallback((query: string) => {
    addToSearchHistory(query);
    setSearchHistory(getSearchHistory());
  }, []);

  const removeHistory = useCallback((query: string) => {
    removeFromSearchHistory(query);
    setSearchHistory(getSearchHistory());
  }, []);

  return { searchHistory, addHistory, removeHistory };
}
