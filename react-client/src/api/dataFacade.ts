import { extractAllInterviewDialogueSections, extractAllSurveyQuestions, extractAllTextualFragments, HTMLByAttribute, HTMLByAttributeValue, HTMLByTag, HTMLByTagValueContains } from './fragment.js';

import { stringify } from 'flatted';
import { createFloor, getBootstrapData, getFloors, updateFloor } from './workspaceClient';
import { normalizeFloorRecord, sanitizeFloorPayload } from '../stateSerialization';

// We have contrived the RPC API to mirror the StorageDriver interface, so we can use 
// it as a type here for better type safety and autocompletion when calling storage methods.
import StorageDriver from "../../../api-server/drivers/storageDriver.ts";


/**
 * Our storage object becomes a simple proxy over the RPC API, allowing us to call methods as if they were 
 * local async functions,  while they are actually making network requests to the server.
 */
console.log(`Initializing storage proxy with API URI: ${import.meta.env.VITE_API_URI}`);
const storage = new Proxy({} as StorageDriver, {
    get(_, method) {

        return async (...args: any[]) => {
            let apiuri = import.meta.env.VITE_API_URI;
            let slash = apiuri.endsWith("/") ? "" : "/"
            const { result } = await fetch(`${apiuri}${slash}rpc`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ method, args })
            }).then(r => r.json());

            return result;
        };

    }
});



/**
 * TODO: All this logic needs refactoring into a proper model; see /model/ for the beginnings of this. 
 * The dataFacade should ideally just be a thin wrapper around the storage proxy, and all the logic for 
 * how to use it should be in the model layer.
 */


/** 
 * Finds all fragments currently linked to this document in the fragments container
 * Returns an object containing lists of both fragment types: HTML and Binary.
 *
 * @export
 * @param {ObjectId} doc_id
 * @return {Object.<string, Array<String|BinaryData>>} 
 */
export async function fragments_search_by_linked_document(doc_id) {
    const rawFragList = await storage.getAllFragments_fromSpecificDoc(doc_id)
    let htmlfragList = []
    let binaryfragList = []

    for (const frag of rawFragList) {
        if (frag.html != null) {
            htmlfragList.push(frag)
        } else {
            binaryfragList.push(frag)
        }
    }

    const fragments = {
        binaryDataFrags: binaryfragList,
        htmlfragList: htmlfragList
    }

    return fragments
}

//dont use this directly
async function document_add_data(data, filepath, type, tags = []) {

    const filename = filepath.split("/").at(-1)

    const newdoc = {
        name: filename,
        data: data,
        html: null,
        type: type,
        tags: tags
    }

    const id = await storage.addNewItem("documents", newdoc)

    return id
}

/**
 * Adds a new document to the collection, using the provided html string as the document's content. Takes a filepath to use as the document name, as well as a type to use for images. Returns the ObjectID for the new document.
 * 
 *
 * @export
 * @param {string} html
 * @param {string} filepath
 * @param {string} type
 * @param {Array<string>} [tags=[]]
 * @return {ObjectId} id
 */
export async function document_add_html(html, filepath, type, tags = []) {

    const filename = filepath.split("/").at(-1)

    const newdoc = {
        name: filename,
        data: null,
        html: html,
        type: type,
        tags: tags
    }

    const id = await storage.addNewItem("documents", newdoc)

    return id
}

/**
 * Stores an HTML based fragment in the fragments container. Requires a documentID.
 * Returns the id mongodb assigned to the fragment
 *
 * @export
 * @param {string} html
 * @param {ObjectId} docid
 * @param {string} [fragName="testFragment"]
 * @param {string} type
 * @param {Array<string>} [tags=[]]
 * @return {ObjectId} 
 */
export async function fragment_add_html(html, docid, fragName = "testFragment", type, coords = null, tags = []) {

    const newfrag = {
        name: fragName,
        docid: docid,
        html: html,
        data: null,
        type: type,
        coords: coords,
        tags: tags
    }

    const id = await storage.addNewItem("fragments", newfrag)

    return id
}


