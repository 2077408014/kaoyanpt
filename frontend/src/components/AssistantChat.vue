<template>
  <div class="assistant-page">
    <div class="chat-header">
      <div class="header-title">{{ title }}</div>
      <div class="header-actions">
        <el-button link type="primary" @click="goToConfig">
          <el-icon><Tools /></el-icon> AI 配置
        </el-button>
        <el-button link type="danger" @click="handleClearHistory">
          <el-icon><Delete /></el-icon> 清空记录
        </el-button>
      </div>
    </div>
    <div ref="bodyRef" class="chat-body">
      <div v-if="messages.length === 0" class="welcome">
        <el-icon class="welcome-icon"><ChatDotRound /></el-icon>
        <div class="welcome-title">{{ title }}</div>
        <div class="welcome-text">{{ welcome }}</div>
        <div class="suggestions">
          <div
            v-for="s in suggestions"
            :key="s"
            class="suggestion-chip"
            @click="send(s)"
          >{{ s }}</div>
        </div>
      </div>

      <div
        v-for="m in messages"
        :key="m.id"
        class="msg-row"
        :class="m.role === 'user' ? 'is-user' : 'is-ai'"
      >
        <div class="bubble" :class="{ error: m.error }">
          <template v-if="m.action">
            <div class="action-head">
              <el-icon><UserFilled /></el-icon>
              请确认以下教师账号信息（可修改）
            </div>
            <el-form label-width="72px" class="action-form" @submit.prevent>
              <el-form-item label="用户名">
                <el-input v-model="m.action.username" :disabled="m.actionStatus !== 'pending'" />
              </el-form-item>
              <el-form-item label="邮箱">
                <el-input v-model="m.action.email" :disabled="m.actionStatus !== 'pending'" />
              </el-form-item>
              <el-form-item label="初始密码">
                <el-input v-model="m.action.password" :disabled="m.actionStatus !== 'pending'" />
              </el-form-item>
            </el-form>
            <div class="action-tip">创建后该教师首次登录需修改密码。</div>
            <div v-if="m.actionStatus === 'pending'" class="action-btns">
              <el-button size="small" @click="dismissAction(m)">取消</el-button>
              <el-button size="small" type="primary" :loading="m.actionStatus === 'pending' && actionLoadingId === m.id" @click="confirmCreateTeacher(m)">
                确认创建
              </el-button>
            </div>
            <div v-else-if="m.actionStatus === 'done'" class="action-result ok">
              <el-icon><CircleCheckFilled /></el-icon> {{ m.actionMsg }}
            </div>
            <div v-else class="action-result fail">
              <el-icon><CircleCloseFilled /></el-icon> {{ m.actionMsg }}
            </div>
          </template>
          <template v-else>
            <div v-if="m.html" class="md" v-html="m.html"></div>
            <div v-else-if="m.streaming" class="typing">正在思考<span class="dots">…</span></div>
          </template>
        </div>
      </div>
    </div>

    <div class="chat-input">
      <el-input
        v-model="draft"
        type="textarea"
        :rows="2"
        resize="none"
        :placeholder="sending ? 'AI 正在回复…' : '输入你的问题，Enter 发送，Shift+Enter 换行'"
        @keydown.enter.exact.prevent="send()"
      />
      <div class="input-bar">
        <span class="input-hint">AI 回答基于平台实时数据，仅供参考</span>
        <el-button type="primary" :loading="sending" @click="send()">发送</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ChatDotRound, CircleCheckFilled, CircleCloseFilled, Delete, Tools, UserFilled } from '@element-plus/icons-vue';
