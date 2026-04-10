import WorkspaceRepository, {
  WorkspaceSessionSnapshot,
} from "../repositories/workspaceRepository.ts";

export function createDefaultWorkspaceSession(): WorkspaceSessionSnapshot {
  return {
    version: 1,
    openTabs: [],
    currentTab: {},
    recentlyDeletedIndex: -1,
    workspaceStateByTab: {
      f2c: [],
      a2c: [],
    },
    updatedAt: new Date().toISOString(),
  };
}

function isWorkspaceSessionSnapshot(value: any): value is WorkspaceSessionSnapshot {
  return (
    value &&
    typeof value === "object" &&
    typeof value.version === "number" &&
    Array.isArray(value.openTabs) &&
    typeof value.currentTab === "object" &&
    typeof value.recentlyDeletedIndex === "number" &&
    value.workspaceStateByTab &&
    Array.isArray(value.workspaceStateByTab.f2c) &&
    Array.isArray(value.workspaceStateByTab.a2c)
  );
}

class WorkspaceService {
  constructor(private readonly repository: WorkspaceRepository) {}

  async getWorkspaceSession() {
    const existing = await this.repository.getWorkspaceSession();
    if (existing) {
      return existing;
    }

    return this.repository.saveWorkspaceSession(createDefaultWorkspaceSession());
  }

  async saveWorkspaceSession(snapshot: unknown) {
    if (!isWorkspaceSessionSnapshot(snapshot)) {
      throw new Error("Invalid workspace session payload.");
    }

    const normalized: WorkspaceSessionSnapshot = {
      version: snapshot.version || 1,
      openTabs: snapshot.openTabs,
      currentTab: snapshot.currentTab || {},
      recentlyDeletedIndex: snapshot.recentlyDeletedIndex ?? -1,
      workspaceStateByTab: {
        f2c: snapshot.workspaceStateByTab.f2c,
        a2c: snapshot.workspaceStateByTab.a2c,
      },
      updatedAt: new Date().toISOString(),
    };

    return this.repository.saveWorkspaceSession(normalized);
  }
}

export default WorkspaceService;
