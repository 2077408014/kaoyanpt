import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useUserStore, roleHomePath } from '../stores/user'
import { getMe } from '../api/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/login'
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { public: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/Register.vue'),
    meta: { public: true }
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: () => import('../views/ForgotPassword.vue'),
    meta: { public: true }
  },
  {
    path: '/dashboard',
    component: () => import('../views/Dashboard.vue'),
    meta: { roles: ['student', 'teacher', 'institution_admin', 'super_admin'] },
    children: [
      {
        path: '',
        name: 'Home',
        component: () => import('../views/Home.vue')
      },
      {
        path: 'mistakes',
        name: 'Mistakes',
        component: () => import('../views/Mistakes.vue')
      },
      {
        path: 'recommend',
        name: 'Recommend',
        component: () => import('../views/Recommend.vue')
      },
      {
        path: 'resources',
        name: 'Resources',
        component: () => import('../views/Resources.vue')
      },
      {
        path: 'words',
        name: 'Words',
        component: () => import('../views/Words.vue')
      },
      {
        path: 'ai',
        name: 'AI',
        component: () => import('../views/AIChat.vue')
      },
      {
        path: 'ai-config',
        name: 'AIConfig',
        component: () => import('../views/AIConfig.vue')
      },
      {
        path: 'supervision',
        name: 'Supervision',
        component: () => import('../views/StudySupervision.vue')
      },
      {
        path: 'my-classes',
        name: 'MyClasses',
        component: () => import('../views/student/ClassJoin.vue')
      },
      {
        path: 'classes/:classId',
        name: 'StudentClassDetail',
        component: () => import('../views/student/ClassDetail.vue')
      }
    ]
  },
  {
    path: '/teacher',
    component: () => import('../views/teacher/TeacherLayout.vue'),
    meta: { roles: ['teacher', 'super_admin'] },
    children: [
      { path: '', name: 'TeacherHome', component: () => import('../views/teacher/ClassList.vue') },
      { path: 'classes/:classId', name: 'TeacherClassDetail', component: () => import('../views/teacher/ClassDetail.vue') },
      { path: 'assignments/:assignmentId', name: 'TeacherAssignmentDetail', component: () => import('../views/teacher/AssignmentDetail.vue') },
      { path: 'students/:studentId', name: 'TeacherStudentDetail', component: () => import('../views/teacher/StudentDetail.vue') },
    ]
  },
  {
    path: '/institution',
    component: () => import('../views/institution/InstitutionLayout.vue'),
    meta: { roles: ['institution_admin', 'super_admin'] },
    children: [
      { path: '', name: 'InstitutionHome', component: () => import('../views/institution/ClassOverview.vue') },
      { path: 'manage-classes', name: 'InstitutionManageClasses', component: () => import('../views/institution/ManageClasses.vue') },
      { path: 'teachers', name: 'InstitutionTeachers', component: () => import('../views/institution/Teachers.vue') },
      { path: 'classes/:classId', name: 'InstitutionClassDetail', component: () => import('../views/institution/ClassDetail.vue') },
      { path: 'students/:studentId', name: 'InstitutionStudentDetail', component: () => import('../views/institution/StudentDetail.vue') },
    ]
  },
  {
    path: '/admin',
    component: () => import('../views/admin/AdminLayout.vue'),
    meta: { roles: ['super_admin'] },
    children: [
      { path: '', redirect: '/admin/institutions' },
      { path: 'institutions', name: 'AdminInstitutions', component: () => import('../views/admin/Institutions.vue') },
      { path: 'users', name: 'AdminUsers', component: () => import('../views/admin/Users.vue') },
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to) => {
  if (to.meta.public) {
    return true
  }

  const userStore = useUserStore()

  if (!userStore.token) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  // 兼容旧会话：本地无角色信息时先拉取 /me
  if (!userStore.role) {
    try {
      const me = await getMe()
      userStore.setUser(me)
    } catch {
      userStore.logout()
      return { path: '/login' }
    }
  }

  const allowed = to.meta.roles as string[] | undefined
  if (allowed && !allowed.includes(userStore.role as string)) {
    return { path: roleHomePath(userStore.role as string) }
  }
  return true
})

export default router
