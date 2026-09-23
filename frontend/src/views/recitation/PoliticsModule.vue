<template>
  <div class="politics-module">
    <div class="module-header">
      <h3>政治背诵内容管理</h3>
      <el-button type="primary" @click="showAddDialog = true">
        <el-icon><Plus /></el-icon>添加背诵内容
      </el-button>
    </div>

    <div class="filters">
      <el-select v-model="filterCategory" placeholder="分类" style="width: 150px" clearable @change="loadRecitations">
        <el-option label="马克思主义原理" value="马原" />
        <el-option label="毛中特" value="毛中特" />
        <el-option label="史纲" value="史纲" />
        <el-option label="思修法基" value="思修" />
        <el-option label="形势与政策" value="时政" />
      </el-select>
      <el-select v-model="filterLevel" placeholder="掌握程度" style="width: 150px" clearable @change="loadRecitations">
        <el-option label="生疏" value="生疏" />
        <el-option label="熟悉" value="熟悉" />
        <el-option label="掌握" value="掌握" />
      </el-select>
      <el-button @click="loadRecitations">筛选</el-button>
    </div>

    <el-table :data="recitations" border>
      <el-table-column prop="title" label="标题" />
      <el-table-column prop="category" label="分类" width="120" />
      <el-table-column prop="mastery_level" label="掌握程度" width="100">
        <template #default="scope">
          <el-tag :type="getMasteryTagType(scope.row.mastery_level)">
            {{ scope.row.mastery_level }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="review_count" label="复习次数" width="100" />
      <el-table-column prop="next_review_date" label="下次复习" width="120" />
      <el-table-column label="操作" width="200">
        <template #default="scope">
          <el-button size="small" @click="viewRecitation(scope.row)">查看</el-button>
          <el-button size="small" @click="editRecitation(scope.row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog title="添加背诵内容" v-model="showAddDialog" width="700px">
      <el-form :model="addForm" label-width="100px">
        <el-form-item label="标题">
          <el-input v-model="addForm.title" placeholder="请输入标题" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="addForm.category" style="width: 100%">
            <el-option label="马克思主义原理" value="马原" />
            <el-option label="毛中特" value="毛中特" />
            <el-option label="史纲" value="史纲" />
            <el-option label="思修法基" value="思修" />
            <el-option label="形势与政策" value="时政" />
          </el-select>
        </el-form-item>
        <el-form-item label="图片上传">
          <div class="upload-area" @paste="handlePaste">
            <el-upload
              :show-file-list="false"
              :before-upload="handleImageUpload"
              accept="image/jpeg,image/png,image/webp"
            >
              <div v-if="!addForm.image_path" class="upload-placeholder">
                <el-icon><Picture /></el-icon>
                <span>点击上传或粘贴图片</span>
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
              AI识别文字
            </el-button>
          </div>
        </el-form-item>
        <el-form-item label="背诵内容">
          <el-input
            v-model="addForm.content"
            type="textarea"
            :rows="8"
            placeholder="请输入背诵内容，或上传图片后点击AI识别自动提取"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="handleAdd">确认添加</el-button>
      </template>
    </el-dialog>

    <el-dialog title="编辑背诵内容" v-model="showEditDialog" width="700px">
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="标题">
          <el-input v-model="editForm.title" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="editForm.category" style="width: 100%">
            <el-option label="马克思主义原理" value="马原" />
            <el-option label="毛中特" value="毛中特" />
            <el-option label="史纲" value="史纲" />
            <el-option label="思修法基" value="思修" />
            <el-option label="形势与政策" value="时政" />
          </el-select>
        </el-form-item>
        <el-form-item label="掌握程度">
          <el-select v-model="editForm.mastery_level" style="width: 100%">
            <el-option label="生疏" value="生疏" />
            <el-option label="熟悉" value="熟悉" />
            <el-option label="掌握" value="掌握" />
          </el-select>
        </el-form-item>
        <el-form-item label="背诵内容">
          <el-input v-model="editForm.content" type="textarea" :rows="10" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="handleEdit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog title="背诵内容详情" v-model="showDetailDialog" width="700px">
      <div v-if="selectedRecitation">
        <div class="detail-header">
          <h3>{{ selectedRecitation.title }}</h3>
          <div class="detail-meta">
            <el-tag>{{ selectedRecitation.category }}</el-tag>
            <el-tag :type="getMasteryTagType(selectedRecitation.mastery_level)">
              {{ selectedRecitation.mastery_level }}
            </el-tag>
            <span>复习 {{ selectedRecitation.review_count }} 次</span>
          </div>
        </div>
        <div v-if="selectedRecitation.image_path" class="detail-image">
          <el-image
            :src="'/uploads/' + selectedRecitation.image_path"
            fit="contain"
            style="max-width: 100%; max-height: 300px"
          />
        </div>
        <div class="detail-content">
          <div class="formatted-text">
            <div v-for="(block, index) in formattedContentBlocks" :key="index" :class="block.type">
              <div v-if="block.type === 'heading'" class="heading-block">{{ block.content }}</div>
              <div v-else-if="block.type === 'list'" class="list-block">
                <div v-for="(item, i) in block.items" :key="i" class="list-item">{{ item }}</div>
              </div>
              <div v-else-if="block.type === 'highlight'" class="highlight-block">{{ block.content }}</div>
              <div v-else class="paragraph-block">{{ block.content }}</div>
            </div>
          </div>
        </div>
        <div class="detail-actions">
          <el-button type="primary" @click="speakContent(selectedRecitation.content)">
            <el-icon><VideoPlay /></el-icon>语音朗读
          </el-button>
          <el-button type="success" @click="markReview('已掌握')">已掌握</el-button>
          <el-button type="warning" @click="markReview('需复习')">需复习</el-button>
          <el-button type="danger" @click="markReview('未掌握')">未掌握</el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Picture, VideoPlay } from '@element-plus/icons-vue'
