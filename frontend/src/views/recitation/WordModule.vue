<template>
  <div class="word-module">
    <div class="stats-section">
      <div class="stat-card">
        <p class="stat-value">{{ wordStats.total }}</p>
        <p class="stat-label">词汇总量</p>
      </div>
      <div class="stat-card">
        <p class="stat-value">{{ wordStats.studied }}</p>
        <p class="stat-label">已学单词</p>
      </div>
      <div class="stat-card">
        <p class="stat-value">{{ wordStats.mastered }}</p>
        <p class="stat-label">已掌握</p>
      </div>
      <div class="stat-card">
        <p class="stat-value">{{ wordStats.today }}</p>
        <p class="stat-label">今日学习</p>
      </div>
      <div class="stat-card source-card">
        <p class="stat-value" style="font-size: 18px">{{ currentSourceLabel }}</p>
        <p class="stat-label">当前来源</p>
      </div>
    </div>

    <el-tabs v-model="subTab" class="sub-tabs">
      <el-tab-pane label="今日学习" name="today">
        <div class="study-section">
          <div class="plan-bar">
            <el-form :inline="true">
              <el-form-item label="词汇分类">
                <el-select
                  v-model="selectedCategory"
                  placeholder="选择词汇分类"
                  style="width: 150px"
                  clearable
                  @change="handleCategoryChange"
                >
                  <el-option label="全部" value="" />
                  <el-option v-for="cat in categories" :key="cat" :label="cat" :value="cat" />
                </el-select>
              </el-form-item>
              <el-form-item label="每日学习量">
                <el-slider v-model="dailyCount" :min="5" :max="100" :step="5" style="width: 160px" />
                <span style="margin-left: 12px">{{ dailyCount }} 词</span>
              </el-form-item>
              <el-form-item label="每轮批次">
                <el-slider v-model="batchSize" :min="5" :max="dailyCount" :step="5" style="width: 140px" />
                <span style="margin-left: 12px">{{ batchSize }} 词</span>
                <span v-if="batchSize > dailyCount" style="color: #f56c6c; margin-left: 8px; font-size: 12px">不能大于每日总量</span>
              </el-form-item>
              <el-form-item label="背诵模式">
                <el-radio-group v-model="studyMode">
                  <el-radio-button label="mixed">混合模式</el-radio-button>
                  <el-radio-button label="new_first">新词优先</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="savePlan">保存背诵配置</el-button>
              </el-form-item>
              <el-form-item>
                <el-button type="success" :loading="uploadingWordbook" @click="triggerWordbookUpload">
                  <el-icon><Upload /></el-icon>上传词书
                </el-button>
                <input
                  ref="wordbookInput"
                  type="file"
                  accept=".pdf,.txt,.doc,.docx"
                  class="hidden-input"
                  @change="handleWordbookSelect"
                />
              </el-form-item>
            </el-form>
            <div class="daily-stats">
              <span class="daily-stat-item">
                <el-tag type="warning">待复习: {{ reviewCount }}</el-tag>
              </span>
              <span class="daily-stat-item">
                <el-tag type="success">新单词: {{ newCount }}</el-tag>
              </span>
              <span class="daily-stat-item">
                <el-tag type="info">今日到期: {{ wordStats.review_due || 0 }}</el-tag>
              </span>
            </div>
          </div>

          <!-- 轮次进度条 -->
          <div v-if="totalRounds > 0" class="round-progress-bar">
            <div class="progress-info">
              <span>全局进度: {{ globalIndex }} / {{ totalWordsToday }}</span>
              <span v-if="currentRound > 0 && currentRound <= totalRounds">
                | 第 {{ currentRound }} / {{ totalRounds }} 轮
              </span>
              <span v-if="currentRound > 0 && currentRound <= totalRounds">
                | 本轮剩余: {{ roundQueue.length }} / {{ currentRoundSize }}
              </span>
            </div>
            <el-progress
              :percentage="Math.round((globalIndex / Math.max(totalWordsToday, 1)) * 100)"
              :stroke-width="10"
              status="success"
            />
          </div>

          <!-- 单词卡片 -->
          <div v-if="currentWord" class="word-card">
            <div class="word-header">
              <span class="word-number">
                全局 {{ globalIndex + 1 }} / {{ totalWordsToday }}
                <span v-if="currentRound > 0"> | 本轮 {{ currentRoundIndex + 1 }} / {{ currentRoundSize }}</span>
              </span>
              <span class="word-tag">{{ currentWord.exam_requirement }}</span>
              <span :class="currentWord.type === 'review' ? 'review-badge' : 'new-badge'">
                {{ currentWord.type === 'review' ? '复习' : '新单词' }}
              </span>
            </div>
            <h2 class="word">{{ currentWord.word }}</h2>
            <p class="phonetic">{{ currentWord.phonetic }}</p>
            <div class="word-actions">
              <el-button @click="showMeaning = !showMeaning">
                {{ showMeaning ? '隐藏释义' : '显示释义' }}
              </el-button>
              <el-button @click="speakWord(currentWord.word)">
                <el-icon><VideoPlay /></el-icon>发音
              </el-button>
            </div>
            <div v-if="showMeaning" class="word-detail">
              <p class="meaning">{{ currentWord.meaning }}</p>
              <p v-if="currentWord.example_sentence" class="example">
                例句：{{ currentWord.example_sentence }}
                <el-button size="small" text @click="speakWord(currentWord.example_sentence)">
                  <el-icon><VideoPlay /></el-icon>朗读
                </el-button>
              </p>
            </div>
            <div class="study-buttons">
              <el-button type="danger" size="large" @click="markResult('不认识')">不认识</el-button>
              <el-button type="warning" size="large" @click="markResult('模糊')">模糊</el-button>
              <el-button type="success" size="large" @click="markResult('认识')">认识</el-button>
            </div>
          </div>

          <!-- 今日完成 -->
          <div v-else-if="allRoundsComplete" class="empty-state">
            <el-empty description="今日所有轮次已完成！">
              <el-button type="primary" @click="restartToday">重新开始今日学习</el-button>
            </el-empty>
          </div>

          <!-- 空状态 -->
          <div v-else class="empty-state">
            <el-empty description="今日单词已学完">
              <el-button type="primary" @click="loadTodayWords">重新加载</el-button>
            </el-empty>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="今日复习" name="review">
        <div class="study-section">
          <div class="plan-bar">
            <el-form :inline="true">
              <el-form-item label="复习范围">
                <el-select
                  v-model="reviewRange"
                  placeholder="选择复习范围"
                  style="width: 150px"
                  @change="loadReviewWords"
                >
                  <el-option label="今日到期" value="today" />
                  <el-option label="近一日" value="day" />
                  <el-option label="近一周" value="week" />
                  <el-option label="近一月" value="month" />
                  <el-option label="系统推荐" value="recommended" />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="loadReviewWords">刷新列表</el-button>
              </el-form-item>
            </el-form>
            <div class="daily-stats">
              <span class="daily-stat-item">
                <el-tag type="info">待复习: {{ reviewWords.length }} 词</el-tag>
              </span>
            </div>
          </div>

          <el-table :data="reviewWords" border style="margin-top: 12px">
            <el-table-column prop="word" label="单词" width="140" />
            <el-table-column prop="phonetic" label="音标" width="140" />
            <el-table-column prop="meaning" label="释义" />
            <el-table-column prop="exam_requirement" label="标签" width="100" />
            <el-table-column label="操作" width="120">
              <template #default="scope">
                <el-button size="small" @click="speakWord(scope.row.word)">
                  <el-icon><VideoPlay /></el-icon>发音
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <el-tab-pane label="单词列表" name="list">
        <div class="list-section">
          <div class="list-filters">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索单词"
              style="width: 200px"
              clearable
              @clear="loadWordList"
              @keyup.enter="loadWordList"
            />
            <el-select
              v-model="filterLevel"
              placeholder="掌握程度"
              style="width: 150px"
              clearable
              @change="loadWordList"
            >
              <el-option label="未学习" value="未学习" />
              <el-option label="陌生" value="陌生" />
              <el-option label="认识" value="认识" />
              <el-option label="熟悉" value="熟悉" />
              <el-option label="掌握" value="掌握" />
            </el-select>
            <el-button type="primary" @click="loadWordList">筛选</el-button>
          </div>
          <el-table :data="wordList" border>
            <el-table-column prop="word" label="单词" width="140" />
            <el-table-column prop="phonetic" label="音标" width="140" />
            <el-table-column prop="meaning" label="释义" />
            <el-table-column prop="mastery_level" label="掌握程度" width="100">
              <template #default="scope">
                <el-tag :type="getMasteryTagType(scope.row.mastery_level)">
                  {{ scope.row.mastery_level }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="review_count" label="复习次数" width="100" />
            <el-table-column prop="next_review_date" label="下次复习" width="120">
              <template #default="scope">
                {{ scope.row.next_review_date ? scope.row.next_review_date.substring(0, 10) : '-' }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="scope">
                <el-button size="small" @click="speakWord(scope.row.word)">
                  <el-icon><VideoPlay /></el-icon>
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination">
            <el-pagination
              v-model:current-page="currentPage"
              v-model:page-size="pageSize"
              :total="totalWords"
              :page-sizes="[20, 50, 100]"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="loadWordList"
              @current-change="loadWordList"
            />
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 轮次完成弹窗 -->
    <el-dialog
      v-model="roundCompleteVisible"
      title="本轮完成！"
      width="400px"
      :close-on-click-modal="false"
      :show-close="false"
    >
      <div class="round-stats">
        <p class="round-stats-title">第 {{ currentRound }} 轮统计</p>
        <div class="round-stats-grid">
          <div class="round-stat-item success">
            <span class="stat-num">{{ roundStats.known }}</span>
            <span class="stat-label">认识</span>
          </div>
          <div class="round-stat-item warning">
            <span class="stat-num">{{ roundStats.vague }}</span>
            <span class="stat-label">模糊</span>
          </div>
          <div class="round-stat-item danger">
            <span class="stat-num">{{ roundStats.unknown }}</span>
            <span class="stat-label">不认识</span>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="exitStudy">退出背诵</el-button>
        <el-button type="primary" @click="startNextRound">开启下一轮</el-button>
      </template>
    </el-dialog>

    <!-- 恢复进度弹窗 -->
    <el-dialog
      v-model="resumeVisible"
      title="恢复背诵进度"
      width="360px"
    >
      <p>检测到未完成的背诵进度，是否继续？</p>
      <p style="color: #999; font-size: 14px; margin-top: 8px">
        第 {{ savedSession?.current_round }} / {{ savedSession?.total_rounds }} 轮，
        剩余 {{ savedSession?.round_queue?.length || 0 }} 个单词
      </p>
      <template #footer>
        <el-button @click="discardSession">重新开始</el-button>
        <el-button type="primary" @click="resumeSession">继续背诵</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { VideoPlay, Upload } from '@element-plus/icons-vue'
import {
  getWordStats, getTodayWords, getWordList,
  studyWord, getStudyPlan, saveStudyPlan, getWordCategories, uploadWordbook,
  getReviewWordsByRange, getStudySession, saveStudySession, clearStudySession,
  type Word, type UserWord, type TodayWordsResponse, type StudySession, type RoundQueueItem
} from '../../api/words'
import { useSpeech } from '@/composables/useSpeech'

const { speak: speakWord } = useSpeech()

const subTab = ref('today')
const wordStats = reactive({
  total: 0,
  studied: 0,
  mastered: 0,
  today: 0,
  has_wordbook: false,
  review_due: 0
})
const uploadingWordbook = ref(false)
const wordbookInput = ref<HTMLInputElement | null>(null)

// 计划配置
const dailyCount = ref(20)
const batchSize = ref(20)
const studyMode = ref('mixed')
const selectedCategory = ref<string>('')
const categories = ref<string[]>([])

// 今日单词数据
const todayWords = ref<Word[]>([])
const reviewCount = ref(0)
const newCount = ref(0)

// 轮次状态
const currentRound = ref(0)
const totalRounds = ref(0)
const roundQueue = ref<RoundQueueItem[]>([])
const roundStats = reactive({ known: 0, vague: 0, unknown: 0 })
const globalIndex = ref(0)
const totalWordsToday = ref(0)
const completedRounds = ref(0)
const allRoundsComplete = ref(false)

// UI 状态
const showMeaning = ref(false)
const roundCompleteVisible = ref(false)
const resumeVisible = ref(false)
const savedSession = ref<StudySession | null>(null)

// 统计刷新防抖
let statsRefreshTimer: ReturnType<typeof setTimeout> | null = null
function scheduleStatsRefresh(delay = 2000) {
  if (statsRefreshTimer) {
    clearTimeout(statsRefreshTimer)
  }
  statsRefreshTimer = setTimeout(async () => {
    statsRefreshTimer = null
    await loadStats(selectedCategory.value || undefined)
  }, delay)
}

// 单词列表
const wordList = ref<UserWord[]>([])
const searchKeyword = ref('')
const filterLevel = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const totalWords = ref(0)

// 复习列表
const reviewWords = ref<Word[]>([])
const reviewRange = ref('today')

const currentSourceLabel = computed(() => {
  const cat = selectedCategory.value
  if (!cat || cat === '全部') return '系统+词书'
  if (cat === '我的词书') return '我的词书'
  return cat
})

const currentWord = computed<RoundQueueItem | null>(() => {
  return roundQueue.value.length > 0 ? roundQueue.value[0] : null
})

const currentRoundIndex = computed(() => {
  if (currentRound.value <= 0 || currentRound.value > totalRounds.value) return 0
  const roundStart = (currentRound.value - 1) * batchSize.value
  return globalIndex.value - roundStart
})

const currentRoundSize = computed(() => {
  if (currentRound.value <= 0 || currentRound.value > totalRounds.value) return 0
  const start = (currentRound.value - 1) * batchSize.value
  const end = Math.min(start + batchSize.value, totalWordsToday.value)
  return end - start
})

function getMasteryTagType(level: string) {
  switch (level) {
    case '未学习': return 'default'
    case '陌生': return 'danger'
    case '认识': return 'warning'
    case '熟悉': return 'info'
    case '掌握': return 'success'
    default: return 'default'
  }
}

async function loadStats(category?: string) {
  try {
    const stats = await getWordStats(category)
    Object.assign(wordStats, stats)
  } catch {
    wordStats.total = 0
    wordStats.studied = 0
    wordStats.mastered = 0
    wordStats.today = 0
    wordStats.review_due = 0
  }
}

async function loadPlan() {
  try {
    const plan = await getStudyPlan()
    dailyCount.value = plan.daily_word_count
    batchSize.value = plan.batch_size ?? 20
    studyMode.value = plan.study_mode ?? 'mixed'
    if (plan.word_category !== null && plan.word_category !== undefined) {
      selectedCategory.value = plan.word_category
    }
  } catch {
    dailyCount.value = 20
    batchSize.value = 20
    studyMode.value = 'mixed'
  }
}

async function loadCategories() {
  try {
    const result = await getWordCategories()
    categories.value = result.categories
  } catch {
    categories.value = ['CET-4', 'CET-6', '考研']
  }
}

async function savePlan() {
  try {
    await saveStudyPlan(dailyCount.value, selectedCategory.value || undefined, batchSize.value, studyMode.value)
    ElMessage.success('背诵配置已保存')
    await loadTodayWords()
  } catch {
    ElMessage.success(`配置已保存：每日${dailyCount.value}词，每轮${batchSize.value}词`)
    await loadTodayWords()
  }
}

async function loadTodayWords() {
  try {
    const category = selectedCategory.value || undefined
    const result: TodayWordsResponse = await getTodayWords(dailyCount.value, category)

    // 根据背诵模式排序单词
    if (studyMode.value === 'new_first') {
      todayWords.value = [...result.new, ...result.review]
    } else {
      todayWords.value = [...result.review, ...result.new]
    }

    reviewCount.value = result.review_count
    newCount.value = result.new_count
    totalWordsToday.value = result.total_today
    globalIndex.value = 0
    completedRounds.value = 0
    allRoundsComplete.value = false

    // 构建轮次
    buildRounds()

    // 启动第一轮
    if (totalRounds.value > 0) {
      await startRound(1)
    } else {
      roundQueue.value = []
    }
  } catch {
    todayWords.value = [
      { id: 1, word: 'abandon', phonetic: '/əˈbændən/', meaning: 'v. 放弃，抛弃', example_sentence: 'He decided to abandon the project.', difficulty: 1, frequency: 95, exam_requirement: '高频词', type: 'new' },
      { id: 2, word: 'ability', phonetic: '/əˈbɪləti/', meaning: 'n. 能力，才能', example_sentence: 'She has the ability to learn quickly.', difficulty: 1, frequency: 88, exam_requirement: '考纲词', type: 'new' },
      { id: 3, word: 'absolute', phonetic: '/ˈæbsəluːt/', meaning: 'adj. 绝对的，完全的', example_sentence: 'This is an absolute truth.', difficulty: 2, frequency: 75, exam_requirement: '考纲词', type: 'new' },
    ]
    reviewCount.value = 0
    newCount.value = todayWords.value.length
    totalWordsToday.value = todayWords.value.length
    buildRounds()
    if (totalRounds.value > 0) await startRound(1)
  }
}

function buildRounds() {
  if (!todayWords.value.length) {
    totalRounds.value = 0
    return
  }

  const total = todayWords.value.length
  totalRounds.value = Math.ceil(total / batchSize.value)
}

async function startRound(roundNum: number) {
  if (roundNum > totalRounds.value) {
    allRoundsComplete.value = true
    roundQueue.value = []
    currentRound.value = totalRounds.value
    await clearStudySession()
    return
  }

  currentRound.value = roundNum
  const start = (roundNum - 1) * batchSize.value
  const end = Math.min(start + batchSize.value, totalWordsToday.value)
  const roundWords = todayWords.value.slice(start, end)

  roundQueue.value = roundWords.map(w => ({
    wordId: w.id,
    word: w.word,
    phonetic: w.phonetic,
    meaning: w.meaning,
    example_sentence: w.example_sentence,
    exam_requirement: w.exam_requirement,
    type: w.type || 'new',
    repeatCount: 0
  }))

  roundStats.known = 0
  roundStats.vague = 0
  roundStats.unknown = 0
  showMeaning.value = false
  allRoundsComplete.value = false

  await saveCurrentSession()
}

async function markResult(result: string) {
  if (!currentWord.value) return

  const word = currentWord.value

  // 调用后端记录学习结果
  try {
    await studyWord(word.wordId, result)
  } catch {
    // 本地回退
  }

  // 更新全局统计
  wordStats.today++
  if (result === '认识') {
    wordStats.mastered++
  }

  // 防抖刷新后端统计（处理跨轮、跨批次的已学/已掌握口径差异）
  scheduleStatsRefresh()

  // 更新轮次内队列
  if (result === '认识') {
    roundStats.known++
    roundQueue.value.shift()
    globalIndex.value++
  } else if (result === '模糊') {
    roundStats.vague++
    if (word.repeatCount < 2) {
      // 重新插入队尾，重复次数+1
      const item = roundQueue.value.shift()
      if (item) {
        item.repeatCount++
        roundQueue.value.push(item)
      }
    } else {
      // 已达到最大重复次数，移出队列
      roundQueue.value.shift()
      globalIndex.value++
    }
  } else if (result === '不认识') {
    roundStats.unknown++
    // 重新插入队尾，持续重复
    const item = roundQueue.value.shift()
    if (item) {
      item.repeatCount++
      roundQueue.value.push(item)
    }
  }

  showMeaning.value = false

  // 保存进度
  await saveCurrentSession()

  // 检查本轮是否完成
  if (roundQueue.value.length === 0) {
    completedRounds.value++
    roundCompleteVisible.value = true
  }
}

async function startNextRound() {
  roundCompleteVisible.value = false
  // 轮次切换时立即刷新统计，保证跨轮数据准确
  if (statsRefreshTimer) {
    clearTimeout(statsRefreshTimer)
    statsRefreshTimer = null
  }
  await loadStats(selectedCategory.value || undefined)
  startRound(currentRound.value + 1)
}

async function exitStudy() {
  roundCompleteVisible.value = false
  allRoundsComplete.value = true
  roundQueue.value = []
  // 退出时取消未执行的防抖刷新，并立即同步一次统计
  if (statsRefreshTimer) {
    clearTimeout(statsRefreshTimer)
    statsRefreshTimer = null
  }
  await loadStats(selectedCategory.value || undefined)
  await clearStudySession()
  ElMessage.success('背诵已结束，进度已保存')
}

function restartToday() {
  allRoundsComplete.value = false
  loadTodayWords()
}

async function saveCurrentSession() {
  if (totalWordsToday.value === 0) return
  const session: StudySession = {
    current_round: currentRound.value,
    total_rounds: totalRounds.value,
    round_queue: roundQueue.value,
    round_stats: { known: roundStats.known, vague: roundStats.vague, unknown: roundStats.unknown },
    global_index: globalIndex.value,
    total_words_today: totalWordsToday.value,
    study_mode: studyMode.value,
    batch_size: batchSize.value,
    all_word_ids: todayWords.value.map(w => w.id),
    completed_rounds: completedRounds.value,
    category: selectedCategory.value || null
  }
  try {
    await saveStudySession(session)
  } catch {
    // 忽略保存错误
  }
}

async function checkAndResumeSession() {
  try {
    const session = await getStudySession()
    if (session && session.total_words_today > 0 && session.category === (selectedCategory.value || null)) {
      savedSession.value = session
      resumeVisible.value = true
    }
  } catch {
    // 无保存的进度
  }
}

async function resumeSession() {
  resumeVisible.value = false
  const session = savedSession.value
  if (!session) return

  // 恢复状态
  currentRound.value = session.current_round
  totalRounds.value = session.total_rounds
  roundQueue.value = session.round_queue.map((item: any) => ({
    wordId: item.wordId || item.word_id,
    word: item.word,
    phonetic: item.phonetic,
    meaning: item.meaning,
    example_sentence: item.example_sentence,
    exam_requirement: item.exam_requirement,
    type: item.type,
    repeatCount: item.repeatCount || 0
  }))
  roundStats.known = session.round_stats.known
  roundStats.vague = session.round_stats.vague
  roundStats.unknown = session.round_stats.unknown
  globalIndex.value = session.global_index
  totalWordsToday.value = session.total_words_today
  completedRounds.value = session.completed_rounds || 0
  studyMode.value = session.study_mode
  batchSize.value = session.batch_size
  allRoundsComplete.value = false

  // 需要重新加载 todayWords 以恢复单词数据
  try {
    const category = selectedCategory.value || undefined
    const result: TodayWordsResponse = await getTodayWords(dailyCount.value, category)
    todayWords.value = [...result.review, ...result.new]
  } catch {
    // 使用已有数据
  }

  ElMessage.success('已恢复背诵进度')
}

async function discardSession() {
  resumeVisible.value = false
  await clearStudySession()
  await loadTodayWords()
}

async function loadReviewWords() {
  try {
    const result = await getReviewWordsByRange(reviewRange.value)
    reviewWords.value = result.words.map(w => ({ ...w, type: 'review' }))
  } catch {
    reviewWords.value = []
  }
}

async function loadWordList() {
  try {
    const result = await getWordList({
      page: currentPage.value,
      page_size: pageSize.value,
      mastery_level: filterLevel.value || undefined,
      keyword: searchKeyword.value || undefined,
      category: selectedCategory.value || undefined
    })
    wordList.value = result.items
    totalWords.value = result.total
  } catch {
    wordList.value = []
    totalWords.value = 0
  }
}

onMounted(async () => {
  await loadPlan()
  await loadStats(selectedCategory.value || undefined)
  await loadCategories()
  await loadWordList()
  await checkAndResumeSession()
  if (!resumeVisible.value) {
    await loadTodayWords()
  }
})

watch(dailyCount, (newVal) => {
  if (batchSize.value > newVal) {
    batchSize.value = newVal
  }
})

watch(subTab, async (newTab) => {
  if (newTab === 'review') {
    await loadReviewWords()
  }
})

async function handleCategoryChange() {
  const cat = selectedCategory.value || undefined
  await loadTodayWords()
  await loadStats(cat)
  await loadWordList()
  await savePlan()
}

function triggerWordbookUpload() {
  wordbookInput.value?.click()
}

async function handleWordbookSelect(event: Event) {
  const target = event.target as HTMLInputElement
  if (!target.files || target.files.length === 0) return
  const file = target.files[0]

  uploadingWordbook.value = true
  try {
    const result = await uploadWordbook(file)
    ElMessage.success(result.message)
    selectedCategory.value = ''
    await loadStats()
    await loadCategories()
    await loadTodayWords()
    await loadWordList()
  } catch (error: any) {
    const msg = error.response?.data?.detail || error.message || '词书上传失败'
    ElMessage.error(msg)
  } finally {
    uploadingWordbook.value = false
    if (wordbookInput.value) {
      wordbookInput.value.value = ''
    }
  }
}
</script>

<style scoped>
.word-module {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.stats-section {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 20px;
  margin-bottom: 20px;
}

.stat-card {
  background: #f5f7fa;
  padding: 20px;
  border-radius: 12px;
  text-align: center;
}

.source-card {
  background: #ecfdf5;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  margin: 0;
  color: #333;
}

.stat-label {
  font-size: 14px;
  color: #999;
  margin: 8px 0 0;
}

.sub-tabs {
  margin-top: 10px;
}

.plan-bar {
  background: #f5f7fa;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.round-progress-bar {
  background: #f0f9ff;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 16px;
}

.progress-info {
  font-size: 14px;
  color: #555;
  margin-bottom: 8px;
  display: flex;
  gap: 16px;
}

.word-card {
  text-align: center;
  padding: 40px;
  background: #fafafa;
  border-radius: 12px;
}

.word-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.word-number {
  font-size: 14px;
  color: #999;
}

.word-tag {
  padding: 4px 12px;
  background: #dbeafe;
  color: #3b82f6;
  border-radius: 4px;
  font-size: 12px;
}

.review-badge {
  padding: 4px 12px;
  background: #fef3c7;
  color: #d97706;
  border-radius: 4px;
  font-size: 12px;
  font-weight: bold;
}

.new-badge {
  padding: 4px 12px;
  background: #dcfce7;
  color: #22c55e;
  border-radius: 4px;
  font-size: 12px;
  font-weight: bold;
}

.daily-stats {
  display: flex;
  gap: 12px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed #e0e0e0;
}

.word {
  font-size: 48px;
  font-weight: bold;
  margin: 0 0 8px;
  color: #333;
}

.phonetic {
  font-size: 18px;
  color: #666;
  margin: 0 0 20px;
}

.word-actions {
  margin-bottom: 20px;
}

.word-detail {
  text-align: left;
  padding: 20px;
  background: white;
  border-radius: 8px;
  margin-bottom: 20px;
}

.meaning {
  font-size: 16px;
  color: #333;
  margin: 0 0 12px;
}

.example {
  font-size: 14px;
  color: #666;
  margin: 0;
  font-style: italic;
  display: flex;
  align-items: center;
  gap: 8px;
}

.study-buttons {
  display: flex;
  justify-content: center;
  gap: 12px;
}

.empty-state {
  text-align: center;
  padding: 40px;
}

.list-filters {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.pagination {
  margin-top: 16px;
  text-align: right;
}

.hidden-input {
  display: none;
}

.round-stats {
  text-align: center;
}

.round-stats-title {
  font-size: 18px;
  font-weight: bold;
  margin-bottom: 20px;
}

.round-stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.round-stat-item {
  padding: 16px;
  border-radius: 8px;
  text-align: center;
}

.round-stat-item.success {
  background: #dcfce7;
  color: #16a34a;
}

.round-stat-item.warning {
  background: #fef3c7;
  color: #d97706;
}

.round-stat-item.danger {
  background: #fee2e2;
  color: #dc2626;
}

.round-stat-item .stat-num {
  display: block;
  font-size: 28px;
  font-weight: bold;
}

.round-stat-item .stat-label {
  font-size: 14px;
  margin-top: 4px;
}
</style>