/**
 * Stores an non-HTML based fragment in the fragments container, as a binary object.
 * Requires a documentID.
 * Returns the id mongodb assigned to the fragment
 *
 * @export
 * @param {BinaryData} data
 * @param {ObjectId} docid
 * @param {string} [fragName="testFragment"]
 * @return {ObjectId} 
 */
export async function fragment_add_data(data, docid, fragName = "testFragment", type, tags = []) {

    const newfrag = {
        name: fragName,
        docid: docid,
        html: null,
        data: data,
        type: type,
        tags: tags
    }

    const id = await storage.addNewItem("fragments", newfrag)

    return id
}


/**
 * Fetches a fragment from the fragments container using the fragmentID.
 * Returns the object
 *
 * @export
 * @param {ObjectId} id
 * @return {BinaryData|string} 
 */
export async function fragment_find(id) {

    const newfrag = await storage.getItem("fragments", id)
    return newfrag

}

/**
 * Fetches a document from the documents container using the documentID.
 * Returns the object
 *
 * @export
 * @param {ObjectId} id
 * @return {object} 
 */
export async function document_find(id) {

    const newDoc = await storage.getItem("documents", id)
    return newDoc
}

/**
 * Fetches a annotation from the annotations container using the annotationID.
 * Returns the object
 *
 * @export
 * @param {ObjectId} id
 * @return {object} 
 */
export async function annotation_find(id) {

    const newDoc = await storage.getItem("annotations", id)
    return newDoc
}




/**
 * Deletes a document from the documents container using a documentID. Returns a DeleteResult for confirmation.
 * WILL ALSO DELETE ALL FRAGMENTS LINKED TO THE DOC.
 *
 * @export
 * @param {ObjectId} id
 * @return {DeleteResult} 
 */
export async function document_delete(id) { return await storage.deleteItem("documents", id) }


/**
 * Deletes a fragment from the fragments container using a fragmentID. Returns a DeleteResult for confirmation.
 *
 * @export
 * @param {ObjectId} id
 * @return {DeleteResult} 
 */
export async function fragment_delete(id) { return await storage.deleteItem("fragments", id) }


/**
 * Searches through a registered html document for html sections with matching attributes. Returns a list of the tag sections that match
 *
 * @export
 * @param {ObjectId} docid
 * @param {String} attribute
 * @return {Array<String>} 
 */
export async function document_searchContentsFor_HTMLattribute(docid, attribute) {

    let matches = []
    const doc = await document_find(docid)
    if (doc.html != null) {
        matches = await HTMLByAttribute(doc.html, attribute)
    } else {
        console.error("File has no HTML content: " + docid)
    }

    return matches

}

/**
 * Searches through a registered html document for html sections with matching attribute-value pairs. Returns a list of the tag sections that match
 *
 * @export
 * @param {ObjectId} docid
 * @param {String} attribute
 * @param {String} value
 * @return {Array<String>} 
 */
export async function document_searchContentsFor_HTMLattributeValue(docid, attribute, value) {

    let matches = []
    const doc = await document_find(docid)

    if (doc.html != null) {
        matches = await HTMLByAttributeValue(doc, attribute, value)
    } else {
        console.error("File has no HTML content: " + docid)
    }

    return matches

}

/**
 *
 * Searches through a registered html document for html sections with matching tag-value pairs. Returns a list of the tag sections that match.
 * Provides the option to specify tag class, for greater refinement.
 * 
 * Leaving the value field null means all matching tags, regardless of tag-value will be returned.
 *
 * @export
 * @param {ObjectId} docid
 * @param {string} tag
 * @param {string} value
 * @param {string} [t_class=null]
 * @return {*} 
 */
export async function document_searchContentsFor_HTMLTagValue(docid, tag, value = null, t_class = null) {
    let matches = []
    const doc = await document_find(docid)

    if (doc.html != null) {
        if (value != null) {
            matches = await HTMLByTagValueContains(doc, tag, value, t_class)
        } else {
            matches = await HTMLByTag(doc, tag, t_class)
        }
    } else {
        console.error("File has no HTML content: " + docid)
    }

    return matches
}


