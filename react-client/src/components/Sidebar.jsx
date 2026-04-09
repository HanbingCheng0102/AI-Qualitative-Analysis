import {
    Card,
    Typography,
    List,
    ListItem,
    Box,
    ListItemPrefix,
    ListItemSuffix,
    Chip,
    Accordion,
    AccordionHeader,
    AccordionBody,
    Dialog,
    DialogHeader,
    DialogBody,
    DialogFooter,
    Button,
    CardBody,
  } from "@material-tailwind/react";
  import {
    HomeIcon,
    DocumentIcon,
    SquaresPlusIcon,
    ArrowUpOnSquareStackIcon,
    PuzzlePieceIcon,
    RectangleGroupIcon,
    ChevronDownIcon,
    ChevronRightIcon,
    PlusCircleIcon,
    PlusIcon,
    DocumentDuplicateIcon,
    XCircleIcon,
    ArrowUpTrayIcon,
    CircleStackIcon,
  } from "@heroicons/react/24/solid";
import { useLocation, useNavigate } from "react-router-dom";
import React, { useEffect, useRef, useState } from "react";
import { useAtom } from "jotai";
import { currentTab_atom, openTabs_atom, recentlyDeletedIndex_atom, vfTabReady_atom, virtualFloors } from "../state";
import ItemList from "./ItemList";
import { RESET } from "jotai/utils";
   
