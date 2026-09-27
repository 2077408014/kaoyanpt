import axios from "./axios";
async function agentChat(data) {
  return await axios.post("/agent/chat", data);
}
async function getAgentHistory(agent_name, limit = 50) {
  return await axios.get("/agent/history", { params: { agent_name, limit } });
}
async function clearAgentHistory(agent_name) {
  return await axios.delete("/agent/history", { params: { agent_name } });
}
export {
  agentChat,
  clearAgentHistory,
  getAgentHistory
};
