<template>
  <div v-loading="loading">
    <!-- 指标卡 -->
    <div class="stat-grid">
      <el-card shadow="never" class="stat-card">
        <div class="stat-label">近7天学习时长</div>
        <div class="stat-value">{{ overview?.study_time_7d ?? 0 }} <small>分钟</small></div>
      </el-card>
      <el-card shadow="never" class="stat-card">
        <div class="stat-label">近7天单词</div>
        <div class="stat-value">{{ overview?.words_7d ?? 0 }}</div>
      </el-card>
      <el-card shadow="never" class="stat-card">
        <div class="stat-label">近7天做题</div>
        <div class="stat-value">{{ overview?.questions_7d ?? 0 }}</div>
      </el-card>
      <el-card shadow="never" class="stat-card">
        <div class="stat-label">累计错题</div>
        <div class="stat-value">{{ overview?.total_mistakes ?? 0 }}</div>
      </el-card>
      <el-card shadow="never" class="stat-card">
        <div class="stat-label">已掌握错题</div>
        <div class="stat-value good">{{ overview?.mastered_mistakes ?? 0 }}</div>
      </el-card>
      <el-card shadow="never" class="stat-card">
        <div class="stat-label">监督异常</div>
        <div class="stat-value" :class="{ bad: (overview?.supervision_abnormal ?? 0) > 0 }">
          {{ overview?.supervision_abnormal ?? 0 }}
        </div>
      </el-card>
    </div>

    <!-- 掌握度分布 -->
    <el-card shadow="never" class="block">
      <template #header>错题掌握度分布</template>
      <div v-if="distEntries.length === 0" class="muted">暂无错题</div>
      <div v-else class="dist-row">
        <div v-for="[level, count] in distEntries" :key="level" class="dist-item">
          <el-tag effect="plain">{{ level }}</el-tag>
          <span class="dist-count">{{ count }}</span>
        </div>
      </div>
    </el-card>

    <!-- 7 天学习趋势 -->
    <el-card shadow="never" class="block">
      <template #header>
        <div class="trend-head">
          <span>近7天学习趋势（主线为五项当日合计，可点击图例切换单项）</span>
          <div class="trend-legend">
            <span>悬停查看明细</span>
            <span>有监督异常的日期以红点标出</span>
          </div>
        </div>
      </template>
      <div ref="trendRef" class="trend-chart"></div>
    </el-card>

    <!-- 错题列表 -->
    <el-card shadow="never" class="block">
      <template #header>
        <div class="mistake-head">
          <span>错题列表</span>
          <el-select v-model="subject" placeholder="全部科目" clearable size="small" style="width: 140px" @change="loadMistakes">
            <el-option v-for="s in subjectOptions" :key="s" :label="s" :value="s" />
          </el-select>
        </div>
      </template>
      <el-table :data="mistakes" stripe border @row-click="openDetail">
        <el-table-column prop="subject" label="科目" width="90" />
        <el-table-column prop="knowledge_point" label="知识点" min-width="120" />
        <el-table-column prop="error_type" label="错误类型" min-width="100" />
        <el-table-column prop="difficulty" label="难度" width="80" />
        <el-table-column prop="mastery_level" label="掌握度" width="90">
          <template #default="{ row }">
            <el-tag :type="masteryType(row.mastery_level)" effect="plain" size="small">
              {{ row.mastery_level }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="记录时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 错题详情抽屉 -->
    <el-drawer v-model="detailVisible" title="错题详情" size="42%">
      <template v-if="detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="科目">{{ detail.subject }}</el-descriptions-item>
          <el-descriptions-item label="知识点">{{ detail.knowledge_point || '-' }}</el-descriptions-item>
          <el-descriptions-item label="错误类型">{{ detail.error_type || '-' }}</el-descriptions-item>
          <el-descriptions-item label="难度">{{ detail.difficulty || '-' }}</el-descriptions-item>
          <el-descriptions-item label="掌握度">{{ detail.mastery_level }}</el-descriptions-item>
          <el-descriptions-item label="题目">{{ detail.question_text || '-' }}</el-descriptions-item>
          <el-descriptions-item label="正确答案">{{ detail.answer || '-' }}</el-descriptions-item>
          <el-descriptions-item label="解析">{{ detail.analysis || '-' }}</el-descriptions-item>
          <el-descriptions-item label="错误原因">{{ detail.error_reason || '-' }}</el-descriptions-item>
          <el-descriptions-item label="复习次数">{{ detail.review_count }}（正确 {{ detail.correct_count }} 次）</el-descriptions-item>
        </el-descriptions>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import {
  type StudentOverview, type MistakeItem, type DailyPoint,
} from '../api/organization'

interface StudentApi {
  studentOverview: (id: number) => Promise<StudentOverview>
  studentMistakes: (id: number, subject?: string) => Promise<MistakeItem[]>
  studentMistakeDetail: (id: number, mistakeId: number) => Promise<MistakeItem>
}

const props = defineProps<{ studentId: number; api: StudentApi }>()

const loading = ref(false)
const overview = ref<StudentOverview | null>(null)
const mistakes = ref<MistakeItem[]>([])
const subject = ref('')
const detailVisible = ref(false)
const detail = ref<MistakeItem | null>(null)

const distEntries = computed(() => Object.entries(overview.value?.mastery_distribution || {}))
const subjectOptions = computed(() => [...new Set(mistakes.value.map(m => m.subject))])
// 当日综合得分：学习分钟 + 单词 + 做题 + 新增错题 + 监督异常
function dayScore(d: DailyPoint): number {
  return d.study_time + d.words + d.questions + d.mistakes + d.abnormal
}

// ---------- 趋势折线图 ----------
const trendRef = ref<HTMLElement | null>(null)
let trendChart: echarts.ECharts | null = null

function renderTrend() {
  const daily = overview.value?.daily
  if (!trendRef.value || !daily) return
  if (!trendChart) trendChart = echarts.init(trendRef.value)
  const dates = daily.map(d => d.date.slice(5))
  // 有监督异常的日期在合计线上标红点
  const composite = daily.map(d => ({
    value: dayScore(d),
    itemStyle: d.abnormal > 0 ? { color: '#ef4444' } : undefined,
  }))
  trendChart.setOption({
    tooltip: {
      trigger: 'axis',
      valueFormatter: (v: unknown) => String(v),
    },
    legend: {
      data: ['合计', '学习分钟', '单词', '做题', '错题', '监督异常'],
      selected: { 学习分钟: false, 单词: false, 做题: false, 错题: false, 监督异常: false },
      bottom: 0,
    },
    grid: { left: 40, right: 16, top: 16, bottom: 42 },
    xAxis: { type: 'category', data: dates, boundaryGap: false },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      {
        name: '合计', type: 'line', smooth: true, data: composite,
        lineStyle: { width: 3 }, areaStyle: { opacity: 0.08 },
      },
      { name: '学习分钟', type: 'line', smooth: true, data: daily.map(d => d.study_time) },
      { name: '单词', type: 'line', smooth: true, data: daily.map(d => d.words) },
      { name: '做题', type: 'line', smooth: true, data: daily.map(d => d.questions) },
      { name: '错题', type: 'line', smooth: true, data: daily.map(d => d.mistakes) },
      { name: '监督异常', type: 'line', smooth: true, data: daily.map(d => d.abnormal) },
    ],
  })
}

