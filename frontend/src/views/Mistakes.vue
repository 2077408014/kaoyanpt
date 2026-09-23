<template>
  <div class="mistakes">
    <div class="toolbar">
      <el-button type="primary" @click="showAddDialog = true">
        <el-icon><Plus /></el-icon>
        添加错题
      </el-button>
      <div class="filters">
        <el-select v-model="filters.subject" placeholder="科目" class="filter-select" clearable>
          <el-option label="数学" value="数学" />
          <el-option label="英语" value="英语" />
          <el-option label="政治" value="政治" />
          <el-option label="专业课" value="专业课" />
        </el-select>
        <el-select v-model="filters.mastery_level" placeholder="掌握程度" class="filter-select" clearable>
          <el-option label="生疏" value="生疏" />
          <el-option label="熟悉" value="熟悉" />
          <el-option label="掌握" value="掌握" />
        </el-select>
        <el-button @click="loadMistakes">筛选</el-button>
      </div>
    </div>
    <el-table :data="mistakes" border>
      <el-table-column prop="subject" label="科目" width="100" />
      <el-table-column label="图片" width="80">
        <template #default="scope">
          <el-image
            v-if="scope.row.image_path"
            :src="'/uploads/' + scope.row.image_path"
            :preview-src-list="['/uploads/' + scope.row.image_path]"
            fit="cover"
            style="width: 50px; height: 50px; border-radius: 4px"
          />
          <span v-else style="color: #ccc">无</span>
        </template>
      </el-table-column>
      <el-table-column prop="knowledge_point" label="知识点" />
      <el-table-column prop="error_type" label="错误类型" width="100" />
      <el-table-column prop="difficulty" label="难度" width="80" />
      <el-table-column prop="mastery_level" label="掌握程度" width="100">
        <template #default="scope">
          <el-tag :type="getMasteryTagType(scope.row.mastery_level)">
            {{ scope.row.mastery_level }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="next_review_date" label="下次复习" width="120" />
      <el-table-column prop="review_count" label="复习次数" width="100" />
      <el-table-column label="操作" width="340">
        <template #default="scope">
          <div class="action-btns">
            <el-button size="small" @click="viewMistake(scope.row)">查看</el-button>
            <el-button size="small" @click="openReviewDialog(scope.row)">重做</el-button>
            <el-button size="small" type="primary" @click="openEditDialog(scope.row)">修改</el-button>
            <el-button size="small" type="danger" @click="handleDelete(scope.row)">删除</el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog title="添加错题" v-model="showAddDialog" width="650px">
      <el-form ref="addFormRef" :model="addForm" :rules="addRules" label-width="100px">
        <el-form-item label="题目图片">
          <div class="upload-area" @paste="handlePaste">
            <el-upload
              :show-file-list="false"
              :before-upload="handleImageSelect"
              accept="image/jpeg,image/png,image/webp"
            >
              <div v-if="!addForm.image_path" class="upload-placeholder">
                <el-icon><Picture /></el-icon>
                <span>点击上传或粘贴题目图片</span>
              </div>
              <div v-else class="image-preview">
                <el-image
                  :src="'/uploads/' + addForm.image_path + '?t=' + Date.now()"
                  fit="contain"
                  class="preview-img"
                />
                <el-button size="small" type="danger" @click.stop="removeImage">移除</el-button>
              </div>
            </el-upload>
            <el-button
              v-if="addForm.image_path"
              type="primary"
              :loading="recognizing"
              @click="handleRecognize"
              style="margin-left: 12px"
            >
              AI识别
            </el-button>
          </div>
        </el-form-item>
        <el-form-item label="科目" prop="subject">
          <el-select
            v-model="addForm.subject"
            placeholder="请选择科目"
            class="full-width"
          >
            <el-option label="数学" value="数学" />
            <el-option label="英语" value="英语" />
            <el-option label="政治" value="政治" />
            <el-option label="专业课" value="专业课" />
          </el-select>
        </el-form-item>
        <el-form-item label="知识点">
          <el-input v-model="addForm.knowledge_point" placeholder="可选，AI可自动识别" />
        </el-form-item>
        <el-form-item label="错误类型">
          <el-select v-model="addForm.error_type" placeholder="可选" clearable>
            <el-option label="概念错误" value="概念错误" />
            <el-option label="计算错误" value="计算错误" />
            <el-option label="审题错误" value="审题错误" />
          </el-select>
        </el-form-item>
        <el-form-item label="难度">
          <el-select v-model="addForm.difficulty" placeholder="可选" clearable>
            <el-option label="简单" value="简单" />
            <el-option label="中等" value="中等" />
            <el-option label="困难" value="困难" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="正确答案">
          <el-input v-model="addForm.answer" type="textarea" :rows="2" placeholder="可选" />
        </el-form-item>
        <el-form-item label="解析">
          <el-input v-model="addForm.analysis" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="错误原因">
          <el-input v-model="addForm.error_reason" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="handleAdd">确认添加</el-button>
      </template>
    </el-dialog>
    <el-dialog title="错题详情" v-model="showDetailDialog" width="700px">
      <div v-if="selectedMistake">
        <div class="detail-item" v-if="selectedMistake.image_path">
          <span class="label">题目图片：</span>
          <el-image
            :src="'/uploads/' + selectedMistake.image_path"
            :preview-src-list="['/uploads/' + selectedMistake.image_path]"
            fit="contain"
            style="max-width: 100%; max-height: 300px; margin-top: 8px"
          />
        </div>
        <div class="detail-item">
          <span class="label">科目：</span>
          <span>{{ selectedMistake.subject }}</span>
        </div>
        <div class="detail-item">
          <span class="label">知识点：</span>
          <span>{{ selectedMistake.knowledge_point || '未填写' }}</span>
        </div>
        <div class="detail-item">
          <span class="label">错误类型：</span>
          <span>{{ selectedMistake.error_type || '未填写' }}</span>
        </div>
        <div class="detail-item">
          <span class="label">难度：</span>
          <span>{{ selectedMistake.difficulty || '未填写' }}</span>
        </div>
        <div class="detail-item" v-if="selectedMistake.question_text">
          <span class="label">题目文本：</span>
          <p>{{ selectedMistake.question_text }}</p>
        </div>
        <div class="detail-item">
          <span class="label">答案：</span>
          <div class="math-content" v-html="renderMathContent(selectedMistake.answer || '暂无')"></div>
        </div>
        <div class="detail-item">
          <span class="label">解析：</span>
          <div class="math-content" v-html="renderMathContent(selectedMistake.analysis || '暂无解析')"></div>
        </div>
        <div class="detail-item">
          <span class="label">错误原因：</span>
          <p>{{ selectedMistake.error_reason || '暂无' }}</p>
        </div>
        <el-divider />
        <div class="similar-section">
          <div class="similar-header">
            <h4>同类题推荐</h4>
            <el-button size="small" @click="loadSimilarQuestions" :loading="loadingSimilar">
              加载推荐
            </el-button>
          </div>
          <div v-if="similarQuestions.length > 0" class="similar-list">
            <div v-for="(item, index) in similarQuestions" :key="index" class="similar-item">
              <div class="similar-header-row">
                <span class="similar-number">{{ index + 1 }}.</span>
                <span class="similar-label">推荐题目</span>
              </div>
              <div class="similar-question" v-html="renderMathContent(item.question || '')"></div>
              <div class="similar-answer">
                <span class="answer-label">答案：</span>
                <span v-html="renderMathContent(item.answer || '')"></span>
              </div>
              <div class="similar-analysis">
                <span class="analysis-label">解析：</span>
                <div v-html="renderMathContent(item.analysis || '')"></div>
              </div>
            </div>
          </div>
          <el-empty v-else-if="!loadingSimilar && hasLoadedSimilar" description="暂无同类题" />
        </div>
      </div>
    </el-dialog>
    <el-dialog title="重做错题" v-model="showReviewDialog" width="600px">
      <div v-if="reviewingMistake">
        <div v-if="reviewingMistake.image_path" class="review-image">
          <el-image
            :src="'/uploads/' + reviewingMistake.image_path"
            :preview-src-list="['/uploads/' + reviewingMistake.image_path]"
            fit="contain"
            style="max-width: 100%; max-height: 200px"
          />
        </div>
        
        <el-form-item>
          <el-button 
            type="info" 
            size="small" 
            @click="showAnswer = !showAnswer"
          >
            {{ showAnswer ? '隐藏答案' : '对答案' }}
          </el-button>
        </el-form-item>
        
        <div v-if="showAnswer" class="answer-section">
          <div v-if="reviewingMistake.answer" class="answer-item">
            <span class="answer-label">正确答案：</span>
            <span v-html="renderMathContent(reviewingMistake.answer)"></span>
          </div>
          <div v-if="reviewingMistake.analysis" class="answer-item">
            <span class="answer-label">解析：</span>
            <div v-html="renderMathContent(reviewingMistake.analysis)"></div>
          </div>
          <div v-if="!reviewingMistake.answer && !reviewingMistake.analysis" class="no-answer">
            暂无答案和解析
          </div>
        </div>
        
        <el-form-item label="答题结果">
          <el-radio-group v-model="reviewResult">
            <el-radio label="正确" />
            <el-radio label="错误" />
            <el-radio label="部分正确" />
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="reviewNotes" type="textarea" :rows="2" />
        </el-form-item>
      </div>
      <template #footer>
        <el-button @click="showReviewDialog = false">取消</el-button>
        <el-button type="primary" @click="handleReview">确认提交</el-button>
      </template>
    </el-dialog>
    <el-dialog title="编辑错题" v-model="editDialogVisible" width="650px">
      <el-form ref="editFormRef" :model="editForm" label-width="100px">
        <el-form-item label="科目">
          <el-select v-model="editForm.subject" placeholder="请选择科目" class="full-width">
            <el-option label="数学" value="数学" />
            <el-option label="英语" value="英语" />
            <el-option label="政治" value="政治" />
            <el-option label="专业课" value="专业课" />
          </el-select>
        </el-form-item>
        <el-form-item label="知识点">
          <el-input v-model="editForm.knowledge_point" placeholder="知识点" />
        </el-form-item>
        <el-form-item label="错误类型">
          <el-select v-model="editForm.error_type" placeholder="错误类型" clearable class="full-width">
            <el-option label="概念错误" value="概念错误" />
            <el-option label="计算错误" value="计算错误" />
            <el-option label="审题错误" value="审题错误" />
          </el-select>
        </el-form-item>
        <el-form-item label="难度">
          <el-select v-model="editForm.difficulty" placeholder="难度" clearable class="full-width">
            <el-option label="简单" value="简单" />
            <el-option label="中等" value="中等" />
            <el-option label="困难" value="困难" />
          </el-select>
        </el-form-item>
        <el-form-item label="正确答案">
          <el-input v-model="editForm.answer" type="textarea" :rows="3" placeholder="正确答案" />
        </el-form-item>
        <el-form-item label="解析">
          <el-input v-model="editForm.analysis" type="textarea" :rows="3" placeholder="解析" />
        </el-form-item>
        <el-form-item label="错误原因">
          <el-input v-model="editForm.error_reason" type="textarea" :rows="2" placeholder="错误原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Picture } from '@element-plus/icons-vue'
import katex from 'katex'
import 'katex/dist/katex.min.css'
import {
  getMistakes, createMistake, updateMistake as updateMistakeApi,
  deleteMistake as deleteMistakeApi,
  reviewMistake as reviewMistakeApi, uploadMistakeImage, recognizeMistake
} from '../api/mistakes'
import { recommendQuestions, type RecommendQuestion } from '../api/ai'

function renderMathFormula(formula: string, displayMode: boolean): string {
  try {
    return katex.renderToString(formula.trim(), {
      displayMode,
      throwOnError: false,
      strict: false,
      trust: true
    })
  } catch {
    return `<span class="math-error">${displayMode ? '$$' : '$'}${formula.trim()}${displayMode ? '$$' : '$'}</span>`
  }
}

function renderMathContent(text: string): string {
  if (!text) return ''
  
  let result = text
  
  result = result.replace(/\$\$(.*?)\$\$/gms, (_, formula) => {
    const trimmedFormula = formula.trim()
    if (!trimmedFormula) return '$$'
    return renderMathFormula(trimmedFormula, true)
  })
  
  result = result.replace(/(?<!\\)\$(.*?)(?<!\\)\$/g, (_, formula) => {
    const trimmedFormula = formula.trim()
    if (!trimmedFormula) return '$'
    if (trimmedFormula.length > 100) {
      return renderMathFormula(trimmedFormula, true)
    }
    return renderMathFormula(trimmedFormula, false)
  })
  
  return result
}

const mistakes = ref<any[]>([])
const showAddDialog = ref(false)
const showDetailDialog = ref(false)
const showReviewDialog = ref(false)
const selectedMistake = ref<any>(null)
const reviewingMistake = ref<any>(null)
const reviewResult = ref('')
const reviewNotes = ref('')
const showAnswer = ref(false)
const addFormRef = ref()
const recognizing = ref(false)
const similarQuestions = ref<RecommendQuestion[]>([])
const loadingSimilar = ref(false)
const hasLoadedSimilar = ref(false)

const editDialogVisible = ref(false)
const editFormRef = ref()
const editForm = reactive({
  subject: '',
  knowledge_point: '',
  error_type: '',
  difficulty: '',
  answer: '',
  analysis: '',
  error_reason: ''
})
const editingId = ref<number | null>(null)

const filters = reactive({
  subject: '',
  mastery_level: ''
})

const addForm = reactive({
  subject: '',
  knowledge_point: '',
  error_type: '',
  difficulty: '',
  question_text: '',
  answer: '',
  analysis: '',
  error_reason: '',
  image_path: ''
})

const addRules = {
  subject: [{ required: true, message: '请选择科目', trigger: 'change' }]
}

function getMasteryTagType(level: string) {
  switch (level) {
    case '生疏': return 'danger'
    case '熟悉': return 'warning'
    case '掌握': return 'success'
    default: return 'info'
  }
}

async function loadMistakes() {
  const params: Record<string, string> = {}
  if (filters.subject) params.subject = filters.subject
  if (filters.mastery_level) params.mastery_level = filters.mastery_level
  mistakes.value = await getMistakes(params)
}

onMounted(loadMistakes)

async function handleImageSelect(file: File): Promise<boolean> {
  try {
    const result = await uploadMistakeImage(file)
    addForm.image_path = result.image_path
    ElMessage.success('图片上传成功')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '图片上传失败')
  }
  return false
}

