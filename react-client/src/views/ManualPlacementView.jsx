/**
 * ManualPlacementView — freeform whiteboard where researchers drag survey
 * fragments onto a canvas and form clusters by proximity.
 *
 * Flow:
 *   1. Fragments are loaded from MongoDB for the given doc_id
 *   2. Sidebar shows one fragment at a time; drag it onto the canvas
 *   3. Fragments placed within PROX_PX of each other auto-group with a coloured hull
 *   4. After each drop the AI runs a sanity check: if it thinks a better group
 *      exists, an animated arrow appears pointing from the fragment to that group
 *      with tick / cross buttons — accept moves the fragment, reject dismisses.
 *   5. After 20 placements the AI also starts suggesting where the NEXT fragment goes
 *   6. "Save & Label" persists groups as clusters and navigates to ClusterGraphView
 */
import { useCallback, useEffect, useRef, useState } from "react";
import {
    ReactFlow, Background, Controls, MiniMap,
    useNodesState, useEdgesState,
    Handle, Position, useReactFlow, ReactFlowProvider,
    BaseEdge, EdgeLabelRenderer, getSmoothStepPath, MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useLocation, useNavigate } from "react-router-dom";

import { fragments_findByDoc } from "../api/dataFacade";
import {
    pipeline_suggestManualPlacement,
    pipeline_suggestLLMManualPlacement,
    pipeline_saveManualClusters,
    pipeline_sanityCheck,
} from "../api/aiServiceFacade";

// ─────────────────────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────────────────────

const FRAG_W     = 180;
const FRAG_H     = 100;
const PROX_PX    = 220;
const GROUP_PAD  = 36;
const SUGGEST_AT = 20;

const COLORS = [
    "#4CAF50", "#2196F3", "#FF5722", "#9C27B0", "#FF9800",
    "#00BCD4", "#E91E63", "#3F51B5", "#8BC34A", "#FFC107",
    "#009688", "#F44336", "#673AB7", "#03A9F4", "#CDDC39",
];

// ─────────────────────────────────────────────────────────────────────────────
// Proximity grouping (union-find)
// ─────────────────────────────────────────────────────────────────────────────

function computeProximityGroups(respNodes, threshold) {
    const n = respNodes.length;
    if (n === 0) return [];

    const parent = respNodes.map((_, i) => i);
    function find(i) {
        if (parent[i] !== i) parent[i] = find(parent[i]);
        return parent[i];
    }
    function union(i, j) { parent[find(i)] = find(j); }

    for (let i = 0; i < n; i++) {
        for (let j = i + 1; j < n; j++) {
            const dx = respNodes[i].position.x - respNodes[j].position.x;
            const dy = respNodes[i].position.y - respNodes[j].position.y;
            if (Math.sqrt(dx * dx + dy * dy) < threshold) union(i, j);
        }
    }

    const map = {};
    respNodes.forEach((node, i) => {
        const root = find(i);
        if (!map[root]) map[root] = [];
        map[root].push(node);
    });

    return Object.values(map).sort((a, b) =>
        Math.min(...a.map(n => n.data.placedAt)) - Math.min(...b.map(n => n.data.placedAt))
    );
}

// ─────────────────────────────────────────────────────────────────────────────
// Rebuild full nodes array (group hulls + fragment cards)
// Only returns groupNode + manualFragNode types — sanityAnchorNodes are
// intentionally excluded so they disappear after any rebuild.
// ─────────────────────────────────────────────────────────────────────────────

function rebuildNodes(respNodes, suggestedGroupIdx = null) {
    const groups = computeProximityGroups(respNodes, PROX_PX);

    const groupNodes = [];
    const colorByFragId = {};

    groups.forEach((group, idx) => {
        const color = COLORS[idx % COLORS.length];
        group.forEach(n => { colorByFragId[n.data.fragId] = color; });

        if (group.length < 2) return;

        const xs = group.map(n => n.position.x);
        const ys = group.map(n => n.position.y);
        const minX = Math.min(...xs) - GROUP_PAD;
        const minY = Math.min(...ys) - GROUP_PAD;
        const w    = Math.max(...xs) + FRAG_W + GROUP_PAD - minX;
        const h    = Math.max(...ys) + FRAG_H + GROUP_PAD - minY;

        groupNodes.push({
            id: `group-${idx}`,
            type: "groupNode",
            position: { x: minX, y: minY },
            data: { color, w, h, label: `Group ${idx + 1}`, fragmentIds: group.map(n => n.data.fragId), isCandidate: idx === suggestedGroupIdx },
            draggable: false,
            selectable: false,
            zIndex: 0,
        });
    });

    const updatedRespNodes = respNodes.map(n => ({
        ...n,
        data: { ...n.data, color: colorByFragId[n.data.fragId] ?? "#94a3b8" },
        zIndex: 1,
    }));

    return [...groupNodes, ...updatedRespNodes];
}

