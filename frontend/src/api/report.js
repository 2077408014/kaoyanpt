import axios from "./axios";
async function getStudyReport(period = "week") {
  return await axios.get("/report/study", { params: { period } });
}
async function getWeeklyTrend() {
  return await axios.get("/report/weekly-trend");
}
export {
  getStudyReport,
  getWeeklyTrend
};
