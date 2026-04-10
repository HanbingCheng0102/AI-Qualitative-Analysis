
import './App.css'

import { BrowserRouter, Routes, Route } from 'react-router-dom';
import DocumentViewer from './views/DocumentViewer';
import Sidebar from './components/Sidebar';
import VirtualFloor from './views/VirtualFloor';
import FragmentExtractorTextual from './views/FragmentExtractorTextual';
import FragmentExtractorQuery from './views/FragmentExtractorQuery';
import { annotations, documents, virtualFloors } from './state';
import { useAtom } from 'jotai';
import { annotations_findAll, documents_findAll, floors_findAll } from './api/dataFacade';
import { useEffect } from 'react';
import FragmentImage from './views/FragmentImage';
import SurveyIngestionView from './views/SurveyIngestionView';
import ClusterGraphView from './views/ClusterGraphView';
import ManualPlacementView from './views/ManualPlacementView';

import { DevTools } from 'jotai-devtools';
import 'jotai-devtools/styles.css';
import MyFragments from './views/MyFragments';
import WorkspaceArea from './views/WorkspaceArea';

function App() {

  const [documentList, setDocumentList] = useAtom(documents)
  const [annotationList, setAnnotationList] = useAtom(annotations)
  const [virtualFloorList, setVirtualFloorList] = useAtom(virtualFloors)
  
  useEffect(() => {
    async function loadAllDocs(){
    const docList = await documents_findAll()

    setDocumentList(docList)
    }

    async function loadAllAnnots(){
      const annotList = await annotations_findAll()

      setAnnotationList(annotList)
    }

    async function loadAllFloors(){
      const floorList = await floors_findAll()
      setVirtualFloorList(floorList)
    }

    loadAllDocs()
    loadAllAnnots()
    loadAllFloors()

}, [])

  return (
    <>
      <DevTools/>
      <div className='app-shell'>
        <BrowserRouter>
          <div className='side-panel'>
            <Sidebar></Sidebar>
          </div>
          <div className='main-content'>
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
