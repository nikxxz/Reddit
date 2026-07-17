import { useCallback, useEffect, useRef, useState } from "react";
import {
  getUniversalSearch,
  listUniversalProviders,
  startUniversalSearch
} from "../api/universalSearchApi";

const TERMINAL_STATUSES = new Set([
  "completed",
  "completed_with_errors",
  "failed",
  "cancelled"
]);

const INITIAL_STATE = {
  searchId: null,
  status: "idle",
  providers: {},
  providerMetadata: [],
  items: [],
  error: null,
  polling: false
};

export function useUniversalSearch() {
  const [state, setState] = useState(INITIAL_STATE);
  const generationRef = useRef(0);
  const pollTimerRef = useRef(null);
  const controllerRef = useRef(null);

  const clearPolling = useCallback(() => {
    if (pollTimerRef.current) {
      window.clearTimeout(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  const loadProviders = useCallback(() => {
    const controller = new AbortController();
    listUniversalProviders({ signal: controller.signal })
      .then((response) => {
        setState((current) => ({
          ...current,
          providerMetadata: response.providers || []
        }));
      })
      .catch((error) => {
        if (error.name === "AbortError") {
          return;
        }
        setState((current) => ({
          ...current,
          error: "Unable to load Universal Search providers."
        }));
      });
    return controller;
  }, []);

  useEffect(() => {
    const controller = loadProviders();
    return () => {
      controller.abort();
      controllerRef.current?.abort();
      clearPolling();
    };
  }, [clearPolling, loadProviders]);

  const pollSearch = useCallback((searchId, generation) => {
    getUniversalSearch(searchId)
      .then((response) => {
        if (generation !== generationRef.current) {
          return;
        }
        const terminal = TERMINAL_STATUSES.has(response.status);
        setState((current) => ({
          ...current,
          searchId,
          status: response.status,
          providers: response.providers || {},
          items: response.items || [],
          error: response.status === "failed" ? "Universal Search failed." : null,
          polling: !terminal
        }));
        if (!terminal) {
          pollTimerRef.current = window.setTimeout(() => {
            pollSearch(searchId, generation);
          }, 1200);
        }
      })
      .catch((error) => {
        if (generation !== generationRef.current || error.name === "AbortError") {
          return;
        }
        setState((current) => ({
          ...current,
          status: "failed",
          error: error.message || "Unable to check search status.",
          polling: false
        }));
      });
  }, []);

  const submitSearch = useCallback((payload) => {
    generationRef.current += 1;
    const generation = generationRef.current;
    clearPolling();
    controllerRef.current?.abort();

    const controller = new AbortController();
    controllerRef.current = controller;
    setState((current) => ({
      ...current,
      searchId: null,
      status: "searching",
      providers: Object.fromEntries(
        payload.providers.map((provider) => [
          provider,
          { status: "queued", result_count: 0, error: null }
        ])
      ),
      items: [],
      error: null,
      polling: false
    }));

    return startUniversalSearch(payload, { signal: controller.signal })
      .then((response) => {
        if (generation !== generationRef.current) {
          return null;
        }
        const terminal = TERMINAL_STATUSES.has(response.status);
        setState((current) => ({
          ...current,
          searchId: response.search_id,
          status: response.status,
          providers: response.providers || {},
          polling: !terminal
        }));
        if (!terminal) {
          pollTimerRef.current = window.setTimeout(() => {
            pollSearch(response.search_id, generation);
          }, 1200);
        }
        return response;
      })
      .catch((error) => {
        if (error.name === "AbortError" || generation !== generationRef.current) {
          return null;
        }
        setState((current) => ({
          ...current,
          status: "failed",
          error: error.message || "Universal Search failed.",
          polling: false
        }));
        return null;
      });
  }, [clearPolling, pollSearch]);

  return {
    state,
    submitSearch,
    reloadProviders: loadProviders
  };
}

