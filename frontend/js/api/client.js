export async function requestJson(path, options = {}) {
  const { timeoutMs, signal, ...fetchOptions } = options;
  const timeoutController = timeoutMs ? new AbortController() : null;
  const signals = [signal, timeoutController?.signal].filter(Boolean);
  const combinedSignal = combineSignals(signals);
  let timeoutId = null;
  if (timeoutController) {
    timeoutId = window.setTimeout(() => timeoutController.abort(), timeoutMs);
  }

  try {
    const response = await fetch(path, {
      headers: {
        Accept: "application/json",
        ...(fetchOptions.headers || {}),
      },
      ...fetchOptions,
      signal: combinedSignal,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || "Request failed.");
    }
    return data;
  } finally {
    if (timeoutId) {
      window.clearTimeout(timeoutId);
    }
  }
}


function combineSignals(signals) {
  if (!signals.length) {
    return undefined;
  }
  if (signals.length === 1) {
    return signals[0];
  }
  const controller = new AbortController();
  const abort = () => controller.abort();
  signals.forEach((signal) => {
    if (signal.aborted) {
      abort();
    } else {
      signal.addEventListener("abort", abort, { once: true });
    }
  });
  return controller.signal;
}
