<template>
  <div class="resource-chat-container">
    <div class="chat-header">
      <h3>🤖 AI资料检索</h3>
      <el-button text size="small" @click="handleClear">清除记录</el-button>
    </div>
    <div ref="chatContainerRef" class="chat-messages">
      <div v-if="messages.length === 0" class="welcome-message">
        <p>提问关于已上传资料的问题，系统将检索知识库并用AI组织回答。</p>
      </div>
      <div v-for="(msg, idx) in messages" :key="idx" class="message" :class="msg.role">
        <div class="avatar">
          <el-icon v-if="msg.role === 'user'"><User /></el-icon>
          <el-icon v-else><Message /></el-icon>
        </div>
        <div class="content">
          <p v-if="msg.role === 'user'">{{ msg.content }}</p>
          <div v-else class="ai-content" v-html="renderMarkdown(msg.content)"></div>
          <div v-if="msg.role === 'ai'" class="message-meta">
            <el-tag v-if="msg.source === '知识库'" size="small" type="success">知识库</el-tag>
            <el-tag v-else-if="msg.source === 'AI'" size="small" type="info">AI回答</el-tag>
            <span v-if="msg.source" class="source-text">{{ msg.source }}</span>
          </div>
          <div v-if="msg.role === 'ai' && msg.chunks && msg.chunks.length > 0" class="chunks">
            <el-collapse>
              <el-collapse-item title="参考来源" name="chunks">
                <div v-for="(chunk, ci) in msg.chunks.slice(0, 3)" :key="ci" class="chunk-item">
                  <div class="chunk-header">
                    <el-tag size="small" :type="getScoreType(chunk.similarity)">{{ (chunk.similarity * 100).toFixed(0) }}%</el-tag>
                    <span class="chunk-filename">{{ chunk.metadata?.filename || '未知文档' }}</span>
                  </div>
                  <div class="chunk-text">{{ truncate(chunk.content, 120) }}</div>
                </div>
              </el-collapse-item>
            </el-collapse>
          </div>
        </div>
      </div>
    </div>
    <div class="chat-input">
      <el-select v-model="subjectFilter" placeholder="全部学科" clearable style="width: 130px; margin-right: 8px" size="small">
        <el-option label="全部" value="" />
        <el-option v-for="s in SUBJECTS" :key="s" :label="s" :value="s" />
      </el-select>
      <el-input
        v-model="inputMessage"
        placeholder="输入关于资料的问题..."
        :disabled="loading"
        @keyup.enter="handleSend"
      />
      <el-button type="primary" @click="handleSend" :loading="loading">发送</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { User, Message } from '@element-plus/icons-vue'
import { agentChat, getAgentHistory, clearAgentHistory } from '../../api/agent'
import katex from 'katex'
import 'katex/dist/katex.min.css'

const SUBJECTS = ['数学', '英语', '政治', '马原', '毛中特', '史纲', '思修', '时政', '专业课']

const messages = ref<any[]>([])
const inputMessage = ref('')
const loading = ref(false)
const subjectFilter = ref('')
const chatContainerRef = ref<HTMLElement | null>(null)
const AGENT_NAME = 'resource-qa'

onMounted(async () => {
  await loadHistory()
})

async function loadHistory() {
  try {
    const history = await getAgentHistory(AGENT_NAME, 50)
    messages.value = history.map((m: any) => ({
      role: m.message_type === 'question' ? 'user' : 'ai',
      content: m.content,
      source: m.source,
      chunks: m.relevant_chunks || []
    }))
  } catch { /* ignore */ }
}

