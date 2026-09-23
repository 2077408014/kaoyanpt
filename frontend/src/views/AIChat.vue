<template>
  <div class="ai-chat">
    <div class="chat-container">
      <div class="chat-header">
        <h2>AI智能助手</h2>
        <div class="header-actions">
          <el-button type="text" @click="goToConfig">
            <el-icon><Tools /></el-icon>AI配置
          </el-button>
          <el-button type="text" @click="handleClearHistory">
            <el-icon><Delete /></el-icon>清除记录
          </el-button>
        </div>
      </div>
      <div ref="chatContainerRef" class="chat-messages">
        <div v-for="msg in messages" :key="msg.id" class="message" :class="msg.role">
          <div class="avatar">
            <el-icon v-if="msg.role === 'user'"><User /></el-icon>
            <el-icon v-else><Message /></el-icon>
          </div>
          <div class="content">
            <p v-if="msg.role === 'user'">{{ msg.content }}</p>
            <div v-else class="ai-content" v-html="renderMarkdown(msg.content)"></div>
            <div v-if="msg.role === 'ai'" class="message-meta">
              <span v-if="msg.fromKnowledgeBase" class="knowledge-badge">
                <el-icon><DataLine /></el-icon>知识库
              </span>
              <el-tag v-if="msg.source && msg.source !== 'AI系统' && msg.source !== '调用失败'" size="small" type="info" effect="plain" class="ai-name-tag">
                <el-icon><Cpu /></el-icon>{{ msg.source }}
              </el-tag>
              <el-tag v-else-if="msg.source === '调用失败'" size="small" type="danger" effect="plain" class="ai-name-tag">
                <el-icon><WarningFilled /></el-icon>{{ msg.source }}
              </el-tag>
              <span v-else-if="msg.source" class="source">{{ msg.source }}</span>
              <el-button
                v-if="msg.lastUserMessage"
                size="small"
                :type="msg.failed ? 'primary' : 'default'"
                text
                class="regenerate-btn"
                :loading="regeneratingIds[msg.id]"
                :disabled="loading"
                @click="regenerateMessage(msg)"
              >
                <el-icon><RefreshRight /></el-icon>{{ msg.failed ? '重新生成' : '重新回答' }}
              </el-button>
            </div>
          </div>
        </div>
        <div v-if="suggestions.length > 0" class="suggestions">
          <el-tag
            v-for="(suggestion, index) in suggestions"
            :key="index"
            size="small"
            type="info"
            @click="sendSuggestion(suggestion)"
          >
            {{ suggestion }}
          </el-tag>
        </div>
      </div>
      <div class="chat-input">
        <div class="input-row">
          <el-input
            v-model="inputMessage"
            placeholder="输入你的问题或指令..."
            type="textarea"
            :rows="2"
            :disabled="loading"
            @keyup.enter="handleSend"
          />
          <el-button type="primary" @click="handleSend" :loading="loading" class="send-btn">
            <el-icon><Refresh /></el-icon>发送
          </el-button>
        </div>
      </div>
    </div>
    <div class="sidebar">
      <div class="quick-commands">
        <h3>快捷指令</h3>
        <div class="command-buttons">
          <el-button @click="sendCommand('打开错题模块')">打开错题模块</el-button>
          <el-button @click="sendCommand('开始今日单词复习')">开始今日单词复习</el-button>
          <el-button @click="sendCommand('推荐10道高数微分方程题目')">推荐10道题目</el-button>
          <el-button @click="sendCommand('分析我的薄弱知识点')">分析薄弱知识点</el-button>
        </div>
      </div>
      <div class="usage-tips">
        <h3>使用提示</h3>
        <ul>
          <li>支持自然语言指令，如："打开错题模块"、"开始复习"</li>
          <li>可以提问考研相关问题，如："什么是微积分？"</li>
          <li>支持多轮对话，系统会记住上下文</li>
          <li>答案来源会标注（本地资料/网络资源）</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Message, Delete, Refresh, Tools, Cpu, RefreshRight, WarningFilled } from '@element-plus/icons-vue'
import { command } from '../api/ai'
import { agentChat, getAgentHistory, clearAgentHistory } from '../api/agent'
import { marked } from 'marked'
import katex from 'katex'
import 'katex/dist/katex.min.css'

marked.setOptions({
  breaks: true,
  gfm: true
})

