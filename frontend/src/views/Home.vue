<template>
  <div class="home">
    <div class="page-header">
      <h2>学习报告</h2>
      <el-radio-group v-model="period" @change="loadReport">
        <el-radio-button label="day">今日</el-radio-button>
        <el-radio-button label="week">本周</el-radio-button>
        <el-radio-button label="month">本月</el-radio-button>
      </el-radio-group>
    </div>
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon word-icon">
          <el-icon><Document /></el-icon>
        </div>
        <div class="stat-info">
          <p class="stat-value">{{ report.word_stats.total_words }}</p>
          <p class="stat-label">已学单词</p>
        </div>
        <p class="stat-rate">掌握率 {{ report.word_stats.mastery_rate }}%</p>
      </div>
      <div class="stat-card">
        <div class="stat-icon mistake-icon">
          <el-icon><Warning /></el-icon>
        </div>
        <div class="stat-info">
          <p class="stat-value">{{ report.mistake_stats.total_mistakes }}</p>
          <p class="stat-label">错题总数</p>
        </div>
        <p class="stat-rate">掌握率 {{ report.mistake_stats.mastery_rate }}%</p>
      </div>
      <div class="stat-card">
        <div class="stat-icon rec-icon">
          <el-icon><DataAnalysis /></el-icon>
        </div>
        <div class="stat-info">
          <p class="stat-value">{{ report.recommendation_stats.completed_this_period }}</p>
          <p class="stat-label">本期完成推荐</p>
        </div>
        <p class="stat-rate">正确率 {{ report.recommendation_stats.success_rate }}%</p>
      </div>
      <div class="stat-card">
        <div class="stat-icon time-icon">
          <el-icon><Clock /></el-icon>
        </div>
        <div class="stat-info">
          <p class="stat-value">{{ report.overall_stats.avg_daily_time }}</p>
          <p class="stat-label">日均学习(分钟)</p>
        </div>
        <p class="stat-rate">累计 {{ report.overall_stats.total_study_days }} 天</p>
      </div>
    </div>
    <div class="quick-actions">
      <h3>快捷操作</h3>
      <div class="action-buttons">
        <el-button type="primary" @click="$router.push('/dashboard/mistakes')">
          <el-icon><Plus /></el-icon>
          添加错题
        </el-button>
        <el-button type="success" @click="$router.push('/dashboard/mistakes')">
          <el-icon><Refresh /></el-icon>
          开始复习
        </el-button>
        <el-button type="warning" @click="$router.push('/dashboard/words')">
          <el-icon><Notebook /></el-icon>
          学习单词
        </el-button>
        <el-button type="info" @click="$router.push('/dashboard/ai')">
          <el-icon><Message /></el-icon>
          AI问答
        </el-button>
      </div>
    </div>

    <div class="agent-section">
      <div class="section-header">
        <h3>智能体状态</h3>
        <el-tag v-if="agents.length > 0" type="info" effect="plain">
          {{ agents.filter(a => a.enabled).length }} / {{ agents.length }} 启用中
        </el-tag>
      </div>
      <div v-if="agents.length > 0" class="agents-grid">
        <el-card
          v-for="agent in agents"
          :key="agent.name"
          class="agent-card"
          :class="{ 'agent-disabled': !agent.enabled }"
        >
          <div class="agent-header">
            <div class="agent-info">
              <div class="agent-name">{{ agent.domain }}</div>
              <div class="agent-desc">{{ agent.description }}</div>
            </div>
            <el-switch
              v-model="agent.enabled"
              @change="handleToggleAgent(agent.name, agent.enabled)"
              :disabled="agentLoading"
            />
          </div>
          <div class="agent-keywords">
            <el-tag v-for="kw in agent.keywords.slice(0, 3)" :key="kw" size="small" type="info" effect="plain">{{ kw }}</el-tag>
            <span v-if="agent.keywords.length > 3" class="more-keywords">+{{ agent.keywords.length - 3 }}</span>
          </div>
        </el-card>
      </div>
      <div v-else class="empty-tip">
        <el-icon><InfoFilled /></el-icon>暂无智能体信息
      </div>
    </div>

    <div class="overview-section">
      <div class="overview-card">
        <h3>本周学习趋势</h3>
        <div ref="trendChart" class="chart-container"></div>
      </div>
      <div class="overview-card">
        <h3>错题科目分布</h3>
        <div v-if="mistakeBySubject.length > 0" ref="subjectChart" class="subject-chart-container"></div>
        <div v-else class="empty-text">暂无错题数据</div>
      </div>
    </div>
    <div class="recent-section">
      <h3>最近添加的错题</h3>
      <el-table :data="recentMistakes" border>
        <el-table-column prop="subject" label="科目" width="100" />
        <el-table-column prop="knowledge_point" label="知识点" />
        <el-table-column prop="difficulty" label="难度" width="80" />
        <el-table-column prop="mastery_level" label="掌握程度" width="100" />
        <el-table-column prop="created_at" label="添加时间" width="180" />
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, computed, watch } from 'vue'
import { Clock, Plus, Refresh, Notebook, Message, Document, Warning, DataAnalysis, InfoFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getMistakes } from '../api/mistakes'
import { getWeeklyTrend, getStudyReport, type DailyStats, type StudyReport } from '../api/report'
import { getAgentStatus, toggleAgent, type AgentInfo } from '../api/recommendation'

