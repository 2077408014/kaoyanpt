import axios from 'axios'
import router from '../router'
import { useUserStore } from '../stores/user'
import { trackStudyEvent, type StudyEventType } from './study_tracker'

function trackStudyEventAuto(eventType: StudyEventType) {
  trackStudyEvent(eventType).catch(() => {})
}

const instance = axios.create({
  baseURL: '/api',
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json'
  }
})

let isRefreshing = false
let failedQueue: Array<{ resolve: (token: string) => void; reject: (error: any) => void }> = []

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach(prom => {
    if (token) {
      prom.resolve(token)
    } else {
      prom.reject(error)
    }
  })
  failedQueue = []
}

const refreshToken = async () => {
  const refreshToken = localStorage.getItem('refresh_token')
  if (!refreshToken) {
    throw new Error('No refresh token available')
  }
  
  const response = await axios.post('/api/auth/refresh', {
    refresh_token: refreshToken
  })
  
  return response.data
}

instance.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  
  if (config.data instanceof FormData) {
    delete config.headers['Content-Type']
  }
  
  return config
}, (error) => {
  return Promise.reject(error)
})

instance.interceptors.response.use(
  (response) => {
    // 自动跟踪学习事件（独立模块：无需修改业务文件）
    try {
      const url: string = response.config?.url || ''
      const method: string = (response.config?.method || 'get').toLowerCase()
      if (method === 'post' && response.status >= 200 && response.status < 300) {
        if (url.includes('/mistakes') && !url.includes('/review') && !url.includes('/recognize')) {
          trackStudyEventAuto('mistake_added')
        } else if (url.endsWith('/words/study') || url === '/words/study') {
          trackStudyEventAuto('word_learned')
        } else if (/\/recommend\/\d+\/complete/.test(url)) {
          trackStudyEventAuto('question_completed')
        }
      }
    } catch {
      // ignore
    }
    return response.data
  },
  async (error) => {
    const originalRequest = error.config
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return axios(originalRequest)
        }).catch((err) => {
          return Promise.reject(err)
        })
      }
      
      originalRequest._retry = true
      isRefreshing = true
      
      try {
        const result = await refreshToken()
        const newAccessToken = result.access_token
        const newRefreshToken = result.refresh_token
        
        localStorage.setItem('token', newAccessToken)
        localStorage.setItem('refresh_token', newRefreshToken)
        
        const store = useUserStore()
        store.setToken(newAccessToken)
        
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
        processQueue(null, newAccessToken)
        
        return axios(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError, null)
        
        try {
          const store = useUserStore()
          store.logout()
        } catch (e) {
          console.error('Failed to clear user store:', e)
        }
        
        localStorage.removeItem('token')
        localStorage.removeItem('refresh_token')
        router.push('/login')
        
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }
    
    if (error.response) {
      const { status, data } = error.response
      console.error(`HTTP Error ${status}:`, data)
      
      if (status === 403) {
        console.error('Forbidden access - CSRF or permission issue')
      } else if (status === 422) {
        console.error('Validation error:', data)
      }
    } else if (error.request) {
      console.error('Network error - no response received:', error.request)
    } else {
      console.error('Request setup error:', error.message)
    }
    
    return Promise.reject(error)
  }
)

export default instance