import { ref, nextTick, watch, onBeforeUnmount, onMounted } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { streamAssistant, getAssistantHistory, clearAssistantHistory } from "../api/assistant";
import { institutionApi } from "../api/organization";
const props = defineProps({
    kind: { type: String, required: true },
    title: { type: String, required: true },
    welcome: { type: String, required: true },
    suggestions: { type: Array, required: true }
});
let seq = 0;
const messages = ref([]);
const draft = ref("");
const sending = ref(false);
const actionLoadingId = ref(null);
const bodyRef = ref(null);
let abortCtrl = null;
const router = useRouter();
const HISTORY_SEND_LIMIT = 20;
function goToConfig() {
    router.push(props.kind === "teacher" ? "/teacher/ai-config" : "/institution/ai-config");
}
async function loadHistory() {
    try {
        const list = await getAssistantHistory(props.kind, 50);
        messages.value = list.map((item) => {
            const content = item.content;
            return {
                id: item.id,
                role: item.message_type === "question" ? "user" : "assistant",
                content,
                html: renderRich(content, true)
            };
        });
        seq = Math.max(0, ...list.map((i) => i.id));
        await nextTick();
        await hydrateMermaid();
    }
    catch {
    }
}
async function handleClearHistory() {
    if (sending.value)
        return;
    try {
        await ElMessageBox.confirm("确定要清空全部聊天记录吗？该操作不可恢复。", "清空记录", {
            confirmButtonText: "清空",
            cancelButtonText: "取消",
            type: "warning"
        });
    }
    catch {
        return;
    }
    try {
        await clearAssistantHistory(props.kind);
        messages.value = [];
        ElMessage.success("聊天记录已清空");
    }
    catch (e) {
        ElMessage.error(e?.response?.data?.detail || "清空失败，请重试");
    }
}
watch(() => messages.value.map((m) => m.content).join("|"), async () => {
    for (const m of messages.value) {
        if (m.streaming)
            m.html = renderRich(m.content, false);
    }
    await nextTick();
    bodyRef.value?.scrollTo({ top: bodyRef.value.scrollHeight });
}, { flush: "post" });
async function scrollBottom() {
    await nextTick();
    bodyRef.value?.scrollTo({ top: bodyRef.value.scrollHeight });
}
function outboundMessages() {
    return messages.value.filter((m) => !m.action && m.content.trim()).map((m) => ({ role: m.role, content: m.content }));
}
async function send(preset) {
    const text = (preset ?? draft.value).trim();
    if (!text || sending.value)
        return;
    draft.value = "";
    messages.value.push({
        id: ++seq,
        role: "user",
        content: text,
        html: renderRich(text, false)
    });
    const aiMsg = {
        id: ++seq,
        role: "assistant",
        content: "",
        html: "",
        streaming: true,
        action: null
    };
    messages.value.push(aiMsg);
    sending.value = true;
    await scrollBottom();
    abortCtrl = new AbortController();
    const history = outboundMessages().slice(-HISTORY_SEND_LIMIT);
    try {
        await streamAssistant(props.kind, history, {
            onDelta: (t) => {
                aiMsg.streaming = false;
                aiMsg.content += t;
            },
            onAction: (action) => {
                aiMsg.streaming = false;
                aiMsg.action = action;
                aiMsg.actionStatus = "pending";
            },
            onError: (msg) => {
                aiMsg.streaming = false;
                aiMsg.error = true;
                aiMsg.content = msg;
            }
        }, abortCtrl.signal);
    }
    catch (e) {
        if (e?.name !== "AbortError") {
            aiMsg.streaming = false;
            aiMsg.error = true;
            aiMsg.content = e?.message || "请求失败";
        }
    }
    finally {
        aiMsg.streaming = false;
        sending.value = false;
        abortCtrl = null;
        if (!aiMsg.action) {
            aiMsg.html = renderRich(aiMsg.content, true);
            await nextTick();
            await hydrateMermaid();
        }
    }
}
function dismissAction(m) {
    m.action = null;
    m.actionStatus = void 0;
    m.content = "已取消创建。如信息有误，你可以重新告诉我用户名和邮箱。";
    m.html = renderRich(m.content, true);
}
async function confirmCreateTeacher(m) {
    if (!m.action)
        return;
    const a = m.action;
    if (a.username.trim().length < 3)
        return ElMessage.warning("用户名至少 3 个字符");
    if (!a.email.includes("@"))
        return ElMessage.warning("请输入正确的邮箱");
    if (a.password.length < 6)
        return ElMessage.warning("初始密码至少 6 位");
    actionLoadingId.value = m.id;
    try {
        await institutionApi.createTeacher({
            username: a.username.trim(),
            email: a.email.trim(),
            password: a.password
        });
        m.actionStatus = "done";
        m.actionMsg = `教师「${a.username.trim()}」创建成功，初始密码：${a.password}，首次登录需修改密码。`;
        const doneText = m.actionMsg;
        messages.value.push({
            id: ++seq,
            role: "assistant",
            content: doneText,
            html: renderRich(doneText, true)
        });
        await nextTick();
        await hydrateMermaid();
    }
    catch (e) {
        m.actionStatus = "failed";
        m.actionMsg = e.response?.data?.detail || "创建失败，请重试或前往教师管理页操作";
    }
    finally {
        actionLoadingId.value = null;
    }
}
function escapeHtml(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
function renderTextChunk(raw) {
    return raw.split("\n").map((line) => {
        const t = escapeHtml(line).replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
        if (/^#{1,4}\s+/.test(t)) {
            return `<div class="md-h">${t.replace(/^#{1,4}\s+/, "")}</div>`;
        }
        if (/^\s*[-*]\s+/.test(t)) {
            return `<div class="md-li">${t.replace(/^\s*[-*]\s+/, "")}</div>`;
        }
        if (/^\s*\d+\.\s+/.test(t)) {
            return `<div class="md-li">${t.trim()}</div>`;
        }
        return t || '<div class="md-br"></div>';
    }).join("");
}
function codeBlockHtml(body, lang) {
    return `<pre class="code-block">${lang ? `<div class="code-lang">${escapeHtml(lang)}</div>` : ""}<code>${escapeHtml(body)}</code></pre>`;
}
function renderRich(raw, withMermaid) {
    return raw.split("```").map((chunk, idx) => {
        if (idx % 2 === 0)
            return renderTextChunk(chunk);
        let lang = "";
        let body = chunk;
        const nl = chunk.search(/\r?\n/);
        if (nl >= 0) {
            lang = chunk.slice(0, nl).trim().toLowerCase();
            body = chunk.slice(nl).replace(/^\r?\n/, "").replace(/\r?\n$/, "");
        }
        else {
            const m = chunk.match(/^\s*mermaid\s*/i);
            if (m) {
                lang = "mermaid";
                body = chunk.slice(m[0].length);
            }
        }
        if (lang === "mermaid" && withMermaid) {
            return `<div class="mermaid-pending" data-code="${encodeURIComponent(body)}"><div class="mmd-loading">流程图渲染中…</div></div>`;
        }
        return codeBlockHtml(body, lang);
    }).join("");
}
let mermaidLoader = null;
function loadMermaid() {
    if (!mermaidLoader) {
        mermaidLoader = import("mermaid").then((mod) => {
            const mermaid = mod.default;
            mermaid.initialize({
                startOnLoad: false,
                theme: "neutral",
                securityLevel: "loose",
                fontFamily: "inherit"
            });
            return mermaid;
        });
    }
    return mermaidLoader;
}
let mmdSeq = 0;
async function hydrateMermaid() {
    const root = bodyRef.value;
    if (!root)
        return;
    const pending = Array.from(root.querySelectorAll(".mermaid-pending"));
    if (!pending.length)
        return;
    let mermaid;
    try {
        mermaid = await loadMermaid();
    }
    catch {
        for (const node of pending) {
            node.classList.remove("mermaid-pending");
            node.classList.add("mermaid-fail");
            node.innerHTML = codeBlockHtml(decodeURIComponent(node.dataset.code || ""), "mermaid");
        }
        return;
    }
    for (const node of pending) {
        const code = decodeURIComponent(node.dataset.code || "");
        const id = `mmd-${Date.now()}-${++mmdSeq}`;
        try {
            const { svg } = await mermaid.render(id, code);
            node.innerHTML = svg;
            node.classList.remove("mermaid-pending");
            node.classList.add("mermaid-svg");
        }
        catch {
            node.classList.remove("mermaid-pending");
            node.classList.add("mermaid-fail");
            node.innerHTML = '<div class="mmd-err-tip">流程图语法无法渲染，显示源码：</div>' + codeBlockHtml(code, "mermaid");
        }
    }
}
onMounted(() => {
    loadHistory().then(scrollBottom);
});
onBeforeUnmount(() => abortCtrl?.abort());
</script>

<style scoped>
.assistant-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 40px);
  padding: 16px;
}
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 12px;
  margin-bottom: 8px;
  border-bottom: 1px solid #e5e7eb;
}
.header-title {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}
.header-actions {
  display: flex;
  gap: 8px;
}
.chat-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px 12px 16px;
}
.welcome {
  max-width: 640px;
  margin: 8vh auto 0;
  text-align: center;
  color: #4b5563;
}
.welcome-icon { font-size: 44px; color: #2563eb; }
.welcome-title { font-size: 20px; font-weight: 700; color: #1f2937; margin: 12px 0 8px; }
.welcome-text { font-size: 14px; line-height: 1.7; }
.suggestions { display: flex; flex-direction: column; gap: 10px; margin-top: 24px; }
.suggestion-chip {
  border: 1px solid #dbe3f0;
  background: #f8fafc;
  border-radius: 10px;
  padding: 10px 16px;
  font-size: 13px;
  cursor: pointer;
  transition: all .15s;
  text-align: left;
}
.suggestion-chip:hover { border-color: #2563eb; color: #2563eb; background: #eff6ff; }

.msg-row { display: flex; margin: 14px 0; }
.msg-row.is-user { justify-content: flex-end; }
.bubble {
  max-width: 78%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.7;
  white-space: normal;
  word-break: break-word;
}
.is-ai .bubble { background: #fff; border: 1px solid #e5e7eb; color: #1f2937; }
.is-user .bubble { background: #2563eb; color: #fff; }
.bubble.error { border-color: #fca5a5; background: #fef2f2; color: #b91c1c; }

.md :deep(.md-h) { font-weight: 700; margin: 8px 0 4px; color: #111827; }
.md :deep(.md-li) { padding-left: 14px; position: relative; margin: 2px 0; }
.md :deep(.md-li)::before { content: '·'; position: absolute; left: 4px; font-weight: 700; }
.md :deep(code) {
  background: #f1f5f9; border-radius: 4px; padding: 1px 5px;
  font-size: 12px; font-family: monospace;
}
.md :deep(.md-br) { height: 6px; }
.md :deep(.code-block) {
  background: #0f172a;
  color: #e2e8f0;
  border-radius: 8px;
  padding: 10px 12px;
  margin: 8px 0;
  overflow-x: auto;
  font-size: 12.5px;
  line-height: 1.6;
}
.md :deep(.code-block) code {
  background: none;
  color: inherit;
  padding: 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  white-space: pre;
}
.md :deep(.code-lang) {
  color: #93c5fd;
  font-size: 11px;
  margin-bottom: 6px;
  user-select: none;
}
.md :deep(.mermaid-svg) {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 12px;
  margin: 8px 0;
  overflow-x: auto;
  text-align: center;
}
.md :deep(.mermaid-svg svg) { max-width: none; }
.md :deep(.mmd-loading) { color: #9ca3af; font-size: 12px; padding: 12px 0; }
.md :deep(.mermaid-fail) {
  border: 1px dashed #fca5a5;
  border-radius: 8px;
  padding: 8px;
  margin: 8px 0;
}
.md :deep(.mermaid-fail .code-block) { margin: 4px 0 0; }
.md :deep(.mmd-err-tip) { color: #dc2626; font-size: 12px; }
.typing { color: #6b7280; }
.dots { animation: blink 1.2s infinite; }
@keyframes blink { 50% { opacity: .3; } }

.action-head {
  display: flex; align-items: center; gap: 6px;
  font-weight: 600; margin-bottom: 12px; color: #1f2937;
}
.action-form :deep(.el-form-item) { margin-bottom: 10px; }
.action-tip { font-size: 12px; color: #9ca3af; margin-bottom: 10px; }
.action-btns { display: flex; justify-content: flex-end; gap: 8px; }
.action-result { display: flex; align-items: center; gap: 6px; font-size: 13px; }
.action-result.ok { color: #16a34a; }
.action-result.fail { color: #dc2626; }

.chat-input {
  border-top: 1px solid #e5e7eb;
  background: #fff;
  padding: 12px 12px 4px;
}
.input-bar { display: flex; justify-content: space-between; align-items: center; margin-top: 8px; }
.input-hint { font-size: 12px; color: #9ca3af; }
</style>