const period = ref('week')
const report = ref<StudyReport>({
  period: 'week',
  start_date: '',
  end_date: '',
  word_stats: { total_words: 0, mastered_count: 0, learned_this_period: 0, today_review: 0, mastery_rate: 0 },
  mistake_stats: { total_mistakes: 0, added_this_period: 0, mastered_mistakes: 0, today_review: 0, mastery_rate: 0, by_subject: [] },
  recommendation_stats: { total_recommendations: 0, completed_this_period: 0, total_completed: 0, completion_rate: 0, success_rate: 0 },
  overall_stats: { total_study_days: 0, avg_daily_time: 0 }
})
const recentMistakes = ref<any[]>([])
const trendChart = ref<HTMLElement | null>(null)
const subjectChart = ref<HTMLElement | null>(null)
const weeklyTrend = ref<DailyStats[]>([])
const agents = ref<AgentInfo[]>([])
const agentLoading = ref(false)

const mistakeBySubject = computed(() => {
  return report.value.mistake_stats.by_subject
})

async function loadReport() {
  try {
    const [reportData, trendData] = await Promise.all([
      getStudyReport(period.value),
      getWeeklyTrend()
    ])
    report.value = reportData
    weeklyTrend.value = trendData
    await nextTick()
    renderChart()
    renderSubjectChart()
  } catch {
    // ignore
  }
}

async function loadAgents() {
  try {
    const agentData = await getAgentStatus()
    agents.value = agentData.agents
  } catch {
    agents.value = []
  }
}

async function handleToggleAgent(agentName: string, enabled: boolean) {
  agentLoading.value = true
  try {
    const result = await toggleAgent(agentName, enabled)
    ElMessage.success(result.message)
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
    const idx = agents.value.findIndex(a => a.name === agentName)
    if (idx !== -1) {
      agents.value[idx].enabled = !enabled
    }
  } finally {
    agentLoading.value = false
  }
}

onMounted(async () => {
  try {
    const mistakes = await getMistakes()
    recentMistakes.value = mistakes.slice(0, 5)

    await loadReport()
    await loadAgents()
  } catch {
    // ignore
  }
  window.addEventListener('resize', handleResize)
})

watch(period, () => {
  loadReport()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})

let resizeTimer: number | null = null
function handleResize() {
  if (resizeTimer !== null) {
    clearTimeout(resizeTimer)
  }
  resizeTimer = window.setTimeout(() => {
    renderChart()
    renderSubjectChart()
  }, 200)
}

function niceMax(value: number): number {
  if (value <= 0) return 60
  const magnitude = Math.pow(10, Math.floor(Math.log10(value)))
  const norm = value / magnitude
  let nice
  if (norm <= 1) nice = 1
  else if (norm <= 2) nice = 2
  else if (norm <= 5) nice = 5
  else nice = 10
  return nice * magnitude
}

