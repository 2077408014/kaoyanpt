import axios from "./axios";
const adminApi = {
  listInstitutions: () => axios.get("/admin/institutions"),
  createInstitution: (name) => axios.post("/admin/institutions", { name }),
  listUsers: (params) => axios.get("/admin/users", { params }),
  createStaffUser: (data) => axios.post("/admin/users", data),
  updateStaffUser: (userId, data) => axios.put(`/admin/users/${userId}`, data),
  deleteStaffUser: (userId) => axios.delete(`/admin/users/${userId}`)
};
const teacherApi = {
  myClasses: () => axios.get("/teacher/classes"),
  classStudents: (classId) => axios.get(`/teacher/classes/${classId}/students`),
  studentOverview: (studentId) => axios.get(`/teacher/students/${studentId}/overview`),
  studentMistakes: (studentId, subject) => axios.get(`/teacher/students/${studentId}/mistakes`, { params: { subject } }),
  studentMistakeDetail: (studentId, mistakeId) => axios.get(`/teacher/students/${studentId}/mistakes/${mistakeId}`),
  removeStudent: (classId, studentId) => axios.delete(`/teacher/classes/${classId}/students/${studentId}`),
  addStudent: (classId, email) => axios.post(`/teacher/classes/${classId}/students/add`, { email }),
  suspendStudent: (classId, studentId) => axios.post(`/teacher/classes/${classId}/students/${studentId}/suspend`),
  restoreStudent: (classId, studentId) => axios.post(`/teacher/classes/${classId}/students/${studentId}/restore`),
  // 公告
  listAnnouncements: (classId) => axios.get(`/teacher/classes/${classId}/announcements`),
  createAnnouncement: (classId, data) => axios.post(`/teacher/classes/${classId}/announcements`, data),
  updateAnnouncement: (id, data) => axios.put(`/teacher/announcements/${id}`, data),
  deleteAnnouncement: (id) => axios.delete(`/teacher/announcements/${id}`),
  // 作业
  listAssignments: (classId) => axios.get(`/teacher/classes/${classId}/assignments`),
  createAssignment: (classId, data) => axios.post(`/teacher/classes/${classId}/assignments`, data),
  getAssignment: (assignmentId) => axios.get(`/teacher/assignments/${assignmentId}`),
  updateAssignment: (assignmentId, data) => axios.put(`/teacher/assignments/${assignmentId}`, data),
  uploadAssignmentImage: (file) => {
    const formData = new FormData();
    formData.append("file", file);
    return axios.post("/teacher/assignments/upload-image", formData);
  },
  deleteAssignment: (assignmentId) => axios.delete(`/teacher/assignments/${assignmentId}`),
  listSubmissions: (assignmentId) => axios.get(`/teacher/assignments/${assignmentId}/submissions`),
  gradeSubmission: (assignmentId, data) => axios.post(`/teacher/assignments/${assignmentId}/grade`, data)
};
const institutionApi = {
  classes: (institutionId) => axios.get("/institution/classes", { params: { institution_id: institutionId } }),
  classStudents: (classId) => axios.get(`/institution/classes/${classId}/students`),
  classTeachers: (classId) => axios.get(`/institution/classes/${classId}/teachers`),
  studentOverview: (studentId) => axios.get(`/institution/students/${studentId}/overview`),
  studentMistakes: (studentId, subject) => axios.get(`/institution/students/${studentId}/mistakes`, { params: { subject } }),
  studentMistakeDetail: (studentId, mistakeId) => axios.get(`/institution/students/${studentId}/mistakes/${mistakeId}`),
  // 写操作
  createClass: (data) => axios.post("/institution/classes", data),
  updateClass: (classId, data) => axios.patch(`/institution/classes/${classId}`, data),
  resetCode: (classId) => axios.post(`/institution/classes/${classId}/reset-code`),
  listTeachers: (institutionId) => axios.get("/institution/teachers", { params: { institution_id: institutionId } }),
  createTeacher: (data) => axios.post("/institution/teachers", data),
  updateTeacher: (teacherId, data) => axios.put(`/institution/teachers/${teacherId}`, data),
  deleteTeacher: (teacherId) => axios.delete(`/institution/teachers/${teacherId}`),
  assignTeacher: (classId, teacherId) => axios.post(`/institution/classes/${classId}/teachers`, { teacher_id: teacherId }),
  unassignTeacher: (classId, teacherId) => axios.delete(`/institution/classes/${classId}/teachers/${teacherId}`)
};
const studentClassApi = {
  join: (code) => axios.post("/classes/join", { code }),
  my: () => axios.get("/classes/my"),
  announcements: (classId) => axios.get(`/classes/${classId}/announcements`),
  assignments: (classId) => axios.get(`/classes/${classId}/assignments`),
  assignment: (assignmentId) => axios.get(`/classes/assignments/${assignmentId}`),
  submit: (assignmentId, content, images) => axios.post(`/classes/assignments/${assignmentId}/submissions`, { content, images: images || [] }),
  uploadSubmissionImage: (file) => {
    const fd = new FormData();
    fd.append("file", file);
    return axios.post("/classes/assignments/upload-image", fd, {
      headers: { "Content-Type": "multipart/form-data" }
    });
  }
};
export {
  adminApi,
  institutionApi,
  studentClassApi,
  teacherApi
};
