// ── Shared API base URL ──
// All API fetch URLs should use this constant instead of hardcoding
// window.location.origin or an absolute URL. Using the origin ensures
// requests work from any host (localhost, Tailscale IP, domain name, etc.)
// without per-environment configuration.
export const API_BASE = window.location.origin;
