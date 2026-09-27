<template>
  <RoleLayout title="教师工作台" :items="menuItems" />
</template>

<script setup>
import RoleLayout from '../../components/RoleLayout.vue';import { School, ChatDotRound } from "@element-plus/icons-vue";
const menuItems = [
  { index: "/teacher", label: "我的班级", icon: School },
  { index: "/teacher/assistant", label: "AI 助手", icon: ChatDotRound }
];
</script>
