import { parse } from "flatted";

export function stripCanvasObject(entry) {
  if (!entry || typeof entry !== "object") {
    return entry;
  }

  const { canvasObj, ...rest } = entry;
  return rest;
}

export function sanitizeWorkspaceStateByTab(stateByTab = { f2c: [], a2c: [] }) {
  return {
    f2c: (stateByTab.f2c ?? []).map((tabEntries) =>
      (tabEntries ?? []).map((entry) => stripCanvasObject(entry))
    ),
    a2c: (stateByTab.a2c ?? []).map((tabEntries) =>
      (tabEntries ?? []).map((entry) => stripCanvasObject(entry))
    ),
  };
}

export function createDefaultWorkspaceSession() {
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

export function normalizeFloorRecord(floor) {
  if (!floor) {
    return floor;
  }

  if (typeof floor.floor === "string") {
    try {
      return {
        ...floor,
        floor: parse(floor.floor),
      };
    } catch (_error) {
      return floor;
    }
  }

  return floor;
}

export function sanitizeFloorPayload(floorObject, name) {
  return {
    name,
    floor: {
      f2c: (floorObject?.f2c ?? []).map((entry) => stripCanvasObject(entry)),
      a2c: (floorObject?.a2c ?? []).map((entry) => stripCanvasObject(entry)),
    },
  };
}
