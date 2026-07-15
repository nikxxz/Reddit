const LABELS = {
  checking: "Checking...",
  online: "Online",
  failed: "Failed"
};

export function StatusIndicator({ status }) {
  return (
    <span className={`status status-${status}`} aria-live="polite">
      <span className="status-dot" aria-hidden="true" />
      <span>{LABELS[status] ?? LABELS.checking}</span>
    </span>
  );
}