async function handlePaste(event: ClipboardEvent) {
  const items = event.clipboardData?.items
  if (!items) return

  for (const item of items) {
    if (item.type.startsWith('image/')) {
      event.preventDefault()
      const file = item.getAsFile()
      if (file) {
        await handleImageSelect(file)
        return
      }
    }
  }

  const files = event.clipboardData?.files
  if (files && files.length > 0) {
    const imageFile = Array.from(files).find(f => f.type.startsWith('image/'))
    if (imageFile) {
      event.preventDefault()
      await handleImageSelect(imageFile)
    }
  }
}

function removeImage() {
  addForm.image_path = ''
}

async function handleRecognize() {
  if (!addForm.image_path) {
    ElMessage.warning('请先上传题目图片')
    return
  }
  recognizing.value = true
  try {
    const result = await recognizeMistake(addForm.image_path)
    if (result.subject) addForm.subject = result.subject
    if (result.knowledge_point) addForm.knowledge_point = result.knowledge_point
    if (result.difficulty) addForm.difficulty = result.difficulty
    if (result.error_type) addForm.error_type = result.error_type
    if (result.answer) addForm.answer = result.answer
    if (result.analysis) addForm.analysis = result.analysis
    ElMessage.success(`AI识别完成，置信度: ${(result.confidence * 100).toFixed(0)}%`)
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || 'AI识别失败')
  } finally {
    recognizing.value = false
  }
}

