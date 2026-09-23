<template>
  <div class="recommend-page">
    <div class="page-header">
      <h2>智能推荐</h2>
      <div class="generate-controls">
        <el-select
          v-model="selectedSubject"
          placeholder="选择科目"
          clearable
          class="subject-select"
        >
          <el-option label="全部科目" value="" />
          <el-option label="数学" value="数学" />
          <el-option label="英语" value="英语" />
          <el-option label="政治" value="政治" />
          <el-option label="马原" value="马原" />
          <el-option label="毛中特" value="毛中特" />
          <el-option label="史纲" value="史纲" />
          <el-option label="思修" value="思修" />
          <el-option label="时政" value="时政" />
          <el-option label="专业课" value="专业课" />
        </el-select>
        <el-button type="primary" @click="handleGenerate" :loading="generating">
          <el-icon><Refresh /></el-icon>生成推荐题目
        </el-button>
      </div>
    </div>

    <div v-if="generating || generateProgress > 0" class="generate-progress">
      <el-progress
        :percentage="generateProgress"
        :status="generateStatus"
        :stroke-width="16"
        :text-inside="true"
      >
        <template #default="{ percentage }">
          <span class="progress-text">{{ percentage }}%</span>
        </template>
      </el-progress>
      <div class="progress-message">{{ generateMessage }}</div>
    </div>

    <div class="stats-row">
      <el-card class="stat-card">
        <div class="stat-icon">📊</div>
        <div class="stat-info">
          <div class="stat-value">{{ report.total_recommendations }}</div>
          <div class="stat-label">推荐总数</div>
        </div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-icon">✅</div>
        <div class="stat-info">
          <div class="stat-value">{{ report.completed_recommendations }}</div>
          <div class="stat-label">已完成</div>
        </div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-icon">🎯</div>
        <div class="stat-info">
          <div class="stat-value">{{ report.accuracy_rate }}%</div>
          <div class="stat-label">正确率</div>
        </div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-icon">⚡</div>
        <div class="stat-info">
          <div class="stat-value">{{ collaborationStats.avg_response_time_ms }}ms</div>
          <div class="stat-label">平均响应</div>
        </div>
      </el-card>
    </div>

    <div class="section">
      <h3>薄弱知识点分析</h3>
      <div v-if="weakPoints.length > 0" class="weak-points-list">
        <el-tag
          v-for="wp in weakPoints"
          :key="`${wp.subject}-${wp.knowledge_point}`"
          :type="getWeakLevelType(wp.weak_level)"
          class="weak-point-tag"
        >
          {{ wp.subject }} - {{ wp.knowledge_point }}
          <span class="weak-count">错误{{ wp.mistake_count }}次</span>
        </el-tag>
      </div>
      <div v-else class="empty-tip">
        <el-icon><InfoFilled /></el-icon>暂无薄弱知识点数据，请先添加错题
      </div>
    </div>

    <div class="section">
      <h3>待做推荐题目</h3>
      <div v-if="pendingRecommendations.length > 0" class="recommendation-list">
        <el-card
          v-for="rec in pendingRecommendations"
          :key="rec.id"
          class="recommendation-card"
        >
          <div class="rec-header">
            <el-tag>{{ rec.subject }}</el-tag>
            <el-tag :type="getDifficultyType(rec.difficulty)">{{ rec.difficulty }}</el-tag>
            <el-tag size="small">{{ rec.source }}</el-tag>
          </div>
          <div class="rec-question">
            <span class="question-label">题目：</span>
            <div class="question-text" v-html="renderLatex(rec.question_text)"></div>
          </div>
          <div class="rec-answer" v-if="showAnswers[rec.id]">
            <div class="answer-section">
              <span class="answer-label">答案：</span>
              <div class="answer-text" v-html="renderLatex(rec.answer)"></div>
            </div>
            <div class="analysis-section" v-if="rec.analysis">
              <span class="analysis-label">解析：</span>
              <div class="analysis-text" v-html="renderLatex(rec.analysis)"></div>
            </div>
          </div>
          <div class="rec-actions">
            <el-button
              type="danger"
              plain
              size="small"
              :loading="deletingIds.has(rec.id)"
              @click="handleDelete(rec, false)"
            >
              <el-icon><Delete /></el-icon>删除
            </el-button>
            <el-button
              v-if="!showAnswers[rec.id]"
              type="primary"
              size="small"
              @click="showAnswers[rec.id] = true"
            >
              查看答案
            </el-button>
            <div v-else class="result-buttons">
              <el-button type="success" size="small" @click="handleComplete(rec.id, '正确')">
                <el-icon><Check /></el-icon>正确
              </el-button>
              <el-button type="danger" size="small" @click="handleComplete(rec.id, '错误')">
                <el-icon><Close /></el-icon>错误
              </el-button>
            </div>
          </div>
        </el-card>
      </div>
      <div v-else class="empty-tip">
        <el-icon><InfoFilled /></el-icon>暂无待做推荐题目，点击上方按钮生成
      </div>
    </div>

    <div class="section">
      <h3>已完成题目</h3>
      <div v-if="completedRecommendations.length > 0" class="completed-list">
        <el-table :data="completedRecommendations" border>
          <el-table-column prop="subject" label="科目" width="100" />
          <el-table-column prop="knowledge_point" label="知识点" width="120" />
          <el-table-column label="题目" min-width="200">
            <template #default="scope">
              <span v-html="renderLatex(scope.row.question_text)"></span>
            </template>
          </el-table-column>
          <el-table-column prop="result" label="结果" width="80">
            <template #default="scope">
              <el-tag :type="scope.row.result === '正确' ? 'success' : 'danger'">
                {{ scope.row.result }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="source" label="来源" width="100" />
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="scope">
              <el-button
                type="danger"
                plain
                size="small"
                :loading="deletingIds.has(scope.row.id)"
                @click="handleDelete(scope.row, true)"
              >
                <el-icon><Delete /></el-icon>删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <div v-else class="empty-tip">
        <el-icon><InfoFilled /></el-icon>暂无已完成题目
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, InfoFilled, Check, Close, Delete } from '@element-plus/icons-vue'
import katex from 'katex'
import 'katex/dist/katex.min.css'
import {
  analyzeWeakPoints, generateRecommendations, getRecommendations,
  completeRecommendation, getRecommendationReport,
  getCollaborationLogs, deleteRecommendation,
  type Recommendation, type WeakPoint, type RecommendationReport,
  type CollaborationStats
} from '../api/recommendation'

