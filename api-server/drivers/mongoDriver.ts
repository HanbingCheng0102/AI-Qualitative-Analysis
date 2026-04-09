import { MongoClient, ObjectId } from "mongodb";
import StorageDriver from "./storageDriver.ts";
import IDedObject from "./IDedObject.ts";


interface MongoDriverOptions {
  connectionString: string;
  dbName: string;
}

class MongoDriver implements StorageDriver {

  private options: MongoDriverOptions;
  private clientPromise: Promise<MongoClient> | null;

  constructor(options: MongoDriverOptions) {
    this.options = options;
    this.clientPromise = null;
  }

  protected normalizeId(id: string): ObjectId {
    return new ObjectId(id);
  }

  public async getDb() {

    // Prefer MONGO_DB_NAME env var; fall back to parsing the URI path
    const dbName =
      process.env.MONGO_DB_NAME ||
      new URL(this.options.connectionString).pathname.replace(/((^\/+)|(\/+$))/g, "");

    if (!dbName) throw new Error("Database name is not specified. Set MONGO_DB_NAME in your .env file.");

    if (!this.clientPromise) {
      this.clientPromise = MongoClient.connect(this.options.connectionString);
    }

    const client = await this.clientPromise;
    return client.db(dbName);
  }

  public async addNewItem(collectionName: string, item: any) {
    const db = await this.getDb();
    const result = await db.collection(collectionName).insertOne(item);
    return result.insertedId.toString();
  }

  public async updateItem(collectionName: string, id: string, newItem: IDedObject) {
    const db = await this.getDb();

    console.log(`Updating item in collection ${collectionName} with id ${id} and new data:`, newItem);

    // Never allow _id mutation
    if(newItem._id) {
      const { _id, ...rest } = newItem;
    } else {
      var rest = newItem;
    }

    const updateDoc = { $set: rest };

    const result = await db
      .collection(collectionName)
      .updateOne({ _id: this.normalizeId(id) }, updateDoc);

    return result.modifiedCount;
  }

  public async deleteFragment(fragId: string) {
    const db = await this.getDb();
    await db.collection("fragments").deleteOne({ _id: this.normalizeId(fragId) });
  }

  public async deleteDocument(docId: string) {
    const db = await this.getDb();
    const normalizedDocId = this.normalizeId(docId);
    await db.collection("fragments").deleteMany({ docid: normalizedDocId });
    await db.collection("documents").deleteOne({ _id: normalizedDocId });
  }

  public async deleteAnnotation(annotationId: string) {
    const db = await this.getDb();
    await db.collection("annotations").deleteOne({ _id: this.normalizeId(annotationId) });
  }

  public async getItem(collectionName: string, itemId: string) {
    const db = await this.getDb();
    return db.collection(collectionName).findOne({ _id: this.normalizeId(itemId) });
  }

  public async getAllFragments_fromSpecificDoc(docId: string) {
    const db = await this.getDb();
    return db.collection("fragments").find({ docid: this.normalizeId(docId) }).toArray();
  }

  public async getAllAnnotations_fromSpecificFragment(fragId: string) {
    const db = await this.getDb();
    const normalizedFragId = this.normalizeId(fragId);
    return db.collection("annotations").find({ linkedFragments: { $in: [normalizedFragId] } }).toArray();
  }

  public async tagItem(collectionName: string, itemId: string, tag: string) {
    const db = await this.getDb();
    await db.collection(collectionName).updateOne(
      { _id: this.normalizeId(itemId) },
      { $addToSet: { tags: tag } }
    );
  }

  public async searchByTagList_OR(collectionName: string, tagList: string[]) {
    const db = await this.getDb();
    return db.collection(collectionName).find({ tags: { $in: tagList } }).toArray();
  }

  public async searchByTagList_AND(collectionName: string, tagList: string[]) {
    const db = await this.getDb();
    return db.collection(collectionName).find({ tags: { $all: tagList } }).toArray();
  }

  public async getAllDocuments() {
    const db = await this.getDb();
    return db.collection("documents").find({}).toArray();
  }

  public async getAllFragments() {
    const db = await this.getDb();
    return db.collection("fragments").find({}).toArray();
  }

  public async getAllAnnotations() {
    const db = await this.getDb();
    return db.collection("annotations").find({}).toArray();
  }

  public async getAllFloors(): Promise<any[]> {
    const db = await this.getDb();
    return db.collection("virtualFloors").find({}).toArray();
  }

  public async getClusters(surveyDocId: string): Promise<any[]> {
    const db = await this.getDb();
    return db.collection("clusters").find({ survey_doc_id: this.normalizeId(surveyDocId) }).toArray();
  }

  public async getCluster(clusterId: string): Promise<any> {
    const db = await this.getDb();
    return db.collection("clusters").findOne({ _id: this.normalizeId(clusterId) });
  }

  public async getFragmentsByCluster(clusterId: string): Promise<any[]> {
    const db = await this.getDb();
    return db.collection("fragments").find({ cluster_id: this.normalizeId(clusterId) }).toArray();
  }

  public async recordClusterFeedback(feedbackObj: any): Promise<string> {
    const db = await this.getDb();
    const result = await db.collection("clusterFeedback").insertOne(feedbackObj);
    return result.insertedId.toString();
  }

  public async updateClusterLabel(clusterId: string, newLabel: string): Promise<number> {
    const db = await this.getDb();
    const result = await db.collection("clusters").updateOne(
      { _id: this.normalizeId(clusterId) },
      { $set: { label: newLabel } }
    );
    return result.modifiedCount;
  }

  public async updateFragmentCluster(fragmentId: string, newClusterId: string): Promise<number> {
    const db = await this.getDb();
    const result = await db.collection("fragments").updateOne(
      { _id: this.normalizeId(fragmentId) },
      { $set: { feedback_cluster_id: this.normalizeId(newClusterId) } }
    );
    return result.modifiedCount;
  }

  /**
   * Delete an entire survey dataset: document, all its fragments, clusters, and feedback.
   */
  public async deleteSurveyDataset(docId: string): Promise<void> {
    const db = await this.getDb();
    const oid = this.normalizeId(docId);

    // Find cluster IDs for this survey so we can delete feedback too
    const clusterIds = (await db.collection("clusters").find({ survey_doc_id: oid }, { projection: { _id: 1 } }).toArray())
      .map(c => c._id);

    await db.collection("clusterFeedback").deleteMany({ doc_id: oid });
    if (clusterIds.length) {
      await db.collection("clusterFeedback").deleteMany({ to_cluster_id: { $in: clusterIds } });
    }
    await db.collection("clusters").deleteMany({ survey_doc_id: oid });
    await db.collection("fragments").deleteMany({ docid: oid });
    await db.collection("documents").deleteOne({ _id: oid });
  }

}


export default MongoDriver;