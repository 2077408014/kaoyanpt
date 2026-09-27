import axios from "./axios";
async function startSupervisionSession() {
  return await axios.post("/supervision/session/start");
}
async function checkSupervision(data) {
  return await axios.post("/supervision/check", data);
}
async function getSupervisionSessionStats(sessionId) {
  return await axios.get(`/supervision/session/${sessionId}/stats`);
}
async function getSupervisionDailyStats(date) {
  return await axios.get("/supervision/daily-stats", { params: date ? { target_date: date } : {} });
}
export {
  checkSupervision,
  getSupervisionDailyStats,
  getSupervisionSessionStats,
  startSupervisionSession
};
