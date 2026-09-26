<template>
  <div class="page">
    <div class="head">
      <h2 class="page-title">机构管理</h2>
      <el-button type="primary" @click="dialogVisible = true">新建机构</el-button>
    </div>

    <el-card shadow="never" class="panel">
      <el-table :data="institutions" v-loading="loading" stripe border>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="机构名称" min-width="200" />
        <el-table-column prop="class_count" label="班级数" width="120" />
        <el-table-column label="创建时间" width="200">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" title="新建机构" width="420px">
      <el-form @submit.prevent>
        <el-form-item label="机构名称">
          <el-input v-model="name" placeholder="请输入机构名称" maxlength="100" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { adminApi, type Institution } from '../../api/organization'

const loading = ref(false)
const saving = ref(false)
const institutions = ref<Institution[]>([])
const dialogVisible = ref(false)
const name = ref('')

function formatTime(t?: string) {
  return t ? new Date(t).toLocaleString('zh-CN', { hour12: false }) : '-'
}

async function load() {
  loading.value = true
  try {
    institutions.value = await adminApi.listInstitutions()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  if (!name.value.trim()) {
    ElMessage.warning('请输入机构名称')
    return
  }
  saving.value = true
  try {
    await adminApi.createInstitution(name.value.trim())
    ElMessage.success('机构创建成功')
    dialogVisible.value = false
    name.value = ''
    await load()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page { padding: 24px; }
.head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-title { font-size: 22px; font-weight: 700; color: #1f2937; margin: 0; }
.panel { border-radius: 12px; }
</style>
