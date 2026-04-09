/**
 * ClusterGraphView — Sigma.js force-directed graph showing cluster themes
 * and their response nodes. Clicking a theme node opens a VirtualFloor tab
 * pre-populated with that cluster's fragments.
 */
import { useEffect, useRef, useState, useCallback } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAtom, useSetAtom } from "jotai";
import { MultiDirectedGraph } from "graphology";
import { Sigma } from "sigma";
import forceAtlas2 from "graphology-layout-forceatlas2";

import { clusters, selectedClusterId, currentTab_atom, openTabs_atom, vfTabReady_atom } from "../state";
import { clusters_findAll, cluster_getFragments } from "../api/dataFacade";
import { pipeline_getGraphData } from "../api/aiServiceFacade";

// ── helpers ────────────────────────────────────────────────────────────────────

function hexToRgba(hex, alpha = 1) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r},${g},${b},${alpha})`;
}

// ── Tooltip component ─────────────────────────────────────────────────────────

function NodeTooltip({ node, position, onClose, onOpenFloor }) {
    if (!node) return null;
    return (
        <div
            className="absolute z-50 bg-white border border-gray-200 rounded-xl shadow-xl p-4 w-64 pointer-events-auto"
            style={{ left: position.x + 16, top: position.y - 8 }}
        >
            <button onClick={onClose} className="absolute top-2 right-3 text-gray-400 hover:text-gray-600 text-lg">×</button>
            <p className="text-xs uppercase tracking-wide text-gray-400 mb-1">
                {node.type === "theme" ? "Theme Cluster" : "Survey Response"}
            </p>
            <p className="font-bold text-gray-800 text-base mb-1">{node.label}</p>
            {node.summary && <p className="text-sm text-gray-600 mb-3">{node.summary}</p>}
            {node.size && node.type === "theme" && (
                <p className="text-xs text-gray-500 mb-3">{node.fragmentCount} responses</p>
            )}
            {node.type === "theme" && (
                <button
                    onClick={() => onOpenFloor(node)}
                    className="w-full py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold transition-colors"
                >
                    Open in Virtual Floor →
                </button>
            )}
        </div>
    );
}

// ── Main view ─────────────────────────────────────────────────────────────────

export default function ClusterGraphView() {
    const location = useLocation();
    const navigate = useNavigate();
    const containerRef = useRef(null);
    const sigmaRef = useRef(null);
    const graphRef = useRef(null);

    const [clusterList, setClusterList] = useAtom(clusters);
    const [selClusterId, setSelClusterId] = useAtom(selectedClusterId);
    const [tabs, setTabs] = useAtom(openTabs_atom);
    const setCurrentTab = useSetAtom(currentTab_atom);
    const setVfTabReady = useSetAtom(vfTabReady_atom);

    const [docId, setDocId] = useState(location.state?.doc_id ?? null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [tooltip, setTooltip] = useState({ node: null, position: { x: 0, y: 0 } });

    // ── Load clusters list for the survey ─────────────────────────────────────
    useEffect(() => {
        if (!docId) return;
        clusters_findAll(docId).then(setClusterList).catch(console.error);
    }, [docId]);

    // ── Build and render the graph once we have clusters ─────────────────────
    useEffect(() => {
        if (!clusterList.length || !containerRef.current) return;
        buildGraph();

        return () => {
            if (sigmaRef.current) {
                sigmaRef.current.kill();
                sigmaRef.current = null;
            }
        };
    }, [clusterList]);

    const buildGraph = async () => {
        setLoading(true);
        setError(null);

        try {
            const graph = new MultiDirectedGraph();
            graphRef.current = graph;

            // Fetch graph data for every cluster and merge into one graph
            await Promise.all(
                clusterList.map(async (cluster) => {
                    const cid = cluster._id.toString();
                    const data = await pipeline_getGraphData(cid);

                    for (const node of data.nodes) {
                        if (!graph.hasNode(node.id)) {
                            graph.addNode(node.id, {
                                label: node.label,
                                x: node.x,
                                y: node.y,
                                size: node.type === "theme" ? 18 : 4,
                                color: node.type === "theme" ? node.color : hexToRgba(node.color, 0.55),
                                nodeType: node.type,
                                summary: cluster.summary ?? "",
                                fragmentCount: cluster.size ?? 0,
                                clusterId: cid,
                            });
                        }
                    }
                    for (const edge of data.edges) {
                        try {
                            graph.addEdge(edge.source, edge.target, {
                                color: "#cbd5e1",
                                size: 0.5,
                            });
                        } catch (_) { /* duplicate edge guard */ }
                    }
                })
            );

            // Run ForceAtlas2 for a nicer layout (seeded from UMAP coordinates)
            forceAtlas2.assign(graph, {
                iterations: 150,
                settings: forceAtlas2.inferSettings(graph),
            });

            // Instantiate Sigma
            if (sigmaRef.current) sigmaRef.current.kill();

            const renderer = new Sigma(graph, containerRef.current, {
                renderEdgeLabels: false,
                defaultEdgeColor: "#cbd5e1",
                defaultNodeColor: "#94a3b8",
                labelThreshold: 6,          // only show labels for nodes with size ≥ 6 (theme nodes)
                labelFont: "Inter, sans-serif",
                labelSize: 13,
                labelWeight: "600",
                nodeReducer: (node, data) => data,
                edgeReducer: (edge, data) => data,
            });

            sigmaRef.current = renderer;

            // ── Hover: show tooltip ───────────────────────────────────────────
            renderer.on("enterNode", ({ node, event }) => {
                const attrs = graph.getNodeAttributes(node);
                setTooltip({
                    node: { id: node, ...attrs },
                    position: { x: event.x, y: event.y },
                });
                renderer.getContainer().style.cursor = "pointer";
            });

            renderer.on("leaveNode", () => {
                renderer.getContainer().style.cursor = "default";
            });

            // ── Click theme node: open VirtualFloor ───────────────────────────
            renderer.on("clickNode", ({ node }) => {
                const attrs = graph.getNodeAttributes(node);
                if (attrs.nodeType === "theme") {
                    openFloorForCluster({ id: node, ...attrs });
                }
            });

            // ── Click background: close tooltip ───────────────────────────────
            renderer.on("clickStage", () => setTooltip({ node: null, position: { x: 0, y: 0 } }));

        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    // ── Open a new VirtualFloor tab pre-populated with cluster fragments ───────
    const openFloorForCluster = useCallback(async (nodeAttrs) => {
        setTooltip({ node: null, position: { x: 0, y: 0 } });

        // Navigate to workspace first
        navigate("/");

        const uuid = crypto.randomUUID();
        const newTab = {
            type: "floor",
            key: uuid,
            existing: false,
            index: tabs.length,
            name: nodeAttrs.label,
            vf_id: null,
            preloadClusterId: nodeAttrs.clusterId,  // VirtualFloor will read this
        };

        setVfTabReady(false);
        setTabs((prev) => [...prev, newTab]);
        setCurrentTab(newTab);
        setSelClusterId(nodeAttrs.clusterId);
    }, [tabs, navigate]);

    // ── Sidebar cluster list panel ─────────────────────────────────────────────
    const clusterPanel = clusterList.map((c) => (
        <div
            key={c._id.toString()}
            className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-50 cursor-pointer"
            onDoubleClick={() => openFloorForCluster({
                id: c._id.toString(),
                label: c.label,
                clusterId: c._id.toString(),
            })}
        >
            <span
                className="w-3 h-3 rounded-full flex-shrink-0"
                style={{ backgroundColor: c.color ?? "#94a3b8" }}
            />
            <div className="min-w-0">
                <p className="text-sm font-semibold text-gray-800 truncate">{c.label ?? "Unlabelled"}</p>
                <p className="text-xs text-gray-500">{c.size} responses</p>
            </div>
        </div>
    ));

    return (
        <div className="flex h-screen w-full overflow-hidden">

            {/* ── Left panel: cluster list ── */}
            <div className="w-64 flex-shrink-0 border-r border-gray-200 bg-white flex flex-col">
                <div className="p-4 border-b border-gray-200">
                    <h2 className="text-lg font-bold text-gray-800">Cluster Graph</h2>
                    <p className="text-xs text-gray-500 mt-0.5">
                        {clusterList.length} themes · double-click to open floor
                    </p>
                </div>

                {/* Doc selector */}
                <div className="p-3 border-b border-gray-100">
                    <label className="block text-xs font-medium text-gray-500 mb-1">Survey doc ID</label>
                    <input
                        type="text"
                        value={docId ?? ""}
                        onChange={e => setDocId(e.target.value.trim() || null)}
                        placeholder="Paste doc_id from ingestion"
                        className="w-full border border-gray-300 rounded px-2 py-1.5 text-xs
                                   focus:outline-none focus:ring-1 focus:ring-blue-400"
                    />
                </div>

                <div className="flex-1 overflow-y-auto p-2 space-y-1">
                    {clusterList.length === 0 && !loading && (
                        <p className="text-xs text-gray-400 px-2 py-4 text-center">
                            No clusters loaded.<br />Enter a doc ID above or run Survey Ingestion first.
                        </p>
                    )}
                    {clusterPanel}
                </div>

                <div className="p-3 border-t border-gray-100">
                    <button
                        onClick={() => navigate("/survey-ingest")}
                        className="w-full py-2 text-sm rounded-lg border border-blue-300 text-blue-600
                                   hover:bg-blue-50 transition-colors font-medium"
                    >
                        + Ingest new survey
                    </button>
                </div>
            </div>

            {/* ── Graph canvas ── */}
            <div className="relative flex-1 bg-gray-50">

                {/* Loading overlay */}
                {loading && (
                    <div className="absolute inset-0 flex items-center justify-center bg-white/70 z-10">
                        <div className="text-center">
                            <div className="text-4xl animate-spin mb-3">⟳</div>
                            <p className="text-gray-600 font-medium">Building graph…</p>
                        </div>
                    </div>
                )}

                {/* Error banner */}
                {error && (
                    <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 px-5 py-3
                                    bg-red-50 border border-red-300 rounded-lg text-red-700 text-sm shadow">
                        {error}
                    </div>
                )}

                {/* Empty state */}
                {!loading && !error && clusterList.length === 0 && (
                    <div className="absolute inset-0 flex items-center justify-center">
                        <div className="text-center text-gray-400">
                            <div className="text-6xl mb-4">◎</div>
                            <p className="text-xl font-semibold mb-2">No clusters to display</p>
                            <p className="text-sm">Enter a survey doc ID in the panel, or run Survey Ingestion first.</p>
                        </div>
                    </div>
                )}

                {/* Legend */}
                {clusterList.length > 0 && !loading && (
                    <div className="absolute bottom-4 left-4 z-10 bg-white border border-gray-200
                                    rounded-lg px-4 py-3 shadow text-xs text-gray-600 space-y-1.5">
                        <div className="flex items-center gap-2">
                            <span className="w-4 h-4 rounded-full bg-blue-500 inline-block"/>
                            <span>Theme node — click to open floor</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="w-2.5 h-2.5 rounded-full bg-blue-300 inline-block"/>
                            <span>Response node</span>
                        </div>
                    </div>
                )}

                {/* Sigma container */}
                <div ref={containerRef} className="w-full h-full" />

                {/* Tooltip */}
                <div className="absolute inset-0 pointer-events-none">
                    <NodeTooltip
                        node={tooltip.node}
                        position={tooltip.position}
                        onClose={() => setTooltip({ node: null, position: { x: 0, y: 0 } })}
                        onOpenFloor={openFloorForCluster}
                    />
                </div>
            </div>
        </div>
    );
}
