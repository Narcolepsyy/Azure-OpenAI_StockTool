export const apiBase = (): string => {
  const fromEnv = (import.meta as any).env?.VITE_API_BASE as string | undefined
  if (import.meta.env.DEV) {
    return (fromEnv && fromEnv.trim()) || 'http://127.0.0.1:8000'
  }
  return (fromEnv && fromEnv.trim()) || window.location.origin
}

const apiKey = (import.meta as any).env?.VITE_APP_API_KEY as string | undefined

export type ChatRequest = {
  prompt: string
  system_prompt?: string
  deployment?: string
}

export type ChatResponse = {
  content: string
  tool_calls?: Array<{ id: string; name: string; result: unknown }>
}

export async function chat(req: ChatRequest): Promise<ChatResponse> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (apiKey && apiKey.trim()) headers['X-API-Key'] = apiKey.trim()
  const res = await fetch(`${apiBase()}/chat`, {
    method: 'POST',
    headers,
    body: JSON.stringify(req),
  })
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const j = await res.json()
      detail = j.detail || JSON.stringify(j)
    } catch {}
    throw new Error(`Chat failed: ${detail}`)
  }
  return res.json()
}

export type StockQuote = {
  symbol: string
  price: number
  currency: string
  as_of: string
  source: string
}

export async function getStock(symbol: string): Promise<StockQuote> {
  const headers: Record<string, string> = {}
  if (apiKey && apiKey.trim()) headers['X-API-Key'] = apiKey.trim()
  const res = await fetch(`${apiBase()}/stock/${encodeURIComponent(symbol)}`, { headers })
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const j = await res.json()
      detail = j.detail || JSON.stringify(j)
    } catch {}
    throw new Error(`Quote failed: ${detail}`)
  }
  return res.json()
}

export type StockNewsItem = {
  uuid?: string
  title?: string
  publisher?: string
  link?: string
  published_at?: number
  type?: string
  related_tickers?: string[]
  thumbnail?: string
}

export type StockNews = {
  symbol: string
  count: number
  items: StockNewsItem[]
  source: string
}

export async function getNews(symbol: string, limit = 10): Promise<StockNews> {
  const headers: Record<string, string> = {}
  if (apiKey && apiKey.trim()) headers['X-API-Key'] = apiKey.trim()
  const url = `${apiBase()}/news/${encodeURIComponent(symbol)}?limit=${encodeURIComponent(String(limit))}`
  const res = await fetch(url, { headers })
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const j = await res.json()
      detail = (j as any).detail || JSON.stringify(j)
    } catch {}
    throw new Error(`News failed: ${detail}`)
  }
  return res.json()
}