const router = useRouter()
const messages = ref<any[]>([])
const inputMessage = ref('')
const loading = ref(false)
const suggestions = ref<string[]>([])
const chatContainerRef = ref<HTMLElement | null>(null)
const lastSentTime = ref(0)
const regeneratingIds = ref<Record<string | number, boolean>>({})

function goToConfig() {
  router.push('/dashboard/ai-config')
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
  let result = formula
  
  // 修正常见的 AI 拼写错误：inftyty, infinity 等 -> \infty
  result = result.replace(/\\?inftyty/g, '\\infty')
  result = result.replace(/\\?infinity/g, '\\infty')
  
  result = result.replace(/\\lim_\{([^}]+)\}/g, '\\lim_{$1}')
  result = result.replace(/\\lim\s*\{([^}]+)\}/g, '\\lim_{$1}')
  result = result.replace(/lim_\(([^)]+)\)/g, '\\lim_{$1}')
  result = result.replace(/lim_\(([^)]+)\)/g, '\\lim_{$1}')
  result = result.replace(/lim\s*([a-zA-Z]+)\s*[-→]\s*([0-9a-zA-Z]+)/g, '\\lim_{$1 \\to $2}')
  
  result = result.replace(/\\frac\{([^}]+)\}\{([^}]+)\}/g, '\\frac{$1}{$2}')
  result = result.replace(/\\frac\(([^)]+)\)\(([^)]+)\)/g, '\\frac{$1}{$2}')
  
  const mathCommands = ['sin', 'cos', 'tan', 'cot', 'sec', 'csc', 'ln', 'log', 'sqrt', 'int', 'sum', 'to', 'cdot', 'infty', 'alpha', 'beta', 'gamma', 'delta', 'epsilon', 'theta', 'lambda', 'mu', 'pi', 'rho', 'sigma', 'phi', 'psi', 'omega']
  for (const cmd of mathCommands) {
    const regex = new RegExp(`\\\\${cmd}`, 'g')
    result = result.replace(regex, `\\${cmd}`)
  }
  
  result = result.replace(/\^\{([^}]+)\}/g, '^{$1}')
  result = result.replace(/\^([a-zA-Z0-9]+)/g, '^{$1}')
  result = result.replace(/_\{([^}]+)\}/g, '_{$1}')
  result = result.replace(/_([a-zA-Z0-9]+)/g, '_{$1}')
  
  result = result.replace(/\*/g, ' \\cdot ')
  
  // 精确替换独立的 inf 为 \infty，避免误伤 \infty, \int 等
  // 替换 "_inf" -> "_{\infty}"
  result = result.replace(/_\s*inf\b/g, '_{\\infty}')
  // 替换 "\to inf" -> "\to \infty"
  result = result.replace(/\\to\s+inf\b/g, '\\to \\infty')
  // 替换开头或单独的 "inf" -> "\infty" (但不替换 \infty 或 \int 中的 inf)
  result = result.replace(/(?<!\\)inf\b/g, '\\infty')
  
  return result.trim()
}