/**
 * Adds a tag (string) to an existing document. Returns 0 if successful, -1 otherwise.
 *
 * @export
 * @param {ObjectId} docid
 * @param {string} tag
 * @return {number} 
 */
export async function document_addTag(docid, tag) {
    const res = await storage.tagItem("documents", docid, tag);
    return res;
}


/**
 * Adds a tag (string) to an existing fragment. Returns 0 if successful, -1 otherwise.
 *
 * @export
 * @param {ObjectId} fragid
 * @param {string} tag
 * @return {number} 
 */
export async function fragment_addTag(fragid, tag) {
    const res = await storage.tagItem("fragments", fragid, tag);
    return res;
}


/**
 * Adds a tag (string) to an existing annotation. Returns 0 if successful, -1 otherwise.
 *
 * @export
 * @param {ObjectId} fragid
 * @param {string} tag
 * @return {number} 
 */
export async function annotation_addTag(fragid, tag) {
    const res = await storage.tagItem("annotations", fragid, tag);
    return res;
}


/**
 * Retrieves all documents tagged with AT LEAST ONE of the tags in tagList.
 *
 * @export
 * @param {Array<string>} tagList
 * @return {Array<object>} docs
 */
export async function document_searchByTagsList_OR(tagList) {
    const docs = await storage.searchByTagList_OR("documents", tagList)
    return docs
}

/**
 * Retrieves all documents tagged with ALL of the tags in tagList.
 *
 * @export
 * @param {Array<string>} tagList
 * @return {Array<object>} docs
 */
export async function documents_searchByTagsList_AND(tagList) {
    const docs = await storage.searchByTagList_AND("documents", tagList)
    return docs
}

/**
 * Retrieves all fragments tagged with AT LEAST ONE of the tags in tagList.
 *
 * @export
 * @param {Array<string>} tagList
 * @return {Array<object>} docs
 */
export async function fragment_searchByTagsList_OR(tagList) {
    const frags = await storage.searchByTagList_OR("fragments", tagList)
    return frags
}


/**
 * Retrieves all fragments tagged with ALL of the tags in tagList.
 *
 * @export
 * @param {Array<string>} tagList
 * @return {Array<object>} docs
 */
export async function fragment_searchByTagsList_AND(tagList) {
    const frags = await storage.searchByTagList_AND("fragments", tagList)
    return frags
}

/**
 * Retrieves all annotations tagged with AT LEAST ONE of the tags in tagList.
 *
 * @export
 * @param {Array<string>} tagList
 * @return {Array<object>} docs
 */
export async function annotation_searchByTagList_OR(tagList) {
    const frags = await storage.searchByTagList_OR("annotations", tagList)
    return frags
}


/**
 * Retrieves all annotations tagged with ALL of the tags in tagList.
 *
 * @export
 * @param {Array<string>} tagList
 * @return {Array<object>} docs
 */
export async function annotation_searchByTagList_AND(tagList) {
    const frags = await storage.searchByTagList_AND("annotations", tagList)
    return frags
}


/**
 *  Creates an annotation from html content and links it to the available fragments. Options for naming and tagging the annotation are included.
 * 
 *
 * @export
 * @param {string} htmlContent
 * @param {Array<ObjectId>} fragmentIDList
 * @param {Array<string>} [tags=[]]
 * @param {string} [annotationName="New annotation"]
 * @return {ObjectId} insertedID 
 */
export async function annotation_create(htmlContent, fragmentIDList, color, tags = [], annotationName = "New annotation") {
    const newAnnot = {
        name: annotationName,
        content: htmlContent,
        color: color,
        linkedFragments: fragmentIDList,
        tags: tags,
    }

    const insertedId = await storage.addNewItem("annotations", newAnnot)
    return insertedId
}


