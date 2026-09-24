<template>
  <div class="push-module">
    <div class="module-header">
      <h3>弹卡背诵</h3>
      <p class="subtitle">像通知一样在角落弹出单词，边忙边背</p>
    </div>

    <div class="config-section">
      <el-form :inline="true">
        <el-form-item label="弹卡数量">
          <el-slider v-model="config.count" :min="5" :max="50" :step="5" style="width: 160px" />
          <span style="margin-left: 12px">{{ config.count }} 词</span>
        </el-form-item>
        <el-form-item label="间隔(秒)">
          <el-input-number v-model="config.interval_seconds" :min="15" :max="600" :step="15" />
        </el-form-item>
        <el-form-item label="自动发音">
          <el-switch v-model="config.auto_play" />
        </el-form-item>
        <el-form-item label="词汇分类">
          <el-select v-model="config.category" clearable placeholder="全部" style="width: 150px">
            <el-option v-for="cat in categories" :key="cat" :label="cat" :value="cat" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="running" @click="startSession">
            {{ running ? '背单词中…' : '开始弹卡' }}
          </el-button>
          <el-button v-if="running" type="danger" @click="stopSession">停止</el-button>
          <el-button @click="saveConfig">保存配置</el-button>
        </el-form-item>
      </el-form>
      <p v-if="!notifyGranted" class="notify-tip">
        <el-button size="small" type="info" @click="requestNotify">授权浏览器通知（页面后台时升级为系统通知）</el-button>
      </p>
    </div>

    <div v-if="running" class="run-info">
      <p>会话 {{ sessionId }}｜剩余 {{ queue.length }} 词｜已背 {{ doneCount }} 词</p>
      <el-progress :percentage="percent" :stroke-width="10" status="success" />
    </div>

    <!-- 悬浮弹卡 -->
    <Transition name="pop">
      <div v-if="showing && current" class="float-card">
        <div class="fc-top">
          <span class="fc-badge">{{ current.type === 'new' ? '新词' : current.type === 'review' ? '复习' : '学习' }}</span>
          <span class="fc-skip" @click="hideCard">×</span>
        </div>
        <div class="fc-word">{{ current.word }}</div>
        <div class="fc-phonetic">{{ current.phonetic }}</div>
        <div class="fc-meaning">{{ current.meaning }}</div>
        <div class="fc-buttons">
          <el-button size="small" type="danger" @click="rate('忘记')">忘记</el-button>
          <el-button size="small" type="warning" @click="rate('困难')">困难</el-button>
          <el-button size="small" type="info" @click="rate('一般')">一般</el-button>
          <el-button size="small" type="success" @click="rate('认识')">认识</el-button>
          <el-button size="small" @click="playWord"><el-icon><VideoPlay /></el-icon>发音</el-button>
        </div>
      </div>
    </Transition>

    <QuizDialog :visible="quizVisible" :word-ids="sessionWordIds" @close="quizVisible = false" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { VideoPlay } from '@element-plus/icons-vue'
import {
  getSessionCards, studyWord, completeSession,
  getPushConfig, savePushConfig, getWordCategories,
  type SessionCardItem, type PushConfig
} from '@/api/words'
import { useSpeech } from '@/composables/useSpeech'
import QuizDialog from '@/views/recitation/QuizDialog.vue'

const { speak: speakWord } = useSpeech()

const config = reactive<PushConfig>({ count: 10, interval_seconds: 60, category: null, auto_play: true })
const categories = ref<string[]>([])
const running = ref(false)
const sessionId = ref('')
const sessionWordIds = ref<number[]>([])
const queue = ref<SessionCardItem[]>([])
const doneCount = ref(0)
const current = ref<SessionCardItem | null>(null)
const showing = ref(false)
const timers: ReturnType<typeof setTimeout>[] = []
const notifyGranted = ref(false)
const quizVisible = ref(false)

const percent = computed(() => {
  const total = sessionWordIds.value.length
  return total ? Math.round((doneCount.value / total) * 100) : 0
})

function requestNotify() {
  if (!('Notification' in window)) {
    ElMessage.warning('当前浏览器不支持通知')
    return
  }
  Notification.requestPermission().then(p => {
    notifyGranted.value = p === 'granted'
    if (notifyGranted.value) ElMessage.success('通知已开启')
  })
}

async function loadConfig() {
  try {
    const cfg = await getPushConfig()
    Object.assign(config, cfg)
  } catch {
    // 使用默认
  }
  if (config.category === null || config.category === undefined) {
    config.category = ''
  }
}

async function loadCategories() {
  try {
    const res = await getWordCategories()
    categories.value = res.categories.filter(c => c !== '全部')
  } catch {
    categories.value = ['CET-4', 'CET-6', '考研']
  }
}

async function saveConfig() {
  try {
    await savePushConfig({ ...config, category: config.category || null })
    ElMessage.success('配置已保存')
  } catch {
    ElMessage.success('配置已保存')
  }
}

