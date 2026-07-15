import { useCallback, useEffect, useReducer, useRef } from "react";
import { searchRedditMedia } from "../api/redditSearchApi";

const INITIAL_STATE = {
  status: "idle",
  items: [],
  error: null,
  nextAfter: null,
  isLoadingMore: false,
  loadMoreError: null,
  lastRequest: null,
  activeRequestId: null,
  responseMeta: null
};

function getSafeErrorMessage(error) {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return "Unable to complete Reddit search.";
}

function getUniqueItems(currentItems, nextItems) {
  const seenIds = new Set(currentItems.map((item) => item.id));
  const uniqueNextItems = nextItems.filter((item) => {
    if (!item?.id || seenIds.has(item.id)) {
      return false;
    }

    seenIds.add(item.id);
    return true;
  });

  return [...currentItems, ...uniqueNextItems];
}

function getResponseMeta(response) {
  return {
    mode: response.mode || null,
    query: response.query || "",
    subreddit: response.subreddit || null,
    requestedSort: response.requested_sort || null,
    effectiveSort: response.effective_sort || response.sort || null,
    mediaType: response.media_type || "all",
    sort: response.sort || null,
    timeFilter: response.time_filter || null,
    count: response.count || 0,
    message: response.message || null
  };
}

function redditSearchReducer(state, action) {
  if (action.type === "SEARCH_STARTED") {
    return {
      ...INITIAL_STATE,
      status: "loading",
      lastRequest: action.request,
      activeRequestId: action.requestId
    };
  }

  if (action.type === "LOAD_MORE_STARTED") {
    return {
      ...state,
      isLoadingMore: true,
      loadMoreError: null,
      activeRequestId: action.requestId
    };
  }

  if (
    action.requestId &&
    state.activeRequestId &&
    action.requestId !== state.activeRequestId
  ) {
    return state;
  }

  switch (action.type) {
    case "SEARCH_SUCCEEDED":
      return {
        ...state,
        status: "success",
        items: action.items,
        error: null,
        nextAfter: action.nextAfter,
        isLoadingMore: false,
        loadMoreError: null,
        responseMeta: action.responseMeta,
        activeRequestId: action.requestId
      };
    case "SEARCH_EMPTY":
      return {
        ...state,
        status: "empty",
        items: [],
        error: null,
        nextAfter: null,
        isLoadingMore: false,
        loadMoreError: null,
        responseMeta: action.responseMeta,
        activeRequestId: action.requestId
      };
    case "SEARCH_FAILED":
      return {
        ...state,
        status: "error",
        items: [],
        error: action.error,
        nextAfter: null,
        isLoadingMore: false,
        loadMoreError: null,
        activeRequestId: action.requestId
      };
    case "SEARCH_CANCELLED":
      return state;
    case "LOAD_MORE_SUCCEEDED":
      return {
        ...state,
        status: "success",
        items: getUniqueItems(state.items, action.items),
        nextAfter: action.nextAfter,
        isLoadingMore: false,
        loadMoreError: null,
        responseMeta: action.responseMeta,
        activeRequestId: action.requestId
      };
    case "LOAD_MORE_FAILED":
      return {
        ...state,
        isLoadingMore: false,
        loadMoreError: action.error,
        activeRequestId: action.requestId
      };
    case "RESET_SEARCH":
      return INITIAL_STATE;
    default:
      return state;
  }
}

function normalizeRequest(values, overrides = {}) {
  return {
    query: values.query?.trim() || "",
    subreddit: (values.subreddit || "").trim().replace(/^r\//i, ""),
    mediaType: values.mediaType || "all",
    sortBy: values.sortBy || "relevance",
    timeFilter: values.timeFilter || "all",
    includeNsfw: Boolean(values.includeNsfw),
    limit: values.limit || 24,
    ...overrides
  };
}

export function useRedditSearch() {
  const [state, dispatch] = useReducer(redditSearchReducer, INITIAL_STATE);
  const searchControllerRef = useRef(null);
  const loadMoreControllerRef = useRef(null);
  const requestIdRef = useRef(0);
  const stateRef = useRef(state);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  useEffect(
    () => () => {
      searchControllerRef.current?.abort();
      loadMoreControllerRef.current?.abort();
    },
    []
  );

  const runSearch = useCallback(async (values) => {
    const request = normalizeRequest(values);

    if (!request.query && !request.subreddit) {
      return;
    }

    searchControllerRef.current?.abort();
    loadMoreControllerRef.current?.abort();

    const controller = new AbortController();
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    searchControllerRef.current = controller;

    dispatch({ type: "SEARCH_STARTED", request, requestId });

    try {
      const response = await searchRedditMedia(request, {
        signal: controller.signal
      });
      const items = response.items || [];
      const actionType = items.length > 0 ? "SEARCH_SUCCEEDED" : "SEARCH_EMPTY";

      dispatch({
        type: actionType,
        requestId,
        items,
        nextAfter: response.next_after || null,
        responseMeta: getResponseMeta(response)
      });
    } catch (error) {
      if (error.name === "AbortError") {
        dispatch({ type: "SEARCH_CANCELLED", requestId });
        return;
      }

      dispatch({
        type: "SEARCH_FAILED",
        requestId,
        error: getSafeErrorMessage(error)
      });
    } finally {
      if (searchControllerRef.current === controller) {
        searchControllerRef.current = null;
      }
    }
  }, []);

  const retrySearch = useCallback(() => {
    const request = stateRef.current.lastRequest;

    if (request) {
      runSearch(request);
    }
  }, [runSearch]);

  const loadMore = useCallback(async () => {
    const currentState = stateRef.current;

    if (
      currentState.status !== "success" ||
      !currentState.lastRequest ||
      !currentState.nextAfter ||
      currentState.isLoadingMore
    ) {
      return;
    }

    loadMoreControllerRef.current?.abort();

    const controller = new AbortController();
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    loadMoreControllerRef.current = controller;

    dispatch({ type: "LOAD_MORE_STARTED", requestId });

    try {
      const request = normalizeRequest(currentState.lastRequest, {
        after: currentState.nextAfter
      });
      const response = await searchRedditMedia(request, {
        signal: controller.signal
      });

      dispatch({
        type: "LOAD_MORE_SUCCEEDED",
        requestId,
        items: response.items || [],
        nextAfter: response.next_after || null,
        responseMeta: getResponseMeta(response)
      });
    } catch (error) {
      if (error.name === "AbortError") {
        dispatch({ type: "SEARCH_CANCELLED", requestId });
        return;
      }

      dispatch({
        type: "LOAD_MORE_FAILED",
        requestId,
        error: getSafeErrorMessage(error)
      });
    } finally {
      if (loadMoreControllerRef.current === controller) {
        loadMoreControllerRef.current = null;
      }
    }
  }, []);

  const resetSearch = useCallback(() => {
    searchControllerRef.current?.abort();
    loadMoreControllerRef.current?.abort();
    dispatch({ type: "RESET_SEARCH" });
  }, []);

  return {
    state,
    runSearch,
    retrySearch,
    loadMore,
    resetSearch
  };
}
