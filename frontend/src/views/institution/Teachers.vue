<template>
  <div class="page">
    <div class="head">
      <h2 class="page-title">教师管理</h2>
      <el-button type="primary" @click="openCreate">创建教师账号</el-button>
    </div>

    <el-card shadow="never" class="panel">
      <el-table :data="teachers" v-loading="loading" stripe border>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" min-width="140" />
        <el-table-column prop="email" label="邮箱" min-width="200" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" effect="plain">
              {{ row.is_active ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="首次改密" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.must_change_password" type="warning" effect="plain">待修改</el-tag>
            <span v-else class="muted">已修改</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" min-width="150">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑教师账号' : '创建教师账号'" width="460px">
      <el-alert
        v-if="!editingId"
        title="教师首次登录时将被强制修改初始密码。"
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 16px"
      />
      <el-alert
        v-else
        title="重置密码后，该教师下次登录需重新修改密码。"
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 16px"
      />
      <el-form label-width="80px" @submit.prevent>
        <el-form-item label="用户名">
          <el-input v-model="form.username" maxlength="50" placeholder="至少 3 个字符" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" placeholder="教师登录与接收通知使用" />
        </el-form-item>
        <el-form-item :label="editingId ? '重置密码' : '初始密码'">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            :placeholder="editingId ? '留空则不修改密码' : '至少 6 位'"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">
          {{ editingId ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { institutionApi, type StaffUser } from '../../api/organization'

const loading = ref(false)
const teachers = ref<StaffUser[]>([])

const dialogVisible = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)
const form = ref({ username: '', email: '', password: '' })

async function loadTeachers() {
  loading.value = true
  try {
    teachers.value = await institutionApi.listTeachers()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  form.value = { username: '', email: '', password: '' }
  dialogVisible.value = true
}

function openEdit(row: StaffUser) {
  editingId.value = row.id
  form.value = { username: row.username, email: row.email, password: '' }
  dialogVisible.value = true
}

async function handleSave() {
  if (form.value.username.trim().length < 3) {
    ElMessage.warning('用户名至少 3 个字符')
    return
  }
  if (!form.value.email.trim()) {
    ElMessage.warning('请输入邮箱')
    return
  }
  if (!editingId.value && form.value.password.length < 6) {
    ElMessage.warning('初始密码至少 6 位')
    return
  }
  if (form.value.password && form.value.password.length < 6) {
    ElMessage.warning('密码至少 6 位')
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await institutionApi.updateTeacher(editingId.value, {
        username: form.value.username.trim(),
        email: form.value.email.trim(),
        ...(form.value.password ? { password: form.value.password } : {}),
      })
      ElMessage.success('教师账号已更新')
    } else {
      await institutionApi.createTeacher({
        username: form.value.username.trim(),
        email: form.value.email.trim(),
        password: form.value.password,
      })
      ElMessage.success('教师账号创建成功')
    }
    dialogVisible.value = false
    await loadTeachers()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(row: StaffUser) {
  try {
    await ElMessageBox.confirm(
      `确定删除教师账号「${row.username}」吗？该教师与本班机构所有班级的任教关系会一并解除，此操作不可恢复。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await institutionApi.deleteTeacher(row.id)
    ElMessage.success('教师账号已删除')
    await loadTeachers()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

function formatTime(t?: string | null): string {
  if (!t) return ''
  return t.replace('T', ' ').slice(0, 16)
}

onMounted(loadTeachers)
</script>

<style scoped>
.page { padding: 24px; }
.head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-title { font-size: 22px; font-weight: 700; color: #1f2937; margin: 0; }
.panel { border-radius: 12px; }
.muted { color: #9ca3af; font-size: 13px; }
</style>