import {
  getRecitations, createRecitation, updateRecitation, deleteRecitation,
  uploadPoliticsImage, recognizePoliticsImage, reviewRecitation,
  type PoliticsRecitation
} from '../../api/politics'
import { useSpeech } from '@/composables/useSpeech'

const { speak: speakContent } = useSpeech()

const recitations = ref<PoliticsRecitation[]>([])
const filterCategory = ref('')
const filterLevel = ref('')
const showAddDialog = ref(false)
const showEditDialog = ref(false)
const showDetailDialog = ref(false)
const selectedRecitation = ref<PoliticsRecitation | null>(null)
const recognizing = ref(false)

interface ContentBlock {
  type: 'heading' | 'list' | 'highlight' | 'paragraph'
  content?: string
  items?: string[]
}

const formattedContentBlocks = computed<ContentBlock[]>(() => {
  if (!selectedRecitation.value?.content) return []
  
  const content = selectedRecitation.value.content
  const lines = content.split('\n')
  const blocks: ContentBlock[] = []
  
  let currentList: string[] = []
  let currentParagraph = ''
  
  for (const line of lines) {
    if (!line.trim()) {
      if (currentList.length > 0) {
        blocks.push({ type: 'list', items: [...currentList] })
        currentList = []
      }
      if (currentParagraph.trim()) {
        blocks.push({ type: 'paragraph', content: currentParagraph.trim() })
        currentParagraph = ''
      }
      continue
    }
    
    if (line.startsWith('  ') || /^\d+[.．、)]/.test(line) || /^[①②③④⑤⑥⑦⑧⑨⑩]/.test(line)) {
      if (currentParagraph.trim()) {
        blocks.push({ type: 'paragraph', content: currentParagraph.trim() })
        currentParagraph = ''
      }
      currentList.push(line.trim())
      continue
    }
    
    if (line.startsWith('◆')) {
      if (currentList.length > 0) {
        blocks.push({ type: 'list', items: [...currentList] })
        currentList = []
      }
      if (currentParagraph.trim()) {
        blocks.push({ type: 'paragraph', content: currentParagraph.trim() })
        currentParagraph = ''
      }
      blocks.push({ type: 'highlight', content: line.trim() })
      continue
    }
    
    if (/^[>【\[（]/.test(line) || line.length < 30) {
      if (currentList.length > 0) {
        blocks.push({ type: 'list', items: [...currentList] })
        currentList = []
      }
      if (currentParagraph.trim()) {
        blocks.push({ type: 'paragraph', content: currentParagraph.trim() })
        currentParagraph = ''
      }
      blocks.push({ type: 'heading', content: line.trim() })
      continue
    }
    
    if (currentList.length > 0) {
      blocks.push({ type: 'list', items: [...currentList] })
      currentList = []
    }
    currentParagraph += (currentParagraph ? ' ' : '') + line.trim()
  }
  
  if (currentList.length > 0) {
    blocks.push({ type: 'list', items: [...currentList] })
  }
  if (currentParagraph.trim()) {
    blocks.push({ type: 'paragraph', content: currentParagraph.trim() })
  }
  
  return blocks
})

