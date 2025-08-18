export type ChatResponse = { output: string };


const BASE = ""; // Use Next.js API proxy

// Classic chat API call
export async function chatOnce(message: string, history: any[] = [], extra?: Record<string, any>) {
  const res = await fetch(`${BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history, ...(extra || {}) }),
  });
  if (!res.ok) throw new Error(`chat error: ${res.status}`);
  const text = await res.text();
  return { output: text } as ChatResponse;
}


// Memory service API functions
export async function getMemoryStatus() {
  const res = await fetch(`${BASE}/api/memory/status`);
  if (!res.ok) throw new Error(`Memory status error: ${res.status}`);
  return await res.json();
}

export async function searchMemories(query: string, conversationId?: string, limit?: number) {
  const res = await fetch(`${BASE}/api/memory/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ 
      query, 
      conversation_id: conversationId, 
      limit: limit || 10 
    }),
  });
  if (!res.ok) throw new Error(`Memory search error: ${res.status}`);
  return await res.json();
}

export async function rateOutput(
  prompt: string,
  variant: "control" | "mvp",
  score: number,
  notes?: string,
  extra?: { intent?: string; variant_id?: string; conversation_id?: string }
) {
  const res = await fetch(`${BASE}/api/rate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, variant, score, notes: notes || "", ...(extra||{}) }),
  });
  const json = await res.json();
  if (!json.ok) throw new Error(json.error || "rate error");
  return json;
}

// Concept Maps & Chain of Thought Reasoning API functions REMOVED
