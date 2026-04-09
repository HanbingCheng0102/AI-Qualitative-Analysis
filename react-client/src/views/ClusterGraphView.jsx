/**
 * ClusterGraphView — interactive React Flow graph.
 *
 * Layout  : grid of cluster "cells". Each cell has the theme node at the top
 *           and its response nodes in a 2-column grid below it, with enough
 *           padding that no two clusters overlap.
 *
 * Drag UX : while dragging a response, the nearest in-range theme node pulses
 *           with a glowing ring. On release the edge is rewired and the backend
 *           is notified.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import {
    ReactFlow, Background, Controls, MiniMap,
    useNodesState, useEdgesState,
    Handle, Position, useReactFlow, ReactFlowProvider,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useNavigate, useLocation } from "react-router-dom";
import { useAtom } from "jotai";

import { clusters } from "../state";
import { clusters_findAll, cluster_getFragments, fragment_saveNote, cluster_saveNote } from "../api/dataFacade";
import {
    pipeline_recordFeedback,
    pipeline_getFeedbackCount,
    pipeline_suggestPlacements,
} from "../api/aiServiceFacade";

// ─────────────────────────────────────────────────────────────────────────────
// Layout constants
// ─────────────────────────────────────────────────────────────────────────────

const THEME_W    = 200;   // theme node width
const THEME_H    = 110;   // theme node approx height (text + note btn)
const RESP_W     = 170;   // response card width
const RESP_H     = 100;   // response card approx height
const RESP_COLS  = 2;     // response cards per row
const RESP_GAP_X = 12;    // horizontal gap between response cards
const RESP_GAP_Y = 12;    // vertical gap between response cards
const CELL_PAD_X = 60;    // horizontal padding between cluster cells
const CELL_PAD_Y = 80;    // vertical padding between cluster cells
const PROXIMITY  = 280;   // px — max distance to trigger reassignment

// ─────────────────────────────────────────────────────────────────────────────
// Layout builder — grid of cluster cells
// ─────────────────────────────────────────────────────────────────────────────

function computeCellSize(fragCount) {
    const rows = Math.ceil(fragCount / RESP_COLS);
    const w = RESP_COLS * RESP_W + (RESP_COLS - 1) * RESP_GAP_X;
    const h = THEME_H + 24 + rows * RESP_H + Math.max(0, rows - 1) * RESP_GAP_Y;
    return {
        w: Math.max(w, THEME_W),
        h,
    };
}

function buildLayout(clusterList, fragsByCluster) {
    const nodes = [];
    const edges = [];
    const n = clusterList.length;
    const GRID_COLS = Math.ceil(Math.sqrt(n));

    // First pass — compute each cell's size
    const cellSizes = clusterList.map(cl => {
        const frags = fragsByCluster[cl._id.toString()] ?? [];
        return computeCellSize(frags.length);
    });

    // Second pass — figure out column widths and row heights
    const colWidths = Array(GRID_COLS).fill(0);
    const rowHeights = Array(Math.ceil(n / GRID_COLS)).fill(0);

    clusterList.forEach((_, ci) => {
        const col = ci % GRID_COLS;
        const row = Math.floor(ci / GRID_COLS);
        colWidths[col]  = Math.max(colWidths[col],  cellSizes[ci].w);
        rowHeights[row] = Math.max(rowHeights[row], cellSizes[ci].h);
    });

    // Cumulative offsets
    const colX = [0];
    for (let i = 1; i < GRID_COLS; i++) {
        colX[i] = colX[i - 1] + colWidths[i - 1] + CELL_PAD_X;
    }
    const rowY = [0];
    for (let i = 1; i < rowHeights.length; i++) {
        rowY[i] = rowY[i - 1] + rowHeights[i - 1] + CELL_PAD_Y;
    }

    clusterList.forEach((cl, ci) => {
        const col = ci % GRID_COLS;
        const row = Math.floor(ci / GRID_COLS);
        const cid = cl._id.toString();

        // Centre theme node horizontally in its cell column
        const cellW = colWidths[col];
        const tx = colX[col] + (cellW - THEME_W) / 2;
        const ty = rowY[row];

        nodes.push({
            id: cid,
            type: "themeNode",
            position: { x: tx, y: ty },
            data: {
                label: cl.label ?? "Cluster",
                summary: cl.summary ?? "",
                color: cl.color ?? "#94a3b8",
                size: cl.size ?? 0,
                note: cl.note ?? "",
                clusterId: cid,
                isTarget: false,
            },
            draggable: true,
        });

        const frags = fragsByCluster[cid] ?? [];
        const fragAreaTop = ty + THEME_H + 24;

        frags.forEach((frag, fi) => {
            const fid = frag._id.toString();
            const fc  = fi % RESP_COLS;
            const fr  = Math.floor(fi / RESP_COLS);
            const fx  = colX[col] + fc * (RESP_W + RESP_GAP_X);
            const fy  = fragAreaTop + fr * (RESP_H + RESP_GAP_Y);

            nodes.push({
                id: fid,
                type: "responseNode",
                position: { x: fx, y: fy },
                data: {
                    label: frag.name ?? "Response",
                    text: frag.redacted_text ?? stripHtml(frag.html ?? ""),
                    color: cl.color ?? "#94a3b8",
                    note: frag.note ?? "",
                    clusterId: cid,
                    fragId: fid,
                    isSnapping: false,
                },
                draggable: true,
            });

            edges.push({
                id: `e-${cid}-${fid}`,
                source: cid,
                target: fid,
                type: "straight",
                style: { stroke: cl.color ?? "#94a3b8", strokeWidth: 1.5, opacity: 0.4 },
                animated: false,
            });
        });
    });

    return { nodes, edges };
}

function stripHtml(html = "") {
    return html.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
}

// ─────────────────────────────────────────────────────────────────────────────
// Custom node: Theme
// ─────────────────────────────────────────────────────────────────────────────

function ThemeNode({ data }) {
    const [noteOpen, setNoteOpen]       = useState(false);
    const [note, setNote]               = useState(data.note ?? "");
    const [summaryOpen, setSummaryOpen] = useState(false);

    const save = async (val) => {
        setNote(val);
        try { await cluster_saveNote(data.clusterId, val); } catch (_) {}
    };

    // isTarget comes from node data during live drag
    const ring = data.isTarget
        ? `0 0 0 3px ${data.color}, 0 0 18px 6px ${data.color}88`
        : "none";

    return (
        <div
            className="rounded-xl shadow-md select-none transition-shadow"
            style={{
                width: THEME_W,
                background: "#fff",
                border: `3px solid ${data.color}`,
                boxShadow: ring,
                transition: "box-shadow 0.15s ease",
            }}
        >
            <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
            <Handle type="target" position={Position.Top}    style={{ opacity: 0 }} />

            {/* Coloured title bar */}
            <div
                className="px-3 py-2 rounded-t-lg cursor-pointer"
                style={{ background: `${data.color}18` }}
                onPointerDown={e => e.stopPropagation()}
                onClick={e => { e.stopPropagation(); setSummaryOpen(o => !o); }}
            >
                <p className="text-xs font-bold text-gray-800 truncate leading-snug">{data.label}</p>
                <p className="text-xs text-gray-400">{data.size} responses · <span className="text-blue-400">{summaryOpen ? "▲ less" : "▼ more"}</span></p>
            </div>

            {data.summary && (
                <p
                    className="px-3 py-1.5 text-xs text-gray-500 italic leading-snug"
                    style={summaryOpen
                        ? {}
                        : { display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}
                >
                    {data.summary}
                </p>
            )}

            {/* Note */}
            <div className="px-3 pb-2 pt-1">
                <button
                    className="text-xs text-blue-400 hover:underline"
                    onPointerDown={e => e.stopPropagation()}
                    onClick={e => { e.stopPropagation(); setNoteOpen(o => !o); }}
                >
                    {noteOpen ? "↑ hide note" : "✎ note"}
                </button>
                {noteOpen && (
                    <textarea
                        className="w-full mt-1 text-xs border border-gray-200 rounded p-1 resize-none h-16
                                   focus:outline-none focus:ring-1 focus:ring-blue-300"
                        value={note}
                        onChange={e => setNote(e.target.value)}
                        onBlur={() => save(note)}
                        onPointerDown={e => e.stopPropagation()}
                        placeholder="Add a cluster note…"
                    />
                )}
            </div>

            {/* Pulse ring overlay — visible only when isTarget */}
            {data.isTarget && (
                <div
                    className="pointer-events-none absolute inset-0 rounded-xl"
                    style={{
                        animation: "pulseRing 0.9s ease-in-out infinite",
                        border: `3px solid ${data.color}`,
                        opacity: 0.55,
                    }}
                />
            )}
        </div>
    );
}