function renderChart() {
  try {
    if (!trendChart.value) return
    const trend = weeklyTrend.value
    if (trend.length === 0) return

    const labels = trend.map(t => t.date.slice(5))
    const data = trend.map(t => Math.round(t.total_time / 60))

    const canvas = document.createElement('canvas')
    trendChart.value.innerHTML = ''
    trendChart.value.appendChild(canvas)

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    const cssWidth = trendChart.value.clientWidth
    const cssHeight = 220
    canvas.width = cssWidth * dpr
    canvas.height = cssHeight * dpr
    canvas.style.width = cssWidth + 'px'
    canvas.style.height = cssHeight + 'px'
    ctx.scale(dpr, dpr)

    const W = cssWidth
    const H = cssHeight
    const paddingLeft = 50
    const paddingRight = 16
    const paddingTop = 20
    const paddingBottom = 36
    const chartW = W - paddingLeft - paddingRight
    const chartH = H - paddingTop - paddingBottom

    ctx.fillStyle = '#fafbfc'
    ctx.fillRect(0, 0, W, H)

    const rawMax = Math.max(...data, 0)
    const maxValue = niceMax(rawMax)
    const stepX = labels.length > 1 ? chartW / (labels.length - 1) : chartW

    ctx.strokeStyle = '#e5e7eb'
    ctx.lineWidth = 1
    ctx.fillStyle = '#9ca3af'
    ctx.font = '12px Arial'
    ctx.textAlign = 'right'
    ctx.textBaseline = 'middle'
    const ySteps = 4
    for (let i = 0; i <= ySteps; i++) {
      const y = paddingTop + (chartH * i) / ySteps
      ctx.beginPath()
      ctx.moveTo(paddingLeft, y)
      ctx.lineTo(paddingLeft + chartW, y)
      ctx.stroke()
      const v = Math.round(maxValue * (1 - i / ySteps))
      ctx.fillText(v + ' 分', paddingLeft - 8, y)
    }

    const points: Array<{ x: number; y: number; v: number }> = []
    for (let i = 0; i < labels.length; i++) {
      const x = paddingLeft + i * stepX
      const ratio = maxValue > 0 ? data[i] / maxValue : 0
      const y = paddingTop + chartH * (1 - ratio)
      points.push({ x, y, v: data[i] })
    }

    if (points.length > 0) {
      const grad = ctx.createLinearGradient(0, paddingTop, 0, paddingTop + chartH)
      grad.addColorStop(0, 'rgba(102, 126, 234, 0.35)')
      grad.addColorStop(1, 'rgba(118, 75, 162, 0.02)')
      ctx.fillStyle = grad
      ctx.beginPath()
      ctx.moveTo(points[0].x, paddingTop + chartH)
      for (const p of points) {
        ctx.lineTo(p.x, p.y)
      }
      ctx.lineTo(points[points.length - 1].x, paddingTop + chartH)
      ctx.closePath()
      ctx.fill()
    }

    if (points.length > 1) {
      ctx.strokeStyle = '#667eea'
      ctx.lineWidth = 2.5
      ctx.lineJoin = 'round'
      ctx.lineCap = 'round'
      ctx.beginPath()
      ctx.moveTo(points[0].x, points[0].y)
      for (let i = 1; i < points.length; i++) {
        ctx.lineTo(points[i].x, points[i].y)
      }
      ctx.stroke()
    }

    for (const p of points) {
      ctx.fillStyle = '#fff'
      ctx.strokeStyle = '#667eea'
      ctx.lineWidth = 2
      ctx.beginPath()
      ctx.arc(p.x, p.y, 4, 0, Math.PI * 2)
      ctx.fill()
      ctx.stroke()

      if (p.v > 0) {
        ctx.fillStyle = '#374151'
        ctx.font = '11px Arial'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'bottom'
        ctx.fillText(String(p.v), p.x, p.y - 8)
      }
    }

    ctx.fillStyle = '#6b7280'
    ctx.font = '12px Arial'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'top'
    for (let i = 0; i < labels.length; i++) {
      const x = paddingLeft + i * stepX
      ctx.fillText(labels[i], x, paddingTop + chartH + 10)
    }
  } catch {
    // ignore
  }
}

