<template>
  <div class="page">
    <div class="head">
      <h2 class="page-title">班级管理</h2>
      <el-button type="primary" @click="openCreate">新建班级</el-button>
    </div>

    <el-card shadow="never" class="panel">
      <el-table :data="classes" v-loading="loading" stripe border>
        <el-table-column prop="name" label="班级名称" min-width="140" />
        <el-table-column label="入班码" min-width="220">
          <template #default="{ row }">
            <div class="code-cell">
              <el-tag type="warning" effect="dark" class="code-tag">{{ row.join_code }}</el-tag>
              <span class="code-policy">{{ codePolicyText(row) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="student_count" label="学生数" width="90" />
        <el-table-column label="操作" width="300" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="copyCode(row.join_code)">复制</el-button>
            <el-button link type="danger" @click="handleReset(row)">重置入班码</el-button>
            <el-button link type="primary" @click="openSettings(row)">设置</el-button>
            <el-button link type="primary" @click="openAssign(row)">分配教师</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建班级 -->
    <el-dialog v-model="createVisible" title="新建班级" width="460px">
      <el-form label-width="100px" @submit.prevent>
        <el-form-item v-if="isSuperAdmin" label="所属机构">
          <el-select v-model="formInstitutionId" placeholder="选择机构" style="width: 100%">
            <el-option v-for="i in institutions" :key="i.id" :label="i.name" :value="i.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="班级名称">
          <el-input v-model="formName" maxlength="100" />
        </el-form-item>
        <el-form-item label="码过期时间">
          <el-checkbox v-model="formHasExpiry" style="margin-right: 10px">启用</el-checkbox>
          <el-date-picker
            v-if="formHasExpiry"
            v-model="formExpiresAt"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            style="width: 240px"
          />
        </el-form-item>
        <el-form-item label="码使用次数">
          <el-checkbox v-model="formHasMaxUses" style="margin-right: 10px">限制</el-checkbox>
          <el-input-number v-if="formHasMaxUses" v-model="formMaxUses" :min="1" :precision="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleCreate">创建并生成入班码</el-button>
      </template>
    </el-dialog>

    <!-- 入班码/班级设置 -->
    <el-dialog v-model="settingsVisible" title="班级设置" width="460px">
      <div v-if="settingsRow">
        <el-form label-width="100px" @submit.prevent>
          <el-form-item label="班级名称">
            <el-input v-model="settingsName" maxlength="100" />
          </el-form-item>
          <el-form-item label="码过期时间">
            <el-checkbox v-model="setHasExpiry" style="margin-right: 10px">启用</el-checkbox>
            <el-date-picker
              v-if="setHasExpiry"
              v-model="setExpiresAt"
              type="datetime"
              value-format="YYYY-MM-DDTHH:mm:ss"
              style="width: 240px"
            />
          </el-form-item>
          <el-form-item label="码使用次数">
            <el-checkbox v-model="setHasMaxUses" style="margin-right: 10px">限制</el-checkbox>
            <el-input-number v-if="setHasMaxUses" v-model="setMaxUses" :min="1" :precision="0" />
          </el-form-item>
          <el-form-item label="已使用">
            <span class="muted">{{ settingsRow.code_uses ?? 0 }} 次</span>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="settingsVisible = false">取消</el-button>
        <el-button type="primary" :loading="settingsSaving" @click="handleSaveSettings">保存</el-button>
      </template>
    </el-dialog>

    <!-- 分配教师 -->
    <el-dialog v-model="assignVisible" title="分配教师" width="480px">
      <div v-if="assignRow">
        <p class="assign-title">
          {{ assignRow.name }}
          <el-tag type="warning" effect="dark">入班码 {{ assignRow.join_code }}</el-tag>
        </p>
        <div class="assign-row">
          <el-select v-model="assignTeacherId" placeholder="选择本机构教师" style="flex: 1">
            <el-option v-for="t in availableTeachers" :key="t.id" :label="t.username" :value="t.id" />
          </el-select>
          <el-button type="primary" :loading="assignSaving" @click="handleAssign">分配</el-button>
        </div>
        <el-table :data="assignedTeachers" size="small" border>
          <el-table-column prop="username" label="已分配教师" />
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button link type="danger" @click="handleUnassign(row.id)">移除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  institutionApi, adminApi,
  type ClassSummary, type Institution, type StaffUser, type TeacherBrief,
  type ClassSettingsPayload,
} from '../../api/organization'
import { useUserStore } from '../../stores/user'

const store = useUserStore()
const isSuperAdmin = computed(() => store.role === 'super_admin')

const loading = ref(false)
const classes = ref<ClassSummary[]>([])
const institutions = ref<Institution[]>([])

const createVisible = ref(false)
const saving = ref(false)
const formInstitutionId = ref<number | undefined>(undefined)
const formName = ref('')
const formHasExpiry = ref(false)
const formExpiresAt = ref<string | null>(null)
const formHasMaxUses = ref(false)
const formMaxUses = ref(1)

const settingsVisible = ref(false)
const settingsSaving = ref(false)
const settingsRow = ref<ClassSummary | null>(null)
const settingsName = ref('')
const setHasExpiry = ref(false)
const setExpiresAt = ref<string | null>(null)
const setHasMaxUses = ref(false)
const setMaxUses = ref(1)

const assignVisible = ref(false)
const assignRow = ref<ClassSummary | null>(null)
const assignTeacherId = ref<number | undefined>(undefined)
const assignSaving = ref(false)
const teachers = ref<StaffUser[]>([])
const assignedTeachers = ref<TeacherBrief[]>([])

const availableTeachers = computed(() => {
  const assignedIds = new Set(assignedTeachers.value.map(t => t.id))
  return teachers.value.filter(t => !assignedIds.has(t.id))
})

function codePolicyText(row: ClassSummary): string {
  const parts: string[] = []
  if (row.code_expires_at) parts.push(`有效期至 ${row.code_expires_at.replace('T', ' ').slice(0, 16)}`)
  if (row.code_max_uses != null) parts.push(`${row.code_uses ?? 0}/${row.code_max_uses} 次`)
  return parts.join(' · ')
}

async function loadClasses() {
  loading.value = true
  try {
    classes.value = await institutionApi.classes()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

async function copyCode(code?: string) {
  if (!code) return
  try {
    await navigator.clipboard.writeText(code)
    ElMessage.success('入班码已复制')
  } catch {
    ElMessage.warning(`复制失败，请手动复制：${code}`)
  }
}

function openCreate() {
  formName.value = ''
  formInstitutionId.value = undefined
  formHasExpiry.value = false
  formExpiresAt.value = null
  formHasMaxUses.value = false
  formMaxUses.value = 1
  createVisible.value = true
}

async function handleCreate() {
  if (isSuperAdmin.value && !formInstitutionId.value) {
    ElMessage.warning('请选择机构')
    return
  }
  if (!formName.value.trim()) {
    ElMessage.warning('请输入班级名称')
    return
  }
  saving.value = true
  try {
    const cls = await institutionApi.createClass({
      name: formName.value.trim(),
      institution_id: isSuperAdmin.value ? formInstitutionId.value : undefined,
      code_expires_at: formHasExpiry.value ? formExpiresAt.value : null,
      code_max_uses: formHasMaxUses.value ? formMaxUses.value : null,
    })
    ElMessage.success(`创建成功，入班码：${cls.join_code}`)
    createVisible.value = false
    await loadClasses()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  } finally {
    saving.value = false
  }
}

async function handleReset(row: ClassSummary) {
  try {
    await ElMessageBox.confirm(`确定重置「${row.name}」的入班码吗？旧码将立即失效。`, '重置入班码', {
      type: 'warning',
    })
    const updated = await institutionApi.resetCode(row.id)
    ElMessage.success(`新入班码：${updated.join_code}`)
    await loadClasses()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '重置失败')
  }
}

function openSettings(row: ClassSummary) {
  settingsRow.value = row
  settingsName.value = row.name
  setHasExpiry.value = !!row.code_expires_at
  setExpiresAt.value = row.code_expires_at ? row.code_expires_at.replace(' ', 'T').slice(0, 19) : null
  setHasMaxUses.value = row.code_max_uses != null
  setMaxUses.value = row.code_max_uses ?? 1
  settingsVisible.value = true
}

async function handleSaveSettings() {
  if (!settingsRow.value) return
  if (!settingsName.value.trim()) {
    ElMessage.warning('班级名称不能为空')
    return
  }
  const payload: ClassSettingsPayload = {
    name: settingsName.value.trim(),
    code_expires_at: setHasExpiry.value ? setExpiresAt.value : null,
    code_max_uses: setHasMaxUses.value ? setMaxUses.value : null,
  }
  settingsSaving.value = true
  try {
    await institutionApi.updateClass(settingsRow.value.id, payload)
    ElMessage.success('已保存')
    settingsVisible.value = false
    await loadClasses()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    settingsSaving.value = false
  }
}

async function openAssign(row: ClassSummary) {
  assignRow.value = row
  assignTeacherId.value = undefined
  assignedTeachers.value = []
  assignVisible.value = true
  try {
    const [list, assigned] = await Promise.all([
      institutionApi.listTeachers(),
      institutionApi.classTeachers(row.id),
    ])
    teachers.value = list
    assignedTeachers.value = assigned
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  }
}

async function loadAssigned(classId: number) {
  assignedTeachers.value = await institutionApi.classTeachers(classId)
}

async function handleAssign() {
  if (!assignRow.value || !assignTeacherId.value) {
    ElMessage.warning('请选择教师')
    return
  }
  assignSaving.value = true
  try {
    await institutionApi.assignTeacher(assignRow.value.id, assignTeacherId.value)
    ElMessage.success('分配成功')
    await loadAssigned(assignRow.value.id)
    assignTeacherId.value = undefined
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '分配失败')
  } finally {
    assignSaving.value = false
  }
}

async function handleUnassign(teacherId: number) {
  if (!assignRow.value) return
  try {
    await institutionApi.unassignTeacher(assignRow.value.id, teacherId)
    ElMessage.success('已移除')
    await loadAssigned(assignRow.value.id)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

onMounted(async () => {
  await loadClasses()
  if (isSuperAdmin.value) {
    institutions.value = await adminApi.listInstitutions()
  }
})
</script>

<style scoped>
.page { padding: 24px; }
.head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-title { font-size: 22px; font-weight: 700; color: #1f2937; margin: 0; }
.panel { border-radius: 12px; }
.code-cell { display: flex; flex-direction: column; gap: 4px; align-items: flex-start; }
.code-tag { font-family: monospace; letter-spacing: 1px; }
.code-policy { color: #9ca3af; font-size: 12px; }
.muted { color: #9ca3af; font-size: 13px; }
.assign-title { display: flex; align-items: center; gap: 10px; font-weight: 600; margin-bottom: 14px; }
.assign-row { display: flex; gap: 10px; margin-bottom: 14px; }
</style>
