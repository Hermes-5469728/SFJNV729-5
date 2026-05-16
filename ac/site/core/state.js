const UIState = Object.freeze({
  IDLE: 'idle',
  LOADING: 'loading',
  SUCCESS: 'success',
  ERROR: 'error',
  EMPTY: 'empty',
})

function createStateMachine(initialState = UIState.IDLE) {
  let current = initialState
  const listeners = []

  function transition(newState) {
    if (current === newState) return
    const prev = current
    current = newState
    listeners.forEach(fn => fn(newState, prev))
  }

  return {
    get state() { return current },
    is: (s) => current === s,
    transition,
    onChange(fn) {
      listeners.push(fn)
      return () => {
        const idx = listeners.indexOf(fn)
        if (idx > -1) listeners.splice(idx, 1)
      }
    },
    idle() { transition(UIState.IDLE) },
    loading() { transition(UIState.LOADING) },
    success() { transition(UIState.SUCCESS) },
    error() { transition(UIState.ERROR) },
    empty() { transition(UIState.EMPTY) },
  }
}
