export async function apiRequest(
  path,
  {
    method = "GET",
    body,
    signal
  } = {}
) {
  const options = {
    method,
    headers: {
      Accept: "application/json"
    },
    signal
  };

  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }

  let response;

  try {
    response = await fetch(path, options);
  } catch (error) {
    if (error.name === "AbortError") {
      throw error;
    }

    throw new Error("Unable to reach the service.");
  }

  const data = await parseJsonSafely(response);

  if (!response.ok) {
    throw new Error(getReadableError(data, response.status));
  }

  return data;
}

async function parseJsonSafely(response) {
  const text = await response.text();

  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function getReadableError(data, status) {
  if (data && typeof data.message === "string") {
    return data.message;
  }

  if (data && typeof data.detail === "string") {
    return data.detail;
  }

  return `Request failed with status ${status}.`;
}
