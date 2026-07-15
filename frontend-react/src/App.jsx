import { useCallback, useEffect, useRef, useState } from "react";
import { getBackendHealth } from "./api/healthApi";
import { getRedditConnectionStatus } from "./api/redditApi";
import { AppLayout } from "./components/layout/AppLayout";
import { DownloadJobsProvider } from "./hooks/useDownloads";
import { useRedditAuth } from "./hooks/useRedditAuth";
import "./styles/app.css";
import "./styles/account.css";
import "./styles/media-results.css";

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
  const redditAuth = useRedditAuth();

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
    <DownloadJobsProvider>
      <AppLayout
        connections={connections}
        isChecking={isChecking}
        onRetryConnections={handleRetry}
        redditAuth={redditAuth}
      />
    </DownloadJobsProvider>
  );
}
