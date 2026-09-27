import axios from "./axios";
async function login(data) {
  return await axios.post("/auth/login", data);
}
async function register(data) {
  return await axios.post("/auth/register", data);
}
async function getMe() {
  return await axios.get("/auth/me");
}
async function updateAIConfig(config) {
  return await axios.put("/auth/ai-config", config);
}
async function forgotPassword(data) {
  return await axios.post("/auth/forgot-password", data);
}
async function sendRegisterCode(data) {
  return await axios.post("/auth/send-verification-code", data);
}
async function resetPassword(data) {
  return await axios.post("/auth/reset-password", data);
}
async function changePassword(data) {
  return await axios.post("/auth/change-password", data);
}
export {
  changePassword,
  forgotPassword,
  getMe,
  login,
  register,
  resetPassword,
  sendRegisterCode,
  updateAIConfig
};
