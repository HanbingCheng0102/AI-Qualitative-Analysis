import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSetAtom } from "jotai";
import { clusterRunStatus, selectedClusterId } from "../state";
import {
    pipeline_ingestSurvey,
    pipeline_embedFragments,
    pipeline_runClustering,
    pipeline_labelClusters,
    pipeline_llmCluster,
} from "../api/aiServiceFacade";
import { documents_findAll, survey_delete } from "../api/dataFacade";

// ── Step definitions ──────────────────────────────────────────────────────────
const AUTO_STEPS = [
    { id: "ingest",   label: "Parsing & PII Redaction",   desc: "Reading the CSV/XLSX and anonymising personal data" },
    { id: "embed",    label: "Embedding Responses",        desc: "Converting text to semantic vectors" },
    { id: "cluster",  label: "Discovering Clusters",       desc: "Running UMAP + HDBSCAN to group similar responses" },
    { id: "label",    label: "Labelling Clusters",         desc: "Asking Claude to name each theme" },
];

const MANUAL_STEPS = [
    { id: "ingest",   label: "Parsing & PII Redaction",   desc: "Reading the CSV/XLSX and anonymising personal data" },
    { id: "embed",    label: "Embedding Responses",        desc: "Converting text to semantic vectors" },
];

const LLM_STEPS = [
    { id: "ingest",   label: "Parsing & PII Redaction",   desc: "Reading the CSV/XLSX and anonymising personal data" },
    { id: "embed",    label: "Embedding Responses",        desc: "Converting text to semantic vectors" },
    { id: "llm",      label: "LLM Semantic Clustering",   desc: "Filtering and clustering responses using Claude" },
];

const STATUS = { idle: "idle", running: "running", done: "done", error: "error" };

// ── Helpers ───────────────────────────────────────────────────────────────────
function StepRow({ step, status, detail }) {
    const icons = {
        idle:    <span className="text-gray-400 text-xl">○</span>,
        running: <span className="text-blue-500 text-xl animate-spin inline-block">⟳</span>,
        done:    <span className="text-green-500 text-xl">✓</span>,
        error:   <span className="text-red-500 text-xl">✗</span>,
    };
    const colours = {
        idle:    "border-gray-200 bg-white",
        running: "border-blue-300 bg-blue-50",
        done:    "border-green-300 bg-green-50",
        error:   "border-red-300 bg-red-50",
    };
    return (
        <div className={`flex items-start gap-4 p-4 rounded-lg border ${colours[status]} transition-all`}>
            <div className="mt-0.5 w-6 flex-shrink-0">{icons[status]}</div>
            <div className="flex-1">
                <p className="font-semibold text-gray-800">{step.label}</p>
                <p className="text-sm text-gray-500">{step.desc}</p>
                {detail && <p className="text-sm mt-1 text-gray-700">{detail}</p>}
            </div>
        </div>
    );
}

// ── LLM log panel ─────────────────────────────────────────────────────────────
function LLMLog({ entries }) {
    const bottomRef = useRef(null);
    useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [entries]);

    if (!entries.length) return null;

    return (
        <div className="mt-3 rounded-lg border border-gray-200 bg-gray-50 overflow-hidden">
            <div className="px-3 py-2 border-b border-gray-200 bg-gray-100">
                <p className="text-xs font-semibold text-gray-600">Live log</p>
            </div>
            <div className="max-h-56 overflow-y-auto p-2 space-y-1 font-mono text-xs">
                {entries.map((e, i) => (
                    <div key={i} className={`flex items-start gap-2 ${e.type === "error" ? "text-red-600" : "text-gray-700"}`}>
                        <span className={`flex-shrink-0 font-bold w-14 ${
                            e.type === "kept"     ? "text-green-600" :
                            e.type === "dropped"  ? "text-gray-400"  :
                            e.type === "new"      ? "text-purple-600":
                            e.type === "assign"   ? "text-blue-600"  :
                            e.type === "done"     ? "text-green-700" : "text-red-600"
                        }`}>[{e.type}]</span>
                        <span className="break-all">{e.text}</span>
                    </div>
                ))}
                <div ref={bottomRef} />
            </div>
        </div>
    );
}

