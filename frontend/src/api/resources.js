import request from "./axios";
async function uploadResource(file) {
  const formData = new FormData();
  formData.append("file", file);
  return await request.post("/resources/upload", formData);
}
async function getResources() {
  return await request.get("/resources");
}
async function getResource(id) {
  return await request.get(`/resources/${id}`);
}
async function deleteResource(id) {
  await request.delete(`/resources/${id}`);
}
async function searchResources(query) {
  return await request.post("/resources/search", null, { params: { query } });
}
async function resourceQA(resourceId, question) {
  return await request.post("/resources/qa", null, { params: { resource_id: resourceId, question } });
}
export {
  deleteResource,
  getResource,
  getResources,
  resourceQA,
  searchResources,
  uploadResource
};
