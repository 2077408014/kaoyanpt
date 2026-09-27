import request from "./axios";
async function getAssistantHistory(kind, limit = 50) {
  return await request.get(`/assistant/${kind}/history`, { params: { limit } });
}
async function clearAssistantHistory(kind) {
  await request.delete(`/assistant/${kind}/history`);
}
async function streamAssistant(kind, messages, handlers, signal) {
  const token = localStorage.getItem("token");
  let resp;
  try {
    resp = await fetch(`/api/assistant/${kind}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...token ? { Authorization: `Bearer ${token}` } : {}
      },
      body: JSON.stringify({ messages }),
      signal
    });
  } catch (e) {
    if (e?.name === "AbortError") throw e;
    throw new Error("无法连接服务器，请稍后重试");
  }
  if (!resp.ok || !resp.body) {
    let detail = `请求失败（HTTP ${resp.status}）`;
    try {
      const data = await resp.json();
      detail = data?.detail || detail;
    } catch {
    }
    throw new Error(detail);
  }
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  const handleEvent = (rawEvent) => {
    const line = rawEvent.split("\n").find((l) => l.startsWith("data:"));
    if (!line) return;
    try {
      const data = JSON.parse(line.slice(5).trim());
      if (data.delta) handlers.onDelta(data.delta);
      else if (data.action) handlers.onAction(data.action);
      else if (data.error) handlers.onError(data.error);
    } catch {
    }
  };
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let sep;
    while ((sep = buffer.indexOf("\n\n")) >= 0) {
      const rawEvent = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      if (rawEvent.trim()) handleEvent(rawEvent);
    }
  }
  if (buffer.trim()) handleEvent(buffer);
}
export {
  clearAssistantHistory,
  getAssistantHistory,
  streamAssistant
};
