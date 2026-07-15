import { useCallback, useEffect, useRef, useState } from "react";
import {
  cancelDownload,
  getDownloadStatus,
  startDownload
} from "../api/downloadsApi";
import { useDownloads } from "./useDownloads";

const INITIAL_STATE = {
  jobId: null,
  status: "idle",
  progress: null,
  message: "",
  files: [],
  error: null,
  bytesDownloaded: null,
  totalBytes: null
};

const TERMINAL_STATUSES = new Set(["completed", "completed_with_errors", "failed", "cancelled"]);

function normalizeStatus(data) {
  return {
    jobId: data.job_id || null,
    status: data.status || "idle",
    progress: data.progress ?? null,
    message: data.message || "",
    files: Array.isArray(data.files) ? data.files : [],
    error: data.error || null,
    errorCode: data.error_code || null,
    warnings: Array.isArray(data.warnings) ? data.warnings : [],
    succeededCount: data.succeeded_count ?? null,
    failedCount: data.failed_count ?? null,
    retryOfId: data.retry_of_id || null,
    bytesDownloaded: data.bytes_downloaded ?? null,
    totalBytes: data.total_bytes ?? null
  };
}

export function useDownloadJob() {
  const { refreshJobs } = useDownloads();
  const [state, setState] = useState(INITIAL_STATE);
  const stateRef = useRef(INITIAL_STATE);
  const pollTimerRef = useRef(null);
  const activeRequestRef = useRef(null);

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      window.clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  const pollStatus = useCallback(
    async (jobId) => {
      try {
        const status = normalizeStatus(await getDownloadStatus(jobId));
        setState(status);

        if (TERMINAL_STATUSES.has(status.status)) {
          stopPolling();
        }
      } catch {
        setState((current) => ({
          ...current,
          status: "failed",
          error: "Unable to check download status."
        }));
        stopPolling();
      }
    },
    [stopPolling]
  );

  const beginPolling = useCallback(
    (jobId) => {
      stopPolling();
      pollTimerRef.current = window.setInterval(() => {
        pollStatus(jobId);
      }, 1000);
    },
    [pollStatus, stopPolling]
  );

  const start = useCallback(
    async (payload) => {
      if (!payload) {
        return;
      }

      const current = stateRef.current;
      if (!TERMINAL_STATUSES.has(current.status) && current.status !== "idle") {
        return;
      }

      setState({
        ...INITIAL_STATE,
        status: "queued",
        message: "Queued..."
      });

      activeRequestRef.current?.abort();
      const controller = new AbortController();
      activeRequestRef.current = controller;

      try {
        const response = await startDownload(payload, {
          signal: controller.signal
        });
        const nextState = {
          ...INITIAL_STATE,
          jobId: response.job_id,
          status: response.status || "queued",
          message: "Queued..."
        };
        setState(nextState);
        refreshJobs();
        beginPolling(response.job_id);
        pollStatus(response.job_id);
      } catch (error) {
        if (error.name !== "AbortError") {
          setState({
            ...INITIAL_STATE,
            status: "failed",
            error: error.message || "Unable to start download."
          });
        }
      }
    },
    [beginPolling, pollStatus, refreshJobs]
  );

  const cancel = useCallback(async () => {
    if (!state.jobId || TERMINAL_STATUSES.has(state.status)) {
      return;
    }

    try {
      const response = await cancelDownload(state.jobId);
      setState(normalizeStatus(response));
      refreshJobs();
      stopPolling();
    } catch {
      setState((current) => ({
        ...current,
        status: "failed",
        error: "Unable to cancel download."
      }));
    }
  }, [refreshJobs, state.jobId, state.status, stopPolling]);

  const reset = useCallback(() => {
    stopPolling();
    activeRequestRef.current?.abort();
    setState(INITIAL_STATE);
  }, [stopPolling]);

  useEffect(
    () => () => {
      stopPolling();
      activeRequestRef.current?.abort();
    },
    [stopPolling]
  );

  return {
    state,
    start,
    cancel,
    reset,
    isActive: state.status !== "idle" && !TERMINAL_STATUSES.has(state.status)
  };
}