/**
 *  Gets all the annotations linked to a specific fragment.
 *
 * @export
 * @param {ObjectId} fragmentID
 * @return {Array<object>} 
 */
export async function annotation_search_by_linked_fragmentID(fragmentID) {
    const annotations = await storage.getAllAnnotations_fromSpecificFragment(fragmentID)
    return annotations
}


/**
 * Finds all HTML tags containing text and returns them, in a list of html tags
 *
 * @export
 * @param {string} html
 * @return {Array<string>} 
 */
export function HTML_2_Textual_Fragments(html) {
    return extractAllTextualFragments(html)
}


/**
 * Searches html representations of the .xlsx survey format, returning all questions and response pairs, denoted by the .qna class.
 * Returns a list of html strings
 *
 * @export
 * @param {string} html
 * @return {Array<string>} 
 */
export function HTML_2_Dialogue_List(html) {
    return extractAllInterviewDialogueSections(html)
}


/**
 * Searches html representations of the known .txt transcript otter.ai format, returning all dialogue sections as a list, as dented by the .dialogue class.
 *
 * @export
 * @param {string} html
 * @return {Array<string>} 
 */
export function HTML_2_QnA_List(html) {
    return extractAllSurveyQuestions(html)
}



/**
 * Get HTML tags containing each answer to a specific survey question. Provide the document ID of the survey, and the name of the question you would like to query.
 * 
 *
 * @export
 * @param {ObjectId} doc_id
 * @param {string} questionName
 * @return {Array<string>} questionList [HTML String]
 */
export async function survey_AnswersToASpecificQuestion(doc_id, questionName) {
    const doc = await document_find(doc_id)

    let questionList = []

    if (doc.type != "survey") {
        console.error("Wrong doc type! It must be a survey.")
    } else {
        const html = await doc.html

        const qnas = await HTMLByTagValueContains(html, "li", questionName, "qna")

        for (const qna of qnas) {
            const a = await HTMLByTag(qna, "p", "answer")
            questionList.push(a[0])
        }
        //console.log(qnas)

    }

    return questionList

}

/**
 * Get HTML tags containing each dialogue section from a specific speaker. Provide the document ID of the transcript, and the name of the speaker you would like to query.
 * 
 *
 * @export
 * @param {ObjectId} doc_id
 * @param {string} speakerName
 * @return {Array<string>} questionList [HTML String]
 */
export async function transcript_DialogueFromASpecificSpeaker(doc_id, speakerName) {
    const doc = await document_find(doc_id)

    let dialogueList = []

    if (doc.type != "transcript") {
        console.error("Wrong doc type! It must be a transcript. : " + doc.type)
    } else {
        const html = await doc.html

        const sections = await HTMLByTagValueContains(html, "li", speakerName, "dialogue")

        for (const sect of sections) {
            const dialogue = await HTMLByTag(sect, "p", "speech")
            dialogueList.push(dialogue[0])
        }
    }

    return dialogueList

}


function prepareFloorObject(floor_object, name) {
    //removes any circular references that stop JSON parsing from working when saving the floor.
    let flat_floor = stringify(floor_object)

    console.log("Original floor object for saving:", floor_object);
    console.log("Flattened floor object for saving:", flat_floor);

    let flatFloor = {
        floor: flat_floor,
        name: name
    }

    return flatFloor;
}


/**
 * Saves a new virtual floor. Takes an object containing the a2c and f2c object for the new floor, and returns the ID of the new floor.
 * 
 *
 * @export
 * @param {object} floor_object
 * @param {string} name
 * @return {ObjectId} insertedID 
 */
export async function floor_save(floor_object, name) {
    const savedFloor = await createFloor(sanitizeFloorPayload(floor_object, name))
    return savedFloor._id
}

/**
 * Resaves an existing virtual floor. Takes an updated object containing the a2c and f2c object for the new floor, and returns the ID of the new floor.
 * 
 *
 * @export
 * @param {object} floor_object
 * @param {string} name
 * @return {ObjectId} insertedID 
 */