async function handleAdd() {
  if (!addFormRef.value) return
  await addFormRef.value.validate(async (valid: boolean) => {
    if (!valid) return
    if (!addForm.image_path) {
      ElMessage.warning('请上传题目图片')
      return
    }
    try {
      await createMistake(addForm)
      ElMessage.success('添加成功')
      showAddDialog.value = false
      loadMistakes()
      Object.keys(addForm).forEach(key => addForm[key as keyof typeof addForm] = '')
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || '添加失败')
    }
  })
}

function viewMistake(mistake: any) {
  selectedMistake.value = mistake
  similarQuestions.value = []
  hasLoadedSimilar.value = false
  showDetailDialog.value = true
}

async function loadSimilarQuestions() {
  if (!selectedMistake.value) return
  loadingSimilar.value = true
  try {
    const result = await recommendQuestions({
      question_text: selectedMistake.value.question_text || '',
      subject: selectedMistake.value.subject || '',
      knowledge_point: selectedMistake.value.knowledge_point || ''
    })
    similarQuestions.value = result.questions || []
    hasLoadedSimilar.value = true
    if (similarQuestions.value.length === 0) {
      ElMessage.warning('未生成推荐题目，请检查AI配置')
    }
  } catch (error: any) {
    ElMessage.error('加载推荐失败')
  } finally {
    loadingSimilar.value = false
  }
}

