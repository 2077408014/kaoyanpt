import axios from "./axios";
async function sendHeartbeat(seconds) {
  return await axios.post("/study/heartbeat", { seconds });
}
async function trackStudyEvent(eventType, count = 1) {
  return await axios.post("/study/event", { event_type: eventType, count });
}
async function getTodayStats() {
  return await axios.get("/study/today");
}
export {
  getTodayStats,
  sendHeartbeat,
  trackStudyEvent
};
