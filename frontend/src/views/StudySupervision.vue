<template>
  <div class="study-supervision">
    <h2 class="page-title">学习图像监督</h2>

    <div class="camera-section">
      <div class="camera-card">
        <video
          ref="videoRef"
          class="camera-video"
          autoplay
          playsinline
          muted
        />
        <img
          v-if="overlayImage"
          :src="overlayImage"
          class="camera-overlay"
          alt="overlay"
        />
        <div v-if="!isRunning && !hasPermission" class="camera-placeholder">
          <el-icon :size="48"><VideoCamera /></el-icon>
          <p>点击「开始监督」启用摄像头</p>
        </div>
        <div v-if="isRunning" class="status-overlay">
          <el-tag :type="statusTagType" size="large" effect="dark">
            {{ statusLabel }}
          </el-tag>
        </div>
      </div>
    </div>

    <div class="stats-row">
      <div class="stat-card">
        <p class="stat-value">{{ statusLabel }}</p>
        <p class="stat-label">当前状态</p>
      </div>
      <div class="stat-card">
        <p class="stat-value">{{ formatDuration(duration) }}</p>
        <p class="stat-label">本次时长</p>
      </div>
      <div class="stat-card">
        <p class="stat-value">{{ faceCount }}</p>
        <p class="stat-label">人脸数</p>
      </div>
      <div class="stat-card">
        <p class="stat-value">{{ checkCount }}</p>
        <p class="stat-label">检测次数</p>
      </div>
    </div>

    <div class="control-section">
      <el-button
        v-if="!isRunning"
        type="primary"
        size="large"
        :loading="starting"
        @click="startSupervision"
      >
        <el-icon><VideoCamera /></el-icon>
        开始监督
      </el-button>
      <el-button
        v-else
        type="danger"
        size="large"
        @click="stopSupervision"
      >
        <el-icon><CircleClose /></el-icon>
        结束监督
      </el-button>
    </div>

    <div v-if="sessionStats" class="chart-section">
      <h3>本次会话统计</h3>
      <div ref="chartRef" class="chart-container" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { VideoCamera, CircleClose } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import {
  startSupervisionSession,
  checkSupervision,
  getSupervisionSessionStats,
  type SupervisionSessionStats,
} from '../api/supervision'

const videoRef = ref<HTMLVideoElement | null>(null)
const chartRef = ref<HTMLDivElement | null>(null)

const isRunning = ref(false)
const starting = ref(false)
const hasPermission = ref(false)
const sessionId = ref('')
const currentStatus = ref('unknown')
const faceCount = ref(0)
const confidence = ref(0)
const checkCount = ref(0)
const duration = ref(0)
const sessionStats = ref<SupervisionSessionStats | null>(null)
const overlayImage = ref<string | null>(null)

let stream: MediaStream | null = null
let timer: number | null = null
let durationTimer: number | null = null
let chartInstance: echarts.ECharts | null = null

const statusLabel = computed(() => {
  const map: Record<string, string> = {
    focused: '专注',
    distracted: '走神',
    absent: '离开',
    unknown: '未知',
  }
  return map[currentStatus.value] || '未知'
})

const statusTagType = computed(() => {
  const map: Record<string, string> = {
    focused: 'success',
    distracted: 'warning',
    absent: 'info',
    unknown: 'danger',
  }
  return map[currentStatus.value] || 'danger'
})

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

async function startSupervision() {
  starting.value = true
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480, facingMode: 'user' },
      audio: false,
    })

    if (videoRef.value) {
      videoRef.value.srcObject = stream
      hasPermission.value = true
    }

    const session = await startSupervisionSession()
    sessionId.value = session.session_id
    isRunning.value = true
    currentStatus.value = 'unknown'
    faceCount.value = 0
    checkCount.value = 0
    duration.value = 0
    sessionStats.value = null

    // 每15秒检测一次
    timer = window.setInterval(captureAndCheck, 15000)
    // 首次立即检测
    setTimeout(captureAndCheck, 2000)

    // 计时器
    durationTimer = window.setInterval(() => {
      duration.value++
    }, 1000)

    ElMessage.success('监督已启动')
  } catch (err: any) {
    if (stream) {
      stream.getTracks().forEach(track => track.stop())
      stream = null
    }
    if (videoRef.value) {
      videoRef.value.srcObject = null
    }
    hasPermission.value = false

    let msg = ''
    if (err.name === 'NotAllowedError') {
      msg = '摄像头权限被拒绝，请在浏览器设置中允许访问摄像头'
    } else if (err.message && err.message.includes('Network')) {
      msg = '网络连接失败，请检查网络或稍后重试'
    } else if (err.response?.status === 401) {
      msg = '登录已过期，请重新登录'
    } else {
      msg = '启动失败：' + (err.message || '未知错误')
    }
    ElMessage.error(msg)
  } finally {
    starting.value = false
  }
}

