import axios from './axios'

// ---------- 通用类型 ----------
export interface TeacherBrief {
  id: number
  username: string
}

export interface Institution {
  id: number
  name: string
  created_at?: string
  class_count?: number
}

export interface ClassDetail {
  id: number
  name: string
  institution_id: number
  institution_name?: string
  join_code: string
  code_expires_at?: string | null
  code_max_uses?: number | null
  code_uses?: number
  student_count: number
  teacher_count: number
  teachers?: TeacherBrief[]
  created_at?: string
}

export interface ClassSettingsPayload {
  name?: string
  code_expires_at?: string | null
  code_max_uses?: number | null
}

export interface ClassListItem {
  id: number
  name: string
  institution_id: number
  institution_name?: string
  join_code?: string
  code_expires_at?: string | null
  code_max_uses?: number | null
  code_uses?: number
  student_count: number
  teacher_count: number
}

export interface StaffUser {
  id: number
  username: string
  email: string
  role: 'teacher' | 'institution_admin'
  institution_id: number
  institution_name?: string
  is_active?: boolean
  must_change_password?: boolean
  created_at?: string
}

export interface MyClass {
  id: number
  name: string
  institution_name?: string
  join_code: string
  teachers: TeacherBrief[]
  joined_at?: string
  status?: 'active' | 'suspended'
}

export interface StudentSummary {
  id: number
  username: string
  email?: string
  joined_at?: string
  status?: 'active' | 'suspended'
  study_time_7d: number
  words_7d: number
  questions_7d: number
  total_mistakes: number
  supervision_abnormal: number
}

export interface Announcement {
  id: number
  class_id: number
  author_id?: number
  author_name?: string
  title: string
  content: string
  created_at?: string
  updated_at?: string
}

export interface Submission {
  id: number
  assignment_id: number
  student_id: number
  student_name?: string
  content: string
  submitted_at?: string
  score?: number | null
  feedback?: string | null
  graded_at?: string | null
}

export interface Assignment {
  id: number
  class_id: number
  title: string
  content: string
  images?: string[]
  due_at?: string | null
  created_at?: string
  submission_count?: number
  graded_count?: number
  my_submission?: Submission | null
}

export interface DailyPoint {
  date: string
  study_time: number
  words: number
  questions: number
  mistakes: number
  abnormal: number
}

export interface StudentOverview {
  id: number
  username: string
  study_time_7d: number
  words_7d: number
  questions_7d: number
  total_mistakes: number
  mastered_mistakes: number
  supervision_abnormal: number
  mastery_distribution: Record<string, number>
  daily: DailyPoint[]
}

export interface ClassSummary {
  id: number
  name: string
  institution_id: number
  institution_name?: string
  join_code?: string
  code_expires_at?: string | null
  code_max_uses?: number | null
  code_uses?: number
  student_count: number
  avg_study_time_7d: number
  avg_words_7d: number
  avg_questions_7d: number
  avg_mistakes: number
  total_mistakes: number
  supervision_abnormal: number
}

export interface MistakeItem {
  id: number
  user_id: number
  subject: string
  knowledge_point?: string | null
  error_type?: string | null
  difficulty?: string | null
  mastery_level: string
  question_text?: string | null
  answer?: string | null
  analysis?: string | null
  error_reason?: string | null
  image_path?: string | null
  review_count: number
  correct_count: number
  created_at: string
  updated_at?: string | null
}

// ---------- 超管 ----------
export const adminApi = {
  listInstitutions: (): Promise<Institution[]> => axios.get('/admin/institutions'),
  createInstitution: (name: string): Promise<Institution> =>
    axios.post('/admin/institutions', { name }),
  listUsers: (params?: { role?: string; institution_id?: number }): Promise<StaffUser[]> =>
    axios.get('/admin/users', { params }),
  createStaffUser: (data: {
    username: string
    email: string
    password: string
    role: 'teacher' | 'institution_admin'
    institution_id: number
  }): Promise<StaffUser> => axios.post('/admin/users', data),
  updateStaffUser: (userId: number, data: {
    username?: string
    email?: string
    password?: string
    role?: 'teacher' | 'institution_admin'
    institution_id?: number
  }): Promise<StaffUser> => axios.put(`/admin/users/${userId}`, data),
  deleteStaffUser: (userId: number): Promise<{ message: string }> =>
    axios.delete(`/admin/users/${userId}`),
}

