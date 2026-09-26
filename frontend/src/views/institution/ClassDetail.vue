<template>
  <div class="page">
    <el-page-header @back="router.push('/institution')" class="back">
      <template #content>
        <span class="title">班级学生（只读）</span>
      </template>
    </el-page-header>

    <el-card class="panel" shadow="never">
      <template #header>学生名单（{{ students.length }} 人）</template>
      <OrgStudentTable
        :students="students"
        :loading="loading"
        @view="row => router.push(`/institution/students/${row.id}`)"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import OrgStudentTable from '../../components/OrgStudentTable.vue'
import { institutionApi, type StudentSummary } from '../../api/organization'

const route = useRoute()
const router = useRouter()
const classId = Number(route.params.classId)

const loading = ref(false)
const students = ref<StudentSummary[]>([])

onMounted(async () => {
  loading.value = true
  try {
    students.value = await institutionApi.classStudents(classId)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.page { padding: 24px; }
.back { margin-bottom: 16px; }
.title { font-weight: 600; }
.panel { border-radius: 12px; }
</style>
