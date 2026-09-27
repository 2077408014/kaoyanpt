<template>
  <el-dialog
    :model-value="visible"
    title="学后测验"
    width="480px"
    :close-on-click-modal="false"
    :show-close="false"
    @close="$emit('close')"
  >
    <template v-if="current">
      <div class="quiz-progress">答对 {{ stat.correct }} / 已答 {{ stat.done }} / 共 {{ stat.total }}</div>
      <div class="quiz-body" :key="current.word_id + '-' + current.type">
        <div class="quiz-badge">{{ current.type }}</div>
        <h3 class="quiz-prompt">{{ current.prompt }}</h3>
        <div class="quiz-options">
          <button
            v-for="opt in current.options"
            :key="opt.index"
            class="quiz-option"
            :class="optionClass(opt.index)"
            :disabled="answered"
            @click="handleSelect(opt.index)"
          >
            {{ translateIndex(opt.index) }}. {{ opt.text }}
          </button>
        </div>
        <p v-if="feedback !== null" class="quiz-feedback" :class="feedback ? 'ok' : 'bad'">
          {{ feedback ? '回答正确！' : '回答错误，正确答案：' + optionText(current.correct) }}
        </p>
      </div>
    </template>

    <template v-else>
      <div class="quiz-progress">答对 {{ stat.correct }} / 已答 {{ stat.done }} / 共 {{ stat.total }}</div>
      <el-empty description="测验完成！">
        <el-button type="primary" @click="$emit('close')">完成</el-button>
      </el-empty>
    </template>

    <template v-if="current" #footer>
      <el-button :disabled="feedback === null" type="primary" @click="next">
        {{ feedback === null ? '请作答' : (queue.length || pendings.length ? '下一题' : '查看结果') }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>import { ref, reactive, watch } from "vue";
import { getQuiz, answerQuiz } from "@/api/words";
const props = defineProps({
  visible: { type: Boolean, required: true },
  wordIds: { type: Array, required: true }
});
const sessionId = ref("");
const queue = ref([]);
const current = ref(null);
const answered = ref(false);
const feedback = ref(null);
const lastPick = ref(-1);
const pendings = ref([]);
const stat = reactive({ done: 0, correct: 0, total: 0 });
function translateIndex(idx) {
  return ["A", "B", "C", "D"][idx] ?? idx;
}
function optionText(idx) {
  const opt = current.value?.options.find((o) => o.index === idx);
  return opt ? translateIndex(idx) + ". " + opt.text : "";
}
function optionClass(idx) {
  if (feedback.value === null) return "";
  if (idx === current.value?.correct) return "right";
  if (idx === lastPick.value && feedback.value === false) return "wrong";
  return "";
}
async function loadItems(ids) {
  return await getQuiz(ids, Math.min(ids.length, 8));
}
async function start() {
  sessionId.value = "quiz_" + Date.now() + Math.random().toString(36).slice(2, 8);
  stat.done = 0;
  stat.correct = 0;
  stat.total = 0;
  pendings.value = [];
  answered.value = false;
  feedback.value = null;
  queue.value = [];
  if (!props.wordIds.length) return;
  const items = await loadItems(props.wordIds);
  stat.total = items.length;
  queue.value = [...items];
  current.value = queue.value.shift() ?? null;
}
async function handleSelect(idx) {
  if (answered.value || !current.value) return;
  answered.value = true;
  lastPick.value = idx;
  const correct = idx === current.value.correct;
  feedback.value = correct;
  stat.done++;
  if (correct) stat.correct++;
  try {
    await answerQuiz({ word_id: current.value.word_id, selected: idx, correct, session_id: sessionId.value });
  } catch {
  }
  if (!correct) {
    pendings.value.push(current.value.word_id);
  }
}
async function next() {
  feedback.value = null;
  answered.value = false;
  lastPick.value = -1;
  if (queue.value.length > 0) {
    current.value = queue.value.shift() ?? null;
    return;
  }
  if (pendings.value.length > 0) {
    const ids = [...pendings.value];
    pendings.value = [];
    const items = await loadItems(ids);
    stat.total += items.length;
    queue.value = [...items];
    current.value = queue.value.shift() ?? null;
    return;
  }
  current.value = null;
}
watch(() => props.visible, async (v) => {
  if (v) {
    await start();
  } else {
    queue.value = [];
    current.value = null;
    pendings.value = [];
  }
});
</script>

<style scoped>
.quiz-progress { font-size: 13px; color: #999; margin-bottom: 12px; }
.quiz-body { text-align: center; }
.quiz-badge { display: inline-block; padding: 4px 12px; background: #dbeafe; color: #3b82f6; border-radius: 4px; font-size: 12px; margin-bottom: 12px; }
.quiz-prompt { font-size: 22px; color: #333; margin: 0 0 16px; }
.quiz-options { display: flex; flex-direction: column; gap: 10px; }
.quiz-option { padding: 12px; border: 1px solid #e0e0e0; border-radius: 8px; background: #fff; cursor: pointer; font-size: 15px; text-align: left; }
.quiz-option:hover:not(:disabled) { border-color: #409eff; }
.quiz-option.right { border-color: #67c23a; background: #f0f9eb; }
.quiz-option.wrong { border-color: #f56c6c; background: #fef0f0; }
.quiz-option:disabled { cursor: default; }
.quiz-feedback { font-size: 14px; margin-top: 12px; }
.quiz-feedback.ok { color: #67c23a; }
.quiz-feedback.bad { color: #f56c6c; }
</style>