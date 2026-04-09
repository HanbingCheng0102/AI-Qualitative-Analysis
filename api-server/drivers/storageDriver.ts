
/**
 * An interface for NIE storage drivers. This interface defines the methods that a storage driver must implement to be used with NIE.
 */
interface StorageDriver {

    addNewItem(collectionName: string, item: any): Promise<string>;
    updateItem(collectionName: string, id: string, newItem: any): Promise<number>;
    deleteFragment(fragId: string): Promise<void>;
    deleteDocument(docId: string): Promise<void>;
    deleteAnnotation(annotationId: string): Promise<void>;
    getItem(collectionName: string, itemId: string): Promise<any>;

    getAllFragments_fromSpecificDoc(docId: string): Promise<any[]>;

    getAllAnnotations_fromSpecificFragment(fragId: string): Promise<any[]>;

    tagItem(collectionName: string, itemId: string, tag: string): Promise<void>;

    searchByTagList_OR(collectionName: string, tagList: string[]): Promise<any[]>;

    searchByTagList_AND(collectionName: string, tagList: string[]): Promise<any[]>;

    getAllDocuments(): Promise<any[]>;

    getAllFragments(): Promise<any[]>;

    getAllAnnotations(): Promise<any[]>;

    getAllFloors(): Promise<any[]>;

    getClusters(surveyDocId: string): Promise<any[]>;

    getCluster(clusterId: string): Promise<any>;

    getFragmentsByCluster(clusterId: string): Promise<any[]>;

    recordClusterFeedback(feedbackObj: any): Promise<string>;

    updateClusterLabel(clusterId: string, newLabel: string): Promise<number>;

    updateFragmentCluster(fragmentId: string, newClusterId: string): Promise<number>;
}


// TODO: Define and use proper types for fragments, tags, documents, and annotations instead of 'any'

export default StorageDriver;