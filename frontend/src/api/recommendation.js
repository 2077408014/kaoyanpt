import request from "./axios";
async function analyzeWeakPoints() {
  return await request.get("/recommend/analysis");
}
async function generateRecommendations(count = 5, subject) {
  const params = new URLSearchParams();
  params.append("count", count.toString());
  if (subject) {
    params.append("subject", subject);
  }
  return await request.post(`/recommend/generate?${params.toString()}`);
}
async function getRecommendations(completed) {
  return await request.get("/recommend/list", { params: { completed } });
}
async function completeRecommendation(id, result) {
  return await request.post(`/recommend/${id}/complete`, { result });
}
async function deleteRecommendation(id) {
  return await request.delete(`/recommend/${id}`);
}
async function getRecommendationReport() {
  return await request.get("/recommend/report");
}
async function getAgentStatus() {
  return await request.get("/recommend/agents");
}
async function toggleAgent(agentName, enabled) {
  return await request.post(`/recommend/agents/${agentName}/toggle`, { enabled });
}
async function getCollaborationLogs(limit, offset) {
  return await request.get("/recommend/logs", { params: { limit, offset } });
}
export {
  analyzeWeakPoints,
  completeRecommendation,
  deleteRecommendation,
  generateRecommendations,
  getAgentStatus,
  getCollaborationLogs,
  getRecommendationReport,
  getRecommendations,
  toggleAgent
};
