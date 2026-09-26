<template>
  <div class="page">
    <div class="page-head">
      <el-button link @click="$router.push('/teacher')">&lt; 返回班级列表</el-button>
      <h2 class="page-title">{{ classInfo?.name || '班级详情' }}</h2>
      <div v-if="classInfo" class="code-box">
        入班码
        <el-tag type="warning" effect="dark" class="code-tag">{{ classInfo.join_code }}</el-tag>
        <el-button link type="primary" size="small" @click="copyCode(classInfo.join_code || '')">复制</el-button>
      </div>
    </div>

    <el-tabs v-model="activeTab" class="tabs">
      <!-- 成员管理 -->
      <el-tab-pane label="成员管理" name="students">
        <div class="toolbar">
          <el-button type="primary" @click="addVisible = true">手动添加学生</el-button>
        </div>
        <OrgStudentTable
          :students="students"
          :loading="studentsLoading"
          removable
          @view="viewStudent"
          @remove="handleRemove"
          @suspend="handleSuspend"
          @restore="handleRestore"
        />
      </el-tab-pane>

      <!-- 班级公告 -->
      <el-tab-pane label="班级公告" name="announcements">
        <div class="toolbar">
          <el-button type="primary" @click="openAnnouncement()">发布公告</el-button>
        </div>
        <el-table :data="announcements" v-loading="annLoading" stripe border>
          <el-table-column prop="title" label="标题" min-width="180" />
          <el-table-column prop="author_name" label="发布人" width="120" />
          <el-table-column prop="content" label="内容" min-width="260" show-overflow-tooltip />
          <el-table-column prop="created_at" label="发布时间" width="180">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openAnnouncement(row)">编辑</el-button>
              <el-button link type="danger" @click="handleDeleteAnnouncement(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- 作业管理 -->
      <el-tab-pane label="作业管理" name="assignments">
        <div class="toolbar">
          <el-button type="primary" @click="openAssignment()">布置作业</el-button>
        </div>
        <el-table :data="assignments" v-loading="asmLoading" stripe border>
          <el-table-column prop="title" label="作业标题" min-width="180" />
          <el-table-column prop="content" label="内容" min-width="240" show-overflow-tooltip />
          <el-table-column label="截止时间" width="180">
            <template #default="{ row }">
              <span v-if="!row.due_at">无截止</span>
              <el-tag v-else :type="isOverdue(row.due_at) ? 'danger' : 'info'" effect="plain">
                {{ formatTime(row.due_at) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="提交/已批" width="110">
            <template #default="{ row }">
              {{ row.submission_count ?? 0 }} / {{ row.graded_count ?? 0 }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="220" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="$router.push(`/teacher/assignments/${row.id}`)">
                查看提交
              </el-button>
              <el-button link type="primary" @click="openAssignment(row)">编辑</el-button>
              <el-button link type="danger" @click="handleDeleteAssignment(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <OrgStudentPanel
      v-if="selectedStudent && activeTab === 'students'"
      :student-id="selectedStudent.id"
      :api="panelApi"
      @close="selectedStudent = null"
    />

    <!-- 手动添加学生 -->
    <el-dialog v-model="addVisible" title="手动添加学生" width="420px">
      <el-form label-width="80px" @submit.prevent>
        <el-form-item label="学生邮箱">
          <el-input v-model="addEmail" placeholder="请输入已注册学生的注册邮箱" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addVisible = false">取消</el-button>
        <el-button type="primary" :loading="addSaving" @click="handleAddStudent">添加</el-button>
      </template>
    </el-dialog>

    <!-- 公告编辑 -->
    <el-dialog v-model="annVisible" :title="annForm.id ? '编辑公告' : '发布公告'" width="520px">
      <el-form label-width="70px" @submit.prevent>
        <el-form-item label="标题">
          <el-input v-model="annForm.title" maxlength="100" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="annForm.content" type="textarea" :rows="6" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="annVisible = false">取消</el-button>
        <el-button type="primary" :loading="annSaving" @click="handleSaveAnnouncement">保存</el-button>
      </template>
    </el-dialog>

    <!-- 作业编辑 -->
    <el-dialog v-model="asmVisible" :title="asmForm.id ? '编辑作业' : '布置作业'" width="560px">
      <el-form label-width="80px" @submit.prevent>
        <el-form-item label="标题">
          <el-input v-model="asmForm.title" maxlength="100" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="asmForm.content" type="textarea" :rows="6" />
        </el-form-item>
        <el-form-item label="图片">
          <div class="img-list">
            <div v-for="(p, i) in asmForm.images" :key="p" class="img-item">
              <el-image
                :src="'/uploads/' + p"
                :preview-src-list="asmPreviewList"
                :initial-index="i"
                fit="cover"
                class="img-thumb"
              />
              <el-icon class="img-del" @click="asmForm.images.splice(i, 1)"><Close /></el-icon>
            </div>
            <el-upload
              v-if="asmForm.images.length < 9"
              :show-file-list="false"
              :http-request="handleAsmImageUpload"
              accept="image/jpeg,image/png,image/webp"
              :disabled="asmImgUploading"
            >
              <div class="img-add" v-loading="asmImgUploading">
                <el-icon><Plus /></el-icon>
              </div>
            </el-upload>
          </div>
        </el-form-item>
        <el-form-item label="截止时间">
          <el-date-picker
            v-model="asmDue"
            type="datetime"
            placeholder="留空表示无截止"
            value-format="YYYY-MM-DDTHH:mm:ss"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="asmVisible = false">取消</el-button>
        <el-button type="primary" :loading="asmSaving" @click="handleSaveAssignment">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Close, Plus } from '@element-plus/icons-vue'
import OrgStudentTable from '../../components/OrgStudentTable.vue'
import OrgStudentPanel from '../../components/OrgStudentPanel.vue'
import {
  teacherApi,
  type ClassListItem, type StudentSummary,
  type Announcement, type Assignment,
} from '../../api/organization'

const route = useRoute()
const classId = Number(route.params.classId)

const activeTab = ref('students')
const classInfo = ref<ClassListItem | null>(null)
const students = ref<StudentSummary[]>([])
const studentsLoading = ref(false)
const selectedStudent = ref<StudentSummary | null>(null)

// 学生详情面板统一用教师 API
const panelApi = {
  studentOverview: (studentId: number) => teacherApi.studentOverview(studentId),
  studentMistakes: (studentId: number, subject?: string) => teacherApi.studentMistakes(studentId, subject),
  studentMistakeDetail: (studentId: number, mistakeId: number) =>
    teacherApi.studentMistakeDetail(studentId, mistakeId),
}

// ---------- 班级信息 ----------
async function loadClassInfo() {
  const list = await teacherApi.myClasses()
  classInfo.value = list.find(c => c.id === classId) || null
}

async function copyCode(code: string) {
  try {
    await navigator.clipboard.writeText(code)
    ElMessage.success('入班码已复制')
  } catch {
    ElMessage.warning(`复制失败，请手动复制：${code}`)
  }
}

// ---------- 学生 ----------
async function loadStudents() {
  studentsLoading.value = true
  try {
    students.value = await teacherApi.classStudents(classId)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  } finally {
    studentsLoading.value = false
  }
}

function viewStudent(row: StudentSummary) {
  selectedStudent.value = row
}

const addVisible = ref(false)
const addEmail = ref('')
const addSaving = ref(false)

async function handleAddStudent() {
  if (!addEmail.value.trim()) {
    ElMessage.warning('请输入学生邮箱')
    return
  }
  addSaving.value = true
  try {
    await teacherApi.addStudent(classId, addEmail.value.trim())
    ElMessage.success('添加成功')
    addVisible.value = false
    addEmail.value = ''
    await loadStudents()
    await loadClassInfo()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '添加失败')
  } finally {
    addSaving.value = false
  }
}

async function handleSuspend(row: StudentSummary) {
  try {
    await ElMessageBox.confirm(`确定暂停学生「${row.username}」吗？暂停期间该学生无法访问班级内容。`, '暂停成员', {
      type: 'warning',
    })
    await teacherApi.suspendStudent(classId, row.id)
    ElMessage.success('已暂停')
    await loadStudents()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

async function handleRestore(row: StudentSummary) {
  try {
    await teacherApi.restoreStudent(classId, row.id)
    ElMessage.success('已恢复')
    await loadStudents()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

async function handleRemove(row: StudentSummary) {
  try {
    await ElMessageBox.confirm(
      `确定将「${row.username}」移出班级吗？移出后其学习数据仍会保留。`,
      '移出班级',
      { type: 'warning' }
    )
    await teacherApi.removeStudent(classId, row.id)
    ElMessage.success('已移出班级')
    await loadStudents()
    await loadClassInfo()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

// ---------- 公告 ----------
const announcements = ref<Announcement[]>([])
const annLoading = ref(false)
const annVisible = ref(false)
const annSaving = ref(false)
const annForm = ref<{ id?: number; title: string; content: string }>({ title: '', content: '' })

async function loadAnnouncements() {
  annLoading.value = true
  try {
    announcements.value = await teacherApi.listAnnouncements(classId)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  } finally {
    annLoading.value = false
  }
}

function openAnnouncement(row?: Announcement) {
  annForm.value = row
    ? { id: row.id, title: row.title, content: row.content }
    : { title: '', content: '' }
  annVisible.value = true
}

async function handleSaveAnnouncement() {
  if (!annForm.value.title.trim() || !annForm.value.content.trim()) {
    ElMessage.warning('标题和内容不能为空')
    return
  }
  annSaving.value = true
  try {
    if (annForm.value.id) {
      await teacherApi.updateAnnouncement(annForm.value.id, {
        title: annForm.value.title.trim(),
        content: annForm.value.content,
      })
    } else {
      await teacherApi.createAnnouncement(classId, {
        title: annForm.value.title.trim(),
        content: annForm.value.content,
      })
    }
    ElMessage.success('保存成功')
    annVisible.value = false
    await loadAnnouncements()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    annSaving.value = false
  }
}

async function handleDeleteAnnouncement(row: Announcement) {
  try {
    await ElMessageBox.confirm(`确定删除公告「${row.title}」吗？`, '删除公告', { type: 'warning' })
    await teacherApi.deleteAnnouncement(row.id)
    ElMessage.success('已删除')
    await loadAnnouncements()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

// ---------- 作业 ----------
const assignments = ref<Assignment[]>([])
const asmLoading = ref(false)
const asmVisible = ref(false)
const asmSaving = ref(false)
const asmForm = ref<{ id?: number; title: string; content: string; images: string[] }>({
  title: '', content: '', images: [],
})
const asmDue = ref<string | null>(null)
const asmImgUploading = ref(false)

const asmPreviewList = computed(() => asmForm.value.images.map(p => '/uploads/' + p))

async function handleAsmImageUpload(options: { file: File }) {
  if (options.file.size > 10 * 1024 * 1024) {
    ElMessage.warning('图片不能超过 10MB')
    return
  }
  asmImgUploading.value = true
  try {
    const { image_path } = await teacherApi.uploadAssignmentImage(options.file)
    asmForm.value.images.push(image_path)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '图片上传失败')
  } finally {
    asmImgUploading.value = false
  }
}

async function loadAssignments() {
  asmLoading.value = true
  try {
    assignments.value = await teacherApi.listAssignments(classId)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  } finally {
    asmLoading.value = false
  }
}

function openAssignment(row?: Assignment) {
  asmForm.value = row
    ? { id: row.id, title: row.title, content: row.content, images: [...(row.images || [])] }
    : { title: '', content: '', images: [] }
  asmDue.value = row?.due_at ? row.due_at.replace(' ', 'T').slice(0, 19) : null
  asmVisible.value = true
}

async function handleSaveAssignment() {
  if (!asmForm.value.title.trim()) {
    ElMessage.warning('标题不能为空')
    return
  }
  if (!asmForm.value.content.trim() && asmForm.value.images.length === 0) {
    ElMessage.warning('内容和图片至少填写一项')
    return
  }
  const payload = {
    title: asmForm.value.title.trim(),
    content: asmForm.value.content,
    images: asmForm.value.images,
    due_at: asmDue.value || null,
  }
  asmSaving.value = true
  try {
    if (asmForm.value.id) {
      await teacherApi.updateAssignment(asmForm.value.id, payload)
    } else {
      await teacherApi.createAssignment(classId, payload)
    }
    ElMessage.success('保存成功')
    asmVisible.value = false
    await loadAssignments()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    asmSaving.value = false
  }
}

async function handleDeleteAssignment(row: Assignment) {
  try {
    await ElMessageBox.confirm(`确定删除作业「${row.title}」吗？已有提交也会一并删除。`, '删除作业', {
      type: 'warning',
    })
    await teacherApi.deleteAssignment(row.id)
    ElMessage.success('已删除')
    await loadAssignments()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

// ---------- 工具 ----------
function isOverdue(due: string): boolean {
  return new Date(due).getTime() <= Date.now()
}

function formatTime(t?: string | null): string {
  if (!t) return ''
  return t.replace('T', ' ').slice(0, 16)
}

onMounted(async () => {
  try {
    await Promise.all([loadClassInfo(), loadStudents()])
    await Promise.all([loadAnnouncements(), loadAssignments()])
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  }
})
</script>

<style scoped>
.page { padding: 24px; }
.page-head { display: flex; align-items: center; gap: 16px; margin-bottom: 16px; flex-wrap: wrap; }
.page-title { font-size: 22px; font-weight: 700; color: #1f2937; margin: 0; }
.code-box { display: flex; align-items: center; gap: 6px; color: #4b5563; font-size: 14px; margin-left: auto; }
.code-tag { font-family: monospace; letter-spacing: 1px; }
.tabs { margin-top: 8px; }
.toolbar { margin-bottom: 12px; }
.img-list { display: flex; flex-wrap: wrap; gap: 8px; }
.img-item { position: relative; width: 96px; height: 96px; }
.img-thumb { width: 96px; height: 96px; border-radius: 6px; border: 1px solid #e5e7eb; }
.img-del {
  position: absolute; top: -6px; right: -6px;
  background: #ef4444; color: #fff; border-radius: 50%;
  padding: 2px; cursor: pointer; font-size: 12px;
}
.img-add {
  width: 96px; height: 96px; border: 1px dashed #d1d5db; border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  color: #9ca3af; font-size: 22px; cursor: pointer;
}
.img-add:hover { border-color: #409eff; color: #409eff; }
</style>