const addForm = reactive({
  title: '',
  category: '马原',
  content: '',
  image_path: ''
})

const editForm = reactive({
  id: 0,
  title: '',
  category: '马原',
  content: '',
  mastery_level: '生疏'
})

function getMasteryTagType(level: string) {
  switch (level) {
    case '生疏': return 'danger'
    case '熟悉': return 'warning'
    case '掌握': return 'success'
    default: return 'info'
  }
}

async function loadRecitations() {
  try {
    const params: Record<string, string> = {}
    if (filterCategory.value) params.category = filterCategory.value
    if (filterLevel.value) params.mastery_level = filterLevel.value
    recitations.value = await getRecitations(params)
  } catch {
    recitations.value = [
      { id: 1, user_id: 1, title: '唯物辩证法的三大规律', category: '马原', content: '对立统一规律、质量互变规律、否定之否定规律...', image_path: null, mastery_level: '熟悉', review_count: 3, next_review_date: '2026-07-12', last_review_date: '2026-07-10', created_at: '2026-07-01', updated_at: '2026-07-10' },
      { id: 2, user_id: 1, title: '中国特色社会主义进入新时代', category: '毛中特', content: '新时代的内涵和意义...', image_path: null, mastery_level: '生疏', review_count: 1, next_review_date: '2026-07-11', last_review_date: '2026-07-08', created_at: '2026-07-05', updated_at: '2026-07-08' },
    ]
  }
}

async function handleImageUpload(file: File): Promise<boolean> {
  try {
    const result = await uploadPoliticsImage(file)
    addForm.image_path = result.image_path
    ElMessage.success('图片上传成功')
  } catch {
    ElMessage.error('图片上传失败')
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
        await handleImageUpload(file)
        return
      }
    }
  }
  const files = event.clipboardData?.files
  if (files && files.length > 0) {
    const imageFile = Array.from(files).find(f => f.type.startsWith('image/'))
    if (imageFile) {
      event.preventDefault()
      await handleImageUpload(imageFile)
    }
  }
}

function removeImage() {
  addForm.image_path = ''
}

