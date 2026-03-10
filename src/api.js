const BASE_URL = import.meta.env.VITE_API_URL || "";

export async function uploadRepo(file) {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${BASE_URL}/api/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(err.detail || "Upload failed");
  }

  return res.json();
}

export async function uploadGithubUrl(url) {
  const res = await fetch(`${BASE_URL}/api/upload/github`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ github_url: url }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(err.detail || "Upload failed");
  }

  return res.json();
}

export async function getAnalysis(sessionId) {
  const res = await fetch(`${BASE_URL}/api/analysis/${sessionId}`);

  if (!res.ok) {
    throw new Error("Failed to fetch analysis");
  }

  return res.json();
}