function clearTimers() {
  timers.forEach(t => clearTimeout(t))
  timers.length = 0
}

async function startSession() {
  if (running.value) return
  clearTimers()
  queue.value = []
  current.value = null
  showing.value = false
  doneCount.value = 0
  sessionWordIds.value = []

  const category = config.category || undefined
  try {
    const res = await getSessionCards(config.count, category)
    if (!res.cards.length) {
      ElMessage.warning('没有可背的单词了，换个分类或先学习')
      return
    }
    sessionId.value = res.session_id
    queue.value = [...res.cards]
    sessionWordIds.value = res.cards.map(c => c.word_id)
    running.value = true
    scheduleNext(0)
  } catch {
    ElMessage.error('获取弹卡队列失败')
  }
}

function later(ms: number, fn: () => void) {
  const t = setTimeout(() => {
    const idx = timers.indexOf(t)
    if (idx >= 0) timers.splice(idx, 1)
    fn()
  }, ms)
  timers.push(t)
}

async function showNextCard() {
  if (!running.value) return
  if (queue.value.length === 0) {
    await finishSession()
    return
  }
  current.value = queue.value[0]
  showing.value = true
  if (config.auto_play) playWord()
  if (document.hidden) {
    notifyHiddenCard(current.value)
  }
  later(8000, () => {
    showing.value = false
  })
}

function scheduleNext(delayMs: number) {
  later(delayMs, showNextCard)
}

function notifyHiddenCard(card: SessionCardItem) {
  if (notifyGranted.value && Notification.permission === 'granted') {
    const n = new Notification('弹卡背诵', {
      body: `${card.word}  ${card.phonetic || ''}\n${card.meaning}`,
      icon: '/favicon.ico'
    })
    n.onclick = () => window.focus()
  }
}

function playWord() {
  if (current.value?.word) speakWord(current.value.word, { lang: 'en-US' })
}

async function rate(rating: string) {
  if (!current.value) return
  const word = current.value
  showing.value = false
  doneCount.value++

  try {
    const updated = await studyWord(word.word_id, rating, {
      session_id: sessionId.value || undefined,
      source: 'push'
    })
    const kept = queue.value.shift()
    if (updated?.srs_status !== 'reviewed') {
      const dueMs = Math.round((updated?.due_minutes ?? 1) * 60 * 1000)
      later(dueMs, () => {
        if (kept && running.value) queue.value.push(kept)
      })
    }
  } catch {
    queue.value.shift()
  }

  scheduleNext(config.interval_seconds * 1000)
}

async function finishSession() {
  running.value = false
  showing.value = false
  current.value = null
  clearTimers()
  if (sessionId.value) {
    try {
      await completeSession(sessionId.value)
    } catch {
      // 忽略
    }
  }
  ElMessage.success('本轮弹卡完成！')
  if (sessionWordIds.value.length) {
    quizVisible.value = true
  }
}

function stopSession() {
  running.value = false
  showing.value = false
  current.value = null
  clearTimers()
  if (sessionId.value) {
    completeSession(sessionId.value)
  }
  ElMessage.info('已停止弹卡')
}

function hideCard() {
  showing.value = false
}

onMounted(async () => {
  await loadConfig()
  await loadCategories()
  notifyGranted.value = 'Notification' in window && Notification.permission === 'granted'
})

onUnmounted(() => {
  clearTimers()
})
</script>

<style scoped>
.push-module { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06); }
.module-header { margin-bottom: 16px; }
.module-header h3 { margin: 0 0 4px; font-size: 16px; color: #333; }
.subtitle { margin: 0; font-size: 14px; color: #999; }
.config-section { background: #f5f7fa; padding: 16px; border-radius: 8px; }
.notify-tip { margin-top: 8px; }
.run-info { margin-top: 16px; font-size: 13px; color: #666; }
.float-card { position: fixed; right: 24px; bottom: 32px; width: 320px; background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.16); padding: 16px; z-index: 3000; text-align: center; }
.fc-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.fc-badge { padding: 2px 8px; background: #dbeafe; color: #3b82f6; border-radius: 4px; font-size: 12px; }
.fc-skip { cursor: pointer; color: #999; font-size: 18px; }
.fc-word { font-size: 28px; font-weight: bold; color: #333; }
.fc-phonetic { font-size: 14px; color: #666; margin: 4px 0; }
.fc-meaning { font-size: 15px; color: #333; margin-bottom: 12px; }
.fc-buttons { display: flex; justify-content: center; gap: 6px; flex-wrap: wrap; }
.pop-enter-active, .pop-leave-active { transition: opacity 0.25s ease, transform 0.25s ease; }
.pop-enter-from { opacity: 0; transform: translateY(12px); }
.pop-leave-to { opacity: 0; }
</style>