// ─────────────────────────────────────────────────────────────────────────────
// Custom node: Response
// ─────────────────────────────────────────────────────────────────────────────

function ResponseNode({ data }) {
    const [noteOpen, setNoteOpen]   = useState(false);
    const [note, setNote]           = useState(data.note ?? "");
    const [textOpen, setTextOpen]   = useState(false);

    const save = async (val) => {
        setNote(val);
        try { await fragment_saveNote(data.fragId, val); } catch (_) {}
    };

    return (
        <div
            className="rounded-lg shadow-sm select-none transition-all"
            style={{
                width: RESP_W,
                background: data.isSnapping ? `${data.color}12` : "#fff",
                border: data.isSnapping
                    ? `2px solid ${data.color}`
                    : "1px solid #e2e8f0",
                borderLeft: `4px solid ${data.color}`,
                transition: "background 0.15s, border-color 0.15s",
            }}
        >
            <Handle type="target" position={Position.Top}    style={{ opacity: 0 }} />
            <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />

            <div
                className="px-2 pt-2 pb-1 cursor-pointer"
                onPointerDown={e => e.stopPropagation()}
                onClick={e => { e.stopPropagation(); setTextOpen(o => !o); }}
            >
                <p className="text-xs font-semibold text-gray-700 truncate">{data.label}</p>
                <p
                    className="text-xs text-gray-400 mt-0.5 leading-relaxed"
                    style={textOpen
                        ? {}
                        : { display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical", overflow: "hidden" }}
                >
                    {data.text}
                </p>
            </div>

            <div className="px-2 pb-2">
                <button
                    className="text-xs text-blue-400 hover:underline"
                    onPointerDown={e => e.stopPropagation()}
                    onClick={e => { e.stopPropagation(); setNoteOpen(o => !o); }}
                >
                    {noteOpen ? "↑ hide note" : "✎ note"}
                </button>
                {noteOpen && (
                    <textarea
                        className="w-full mt-1 text-xs border border-gray-200 rounded p-1 resize-none h-14
                                   focus:outline-none focus:ring-1 focus:ring-blue-300"
                        value={note}
                        onChange={e => setNote(e.target.value)}
                        onBlur={() => save(note)}
                        onPointerDown={e => e.stopPropagation()}
                        placeholder="Add a note…"
                    />
                )}
            </div>
        </div>
    );
}

const NODE_TYPES = { themeNode: ThemeNode, responseNode: ResponseNode };

// ─────────────────────────────────────────────────────────────────────────────
// Suggestion card
// ─────────────────────────────────────────────────────────────────────────────

function SuggestionCard({ s, onAccept, onReject }) {
    return (
        <div className="flex items-start gap-2 p-2 bg-yellow-50 border border-yellow-200 rounded-lg">
            <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold text-gray-700 truncate">{s.fragment_name}</p>
                <p className="text-xs text-gray-500 truncate">{s.fragment_text?.slice(0, 80)}</p>
                <div className="flex items-center gap-1 mt-1">
                    <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: s.suggested_cluster_color }} />
                    <span className="text-xs text-gray-600 truncate">{s.suggested_cluster_label}</span>
                    <span className="text-xs text-gray-400 ml-auto">{Math.round(s.confidence * 100)}%</span>
                </div>
            </div>
            <div className="flex flex-col gap-1 flex-shrink-0">
                <button onClick={() => onAccept(s)} className="text-xs px-2 py-0.5 bg-green-500 hover:bg-green-600 text-white rounded">✓</button>
                <button onClick={() => onReject(s)} className="text-xs px-2 py-0.5 bg-gray-200 hover:bg-gray-300 text-gray-600 rounded">✕</button>
            </div>
        </div>
    );
}

