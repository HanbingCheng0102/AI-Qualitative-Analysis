import { Card, CardBody } from "@material-tailwind/react"
import DOMPurify from "dompurify"
import { useAtom } from "jotai"
import { annotations } from "../state"
import { useEffect, useState } from "react"

function FragmentEditorPanel({selectedFragment}){

    const [annotationList, setAnnotationList] = useAtom(annotations)
    const [matchingAnnotsList, setMatchingAnnotsList] = useState([])

    useEffect(() => {
        let newList = []
        for (const annot of annotationList){
            console.log(annot.linkedFragments + " - " + selectedFragment._id)
            for (const lf of annot.linkedFragments){
                if(lf.toString() == selectedFragment._id.toString()){
                    newList.push(annot)
                }
            }
        }
        setMatchingAnnotsList(newList)
        console.log(newList)
    }, [annotationList, selectedFragment])

    return (
        <>
        <div className="w-80 flex-shrink-0 overflow-y-auto">
        <Card className="w-full h-full">
        <CardBody>
            <h1 className="mb-4 pb-4 text-xl font-bold leading-none tracking-tight text-gray-900 md:text-base lg:text-base dark:text-white">Selected Fragment</h1>
            <div className="pl-2 pb-6 text-left text-black">
                <b>{selectedFragment.name}</b> <br/>
                <small><b>ID: </b> {selectedFragment._id.toString()}</small> <br/>
                {'type' in selectedFragment ? <small><b>Type: </b>{selectedFragment.type}</small>: <></>}
            </div>
            <div className="h-80">
                <div className="html-content-view !max-h-80 " dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(selectedFragment.html) }} /> 
            </div>

            <h2 className="mb-4 pt-8 text-xl font-bold leading-none tracking-tight text-gray-900 md:text-sm lg:text-sm dark:text-white">Annotations</h2>
            <div className="h-40 overflow-y-auto overflow-x-hidden">
                {matchingAnnotsList.length > 0 ? 
                    matchingAnnotsList.map((item, index) => (
                        <>
                        <div className="relative left-4 h-11" key={index}>
                            <div className='annot-box shadow-lg' style={{backgroundColor: item.color}} ></div>
                            <p className="font-semibold text-black text-left pl-10 pt-1">{item.content}</p>
                        </div>
                        </>
                    ))
                : <i>No annotations found</i>}

            </div>
            

            <h2 className="mb-4 pt-8 text-xl font-bold leading-none tracking-tight text-gray-900 md:text-sm lg:text-sm dark:text-white">Editor goes here</h2>
            
        </CardBody>
        </Card>
        </div>
        
        </>
    )
}

export default FragmentEditorPanel