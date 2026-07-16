import { useCallback, useEffect, useReducer, useRef } from "react";
import { browseRedditEntityMedia } from "../api/redditEntities";

const INITIAL_STATE = {
  status: "idle",
  entity: null,
  items: [],
  error: null,
  nextCursor: null,
  isLoadingMore: false,
  loadMoreError: null,
  lastRequest: null,
  activeRequestId: null,
  message: null
};

function uniqueItems(currentItems, nextItems) {
  const seen = new Set(currentItems.map((item) => item.id));
  const unique = nextItems.filter((item) => {
    if (!item?.id || seen.has(item.id)) {
      return false;
    }
    seen.add(item.id);
    return true;
  });
  return [...currentItems, ...unique];
}

function reducer(state, action) {
  if (action.type === "LOAD_STARTED") {
    return { ...INITIAL_STATE, status: "loading", lastRequest: action.request, activeRequestId: action.requestId };
  }
  if (action.type === "MORE_STARTED") {
    return { ...state, isLoadingMore: true, loadMoreError: null, activeRequestId: action.requestId };
  }
  if (action.requestId && state.activeRequestId && action.requestId !== state.activeRequestId) {
    return state;
  }
  if (action.type === "LOAD_SUCCEEDED") {
    return {
      ...state,
      status: action.items.length ? "success" : "empty",
      entity: action.entity,
      items: action.items,
      error: null,
      nextCursor: action.nextCursor,
      isLoadingMore: false,
      message: action.message,
      activeRequestId: action.requestId
    };
  }
  if (action.type === "LOAD_FAILED") {
    return { ...INITIAL_STATE, status: "error", error: action.error, activeRequestId: action.requestId };
  }
  if (action.type === "MORE_SUCCEEDED") {
    return {
      ...state,
      status: "success",
      entity: action.entity || state.entity,
      items: uniqueItems(state.items, action.items),
      nextCursor: action.nextCursor,
      isLoadingMore: false,
      loadMoreError: null,
      message: action.message,
      activeRequestId: action.requestId
    };
  }
  if (action.type === "MORE_FAILED") {
    return { ...state, isLoadingMore: false, loadMoreError: action.error, activeRequestId: action.requestId };
  }
  return state;
}

function errorMessage(error) {
  return error instanceof Error && error.message ? error.message : "Unable to browse Reddit media.";
}

export function useEntityMedia() {
  const [state, dispatch] = useReducer(reducer, INITIAL_STATE);
  const requestRef = useRef(null);
  const moreRequestRef = useRef(null);
  const requestIdRef = useRef(0);
  const stateRef = useRef(state);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  useEffect(() => () => {
    requestRef.current?.abort();
    moreRequestRef.current?.abort();
  }, []);

  const load = useCallback(async (request) => {
    requestRef.current?.abort();
    moreRequestRef.current?.abort();
    const controller = new AbortController();
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    requestRef.current = controller;
    dispatch({ type: "LOAD_STARTED", request, requestId });
    try {
      const response = await browseRedditEntityMedia(request, { signal: controller.signal });
      dispatch({
        type: "LOAD_SUCCEEDED",
        requestId,
        entity: response.entity,
        items: response.items,
        nextCursor: response.next_cursor,
        message: response.message
      });
    } catch (error) {
      if (error.name !== "AbortError") {
        dispatch({ type: "LOAD_FAILED", requestId, error: errorMessage(error) });
      }
    } finally {
      if (requestRef.current === controller) {
        requestRef.current = null;
      }
    }
  }, []);

  const loadMore = useCallback(async () => {
    const current = stateRef.current;
    if (!current.lastRequest || !current.nextCursor || current.isLoadingMore) {
      return;
    }
    const controller = new AbortController();
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    moreRequestRef.current = controller;
    dispatch({ type: "MORE_STARTED", requestId });
    try {
      const response = await browseRedditEntityMedia(
        { ...current.lastRequest, cursor: current.nextCursor },
        { signal: controller.signal }
      );
      dispatch({
        type: "MORE_SUCCEEDED",
        requestId,
        entity: response.entity,
        items: response.items,
        nextCursor: response.next_cursor,
        message: response.message
      });
    } catch (error) {
      if (error.name !== "AbortError") {
        dispatch({ type: "MORE_FAILED", requestId, error: errorMessage(error) });
      }
    } finally {
      if (moreRequestRef.current === controller) {
        moreRequestRef.current = null;
      }
    }
  }, []);

  return { state, load, loadMore };
}
