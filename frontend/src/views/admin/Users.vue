<template>
  <div class="page">
    <div class="head">
      <h2 class="page-title">账号管理</h2>
      <el-button type="primary" @click="openCreate">新建账号</el-button>
    </div>

    <el-tabs v-model="activeTab" class="role-tabs">
      <el-tab-pane label="教师" name="teacher" />
      <el-tab-pane label="机构管理者" name="institution_admin" />
    </el-tabs>

    <el-card shadow="never" class="panel">
      <el-table :data="groupedUsers" v-loading="loading" stripe border>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="用户名" min-width="130" />
        <el-table-column prop="email" label="邮箱" min-width="180" />
        <el-table-column label="角色" width="120">
          <template #default="{ row }">
            <el-tag :type="row.role === 'teacher' ? 'primary' : 'success'" effect="plain">
              {{ row.role === 'teacher' ? '教师' : '机构管理者' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="institution_name" label="所属机构" min-width="140" />
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑账号' : '新建教师/机构管理者账号'" width="460px">
      <el-form label-width="100px" @submit.prevent>
        <el-form-item label="角色">
          <el-radio-group v-model="form.role">
            <el-radio value="teacher">教师</el-radio>
            <el-radio value="institution_admin">机构管理者</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="所属机构">
          <el-select v-model="form.institution_id" placeholder="选择机构" style="width: 100%">
            <el-option v-for="i in institutions" :key="i.id" :label="i.name" :value="i.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="至少 3 个字符" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" placeholder="登录邮箱" />
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
          {{ editingId ? '保存' : '创建账号' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi, type Institution, type StaffUser } from '../../api/organization'

const loading = ref(false)
const saving = ref(false)
const users = ref<StaffUser[]>([])
const institutions = ref<Institution[]>([])
const activeTab = ref<'teacher' | 'institution_admin'>('teacher')

const groupedUsers = computed(() => users.value.filter(u => u.role === activeTab.value))

const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const form = ref({
  role: 'teacher' as 'teacher' | 'institution_admin',
  institution_id: undefined as number | undefined,
  username: '',
  email: '',
  password: '',
})

function formatTime(t?: string) {
  return t ? new Date(t).toLocaleString('zh-CN', { hour12: false }) : '-'
}

async function loadInstitutions() {
  institutions.value = await adminApi.listInstitutions()
}

async function loadUsers() {
  loading.value = true
  try {
    users.value = await adminApi.listUsers()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  form.value = {
    role: activeTab.value,
    institution_id: institutions.value[0]?.id,
    username: '',
    email: '',
    password: '',
  }
  dialogVisible.value = true
}

function openEdit(row: StaffUser) {
  editingId.value = row.id
  form.value = {
    role: row.role as 'teacher' | 'institution_admin',
    institution_id: row.institution_id,
    username: row.username,
    email: row.email,
    password: '',
  }
  dialogVisible.value = true
}

async function handleSave() {
  const f = form.value
  if (!f.institution_id) return ElMessage.warning('请选择机构')
  if (f.username.trim().length < 3) return ElMessage.warning('用户名至少 3 个字符')
  if (!f.email.trim()) return ElMessage.warning('请输入邮箱')
  if (!editingId.value && f.password.length < 6) return ElMessage.warning('密码至少 6 位')
  if (f.password && f.password.length < 6) return ElMessage.warning('密码至少 6 位')
  saving.value = true
  try {
    if (editingId.value) {
      // 编辑：密码留空则不传
      await adminApi.updateStaffUser(editingId.value, {
        username: f.username.trim(),
        email: f.email.trim(),
        role: f.role,
        institution_id: f.institution_id,
        ...(f.password ? { password: f.password } : {}),
      })
      ElMessage.success('账号已更新')
    } else {
      await adminApi.createStaffUser({
        username: f.username.trim(),
        email: f.email.trim(),
        password: f.password,
        role: f.role,
        institution_id: f.institution_id,
      })
      ElMessage.success('账号创建成功')
    }
    dialogVisible.value = false
    await loadUsers()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(row: StaffUser) {
  try {
    await ElMessageBox.confirm(
      `确定删除账号「${row.username}」吗？该账号的班级任教关系会一并解除，此操作不可恢复。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await adminApi.deleteStaffUser(row.id)
    ElMessage.success('账号已删除')
    await loadUsers()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

onMounted(async () => {
  await loadInstitutions()
  await loadUsers()
})
</script>

<style scoped>
.page { padding: 24px; }
.head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-title { font-size: 22px; font-weight: 700; color: #1f2937; margin: 0; }
.role-tabs { margin-bottom: 12px; }
.panel { border-radius: 12px; }
</style>