function renderSubjectChart() {
  try {
    if (!subjectChart.value) return
    const data = mistakeBySubject.value
    if (data.length === 0) return

    const canvas = document.createElement('canvas')
    subjectChart.value.innerHTML = ''
    subjectChart.value.appendChild(canvas)

    const containerWidth = subjectChart.value.clientWidth || 300
    const containerHeight = 200

    const dpr = window.devicePixelRatio || 1
    canvas.width = containerWidth * dpr
    canvas.height = containerHeight * dpr
    canvas.style.width = containerWidth + 'px'
    canvas.style.height = containerHeight + 'px'

    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.scale(dpr, dpr)

    const W = containerWidth
    const H = containerHeight
    const paddingLeft = 60
    const paddingRight = 20
    const paddingTop = 20
    const paddingBottom = 30
    const chartW = W - paddingLeft - paddingRight
    const chartH = H - paddingTop - paddingBottom

    ctx.fillStyle = '#fafbfc'
    ctx.fillRect(0, 0, W, H)

    const maxCount = Math.max(...data.map(d => d.count), 1)
    const barCount = data.length
    const barWidth = Math.min(40, (chartW - (barCount - 1) * 8) / barCount)
    const totalBarSpace = barCount * barWidth + (barCount - 1) * 8
    const startX = paddingLeft + (chartW - totalBarSpace) / 2

    const colors = [
      '#667eea', '#764ba2', '#f093fb', '#f5576c',
      '#4facfe', '#00f2fe', '#43e97b', '#38f9d7',
      '#fa709a', '#fee140'
    ]

    ctx.strokeStyle = '#e5e7eb'
    ctx.lineWidth = 1
    ctx.fillStyle = '#9ca3af'
    ctx.font = '11px Arial'
    ctx.textAlign = 'right'
    ctx.textBaseline = 'middle'
    
    const ySteps = 3
    for (let i = 0; i <= ySteps; i++) {
      const y = paddingTop + (chartH * i) / ySteps
      ctx.beginPath()
      ctx.moveTo(paddingLeft, y)
      ctx.lineTo(paddingLeft + chartW, y)
      ctx.stroke()
      const v = Math.round(maxCount * (1 - i / ySteps))
      ctx.fillText(String(v), paddingLeft - 8, y)
    }

    data.forEach((item, i) => {
      const x = startX + i * (barWidth + 8)
      const ratio = maxCount > 0 ? item.count / maxCount : 0
      const barH = chartH * ratio
      const y = paddingTop + chartH - barH

      const color = colors[i % colors.length]
      const grad = ctx.createLinearGradient(x, y, x, paddingTop + chartH)
      grad.addColorStop(0, color)
      grad.addColorStop(1, color + '88')

      ctx.fillStyle = grad
      ctx.beginPath()
      const radius = Math.min(6, barWidth / 2)
      ctx.moveTo(x + radius, y)
      ctx.lineTo(x + barWidth - radius, y)
      ctx.quadraticCurveTo(x + barWidth, y, x + barWidth, y + radius)
      ctx.lineTo(x + barWidth, paddingTop + chartH)
      ctx.lineTo(x, paddingTop + chartH)
      ctx.lineTo(x, y + radius)
      ctx.quadraticCurveTo(x, y, x + radius, y)
      ctx.closePath()
      ctx.fill()

      ctx.fillStyle = '#374151'
      ctx.font = '11px Arial'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'bottom'
      ctx.fillText(String(item.count), x + barWidth / 2, y - 6)

      ctx.fillStyle = '#6b7280'
      ctx.font = '11px Arial'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'top'
      ctx.fillText(item.subject || '未分类', x + barWidth / 2, paddingTop + chartH + 8)
    })
  } catch {
    // ignore
  }
}
</script>

<style scoped>
.home {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  font-size: 24px;
  font-weight: bold;
  margin: 0;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 20px;
}

.stat-card {
  background: white;
  padding: 20px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.stat-icon {
  width: 50px;
  height: 50px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.word-icon {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.mistake-icon {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: white;
}

.rec-icon {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  color: white;
}

.time-icon {
  background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
  color: white;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  margin: 0;
  color: #333;
}

.stat-label {
  font-size: 14px;
  color: #999;
  margin: 4px 0 0;
}

.stat-rate {
  font-size: 12px;
  color: #67c23a;
  margin-left: 10px;
}

.quick-actions {
  background: white;
  padding: 20px;
  border-radius: 12px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.quick-actions h3 {
  margin: 0 0 16px;
  font-size: 16px;
  color: #333;
}

.action-buttons {
  display: flex;
  gap: 12px;
}

.recent-section {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.recent-section h3 {
  margin: 0 0 16px;
  font-size: 16px;
  color: #333;
}

.overview-section {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

.overview-card {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.overview-card h3 {
  margin: 0 0 16px;
  font-size: 16px;
  color: #333;
}

.chart-container {
  width: 100%;
  height: 220px;
}

.subject-chart-container {
  width: 100%;
  height: 200px;
}

.empty-text {
  text-align: center;
  color: #909399;
  padding: 20px;
}

.agent-section {
  background: white;
  padding: 20px;
  border-radius: 12px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-header h3 {
  margin: 0;
  font-size: 16px;
  color: #333;
}

.agents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 16px;
}

.agent-card {
  padding: 16px;
  transition: all 0.3s;
}

.agent-card.agent-disabled {
  opacity: 0.6;
  background: #f5f5f5;
}

.agent-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.agent-info {
  flex: 1;
}

.agent-name {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
}

.agent-desc {
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
}

.agent-keywords {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.more-keywords {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

@media (max-width: 1200px) {
  .overview-section {
    grid-template-columns: 1fr;
  }
}
</style>