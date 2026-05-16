function ModelSwitcher(containerSelector) {
  const container = document.querySelector(containerSelector)
  if (!container) throw new Error(`Container ${containerSelector} not found`)

  const state = createStateMachine(UIState.LOADING)
  let currentModel = null
  let models = []

  function render() {
    if (state.is(UIState.LOADING)) {
      container.innerHTML = '<span class="loading-text" style="color:var(--text2);font-size:13px">Loading models...</span>'
      return
    }
    if (state.is(UIState.EMPTY) || models.length === 0) {
      container.innerHTML = '<span class="empty-text" style="color:var(--text3);font-size:13px">No models available</span>'
      return
    }

    container.innerHTML = models.map(m => `
      <button class="model-btn ${m.id === currentModel ? 'active' : ''}" data-model="${m.id}"
        ${m.id === currentModel ? 'aria-current="true"' : ''}
        style="display:inline-flex;align-items:center;gap:6px;padding:6px 14px;border-radius:8px;border:1px solid var(--border);background:${m.id === currentModel ? 'var(--accent)' : 'var(--surface)'};color:${m.id === currentModel ? '#fff' : 'var(--text)'};cursor:pointer;font-size:13px;font-weight:500;transition:all .15s">
        <span style="width:6px;height:6px;border-radius:50%;background:${m.available ? 'var(--green)' : 'var(--red)'};display:inline-block"></span>
        ${m.name}
      </button>
    `).join('')

    container.querySelectorAll('.model-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.dataset.model
        if (id !== currentModel) switchModel(id)
      })
    })
  }

  function switchModel(modelId) {
    const model = models.find(m => m.id === modelId)
    if (!model) return
    currentModel = modelId
    render()
    EventBus.emit('model:switched', { id: modelId, name: model.name })
  }

  async function loadModels() {
    state.loading()
    render()

    const result = await APIClient.get('/api/models')
    if (result.ok && result.data) {
      const env = result.data.env_configured || {}
      const current = result.data.current || {}
      models = [
        { id: 'deepseek', name: 'DeepSeek', available: env.deepseek },
        { id: 'qwen', name: '千问', available: env.qwen },
        { id: 'doubao', name: '豆包', available: env.doubao },
        { id: 'kimi', name: 'Kimi', available: env.kimi },
      ]
      const avail = models.filter(m => m.available)
      currentModel = avail.length > 0 ? avail[0].id : models[0].id
      state.success()
    } else {
      models = [
        { id: 'deepseek', name: 'DeepSeek', available: true },
        { id: 'qwen', name: '千问', available: false },
        { id: 'doubao', name: '豆包', available: false },
        { id: 'kimi', name: 'Kimi', available: false },
      ]
      currentModel = models[0].id
      state.success()
    }
    render()
    EventBus.emit('model:switched', { id: currentModel, name: models.find(m => m.id === currentModel)?.name })
  }

  EventBus.on('model:switch-to', (id) => switchModel(id))
  loadModels()

  return {
    getCurrent: () => currentModel,
    getModels: () => [...models],
    switchTo: switchModel,
    reload: loadModels,
    destroy() { EventBus.off('model:switch-to', switchModel) },
  }
}
