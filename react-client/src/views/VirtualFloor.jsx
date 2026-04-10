import { useCallback, useEffect, useRef, useState } from 'react'
import FragmentSelector from '../components/FragmentSelector'
import { useAtom, atom } from 'jotai'
import { a2c_atom, annotations, f2c_atom, fragments, virtualFloors } from '../state'

import { FabricJSCanvas, useFabricJSEditor } from 'fabricjs-react'
import { Button, Card, CardBody, CardHeader, Dialog, DialogBody, DialogFooter, DialogHeader, Input, Typography } from '@material-tailwind/react'
import AnnotationCreator from '../components/AnnotationCreator'
import { floor_save, floor_update } from '../api/dataFacade'
import { deleteIconSrc } from '../icons'
import { sanitizeFloorPayload } from '../stateSerialization'

function VirtualFloor({tab_index, changeTabName, savedName_initial, savedID_initial=null}){

    const x_canvasSize = 1550
    const y_canvasSize = 1250

    //for the save dialog
    const [openDia, setOpenDia] = useState(false);
    const toggleDialog = () => setOpenDia(!openDia);
    const [saveName, setSaveName] = useState("")

    const [fragmentList, setFragmentList] = useAtom(fragments) 
    const [annotationList, setAnnotationList] = useAtom(annotations)
    const [virtualFloorList, setVirtualFloorList] = useAtom(virtualFloors) 
    
    //f2c & a2c setup
    // TODO: These would be better as derived atoms from a global workspace atom that contains all the workspace data, including f2c and a2c for each tab. 
    // Then we wouldn't have to do all this ref stuff to keep track of the current tab's f2c and a2c.
    const [a2c, seta2c] = useAtom(a2c_atom)
    const [f2c, setf2c] = useAtom(f2c_atom) 

    const f2cRef = useRef()
    const a2cRef = useRef()

    f2cRef.current = f2c
    a2cRef.current = a2c

    //USE THESE!
    const thisf2cRef = useRef()
    const thisa2cRef = useRef()

    thisf2cRef.current = f2c[tab_index]
    thisa2cRef.current = a2c[tab_index]

    function seta2c_ForThisTab(newValue){
        //use tab_index
        let newList = [] 
        for (const tab of a2cRef.current){
            newList.push(tab)
        }
        newList[tab_index] = newValue
        seta2c(newList)
        thisa2cRef.current = a2c[tab_index]
        
    }

    function setf2c_ForThisTab(newValue){
        //use tab_index
        let newList = [] 
        for (const tab of f2cRef.current){
            newList.push(tab)
        }
        newList[tab_index] = newValue
        setf2c(newList)
        thisf2cRef.current = f2c[tab_index]
    }

    const annotsRef = useRef()

    annotsRef.current = annotationList

    const [loaded, setLoaded] = useState(false)
    const [annotsLoaded, setAnnotsLoaded] = useState(false)
    const [isReady, setisReady] = useState(false)
    const [isAnnotsReady, setisAnnotsReady] = useState(false)
    const [selectedObjects, setSelectedObjects] = useState([])
    const [savedIDState, setSavedIDState] = useState(null)
    const selObjRef = useRef()
    selObjRef.current = selectedObjects
    let isMultiSelect = false

    const { editor, onReady } = useFabricJSEditor()
    
    //canvas event setup
    useEffect(() => {
        setSavedIDState(savedID_initial)
        setSaveName(savedName_initial)
        //setfrag2LocationList(RESET)
        editor?.canvas.on('object:modified', objModifiedHandler)
        editor?.canvas.on('selection:created', objSelectedHandler)
        editor?.canvas.on('selection:updated', objSelectUpdatedHandler)
        editor?.canvas.on('selection:cleared', objSelectClearedHandler)
        editor?.canvas.setWidth(x_canvasSize)
        editor?.canvas.setHeight(y_canvasSize) 
        editor?.canvas.setBackgroundColor("#ffffff")
       
        $(document).on('click',".deleteBtn",function(){
            if(editor?.canvas.getActiveObject())
            {
                removeFromStorage(editor.canvas.getActiveObject())
                editor.canvas.remove(editor.canvas.getActiveObject());
                $(".deleteBtn").remove();
            }
        });

        editor?.canvas.on('mouse:down',function(e){
            if(!editor?.canvas.getActiveObject())
            {
                $(".deleteBtn").remove();
            }
        });

        editor?.canvas.on('object:moving',function(e){
                $(".deleteBtn").remove();
        });

        if(editor?.canvas){
             editor.canvas.selectionKey = "ctrlKey"
        }
       
    
    }, [editor]);

    useEffect(() => {
        if(thisa2cRef.current != null){
            if(fragmentList.length > 0 && thisf2cRef.current.length > 0){
                setisReady(true)
            }
        }
        
        
    }, [fragmentList])

    useEffect(() => {
        if(thisa2cRef.current != null){
            if(thisa2cRef.current.length > 0 && editor?.canvas){
                setisAnnotsReady(true)
            }
        }  
        
    }, [thisa2cRef.current, editor])

    useEffect(() => {
        console.log(f2c)
        if(isReady && loaded == false){
            console.log("Load ready: " + thisf2cRef.current)
            console.log(thisf2cRef.current)
            setLoaded(true)
            load()
        }else{      
            console.log("storage not yet loaded")
            console.log(thisf2cRef.current)
        }
    }, [isReady])

    useEffect(() => {
        if(isAnnotsReady && annotsLoaded == false){
            console.log("Annots load ready: " + thisa2cRef.current)
            console.log(thisa2cRef.current)
            setAnnotsLoaded(true)
            loadAnnots()
        }else{      
            console.log("annots storage not yet loaded")
        }
    }, [isAnnotsReady])

    function doReset(){
        console.log("resetting virtual floor")
        editor.canvas.clear()
        editor.canvas.setWidth(x_canvasSize)
        editor.canvas.setHeight(y_canvasSize) 
        editor?.canvas.setBackgroundColor("#ffffff")
        setf2c_ForThisTab([])
        seta2c_ForThisTab([])
         //delete to enable storage
    }



    /* * * * * * */
    /*  Saving   */
    /* * * * * * */

    async function openSaveDialog(){
        toggleDialog()
        console.log("saving current canvas, index: " + tab_index) 
    }

    async function handleSaveConfirmed(){
        changeTabName(saveName)
        console.log(saveName)
        let floorObj = {
            f2c: thisf2cRef.current,
            a2c: thisa2cRef.current
        }

        let id = await floor_save(floorObj, saveName)
        setSavedIDState(id)

        const newVFObj = {
            _id: id,
            floor : sanitizeFloorPayload(floorObj, saveName).floor,
            name: saveName
        }

        refreshVirtualFloorsAtom(newVFObj)

        toggleDialog()
    }

    async function updateSave(){
        let floorObj = {
            f2c: thisf2cRef.current,
            a2c: thisa2cRef.current
        }

        let id = await floor_update(floorObj, savedIDState, saveName)

        const newVFObj = {
            _id: savedIDState,
            floor : sanitizeFloorPayload(floorObj, saveName).floor,
            name: saveName
        }

        refreshVirtualFloorsAtom(newVFObj)
    }

    function refreshVirtualFloorsAtom(newAddition){
        let newList = []
        for (const vf of virtualFloorList){
            console.log(vf)
            console.log(newAddition)
            if (vf._id.toString() != newAddition._id.toString()) {
                newList.push(vf)
            }
        }
        newList.push(newAddition)
        setVirtualFloorList(newList)
    }



    /* * * * * * */
    /*  Loading  */
    /* * * * * * */


    function load(){
        
        let toLoad = []
        let uuidsLoaded = []
        for (const f2lObj of thisf2cRef.current){
            if (uuidsLoaded.includes(f2lObj.uuid)){
                console.log("dupe ignored")
            }else{
                toLoad.push(f2lObj)
                uuidsLoaded.push(f2lObj.uuid)
            }
        }

        for(const f2co of toLoad){
            spawnFromLoad(f2co)
        }
        console.log("finished frag load")
        
    }

    function loadAnnots(){

        let toLoad = []
        let uuidsLoaded = []
        for (const a2lObj of thisa2cRef.current){
            if (uuidsLoaded.includes(a2lObj.uuid)){
                console.log("dupe ignored")
            }else{
                toLoad.push(a2lObj)
                uuidsLoaded.push(a2lObj.uuid)
            }
        }

        for(const a2c of toLoad){
            spawnAnnotFromLoad(a2c)
        }
        console.log("finished annots load")
        
    }

    function spawnAnnotFromLoad(annot2location){
        console.log("spawnAnnotFromLoad called")
        const locObj = annot2location.locationObj
        const uuid = annot2location.uuid
        console.log(annot2location)

        var annot = new fabric.Textbox(annot2location.text, { 
            fill: 'black',
            fontFamily: "Arial",
            fontSize: 28,
            fontStyle: "italic",
            backgroundColor: annot2location.color,
            id: uuid
        });

        doSpawnLoadAnnot(annot, annot2location, locObj, uuid)

        function doSpawnLoadAnnot(annot, a2c, locObj, uuid){
            console.log("adding annot from load")

            annot.scaleToWidth(locObj.width)
            annot.scaleToHeight(locObj.height)
            annot.left = locObj.posx
            annot.top = locObj.posy
            var canObj = editor?.canvas.add(annot);

            annot.controls = {
                ...fabric.Textbox.prototype.controls,
                mtr: new fabric.Control({ visible: false }),
                mt: new fabric.Control({ visible: false }),
                mb: new fabric.Control({ visible: false }),
                ml: new fabric.Control({ visible: false }),
                mr: new fabric.Control({ visible: false }),
                
            }

            const i = thisa2cRef.current.indexOf(a2c)
            let newList
            if (i == 0){
                newList = thisa2cRef.current.slice(1)
            }else{
                newList = [
                    ...thisa2cRef.current.slice(0, i),
                    ...thisa2cRef.current.slice(i + 1)
                ]
            }

            const a2cObj = {
                locationObj: locObj,
                canvasObj: annot,
                uuid: uuid,
                fragids: a2c.fragids,
                annot_id: a2c.annot_id,
                text: a2c.text,
                color: a2c.color
            }

            seta2c_ForThisTab([...newList, a2cObj])

            let toLoad = []
            let uuidsLoaded = []
            for (const a2lObj of thisa2cRef.current){
                if (uuidsLoaded.includes(a2lObj.uuid)){
                    console.log("dupe ignored")
                }else{
                    toLoad.push(a2lObj)
                    uuidsLoaded.push(a2lObj.uuid)
                }
            }

            seta2c_ForThisTab([...toLoad])
        }
    }

    function spawnFromLoad(frag2Location){
        console.log("spawnFromLoad called")
        const frag = frag2Location.frag
        const locObj = frag2Location.locationObj
        const uuid = frag2Location.uuid

        //if image!
        if (frag.type == "image"){
            fabric.Image.fromURL(frag.html.split('\"')[1], function (oImg) {
                doSpawnLoad(oImg, frag, locObj, uuid)
            }, {id: uuid});
        }else{

            const doc = new DOMParser().parseFromString(frag.html, 'text/html');
            const xhtml = new XMLSerializer().serializeToString(doc);
            let svg = '<svg xmlns="http://www.w3.org/2000/svg" display="block"><foreignObject width="200" height="200"><div xmlns="http://www.w3.org/1999/xhtml">'
            svg += xhtml
            svg += '</div></foreignObject></svg>'
        
            fabric.Image.fromURL('data:image/svg+xml,' + encodeURIComponent(svg), function (oImg) {
                doSpawnLoad(oImg, frag, locObj, uuid)
            }, {id: uuid});
        }

        function doSpawnLoad(oImg, frag, locObj, uuid){
            //console.log("adding from load")

            oImg.controls = {
                ...fabric.Image.prototype.controls,
                mtr: new fabric.Control({ visible: false }),
                mt: new fabric.Control({ visible: false }),
                mb: new fabric.Control({ visible: false }),
                ml: new fabric.Control({ visible: false }),
                mr: new fabric.Control({ visible: false }),
            }
            
            oImg.scaleToHeight(locObj.height)
            oImg.scaleToWidth(locObj.width)

            const i = thisf2cRef.current.indexOf(frag2Location)
            let newList
            if (i == 0){
                newList = thisf2cRef.current.slice(1)
            }else{
                newList = [
                    ...thisf2cRef.current.slice(0, i),
                    ...thisf2cRef.current.slice(i + 1)
                ]
            }

            setf2c_ForThisTab(newList)
           
            oImg.left = locObj.posx
            oImg.top = locObj.posy

            const frag2LocationObj = {
                frag: frag, 
                locationObj: locObj,
                canvasObj: oImg,
                uuid: uuid
            }
            setf2c_ForThisTab([...thisf2cRef.current, frag2LocationObj])

            let toLoad = []
            let uuidsLoaded = []
            for (const f2cObj of thisf2cRef.current){
                if (uuidsLoaded.includes(f2cObj.uuid)){
                    console.log("dupe ignored")
                }else{
                    toLoad.push(f2cObj)
                    uuidsLoaded.push(f2cObj.uuid)
                }
            }

            setf2c_ForThisTab([...toLoad])
            
            editor?.canvas.add(oImg);
        }


    }


    /* * * * * * * * * */
    /* Fragment Spawns */
    /* * * * * * * * * */


    function spawnFragAtPosition(fragid, posx, posy){
        console.log("spawnAtPosition called")
        //console.log("fragmentList: " + fragmentList.length)
        for (const frag of fragmentList){
            if (frag._id == fragid){
                const uuid = crypto.randomUUID()

                //if image!
                if (frag.type == "image"){
                    fabric.Image.fromURL(frag.html.split('\"')[1], function (oImg) {
                        doSpawn(oImg, frag, uuid)
                    }, {id: uuid});
                }else{

                    const doc = new DOMParser().parseFromString(frag.html, 'text/html');
                    const xhtml = new XMLSerializer().serializeToString(doc);
                    let svg = '<svg xmlns="http://www.w3.org/2000/svg" display="block"><foreignObject width="200" height="200"><div xmlns="http://www.w3.org/1999/xhtml">'
                    svg += xhtml
                    svg += '</div></foreignObject></svg>'
                    
                    fabric.Image.fromURL('data:image/svg+xml,' + encodeURIComponent(svg), function (oImg) {
                        doSpawn(oImg, frag, uuid)
                    }, {id: uuid});
                }
            }
        }

        function doSpawn(oImg, frag, uuid){

            oImg.controls = {
                ...fabric.Image.prototype.controls,
                mtr: new fabric.Control({ visible: false }),
                mt: new fabric.Control({ visible: false }),
                mb: new fabric.Control({ visible: false }),
                ml: new fabric.Control({ visible: false }),
                mr: new fabric.Control({ visible: false }),
            }
            
            oImg.getScaledHeight() >= oImg.getScaledWidth() ? oImg.scaleToHeight(200) : oImg.scaleToWidth(200)
           
            oImg.left = posx
            oImg.top = posy
            
            
            const frag2LocationObj = {
                frag: frag, 
                locationObj: {
                    height: oImg.getScaledHeight(),
                    width: oImg.getScaledWidth(),
                    posx: posx,
                    posy: posy
                },
                canvasObj: oImg,
                uuid: uuid
            }

            setf2c_ForThisTab([...thisf2cRef.current, frag2LocationObj])
            
            editor?.canvas.add(oImg);
            console.log("adding to canvas")
        }
    }

    function spawnFragment(fragid){
        console.log("adding new fragment to canvas")
        if(thisf2cRef.current.length == 0){
            setLoaded(true) //avoids reload  
        }
        const offsetx = Math.floor(Math.random() * 40) 
        const offsety = Math.floor(Math.random() * 40) 
        spawnFragAtPosition(fragid, 10 + offsetx, 10 + offsety)
    }

    /* Doesn't work properly, f2c is not updated correctly */
    function bulkSpawn(fragidList){   
    
        if(thisf2cRef.current.length == 0){
            setLoaded(true) //avoids reload  
        }
        for (const fid of fragidList){
            spawnFragment(fid)
        }

    }

       
    /* * * * * * * * * * */
    /* Annotation Spawns */
    /* * * * * * * * * * */

    function onAnnotCreated(annotText, selObjList, color, realm_id){
        if(thisa2cRef.current.length == 0){
            setAnnotsLoaded(true)
        }
        //need to create canvas object for annotation
        const uuid = crypto.randomUUID()
        console.log("uuid generated for new annotation")

        var annot = new fabric.Textbox(annotText, { 
            fill: 'black',
            fontFamily: "Arial",
            fontSize: 28,
            fontStyle: "italic",
            backgroundColor: color,
            id: uuid
        });

        let x = selObjList[0].oCoords.mt.x
        let y = selObjList[0].oCoords.mt.y
        console.log(x + "," + y)

        doAnnotSpawn(annot, uuid, selObjList, x, y, annotText, color, realm_id) //CHANGE FOR SPAWNING NEAR THE SELECTION
        
    }

    function doAnnotSpawn(annot, uuid, selObjList, posx, posy, annotText, color, realm_id){
        annot.left = posx
        annot.top = posy

        annot.getScaledHeight() >= annot.getScaledWidth() ? annot.scaleToHeight(200) : annot.scaleToWidth(200)
        
        var cObj = editor.canvas.add(annot)

        annot.controls = {
            ...fabric.Textbox.prototype.controls,
            mtr: new fabric.Control({ visible: false }),
            mt: new fabric.Control({ visible: false }),
            mb: new fabric.Control({ visible: false }),
            ml: new fabric.Control({ visible: false }),
            mr: new fabric.Control({ visible: false }),
        }

        const locObj = {
            height: annot.getScaledHeight(),
            width: annot.getScaledWidth(),
            posx: annot.left,
            posy: annot.top
        }

        let fidList = []
        for (const selObj of selObjList){
            const thisId = selObj.id

            for (const f2l of thisf2cRef.current){
                if(f2l.uuid == thisId){
                    fidList.push(f2l.frag._id)
                }
            }
        }

        const a2lObj = {
            canvasObj: annot,
            locationObj: locObj,
            uuid: uuid,
            annot_id: realm_id,
            fragids: fidList,
            text: annotText,
            color: color
        }

        seta2c_ForThisTab([...thisa2cRef.current, a2lObj])
        console.log(thisa2cRef.current)
        console.log(thisa2cRef.current)
    }

    /* * * * * * * * * * */
    /* Moving & Resizing */
    /* * * * * * * * * * */

    function objModifiedHandler(event){ //called when an object is scaled or moved
        console.log(event)
        if (!isMultiSelect) {
            let [newf2c, newa2c] = updateSingleLocation(event.target, event)
            seta2c_ForThisTab(newa2c)
            setf2c_ForThisTab(newf2c)

            //move the delete button to the new location
            addDeleteBtn(event.target.left, event.target.top);
        }else{
            let list = event.target._objects
            console.log("MULTI-DRAG: updating the location of " + list.length + " objects")
            updateMultipleLocations(event, list)
        }
        console.log("Finished mulit-drag update")
        
    }

    function updateMultipleLocations(event, objectList){
        let rolling_f2c = thisf2cRef.current
        let rolling_a2c = thisa2cRef.current
        console.log("MULTIPLE LOCATIONS")
        for (const object of objectList){
            console.log("Updating object")
            let [f, a] = updateSingleLocation(object, event, event.transform.original, rolling_f2c, rolling_a2c)
            rolling_f2c = f
            rolling_a2c = a
            console.log(object)
        }
        
        seta2c_ForThisTab(rolling_a2c)
        setf2c_ForThisTab(rolling_f2c)
    }

    
    /**
     * Updates the stored location metadata for a single moved/scaled canvas object.
     *
     * The method tries to match the provided `object.id` against:
     * 1) fragment-to-canvas mappings (`f2c`) first, then
     * 2) annotation-to-canvas mappings (`a2c`) if no fragment match is found.
     *
     * For a match, it recalculates `locationObj` (`height`, `width`, `posx`, `posy`)
     * using either:
     * - the object's current absolute canvas coordinates, or
     * - an offset from `orig` (when provided), applied to the previously stored location.
     *
     * It uses `prev_f2c` / `prev_a2c` as override sources when passed; otherwise it falls
     * back to `thisf2cRef.current` / `thisa2cRef.current`.
     *
     * @param {Object} object - The moved/scaled canvas object (expected to expose `id`, `left`, `top`, `getScaledWidth()`, `getScaledHeight()`).
     * @param {Object} event - Fabric/interaction event containing `target.left` and `target.top` for offset calculations.
     * @param {?Object} [orig=null] - Original object position snapshot used to compute relative movement (`orig.left`, `orig.top`).
     * @param {?Array<Object>} [prev_f2c=null] - Optional prior fragment-location list to update instead of the current ref list.
     * @param {?Array<Object>} [prev_a2c=null] - Optional prior annotation-location list to update instead of the current ref list.
     * @returns {[Array<Object>, Array<Object>]} Tuple of updated `[f2c, a2c]` lists.  
     * Returns empty arrays for lists not set during this call (e.g., if no match is found).
     *
     * @remarks
     * - Matching uses UUID/id equality (string-normalized for f2c in current logic).
     * - The selected list is updated in place before being returned.
     */
    function updateSingleLocation(object, event, orig=null, prev_f2c=null, prev_a2c=null){

        
        let newa2c = []
        let newf2c = []
        let list2use

        console.log("Updating single object location", object)

        if (prev_f2c){
            list2use = prev_f2c
        }else{
            list2use = thisf2cRef.current
        }

        let found = false
        
        for (const f2loc of list2use){
            console.log("checking f2c object with uuid " + f2loc.uuid + " against moved object with id " + object.id)
            if (f2loc.uuid.toString() == object.id.toString()){
                found = true
                console.log("moving fragment")
                const i = list2use.indexOf(f2loc)
    
                let newLocObj = {
                    height: object.getScaledHeight(),
                    width: object.getScaledWidth(),
                    posx: object.left,
                    posy: object.top
                }

                if (orig){
                    let offsetx = event.target.left - orig.left 
                    let offsety = event.target.top - orig.top
                    console.log(offsetx + " : " + offsety)
                    newLocObj.posx = f2loc.locationObj.posx + offsetx
                    newLocObj.posy = f2loc.locationObj.posy + offsety
                }

                list2use[i].locationObj = newLocObj

                newf2c = list2use
                newa2c = thisa2cRef.current
                
            }
        }

        if (!found){

            console.log("object not found in f2c, checking a2c")

            if (prev_a2c){
                list2use = prev_a2c
            }else{
                list2use = thisa2cRef.current
            }

            for (const a2loc of list2use){
                if (a2loc.uuid == object.id){
                    const i = list2use.indexOf(a2loc)
                    console.log("moving annotation")
                    found = true
    
                    let newLocObj = {
                        height: object.getScaledHeight(),
                        width: object.getScaledWidth(),
                        posx: object.left,
                        posy: object.top
                    }

                    if (orig){
                        let offsetx = event.target.left - orig.left 
                        let offsety =  event.target.top - orig.top
                        newLocObj.posx = a2loc.locationObj.posx + offsetx
                        newLocObj.posy = a2loc.locationObj.posy + offsety
                    }

                    list2use[i].locationObj = newLocObj
    
                    newa2c = list2use
                    newf2c = thisf2cRef.current
                    
                }
            }
        }

        return [newf2c, newa2c]
    }


    /* * * * * * * * * * * */
    /* Tracking Selections */
    /* * * * * * * * * * * */

    function objSelectedHandler(event){
        console.log("object selected handler entered")

        $(".deleteBtn").remove();
        if (event.selected.length == 1){
            addDeleteBtn(event.selected[0].left, event.selected[0].top);
            isMultiSelect = false
        }else{
            isMultiSelect = true
        }

        setSelectedObjects(event.selected)
    }

    function objSelectUpdatedHandler(event){
        console.log("object select UPDATED handler entered")

        $(".deleteBtn").remove();

        if (event.deselected.length == 0){
            isMultiSelect = true
        }else{
            isMultiSelect = false
            if(event.selected.length > 0){
                addDeleteBtn(event.selected[0].left, event.selected[0].top);
            }
        }


        const current = []
        for (const c of selObjRef.current){
            if (!event.deselected.includes(c)){
                current.push(c)
            }
        }

        for (const selectedCanvasObj of event.selected){
            current.push(selectedCanvasObj)
        }

        setSelectedObjects(current)

    }

    function objSelectClearedHandler(event){
        setSelectedObjects([])
    }

 
    /* * * * * * * * * * * * */
    /*  Deleting From Canvas */
    /* * * * * * * * * * * * */

    function addDeleteBtn(x, y){
        $(".deleteBtn").remove(); 
        var btnLeft = x-35;
        var btnTop = y-35;
        var deleteBtn = '<img src="' + deleteIconSrc + '" class="deleteBtn" style="position:absolute;top:'+btnTop+'px;left:'+btnLeft+'px;cursor:pointer;width:20px;height:20px;"/>';

        $(".canvas-container").append(deleteBtn);
    }

    function removeFromStorage(canvasObj){
        console.log(canvasObj)
        let found = false

        const fList = thisf2cRef.current
        for (const f2loc of fList){
            if (f2loc.uuid == canvasObj.id){
                const i = fList.indexOf(f2loc)
                let newList
                if (i == 0){
                    newList = fList.slice(1)
                }else{
                    newList = [
                        ...fList.slice(0, i),
                        ...fList.slice(i + 1)
                    ]
                }

                setf2c_ForThisTab(newList)
                console.log(fList)

                found = true
            }
        }

        if(!found){
            const aList = thisa2cRef.current
            for (const a2loc of aList){
                if (a2loc.uuid == canvasObj.id){
                    console.log(a2loc)
                    const i = aList.indexOf(a2loc)
                    let newA2L_list
                    if (i == 0){
                        newA2L_list = aList.slice(1)
                    }else{
                        newA2L_list = [
                            ...aList.slice(0, i),
                            ...aList.slice(i + 1)
                        ]
                    }

                    seta2c_ForThisTab(newA2L_list)

                    //remove from annotations collection
                    let newAnnotList = []
                    console.log(annotsRef.current)
                    console.log(a2loc)
                    for (const annot of annotsRef.current){
                        if (annot._id.toString() != a2loc.annot_id.toString()){
                            console.log("keeping")
                            newAnnotList.push(annot)
                        }else{
                            console.log("deleting")
                            async function deleteAnnot(){
                                await realm_deleteAnnotation(annot._id)
                            }
                            deleteAnnot()
                            
                        }
                    }

                    setAnnotationList(newAnnotList)
                    
                    console.log(aList)
                }
            }
        }
        
    }


    
    return(
        <>
        <div className='floor-layout'>
            <div className='floor-canvas-area'>
                <FabricJSCanvas className="floorcanvas" onReady={onReady} style={{width : x_canvasSize.toString() + "px", height : y_canvasSize.toString() + "px"}} />
                <div className='floor-actions'>
                    <button className='hover:bg-red-100 shadow shadow-gray-400 outline outline-1 text-red-500 px-3 py-1 rounded' onClick={doReset}>Reset Canvas</button>
                    {savedIDState != null ? <button className='hover:bg-green-100 shadow shadow-gray-400 outline outline-1 text-green-600 px-3 py-1 rounded' onClick={updateSave}>Save</button> : <></>}
                    <button className='hover:bg-green-100 shadow shadow-gray-400 outline outline-1 text-green-600 px-3 py-1 rounded' onClick={openSaveDialog}>Save As</button>
                </div>
            </div>
            <div className='floor-right-panel'>
                {thisf2cRef.current != null ?
                <FragmentSelector fragmentList={fragmentList} setFragmentList={setFragmentList} spawnFragment={spawnFragment} f2lRef={thisf2cRef} bulkSpawn={bulkSpawn}></FragmentSelector>
                : <></>}
                <AnnotationCreator selObjRef={selObjRef} f2lRef={thisf2cRef} onAnnotCreated={onAnnotCreated}></AnnotationCreator>
            </div>

        </div>





        {/* Save Floor Dialog */}
        <Dialog open={openDia} handler={toggleDialog} size="sm" className='!text-black'>
          <DialogHeader>
            <h1 className="text-lg font-semibold">Name the new Virtual Floor</h1>
            </DialogHeader>
          <DialogBody>
          
            <Input label='Virtual Floor Name' size='lg' color="indigo" className='!text-2xl !h-12' onChange={(event) => setSaveName(event.target.value)}/>
                    <Typography
                variant="small"
                color="gray"
                className="mt-4 flex items-center gap-1 font-normal"
            >
                <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="currentColor"
                className="-mt-px h-4 w-4"
                >
                <path
                    fillRule="evenodd"
                    d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12zm8.706-1.442c1.146-.573 2.437.463 2.126 1.706l-.709 2.836.042-.02a.75.75 0 01.67 1.34l-.04.022c-1.147.573-2.438-.463-2.127-1.706l.71-2.836-.042.02a.75.75 0 11-.671-1.34l.041-.022zM12 9a.75.75 0 100-1.5.75.75 0 000 1.5z"
                    clipRule="evenodd"
                />
                </svg>
                This will re-name your current tab
            </Typography>

          </DialogBody>
          <DialogFooter className='gap-[69%]'>
          <Button
              variant="text"
              color="red"
              onClick={toggleDialog}
              className="mr-1 text-sm"
            >
              <span>Cancel</span>
            </Button>
            <Button
              variant="text"
              color="green"
              onClick={handleSaveConfirmed}
              className="mr-1 text-sm"
            >
              <span>Save</span>
            </Button>
          </DialogFooter>
        </Dialog>
        </>
    )

}

export default VirtualFloor
