function ChatComponent(containerSelector) {
  const container = document.querySelector(containerSelector)
  if (!container) throw new Error(`Container ${containerSelector} not found`)

  const state = createStateMachine(UIState.EMPTY)
  const messages = []
  let apiEndpoint = '/api/chat/deepseek'

  function escapeHtml(str) {
    const d = document.createElement('div')
    d.textContent = str
    return d.innerHTML
  }

  function renderContent(text) {
    const d = document.createElement('div')
    d.textContent = text
    let html = d.innerHTML
    html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) =>
      `<pre><code>${escapeHtml(code.trim())}</code></pre>`)
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>')
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    html = html.split('\n').filter(l => l.trim()).map(l => `<p>${l}</p>`).join('')
    return html
  }

  function render() {
    const messagesEl = container.querySelector('.chat-messages')
    if (!messagesEl) return

    if (state.is(UIState.EMPTY) && messages.length === 0) {
      messagesEl.innerHTML = '<div class="welcome-msg"><div class="welcome-icon">&#x1f4ac;</div><h2>AC 驾驶舱 · 多模型对话</h2><p>选择上方模型，输入问题开始对话</p></div>'
      return
    }

    messagesEl.innerHTML = messages.map(msg => `
      <div class="msg ${msg.role}">
        <div class="msg-avatar">${msg.role === 'user' ? 'U' : 'AI'}</div>
        <div>
          <div class="msg-bubble">${renderContent(msg.content)}</div>
          ${msg.error ? `<div class="msg-meta" style="color:var(--red)">${escapeHtml(msg.error)}</div>` : ''}
          ${msg.meta ? `<div class="msg-meta">${escapeHtml(msg.meta)}</div>` : ''}
        </div>
      </div>
    `).join('')

    messagesEl.scrollTop = messagesEl.scrollHeight
  }

  function addMessage(role, content, meta = null, error = null) {
    messages.push({ role, content, meta, error, timestamp: Date.now() })
    render()
  }

  async function send(text) {
    if (state.is(UIState.LOADING)) return
    if (!text.trim()) return

    const welcome = container.querySelector('.welcome-msg')
    if (welcome) welcome.remove()

    addMessage('user', text)
    state.loading()
    render()

    const result = await APIClient.post(apiEndpoint, { message: text })
    if (result.ok) {
      const d = result.data
      const meta = `${d.model || ''} ${d.latency_ms ? '· '+d.latency_ms+'ms' : ''} ${d.tokens_in ? '· '+d.tokens_in+'→'+d.tokens_out : ''}`
      addMessage('assistant', d.reply || '(empty)', meta.trim() || null)
      state.success()
    } else {
      addMessage('assistant', '', null, result.error)
      state.error()
    }
    render()
  }

  function setEndpoint(endpoint) {
    apiEndpoint = endpoint
  }

  const inputEl = container.querySelector('.chat-input')
  const sendBtn = container.querySelector('.send-btn')

  if (sendBtn && inputEl) {
    sendBtn.addEventListener('click', () => {
      send(inputEl.value)
      inputEl.value = ''
      inputEl.style.height = 'auto'
    })
    inputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        send(inputEl.value)
        inputEl.value = ''
        inputEl.style.height = 'auto'
      }
    })
    inputEl.addEventListener('input', () => {
      inputEl.style.height = 'auto'
      inputEl.style.height = Math.min(inputEl.scrollHeight, 120) + 'px'
    })
  }

  const unsub = EventBus.on('model:switched', (model) => {
    setEndpoint(`/api/chat/${model.id}`)
  })

  render()

  return {
    send,
    setEndpoint,
    getMessages: () => [...messages],
    destroy() {
      unsub()
      if (inputEl) inputEl.value = ''
    },
  }
}
