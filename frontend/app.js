const statusEl = document.getElementById("status");
const analyseButton = document.getElementById("analyse-btn");

function updateStatus(message) {
  statusEl.innerHTML = message.replace(/\n/g, "<br>");
}

async function checkBackendConnection() {
  try {
    const healthResponse = await fetch("/api/health");
    if (!healthResponse.ok) {
      throw new Error("Health check failed");
    }

    const healthData = await healthResponse.json();
    if (healthData.status !== "ok") {
      throw new Error("Unexpected health response");
    }

    let redditMessage = "Reddit API connection: online";
    let redditError = "";

    try {
      const redditResponse = await fetch("/api/reddit/test");
      const redditData = await redditResponse.json();
      if (redditResponse.ok && redditData.status === "ok") {
        redditMessage = "Reddit API connection: online";
      } else {
        redditMessage = "Reddit API connection: failed";
        redditError = redditData.detail || redditData.error || "Unknown error";
      }
    } catch (redditErrorEvent) {
      redditMessage = "Reddit API connection: failed";
      redditError = redditErrorEvent.message || "Unable to reach Reddit API";
    }

    updateStatus(
      `Backend connection: online\n${redditMessage}${redditError ? `\n${redditError}` : ""}`,
    );
    analyseButton.disabled = false;
  } catch (error) {
    updateStatus("Backend connection: offline");
    analyseButton.disabled = true;
  }
}

window.addEventListener("load", checkBackendConnection);