function Sidebar() {

    const navigate = useNavigate()

    const location = useLocation()
    
    const nav = (route) => {
        navigate("/" + route)
        console.log("moving to: /" + route)
    }


    const [openLoad, setOpenLoad] = React.useState(false);
    const [openNewWorkspace, setOpenNewWorkspace] = React.useState(false);
    const [openAccordion, setOpenAccordion] = React.useState(false);

    const [virtualFloorList, setVirtualFloorList] = useAtom(virtualFloors)

    const [tabs, setTabs] = useAtom(openTabs_atom)
    const tabsRef = useRef()
    tabsRef.current = tabs

    const [currentTab, setCurrentTab] = useAtom(currentTab_atom)
    const [vfTabReady, setVfTabReady] = useAtom(vfTabReady_atom)
    const [recentlyDeletedIndex, setRecentlyDeletedIndex] = useAtom(recentlyDeletedIndex_atom)

    const closeTab = (index) => {
      console.log(index)
      setVfTabReady(false)

      let i = 0
      let deleted_found = false
      let newListRe_indexed = []

      for (const tab of tabsRef.current){

        if(i == index){
          deleted_found = true
        }else{
          if(deleted_found){
            let updated_tab = tab
            updated_tab.index = i - 1
            newListRe_indexed.push(updated_tab)

          }else{
            newListRe_indexed.push(tab)
          }
          
        }
        i++
      }
      setTabs(newListRe_indexed)

      setRecentlyDeletedIndex(index)

      if(index > 0){
        setCurrentTab(newListRe_indexed[index - 1])
      }else if (newListRe_indexed.length > 0){
        setCurrentTab(newListRe_indexed[0])
      }else{
        console.log("SETTING CURRENT TAB TO {}")
        setCurrentTab({})
      }
      
    }


    function chooseSavedFloor(floor_id){
      setVfTabReady(false)
      
      let thisvf
      for (const vf of virtualFloorList){
        if(vf._id.toString() == floor_id.toString()){
          thisvf = vf
        }
      }
    

      const { hash, pathname, search } = location
      if(pathname != "/"){
        navigate("/")
      }
      const uuid = crypto.randomUUID()
      const newTab = {
        type: "floor",
        key: uuid,
        index: tabs.length,
        existing: true,
        name: thisvf.name,
        vf_id: thisvf._id
      }
      setTabs((tabs) => [...tabs, newTab])
      console.log("switching to tab " + tabs.length)
      setCurrentTab(newTab)
      //MAKE NEW TAB WITH EXISTING FLOOR!

      handleLoadDialog()
    }
 
    const handleLoadDialog = () => {
      setOpenLoad(!openLoad)
    }
    const handleNewWorkspaceDialog = () => setOpenNewWorkspace(!openNewWorkspace);

    const handleOpenAccordion = (value) => setOpenAccordion(openAccordion === value ? 0 : value);


    const newFloorCreated = () =>{
      setVfTabReady(false)
      const { hash, pathname, search } = location
      if(pathname != "/"){
        navigate("/")
      }
      handleNewWorkspaceDialog()
      const uuid = crypto.randomUUID()
      const newTab = {
        type: "floor",
        key: uuid,
        existing: false,
        index: tabs.length,
        name: "Virtual Floor " + tabs.length,
        vf_id: null
      }
      setTabs((tabs) => [...tabs, newTab])
      console.log("switching to tab " + tabs.length)
      setCurrentTab(newTab)
    }

    const existingTabSwitchedTo = (index) => {
      const { hash, pathname, search } = location
      if(currentTab.index != index || pathname != "/"){
        setVfTabReady(false)

        
        if(pathname != "/"){
          navigate("/")
        }

        console.log("switching to tab " + index)
        setCurrentTab(tabsRef.current[index])
      }
      
    }
    
    return (
      <>
      <Card className="h-full w-full max-w-full rounded-none shadow-none border-0 p-0 text-black overflow-y-auto">
        <div className="px-4 pt-4 pb-2 border-b border-slate-100">
          <h1 className="text-base font-bold tracking-tight text-slate-800 leading-snug">Neighbourhood Insight Engine</h1>
        </div>
        <div className="px-4 pt-3 pb-1">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Tools</p>
        </div>
        <List>         
          <ListItem onClick={() => nav("doc-viewer")}>
            <ListItemPrefix>
              <DocumentIcon className="h-6 w-6" />
            </ListItemPrefix>
            <Typography color="black" className="mr-auto">
            <h2 className="block antialiased tracking-normal text-sm">Document Viewer</h2>
            </Typography>
          </ListItem>

          <ListItem onClick={() => nav("my-frags")}>
            <ListItemPrefix>
              <PuzzlePieceIcon className="h-6 w-6" />
            </ListItemPrefix>
            <Typography color="black" className="mr-auto">
            <h2 className="block antialiased tracking-normal text-sm">My Fragments</h2>
            </Typography>
          </ListItem>

          <ListItem onClick={() => nav("survey-ingest")}>
            <ListItemPrefix>
              <ArrowUpTrayIcon className="h-6 w-6" />
            </ListItemPrefix>
            <Typography color="black" className="mr-auto">
            <h2 className="block antialiased tracking-normal text-sm">Survey Ingestion</h2>
            </Typography>
          </ListItem>

          <ListItem onClick={() => nav("cluster-graph")}>
            <ListItemPrefix>
              <CircleStackIcon className="h-6 w-6" />
            </ListItemPrefix>
            <Typography color="black" className="mr-auto">
            <h2 className="block antialiased tracking-normal text-sm">Cluster Graph</h2>
            </Typography>
          </ListItem>

          {/* FRAGMENT EXTRACTORS */}
          <Accordion
          open={openAccordion === 1}
          icon={
            <ChevronDownIcon
              strokeWidth={2.5}
              className={`mx-auto h-4 w-4 transition-transform ${openAccordion === 1 ? "rotate-180" : ""}`}
            />
          }
        >
          <ListItem className="p-0" selected={openAccordion === 1}>
            <AccordionHeader onClick={() => handleOpenAccordion(1)} className="border-b-0 p-3">
              <ListItemPrefix>
                <SquaresPlusIcon className="h-6 w-6" />
              </ListItemPrefix>
              <Typography color="black" className="mr-auto">
              <h2 className="block antialiased tracking-normal text-sm">Fragment Extractors</h2>
              </Typography>
            </AccordionHeader>
          </ListItem>
          <AccordionBody className="py-1">
            <List className="p-0">
              <ListItem onClick={() => nav("frag-extract-textual")}>
                <ListItemPrefix>
                  <ChevronRightIcon strokeWidth={3} className="h-3 w-5" />
                </ListItemPrefix>
                Use Textual Elements
              </ListItem>
              <ListItem onClick={() => nav("frag-extract-query")}>
                <ListItemPrefix>
                  <ChevronRightIcon strokeWidth={3} className="h-3 w-5" />
                </ListItemPrefix>
                Query Specific Elements
              </ListItem>
              <ListItem onClick={() => nav("frag-image")}>
                <ListItemPrefix>
                  <ChevronRightIcon strokeWidth={3} className="h-3 w-5" />
                </ListItemPrefix>
                Create Image Fragment
              </ListItem>
            </List>
          </AccordionBody>
        </Accordion>

        </List>

        <div className="px-4 pt-4 pb-1 border-t border-slate-100">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Workspaces</p>
        </div>
        <List className="gap-4">


        {/* EACH TAB ICON */}
        {tabs.map((item, _) => (
            <ListItem onClick={() => existingTabSwitchedTo(item.index)} className={item.index == currentTab.index && location.pathname == "/" ? "outline-blue-200 bg-blue-50 !shadow-slate-500 group" : "outline group"} key={item.key}>
              <ListItemPrefix>
                {item.type == "floor" ? 
                <RectangleGroupIcon className="h-6 w-6" /> : <DocumentDuplicateIcon className="h-6 w-6"></DocumentDuplicateIcon>}
              </ListItemPrefix>
              <Typography color="black" className="mr-auto">
              <h2 className="block antialiased tracking-normal text-sm">{item.name}</h2>
              </Typography>
              <XCircleIcon className="hidden group-hover:block relative left-3 h-7 w-7" onClick={() => closeTab(item.index)}></XCircleIcon>
            </ListItem>
        ))}




        <ListItem onClick={handleNewWorkspaceDialog} className="outline-dotted" key={"newWorkspace"}>
            <ListItemPrefix>
              <PlusIcon className="h-6 w-6" />
            </ListItemPrefix>
            <Typography color="black" className="mr-auto">
            <h2 className="block antialiased tracking-normal text-sm">Open New Workspace</h2>
            </Typography>
        </ListItem>

        <Dialog open={openNewWorkspace} handler={handleNewWorkspaceDialog} size="sm">
          <DialogHeader>
            <h1 className="text-lg font-semibold">What would you like to open?</h1>
            </DialogHeader>
          <DialogBody>
          <div className="component-block-dia relative left-14 !gap-32">
            <div className="component-block-vert-xsmall3 !gap-8">

              <Card className="w-70 h-40 bg-[#cdb1fa] hover:bg-[#bf96ff]" onClick={newFloorCreated}>
                <CardBody>
                    <div className="component-block-vert-small">
                    <Typography color="white">
                    <h2 className="block antialiased tracking-normal text-base font-bold text-center">New Virtual Floor</h2>
                    </Typography>
                    <div className="component-block-annot">
                    <PlusIcon className="h-12 w-12 relative pt-4 left-12 bottom-10 fill-white"></PlusIcon>
                    <RectangleGroupIcon className="h-16 w-16 relative left-4 bottom-10 fill-white"></RectangleGroupIcon>
                    </div>
                    </div>
                  
                </CardBody>
              </Card>

              <Card className="w-70 h-36 bg-[#a8d5ff] hover:bg-[#94c8f7]" onClick={handleLoadDialog}>
                <CardBody>
                    <div className="component-block-vert-small">
                    <Typography color="black">
                    <h2 className="block antialiased tracking-normal text-base font-bold text-center">Load Existing Floor</h2>
                    </Typography>
                    <RectangleGroupIcon className="h-14 w-14 relative left-20 bottom-10 "></RectangleGroupIcon>
                    </div>
                  
                </CardBody>
              </Card>
            </div>
            <Card className="w-60 h-76 bg-[#cdb1fa] hover:bg-[#bf96ff]" onClick={handleNewWorkspaceDialog}>
              <CardBody>
                <div className="component-block-vert-small relative top-16">
                <Typography color="white">
                <h2 className="block antialiased tracking-normal text-base font-bold text-center">Document View</h2>
                </Typography>
                <DocumentDuplicateIcon className="h-16 w-16 relative left-16 bottom-8 fill-white"></DocumentDuplicateIcon>
                </div>
              </CardBody>
            </Card>
          </div>

          

          </DialogBody>
          <DialogFooter>
            <Button
              variant="text"
              color="red"
              onClick={handleNewWorkspaceDialog}
              className="mr-1 text-sm"
            >
              <span>Cancel</span>
            </Button>
          </DialogFooter>
        </Dialog>


        <Dialog open={openLoad} handler={handleLoadDialog} size="sm" className="!text-black">
          <DialogHeader>
            <h1 className="text-lg font-semibold">Which Virtual Floor would you like to load?</h1>
            </DialogHeader>
          <DialogBody className="!text-black">
          <ItemList itemList={virtualFloorList} setItemList={setVirtualFloorList} onDoubleClick={chooseSavedFloor} name={"Available Virtual Floors"}></ItemList>

          

          </DialogBody>
          <DialogFooter>
            <Button
              variant="text"
              color="red"
              onClick={handleLoadDialog}
              className="mr-1 text-sm"
            >
              <span>Cancel</span>
            </Button>
          </DialogFooter>
        </Dialog>





        </List>
      </Card>
      </>
    );
}

export default Sidebar