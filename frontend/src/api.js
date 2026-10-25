const BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
let token = null;
export const setToken = (t) => { token = t; };

async function req(path, { method = "GET", body, form } = {}) {
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  let payload;
  if (form) payload = form;
  else if (body) { headers["Content-Type"] = "application/json"; payload = JSON.stringify(body); }
  let r;
  // GET requests are retried a couple of times so a backend that is just restarting / waking up does not flash a red error
  const tries = method === "GET" ? 3 : 1;
  for (let i = 0; i < tries; i++) {
    try { r = await fetch(BASE + path, { method, headers, body: payload }); break; }
    catch {
      if (i === tries - 1) throw new Error("Cannot reach the server. If the backend is on a free plan it may be waking up - wait ~30s and retry.");
      await new Promise((res) => setTimeout(res, 1200 * (i + 1)));
    }
  }
  if (!r.ok) {
    let m = r.statusText;
    try { const j = await r.json(); m = j.detail || m; } catch { /* ignore */ }
    throw new Error(typeof m === "string" ? m : JSON.stringify(m));
  }
  return r.json();
}
const q = (o) => {
  const p = new URLSearchParams();
  Object.entries(o).forEach(([k, v]) => v !== undefined && v !== null && v !== "" && p.set(k, v));
  const s = p.toString();
  return s ? `?${s}` : "";
};

export const api = {
  meta: () => req("/api/meta"),
  login: (role, user_id, password) => req("/api/auth/login", { method: "POST", body: { role, user_id, password } }),
  signup: (role, user_id, password, name) => req("/api/auth/signup", { method: "POST", body: { role, user_id, password, name } }),
  students: (dept) => req(`/api/students${q({ dept })}`),
  commandCenter: (student_id, dept) => req(`/api/command-center${q({ student_id, dept })}`),
  summary: (id) => req(`/api/students/${id}/summary`),
  student360: (id) => req(`/api/students/${id}`),
  skills: (id) => req(`/api/students/${id}/skills`),
  wellness: (id) => req(`/api/students/${id}/wellness`),
  copilot: (id) => req(`/api/students/${id}/copilot`),
  whatif: (id) => req(`/api/students/${id}/whatif`),
  sendEmail: (id, body) => req(`/api/students/${id}/email`, { method: "POST", body: { body } }),
  complete: (id) => req(`/api/students/${id}/complete`, { method: "POST" }),
  regenerate: (id) => req(`/api/students/${id}/regenerate`, { method: "POST" }),
  markRead: (id) => req(`/api/students/${id}/inbox/read`, { method: "POST" }),
  tracker: (student_id, mode, dept) => req(`/api/tracker${q({ student_id, mode, dept })}`),
  upload: (file) => { const f = new FormData(); f.append("file", file); return req("/api/dataset/upload", { method: "POST", form: f }); },
  resetDataset: () => req("/api/dataset/reset", { method: "POST" }),
};
