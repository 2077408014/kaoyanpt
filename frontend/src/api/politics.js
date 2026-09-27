import axios from "./axios";
async function getRecitations(params) {
  return await axios.get("/politics", { params });
}
async function getRecitation(id) {
  return await axios.get(`/politics/${id}`);
}
async function createRecitation(data) {
  return await axios.post("/politics", data);
}
async function updateRecitation(id, data) {
  return await axios.put(`/politics/${id}`, data);
}
async function deleteRecitation(id) {
  await axios.delete(`/politics/${id}`);
}
async function reviewRecitation(id, result) {
  return await axios.post(`/politics/${id}/review`, { result });
}
async function uploadPoliticsImage(file) {
  const formData = new FormData();
  formData.append("file", file);
  return await axios.post("/politics/upload", formData);
}
async function recognizePoliticsImage(imagePath) {
  return await axios.post("/politics/recognize", { image_path: imagePath });
}
async function getReminders(reminderType) {
  return await axios.get("/politics/reminders", { params: { reminder_type: reminderType } });
}
async function createReminder(data) {
  return await axios.post("/politics/reminders", data);
}
async function updateReminder(id, data) {
  return await axios.put(`/politics/reminders/${id}`, data);
}
async function deleteReminder(id) {
  await axios.delete(`/politics/reminders/${id}`);
}
export {
  createRecitation,
  createReminder,
  deleteRecitation,
  deleteReminder,
  getRecitation,
  getRecitations,
  getReminders,
  recognizePoliticsImage,
  reviewRecitation,
  updateRecitation,
  updateReminder,
  uploadPoliticsImage
};