function renderMarkdown(text: string): string {
  let result = text || ''
  
  const mathBlocks: { placeholder: string; html: string }[] = []
  
  const addMathBlock = (formula: string, displayMode: boolean): string => {
    const normalized = normalizeLatex(formula)
    const html = renderMathFormula(normalized, displayMode)
    const placeholder = `@@MATH_${displayMode ? 'BLOCK' : 'INLINE'}_${mathBlocks.length}@@`
    mathBlocks.push({ placeholder, html })
    return placeholder
  }
  
  result = result.replace(/\$\$(.*?)\$\$/gms, (_, formula) => {
    const trimmedFormula = formula.trim()
    if (!trimmedFormula) return '$$'
    return addMathBlock(trimmedFormula, true)
  })
  
  result = result.replace(/(?<!\\)\$(.*?)(?<!\\)\$/g, (_, formula) => {
    const trimmedFormula = formula.trim()
    if (!trimmedFormula) return '$'
    if (trimmedFormula.length > 100) {
      return addMathBlock(trimmedFormula, true)
    }
    return addMathBlock(trimmedFormula, false)
  })
  
  result = result.replace(/\\\((.*?)\\\)/g, (_, formula) => {
    const trimmedFormula = formula.trim()
    if (!trimmedFormula) return '\\()'
    return addMathBlock(trimmedFormula, false)
  })
  
  result = result.replace(/\\\[([\s\S]*?)\\\]/g, (_, formula) => {
    const trimmedFormula = formula.trim()
    if (!trimmedFormula) return '\\[]'
    return addMathBlock(trimmedFormula, true)
  })
  
  result = result.replace(/\[([\s\S]*?)\]/g, (_, formula) => {
    const trimmedFormula = formula.trim()
    if (!trimmedFormula) return '[]'
    if (trimmedFormula.includes('\\') || trimmedFormula.includes('lim') || trimmedFormula.includes('frac') || trimmedFormula.includes('int') || trimmedFormula.includes('sum') || trimmedFormula.includes('sin') || trimmedFormula.includes('cos') || trimmedFormula.includes('tan')) {
      return addMathBlock(trimmedFormula, true)
    }
    return '[' + trimmedFormula + ']'
  })
  
  const mathPattern = /((?:\\frac\{[^}]+\}\{[^}]+\})|(?:\\lim\{[^}]+\})|(?:\\int[^}]+)|(?:\\sum[^}]+)|(?:\\sin|\\cos|\\tan|\\cot|\\sec|\\csc|\\ln|\\log|\\exp|\\sqrt)\s*\([^)]+\)|(?:\\alpha|\\beta|\\gamma|\\delta|\\epsilon|\\zeta|\\eta|\\theta|\\iota|\\kappa|\\lambda|\\mu|\\nu|\\xi|\\pi|\\rho|\\sigma|\\tau|\\upsilon|\\phi|\\chi|\\psi|\\omega|\\Delta|\\Gamma|\\Theta|\\Lambda|\\Xi|\\Pi|\\Sigma|\\Upsilon|\\Phi|\\Psi|\\Omega))/gi
  
  result = result.replace(mathPattern, (match) => {
    if (match.includes('@@MATH_')) return match
    const isDisplayMode = match.length > 50 || match.includes('lim') || match.includes('int') || match.includes('sum') || match.includes('frac')
    return addMathBlock(match, isDisplayMode)
  })
  
  const simpleMathPattern = /((?:\\frac\{[^}]+\}\{[^}]+\})|(?:\\lim\{[^}]+\})|(?:\\int[^}]+)|(?:\\sum[^}]+)|(?:\\sin|\\cos|\\tan|\\cot|\\sec|\\csc|\\ln|\\log|\\exp|\\sqrt)\s*\([^)]+\))/gi
  
  result = result.replace(simpleMathPattern, (match) => {
    if (match.includes('@@MATH_')) return match
    const isDisplayMode = match.length > 50 || match.includes('lim') || match.includes('int') || match.includes('sum') || match.includes('frac')
    return addMathBlock(match, isDisplayMode)
  })
  
  const parsedMarkdown = marked.parse(result)
  if (parsedMarkdown) {
    result = parsedMarkdown as string
  }
  
  mathBlocks.forEach(({ placeholder, html }) => {
    result = result.split(placeholder).join(html)
  })
  
  return result
}

async function loadHistory() {
  try {
    const history = await getAgentHistory('ai-qa', 50)
    const list = history.map(msg => ({
      id: msg.id,
      role: msg.message_type === 'question' ? 'user' : 'ai',
      content: msg.content,
      source: msg.source,
      lastUserMessage: ''
    }))

    // 为每条 AI 消息关联它前一条用户消息，便于"重新回答"
    let prevUser = ''
    for (const item of list) {
      if (item.role === 'user') {
        prevUser = item.content
      } else if (item.role === 'ai') {
        item.lastUserMessage = prevUser
      }
    }

    messages.value = list

    if (messages.value.length === 0) {
      messages.value.push({
        id: 1,
        role: 'ai',
        content: '你好！我是考研复习平台的AI助手。请问有什么我可以帮你的？',
        source: 'AI系统',
        lastUserMessage: ''
      })
    }
  } catch {
    messages.value.push({
      id: 1,
      role: 'ai',
      content: '你好！我是考研复习平台的AI助手。请问有什么我可以帮你的？',
      source: 'AI系统',
      lastUserMessage: ''
    })
  }
}

