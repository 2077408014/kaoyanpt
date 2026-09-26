<template>
  <RoleLayout title="教师工作台" :items="menuItems" />
</template>

<script setup lang="ts">
import { School } from '@element-plus/icons-vue'
import RoleLayout from '../../components/RoleLayout.vue'

const menuItems = [
  { index: '/teacher', label: '我的班级', icon: School },
]
</script>