// ── Column filter builder ─────────────────────────────────────────────────────
function ColumnFilters({ columns, filters, onChange }) {
    if (!columns.length) return null;

    return (
        <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
                Column filters <span className="text-gray-400 font-normal">(optional — leave blank to include all rows)</span>
            </label>
            <div className="space-y-2">
                {columns.map(col => (
                    <div key={col} className="flex items-center gap-2">
                        <span className="text-xs text-gray-500 w-40 truncate flex-shrink-0" title={col}>{col}</span>
                        <span className="text-xs text-gray-400">contains</span>
                        <input
                            type="text"
                            value={filters[col] ?? ""}
                            onChange={e => onChange({ ...filters, [col]: e.target.value })}
                            placeholder={`e.g. Female`}
                            className="flex-1 border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-blue-400"
                        />
                    </div>
                ))}
            </div>
        </div>
    );
}

// ── Main view ─────────────────────────────────────────────────────────────────
export default function SurveyIngestionView() {
    const navigate = useNavigate();
    const fileInputRef = useRef(null);

    const [file, setFile] = useState(null);
    const [surveyName, setSurveyName] = useState("");
    const [mode, setMode] = useState("auto"); // "auto" | "manual" | "llm" | "llm-manual"
    const [minClusterSize, setMinClusterSize] = useState(5);
    const [researchQuestion, setResearchQuestion] = useState("");
    const [columnFilters, setColumnFilters] = useState({});
    const [detectedColumns, setDetectedColumns] = useState([]);
    const [running, setRunning] = useState(false);
    const [error, setError] = useState(null);
    const [result, setResult] = useState(null);

    // Per-step status
    const [stepStatus, setStepStatus] = useState({
        ingest: STATUS.idle, embed: STATUS.idle, cluster: STATUS.idle, label: STATUS.idle, llm: STATUS.idle,
    });
    const [stepDetail, setStepDetail] = useState({});

    // LLM live log
    const [llmLog, setLlmLog] = useState([]);

    const setRunStatus = useSetAtom(clusterRunStatus);
    const setSelectedCluster = useSetAtom(selectedClusterId);

    // Dataset manager
    const [datasets, setDatasets]     = useState([]);
    const [deleteTarget, setDeleteTarget] = useState(null);
    const [deleting, setDeleting]     = useState(false);

    useEffect(() => {
        documents_findAll().then(setDatasets).catch(console.error);
    }, []);

    // Parse column names from the selected file for the column-filter UI
    useEffect(() => {
        if (!file || mode !== "llm") { setDetectedColumns([]); setColumnFilters({}); return; }

        const META_COLS = new Set(["id", "respondent_id", "timestamp", "date", "time", "site", "ward"]);

        const reader = new FileReader();
        reader.onload = (e) => {
            const text = e.target.result;
            // Only handle CSV here (XLSX would need a library — server handles it)
            if (file.name.toLowerCase().endsWith(".csv")) {
                const firstLine = text.split("\n")[0] ?? "";
                const cols = firstLine.split(",").map(c =>
                    c.trim().replace(/^["']|["']$/g, "")
                ).filter(c => c && !META_COLS.has(c.toLowerCase()));
                setDetectedColumns(cols);
                setColumnFilters({});
            }
        };
        reader.readAsText(file);
    }, [file, mode]);

    const handleDelete = async () => {
        if (!deleteTarget) return;
        setDeleting(true);
        try {
            await survey_delete(deleteTarget._id.toString());
            setDatasets(prev => prev.filter(d => d._id.toString() !== deleteTarget._id.toString()));
            setDeleteTarget(null);
        } catch (err) {
            console.error(err);
        } finally {
            setDeleting(false);
        }
    };

    const setStep = (id, status, detail = null) => {
        setStepStatus(s => ({ ...s, [id]: status }));
        if (detail !== null) setStepDetail(d => ({ ...d, [id]: detail }));
    };

    const handleFileChange = (e) => {
        const f = e.target.files[0];
        if (!f) return;
        setFile(f);
        if (!surveyName) setSurveyName(f.name.replace(/\.[^/.]+$/, ""));
    };

    const addLog = (type, text) => setLlmLog(prev => [...prev, { type, text }]);

    const handleRun = async () => {
        if (!file) { setError("Please select a CSV or XLSX file."); return; }
        if (!surveyName.trim()) { setError("Please enter a survey name."); return; }

        setError(null);
        setRunning(true);
        setRunStatus("running");
        setResult(null);
        setLlmLog([]);
        setStepStatus({ ingest: STATUS.idle, embed: STATUS.idle, cluster: STATUS.idle, label: STATUS.idle, llm: STATUS.idle });
        setStepDetail({});

        try {
            // Step 1 — Ingest (all modes)
            setStep("ingest", STATUS.running);
            const ingestRes = await pipeline_ingestSurvey(file, surveyName.trim());
            setStep("ingest", STATUS.done, `${ingestRes.fragment_count} responses loaded, PII redacted`);

            // Step 2 — Embed (all modes)
            setStep("embed", STATUS.running);
            const embedRes = await pipeline_embedFragments(ingestRes.doc_id);
            setStep("embed", STATUS.done, `${embedRes.embedded_count} responses embedded`);

            if (mode === "manual") {
                setRunStatus("done");
                navigate("/manual-placement", { state: { doc_id: ingestRes.doc_id, survey_name: surveyName.trim() } });
                return;
            }

            if (mode === "llm-manual") {
                setRunStatus("done");
                navigate("/manual-placement", {
                    state: {
                        doc_id: ingestRes.doc_id,
                        survey_name: surveyName.trim(),
                        use_llm: true,
                        research_question: researchQuestion.trim(),
                    },
                });
                return;
            }

            if (mode === "llm") {
                setStep("llm", STATUS.running);

                // Active filters — drop empty strings
                const activeFilters = Object.fromEntries(
                    Object.entries(columnFilters).filter(([, v]) => v.trim())
                );

                let doneEvent = null;
                let hadError  = false;

                await pipeline_llmCluster(
                    ingestRes.doc_id,
                    researchQuestion.trim(),
                    activeFilters,
                    (evt) => {
                        if (evt.event === "filter") {
                            if (evt.kept) addLog("kept",    `✓ ${evt.name}`);
                            else           addLog("dropped", `✗ ${evt.name} — filtered out`);
                        } else if (evt.event === "assign") {
                            if (evt.action === "new")
                                addLog("new",    `★ ${evt.name} → new cluster "${evt.cluster_label}"`);
                            else
                                addLog("assign", `→ ${evt.name} → "${evt.cluster_label}"`);
                        } else if (evt.event === "done") {
                            doneEvent = evt;
                            addLog("done", `Complete — ${evt.cluster_count} clusters, ${evt.fragment_count} fragments`);
                        } else if (evt.event === "error") {
                            hadError = true;
                            addLog("error", evt.detail);
                        }
                    },
                );

                if (hadError || !doneEvent) {
                    setStep("llm", STATUS.error, "Pipeline failed — see log above");
                    setError("LLM clustering encountered an error. Check the log for details.");
                    setRunStatus("error");
                    return;
                }

                setStep("llm", STATUS.done, `${doneEvent.cluster_count} clusters from ${doneEvent.fragment_count} fragments`);
                setResult({ ...doneEvent, doc_id: ingestRes.doc_id });
                setRunStatus("done");
                return;
            }

            // Auto mode: Step 3 — UMAP+HDBSCAN, Step 4 — LLM label
            setStep("cluster", STATUS.running);
            const clusterRes = await pipeline_runClustering(ingestRes.doc_id, minClusterSize);
            setStep("cluster", STATUS.done, `${clusterRes.cluster_count} clusters found, ${clusterRes.noise_count} uncategorised`);

            setStep("label", STATUS.running);
            const labelRes = await pipeline_labelClusters(clusterRes.cluster_ids);
            setStep("label", STATUS.done, `${labelRes.labelled.length} clusters labelled`);

            setResult({ ...clusterRes, doc_id: ingestRes.doc_id });
            setRunStatus("done");

        } catch (err) {
            setError(err.message);
            setRunStatus("error");
            // Mark whichever step was running as errored
            setStepStatus(prev => {
                const updated = { ...prev };
                for (const k of Object.keys(updated)) {
                    if (updated[k] === STATUS.running) updated[k] = STATUS.error;
                }
                return updated;
            });
        } finally {
            setRunning(false);
        }
    };

    const handleViewGraph = () => {
        if (result?.cluster_ids?.[0]) setSelectedCluster(result.cluster_ids[0]);
        navigate("/cluster-graph", { state: { doc_id: result?.doc_id } });
    };

    const currentSteps = mode === "auto" ? AUTO_STEPS : (mode === "manual" || mode === "llm-manual") ? MANUAL_STEPS : LLM_STEPS;

    return (
        <div className="p-8 max-w-2xl">
            <h1 className="text-3xl font-bold text-gray-800 mb-1">Survey Ingestion</h1>
            <p className="text-gray-500 mb-8">
                Upload a CSV, XLSX, or plain text (.txt) file to run the AI pipeline.
            </p>

            {/* ── File + config ── */}
            <div className="space-y-4 mb-8">
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Survey file (CSV, XLSX, or TXT)</label>
                    <input
                        type="file"
                        accept=".csv,.xlsx,.xls,.txt"
                        ref={fileInputRef}
                        onChange={handleFileChange}
                        className="block w-full text-sm text-gray-700 file:mr-4 file:py-2 file:px-4
                                   file:rounded file:border-0 file:text-sm file:font-semibold
                                   file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Survey name</label>
                    <input
                        type="text"
                        value={surveyName}
                        onChange={e => setSurveyName(e.target.value)}
                        placeholder="e.g. NHS Ward Survey Q1 2024"
                        className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                    />
                </div>

                {/* ── Mode selector ── */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Clustering mode</label>
                    <div className="grid grid-cols-2 gap-3">
                        {[
                            {
                                value: "auto",
                                title: "Auto",
                                desc: "UMAP + HDBSCAN finds clusters mathematically, Claude labels them",
                            },
                            {
                                value: "manual",
                                title: "Manual",
                                desc: "You drag responses onto a whiteboard; proximity forms groups",
                            },
                            {
                                value: "llm",
                                title: "LLM Semantic",
                                desc: "Claude reads every response and decides which theme it belongs to",
                                badge: "New",
                            },
                            {
                                value: "llm-manual",
                                title: "LLM Manual",
                                desc: "You drag responses; Claude reads group samples to suggest placement instead of maths",
                                badge: "New",
                            },
                        ].map(opt => (
                            <button
                                key={opt.value}
                                type="button"
                                onClick={() => setMode(opt.value)}
                                className={`relative text-left p-3 rounded-lg border-2 transition-colors
                                    ${mode === opt.value
                                        ? "border-blue-500 bg-blue-50"
                                        : "border-gray-200 bg-white hover:border-gray-300"}`}
                            >
                                {opt.badge && (
                                    <span className="absolute top-2 right-2 text-xs font-bold bg-purple-500 text-white rounded px-1.5 py-0.5">
                                        {opt.badge}
                                    </span>
                                )}
                                <p className={`text-sm font-semibold ${mode === opt.value ? "text-blue-700" : "text-gray-800"}`}>
                                    {opt.title}
                                </p>
                                <p className="text-xs text-gray-500 mt-0.5 leading-snug">{opt.desc}</p>
                            </button>
                        ))}
                    </div>
                </div>

                {/* ── Auto-only: min cluster size ── */}
                {mode === "auto" && (
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Minimum cluster size <span className="text-gray-400 font-normal">(smaller = more clusters)</span>
                        </label>
                        <input
                            type="number"
                            value={minClusterSize}
                            min={2}
                            max={50}
                            onChange={e => setMinClusterSize(Number(e.target.value))}
                            className="w-24 border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                        />
                    </div>
                )}

                {/* ── LLM modes: research question (+ column filters for full LLM mode) ── */}
                {(mode === "llm" || mode === "llm-manual") && (
                    <div className="space-y-4 p-4 rounded-lg border border-purple-200 bg-purple-50">
                        <div>
                            <label className="block text-sm font-medium text-purple-800 mb-1">
                                Research question <span className="text-purple-400 font-normal">(optional)</span>
                            </label>
                            <textarea
                                value={researchQuestion}
                                onChange={e => setResearchQuestion(e.target.value)}
                                rows={2}
                                placeholder={`e.g. "Focus on responses about staff communication and attitude"\nor "Identify themes related to pain management and discharge planning"`}
                                className="w-full border border-purple-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400 bg-white resize-none"
                            />
                            <p className="text-xs text-purple-500 mt-1">
                                Claude will filter out irrelevant responses and cluster with this focus in mind.
                                Leave blank to cluster all responses without a specific lens.
                            </p>
                        </div>

                        {mode === "llm" && (
                            <>
                                <ColumnFilters
                                    columns={detectedColumns}
                                    filters={columnFilters}
                                    onChange={setColumnFilters}
                                />
                                {detectedColumns.length === 0 && file && (
                                    <p className="text-xs text-purple-400">
                                        Column filters are auto-detected from CSV files. Upload a CSV to enable them, or use the research question for semantic filtering.
                                    </p>
                                )}
                            </>
                        )}

                        {mode === "llm-manual" && (
                            <p className="text-xs text-purple-500">
                                After {20} placements, Claude will read actual responses from each group to suggest where the next one fits — guided by your research question above.
                            </p>
                        )}
                    </div>
                )}
            </div>

            {/* ── Run button ── */}
            <button
                onClick={handleRun}
                disabled={running || !file}
                className="mb-8 px-6 py-3 rounded-lg font-semibold text-white
                           bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300
                           disabled:cursor-not-allowed transition-colors"
            >
                {running ? "Running pipeline…" : "Run Pipeline"}
            </button>

            {/* ── Pipeline steps ── */}
            <div className="space-y-3 mb-4">
                {currentSteps.map(step => (
                    <StepRow
                        key={step.id}
                        step={step}
                        status={stepStatus[step.id]}
                        detail={stepDetail[step.id]}
                    />
                ))}
            </div>

            {/* ── LLM live log ── */}
            {mode === "llm" && <LLMLog entries={llmLog} />}

            {/* ── Error banner ── */}
            {error && (
                <div className="p-4 rounded-lg bg-red-50 border border-red-300 text-red-700 text-sm mt-4 mb-6">
                    <strong>Error:</strong> {error}
                </div>
            )}

            {/* ── Success + navigate ── */}
            {result && !error && (
                <div className="p-5 rounded-lg bg-green-50 border border-green-300 mt-4 mb-8">
                    <p className="text-green-800 font-semibold text-lg mb-1">Pipeline complete!</p>
                    <p className="text-green-700 text-sm mb-4">
                        {result.cluster_count} themes discovered from your survey.
                    </p>
                    <button
                        onClick={handleViewGraph}
                        className="px-5 py-2 rounded-lg font-semibold text-white bg-green-600 hover:bg-green-700 transition-colors"
                    >
                        View Cluster Graph →
                    </button>
                </div>
            )}

            {/* ── Dataset manager ── */}
            <div className="mt-4">
                <h2 className="text-base font-bold text-gray-700 mb-3">Uploaded Datasets</h2>
                {datasets.length === 0 && (
                    <p className="text-sm text-gray-400">No datasets uploaded yet.</p>
                )}
                <div className="space-y-2">
                    {datasets.map(doc => (
                        <div
                            key={doc._id.toString()}
                            className="flex items-center justify-between px-4 py-3 rounded-lg border border-gray-200 bg-white"
                        >
                            <div className="min-w-0">
                                <p className="text-sm font-semibold text-gray-800 truncate">{doc.name}</p>
                                <p className="text-xs text-gray-400 font-mono">{doc._id.toString()}</p>
                            </div>
                            <div className="flex gap-2 flex-shrink-0 ml-4">
                                <button
                                    onClick={() => navigate("/cluster-graph", { state: { doc_id: doc._id.toString() } })}
                                    className="text-xs px-3 py-1.5 rounded border border-blue-300 text-blue-600 hover:bg-blue-50 transition-colors"
                                >
                                    View graph
                                </button>
                                <button
                                    onClick={() => setDeleteTarget(doc)}
                                    className="text-xs px-3 py-1.5 rounded border border-red-200 text-red-500 hover:bg-red-50 transition-colors"
                                >
                                    Delete
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* ── Delete confirmation modal ── */}
            {deleteTarget && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
                    <div className="bg-white rounded-xl shadow-2xl p-6 w-96">
                        <h3 className="text-base font-bold text-gray-800 mb-2">Delete dataset?</h3>
                        <p className="text-sm text-gray-500 mb-1">This will permanently delete:</p>
                        <ul className="text-sm text-gray-600 list-disc list-inside mb-4 space-y-0.5">
                            <li>The survey document <strong>{deleteTarget.name}</strong></li>
                            <li>All its fragments and embeddings</li>
                            <li>All clusters and labels</li>
                            <li>All manual placement feedback</li>
                        </ul>
                        <p className="text-sm text-red-600 font-medium mb-5">This cannot be undone.</p>
                        <div className="flex gap-3">
                            <button
                                onClick={() => setDeleteTarget(null)}
                                disabled={deleting}
                                className="flex-1 py-2 rounded-lg border border-gray-300 text-gray-600 text-sm hover:bg-gray-50 transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleDelete}
                                disabled={deleting}
                                className="flex-1 py-2 rounded-lg bg-red-500 hover:bg-red-600 text-white text-sm font-semibold transition-colors disabled:opacity-50"
                            >
                                {deleting ? "Deleting…" : "Yes, delete"}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
