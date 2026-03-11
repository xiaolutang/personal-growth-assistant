import type { ParseResponse } from "@/types/task";

const API_BASE = "/api";

export async function parseText(text: string): Promise<ParseResponse> {
  const response = await fetch(`${API_BASE}/parse?text=${encodeURIComponent(text)}`, {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}
