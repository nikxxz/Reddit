import { useCallback, useEffect, useRef, useState } from "react";
import { getBackendHealth } from "./api/healthApi";
import { getRedditConnectionStatus } from "./api/redditApi";
import { ConnectionCard } from "./components/ConnectionCard";
import "./styles/app.css";

const CHECKING_STATE = {
  backend: {
    status: "checking",
    message: ""
  },
  reddit: {
    status: "checking",
    message: ""
  }
};

export default function App() {
  const [connections, setConnections] = useState(CHECKING_STATE);
  const controllerRef = useRef(null);

  const checkConnections = useCallback(() => {
    controllerRef.current?.abort();

    const controller = new AbortController();
    controllerRef.current = controller;

    setConnections(CHECKING_STATE);

    Promise.allSettled([
      getBackendHealth({ signal: controller.signal }),
      getRedditConnectionStatus({ signal: controller.signal })
    ]).then(([backendResult, redditResult]) => {
      if (controller.signal.aborted) {
        return;
      }

      setConnections({
        backend:
          backendResult.status === "fulfilled"
            ? { status: "online", message: "" }
            : {
                status: "failed",
                message: "Unable to reach the backend."
              },
        reddit:
          redditResult.status === "fulfilled"
            ? { status: "online", message: "" }
            : {
                status: "failed",
                message: "Unable to verify Reddit connectivity."
              }
      });
    });
  }, []);

  useEffect(() => {
    checkConnections();

    return () => {
      controllerRef.current?.abort();
    };
  }, [checkConnections]);

  const handleRetry = () => {
    checkConnections();
  };

  const isChecking = Object.values(connections).some(
    (connection) => connection.status === "checking"
  );

  return (
    <main className="app-shell">
      <section className="workspace" aria-labelledby="workspace-title">
        <header className="workspace-header">
          <h1 id="workspace-title">Reddit Media Downloader</h1>
          <p>React Migration Workspace</p>
        </header>

        <div className="workspace-body">
          <p>Existing FastAPI backend connectivity</p>

          <div className="connection-grid">
            <ConnectionCard
              title="Backend API"
              status={connections.backend.status}
              message={connections.backend.message}
            />
            <ConnectionCard
              title="Reddit API"
              status={connections.reddit.status}
              message={connections.reddit.message}
            />
          </div>

          <div className="actions">
            <button
              className="retry-button"
              type="button"
              onClick={handleRetry}
              disabled={isChecking}
            >
              Retry Connections
            </button>
          </div>

          <p className="workspace-footer">
            Current frontend remains available on port 8000.
          </p>
        </div>
      </section>
    </main>
  );
}