async function handleSend() {
  const msg = inputMessage.value.trim()
  if (!msg || loading.value) return

  messages.value.push({ role: 'user', content: msg })
  inputMessage.value = ''
  loading.value = true

  try {
    const result = await agentChat({
      agent_name: AGENT_NAME,
      message: msg,
      subject: subjectFilter.value || undefined
    })
    messages.value.push({
      role: 'ai',
      content: result.answer,
      source: result.source,
      chunks: result.relevant_chunks || []
    })
  } catch (e: any) {
    const detail = e.response?.data?.detail || '请求失败'
    messages.value.push({ role: 'ai', content: `错误: ${detail}`, source: 'error', chunks: [] })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

function scrollToBottom() {
  setTimeout(() => {
    if (chatContainerRef.value) {
      chatContainerRef.value.scrollTop = chatContainerRef.value.scrollHeight
    }
  }, 100)
}

async function handleClear() {
  await clearAgentHistory(AGENT_NAME)
  messages.value = []
  ElMessage.success('历史已清除')
}

function truncate(text: string, maxLen: number): string {
  if (!text || text.length <= maxLen) return text || ''
  return text.slice(0, maxLen) + '...'
}

function getScoreType(similarity: number): string {
  if (similarity >= 0.8) return 'success'
  if (similarity >= 0.5) return 'warning'
  return 'danger'
}

function renderMathFormula(formula: string, displayMode: boolean): string {
  try {
    return katex.renderToString(formula.trim(), {
      displayMode,
      throwOnError: false,
      strict: false,
      trust: true
    })
  } catch {
    return `<span class="math-error">${displayMode ? '$$' : '$'}${formula.trim()}${displayMode ? '$$' : '$'}</span>`
  }
}

function normalizeLatex(formula: string): string {
  return formula
    .replace(/\\[Ll]im/g, '\\lim')
    .replace(/\\([Ss]um|[Pp]rod|[Ii]nt)/g, '\\$1')
    .replace(/\\[Ff]rac/g, '\\frac')
    .replace(/\\[Ss]qrt/g, '\\sqrt')
    .replace(/\\[Aa]lpha/g, '\\alpha')
    .replace(/\\[Bb]eta/g, '\\beta')
    .replace(/\\[Gg]amma/g, '\\gamma')
    .replace(/\\[Dd]elta/g, '\\delta')
    .replace(/\\[Pp]i/g, '\\pi')
    .replace(/\\[Tt]heta/g, '\\theta')
    .replace(/\\[Ii]nfty/g, '\\infty')
    .replace(/\\[Rr]ightarrow/g, '\\rightarrow')
    .replace(/\\[Ll]eftarrow/g, '\\leftarrow')
    .replace(/\\[Tt]o/g, '\\to')
    // ∞ 拼写错误兜底（含空格连写）
    .replace(/\\inf\s*i\s*t\s*[yi]/g, '\\infty')
    .replace(/(^|[^A-Za-z])inf\s*i\s*t\s*y(?![A-Za-z])/g, '$1\\infty')
    .replace(/(^|[^A-Za-z])inf\s*it\s*y(?![A-Za-z])/g, '$1\\infty')
    .replace(/(^|[^A-Za-z])inf\s*in\s*ity(?![A-Za-z])/g, '$1\\infty')
    .replace(/inf\s*ty/g, '\\infty')
    .replace(/infinity/g, '\\infty')
    .replace(/inf\b/g, '\\infty')
    .replace(/->/g, '\\to')
    .replace(/→/g, '\\to')
    .replace(/\*/g, ' \\cdot ')
}

function renderMarkdown(text: string): string {
  if (!text) return ''

  let result = text

  const mathBlocks: { placeholder: string; html: string }[] = []

  const addMathBlock = (formula: string, displayMode: boolean): string => {
    const normalized = normalizeLatex(formula)
    try {
      const html = renderMathFormula(normalized, displayMode)
      const placeholder = `XMK${mathBlocks.length}MKX`
      mathBlocks.push({ placeholder, html })
      return placeholder
    } catch {
      return displayMode ? `$$${formula}$$` : `$${formula}$`
    }
  }

  result = result.replace(/\$\$([\s\S]*?)\$\$/g, (_, formula) => {
    const trimmed = formula.trim()
    if (!trimmed) return '$$'
    return addMathBlock(trimmed, true)
  })

  result = result.replace(/\$([^\$\n]+?)\$/g, (_, formula) => {
    const trimmed = formula.trim()
    if (!trimmed) return '$'
    if (trimmed.length > 80) {
      return addMathBlock(trimmed, true)
    }
    return addMathBlock(trimmed, false)
  })

  result = result
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/^### (.*$)/gm, '<h3>$1</h3>')
    .replace(/^## (.*$)/gm, '<h2>$1</h2>')
    .replace(/^# (.*$)/gm, '<h1>$1</h1>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br>')

  mathBlocks.forEach(({ placeholder, html }) => {
    result = result.split(placeholder).join(html)
  })

  return result
}

defineExpose({ handleClear })
</script>

<style scoped>
.resource-chat-container {
  display: flex;
  flex-direction: column;
  flex: 1;
  width: 100%;
  height: 100%;
  min-height: 500px;
  overflow: hidden;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
}
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #e4e7ed;
  background: #fafafa;
}
.chat-header h3 {
  margin: 0;
  font-size: 15px;
}
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}
.welcome-message {
  text-align: center;
  padding: 40px 20px;
  color: #909399;
}
.welcome-message h3 { margin: 0 0 8px; font-size: 18px; }
.message {
  margin-bottom: 20px;
  display: flex;
  gap: 12px;
  align-items: flex-start;
}
.message.ai { flex-direction: row; }
.message.user { flex-direction: row-reverse; }
.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.message.ai .avatar { background: #e6f7ff; color: #1890ff; }
.message.user .avatar { background: #1890ff; color: #fff; }
.content {
  max-width: calc(100% - 44px);
  padding: 12px 16px;
  border-radius: 8px;
  line-height: 1.7;
  box-sizing: border-box;
  word-break: break-word;
}
.message.ai .content {
  width: calc(100% - 44px);
  background: #f0f5ff;
}
.message.user .content {
  width: auto;
  background: #1890ff;
  color: #fff;
  display: inline-block;
  max-width: calc(100% - 44px);
}
.message-meta { margin-top: 6px; display: flex; align-items: center; gap: 6px; }
.source-text { font-size: 12px; color: #909399; }
.chunks { margin-top: 12px; }
.chunk-item { font-size: 13px; margin-bottom: 8px; padding: 8px; background: #f5f7fa; border-radius: 4px; }
.chunk-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.chunk-filename { font-size: 12px; color: #909399; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chunk-text { color: #606266; }

/* AI 回答内容的段落与列表间距 */
.content :deep(p) {
  margin: 0 0 12px 0;
}
.content :deep(p:last-child) {
  margin-bottom: 0;
}
.content :deep(h1),
.content :deep(h2),
.content :deep(h3) {
  margin: 16px 0 10px 0;
  line-height: 1.4;
}
.content :deep(strong) {
  font-weight: 600;
}
/* 行内间距：让 <br> 产生明显换行间距 */
.content :deep(br) {
  display: block;
  margin: 8px 0;
  content: "";
}
/* 有序/无序列表（如果 AI 输出用了） */
.content :deep(ol),
.content :deep(ul) {
  margin: 10px 0;
  padding-left: 24px;
}
.content :deep(li) {
  margin-bottom: 8px;
  line-height: 1.7;
}
/* KaTeX 块级公式间距 */
.content :deep(.katex-display) {
  margin: 14px 0;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 4px 0;
}
/* 行内公式微调 */
.content :deep(.katex) {
  display: inline;
}
/* 参考来源折叠区 */
.chat-input {
  display: flex;
  padding: 12px;
  border-top: 1px solid #e4e7ed;
  background: #fafafa;
  gap: 8px;
}
.chat-input .el-input { flex: 1; }
:deep(.el-collapse) { border: none; }
:deep(.el-collapse-item__header) { font-size: 13px; }
:deep(.el-collapse-item__content) { padding-bottom: 8px; }
</style>
