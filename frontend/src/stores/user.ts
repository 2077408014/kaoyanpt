import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { User, UserRole } from '../api/auth'

export function roleHomePath(role?: string): string {
  switch (role) {
    case 'teacher': return '/teacher'
    case 'institution_admin': return '/institution'
    case 'super_admin': return '/admin'
    default: return '/dashboard'
  }
}

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref<User | null>(null)
  const role = ref<UserRole | ''>(localStorage.getItem('role') as UserRole | '' || '')
  const mustChangePassword = ref(localStorage.getItem('must_change_password') === '1')

  function setToken(newToken: string) {
    token.value = newToken
    localStorage.setItem('token', newToken)
  }

  function setUser(newUser: User) {
    user.value = newUser
    role.value = newUser.role || 'student'
    mustChangePassword.value = !!newUser.must_change_password
    localStorage.setItem('role', newUser.role || 'student')
    localStorage.setItem('must_change_password', newUser.must_change_password ? '1' : '0')
  }

  function clearMustChangePassword() {
    mustChangePassword.value = false
    localStorage.setItem('must_change_password', '0')
    if (user.value) user.value.must_change_password = false
  }

  function logout() {
    token.value = ''
    user.value = null
    role.value = ''
    mustChangePassword.value = false
    localStorage.removeItem('token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('role')
    localStorage.removeItem('must_change_password')
  }

  return {
    token, user, role, mustChangePassword,
    setToken, setUser, clearMustChangePassword, logout,
  }
})