// ---------- 教师 ----------
export const teacherApi = {
  myClasses: (): Promise<ClassListItem[]> => axios.get('/teacher/classes'),
  classStudents: (classId: number): Promise<StudentSummary[]> =>
    axios.get(`/teacher/classes/${classId}/students`),
  studentOverview: (studentId: number): Promise<StudentOverview> =>
    axios.get(`/teacher/students/${studentId}/overview`),
  studentMistakes: (studentId: number, subject?: string): Promise<MistakeItem[]> =>
    axios.get(`/teacher/students/${studentId}/mistakes`, { params: { subject } }),
  studentMistakeDetail: (studentId: number, mistakeId: number): Promise<MistakeItem> =>
    axios.get(`/teacher/students/${studentId}/mistakes/${mistakeId}`),
  removeStudent: (classId: number, studentId: number): Promise<{ message: string }> =>
    axios.delete(`/teacher/classes/${classId}/students/${studentId}`),
  addStudent: (classId: number, email: string): Promise<{ message: string }> =>
    axios.post(`/teacher/classes/${classId}/students/add`, { email }),
  suspendStudent: (classId: number, studentId: number): Promise<{ message: string }> =>
    axios.post(`/teacher/classes/${classId}/students/${studentId}/suspend`),
  restoreStudent: (classId: number, studentId: number): Promise<{ message: string }> =>
    axios.post(`/teacher/classes/${classId}/students/${studentId}/restore`),
  // 公告
  listAnnouncements: (classId: number): Promise<Announcement[]> =>
    axios.get(`/teacher/classes/${classId}/announcements`),
  createAnnouncement: (classId: number, data: { title: string; content: string }): Promise<Announcement> =>
    axios.post(`/teacher/classes/${classId}/announcements`, data),
  updateAnnouncement: (id: number, data: Partial<{ title: string; content: string }>): Promise<Announcement> =>
    axios.put(`/teacher/announcements/${id}`, data),
  deleteAnnouncement: (id: number): Promise<{ message: string }> =>
    axios.delete(`/teacher/announcements/${id}`),
  // 作业
  listAssignments: (classId: number): Promise<Assignment[]> =>
    axios.get(`/teacher/classes/${classId}/assignments`),
  createAssignment: (classId: number, data: {
    title: string; content: string; images?: string[]; due_at?: string | null
  }): Promise<Assignment> =>
    axios.post(`/teacher/classes/${classId}/assignments`, data),
  getAssignment: (assignmentId: number): Promise<Assignment> =>
    axios.get(`/teacher/assignments/${assignmentId}`),
  updateAssignment: (assignmentId: number, data: Partial<{
    title: string; content: string; images: string[]; due_at: string | null
  }>): Promise<Assignment> =>
    axios.put(`/teacher/assignments/${assignmentId}`, data),
  uploadAssignmentImage: (file: File): Promise<{ image_path: string; image_url: string }> => {
    const formData = new FormData()
    formData.append('file', file)
    return axios.post('/teacher/assignments/upload-image', formData)
  },
  deleteAssignment: (assignmentId: number): Promise<{ message: string }> =>
    axios.delete(`/teacher/assignments/${assignmentId}`),
  listSubmissions: (assignmentId: number): Promise<Submission[]> =>
    axios.get(`/teacher/assignments/${assignmentId}/submissions`),
  gradeSubmission: (assignmentId: number, data: {
    student_id: number; score: number; feedback?: string
  }): Promise<Submission> =>
    axios.post(`/teacher/assignments/${assignmentId}/grade`, data),
}

// ---------- 机构管理者 ----------
export const institutionApi = {
  classes: (institutionId?: number): Promise<ClassSummary[]> =>
    axios.get('/institution/classes', { params: { institution_id: institutionId } }),
  classStudents: (classId: number): Promise<StudentSummary[]> =>
    axios.get(`/institution/classes/${classId}/students`),
  classTeachers: (classId: number): Promise<TeacherBrief[]> =>
    axios.get(`/institution/classes/${classId}/teachers`),
  studentOverview: (studentId: number): Promise<StudentOverview> =>
    axios.get(`/institution/students/${studentId}/overview`),
  studentMistakes: (studentId: number, subject?: string): Promise<MistakeItem[]> =>
    axios.get(`/institution/students/${studentId}/mistakes`, { params: { subject } }),
  studentMistakeDetail: (studentId: number, mistakeId: number): Promise<MistakeItem> =>
    axios.get(`/institution/students/${studentId}/mistakes/${mistakeId}`),
  // 写操作
  createClass: (data: {
    name: string
    institution_id?: number
    code_expires_at?: string | null
    code_max_uses?: number | null
  }): Promise<ClassDetail> => axios.post('/institution/classes', data),
  updateClass: (classId: number, data: ClassSettingsPayload): Promise<ClassDetail> =>
    axios.patch(`/institution/classes/${classId}`, data),
  resetCode: (classId: number): Promise<ClassDetail> =>
    axios.post(`/institution/classes/${classId}/reset-code`),
  listTeachers: (institutionId?: number): Promise<StaffUser[]> =>
    axios.get('/institution/teachers', { params: { institution_id: institutionId } }),
  createTeacher: (data: {
    username: string; email: string; password: string
  }): Promise<StaffUser> => axios.post('/institution/teachers', data),
  updateTeacher: (teacherId: number, data: {
    username?: string; email?: string; password?: string
  }): Promise<StaffUser> => axios.put(`/institution/teachers/${teacherId}`, data),
  deleteTeacher: (teacherId: number): Promise<{ message: string }> =>
    axios.delete(`/institution/teachers/${teacherId}`),
  assignTeacher: (classId: number, teacherId: number): Promise<{ message: string }> =>
    axios.post(`/institution/classes/${classId}/teachers`, { teacher_id: teacherId }),
  unassignTeacher: (classId: number, teacherId: number): Promise<{ message: string }> =>
    axios.delete(`/institution/classes/${classId}/teachers/${teacherId}`),
}

// ---------- 学生（班级成员视角，任意角色均可） ----------
export const studentClassApi = {
  join: (code: string): Promise<MyClass> => axios.post('/classes/join', { code }),
  my: (): Promise<MyClass[]> => axios.get('/classes/my'),
  announcements: (classId: number): Promise<Announcement[]> =>
    axios.get(`/classes/${classId}/announcements`),
  assignments: (classId: number): Promise<Assignment[]> =>
    axios.get(`/classes/${classId}/assignments`),
  assignment: (assignmentId: number): Promise<Assignment> =>
    axios.get(`/classes/assignments/${assignmentId}`),
  submit: (assignmentId: number, content: string): Promise<Submission> =>
    axios.post(`/classes/assignments/${assignmentId}/submissions`, { content }),
}