function renderLatex(text: string): string {
  if (!text) return ''
  
  let result = text
  
  result = result.replace(/\$\$([\s\S]*?)\$\$/g, (match, formula) => {
    try {
      return katex.renderToString(formula.trim(), {
        throwOnError: false,
        displayMode: true
      })
    } catch {
      return match
    }
  })
  
  result = result.replace(/\$([^\$]+)\$/g, (match, formula) => {
    try {
      const isDisplayMode = formula.includes('lim') || formula.includes('int') || formula.includes('sum') || formula.includes('frac') || formula.length > 50
      return katex.renderToString(formula.trim(), {
        throwOnError: false,
        displayMode: isDisplayMode
      })
    } catch {
      return match
    }
  })
  
  const limPattern = /lim_{[^}]+}/g
  result = result.replace(limPattern, (match) => {
    try {
      return katex.renderToString(match, {
        throwOnError: false,
        displayMode: true
      })
    } catch {
      return match
    }
  })
  
  const fracPattern = /frac_{[^}]+}_{[^}]+}/g
  result = result.replace(fracPattern, (match) => {
    try {
      return katex.renderToString(match.replace(/_/g, '\\'), {
        throwOnError: false,
        displayMode: true
      })
    } catch {
      return match
    }
  })
  
  result = processMathProblems(result)
  
  return result
}

function processMathProblems(text: string): string {
  if (!text) return ''
  
  const mathPattern = /(求\s*(?:lim|导数|积分|解|证明)\s*[\s\S]*?)(?=\n\n|\n求|\n\d+\.|$)/gi
  
  return text.replace(mathPattern, (problem) => {
    const cleaned = cleanMathText(problem)
    const formatted = formatMathProblem(cleaned)
    
    try {
      return katex.renderToString(formatted, {
        throwOnError: false,
        displayMode: true
      })
    } catch {
      return problem
    }
  })
}

function cleanMathText(text: string): string {
  let cleaned = text
  
  cleaned = cleaned.replace(/<[^>]+>/g, '')
  cleaned = cleaned.replace(/\\\([^)]+\\\)/g, (match) => {
    return match.replace(/\\\(|\)/g, '')
  })
  cleaned = cleaned.replace(/\\\[[^\]]+\\\]/g, (match) => {
    return match.replace(/\\\[|\\\]/g, '')
  })
  cleaned = cleaned.replace(/\*\*/g, '')
  cleaned = cleaned.replace(/\*/g, ' \\cdot ')
  cleaned = cleaned.replace(/\^\{?(\d+)\}?/g, '^{$1}')
  cleaned = cleaned.replace(/\^([a-zA-Z]+)/g, '^{$1}')
  cleaned = cleaned.replace(/\_\{?(\d+)\}?/g, '_{$1}')
  cleaned = cleaned.replace(/\n\s*/g, ' ')
  
  return cleaned.trim()
}

