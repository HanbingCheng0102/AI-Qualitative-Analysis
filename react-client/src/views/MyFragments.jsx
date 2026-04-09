import { useAtom } from "jotai"
import { documents, fragments } from "../state"
import FragmentGrid from "../components/FragmentGrid"
import { useEffect, useState } from "react"
import { fragments_findAll } from "../api/dataFacade"
import { Option, Select, Typography } from '@material-tailwind/react';
import FragmentEditorPanel from "../components/FragmentEditorPanel"

function MyFragments(){

    const [fragmentList, setFragmentList] = useAtom(fragments)
    const [subsetList, setSubsetList] = useState([])
    const [docsWithFrags, setDocsWithFrags] = useState([])
    const [documentList] = useAtom(documents)
    const [docIDStr, setDocIDStr] = useState("")
    const [selectedFragment, setSelectedFragment] = useState(null)

    useEffect(() => {
        async function loadAllFrags(){
        const fragList = await fragments_findAll()
        //console.log("items: " + fragList.length)
        let newlist = []
        for (const doc of fragList){
            newlist.push(doc)
        }
        setSubsetList(newlist)
        setFragmentList(newlist)

        }

        loadAllFrags()

    }, [])

    //finds all documents that have a fragment, and adds them to the dropdown
    useEffect(() => {
        let docsWithFragsBuilder = []
        let foundIDList = []
        for (const frag of fragmentList){
            if (!foundIDList.includes(frag.docid.toString())){
                for (const doc of documentList){
                    if(doc._id.toString() == frag.docid.toString()){
                        docsWithFragsBuilder.push(doc)
                        foundIDList.push(doc._id.toString())
                    }
                }
            }  
        }
        setDocsWithFrags(docsWithFragsBuilder)
    }, [fragmentList, documentList])

    const filterFrags = (docIDstr) => {
        if (docIDstr == ""){
            setSubsetList(fragmentList)
        }else{
            let newList = []
            for (const frag of fragmentList){
                if (frag.docid.toString() == docIDstr){
                    newList.push(frag)
                }
            }
            setSubsetList(newList)
        }
        
    }

    

    return (
    <div className="flex flex-col h-full overflow-hidden p-4 gap-3">
      <div className="flex items-center gap-4 flex-shrink-0">
        <h1 className="text-lg font-bold text-gray-900">My Fragments</h1>
        <div className="w-72 text-black z-50">
          <Select size="md" label="Filter by document" className="bg-white"
              onChange={(val) => {
                  filterFrags(val)
                  setDocIDStr(val)
              }} value={docIDStr}>
              <Option value={""} key={"any"} className='text-left'>
              <Typography color="black">*ALL DOCUMENTS*</Typography>
              </Option>
              {docsWithFrags.map((item, index) => (
                  <Option value={item._id.toString()} key={item.name + index} className='text-left' >
                      <Typography color="black">
                          {item.name + " - " + item._id.toString()}
                      </Typography>
                  </Option>
              ))}
          </Select>
        </div>
      </div>

      <div className="flex flex-1 gap-4 min-h-0 overflow-hidden">
        <FragmentGrid subsetList={subsetList} selectedFragment={selectedFragment} setSelectedFragment={setSelectedFragment}></FragmentGrid>
        {selectedFragment != null ? <FragmentEditorPanel selectedFragment={selectedFragment}></FragmentEditorPanel> : <></>}
      </div>
    </div>
    )
}

export default MyFragments