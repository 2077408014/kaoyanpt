<template>
  <div class="page">
    <div class="page-head">
      <el-button link @click="$router.back()">&lt; 返回班级</el-button>
      <h2 class="page-title">{{ assignment?.title || '作业详情' }}</h2>
    </div>

    <el-card v-if="assignment" shadow="never" class="info-card">
      <div class="info-meta">
        <el-tag :type="assignment.due_at && isOverdue(assignment.due_at) ? 'danger' : 'info'" effect="plain">
          {{ assignment.due_at ? `截止：${formatTime(assignment.due_at)}` : '无截止时间' }}
        </el-tag>
        <span>已提交 {{ assignment.submission_count ?? submissions.length }} 份</span>
        <span>已批改 {{ assignment.graded_count ?? gradedCount }} 份</span>
      </div>
      <div class="info-content">{{ assignment.content }}</div>
      <div v-if="assignment.images && assignment.images.length" class="info-images">
        <el-image
          v-for="p in assignment.images"
          :key="p"
          :src="'/uploads/' + p"
          :preview-src-list="assignment.images.map(x => '/uploads/' + x)"
          fit="cover"
          class="info-img"
        />
      </div>
    </el-card>

    <el-table :data="submissions" v-loading="loading" stripe border class="sub-table">
      <el-table-column prop="student_name" label="学生" width="140" />
      <el-table-column prop="content" label="提交内容" min-width="280" show-overflow-tooltip />
      <el-table-column prop="submitted_at" label="提交时间" width="170">
        <template #default="{ row }">{{ formatTime(row.submitted_at) }}</template>
      </el-table-column>
      <el-table-column label="分数" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.score !== null && row.score !== undefined" type="success" effect="dark">
            {{ row.score }}
          </el-tag>
          <span v-else class="muted">未批改</span>
        </template>
      </el-table-column>
      <el-table-column prop="feedback" label="评语" min-width="180" show-overflow-tooltip />
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openGrade(row)">打分/评语</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 打分弹窗 -->
    <el-dialog v-model="gradeVisible" title="批改作业" width="480px">
      <div v-if="current" class="grade-body">
        <p class="grade-student">{{ current.student_name }} 的提交</p>
        <div class="grade-content">{{ current.content }}</div>
        <el-form label-width="70px" style="margin-top: 16px" @submit.prevent>
          <el-form-item label="分数">
            <el-input-number v-model="gradeScore" :min="0" :max="100" :precision="0" />
            <span class="muted" style="margin-left: 10px">0 - 100</span>
          </el-form-item>
          <el-form-item label="评语">
            <el-input v-model="gradeFeedback" type="textarea" :rows="4" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="gradeVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleGrade">提交批改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { teacherApi, type Assignment, type Submission } from '../../api/organization'

const route = useRoute()
const assignmentId = Number(route.params.assignmentId)

const loading = ref(false)
const assignment = ref<Assignment | null>(null)
const submissions = ref<Submission[]>([])

const gradeVisible = ref(false)
const saving = ref(false)
const current = ref<Submission | null>(null)
const gradeScore = ref<number>(80)
const gradeFeedback = ref('')

const gradedCount = computed(() =>
  submissions.value.filter(s => s.score !== null && s.score !== undefined).length
)

function openGrade(row: Submission) {
  current.value = row
  gradeScore.value = row.score ?? 80
  gradeFeedback.value = row.feedback || ''
  gradeVisible.value = true
}

async function handleGrade() {
  if (!current.value) return
  if (gradeScore.value === null || gradeScore.value === undefined) {
    ElMessage.warning('请输入分数')
    return
  }
  saving.value = true
  try {
    const updated = await teacherApi.gradeSubmission(assignmentId, {
      student_id: current.value.student_id,
      score: gradeScore.value,
      feedback: gradeFeedback.value,
    })
    const idx = submissions.value.findIndex(s => s.student_id === updated.student_id)
    if (idx >= 0) submissions.value[idx] = updated
    if (assignment.value) {
      assignment.value.submission_count = submissions.value.length
      assignment.value.graded_count = gradedCount.value
    }
    ElMessage.success('批改成功')
    gradeVisible.value = false
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '批改失败')
  } finally {
    saving.value = false
  }
}

function isOverdue(due: string): boolean {
  return new Date(due).getTime() <= Date.now()
}

function formatTime(t?: string | null): string {
  if (!t) return ''
  return t.replace('T', ' ').slice(0, 16)
}

onMounted(async () => {
  loading.value = true
  try {
    const [asm, subs] = await Promise.all([
      teacherApi.getAssignment(assignmentId),
      teacherApi.listSubmissions(assignmentId),
    ])
    assignment.value = asm
    submissions.value = subs
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.page { padding: 24px; }
.page-head { margin-bottom: 16px; }
.page-title { font-size: 22px; font-weight: 700; color: #1f2937; margin: 8px 0 0; }
.info-card { margin-bottom: 18px; border-radius: 12px; }
.info-meta { display: flex; align-items: center; gap: 16px; color: #4b5563; font-size: 14px; margin-bottom: 12px; }
.info-content { white-space: pre-wrap; color: #1f2937; line-height: 1.7; }
.info-images { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.info-img { width: 120px; height: 120px; border-radius: 6px; border: 1px solid #e5e7eb; }
.sub-table { margin-top: 4px; }
.muted { color: #9ca3af; font-size: 13px; }
.grade-student { font-weight: 600; margin-bottom: 10px; }
.grade-content {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 12px;
  max-height: 220px;
  overflow-y: auto;
  white-space: pre-wrap;
  line-height: 1.6;
  font-size: 14px;
}
</style>
