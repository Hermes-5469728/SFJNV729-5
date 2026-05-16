const EventBus = (() => {
  const listeners = new Map()

  function on(event, fn) {
    if (!listeners.has(event)) listeners.set(event, new Set())
    const entry = { fn, once: false }
    listeners.get(event).add(entry)
    return () => off(event, fn)
  }

  function once(event, fn) {
    if (!listeners.has(event)) listeners.set(event, new Set())
    const entry = { fn, once: true }
    listeners.get(event).add(entry)
    return () => off(event, fn)
  }

  function off(event, fn) {
    const set = listeners.get(event)
    if (!set) return
    for (const entry of set) {
      if (entry.fn === fn) { set.delete(entry); break }
    }
  }

  function emit(event, data) {
    const set = listeners.get(event)
    if (!set) return
    for (const entry of [...set]) {
      try { entry.fn(data) } catch (e) { console.error(`[EventBus:${event}]`, e) }
      if (entry.once) set.delete(entry)
    }
  }

  function clear() { listeners.clear() }

  window.addEventListener('beforeunload', clear)

  return { on, once, off, emit, clear }
})()
