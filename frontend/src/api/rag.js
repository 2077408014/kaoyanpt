import axios from "./axios";
async function uploadDocument(file, subject, onProgress) {
  const formData = new FormData();
  formData.append("file", file);
  if (subject) {
    formData.append("subject", subject);
  }
  return await axios.post("/rag/upload", formData, {
    timeout: 3e5,
    onUploadProgress: (progressEvent) => {
      if (onProgress && progressEvent.total) {
        const percent = Math.round(progressEvent.loaded / progressEvent.total * 100);
        onProgress(percent);
      }
    }
  });
}
async function getDocuments(subject) {
  const data = await axios.get("/rag/documents", { params: { subject } });
  return data.documents;
}
async function getDocument(id) {
  return await axios.get(`/rag/documents/${id}`);
}
function getDocumentDownloadUrl(id) {
  const token = localStorage.getItem("token");
  return `/api/rag/documents/${id}/download?token=${token || ""}`;
}
function getDocumentPreviewUrl(id) {
  const token = localStorage.getItem("token");
  return `/api/rag/documents/${id}/download?token=${token || ""}&preview=true`;
}
async function deleteDocument(id) {
  return await axios.delete(`/rag/documents/${id}`);
}
async function indexDocument(id) {
  return await axios.post(`/rag/documents/${id}/index`);
}
async function cancelIndexDocument(id) {
  return await axios.post(`/rag/documents/${id}/index/cancel`);
}
async function getKnowledgeStatus() {
  return await axios.get("/rag/knowledge/status");
}
async function ragChat(question, top_k = 3, threshold = 0.3, subject, onlyKnowledgeBase = false) {
  return await axios.post("/rag/chat", {
    question,
    top_k,
    threshold,
    subject,
    only_knowledge_base: onlyKnowledgeBase
  });
}
async function ragSearch(question, top_k = 3, threshold = 0.3) {
  return await axios.post("/rag/search", null, {
    params: {
      question,
      top_k,
      threshold
    }
  });
}
export {
  cancelIndexDocument,
  deleteDocument,
  getDocument,
  getDocumentDownloadUrl,
  getDocumentPreviewUrl,
  getDocuments,
  getKnowledgeStatus,
  indexDocument,
  ragChat,
  ragSearch,
  uploadDocument
};
