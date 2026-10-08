const BASE_URL = import.meta.env.VITE_API_URL || "";
const DEFAULT_TIMEOUT_MS = 150_000;

async function request(path, options = {}, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${BASE_URL}${path}`, {
      ...options,
      signal: controller.signal,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Request failed" }));
      throw new Error(err.detail || "Request failed");
    }

    return res.json();
  } catch (error) {
    if (error?.name === "AbortError") {
      throw new Error("The analysis request timed out. Try a smaller repository.");
    }
    throw error;
  } finally {
    window.clearTimeout(timer);
  }
}

export async function uploadRepo(file) {
  const formData = new FormData();
  formData.append("file", file);
  return request("/api/upload", {
    method: "POST",
    body: formData,
  });
}

export async function uploadGithubUrl(url) {
  return request("/api/upload/github", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ github_url: url }),
  });
}

export async function getAnalysis(sessionId) {
  return request(`/api/analysis/${encodeURIComponent(sessionId)}`);
}