function formatMathProblem(text: string): string {
  let formatted = text
  
  formatted = formatted.replace(/(\b(?:sin|cos|tan|cot|sec|csc|log|ln|exp|sqrt|abs|lim|int|sum|prod))\s*\(/gi, '$1(')
  formatted = formatted.replace(/(\b(?:sin|cos|tan|cot|sec|csc|log|ln|exp|sqrt|abs|lim|int|sum|prod))\s+([a-zA-Z])/gi, '$1($2)')
  
  formatted = formatted.replace(/lim\s+x\s*→\s*(\d+)/gi, '\\lim_{x \\to $1}')
  formatted = formatted.replace(/lim\s+x\s*→\s*([a-zA-Z]+)/gi, '\\lim_{x \\to $1}')
  formatted = formatted.replace(/lim\s+x\s*→\s*(\d+(\.\d+)?)/gi, '\\lim_{x \\to $1}')
  
  formatted = formatted.replace(/lim_\\{([^}]+)\\}/g, '\\lim_{$1}')
  formatted = formatted.replace(/lim\\{([^}]+)\\}/g, '\\lim_{$1}')
  
  formatted = formatted.replace(/(\d+)\s*\/\s*(\d+)/g, '\\frac{$1}{$2}')
  formatted = formatted.replace(/([a-zA-Z0-9]+)\s*\/\s*([a-zA-Z0-9]+)/g, '\\frac{$1}{$2}')
  
  formatted = formatted.replace(/frac_\\{([^}]+)\\}\\{([^}]+)\\}/g, '\\frac{$1}{$2}')
  formatted = formatted.replace(/frac\\{([^}]+)\\}\\{([^}]+)\\}/g, '\\frac{$1}{$2}')
  
  formatted = formatted.replace(/(\b[a-zA-Z]+\^\d+)/g, (match) => {
    const parts = match.match(/([a-zA-Z]+)\^(\d+)/)
    if (parts) {
      return `${parts[1]}^{${parts[2]}}`
    }
    return match
  })
  
  formatted = formatted.replace(/(\b[a-zA-Z]+\_[a-zA-Z0-9]+)/g, (match) => {
    const parts = match.match(/([a-zA-Z]+)\_([a-zA-Z0-9]+)/)
    if (parts) {
      return `${parts[1]}_{${parts[2]}}`
    }
    return match
  })
  
  formatted = formatted.replace(/(\b(?:alpha|beta|gamma|delta|epsilon|zeta|eta|theta|iota|kappa|lambda|mu|nu|xi|pi|rho|sigma|tau|upsilon|phi|chi|psi|omega)\b)/gi, (match) => {
    const greekMap: Record<string, string> = {
      'alpha': '\\alpha', 'beta': '\\beta', 'gamma': '\\gamma',
      'delta': '\\delta', 'epsilon': '\\epsilon', 'zeta': '\\zeta',
      'eta': '\\eta', 'theta': '\\theta', 'iota': '\\iota',
      'kappa': '\\kappa', 'lambda': '\\lambda', 'mu': '\\mu',
      'nu': '\\nu', 'xi': '\\xi', 'pi': '\\pi', 'rho': '\\rho',
      'sigma': '\\sigma', 'tau': '\\tau', 'upsilon': '\\upsilon',
      'phi': '\\phi', 'chi': '\\chi', 'psi': '\\psi', 'omega': '\\omega'
    }
    return greekMap[match.toLowerCase()] || match
  })
  
  formatted = formatted.replace(/\b(?:inf|infty|infinity)\b/gi, '\\infty')
  
  formatted = formatted.replace(/\\to/g, '\\to')
  formatted = formatted.replace(/→/g, '\\to')
  
  return formatted
}

const weakPoints = ref<WeakPoint[]>([])
const recommendations = ref<Recommendation[]>([])
const report = reactive<RecommendationReport>({
  total_recommendations: 0,
  completed_recommendations: 0,
  correct_recommendations: 0,
  accuracy_rate: 0,
  weak_points: []
})
const showAnswers = reactive<Record<number, boolean>>({})
const collaborationStats = reactive<CollaborationStats>({
  total_collaborations: 0,
  success_rate: 0,
  avg_response_time_ms: 0
})
const generating = ref(false)
const generateProgress = ref(0)
const generateStatus = ref<'success' | 'exception' | 'warning' | undefined>(undefined)
const generateMessage = ref('')
const selectedSubject = ref('')
const deletingIds = reactive<Set<number>>(new Set())

const pendingRecommendations = computed(() => recommendations.value.filter((r: Recommendation) => !r.completed))
const completedRecommendations = computed(() => recommendations.value.filter((r: Recommendation) => r.completed))

function getWeakLevelType(level: number) {
  if (level >= 4) return 'danger'
  if (level >= 3) return 'warning'
  return 'info'
}

