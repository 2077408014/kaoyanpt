import axios from "./axios";
async function getWordStats(category) {
  return await axios.get("/words/stats", { params: category ? { category } : {} });
}
async function getTodayWords(count = 20, category) {
  return await axios.get("/words/today", { params: { count, category } });
}
async function getDailyReviewWords(category) {
  return await axios.get("/words/daily-review", { params: { category } });
}
async function getReviewWordsByRange(timeRange = "today") {
  return await axios.get("/words/review-words", { params: { time_range: timeRange } });
}
async function getWordCategories() {
  return await axios.get("/words/categories");
}
async function getReviewWords() {
  return await axios.get("/words/review");
}
async function getWordList(params) {
  return await axios.get("/words/list", { params });
}
async function studyWord(wordId, result, opts) {
  return await axios.post("/words/study", {
    word_id: wordId,
    result,
    session_id: opts?.session_id,
    source: opts?.source ?? "card",
    quiz_result: opts?.quiz_result
  });
}
async function getStudyPlan() {
  return await axios.get("/words/plan");
}
async function saveStudyPlan(dailyWordCount, wordCategory, batchSize, studyMode) {
  return await axios.post("/words/plan", {
    daily_word_count: dailyWordCount,
    word_category: wordCategory,
    batch_size: batchSize ?? 20,
    study_mode: studyMode ?? "mixed"
  });
}
async function getStudySession() {
  const res = await axios.get("/words/session");
  return res && Object.keys(res).length > 0 ? res : null;
}
async function saveStudySession(session) {
  return await axios.post("/words/session", session);
}
async function clearStudySession() {
  return await axios.delete("/words/session");
}
async function uploadWordbook(file, category) {
  const formData = new FormData();
  formData.append("file", file);
  if (category) {
    formData.append("category", category);
  }
  return await axios.post("/words/upload-wordbook", formData);
}
async function getSessionCards(count = 10, category) {
  return await axios.get("/words/session-cards", { params: { count, category } });
}
async function completeSession(sessionId) {
  return await axios.post("/words/session-complete", { session_id: sessionId });
}
async function getQuiz(wordIds, count = 8) {
  return await axios.get("/words/quiz", { params: { word_ids: wordIds.join(","), count } });
}
async function answerQuiz(payload) {
  return await axios.post("/words/quiz/answer", payload);
}
async function getStudyRecords(page = 1, pageSize = 10) {
  return await axios.get("/words/records", { params: { page, page_size: pageSize } });
}
async function exportStudyRecords() {
  const blob = await axios.get("/words/records/export", { responseType: "blob" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "背诵记录.xlsx";
  a.click();
  URL.revokeObjectURL(url);
}
async function importStudyRecords(file) {
  const formData = new FormData();
  formData.append("file", file);
  return await axios.post("/words/records/import", formData);
}
async function getPushConfig() {
  return await axios.get("/words/push-config");
}
async function savePushConfig(cfg) {
  return await axios.post("/words/push-config", cfg);
}
export {
  answerQuiz,
  clearStudySession,
  completeSession,
  exportStudyRecords,
  getDailyReviewWords,
  getPushConfig,
  getQuiz,
  getReviewWords,
  getReviewWordsByRange,
  getSessionCards,
  getStudyPlan,
  getStudyRecords,
  getStudySession,
  getTodayWords,
  getWordCategories,
  getWordList,
  getWordStats,
  importStudyRecords,
  savePushConfig,
  saveStudyPlan,
  saveStudySession,
  studyWord,
  uploadWordbook
};
