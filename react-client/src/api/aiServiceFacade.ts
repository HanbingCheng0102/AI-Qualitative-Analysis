/**
 * Client-side facade for the Python AI service (port 8000).
 * Mirrors the pattern of dataFacade.ts — thin wrappers over fetch calls.
 */

const AI_URI = import.meta.env.VITE_AI_URI ?? "http://localhost:8000";

async function post(path: string, body: object) {
    const res = await fetch(`${AI_URI}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail ?? `AI service error: ${res.status}`);
    }
    return res.json();
}

/**
 * Upload a CSV/XLSX survey file. Runs PII redaction and writes fragments to MongoDB.
 * Returns { doc_id, fragment_count }
 */
export async function pipeline_ingestSurvey(file: File, surveyName: string) {
    const form = new FormData();
    form.append("file", file);
    form.append("survey_name", surveyName);

    const res = await fetch(`${AI_URI}/ingest/survey`, {
        method: "POST",
        body: form,
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail ?? `Ingest error: ${res.status}`);
    }
    return res.json() as Promise<{ doc_id: string; fragment_count: number }>;
}

/**
 * Embed all fragments for a doc_id using sentence-transformers.
 * Returns { embedded_count }
 */
export async function pipeline_embedFragments(docId: string) {
    return post("/embed/fragments", { doc_id: docId }) as Promise<{ embedded_count: number }>;
}

/**
 * Run UMAP + HDBSCAN clustering on embedded fragments.
 * Returns { cluster_count, noise_count, cluster_ids }
 */
export async function pipeline_runClustering(docId: string, minClusterSize = 5) {
    return post("/cluster/run", { doc_id: docId, min_cluster_size: minClusterSize }) as Promise<{
        cluster_count: number;
        noise_count: number;
        cluster_ids: string[];
    }>;
}

/**
 * Label clusters using the configured LLM backend.
 * Returns { labelled: [{ cluster_id, label, summary }] }
 */
export async function pipeline_labelClusters(clusterIds: string[]) {
    return post("/label/clusters", { cluster_ids: clusterIds }) as Promise<{
        labelled: { cluster_id: string; label: string; summary: string }[];
    }>;
}

/**
 * Fetch Sigma.js-ready graph data for a single cluster.
 * Returns { nodes, edges }
 */
export async function pipeline_getGraphData(clusterId: string) {
    const res = await fetch(`${AI_URI}/cluster/${clusterId}/graph-data`);
    if (!res.ok) throw new Error(`Graph data error: ${res.status}`);
    return res.json();
}

/**
 * Record a manual re-coding event (user moved fragment to a different cluster).
 * Returns { ok: true }
 */
export async function pipeline_recordFeedback(
    fragmentId: string,
    fromClusterId: string,
    toClusterId: string,
    userNote = ""
) {
    return post("/feedback/recluster", {
        fragment_id: fragmentId,
        from_cluster_id: fromClusterId,
        to_cluster_id: toClusterId,
        user_note: userNote,
    });
}

/**
 * Get total number of manual placement events for a survey doc.
 * Returns { count: number }
 */
export async function pipeline_getFeedbackCount(docId: string) {
    const res = await fetch(`${AI_URI}/feedback/count/${docId}`);
    if (!res.ok) throw new Error(`Feedback count error: ${res.status}`);
    return res.json() as Promise<{ count: number }>;
}

/**
 * Suggest which manual group a queued fragment belongs to.
 * Called after >= 20 fragments have been placed on the manual canvas.
 * groups = current proximity groups: [{ group_id, fragment_ids }]
 */
export async function pipeline_suggestManualPlacement(
    docId: string,
    fragmentId: string,
    groups: { group_id: string; fragment_ids: string[] }[]
) {
    return post("/suggest/placement", { doc_id: docId, fragment_id: fragmentId, groups }) as Promise<{
        suggestion: { group_id: string | null; confidence: number; new_cluster: boolean } | null;
    }>;
}

/**
 * Persist manual proximity groups as labelled cluster documents.
 * groups = array of { fragment_ids: string[] }
 * Returns { cluster_ids, labelled }
 */
export async function pipeline_saveManualClusters(
    docId: string,
    groups: { fragment_ids: string[] }[]
) {
    return post("/suggest/save", { doc_id: docId, groups }) as Promise<{
        cluster_ids: string[];
        labelled: { cluster_id: string; label: string }[];
    }>;
}

/**
 * Get AI-suggested cluster placements for uncategorised fragments.
 * Should only be called after >= 20 manual placements.
 * Returns { suggestions: [...] }
 */
export async function pipeline_suggestPlacements(docId: string) {
    return post("/feedback/suggest", { doc_id: docId }) as Promise<{
        suggestions: {
            fragment_id: string;
            fragment_name: string;
            fragment_text: string;
            suggested_cluster_id: string;
            suggested_cluster_label: string;
            suggested_cluster_color: string;
            confidence: number;
        }[];
    }>;
}