async function captureAndCheck() {
  if (!videoRef.value || !sessionId.value) return

  const video = videoRef.value
  const canvas = document.createElement('canvas')
  const maxWidth = 640
  const scale = Math.min(1, maxWidth / video.videoWidth)
  canvas.width = video.videoWidth * scale
  canvas.height = video.videoHeight * scale

  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height)

  const base64 = canvas.toDataURL('image/jpeg', 0.7)

  try {
    const result = await checkSupervision({
      image_base64: base64,
      session_id: sessionId.value,
    })
    currentStatus.value = result.status
    faceCount.value = result.face_count
    confidence.value = result.confidence
    checkCount.value++
    if (result.overlay_base64) {
      overlayImage.value = 'data:image/jpeg;base64,' + result.overlay_base64
    }
  } catch {
    // 网络错误不中断监督
  }
}

async function stopSupervision() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
  if (durationTimer) {
    clearInterval(durationTimer)
    durationTimer = null
  }

  if (stream) {
    stream.getTracks().forEach(track => track.stop())
    stream = null
  }

  if (videoRef.value) {
    videoRef.value.srcObject = null
  }

  isRunning.value = false
  hasPermission.value = false
  overlayImage.value = null

  if (sessionId.value) {
    try {
      const stats = await getSupervisionSessionStats(sessionId.value)
      sessionStats.value = stats
      await nextTick()
      renderChart(stats)
    } catch {
      // 忽略统计错误
    }
  }

  ElMessage.success('监督已结束')
}

function renderChart(stats: SupervisionSessionStats) {
  if (!chartRef.value) return
  if (chartInstance) {
    chartInstance.dispose()
  }

  chartInstance = echarts.init(chartRef.value)
  chartInstance.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: '0%' },
    series: [
      {
        name: '专注状态',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2,
        },
        label: { show: true, formatter: '{b}: {c}次 ({d}%)' },
        data: [
          { value: stats.focused_count, name: '专注', itemStyle: { color: '#67c23a' } },
          { value: stats.distracted_count, name: '走神', itemStyle: { color: '#e6a23c' } },
          { value: stats.absent_count, name: '离开', itemStyle: { color: '#909399' } },
          { value: stats.unknown_count, name: '未知', itemStyle: { color: '#f56c6c' } },
        ],
      },
    ],
  })
}

onMounted(() => {
  window.addEventListener('resize', () => {
    chartInstance?.resize()
  })
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  if (durationTimer) clearInterval(durationTimer)
  if (stream) {
    stream.getTracks().forEach(track => track.stop())
  }
  if (chartInstance) {
    chartInstance.dispose()
  }
})
</script>

<style scoped>
.study-supervision {
  padding: 20px;
}

.page-title {
  font-size: 24px;
  font-weight: bold;
  margin: 0 0 20px;
  color: #333;
}

.camera-section {
  display: flex;
  justify-content: center;
  margin-bottom: 20px;
}

.camera-card {
  position: relative;
  width: 640px;
  max-width: 100%;
  aspect-ratio: 4 / 3;
  background: #1a1a2e;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
}

.camera-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.camera-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0.85;
  pointer-events: none;
}

.camera-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #888;
  gap: 12px;
}

.status-overlay {
  position: absolute;
  top: 16px;
  right: 16px;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  background: #f5f7fa;
  padding: 20px;
  border-radius: 12px;
  text-align: center;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  margin: 0 0 8px;
  color: #333;
}

.stat-label {
  font-size: 14px;
  color: #999;
  margin: 0;
}

.control-section {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-bottom: 24px;
}

.chart-section {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.chart-section h3 {
  margin: 0 0 16px;
  font-size: 18px;
  color: #333;
}

.chart-container {
  width: 100%;
  height: 320px;
}
</style>
