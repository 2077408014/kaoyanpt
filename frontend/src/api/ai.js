import request from "./axios";
async function chat(message) {
  return await request.post("/ai/chat", { message });
}
async function command(cmd) {
  return await request.post("/ai/command", { command: cmd });
}
async function getHistory(limit = 20) {
  return await request.get("/ai/history", { params: { limit } });
}
async function clearHistory() {
  await request.delete("/ai/history");
}
async function recommendQuestions(data) {
  return await request.post("/ai/recommend", data);
}
export {
  chat,
  clearHistory,
  command,
  getHistory,
  recommendQuestions
};
