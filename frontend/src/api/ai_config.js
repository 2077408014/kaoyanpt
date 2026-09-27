import request from "./axios";
async function listAIConfigs() {
  return await request.get("/ai-configs");
}
async function getAIConfig(id) {
  return await request.get(`/ai-configs/${id}`);
}
async function createAIConfig(data) {
  return await request.post("/ai-configs", data);
}
async function updateAIConfig(id, data) {
  return await request.put(`/ai-configs/${id}`, data);
}
async function deleteAIConfig(id) {
  return await request.delete(`/ai-configs/${id}`);
}
async function switchAIConfig(configId) {
  return await request.post("/ai-configs/switch", { config_id: configId });
}
export {
  createAIConfig,
  deleteAIConfig,
  getAIConfig,
  listAIConfigs,
  switchAIConfig,
  updateAIConfig
};
