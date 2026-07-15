import { useCallback, useEffect, useReducer, useRef } from "react";
import {
  getRedditAuthStatus,
  getRedditLoginUrl,
  logoutRedditAccount
} from "../api/redditAuthApi";

const LOGIN_TIMEOUT_MS = 120000;
const POLL_INTERVAL_MS = 1000;
const POPUP_WIDTH = 560;
const POPUP_HEIGHT = 720;

const INITIAL_STATE = {
  status: "checking",
  connected: false,
  username: null,
  readOnly: true,
  error: null,
  popupOpen: false
};

function safeErrorMessage(error, fallback) {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallback;
}

function reducer(state, action) {
  switch (action.type) {
    case "STATUS_CHECK_STARTED":
      return {
        ...state,
        status: "checking",
        error: null
      };
    case "STATUS_CONNECTED":
      return {
        ...state,
        status: "connected",
        connected: true,
        username: action.username,
        readOnly: Boolean(action.readOnly),
        error: null,
        popupOpen: false
      };
    case "STATUS_DISCONNECTED":
      return {
        ...state,
        status: "disconnected",
        connected: false,
        username: null,
        readOnly: true,
        error: null,
        popupOpen: false
      };
    case "STATUS_FAILED":
      return {
        ...state,
        status: "error",
        error: action.error,
        popupOpen: false
      };
    case "LOGIN_STARTED":
      return {
        ...state,
        status: "connecting",
        error: null,
        popupOpen: true
      };
    case "LOGIN_FAILED":
      return {
        ...state,
        status: state.connected ? "connected" : "error",
        error: action.error,
        popupOpen: false
      };
    case "LOGIN_CANCELLED":
      return {
        ...state,
        status: state.connected ? "connected" : "disconnected",
        error: action.error || null,
        popupOpen: false
      };
    case "LOGOUT_STARTED":
      return {
        ...state,
        status: "disconnecting",
        error: null
      };
    case "LOGOUT_SUCCEEDED":
      return {
        ...state,
        status: "disconnected",
        connected: false,
        username: null,
        readOnly: true,
        error: null,
        popupOpen: false
      };
    case "LOGOUT_FAILED":
      return {
        ...state,
        status: state.connected ? "connected" : "error",
        error: action.error
      };
    case "CLEAR_ERROR":
      return {
        ...state,
        error: null,
        status: state.connected ? "connected" : "disconnected"
      };
    default:
      return state;
  }
}

function dispatchStatus(dispatch, status) {
  if (status.connected) {
    dispatch({
      type: "STATUS_CONNECTED",
      username: status.username,
      readOnly: status.readOnly
    });
    return true;
  }

  dispatch({ type: "STATUS_DISCONNECTED" });
  return false;
}

function getPopupFeatures() {
  const left = Math.max(0, window.screenX + (window.outerWidth - POPUP_WIDTH) / 2);
  const top = Math.max(0, window.screenY + (window.outerHeight - POPUP_HEIGHT) / 2);

  return [
    `width=${POPUP_WIDTH}`,
    `height=${POPUP_HEIGHT}`,
    `left=${Math.round(left)}`,
    `top=${Math.round(top)}`,
    "resizable=yes",
    "scrollbars=yes",
    "noopener=no"
  ].join(",");
}