function getDifficultyType(difficulty: string) {
  switch (difficulty) {
    case '困难': return 'danger'
    case '中等': return 'warning'
    default: return 'success'
  }
}

async function loadData() {
  try {
    weakPoints.value = await analyzeWeakPoints()
    recommendations.value = await getRecommendations()
    const data = await getRecommendationReport()
    Object.assign(report, data)
    
    const logData = await getCollaborationLogs()
    Object.assign(collaborationStats, logData.stats)
  } catch {
    recommendations.value = []
  }
}

async function handleGenerate() {
  generating.value = true
  generateProgress.value = 0
  generateStatus.value = undefined
  generateMessage.value = '正在分析薄弱知识点...'
  try {
    const subject = selectedSubject.value || undefined
    generateMessage.value = '正在生成推荐题目（AI处理中，请耐心等待）...'
    generateProgress.value = 30
    const newRecs = await generateRecommendations(5, subject)
    generateProgress.value = 90
    recommendations.value = [...newRecs, ...recommendations.value]
    const data = await getRecommendationReport()
    Object.assign(report, data)
    generateProgress.value = 100
    generateStatus.value = 'success'
    generateMessage.value = '生成完成'
    ElMessage.success(`成功生成 ${newRecs.length} 道推荐题目`)
  } catch (error: any) {
    generateStatus.value = 'exception'
    generateMessage.value = '生成失败'
    ElMessage.error(error.response?.data?.detail || '生成失败')
  } finally {
    generating.value = false
  }
}

async function handleComplete(id: number, result: string) {
  try {
    await completeRecommendation(id, result)
    showAnswers[id] = false
    await loadData()
    ElMessage.success(`已标记为${result}`)
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  }
}

async function handleDelete(rec: Recommendation, isCompleted: boolean) {
  const label = isCompleted ? '已完成题目' : '待做推荐题目'
  try {
    await ElMessageBox.confirm(
      `确定删除该${label}吗？删除后无法恢复。`,
      '删除确认',
      {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        confirmButtonClass: 'el-button--danger',
      }
    )
  } catch {
    return
  }

  deletingIds.add(rec.id)
  try {
    await deleteRecommendation(rec.id)
    recommendations.value = recommendations.value.filter(r => r.id !== rec.id)
    delete showAnswers[rec.id]
    const data = await getRecommendationReport()
    Object.assign(report, data)
    ElMessage.success('已删除')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '删除失败')
  } finally {
    deletingIds.delete(rec.id)
  }
}

onMounted(loadData)
</script>

<style scoped>
.recommend-page {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
}

.generate-controls {
  display: flex;
  gap: 12px;
  align-items: center;
}

.generate-progress {
  margin-bottom: 20px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
}

.progress-text {
  font-size: 13px;
  font-weight: 600;
}

.progress-message {
  margin-top: 8px;
  font-size: 13px;
  color: #909399;
  text-align: center;
}

.subject-select {
  width: 160px;
}

.stats-row {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  font-size: 32px;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #409eff;
}

.stat-label {
  font-size: 14px;
  color: #666;
}

.section {
  margin-bottom: 24px;
}

.section h3 {
  margin: 0 0 16px;
  font-size: 16px;
  color: #333;
}

.weak-points-list {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.weak-point-tag {
  padding: 8px 16px;
}

.weak-count {
  margin-left: 8px;
  font-size: 12px;
  opacity: 0.8;
}

.recommendation-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.recommendation-card {
  padding: 16px;
}

.rec-header {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.rec-question {
  font-size: 14px;
  line-height: 1.6;
  margin-bottom: 12px;
}

.question-label {
  font-weight: 600;
  color: #333;
  display: block;
  margin-bottom: 8px;
}

.question-text, .answer-text, .analysis-text {
  font-size: 14px;
  line-height: 1.8;
  color: #333;
}

.question-text {
  white-space: pre-wrap;
}

.katex {
  font-size: 1.1em;
}

.katex-display {
  margin: 0.5em 0;
  text-align: center;
}

.rec-answer {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  margin-bottom: 12px;
}

.answer-section, .analysis-section {
  font-size: 14px;
  line-height: 1.6;
  margin-bottom: 12px;
}

.answer-section:last-child, .analysis-section:last-child {
  margin-bottom: 0;
}

.answer-label, .analysis-label {
  font-weight: 600;
  color: #333;
  display: block;
  margin-bottom: 8px;
}

.rec-actions {
  display: flex;
  justify-content: flex-end;
}

.result-buttons {
  display: flex;
  gap: 8px;
}

.completed-list {
  max-height: 400px;
  overflow-y: auto;
}

.empty-tip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 40px;
  background: #f5f7fa;
  border-radius: 8px;
  color: #909399;
  justify-content: center;
}
</style>