<template>
  <RoleLayout title="机构管理端" :items="menuItems" />
</template>

<script setup lang="ts">
import { DataBoard, Setting, User } from '@element-plus/icons-vue'
import RoleLayout from '../../components/RoleLayout.vue'

const menuItems = [
  { index: '/institution', label: '班级总览', icon: DataBoard },
  { index: '/institution/manage-classes', label: '班级管理', icon: Setting },
  { index: '/institution/teachers', label: '教师管理', icon: User },
]
</script>
