<template>
  <div class="page">
    <el-page-header @back="router.back()" class="back">
      <template #content>
        <span class="title">学生学习详情（只读）</span>
      </template>
    </el-page-header>
    <OrgStudentPanel :student-id="studentId" :api="institutionApi" />
  </div>
</template>

<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import OrgStudentPanel from '../../components/OrgStudentPanel.vue'
import { institutionApi } from '../../api/organization'

const route = useRoute()
const router = useRouter()
const studentId = Number(route.params.studentId)
</script>

<style scoped>
.page { padding: 24px; }
.back { margin-bottom: 16px; }
.title { font-weight: 600; }
</style>