export function useRedditAuth() {
  const [state, dispatch] = useReducer(reducer, INITIAL_STATE);
  const popupRef = useRef(null);
  const pollTimerRef = useRef(null);
  const timeoutTimerRef = useRef(null);
  const statusControllerRef = useRef(null);
  const loginControllerRef = useRef(null);
  const logoutControllerRef = useRef(null);

  const stopLoginWatchers = useCallback(() => {
    if (pollTimerRef.current) {
      window.clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }

    if (timeoutTimerRef.current) {
      window.clearTimeout(timeoutTimerRef.current);
      timeoutTimerRef.current = null;
    }
  }, []);

  const checkStatus = useCallback(
    async ({ silent = false, signal, updateDisconnected = true } = {}) => {
      if (!silent) {
        dispatch({ type: "STATUS_CHECK_STARTED" });
      }

      try {
        const status = await getRedditAuthStatus({ signal });

        if (status.connected || updateDisconnected) {
          return dispatchStatus(dispatch, status);
        }

        return false;
      } catch (error) {
        if (error.name === "AbortError") {
          return false;
        }

        if (!silent) {
          dispatch({
            type: "STATUS_FAILED",
            error: "Unable to check Reddit account status."
          });
        }

        return false;
      }
    },
    []
  );

  const beginPolling = useCallback(() => {
    stopLoginWatchers();

    pollTimerRef.current = window.setInterval(async () => {
      if (popupRef.current?.closed) {
        stopLoginWatchers();
        const connected = await checkStatus({ silent: true });

        if (!connected) {
          dispatch({
            type: "LOGIN_CANCELLED",
            error: "Reddit authorization was not completed."
          });
        }

        return;
      }

      const connected = await checkStatus({
        silent: true,
        updateDisconnected: false
      });

      if (connected) {
        stopLoginWatchers();
        popupRef.current?.close();
        popupRef.current = null;
      }
    }, POLL_INTERVAL_MS);

    timeoutTimerRef.current = window.setTimeout(() => {
      stopLoginWatchers();
      popupRef.current?.close();
      popupRef.current = null;
      dispatch({
        type: "LOGIN_CANCELLED",
        error: "Reddit authorization was not completed."
      });
    }, LOGIN_TIMEOUT_MS);
  }, [checkStatus, stopLoginWatchers]);

  const connect = useCallback(async () => {
    if (popupRef.current && !popupRef.current.closed) {
      popupRef.current.focus();
      return;
    }

    const popup = window.open("", "redditOAuthLogin", getPopupFeatures());

    if (!popup) {
      dispatch({
        type: "LOGIN_FAILED",
        error: "The Reddit login popup was blocked. Allow popups and try again."
      });
      return;
    }

    popupRef.current = popup;
    dispatch({ type: "LOGIN_STARTED" });

    loginControllerRef.current?.abort();
    const controller = new AbortController();
    loginControllerRef.current = controller;

    try {
      const loginUrl = await getRedditLoginUrl({
        frontendOrigin: window.location.origin,
        signal: controller.signal
      });

      popup.location.href = loginUrl;
      beginPolling();
    } catch (error) {
      popup.close();
      popupRef.current = null;

      if (error.name !== "AbortError") {
        dispatch({
          type: "LOGIN_FAILED",
          error: safeErrorMessage(error, "Unable to start Reddit login.")
        });
      }
    }
  }, [beginPolling]);

  const disconnect = useCallback(async () => {
    logoutControllerRef.current?.abort();
    const controller = new AbortController();
    logoutControllerRef.current = controller;

    dispatch({ type: "LOGOUT_STARTED" });

    try {
      await logoutRedditAccount({ signal: controller.signal });
      dispatch({ type: "LOGOUT_SUCCEEDED" });
    } catch (error) {
      if (error.name !== "AbortError") {
        dispatch({
          type: "LOGOUT_FAILED",
          error: "Unable to disconnect Reddit account."
        });
      }
    }
  }, []);

  const retry = useCallback(() => {
    statusControllerRef.current?.abort();
    const controller = new AbortController();
    statusControllerRef.current = controller;
    checkStatus({ signal: controller.signal });
  }, [checkStatus]);

  const clearError = useCallback(() => {
    dispatch({ type: "CLEAR_ERROR" });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    statusControllerRef.current = controller;
    checkStatus({ signal: controller.signal });

    return () => {
      controller.abort();
    };
  }, [checkStatus]);

  useEffect(() => {
    const handleMessage = async (event) => {
      if (event.origin !== window.location.origin) {
        return;
      }

      if (event.data?.type === "reddit-oauth-success" || event.data?.type === "reddit-auth-success") {
        stopLoginWatchers();
        popupRef.current?.close();
        popupRef.current = null;
        await checkStatus({ silent: true, updateDisconnected: false });
      }

      if (event.data?.type === "reddit-oauth-error" || event.data?.type === "reddit-auth-error") {
        stopLoginWatchers();
        popupRef.current?.close();
        popupRef.current = null;
        dispatch({
          type: "LOGIN_FAILED",
          error: event.data?.message || "Reddit authorization was not completed."
        });
      }
    };

    window.addEventListener("message", handleMessage);

    return () => {
      window.removeEventListener("message", handleMessage);
    };
  }, [checkStatus, stopLoginWatchers]);

  useEffect(
    () => () => {
      stopLoginWatchers();
      statusControllerRef.current?.abort();
      loginControllerRef.current?.abort();
      logoutControllerRef.current?.abort();
    },
    [stopLoginWatchers]
  );

  return {
    state,
    connect,
    disconnect,
    retry,
    clearError
  };
}