function openReviewDialog(mistake: any) {
  reviewingMistake.value = mistake
  reviewResult.value = ''
  reviewNotes.value = ''
  showAnswer.value = false
  showReviewDialog.value = true
}

async function handleReview() {
  if (!reviewResult.value) {
    ElMessage.warning('请选择答题结果')
    return
  }
  try {
    await reviewMistakeApi(reviewingMistake.value.id, {
      result: reviewResult.value,
      notes: reviewNotes.value
    })
    ElMessage.success('提交成功')
    showReviewDialog.value = false
    loadMistakes()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '提交失败')
  }
}

function openEditDialog(mistake: any) {
  editingId.value = mistake.id
  editForm.subject = mistake.subject || ''
  editForm.knowledge_point = mistake.knowledge_point || ''
  editForm.error_type = mistake.error_type || ''
  editForm.difficulty = mistake.difficulty || ''
  editForm.answer = mistake.answer || ''
  editForm.analysis = mistake.analysis || ''
  editForm.error_reason = mistake.error_reason || ''
  editDialogVisible.value = true
}

async function saveEdit() {
  if (!editingId.value) return
  try {
    await updateMistakeApi(editingId.value, {
      subject: editForm.subject || undefined,
      knowledge_point: editForm.knowledge_point || undefined,
      error_type: editForm.error_type || undefined,
      difficulty: editForm.difficulty || undefined,
      answer: editForm.answer || undefined,
      analysis: editForm.analysis || undefined,
      error_reason: editForm.error_reason || undefined
    })
    ElMessage.success('修改成功')
    editDialogVisible.value = false
    loadMistakes()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '修改失败')
  }
}

