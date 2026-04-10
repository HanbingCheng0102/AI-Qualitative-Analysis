import { Db } from "mongodb";

export type WorkspaceSessionSnapshot = {
  version: number;
  openTabs: any[];
  currentTab: any;
  recentlyDeletedIndex: number;
  workspaceStateByTab: {
    f2c: any[][];
    a2c: any[][];
  };
  updatedAt: string;
};

const COLLECTION_NAME = "workspaceSessions";
const DEFAULT_SESSION_ID = "default";

class WorkspaceRepository {
  constructor(private readonly getDb: () => Promise<Db>) {}

  async getWorkspaceSession(): Promise<WorkspaceSessionSnapshot | null> {
    const db = await this.getDb();
    const doc = await db
      .collection<WorkspaceSessionSnapshot & { _id: string }>(COLLECTION_NAME)
      .findOne({ _id: DEFAULT_SESSION_ID });

    if (!doc) {
      return null;
    }

    const { _id, ...snapshot } = doc;
    return snapshot;
  }

  async saveWorkspaceSession(
    snapshot: WorkspaceSessionSnapshot
  ): Promise<WorkspaceSessionSnapshot> {
    const db = await this.getDb();

    await db.collection(COLLECTION_NAME).updateOne(
      { _id: DEFAULT_SESSION_ID },
      {
        $set: {
          ...snapshot,
          updatedAt: new Date().toISOString(),
        },
      },
      { upsert: true }
    );

    const saved = await this.getWorkspaceSession();
    if (!saved) {
      throw new Error("Failed to load workspace session after save.");
    }

    return saved;
  }
}

export default WorkspaceRepository;
