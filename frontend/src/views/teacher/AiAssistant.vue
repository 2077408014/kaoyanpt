<template>
  <AssistantChat
    kind="teacher"
    title="教师 AI 助手"
    welcome="我可以基于你任教班级的真实数据，帮你分析学生学习状态、作业提交情况，并给出针对性的教学建议。试试下面的问题："
    :suggestions="suggestions"
  />
</template>

<script setup>import AssistantChat from "../../components/AssistantChat.vue";
const suggestions = [
  "哪些学生近7天学习状态需要重点关注？",
  "对比一下各班级的整体学习情况",
  "最近作业提交和批改情况怎么样？",
  "针对学习落后的学生，给我一些干预建议"
];
</script>
