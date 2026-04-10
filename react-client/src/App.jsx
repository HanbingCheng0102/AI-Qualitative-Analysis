
import './App.css'

import { BrowserRouter, Routes, Route } from 'react-router-dom';
import DocumentViewer from './views/DocumentViewer';
import Sidebar from './components/Sidebar';
import VirtualFloor from './views/VirtualFloor';
import FragmentExtractorTextual from './views/FragmentExtractorTextual';
import FragmentExtractorQuery from './views/FragmentExtractorQuery';
import { a2c_atom, annotations, appConnection_atom, currentTab_atom, documents, f2c_atom, openTabsCount_atom, openTabs_atom, recentlyDeletedIndex_atom, virtualFloors, workspaceHydrated_atom } from './state';
import { useAtom } from 'jotai';
import { bootstrap_findAll } from './api/dataFacade';
import { useEffect, useRef, useState } from 'react';
import FragmentImage from './views/FragmentImage';
import SurveyIngestionView from './views/SurveyIngestionView';
import ClusterGraphView from './views/ClusterGraphView';
import ManualPlacementView from './views/ManualPlacementView';
import { getWorkspaceSession, saveWorkspaceSession } from './api/workspaceClient';
import { createDefaultWorkspaceSession, sanitizeWorkspaceStateByTab } from './stateSerialization';

import { DevTools } from 'jotai-devtools';
import 'jotai-devtools/styles.css';
import MyFragments from './views/MyFragments';
import WorkspaceArea from './views/WorkspaceArea';

function App() {

  const [documentList, setDocumentList] = useAtom(documents)
  const [annotationList, setAnnotationList] = useAtom(annotations)
  const [virtualFloorList, setVirtualFloorList] = useAtom(virtualFloors)
  const [openTabs, setOpenTabs] = useAtom(openTabs_atom)
  const [currentTab, setCurrentTab] = useAtom(currentTab_atom)
  const [f2c, setf2c] = useAtom(f2c_atom)
  const [a2c, seta2c] = useAtom(a2c_atom)
  const [recentlyDeletedIndex, setRecentlyDeletedIndex] = useAtom(recentlyDeletedIndex_atom)
  const [, setOpenTabsCount] = useAtom(openTabsCount_atom)
  const [workspaceHydrated, setWorkspaceHydrated] = useAtom(workspaceHydrated_atom)
  const [, setConnection] = useAtom(appConnection_atom)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState(null)
  const lastSavedSessionRef = useRef("")
  
  useEffect(() => {
    let cancelled = false

    async function hydrateApp(){
      try {
        const [bootstrap, session] = await Promise.all([
          bootstrap_findAll(),
          getWorkspaceSession()
        ])

        if (cancelled) return

        setDocumentList(bootstrap.documents)
        setAnnotationList(bootstrap.annotations)
        setVirtualFloorList(bootstrap.floors)

        setOpenTabs(session.openTabs ?? [])
        setCurrentTab(session.currentTab ?? {})
        setRecentryDeletedSafely(session.recentlyDeletedIndex ?? -1)
        setf2c(session.workspaceStateByTab?.f2c ?? [])
        seta2c(session.workspaceStateByTab?.a2c ?? [])
        setOpenTabsCount((session.openTabs ?? []).length)
        setWorkspaceHydrated(true)
        lastSavedSessionRef.current = JSON.stringify({
          openTabs: session.openTabs ?? [],
          currentTab: session.currentTab ?? {},
          recentlyDeletedIndex: session.recentlyDeletedIndex ?? -1,
          workspaceStateByTab: sanitizeWorkspaceStateByTab(session.workspaceStateByTab)
        })
        setConnection({
          connected: true,
          apiPath: import.meta.env.VITE_API_URI ?? "http://localhost:3000"
        })
      } catch (error) {
        if (cancelled) return

        const fallback = createDefaultWorkspaceSession()
        setOpenTabs(fallback.openTabs)
        setCurrentTab(fallback.currentTab)
        setRecentryDeletedSafely(fallback.recentlyDeletedIndex)
        setf2c(fallback.workspaceStateByTab.f2c)
        seta2c(fallback.workspaceStateByTab.a2c)
        setOpenTabsCount(0)
        setWorkspaceHydrated(true)
        setLoadError(error.message ?? "Failed to load workspace state.")
        setConnection({
          connected: false,
          apiPath: import.meta.env.VITE_API_URI ?? "http://localhost:3000"
        })
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    function setRecentryDeletedSafely(value) {
      setRecentlyDeletedIndex(value)
    }

    hydrateApp()

    return () => {
      cancelled = true
    }

}, [])

  useEffect(() => {
    if (!workspaceHydrated || loading) {
      return
    }

    const snapshot = {
      version: 1,
      openTabs,
      currentTab,
      recentlyDeletedIndex,
      workspaceStateByTab: sanitizeWorkspaceStateByTab({ f2c, a2c }),
      updatedAt: new Date().toISOString()
    }

    const comparable = JSON.stringify({
      openTabs: snapshot.openTabs,
      currentTab: snapshot.currentTab,
      recentlyDeletedIndex: snapshot.recentlyDeletedIndex,
      workspaceStateByTab: snapshot.workspaceStateByTab
    })

    if (comparable === lastSavedSessionRef.current) {
      return
    }

    const timeoutId = window.setTimeout(async () => {
      try {
        const saved = await saveWorkspaceSession(snapshot)
        lastSavedSessionRef.current = JSON.stringify({
          openTabs: saved.openTabs,
          currentTab: saved.currentTab,
          recentlyDeletedIndex: saved.recentlyDeletedIndex,
          workspaceStateByTab: sanitizeWorkspaceStateByTab(saved.workspaceStateByTab)
        })
        setConnection({
          connected: true,
          apiPath: import.meta.env.VITE_API_URI ?? "http://localhost:3000"
        })
      } catch (error) {
        console.error("Workspace autosave failed", error)
        setConnection({
          connected: false,
          apiPath: import.meta.env.VITE_API_URI ?? "http://localhost:3000"
        })
      }
    }, 800)

    return () => window.clearTimeout(timeoutId)
  }, [workspaceHydrated, loading, openTabs, currentTab, recentlyDeletedIndex, f2c, a2c])

  if (loading) {
    return <div className='app-shell'><div className='main-content p-6 text-slate-500'>Loading workspace…</div></div>
  }

  return (
    <>
      <DevTools/>
      <div className='app-shell'>
        <BrowserRouter>
          <div className='side-panel'>
            <Sidebar></Sidebar>
          </div>
          <div className='main-content'>
            {loadError ? <div className='px-4 py-2 text-sm text-amber-700 bg-amber-50 border-b border-amber-200'>API workspace session could not be loaded, so the app started with an empty local session. Autosave will resume when the API is available.</div> : null}
            <Routes>
              <Route path='/' Component={WorkspaceArea}></Route>
              <Route path='/doc-viewer' Component={DocumentViewer}></Route>
              <Route path='/my-frags' Component={MyFragments}></Route>
              <Route path='/frag-extract-textual' Component={FragmentExtractorTextual}></Route>
              <Route path='/frag-extract-query' Component={FragmentExtractorQuery}></Route>
              <Route path='/frag-image' Component={FragmentImage}></Route>
              <Route path='/survey-ingest' Component={SurveyIngestionView}></Route>
              <Route path='/cluster-graph' Component={ClusterGraphView}></Route>
              <Route path='/manual-placement' Component={ManualPlacementView}></Route>
            </Routes>
          </div>
        </BrowserRouter>
      </div>
    </>
  )
}

export default App
