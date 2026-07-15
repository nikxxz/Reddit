import { StatusIndicator } from "./StatusIndicator";

export function ConnectionCard({ title, status, message }) {
  return (
    <article className="connection-card">
      <h2>{title}</h2>
      <StatusIndicator status={status} />
      {message ? <p>{message}</p> : null}
    </article>
  );
}
