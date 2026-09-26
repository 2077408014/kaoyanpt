<template>
  <div class="page">
    <h2 class="page-title">我带的班级</h2>
    <el-skeleton v-if="loading" :rows="4" animated />
    <el-empty v-else-if="classes.length === 0" description="暂无分配的班级" />
    <div v-else class="card-grid">
      <router-link
        v-for="cls in classes"
        :key="cls.id"
        class="class-card-wrap"
        :to="`/teacher/classes/${cls.id}`"
      >
        <el-card class="class-card" shadow="hover">
          <div class="class-name">{{ cls.name }}</div>
          <div class="class-inst">{{ cls.institution_name }}</div>
          <div class="stat-row">
            <span><el-icon><User /></el-icon> 学生 {{ cls.student_count }}</span>
            <span><el-icon><Avatar /></el-icon> 教师 {{ cls.teacher_count }}</span>
          </div>
        </el-card>
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { User, Avatar } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { teacherApi, type ClassListItem } from '../../api/organization'

const loading = ref(false)
const classes = ref<ClassListItem[]>([])

onMounted(async () => {
  loading.value = true
  try {
    classes.value = await teacherApi.myClasses()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.page { padding: 24px; }
.page-title { font-size: 22px; font-weight: 700; color: #1f2937; margin: 0 0 20px; }
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}
.class-card-wrap { cursor: pointer; display: block; text-decoration: none; color: inherit; }
.class-card-wrap :deep(.el-card) { height: 100%; }
.class-card { border-radius: 12px; }
.class-name { font-size: 18px; font-weight: 600; color: #1f2937; }
.class-inst { color: #6b7280; font-size: 13px; margin: 6px 0 14px; }
.stat-row { display: flex; gap: 18px; color: #4b5563; font-size: 14px; }
.stat-row span { display: inline-flex; align-items: center; gap: 4px; }
</style>