async function handleDelete(mistake: any) {
  try {
    await ElMessageBox.confirm('确定要删除这个错题吗？', '提示', {
      type: 'warning'
    })
    await deleteMistakeApi(mistake.id)
    ElMessage.success('删除成功')
    loadMistakes()
  } catch {
    // 用户取消
  }
}
</script>

<style scoped>
.mistakes {
  padding: 20px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.filters {
  display: flex;
  gap: 12px;
}

.action-btns {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: 6px;
}

.filter-select {
  width: 120px;
}

.upload-area {
  display: flex;
  align-items: center;
  gap: 12px;
}

.upload-placeholder {
  width: 200px;
  height: 120px;
  border: 2px dashed #dcdfe6;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #909399;
  cursor: pointer;
}

.upload-placeholder .el-icon {
  font-size: 28px;
}

.image-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.preview-img {
  width: 200px;
  height: 120px;
  object-fit: cover;
  border-radius: 8px;
}

.detail-item {
  margin-bottom: 12px;
}

.detail-item .label {
  font-weight: bold;
  color: #666;
}

.detail-item p {
  margin: 4px 0 0;
  color: #333;
}

.similar-section {
  margin-top: 8px;
}

.similar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.similar-header h4 {
  margin: 0;
  font-size: 15px;
  color: #333;
}

.similar-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.similar-item {
  padding: 16px;
  background: #f5f7fa;
  border-radius: 10px;
  border-left: 4px solid #409eff;
}

.similar-header-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
}

.similar-number {
  font-weight: bold;
  color: #409eff;
  font-size: 15px;
}

.similar-label {
  font-weight: bold;
  color: #333;
  font-size: 14px;
}

.similar-question {
  font-size: 14px;
  color: #333;
  line-height: 1.8;
  margin-bottom: 10px;
  padding: 10px;
  background: #fff;
  border-radius: 6px;
}

.similar-answer {
  font-size: 14px;
  color: #67c23a;
  line-height: 1.8;
  margin-bottom: 8px;
}

.answer-label {
  font-weight: bold;
}

.similar-analysis {
  font-size: 13px;
  color: #666;
  line-height: 1.8;
  padding: 10px;
  background: #fff;
  border-radius: 6px;
}

.analysis-label {
  font-weight: bold;
  color: #909399;
  display: block;
  margin-bottom: 6px;
}

.review-image {
  margin-bottom: 16px;
  text-align: center;
}

.answer-section {
  background: #f9fafb;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
  border-left: 4px solid #667eea;
}

.answer-item {
  margin-bottom: 12px;
}

.answer-item:last-child {
  margin-bottom: 0;
}

.answer-label {
  font-weight: 600;
  color: #667eea;
  display: block;
  margin-bottom: 4px;
}

.no-answer {
  color: #999;
  font-style: italic;
}

.question {
  font-size: 16px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 20px;
}

.math-content {
  margin: 4px 0 0;
  color: #333;
  line-height: 1.8;
}

.math-content :deep(.katex) {
  font-size: 1.1em;
}

.math-content :deep(.katex-display) {
  margin: 0.5em 0;
  overflow-x: auto;
  overflow-y: hidden;
}

.math-content :deep(.katex-display::-webkit-scrollbar) {
  height: 6px;
}

.math-content :deep(.katex-display::-webkit-scrollbar-track) {
  background: #f0f0f0;
  border-radius: 3px;
}

.math-content :deep(.katex-display::-webkit-scrollbar-thumb) {
  background: #c0c0c0;
  border-radius: 3px;
}

.math-content :deep(.katex-display::-webkit-scrollbar-thumb:hover) {
  background: #a0a0a0;
}

.math-error {
  color: #e6a23c;
  font-family: monospace;
}
</style>
