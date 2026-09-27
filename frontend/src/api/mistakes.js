import axios from "./axios";
async function createMistake(data) {
  return await axios.post("/mistakes", data);
}
async function getMistakes(params) {
  return await axios.get("/mistakes", { params });
}
async function getMistake(id) {
  return await axios.get(`/mistakes/${id}`);
}
async function updateMistake(id, data) {
  return await axios.put(`/mistakes/${id}`, data);
}
async function deleteMistake(id) {
  await axios.delete(`/mistakes/${id}`);
}
async function reviewMistake(id, data) {
  await axios.post(`/mistakes/${id}/review`, data);
}
async function getTodayReviews() {
  return await axios.get("/mistakes/review/today");
}
async function uploadMistakeImage(file) {
  const formData = new FormData();
  formData.append("file", file);
  return await axios.post("/mistakes/upload", formData);
}
async function recognizeMistake(imagePath) {
  return await axios.post("/mistakes/recognize", { image_path: imagePath });
}
async function getSimilarMistakes(id) {
  return await axios.get(`/mistakes/${id}/similar`);
}
export {
  createMistake,
  deleteMistake,
  getMistake,
  getMistakes,
  getSimilarMistakes,
  getTodayReviews,
  recognizeMistake,
  reviewMistake,
  updateMistake,
  uploadMistakeImage
};