// ─────────────────────────────────────────────────────────────────────────────
// Inner — needs ReactFlowProvider context for useReactFlow()
// ─────────────────────────────────────────────────────────────────────────────

function GraphInner({ docId }) {
    const { getNodes, fitView } = useReactFlow();
    const [clusterList, setClusterList] = useAtom(clusters);
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);
    const [loading, setLoading]   = useState(false);
    const [error, setError]       = useState(null);
    const [feedbackCount, setFeedbackCount] = useState(0);
    const [suggestions, setSuggestions]     = useState([]);

    // fragId → clusterId, kept in sync with every reassignment
    const assignmentRef  = useRef({});
    // last highlighted cluster during drag (to clear it on leave)
    const prevTargetRef  = useRef(null);

    // ── Load ─────────────────────────────────────────────────────────────────
    useEffect(() => {
        if (!docId) return;
        setLoading(true);
        setError(null);

        (async () => {
            try {
                const cls = await clusters_findAll(docId);
                setClusterList(cls);

                const fragsByCluster = {};
                const assignment = {};
                await Promise.all(cls.map(async cl => {
                    const cid = cl._id.toString();
                    const frags = await cluster_getFragments(cid);
                    fragsByCluster[cid] = frags;
                    frags.forEach(f => { assignment[f._id.toString()] = cid; });
                }));

                assignmentRef.current = assignment;
                const { nodes: n, edges: e } = buildLayout(cls, fragsByCluster);
                setNodes(n);
                setEdges(e);

                const { count } = await pipeline_getFeedbackCount(docId);
                setFeedbackCount(count);
                if (count >= 20) {
                    const { suggestions: sg } = await pipeline_suggestPlacements(docId);
                    setSuggestions(sg);
                }
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        })();
    }, [docId]);

    // ── Live drag: highlight nearest in-range theme ───────────────────────────
    const onNodeDrag = useCallback((_, draggedNode) => {
        if (draggedNode.type !== "responseNode") return;

        const cx = draggedNode.position.x + RESP_W / 2;
        const cy = draggedNode.position.y + RESP_H / 2;

        const themeNodes = getNodes().filter(n => n.type === "themeNode");
        let nearestId = null;
        let minDist   = Infinity;

        for (const tn of themeNodes) {
            const tx = tn.position.x + THEME_W / 2;
            const ty = tn.position.y + THEME_H / 2;
            const d  = Math.hypot(cx - tx, cy - ty);
            if (d < minDist) { minDist = d; nearestId = tn.id; }
        }

        // Only highlight if within range AND different from current owner
        const currentOwner = assignmentRef.current[draggedNode.id];
        const targetId = (nearestId && minDist <= PROXIMITY && nearestId !== currentOwner)
            ? nearestId : null;

        if (targetId === prevTargetRef.current) return; // no change — skip re-render
        prevTargetRef.current = targetId;

        setNodes(prev => prev.map(n => {
            if (n.type !== "themeNode") {
                // mark the dragged response as "snapping"
                if (n.id === draggedNode.id) {
                    return { ...n, data: { ...n.data, isSnapping: targetId !== null } };
                }
                return n;
            }
            // theme nodes: set isTarget
            const should = n.id === targetId;
            if (n.data.isTarget === should) return n;
            return { ...n, data: { ...n.data, isTarget: should } };
        }));
    }, [getNodes]);

    // ── Drag stop: commit reassignment ────────────────────────────────────────
    const onNodeDragStop = useCallback((_, draggedNode) => {
        if (draggedNode.type !== "responseNode") {
            // clear any lingering highlights when a theme moves
            setNodes(prev => prev.map(n =>
                n.type === "themeNode" && n.data.isTarget
                    ? { ...n, data: { ...n.data, isTarget: false } }
                    : n
            ));
            return;
        }

        prevTargetRef.current = null;

        // Clear all highlights
        setNodes(prev => prev.map(n => {
            if (n.type === "themeNode") return { ...n, data: { ...n.data, isTarget: false } };
            if (n.id === draggedNode.id) return { ...n, data: { ...n.data, isSnapping: false } };
            return n;
        }));

        const fragId = draggedNode.id;
        const cx = draggedNode.position.x + RESP_W / 2;
        const cy = draggedNode.position.y + RESP_H / 2;

        const themeNodes = getNodes().filter(n => n.type === "themeNode");
        let nearest  = null;
        let minDist  = Infinity;
        for (const tn of themeNodes) {
            const d = Math.hypot(cx - (tn.position.x + THEME_W / 2), cy - (tn.position.y + THEME_H / 2));
            if (d < minDist) { minDist = d; nearest = tn; }
        }

        const oldClusterId = assignmentRef.current[fragId];
        const newClusterId = nearest?.id;
        if (!newClusterId || newClusterId === oldClusterId || minDist > PROXIMITY) return;

        const newCluster = clusterList.find(c => c._id.toString() === newClusterId);
        if (!newCluster) return;

        assignmentRef.current[fragId] = newClusterId;

        // Rewire edge
        setEdges(prev => [
            ...prev.filter(e => e.target !== fragId),
            {
                id: `e-${newClusterId}-${fragId}`,
                source: newClusterId, target: fragId, type: "straight",
                style: { stroke: newCluster.color, strokeWidth: 1.5, opacity: 0.4 },
            },
        ]);

        // Update card colour
        setNodes(prev => prev.map(n =>
            n.id === fragId
                ? { ...n, data: { ...n.data, color: newCluster.color, clusterId: newClusterId } }
                : n
        ));

        // Persist
        pipeline_recordFeedback(fragId, oldClusterId, newClusterId)
            .then(async () => {
                const { count } = await pipeline_getFeedbackCount(docId);
                setFeedbackCount(count);
                if (count >= 20) {
                    const { suggestions: sg } = await pipeline_suggestPlacements(docId);
                    setSuggestions(sg);
                }
            })
            .catch(console.error);
    }, [clusterList, docId, getNodes]);

    // ── Accept suggestion ─────────────────────────────────────────────────────
    const acceptSuggestion = async (s) => {
        const { fragment_id: fragId, suggested_cluster_id: newCid } = s;
        const oldCid = assignmentRef.current[fragId] ?? "";
        const nc = clusterList.find(c => c._id.toString() === newCid);
        if (!nc) return;
        assignmentRef.current[fragId] = newCid;
        setEdges(prev => [...prev.filter(e => e.target !== fragId), {
            id: `e-${newCid}-${fragId}`, source: newCid, target: fragId, type: "straight",
            style: { stroke: nc.color, strokeWidth: 1.5, opacity: 0.4 },
        }]);
        setNodes(prev => prev.map(n =>
            n.id === fragId ? { ...n, data: { ...n.data, color: nc.color, clusterId: newCid } } : n
        ));
        setSuggestions(prev => prev.filter(x => x.fragment_id !== fragId));
        try {
            await pipeline_recordFeedback(fragId, oldCid, newCid);
            const { count } = await pipeline_getFeedbackCount(docId);
            setFeedbackCount(count);
        } catch (err) { console.error(err); }
    };

    const rejectSuggestion = s => setSuggestions(prev => prev.filter(x => x.fragment_id !== s.fragment_id));

    // ── Click theme node: zoom to fit that cluster + its responses ────────────
    const onNodeClick = useCallback((_, clickedNode) => {
        if (clickedNode.type !== "themeNode") return;
        const clusterId = clickedNode.id;
        // Collect IDs of this theme + all its response nodes
        const nodeIds = getNodes()
            .filter(n => n.id === clusterId || (n.type === "responseNode" && n.data.clusterId === clusterId))
            .map(n => n.id);
        fitView({ nodes: nodeIds.map(id => ({ id })), duration: 500, padding: 0.18 });
    }, [getNodes, fitView]);

    // ── Render ────────────────────────────────────────────────────────────────
    return (
        <div className="flex-1 relative h-full min-w-0">
            {loading && (
                <div className="absolute inset-0 flex items-center justify-center bg-white/80 z-20">
                    <div className="text-center">
                        <div className="text-4xl animate-spin mb-3">⟳</div>
                        <p className="text-gray-600 font-medium">Building graph…</p>
                    </div>
                </div>
            )}
            {error && (
                <div className="absolute top-4 left-1/2 -translate-x-1/2 z-30 px-5 py-3
                                bg-red-50 border border-red-300 rounded-lg text-red-700 text-sm shadow">
                    {error}
                </div>
            )}
            {!loading && nodes.length === 0 && (
                <div className="absolute inset-0 flex items-center justify-center z-10">
                    <div className="text-center text-gray-400">
                        <div className="text-5xl mb-3">◎</div>
                        <p className="font-semibold">No clusters to display</p>
                        <p className="text-sm mt-1">Enter a survey doc ID in the left panel.</p>
                    </div>
                </div>
            )}

            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                nodeTypes={NODE_TYPES}
                onNodeDrag={onNodeDrag}
                onNodeDragStop={onNodeDragStop}
                onNodeClick={onNodeClick}
                fitView
                fitViewOptions={{ padding: 0.1 }}
                minZoom={0.1}
                maxZoom={2}
                deleteKeyCode={null}
                elevateNodesOnSelect={false}
            >
                <Background color="#e2e8f0" gap={24} />
                <Controls />
                <MiniMap
                    nodeColor={n => n.data?.color ?? "#94a3b8"}
                    maskColor="rgba(248,250,252,0.85)"
                />
            </ReactFlow>

            {/* Feedback overlay — bottom right */}
            {nodes.length > 0 && (
                <div className="absolute bottom-4 right-4 z-20 w-72 space-y-2 pointer-events-auto">
                    {feedbackCount > 0 && feedbackCount < 20 && (
                        <div className="bg-white border border-gray-200 rounded-lg px-4 py-3 shadow text-xs">
                            <p className="text-gray-500 mb-1">{feedbackCount}/20 placements to unlock AI suggestions</p>
                            <div className="h-1.5 rounded bg-gray-200">
                                <div className="h-1.5 rounded bg-blue-500 transition-all"
                                     style={{ width: `${(feedbackCount / 20) * 100}%` }} />
                            </div>
                        </div>
                    )}
                    {suggestions.length > 0 && (
                        <div className="bg-white border border-yellow-200 rounded-lg shadow overflow-hidden">
                            <div className="px-3 py-2 bg-yellow-50 border-b border-yellow-200">
                                <p className="text-xs font-semibold text-yellow-800">
                                    ✦ AI suggestions · {feedbackCount} placements learned
                                </p>
                            </div>
                            <div className="p-2 space-y-2 max-h-56 overflow-y-auto">
                                {suggestions.map(s => (
                                    <SuggestionCard key={s.fragment_id} s={s} onAccept={acceptSuggestion} onReject={rejectSuggestion} />
                                ))}
                            </div>
                        </div>
                    )}
                    {feedbackCount >= 20 && suggestions.length === 0 && (
                        <div className="bg-green-50 border border-green-200 rounded-lg px-4 py-2 shadow text-xs text-green-700">
                            ✓ AI has learned from {feedbackCount} placements — no pending suggestions
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

// ─────────────────────────────────────────────────────────────────────────────
// Shell — left panel + provider
// ─────────────────────────────────────────────────────────────────────────────

export default function ClusterGraphView() {
    const location  = useLocation();
    const navigate  = useNavigate();
    const [clusterList] = useAtom(clusters);
    const [inputVal, setInputVal] = useState(location.state?.doc_id ?? "");
    const [docId, setDocId]       = useState(location.state?.doc_id ?? null);

    const nonNoise = clusterList.filter(c => c.label !== "Uncategorised");

    return (
        <>
            {/* Pulse keyframe — injected once */}
            <style>{`
                @keyframes pulseRing {
                    0%   { transform: scale(1);    opacity: 0.55; }
                    50%  { transform: scale(1.06); opacity: 0.85; }
                    100% { transform: scale(1);    opacity: 0.55; }
                }
            `}</style>

            <div className="flex h-screen w-full overflow-hidden bg-gray-50">
                {/* Left panel */}
                <div className="w-56 flex-shrink-0 border-r border-gray-200 bg-white flex flex-col">
                    <div className="px-4 py-3 border-b border-gray-100">
                        <h2 className="text-sm font-bold text-gray-800">Clusters</h2>
                        <p className="text-xs text-gray-400">{nonNoise.length} themes</p>
                    </div>

                    <div className="px-3 py-2 border-b border-gray-100">
                        <input
                            type="text"
                            value={inputVal}
                            onChange={e => setInputVal(e.target.value)}
                            onKeyDown={e => { if (e.key === "Enter") setDocId(inputVal.trim() || null); }}
                            onBlur={() => setDocId(inputVal.trim() || null)}
                            placeholder="Survey doc ID + Enter"
                            className="w-full border border-gray-300 rounded px-2 py-1.5 text-xs
                                       focus:outline-none focus:ring-1 focus:ring-blue-400"
                        />
                    </div>

                    <div className="flex-1 overflow-y-auto p-2 space-y-1">
                        {nonNoise.map(c => (
                            <div key={c._id.toString()} className="flex items-center gap-2 px-2 py-2 rounded-lg">
                                <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: c.color ?? "#94a3b8" }} />
                                <div className="min-w-0">
                                    <p className="text-xs font-semibold text-gray-800 truncate">{c.label ?? "Unlabelled"}</p>
                                    <p className="text-xs text-gray-400">{c.size} responses</p>
                                </div>
                            </div>
                        ))}
                        {nonNoise.length === 0 && (
                            <p className="text-xs text-gray-400 text-center py-4 px-2">
                                Enter a doc ID above<br />or run Survey Ingestion first
                            </p>
                        )}
                    </div>

                    <div className="p-3 border-t border-gray-100">
                        <button
                            onClick={() => navigate("/survey-ingest")}
                            className="w-full py-2 text-xs rounded-lg border border-blue-300 text-blue-600 hover:bg-blue-50 transition-colors font-medium"
                        >
                            + Ingest new survey
                        </button>
                    </div>
                </div>

                <ReactFlowProvider>
                    <GraphInner docId={docId} />
                </ReactFlowProvider>
            </div>
        </>
    );
}
