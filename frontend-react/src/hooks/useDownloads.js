import {
  createContext,
  createElement,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState
} from "react";
import {
  cancelDownload,
  clearTerminalDownloads,
  listDownloads,
  retryDownload
} from "../api/downloadsApi";

const ACTIVE_STATUSES = new Set(["queued", "resolving", "downloading", "merging", "finalizing"]);
const TERMINAL_STATUSES = new Set(["completed", "completed_with_errors", "failed", "cancelled"]);
const POLL_ACTIVE_MS = 1500;
const POLL_IDLE_MS = 5000;

const DownloadJobsContext = createContext(null);

function normalizeJob(job) {
  return {
    jobId: job.job_id,
    postId: job.post_id,
    status: job.status,
    availability: job.availability || "unknown",
    progress: job.progress ?? null,
    message: job.message || "",
    mediaType: job.media_type || "media",
    title: job.title || "",
    subreddit: job.subreddit || "",
    author: job.author || "",
    thumbnailUrl: job.thumbnail_url || null,
    createdAt: job.created_at || null,
    startedAt: job.started_at || null,
    completedAt: job.completed_at || null,
    files: Array.isArray(job.files) ? job.files : [],
    error: job.error || null,
    errorCode: job.error_code || null,
    warnings: Array.isArray(job.warnings) ? job.warnings : [],
    succeededCount: job.succeeded_count ?? null,
    failedCount: job.failed_count ?? null,
    retryOfId: job.retry_of_id || null,
    bytesDownloaded: job.bytes_downloaded ?? null,
    totalBytes: job.total_bytes ?? null,
    cancellable: Boolean(job.cancellable),
    retryable: Boolean(job.retryable)
  };
}

export function DownloadJobsProvider({ children }) {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [pendingActions, setPendingActions] = useState({});
  const jobsRef = useRef([]);
  const requestRef = useRef(null);

  useEffect(() => {
    jobsRef.current = jobs;
  }, [jobs]);

  const refreshJobs = useCallback(async ({ signal } = {}) => {
    requestRef.current?.abort();
    const controller = new AbortController();
    requestRef.current = controller;
    const requestSignal = signal || controller.signal;

    try {
      setLoading((current) => current || jobsRef.current.length === 0);
      const response = await listDownloads("all", { signal: requestSignal });
      setJobs(Array.isArray(response.jobs) ? response.jobs.map(normalizeJob) : []);
      setError(null);
    } catch (refreshError) {
      if (refreshError.name !== "AbortError") {
        setError("Unable to load download jobs.");
      }
    } finally {
      if (requestRef.current === controller) {
        requestRef.current = null;
      }
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshJobs();

    return () => {
      requestRef.current?.abort();
    };
  }, [refreshJobs]);

  const activeJobCount = jobs.filter((job) => ACTIVE_STATUSES.has(job.status)).length;
  const hasActiveJobs = activeJobCount > 0;

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      refreshJobs();
    }, hasActiveJobs ? POLL_ACTIVE_MS : POLL_IDLE_MS);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [hasActiveJobs, refreshJobs]);

  const runJobAction = useCallback(
    async (key, action, fallbackMessage) => {
      setActionError(null);
      setPendingActions((current) => ({ ...current, [key]: true }));
      try {
        const result = await action();
        await refreshJobs();
        return result;
      } catch (actionFailure) {
        if (actionFailure.name !== "AbortError") {
          setActionError(actionFailure.message || fallbackMessage);
        }
        return null;
      } finally {
        setPendingActions((current) => {
          const next = { ...current };
          delete next[key];
          return next;
        });
      }
    },
    [refreshJobs]
  );

  const cancelJob = useCallback(
    (jobId) =>
      runJobAction(
        `cancel:${jobId}`,
        () => cancelDownload(jobId),
        "Unable to cancel this download."
      ),
    [runJobAction]
  );

  const retryJob = useCallback(
    (jobId) =>
      runJobAction(
        `retry:${jobId}`,
        () => retryDownload(jobId),
        "Unable to retry this download."
      ),
    [runJobAction]
  );

  const clearFinished = useCallback(
    () =>
      runJobAction(
        "clear",
        () => clearTerminalDownloads(),
        "Unable to clear finished records."
      ),
    [runJobAction]
  );

  const value = useMemo(
    () => ({
      jobs,
      loading,
      error,
      actionError,
      activeJobCount,
      hasActiveJobs,
      pendingActions,
      terminalJobCount: jobs.filter((job) => TERMINAL_STATUSES.has(job.status)).length,
      refreshJobs,
      cancelJob,
      retryJob,
      clearFinished
    }),
    [
      jobs,
      loading,
      error,
      actionError,
      activeJobCount,
      hasActiveJobs,
      pendingActions,
      refreshJobs,
      cancelJob,
      retryJob,
      clearFinished
    ]
  );

  return createElement(DownloadJobsContext.Provider, { value }, children);
}

export function useDownloads() {
  const context = useContext(DownloadJobsContext);
  if (!context) {
    throw new Error("useDownloads must be used within DownloadJobsProvider.");
  }
  return context;
}