// ─────────────────────────────────────────────────────────────────────────────
// Custom node: Group hull
// ─────────────────────────────────────────────────────────────────────────────

function GroupNode({ data }) {
    return (
        <div style={{
            width: data.w,
            height: data.h,
            background: `${data.color}10`,
            border: `2px ${data.isCandidate ? "solid" : "dashed"} ${data.color}${data.isCandidate ? "cc" : "55"}`,
            borderRadius: 18,
            pointerEvents: "none",
            animation: data.isCandidate ? "pulseRing 0.9s ease-in-out infinite" : "none",
            position: "relative",
        }}>
            <div style={{ padding: "8px 12px", display: "flex", alignItems: "center", gap: 6 }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: data.color }}>{data.label}</span>
                {data.isCandidate && (
                    <span style={{ fontSize: 10, fontWeight: 600, background: data.color, color: "#fff", borderRadius: 4, padding: "1px 5px" }}>
                        AI suggest
                    </span>
                )}
            </div>
        </div>
    );
}

// ─────────────────────────────────────────────────────────────────────────────
// Custom node: Fragment card on canvas
// ─────────────────────────────────────────────────────────────────────────────

function ManualFragNode({ data }) {
    const [expanded, setExpanded] = useState(false);
    return (
        <div
            style={{
                width: FRAG_W,
                background: data.sanityHighlight ? "#faf5ff" : "#fff",
                border: data.sanityHighlight ? "2px solid #7c3aed" : "1px solid #e2e8f0",
                borderLeft: `4px solid ${data.color}`,
                borderRadius: 8,
                boxShadow: data.sanityHighlight
                    ? "0 0 0 3px #7c3aed33, 0 2px 8px rgba(124,58,237,0.15)"
                    : "0 1px 4px rgba(0,0,0,0.08)",
                cursor: "grab",
                transition: "border-color 0.2s, box-shadow 0.2s",
                userSelect: "none",
            }}
            onClick={e => { e.stopPropagation(); setExpanded(v => !v); }}
        >
            <Handle type="target" position={Position.Top}    style={{ opacity: 0 }} />
            <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
            <div style={{ padding: "6px 10px" }}>
                <p style={{ fontSize: 11, fontWeight: 600, color: "#374151", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {data.label}
                </p>
                <p style={{
                    fontSize: 11, color: "#6b7280", marginTop: 3, lineHeight: 1.5,
                    ...(expanded ? {} : { display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical", overflow: "hidden" }),
                }}>
                    {data.text}
                </p>
            </div>
        </div>
    );
}

// ─────────────────────────────────────────────────────────────────────────────
// Custom node: Invisible anchor — target for the sanity check arrow.
// Positioned at the centre of the suggested group.
// ─────────────────────────────────────────────────────────────────────────────

function SanityAnchorNode() {
    return (
        <div style={{ width: 2, height: 2, opacity: 0 }}>
            <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
        </div>
    );
}

// ─────────────────────────────────────────────────────────────────────────────
// Custom edge: Sanity check arrow
// Animated dashed purple arrow from the fragment to the suggested group's
// anchor node, with a reason tooltip and tick / cross buttons at the midpoint.
// ─────────────────────────────────────────────────────────────────────────────

function SanityEdge({ id, sourceX, sourceY, targetX, targetY, markerEnd, data }) {
    const { setNodes, setEdges } = useReactFlow();

    const [edgePath, labelX, labelY] = getSmoothStepPath({
        sourceX, sourceY, sourcePosition: Position.Bottom,
        targetX, targetY, targetPosition: Position.Top,
        borderRadius: 20,
    });

    const handleAccept = useCallback(() => {
        setNodes(prev => {
            // Move the fragment to the target position, then rebuild
            // (rebuildNodes drops sanityAnchorNodes automatically)
            const respNodes = prev
                .filter(n => n.type === "manualFragNode")
                .map(n => n.id === data.fragmentId
                    ? { ...n, position: { x: data.targetX, y: data.targetY }, data: { ...n.data, sanityHighlight: false } }
                    : n.type === "manualFragNode" ? { ...n, data: { ...n.data, sanityHighlight: false } } : n
                );
            return rebuildNodes(respNodes);
        });
        setEdges(prev => prev.filter(e => e.id !== id));
    }, [id, data, setNodes, setEdges]);

    const handleReject = useCallback(() => {
        // Remove anchor node and edge, clear highlight on the fragment
        setNodes(prev => prev
            .filter(n => n.id !== data.anchorNodeId)
            .map(n => n.id === data.fragmentId
                ? { ...n, data: { ...n.data, sanityHighlight: false } }
                : n
            )
        );
        setEdges(prev => prev.filter(e => e.id !== id));
    }, [id, data, setNodes, setEdges]);

    return (
        <>
            <BaseEdge
                id={id}
                path={edgePath}
                markerEnd={markerEnd}
                style={{
                    stroke: "#7c3aed",
                    strokeWidth: 2.5,
                    strokeDasharray: "8 4",
                    animation: "sanityDash 0.7s linear infinite",
                }}
            />
            <EdgeLabelRenderer>
                <div style={{
                    position: "absolute",
                    transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
                    pointerEvents: "all",
                    zIndex: 100,
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: 5,
                }}>
                    {/* Reason tooltip */}
                    {data.reason && (
                        <div style={{
                            background: "#7c3aed",
                            color: "#fff",
                            fontSize: 10,
                            fontWeight: 600,
                            borderRadius: 6,
                            padding: "4px 9px",
                            maxWidth: 190,
                            textAlign: "center",
                            lineHeight: 1.4,
                            boxShadow: "0 2px 8px rgba(124,58,237,0.35)",
                            whiteSpace: "normal",
                        }}>
                            {data.reason}
                        </div>
                    )}
                    {/* Tick / cross buttons */}
                    <div style={{ display: "flex", gap: 6 }}>
                        <button
                            title="Move to suggested group"
                            onClick={handleAccept}
                            style={{
                                width: 30, height: 30, borderRadius: "50%",
                                background: "#16a34a", color: "#fff",
                                border: "2px solid #fff",
                                cursor: "pointer", fontSize: 15, fontWeight: 700,
                                display: "flex", alignItems: "center", justifyContent: "center",
                                boxShadow: "0 2px 6px rgba(0,0,0,0.25)",
                            }}
                        >✓</button>
                        <button
                            title="Keep in current group"
                            onClick={handleReject}
                            style={{
                                width: 30, height: 30, borderRadius: "50%",
                                background: "#6b7280", color: "#fff",
                                border: "2px solid #fff",
                                cursor: "pointer", fontSize: 15, fontWeight: 700,
                                display: "flex", alignItems: "center", justifyContent: "center",
                                boxShadow: "0 2px 6px rgba(0,0,0,0.25)",
                            }}
                        >✗</button>
                    </div>
                </div>
            </EdgeLabelRenderer>
        </>
    );
}

const NODE_TYPES = { groupNode: GroupNode, manualFragNode: ManualFragNode, sanityAnchorNode: SanityAnchorNode };
const EDGE_TYPES = { sanityEdge: SanityEdge };

// ─────────────────────────────────────────────────────────────────────────────
// Inner component (needs useReactFlow)
// ─────────────────────────────────────────────────────────────────────────────

function ManualPlacementInner() {
    const navigate         = useNavigate();
    const { state }        = useLocation();
    const docId            = state?.doc_id ?? null;
    const surveyName       = state?.survey_name ?? "Survey";
    const useLLM           = state?.use_llm ?? false;
    const researchQuestion = state?.research_question ?? "";

    const { screenToFlowPosition, getNodes } = useReactFlow();
    const wrapperRef = useRef(null);
    const placedAt   = useRef(0);

    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges]                = useEdgesState([]);
    const [queue,      setQueue]      = useState([]);
    const [placed,     setPlaced]     = useState(0);
    const [loading,    setLoading]    = useState(true);
    const [saving,     setSaving]     = useState(false);
    const [error,      setError]      = useState(null);
    const [suggestion, setSuggestion] = useState(null);

    // ── Load fragments ────────────────────────────────────────────────────────
    useEffect(() => {
        if (!docId) { setError("No doc_id provided."); setLoading(false); return; }
        fragments_findByDoc(docId)
            .then(frags => setQueue(frags.filter(f => f.redacted_text)))
            .catch(e => setError(e.message))
            .finally(() => setLoading(false));
    }, [docId]);

    // ── Sanity check — fires after each drop ──────────────────────────────────
    const triggerSanityCheck = useCallback(async (fragId, newRespNodes) => {
        const groups = computeProximityGroups(newRespNodes, PROX_PX);

        // Need at least 2 groups, and at least one other group with 2+ members,
        // so the LLM has enough context to compare against.
        if (groups.length < 2) return;

        // Which group did the fragment land in?
        const fragGroupIdx = groups.findIndex(g => g.some(n => n.id === fragId));
        if (fragGroupIdx === -1) return; // lone fragment — nothing to compare

        // At least one OTHER group must have 2+ members for a meaningful comparison
        const otherGroupsWithContext = groups.filter((_, i) => i !== fragGroupIdx && _.length >= 2);
        if (otherGroupsWithContext.length === 0) return;

        const groupSpecs = groups.map((g, i) => ({
            group_id: String(i),
            fragment_ids: g.map(n => n.data.fragId),
        }));

        try {
            const res = await pipeline_sanityCheck(
                docId,
                fragId,
                String(fragGroupIdx),
                groupSpecs,
                researchQuestion,
            );

            if (!res || res.ok !== false) return;

            const suggestedIdx = parseInt(res.suggested_group_id, 10);
            const suggestedGroup = groups[suggestedIdx];
            if (!suggestedGroup) return;

            // Compute centre of the suggested group to place the anchor node
            const xs = suggestedGroup.map(n => n.position.x);
            const ys = suggestedGroup.map(n => n.position.y);
            const avgX = xs.reduce((a, b) => a + b, 0) / xs.length;
            const avgY = ys.reduce((a, b) => a + b, 0) / ys.length;

            // Target position for the fragment if accepted (centre of suggested group)
            const targetX = avgX + 10;
            const targetY = avgY + 10;

            const anchorId = `sanity-anchor-${fragId}`;
            const edgeId   = `sanity-edge-${fragId}`;

            // Highlight the fragment being questioned
            setNodes(prev => prev.map(n =>
                n.id === fragId ? { ...n, data: { ...n.data, sanityHighlight: true } } : n
            ));

            // Add invisible anchor at centre of suggested group
            setNodes(prev => [
                ...prev.filter(n => n.id !== anchorId),
                {
                    id: anchorId,
                    type: "sanityAnchorNode",
                    position: { x: avgX, y: avgY },
                    data: {},
                    draggable: false,
                    selectable: false,
                    zIndex: 10,
                },
            ]);

            // Add animated arrow edge
            setEdges(prev => [
                ...prev.filter(e => e.id !== edgeId),
                {
                    id: edgeId,
                    source: fragId,
                    target: anchorId,
                    type: "sanityEdge",
                    markerEnd: { type: MarkerType.ArrowClosed, color: "#7c3aed", width: 18, height: 18 },
                    data: {
                        fragmentId: fragId,
                        anchorNodeId: anchorId,
                        targetX,
                        targetY,
                        reason: res.reason,
                    },
                },
            ]);
        } catch (_) {
            // Sanity check is non-blocking — silent fail
        }
    }, [docId, researchQuestion, setNodes, setEdges]);

    // ── Forward suggestion after 20 placements ────────────────────────────────
    useEffect(() => {
        if (placed < SUGGEST_AT || queue.length === 0) { setSuggestion(null); return; }

        const fragId   = queue[0]._id.toString();
        const respNodes = getNodes().filter(n => n.type === "manualFragNode");
        const groups   = computeProximityGroups(respNodes, PROX_PX);
        if (groups.length === 0) return;

        const groupSpecs = groups.map((g, i) => ({
            group_id: String(i),
            fragment_ids: g.map(n => n.data.fragId),
        }));

        const call = useLLM
            ? pipeline_suggestLLMManualPlacement(docId, fragId, groupSpecs, researchQuestion)
            : pipeline_suggestManualPlacement(docId, fragId, groupSpecs);

        call.then(res => {
            if (!res.suggestion) return;
            setSuggestion(res.suggestion);
            if (!res.suggestion.new_cluster && res.suggestion.group_id !== null) {
                const idx = parseInt(res.suggestion.group_id, 10);
                setNodes(prev => rebuildNodes(prev.filter(n => n.type === "manualFragNode"), idx));
            }
        }).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [placed, queue, docId]);

    // ── Drop from sidebar ─────────────────────────────────────────────────────
    const onDrop = useCallback((e) => {
        e.preventDefault();
        const fragId    = e.dataTransfer.getData("fragId");
        const fragLabel = e.dataTransfer.getData("fragLabel");
        const fragText  = e.dataTransfer.getData("fragText");
        if (!fragId) return;

        const position = screenToFlowPosition({ x: e.clientX, y: e.clientY });
        const order    = placedAt.current++;

        // Clear any existing sanity check before handling the new drop
        setEdges([]);

        const prevResp    = getNodes().filter(n => n.type === "manualFragNode");
        const newNode     = {
            id: fragId,
            type: "manualFragNode",
            position,
            data: { fragId, label: fragLabel, text: fragText, color: "#94a3b8", placedAt: order, sanityHighlight: false },
            zIndex: 1,
            draggable: true,
        };
        const newRespNodes = [...prevResp, newNode];

        setNodes(rebuildNodes(newRespNodes));
        setQueue(prev => prev.filter(f => f._id.toString() !== fragId));
        setPlaced(p => p + 1);
        setSuggestion(null);

        // Fire sanity check asynchronously — does not block the drop
        triggerSanityCheck(fragId, newRespNodes);
    }, [screenToFlowPosition, getNodes, setNodes, setEdges, triggerSanityCheck]);

    // ── Recompute groups after drag stop (clears sanity check) ───────────────
    const onNodeDragStop = useCallback((_, node) => {
        if (node.type !== "manualFragNode") return;
        // rebuildNodes drops sanityAnchorNodes; also clear edges and highlight
        setNodes(prev => rebuildNodes(prev.filter(n => n.type === "manualFragNode")));
        setEdges([]);
        setSuggestion(null);
    }, [setNodes, setEdges]);

    // ── Save ──────────────────────────────────────────────────────────────────
    const handleSave = async () => {
        const respNodes = getNodes().filter(n => n.type === "manualFragNode");
        const groups    = computeProximityGroups(respNodes, PROX_PX);
        const nonEmpty  = groups.filter(g => g.length > 0);
        if (nonEmpty.length === 0) { setError("Place at least one fragment on the canvas first."); return; }

        setSaving(true);
        setError(null);
        try {
            const groupSpecs = nonEmpty.map(g => ({ fragment_ids: g.map(n => n.data.fragId) }));
            await pipeline_saveManualClusters(docId, groupSpecs);
            navigate("/cluster-graph", { state: { doc_id: docId } });
        } catch (err) {
            setError(err.message);
            setSaving(false);
        }
    };

    const handleSkip = () => {
        setQueue(prev => {
            if (prev.length < 2) return prev;
            const [first, ...rest] = prev;
            return [...rest, first];
        });
        setSuggestion(null);
    };

    // ─────────────────────────────────────────────────────────────────────────
    // Render
    // ─────────────────────────────────────────────────────────────────────────

    if (loading) {
        return <div className="flex items-center justify-center h-full text-gray-400 text-sm">Loading fragments…</div>;
    }

    const currentFrag = queue[0] ?? null;
    const upNext      = queue.slice(1, 4);

    return (
        <div style={{ display: "flex", height: "100%", overflow: "hidden" }}>
            <style>{`
                @keyframes pulseRing  { 0%,100%{transform:scale(1);opacity:.7} 50%{transform:scale(1.02);opacity:1} }
                @keyframes sanityDash { to { stroke-dashoffset: -24; } }
            `}</style>

            {/* ════ LEFT SIDEBAR ════ */}
            <div style={{
                width: 280, flexShrink: 0,
                borderRight: "1px solid #e5e7eb",
                background: "#f9fafb",
                display: "flex", flexDirection: "column",
                overflow: "hidden",
            }}>
                {/* Header */}
                <div style={{ padding: "16px 16px 12px", borderBottom: "1px solid #e5e7eb" }}>
                    <button
                        onClick={() => navigate("/survey-ingest")}
                        style={{ fontSize: 12, color: "#6b7280", marginBottom: 6, background: "none", border: "none", cursor: "pointer", padding: 0 }}
                    >← Back</button>
                    <h2 style={{ fontSize: 14, fontWeight: 700, color: "#111827", margin: 0 }}>
                        Manual Placement
                        {useLLM && (
                            <span style={{ marginLeft: 6, fontSize: 10, fontWeight: 700, background: "#7c3aed", color: "#fff", borderRadius: 4, padding: "1px 5px", verticalAlign: "middle" }}>LLM</span>
                        )}
                    </h2>
                    <p style={{ fontSize: 12, color: "#6b7280", marginTop: 2 }}>{surveyName}</p>
                    {useLLM && researchQuestion && (
                        <p style={{ fontSize: 11, color: "#7c3aed", marginTop: 4, fontStyle: "italic", lineHeight: 1.4, borderLeft: "2px solid #7c3aed", paddingLeft: 6 }}>
                            {researchQuestion}
                        </p>
                    )}
                </div>

                {/* Progress */}
                <div style={{ padding: "10px 16px", borderBottom: "1px solid #e5e7eb" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                        <span style={{ fontSize: 11, color: "#6b7280" }}>Placed</span>
                        <span style={{ fontSize: 11, fontWeight: 600, color: "#374151" }}>{placed} / {placed + queue.length}</span>
                    </div>
                    <div style={{ height: 4, background: "#e5e7eb", borderRadius: 2, overflow: "hidden" }}>
                        <div style={{
                            height: "100%",
                            width: `${placed + queue.length > 0 ? (placed / (placed + queue.length)) * 100 : 0}%`,
                            background: "#3b82f6", transition: "width 0.3s",
                        }} />
                    </div>
                    {placed < SUGGEST_AT && placed + queue.length > 0 && (
                        <p style={{ fontSize: 11, color: "#9ca3af", marginTop: 4 }}>
                            {useLLM ? "Claude suggestions" : "AI suggestions"} unlock at {SUGGEST_AT} placements ({SUGGEST_AT - placed} to go)
                        </p>
                    )}
                </div>

                {/* Sanity check legend */}
                <div style={{ padding: "8px 16px", borderBottom: "1px solid #e5e7eb", background: "#faf5ff" }}>
                    <p style={{ fontSize: 11, color: "#7c3aed", margin: 0, lineHeight: 1.5 }}>
                        <strong>Sanity check on.</strong> After each placement, Claude checks if you chose the best group and will draw an arrow if it disagrees.
                    </p>
                </div>

                {/* Fragment queue */}
                <div style={{ flex: 1, overflowY: "auto", padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
                    {currentFrag ? (
                        <>
                            {suggestion && (
                                <div style={{
                                    padding: "8px 10px", borderRadius: 8,
                                    background: suggestion.new_cluster ? "#fef3c7" : "#eff6ff",
                                    border: `1px solid ${suggestion.new_cluster ? "#fbbf24" : "#93c5fd"}`,
                                    fontSize: 11, color: suggestion.new_cluster ? "#92400e" : "#1e40af",
                                }}>
                                    <strong>AI suggests:</strong>{" "}
                                    {suggestion.new_cluster
                                        ? "Create a new group for this response"
                                        : `Place in Group ${parseInt(suggestion.group_id, 10) + 1} (${Math.round(suggestion.confidence * 100)}% match)`}
                                </div>
                            )}

                            <div
                                draggable
                                onDragStart={e => {
                                    e.dataTransfer.setData("fragId",    currentFrag._id.toString());
                                    e.dataTransfer.setData("fragLabel", currentFrag.name ?? "Response");
                                    e.dataTransfer.setData("fragText",  currentFrag.redacted_text ?? "");
                                    e.dataTransfer.effectAllowed = "move";
                                }}
                                style={{
                                    background: "#fff", border: "1px solid #d1d5db",
                                    borderRadius: 10, padding: 12, cursor: "grab",
                                    boxShadow: "0 1px 6px rgba(0,0,0,0.08)",
                                }}
                            >
                                <p style={{ fontSize: 12, fontWeight: 700, color: "#111827", marginBottom: 6 }}>{currentFrag.name ?? "Response"}</p>
                                <p style={{ fontSize: 12, color: "#4b5563", lineHeight: 1.5 }}>{currentFrag.redacted_text}</p>
                                <p style={{ fontSize: 11, color: "#9ca3af", marginTop: 8, textAlign: "center" }}>↑ Drag onto canvas</p>
                            </div>

                            <button
                                onClick={handleSkip}
                                style={{ fontSize: 12, color: "#6b7280", background: "none", border: "none", cursor: "pointer", textAlign: "center", textDecoration: "underline" }}
                            >Place later →</button>

                            {upNext.length > 0 && (
                                <div>
                                    <p style={{ fontSize: 11, fontWeight: 600, color: "#9ca3af", marginBottom: 6 }}>Up next</p>
                                    {upNext.map(f => (
                                        <div key={f._id.toString()} style={{ fontSize: 11, color: "#6b7280", padding: "4px 8px", borderRadius: 6, background: "#f3f4f6", marginBottom: 4, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                                            {f.name ?? "Response"}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </>
                    ) : (
                        <div style={{ textAlign: "center", color: "#6b7280", paddingTop: 16 }}>
                            <p style={{ fontSize: 16 }}>✓</p>
                            <p style={{ fontSize: 13, fontWeight: 600, marginTop: 4 }}>All fragments placed!</p>
                            <p style={{ fontSize: 12, marginTop: 4 }}>Review groups on the canvas, then save.</p>
                        </div>
                    )}
                </div>

                {/* Save */}
                <div style={{ padding: 16, borderTop: "1px solid #e5e7eb" }}>
                    {error && <p style={{ fontSize: 11, color: "#ef4444", marginBottom: 8 }}>{error}</p>}
                    <button
                        onClick={handleSave}
                        disabled={saving || placed === 0}
                        style={{
                            width: "100%", padding: "10px 0", borderRadius: 8, border: "none",
                            background: saving || placed === 0 ? "#d1d5db" : "#16a34a",
                            color: "#fff", fontSize: 13, fontWeight: 600,
                            cursor: saving || placed === 0 ? "not-allowed" : "pointer",
                        }}
                    >
                        {saving ? "Saving & labelling…" : "Save & Label Clusters →"}
                    </button>
                </div>
            </div>

            {/* ════ CANVAS ════ */}
            <div
                ref={wrapperRef}
                style={{ flex: 1, height: "100%" }}
                onDragOver={e => e.preventDefault()}
                onDrop={onDrop}
            >
                <ReactFlow
                    nodes={nodes}
                    edges={edges}
                    nodeTypes={NODE_TYPES}
                    edgeTypes={EDGE_TYPES}
                    onNodesChange={onNodesChange}
                    onNodeDragStop={onNodeDragStop}
                    fitView
                    minZoom={0.2}
                    maxZoom={2}
                    deleteKeyCode={null}
                >
                    <Background color="#e5e7eb" gap={24} />
                    <Controls />
                    <MiniMap nodeStrokeWidth={3} zoomable pannable />

                    {placed === 0 && (
                        <div style={{
                            position: "absolute", inset: 0,
                            display: "flex", flexDirection: "column",
                            alignItems: "center", justifyContent: "center",
                            pointerEvents: "none", color: "#9ca3af",
                        }}>
                            <p style={{ fontSize: 32, marginBottom: 8 }}>↙</p>
                            <p style={{ fontSize: 14, fontWeight: 500 }}>Drag the fragment card here to begin</p>
                            <p style={{ fontSize: 12, marginTop: 4 }}>Responses placed within {PROX_PX}px of each other will form a group automatically</p>
                        </div>
                    )}
                </ReactFlow>
            </div>
        </div>
    );
}

// ─────────────────────────────────────────────────────────────────────────────
// Export
// ─────────────────────────────────────────────────────────────────────────────

export default function ManualPlacementView() {
    return (
        <ReactFlowProvider>
            <ManualPlacementInner />
        </ReactFlowProvider>
    );
}
