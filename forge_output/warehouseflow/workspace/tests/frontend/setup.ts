import '@testing-library/jest-dom'

// jsdom 24 ships with a file-based localStorage that breaks the Web Storage API.
// Replace it with a fully-compliant in-memory implementation before any module
// (including Zustand's persist middleware) can call setItem/getItem.
const makeLocalStorageMock = () => {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => { store[key] = String(value) },
    removeItem: (key: string) => { delete store[key] },
    clear: () => { store = {} },
    get length() { return Object.keys(store).length },
    key: (index: number) => Object.keys(store)[index] ?? null,
  }
}

Object.defineProperty(window, 'localStorage', {
  value: makeLocalStorageMock(),
  writable: true,
})
