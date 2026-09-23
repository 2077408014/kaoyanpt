import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, type RouteLocationNormalized } from 'vue-router'
import { sendHeartbeat, trackStudyEvent, type StudyEventType } from '../api/study_tracker'

/**
 * 学习时长心跳 composable（独立模块）
 *
 * - 用户在「学习相关页面」停留时，每 HEARTBEAT_INTERVAL 秒发送一次心跳
 * - 切到非学习页面或离开应用时，立即发送累计时长
 * - 暴露 trackEvent 供业务页调用，记录事件计数
 *
 * 使用：在 Dashboard.vue 中 const { trackEvent } = useStudyHeartbeat()
 */

const HEARTBEAT_INTERVAL = 30 // 每 30 秒发送一次心跳

// 学习相关路径：错题/推荐/单词/AI/资料/报告/监督
const STUDY_PATHS = [
  '/dashboard/mistakes',
  '/dashboard/recommend',
  '/dashboard/words',
  '/dashboard/ai',
  '/dashboard/resources',
  '/dashboard/report',
  '/dashboard/supervision',
]

function isStudyPath(path: string): boolean {
  return STUDY_PATHS.some(p => path === p || path.startsWith(p + '/'))
}

export function useStudyHeartbeat() {
  const route = useRoute()
  const isStudying = ref(false)
  const lastTickAt = ref<number>(0)
  const accumulatedSeconds = ref(0)

  let timer: number | null = null
  let stopWatch: (() => void) | null = null

  function resetAccumulator() {
    accumulatedSeconds.value = 0
    lastTickAt.value = Date.now()
  }

  async function flushHeartbeat(force = false) {
    const now = Date.now()
    const elapsed = Math.floor((now - lastTickAt.value) / 1000)
    lastTickAt.value = now

    if (elapsed <= 0) return
    if (!force && elapsed < HEARTBEAT_INTERVAL) {
      accumulatedSeconds.value += elapsed
      return
    }

    const total = accumulatedSeconds.value + elapsed
    accumulatedSeconds.value = 0
    const seconds = Math.min(total, 30 * 60)
    if (seconds <= 0) return

    try {
      await sendHeartbeat(seconds)
    } catch {
      // 网络失败不抛错，下次重试
    }
  }

  function startTicking() {
    if (isStudying.value) return
    isStudying.value = true
    lastTickAt.value = Date.now()
    accumulatedSeconds.value = 0
    timer = window.setInterval(() => {
      flushHeartbeat(false).catch(() => {})
    }, HEARTBEAT_INTERVAL * 1000)
  }

  function stopTicking() {
    if (!isStudying.value) return
    isStudying.value = false
    if (timer !== null) {
      clearInterval(timer)
      timer = null
    }
    flushHeartbeat(true).catch(() => {})
  }

  function onVisibilityChange() {
    if (document.hidden) {
      stopTicking()
    } else if (isStudyPath(route.path)) {
      lastTickAt.value = Date.now()
      startTicking()
    }
  }

  function onBeforeUnload() {
    if (!isStudying.value) return
    const now = Date.now()
    const elapsed = Math.floor((now - lastTickAt.value) / 1000)
    const total = accumulatedSeconds.value + elapsed
    const seconds = Math.min(total, 30 * 60)
    if (seconds <= 0) return
    // 使用 fetch + keepalive，页面卸载时仍可发出请求
    try {
      const token = localStorage.getItem('token') || ''
      fetch('/api/study/heartbeat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ seconds }),
        keepalive: true,
      }).catch(() => {})
    } catch {
      // ignore
    }
  }

  async function trackEvent(eventType: StudyEventType, count: number = 1) {
    try {
      await trackStudyEvent(eventType, count)
    } catch {
      // ignore
    }
  }

  function handleRouteChange(to: RouteLocationNormalized) {
    const path = to.path
    if (isStudyPath(path)) {
      if (!isStudying.value) {
        resetAccumulator()
        startTicking()
      }
    } else {
      if (isStudying.value) {
        stopTicking()
      }
    }
  }

  onMounted(() => {
    document.addEventListener('visibilitychange', onVisibilityChange)
    window.addEventListener('beforeunload', onBeforeUnload)

    // 初始化时根据当前路径决定是否开始计时
    handleRouteChange(route)

    // 监听路由变化
    stopWatch = watch(
      () => route.path,
      () => handleRouteChange(route),
    )
  })

  onUnmounted(() => {
    stopTicking()
    document.removeEventListener('visibilitychange', onVisibilityChange)
    window.removeEventListener('beforeunload', onBeforeUnload)
    if (stopWatch) {
      stopWatch()
      stopWatch = null
    }
  })

  return {
    isStudying,
    trackEvent,
  }
}
