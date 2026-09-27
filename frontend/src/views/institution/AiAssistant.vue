<template>
  <AssistantChat
    kind="institution"
    title="机构 AI 助手"
    welcome="我可以基于本机构的实时班级数据，帮你分析各班学习情况、教师资源配置，也可以帮你创建教师账号（需你二次确认）。试试下面的问题："
    :suggestions="suggestions"
  />
</template>

<script setup>import AssistantChat from "../../components/AssistantChat.vue";
const suggestions = [
  "分析一下各班级的整体学习情况",
  "哪个班级最需要关注？为什么？",
  "帮我创建一个教师账号，用户名 liwei，邮箱 liwei@test.com",
  "机构的教师和班级资源配置有什么建议？"
];
</script>