async function handleSend() {
  if (!inputMessage.value.trim() || loading.value) {
    if (!inputMessage.value.trim()) {
      ElMessage.warning('请输入内容')
    }
    return
  }

  const now = Date.now()
  if (now - lastSentTime.value < 500) {
    return
  }

  const userMsg = inputMessage.value.trim()

  loading.value = true
  inputMessage.value = ''
  lastSentTime.value = now

  const lastMessage = messages.value[messages.value.length - 1]
  if (lastMessage && lastMessage.role === 'user' && lastMessage.content === userMsg) {
    loading.value = false
    return
  }

  messages.value.push({
    id: Date.now(),
    role: 'user',
    content: userMsg
  })

  suggestions.value = []

  try {
    const result = await agentChat({ agent_name: 'ai-qa', message: userMsg })

    messages.value.push({
      id: Date.now() + 1,
      role: 'ai',
      content: result.answer || '暂无回答',
      source: result.source || 'AI',
      fromKnowledgeBase: false,
      lastUserMessage: userMsg
    })

    handleRouteNavigation(userMsg)
  } catch (error: any) {
    const errorMsg = error.response?.data?.detail || error.message || '抱歉，我暂时无法回答这个问题。'
    messages.value.push({
      id: Date.now() + 1,
      role: 'ai',
      content: errorMsg,
      source: '调用失败',
      fromKnowledgeBase: false,
      failed: true,
      lastUserMessage: userMsg
    })
  } finally {
    loading.value = false
  }
}

async function regenerateMessage(failedMsg: any) {
  const userMsg = failedMsg.lastUserMessage
  if (!userMsg) {
    ElMessage.warning('没有可重新生成的问题')
    return
  }
  if (loading.value || regeneratingIds.value[failedMsg.id]) return

  regeneratingIds.value[failedMsg.id] = true

  try {
    const result = await agentChat({ agent_name: 'ai-qa', message: userMsg })

    const newMsg = {
      id: Date.now() + 1,
      role: 'ai',
      content: result.answer || '暂无回答',
      source: result.source || 'AI',
      fromKnowledgeBase: false,
      lastUserMessage: userMsg
    }

    // 替换原失败/旧回答
    const idx = messages.value.findIndex(m => m.id === failedMsg.id)
    if (idx >= 0) {
      messages.value.splice(idx, 1, newMsg)
    } else {
      messages.value.push(newMsg)
    }
  } catch (error: any) {
    const errorMsg = error.response?.data?.detail || error.message || '抱歉，我暂时无法回答这个问题。'
    const errorAiMsg = {
      id: Date.now() + 1,
      role: 'ai',
      content: errorMsg,
      source: '调用失败',
      fromKnowledgeBase: false,
      failed: true,
      lastUserMessage: userMsg
    }
    const idx = messages.value.findIndex(m => m.id === failedMsg.id)
    if (idx >= 0) {
      messages.value.splice(idx, 1, errorAiMsg)
    } else {
      messages.value.push(errorAiMsg)
    }
  } finally {
    regeneratingIds.value[failedMsg.id] = false
  }
}

function handleRouteNavigation(userMessage: string) {
  const commands: Array<{ keywords: string[]; route: string }> = [
    { keywords: ['打开错题', '去错题', '错题管理', '跳转错题'], route: '/dashboard/mistakes' },
    { keywords: ['打开单词', '去单词', '背诵中心', '单词复习', '跳转单词'], route: '/dashboard/words' },
    { keywords: ['打开推荐', '去推荐', '智能推荐', '跳转推荐', '生成推荐'], route: '/dashboard/recommend' },
    { keywords: ['打开报告', '去报告', '学习报告', '跳转报告'], route: '/dashboard/report' },
    { keywords: ['打开首页', '去首页', '跳转首页'], route: '/dashboard' },
    { keywords: ['打开资料', '去资料', '资料管理', '跳转资料'], route: '/dashboard/resources' },
    { keywords: ['打开ai配置', 'ai配置', '跳转ai配置'], route: '/dashboard/ai-config' }
  ]
  
  const lowerMessage = userMessage.toLowerCase()
  for (const cmd of commands) {
    if (cmd.keywords.some(kw => lowerMessage.includes(kw))) {
      router.push(cmd.route)
      break
    }
  }
}

async function sendCommand(cmd: string) {
  inputMessage.value = cmd
  
  try {
    const result = await command(cmd)
    
    messages.value.push({
      id: Date.now(),
      role: 'user',
      content: cmd
    })
    
    messages.value.push({
      id: Date.now() + 1,
      role: 'ai',
      content: result.message,
      source: '指令系统',
      fromKnowledgeBase: false
    })
    
    if (result.action === 'open_mistakes') {
      setTimeout(() => router.push('/dashboard/mistakes'), 1000)
    } else if (result.action === 'start_recitation') {
      setTimeout(() => router.push('/dashboard/words'), 1000)
    } else if (result.action === 'generate_recommendation') {
      setTimeout(() => router.push('/dashboard/recommend'), 1000)
    } else if (result.action === 'analyze_weak_points') {
      setTimeout(() => router.push('/dashboard/recommend'), 1000)
    } else if (result.action === 'generate_report') {
      setTimeout(() => router.push('/dashboard/report'), 1000)
    }
  } catch {
    // ignore
  }
}