function formatRecognizedText(text: string): string {
  if (!text) return ''
  
  let formatted = text
    .replace(/\r\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .replace(/\s{2,}/g, ' ')
    .trim()
  
  return formatted
}

async function handleRecognize() {
  if (!addForm.image_path) {
    ElMessage.warning('请先上传图片')
    return
  }
  recognizing.value = true
  try {
    const result = await recognizePoliticsImage(addForm.image_path)
    if (result.content) {
      const formatted = formatRecognizedText(result.content)
      addForm.content = formatted
      ElMessage.success(`识别成功，置信度: ${(result.confidence * 100).toFixed(0)}%`)
    } else {
      ElMessage.warning('未识别到文字内容')
    }
  } catch (error: any) {
    const message = error.response?.data?.detail || error.message || '识别失败'
    ElMessage.error(`识别失败: ${message}`)
  } finally {
    recognizing.value = false
  }
}

async function handleAdd() {
  if (!addForm.title.trim()) {
    ElMessage.warning('请输入标题')
    return
  }
  if (!addForm.content.trim()) {
    ElMessage.warning('请输入背诵内容')
    return
  }
  try {
    await createRecitation({
      title: addForm.title,
      category: addForm.category,
      content: addForm.content,
      image_path: addForm.image_path || undefined
    })
    ElMessage.success('添加成功')
    showAddDialog.value = false
    resetAddForm()
    loadRecitations()
  } catch (error: any) {
    const message = error.response?.data?.detail || error.message || '添加失败'
    console.error('添加政治背诵内容失败:', error)
    ElMessage.error(`添加失败: ${message}`)
  }
}

function resetAddForm() {
  addForm.title = ''
  addForm.category = '马原'
  addForm.content = ''
  addForm.image_path = ''
}

function viewRecitation(item: PoliticsRecitation) {
  selectedRecitation.value = item
  showDetailDialog.value = true
}

function editRecitation(item: PoliticsRecitation) {
  editForm.id = item.id
  editForm.title = item.title
  editForm.category = item.category
  editForm.content = item.content
  editForm.mastery_level = item.mastery_level
  showEditDialog.value = true
}

async function handleEdit() {
  try {
    await updateRecitation(editForm.id, {
      title: editForm.title,
      category: editForm.category,
      content: editForm.content,
      mastery_level: editForm.mastery_level
    })
    ElMessage.success('保存成功')
    showEditDialog.value = false
    loadRecitations()
  } catch {
    ElMessage.error('保存失败')
  }
}

async function handleDelete(item: PoliticsRecitation) {
  try {
    await ElMessageBox.confirm('确定要删除这个背诵内容吗？', '提示', { type: 'warning' })
    await deleteRecitation(item.id)
    ElMessage.success('删除成功')
    loadRecitations()
  } catch {
    // 用户取消
  }
}

async function markReview(result: string) {
  if (!selectedRecitation.value) return
  try {
    const updated = await reviewRecitation(selectedRecitation.value.id, result)
    selectedRecitation.value.mastery_level = updated.mastery_level
    selectedRecitation.value.next_review_date = updated.next_review_date
    selectedRecitation.value.review_count = updated.review_count
    ElMessage.success(`已标记为：${result}`)
    loadRecitations()
  } catch {
    ElMessage.success(`已标记为：${result}`)
  }
}

onMounted(loadRecitations)
</script>

<style scoped>
.politics-module {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.module-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.module-header h3 {
  margin: 0;
  font-size: 16px;
  color: #333;
}

.filters {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.upload-area {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
}

.upload-placeholder {
  width: 300px;
  height: 150px;
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

.upload-placeholder:hover {
  border-color: #409eff;
  color: #409eff;
}

.upload-placeholder .el-icon {
  font-size: 32px;
}

.image-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.preview-img {
  max-width: 300px;
  max-height: 200px;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
}

.detail-header {
  margin-bottom: 16px;
}

.detail-header h3 {
  margin: 0 0 8px;
  color: #333;
}

.detail-meta {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 14px;
  color: #666;
}

.detail-image {
  margin-bottom: 16px;
  text-align: center;
}

.detail-content {
  background: #f5f7fa;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 16px;
}

.formatted-text {
  font-size: 14px;
  line-height: 1.8;
  color: #333;
}

.heading-block {
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 2px solid #409eff;
}

.list-block {
  margin-bottom: 16px;
  padding-left: 20px;
}

.list-item {
  position: relative;
  padding-left: 20px;
  margin-bottom: 8px;
}

.list-item::before {
  content: '•';
  position: absolute;
  left: 0;
  color: #409eff;
  font-weight: bold;
}

.highlight-block {
  background: linear-gradient(135deg, #fff3cd 0%, #ffeeba 100%);
  border-left: 4px solid #ffc107;
  padding: 12px 16px;
  margin-bottom: 12px;
  border-radius: 0 4px 4px 0;
  font-weight: 500;
  color: #856404;
}

.paragraph-block {
  margin-bottom: 16px;
  text-align: justify;
}

.detail-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}
</style>
