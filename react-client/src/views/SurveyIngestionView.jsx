import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSetAtom } from "jotai";
import { clusterRunStatus, selectedClusterId } from "../state";
import {
    pipeline_ingestSurvey,
    pipeline_embedFragments,
    pipeline_runClustering,
    pipeline_labelClusters,
} from "../api/aiServiceFacade";
import { documents_findAll, survey_delete } from "../api/dataFacade";

// ── Step definitions ──────────────────────────────────────────────────────────
const STEPS = [
    { id: "ingest",   label: "Parsing & PII Redaction",   desc: "Reading the CSV/XLSX and anonymising personal data" },
    { id: "embed",    label: "Embedding Responses",        desc: "Converting text to semantic vectors" },
    { id: "cluster",  label: "Discovering Clusters",       desc: "Running UMAP + HDBSCAN to group similar responses" },
    { id: "label",    label: "Labelling Clusters",         desc: "Asking Claude to name each theme" },
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

// ── Main view ─────────────────────────────────────────────────────────────────
export default function SurveyIngestionView() {
    const navigate = useNavigate();
    const fileInputRef = useRef(null);

    const [file, setFile] = useState(null);
    const [surveyName, setSurveyName] = useState("");
    const [minClusterSize, setMinClusterSize] = useState(5);
    const [running, setRunning] = useState(false);
    const [error, setError] = useState(null);
    const [result, setResult] = useState(null); // { cluster_count, noise_count, cluster_ids, doc_id }

    // Per-step status
    const [stepStatus, setStepStatus] = useState({
        ingest: STATUS.idle,
        embed:  STATUS.idle,
        cluster: STATUS.idle,
        label:  STATUS.idle,
    });
    const [stepDetail, setStepDetail] = useState({});

    const setRunStatus = useSetAtom(clusterRunStatus);
    const setSelectedCluster = useSetAtom(selectedClusterId);

    // Dataset manager
    const [datasets, setDatasets]         = useState([]);
    const [deleteTarget, setDeleteTarget] = useState(null); // doc being confirmed
    const [deleting, setDeleting]         = useState(false);

    useEffect(() => {
        documents_findAll().then(setDatasets).catch(console.error);
    }, []);

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

    const handleRun = async () => {
        if (!file) { setError("Please select a CSV or XLSX file."); return; }
        if (!surveyName.trim()) { setError("Please enter a survey name."); return; }

        setError(null);
        setRunning(true);
        setRunStatus("running");
        setResult(null);
        setStepStatus({ ingest: STATUS.idle, embed: STATUS.idle, cluster: STATUS.idle, label: STATUS.idle });
        setStepDetail({});

        try {
            // Step 1 — Ingest
            setStep("ingest", STATUS.running);
            const ingestRes = await pipeline_ingestSurvey(file, surveyName.trim());
            setStep("ingest", STATUS.done, `${ingestRes.fragment_count} responses loaded, PII redacted`);

            // Step 2 — Embed
            setStep("embed", STATUS.running);
            const embedRes = await pipeline_embedFragments(ingestRes.doc_id);
            setStep("embed", STATUS.done, `${embedRes.embedded_count} responses embedded`);

            // Step 3 — Cluster
            setStep("cluster", STATUS.running);
            const clusterRes = await pipeline_runClustering(ingestRes.doc_id, minClusterSize);
            setStep(
                "cluster",
                STATUS.done,
                `${clusterRes.cluster_count} clusters found, ${clusterRes.noise_count} uncategorised`
            );

            // Step 4 — Label
            setStep("label", STATUS.running);
            const labelRes = await pipeline_labelClusters(clusterRes.cluster_ids);
            setStep("label", STATUS.done, `${labelRes.labelled.length} clusters labelled`);

            setResult({ ...clusterRes, doc_id: ingestRes.doc_id });
            setRunStatus("done");

        } catch (err) {
            // Mark the currently-running step as errored
            const currentStep = STEPS.find(s => stepStatus[s.id] === STATUS.running);
            if (currentStep) setStep(currentStep.id, STATUS.error, err.message);
            setError(err.message);
            setRunStatus("error");
        } finally {
            setRunning(false);
        }
    };

    const handleViewGraph = () => {
        if (result?.cluster_ids?.[0]) setSelectedCluster(result.cluster_ids[0]);
        navigate("/cluster-graph", { state: { doc_id: result?.doc_id } });
    };

    return (
        <div className="p-8 max-w-2xl">
            <h1 className="text-3xl font-bold text-gray-800 mb-1">Survey Ingestion</h1>
            <p className="text-gray-500 mb-8">
                Upload an NHS survey CSV or XLSX file to run the full AI pipeline:
                PII redaction → embeddings → clustering → LLM labelling.
            </p>

            {/* ── File + config ── */}
            <div className="space-y-4 mb-8">
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Survey file (CSV or XLSX)</label>
                    <input
                        type="file"
                        accept=".csv,.xlsx,.xls"
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
            <div className="space-y-3 mb-6">
                {STEPS.map(step => (
                    <StepRow
                        key={step.id}
                        step={step}
                        status={stepStatus[step.id]}
                        detail={stepDetail[step.id]}
                    />
                ))}
            </div>

            {/* ── Error banner ── */}
            {error && (
                <div className="p-4 rounded-lg bg-red-50 border border-red-300 text-red-700 text-sm mb-6">
                    <strong>Error:</strong> {error}
                </div>
            )}

            {/* ── Success + navigate ── */}
            {result && !error && (
                <div className="p-5 rounded-lg bg-green-50 border border-green-300 mb-8">
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
                        <p className="text-sm text-gray-500 mb-1">
                            This will permanently delete:
                        </p>
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
