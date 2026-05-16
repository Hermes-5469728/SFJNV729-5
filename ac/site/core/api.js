const APIClient = (() => {
  const BASE = 'http://localhost:8001'
  const DEFAULT_TIMEOUT = 15000

  async function safeParseJSON(response) {
    if (!response.ok) {
      let detail = ''
      try { detail = await response.text() } catch {}
      return { ok: false, error: `HTTP ${response.status}: ${detail || response.statusText}` }
    }
    try {
      const data = await response.json()
      return { ok: true, data }
    } catch (e) {
      return { ok: false, error: `JSON parse: ${e.message}` }
    }
  }

  async function fetchWithTimeout(url, options = {}, timeoutMs = DEFAULT_TIMEOUT) {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), timeoutMs)
    try {
      return await fetch(url, { ...options, signal: controller.signal })
    } finally {
      clearTimeout(timer)
    }
  }

  async function call(url, options = {}) {
    try {
      const response = await fetchWithTimeout(BASE + url, options)
      return await safeParseJSON(response)
    } catch (e) {
      return { ok: false, error: `Network: ${e.message}` }
    }
  }

  return {
    get: (url) => call(url),
    post: (url, body) => call(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
    call,
  }
})()
