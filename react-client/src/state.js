import { atom } from "jotai";

export const documents = atom([])
export const fragments = atom([])
export const annotations = atom([])
export const virtualFloors = atom([])

export const openTabs_atom = atom([])
export const openTabsCount_atom = atom(0)
export const currentTab_atom = atom({})
export const vfTabReady_atom = atom(false)

export const f2c_atom = atom([])
export const a2c_atom = atom([])

export const recentlyDeletedIndex_atom = atom(-1)
export const appConnection_atom = atom({ connected: false, apiPath: import.meta.env.VITE_API_URI ?? "http://localhost:3000" })
export const workspaceHydrated_atom = atom(false)

// Cluster state
export const clusters = atom([])
export const selectedClusterId = atom(null)
export const clusterRunStatus = atom('idle') // 'idle' | 'running' | 'done' | 'error'
