import { requestJson } from "./client.js";


export function fetchHealth() {
  return requestJson("/api/health");
}


export function fetchAppConfig() {
  return requestJson("/api/app-config");
}