function sendSuggestion(suggestion: string) {
  inputMessage.value = suggestion
  handleSend()
}

async function handleClearHistory() {
  try {
    await clearAgentHistory('ai-qa')
    messages.value = [{
      id: 1,
      role: 'ai',
      content: '你好！我是考研复习平台的AI助手。请问有什么我可以帮你的？',
      source: 'AI系统',
      lastUserMessage: ''
    }]
    ElMessage.success('聊天记录已清除')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '清除失败')
  }
}

onMounted(() => {
  loadHistory()
})
</script>

<style scoped>
.ai-chat {
  padding: 20px;
  display: flex;
  gap: 20px;
  min-height: calc(100vh - 80px);
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e0e0e0;
}

.chat-header h2 {
  margin: 0;
  font-size: 18px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.chat-messages {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

.message {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.message.user {
  flex-direction: row-reverse;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.message.user .avatar {
  background: #667eea;
  color: white;
}

.message.ai .avatar {
  background: #f0f0f0;
  color: #666;
}

.content {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
}

.message.user .content {
  background: #667eea;
  color: white;
  border-radius: 12px 0 12px 12px;
}

.message.ai .content {
  background: #f5f7fa;
  color: #333;
  border-radius: 0 12px 12px 12px;
}

.content p {
  margin: 0;
  line-height: 1.6;
}

.ai-content {
  line-height: 1.8;
}

.ai-content h1,
.ai-content h2,
.ai-content h3 {
  margin: 12px 0 8px;
  font-weight: 600;
}

.ai-content h1 {
  font-size: 18px;
}

.ai-content h2 {
  font-size: 16px;
}

.ai-content h3 {
  font-size: 14px;
}

.ai-content ul,
.ai-content ol {
  margin: 8px 0;
  padding-left: 24px;
}

.ai-content li {
  margin-bottom: 4px;
}

.ai-content strong {
  font-weight: 600;
  color: #667eea;
}

.ai-content code {
  background: rgba(0, 0, 0, 0.06);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
}

.ai-content pre {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
}

.ai-content pre code {
  background: none;
  padding: 0;
}

.message-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}

.knowledge-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  background: #e8f5e9;
  color: #2e7d32;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.knowledge-badge .el-icon {
  font-size: 12px;
}

.source {
  font-size: 12px;
  color: #999;
}

.message.user .source {
  color: rgba(255, 255, 255, 0.7);
}

.ai-name-tag {
  font-size: 11px;
}

.ai-name-tag .el-icon {
  margin-right: 3px;
  font-size: 11px;
}

.regenerate-btn {
  font-size: 12px;
  margin-left: 4px;
  padding: 2px 8px;
}

.regenerate-btn .el-icon {
  font-size: 12px;
  margin-right: 2px;
}

.suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
  padding-left: 52px;
}

.suggestions .el-tag {
  cursor: pointer;
}

.chat-input {
  padding: 20px;
  border-top: 1px solid #e0e0e0;
}

.input-row {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.input-row .el-textarea {
  flex: 1;
}

.send-btn {
  height: 40px;
  flex-shrink: 0;
}

.sidebar {
  width: 300px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.quick-commands,
.usage-tips {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.quick-commands h3,
.usage-tips h3 {
  margin: 0 0 16px;
  font-size: 16px;
  color: #333;
}

.command-buttons {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.command-buttons .el-button {
  text-align: left;
}

.usage-tips ul {
  margin: 0;
  padding-left: 20px;
}

.usage-tips li {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

.ai-content .katex {
  font-size: 1.1em;
}

.ai-content .katex-display {
  margin: 12px 0;
  overflow-x: auto;
  overflow-y: hidden;
}

.ai-content .katex-display::-webkit-scrollbar {
  height: 6px;
}

.ai-content .katex-display::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.ai-content .katex-display::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.ai-content .katex-display::-webkit-scrollbar-thumb:hover {
  background: #a1a1a1;
}

.math-error {
  color: #e74c3c;
  font-family: monospace;
  background: #fef5f5;
  padding: 2px 4px;
  border-radius: 3px;
}
</style>