export async function floor_update(floor_object, floor_id, name) {
    await updateFloor(floor_id, sanitizeFloorPayload(floor_object, name))
    return floor_id
}

/**
 * Fetches all documents from the documents container
 * Returns a list of document objects
 *
 * @export
 * @return {Array<object>} 
 */
export async function documents_findAll() {
    const docs = await storage.getAllDocuments()
    return docs
}

/**
 * Fetches all annotations from the annotations container
 * Returns a list of annotation objects
 *
 * @export
 * @return {Array<object>} 
 */
export async function annotations_findAll() {
    const annots = await storage.getAllAnnotations()
    return annots
}

/**
 * Fetches all fragments from the fragments container
 * Returns a list of fragment objects
 *
 * @export
 * @return {Array<object>} 
 */
export async function fragments_findAll() {
    const fragments = await storage.getAllFragments()
    return fragments
}

/**
 * Fetches all floors from the floors container
 * Returns a list of floor objects
 *
 * @export
 * @return {Array<object>} 
 */
export async function floors_findAll() {
    const vfs = await getFloors()
    return vfs.map(normalizeFloorRecord)
}

export async function bootstrap_findAll() {
    const bootstrap = await getBootstrapData()
    return {
        documents: bootstrap.documents ?? [],
        annotations: bootstrap.annotations ?? [],
        floors: (bootstrap.floors ?? []).map(normalizeFloorRecord)
    }
}

/**
 * Fetches all clusters for a given survey document.
 *
 * @export
 * @param {string} surveyDocId
 * @return {Array<object>}
 */
export async function clusters_findAll(surveyDocId: string) {
    return await storage.getClusters(surveyDocId);
}

/**
 * Fetches a single cluster by ID.
 *
 * @export
 * @param {string} clusterId
 * @return {object}
 */
export async function cluster_find(clusterId: string) {
    return await storage.getCluster(clusterId);
}

/**
 * Fetches all fragments belonging to a cluster.
 *
 * @export
 * @param {string} clusterId
 * @return {Array<object>}
 */
export async function cluster_getFragments(clusterId: string) {
    return await storage.getFragmentsByCluster(clusterId);
}

/**
 * Records a manual re-coding event (user moved a fragment to a different cluster).
 *
 * @export
 * @param {object} feedbackObj - { fragment_id, from_cluster_id, to_cluster_id, user_note }
 * @return {string} inserted ID
 */
export async function cluster_recordFeedback(feedbackObj: any) {
    return await storage.recordClusterFeedback(feedbackObj);
}

/**
 * Updates the label of a cluster (after LLM re-labelling or manual edit).
 *
 * @export
 * @param {string} clusterId
 * @param {string} newLabel
 * @return {number} modified count
 */
export async function cluster_updateLabel(clusterId: string, newLabel: string) {
    return await storage.updateClusterLabel(clusterId, newLabel);
}

/**
 * Records that a fragment has been manually reassigned to a different cluster.
 *
 * @export
 * @param {string} fragmentId
 * @param {string} newClusterId
 * @return {number} modified count
 */
export async function cluster_updateFragmentAssignment(fragmentId: string, newClusterId: string) {
    return await storage.updateFragmentCluster(fragmentId, newClusterId);
}

/** Save a researcher note on a fragment. */
export async function fragment_saveNote(fragmentId: string, note: string) {
    return await storage.updateItem("fragments", fragmentId, { note });
}

/** Save a researcher note on a cluster. */
export async function cluster_saveNote(clusterId: string, note: string) {
    return await storage.updateItem("clusters", clusterId, { note });
}

/** Delete an entire survey dataset (document, fragments, clusters, feedback). */
export async function survey_delete(docId: string) {
    return await storage.deleteSurveyDataset(docId);
}

/** Fetch all fragments belonging to a specific document (raw array). */
export async function fragments_findByDoc(docId: string): Promise<any[]> {
    return await storage.getAllFragments_fromSpecificDoc(docId);
}
