<template>
  <RoleLayout title="机构管理端" :items="menuItems" />
</template>

<script setup>
import RoleLayout from '../../components/RoleLayout.vue';import { DataBoard, Setting, User, ChatDotRound } from "@element-plus/icons-vue";
const menuItems = [
  { index: "/institution", label: "班级总览", icon: DataBoard },
  { index: "/institution/manage-classes", label: "班级管理", icon: Setting },
  { index: "/institution/teachers", label: "教师管理", icon: User },
  { index: "/institution/assistant", label: "AI 助手", icon: ChatDotRound }
];
</script>