onBeforeUnmount(() => {
  trendChart?.dispose()
  trendChart = null
})

function masteryType(level: string) {
  if (level === '掌握') return 'success'
  if (level === '熟悉') return 'warning'
  return 'info'
}

function formatTime(t?: string) {
  return t ? new Date(t).toLocaleString('zh-CN', { hour12: false }) : '-'
}

async function loadMistakes() {
  mistakes.value = await props.api.studentMistakes(props.studentId, subject.value || undefined)
}

async function openDetail(row: MistakeItem) {
  try {
    detail.value = await props.api.studentMistakeDetail(props.studentId, row.id)
  } catch {
    detail.value = row
  }
  detailVisible.value = true
}

async function loadAll() {
  // 切换学生时重置面板状态
  overview.value = null
  mistakes.value = []
  subject.value = ''
  detail.value = null
  detailVisible.value = false
  loading.value = true
  try {
    overview.value = await props.api.studentOverview(props.studentId)
    await loadMistakes()
    renderTrend()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

// immediate 同时覆盖首次进入与切换学生两种情况
watch(() => props.studentId, loadAll, { immediate: true })
</script>

<style scoped>
.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 14px;
  margin-bottom: 16px;
}
.stat-card { border-radius: 12px; }
.stat-label { color: #6b7280; font-size: 13px; margin-bottom: 8px; }
.stat-value { font-size: 26px; font-weight: 700; color: #1f2937; }
.stat-value small { font-size: 13px; font-weight: 400; color: #6b7280; }
.stat-value.good { color: #16a34a; }
.stat-value.bad { color: #dc2626; }
.block { border-radius: 12px; margin-bottom: 16px; }
.muted { color: #9ca3af; }
.dist-row { display: flex; gap: 20px; flex-wrap: wrap; }
.dist-item { display: flex; align-items: center; gap: 8px; }
.dist-count { font-weight: 600; }
.trend-chart { width: 100%; height: 220px; }
.trend-head { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.trend-legend { display: flex; gap: 12px; font-size: 12px; color: #9ca3af; font-weight: 400; }
.mistake-head { display: flex; justify-content: space-between; align-items: center; }
:deep(.el-table__row) { cursor: pointer; }
</style>
