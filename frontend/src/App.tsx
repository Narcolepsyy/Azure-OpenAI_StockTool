import React, { useMemo, useState } from 'react'
import { chat as chatApi, getStock, type ChatResponse } from './lib/api'

export default function App() {
  // Chat state
  const [prompt, setPrompt] = useState('What is the latest price of AAPL?')
  const [systemPrompt, setSystemPrompt] = useState('You are a helpful assistant. Use the stock tool when users ask about stock prices.')
  const [deployment, setDeployment] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [chatError, setChatError] = useState<string | null>(null)
  const [chatResult, setChatResult] = useState<ChatResponse | null>(null)

  // Stock state
  const [symbol, setSymbol] = useState('AAPL')
  const [stockLoading, setStockLoading] = useState(false)
  const [stockError, setStockError] = useState<string | null>(null)
  const [stockResult, setStockResult] = useState<any | null>(null)

  const onSubmitChat = async (e: React.FormEvent) => {
    e.preventDefault()
    setChatError(null)
    setChatLoading(true)
    setChatResult(null)
    try {
      const res = await chatApi({ prompt, system_prompt: systemPrompt, deployment })
      setChatResult(res)
    } catch (err: any) {
      setChatError(err?.message || 'Chat failed')
    } finally {
      setChatLoading(false)
    }
  }

  const onSubmitStock = async (e: React.FormEvent) => {
    e.preventDefault()
    setStockError(null)
    setStockLoading(true)
    setStockResult(null)
    try {
      const res = await getStock(symbol)
      setStockResult(res)
    } catch (err: any) {
      setStockError(err?.message || 'Quote failed')
    } finally {
      setStockLoading(false)
    }
  }

  const toolCalls = useMemo(() => chatResult?.tool_calls ?? [], [chatResult])

  return (
    <div className="container">
      <header>
        <h1>AI Stocks Assistant</h1>
        <p>FastAPI + Azure OpenAI tool-calling + yfinance</p>
      </header>

      <main>
        <section className="card">
          <h2>Chat</h2>
          <form onSubmit={onSubmitChat} className="form">
            <label>
              Prompt
              <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} required />
            </label>
            <div className="row">
              <label>
                System prompt (optional)
                <input value={systemPrompt} onChange={(e) => setSystemPrompt(e.target.value)} />
              </label>
              <label>
                Deployment (optional)
                <input placeholder="Use server .env if blank" value={deployment} onChange={(e) => setDeployment(e.target.value)} />
              </label>
            </div>
            <button disabled={chatLoading} type="submit">{chatLoading ? 'Sending...' : 'Send'}</button>
          </form>
          {chatError && <div className="error">{chatError}</div>}
          {chatResult && (
            <div className="result">
              <h3>Assistant</h3>
              <p style={{ whiteSpace: 'pre-wrap' }}>{chatResult.content}</p>
              {toolCalls.length > 0 && (
                <details className="details">
                  <summary>Tool calls ({toolCalls.length})</summary>
                  <pre>{JSON.stringify(toolCalls, null, 2)}</pre>
                </details>
              )}
            </div>
          )}
        </section>

        <section className="card">
          <h2>Direct Stock Quote</h2>
          <form onSubmit={onSubmitStock} className="form">
            <label>
              Symbol
              <input value={symbol} onChange={(e) => setSymbol(e.target.value)} placeholder="AAPL" required />
            </label>
            <button disabled={stockLoading} type="submit">{stockLoading ? 'Fetching...' : 'Get Quote'}</button>
          </form>
          {stockError && <div className="error">{stockError}</div>}
          {stockResult && (
            <div className="result">
              <dl className="kv">
                <div><dt>Symbol</dt><dd>{stockResult.symbol}</dd></div>
                <div><dt>Price</dt><dd>{stockResult.price}</dd></div>
                <div><dt>Currency</dt><dd>{stockResult.currency}</dd></div>
                <div><dt>As of</dt><dd>{new Date(stockResult.as_of).toLocaleString()}</dd></div>
                <div><dt>Source</dt><dd>{stockResult.source}</dd></div>
              </dl>
            </div>
          )}
        </section>
      </main>

      <footer>
        <small>For dev: start FastAPI at 127.0.0.1:8000 and run Vite dev at 5173. For prod: build React and access /app.</small>
      </footer>
    </div>
  )
}

