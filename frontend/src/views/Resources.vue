<template>
  <div class="resources-page">
    <div class="page-header">
      <h2>资料管理</h2>
      <div class="header-actions">
        <el-button type="primary" @click="triggerUpload" v-if="activeTab === 'files'">
          <el-icon><Plus /></el-icon>上传资料
        </el-button>
        <input
          ref="fileInput"
          type="file"
          accept=".pdf,.doc,.docx,.txt,.md,.png,.jpg,.jpeg"
          class="hidden-input"
          @change="handleFileSelect"
        />
      </div>
    </div>

    <el-tabs v-model="activeTab" class="resources-tabs">
      <el-tab-pane label="📁 文件管理" name="files">
        <div v-if="knowledgeStatus" class="status-card">
          <div class="status-item">
            <el-icon><DataLine /></el-icon>
            <div class="status-info">
              <div class="status-value">{{ knowledgeStatus.document_count }}</div>
              <div class="status-label">文档数量</div>
            </div>
          </div>
          <div class="status-item">
            <el-icon><FolderOpened /></el-icon>
            <div class="status-info">
              <div class="status-value">{{ knowledgeStatus.total_chunks }}</div>
              <div class="status-label">索引块数</div>
            </div>
          </div>
          <div class="status-item">
            <el-icon><Connection /></el-icon>
            <div class="status-info">
              <div class="status-value">{{ knowledgeStatus.index_size || 0 }}</div>
              <div class="status-label">向量索引</div>
            </div>
          </div>
        </div>

        <div class="filter-bar">
          <span class="filter-label">学科筛选：</span>
          <el-select v-model="filterSubject" placeholder="全部学科" clearable @change="loadResources" class="subject-filter">
            <el-option label="全部" value="" />
            <el-option v-for="s in SUBJECTS" :key="s" :label="s" :value="s" />
          </el-select>
          <el-input
            v-model="searchQuery"
            placeholder="搜索文件名..."
            clearable
            @keyup.enter="handleSearch"
            class="search-input"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-button @click="handleSearch">搜索</el-button>
        </div>

        <div v-if="resources.length > 0" class="resources-grid">
          <el-card
            v-for="resource in resources"
            :key="resource.id"
            class="resource-card"
            @click="openDocument(resource)"
          >
            <div class="resource-icon">
              {{ getFileIcon(resource.file_type) }}
            </div>
            <div class="resource-info">
              <div class="resource-name">{{ resource.filename }}</div>
              <div class="resource-meta">
                <span class="subject-tag">{{ resource.subject || '未分类' }}</span>
                <span>{{ getFileSize(resource.file_size) }}</span>
                <span>{{ formatDate(resource.created_at) }}</span>
                <span v-if="resource.indexed_at" class="indexed-badge">已索引</span>
              </div>
            </div>
            <div class="resource-actions">
              <el-button type="text" size="small" @click.stop="openDocument(resource)" title="打开">
                <el-icon><View /></el-icon>
              </el-button>
              <el-button type="text" size="small" @click.stop="openResourceDetail(resource)" title="详情">
                <el-icon><InfoFilled /></el-icon>
              </el-button>
              <el-button type="text" size="small" @click.stop="handleDelete(resource.id)" title="删除">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </el-card>
        </div>
        <div v-if="resources.length === 0" class="empty-tip">
          <el-icon><FolderOpened /></el-icon>暂无资料，点击上方按钮上传
        </div>
      </el-tab-pane>

      <el-tab-pane label="🤖 AI资料检索" name="chat">
        <div class="chat-container">
          <ResourceChat ref="resourceChatRef" />
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-dialog
      v-model="showDetail"
      :title="selectedResource?.filename || '资料详情'"
      width="600px"
    >
      <div v-if="selectedResource" class="detail-content">
        <div class="detail-row">
          <span class="detail-label">文件类型：</span>
          <span>{{ selectedResource.file_type.toUpperCase() }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">文件大小：</span>
          <span>{{ getFileSize(selectedResource.file_size) }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">上传时间：</span>
          <span>{{ formatDate(selectedResource.created_at) }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">索引状态：</span>
          <span v-if="selectedResource.indexed_at" class="indexed-badge">已索引</span>
          <span v-else class="not-indexed">未索引</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">分块数量：</span>
          <span>{{ selectedResource.chunk_count || 0 }}</span>
        </div>
        <div v-if="indexing" class="index-progress">
          <div class="progress-label">{{ indexProgressMessage }}</div>
          <el-progress 
            :percentage="indexProgress" 
            :status="indexProgressStatus"
            :stroke-width="16"
            class="progress-bar"
          />
          <el-button 
            type="danger" 
            size="small" 
            class="cancel-btn"
            @click="handleCancelIndex"
          >
            取消索引
          </el-button>
        </div>
      </div>
      <template #footer>
        <el-button @click="showDetail = false">关闭</el-button>
        <el-button 
          v-if="selectedResource && !indexing" 
          type="primary" 
          @click="handleIndex"
        >
          {{ selectedResource.indexed_at ? '重新索引' : '开始索引' }}
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="showUploadDialog"
      title="确认上传"
      width="400px"
    >
      <div v-if="selectedFile" class="upload-dialog-content">
        <div class="upload-icon">📁</div>
        <div class="upload-info">
          <div class="upload-filename">{{ selectedFile.name }}</div>
          <div class="upload-size">{{ getFileSize(selectedFile.size) }}</div>
        </div>
        <div class="upload-subject-select">
          <span class="upload-subject-label">所属学科：</span>
          <el-select v-model="uploadSubject" placeholder="选择学科" class="upload-subject-picker">
            <el-option label="未分类" value="未分类" />
            <el-option v-for="s in SUBJECTS" :key="s" :label="s" :value="s" />
          </el-select>
        </div>
        <div v-if="uploading" class="upload-progress">
          <el-progress
            :percentage="uploadProgress"
            :stroke-width="12"
            :status="uploadProgressStatus"
          />
          <span class="upload-progress-text">{{ uploadProgress }}%</span>
        </div>
      </div>
      <template #footer>
        <el-button @click="cancelUpload" :disabled="uploading">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="confirmUpload">
          {{ uploading ? '上传中...' : '确认上传' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, View, InfoFilled, Delete, FolderOpened, DataLine, Connection } from '@element-plus/icons-vue'
import ResourceChat from './recitation/ResourceChat.vue'
import {
  uploadDocument, getDocuments, deleteDocument, getKnowledgeStatus, indexDocument, cancelIndexDocument, getDocumentDownloadUrl, getDocumentPreviewUrl,
  type RAGDocument, type KnowledgeStatus
} from '../api/rag'

// 学科列表（与推荐模块保持一致）
const SUBJECTS = ['数学', '英语', '政治', '马原', '毛中特', '史纲', '思修', '时政', '专业课']

const activeTab = ref('files')
const resources = ref<RAGDocument[]>([])
const searchQuery = ref('')
const resourceChatRef = ref<InstanceType<typeof ResourceChat> | null>(null)
const filterSubject = ref<string>('')           // 文件列表筛选学科
const uploadSubject = ref<string>('未分类')      // 上传时选择的学科
const showDetail = ref(false)
const selectedResource = ref<RAGDocument | null>(null)
const knowledgeStatus = ref<KnowledgeStatus | null>(null)
const showKnowledgeSearchResult = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const showUploadDialog = ref(false)
const selectedFile = ref<File | null>(null)
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadProgressStatus = ref<'success' | 'exception' | 'warning' | undefined>(undefined)
const indexing = ref(false)
const indexProgress = ref(0)
const indexProgressMessage = ref('准备开始')
const indexProgressStatus = ref<'success' | 'exception' | 'warning' | undefined>(undefined)
let progressEventSource: EventSource | null = null

function getFileIcon(fileType: string) {
  const icons: Record<string, string> = {
    pdf: '📄',
    doc: '📝',
    docx: '📝',
    txt: '📄',
    md: '📝',
    png: '🖼️',
    jpg: '🖼️',
    jpeg: '🖼️'
  }
  return icons[fileType] || '📁'
}

function getFileSize(bytes: number) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatDate(dateStr: string | null) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

async function loadResources() {
  try {
    resources.value = await getDocuments(filterSubject.value || undefined)
    await loadKnowledgeStatus()
  } catch {
    resources.value = []
  }
}

async function loadKnowledgeStatus() {
  try {
    knowledgeStatus.value = await getKnowledgeStatus()
  } catch {
    knowledgeStatus.value = null
  }
}

function triggerUpload() {
  if (fileInput.value) {
    fileInput.value.click()
  }
}

function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    selectedFile.value = target.files[0]
    showUploadDialog.value = true
  }
}

async function confirmUpload() {
  if (!selectedFile.value) {
    ElMessage.warning('请选择文件')
    return
  }
  
  uploading.value = true
  uploadProgress.value = 0
  uploadProgressStatus.value = undefined
  try {
    await uploadDocument(selectedFile.value, uploadSubject.value || undefined, (progress) => {
      uploadProgress.value = progress
    })
    uploadProgress.value = 100
    uploadProgressStatus.value = 'success'
    ElMessage.success('上传成功')
    await loadResources()
    setTimeout(() => {
      showUploadDialog.value = false
      selectedFile.value = null
      uploadProgress.value = 0
      uploadProgressStatus.value = undefined
      if (fileInput.value) {
        fileInput.value.value = ''
      }
    }, 500)
  } catch (error: any) {
    uploadProgressStatus.value = 'exception'
    const errorMsg = error.response?.data?.detail || 
                     error.message || 
                     '上传失败，请检查网络连接或文件大小'
    ElMessage.error(errorMsg)
    console.error('上传错误:', error)
  } finally {
    uploading.value = false
  }
}

function cancelUpload() {
  showUploadDialog.value = false
  selectedFile.value = null
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

async function handleSearch() {
  showKnowledgeSearchResult.value = false
  try {
    if (searchQuery.value.trim()) {
      const allResources = await getDocuments(filterSubject.value || undefined)
      resources.value = allResources.filter(r =>
        r.filename.toLowerCase().includes(searchQuery.value.trim().toLowerCase())
      )
    } else {
      await loadResources()
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '搜索失败')
  }
}

function openDocument(resource: RAGDocument) {
  if (resource.file_type === 'pdf') {
    const url = getDocumentPreviewUrl(resource.id)
    window.open(url, '_blank', 'noopener,noreferrer')
  } else {
    const url = getDocumentDownloadUrl(resource.id)
    window.open(url, '_blank')
  }
}

function openResourceDetail(resource: RAGDocument) {
  selectedResource.value = resource
  showDetail.value = true
}

async function handleDelete(id: number) {
  try {
    await ElMessageBox.confirm('确定要删除该资料吗？删除后将从知识库中移除', '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await deleteDocument(id)
    ElMessage.success('删除成功')
    await loadResources()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

async function handleIndex() {
  if (!selectedResource.value) return
  
  indexing.value = true
  indexProgress.value = 0
  indexProgressMessage.value = '准备开始'
  indexProgressStatus.value = undefined
  
  const documentId = selectedResource.value.id
  
  try {
    await indexDocument(documentId)
  } catch (error: any) {
    const errorMsg = error.response?.data?.detail || '启动索引失败'
    ElMessage.error(errorMsg)
    indexing.value = false
    return
  }
  
  await new Promise<void>((resolve) => {
    const token = localStorage.getItem('token')
    progressEventSource = new EventSource(`/api/rag/documents/${documentId}/index/progress?token=${token}`)
    
    progressEventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        indexProgress.value = data.progress
        indexProgressMessage.value = data.message
        
        if (data.status === 'completed') {
          indexProgressStatus.value = 'success'
          progressEventSource?.close()
          resolve()
        } else if (data.status === 'failed') {
          indexProgressStatus.value = 'exception'
          progressEventSource?.close()
          resolve()
        } else if (data.status === 'cancelled') {
          indexProgressStatus.value = 'exception'
          progressEventSource?.close()
          resolve()
        }
      } catch (e) {
        console.error('解析进度数据失败:', e)
      }
    }
    
    progressEventSource.onerror = () => {
      progressEventSource?.close()
      resolve()
    }
  })
  
  try {
    if (indexProgressMessage.value === '用户已取消索引') {
      ElMessage.info('索引已取消')
    } else if (indexProgressStatus.value === 'success') {
      ElMessage.success('索引创建成功')
      showDetail.value = false
      await loadResources()
    } else if (indexProgressStatus.value === 'exception') {
      ElMessage.error(indexProgressMessage.value || '索引失败')
    }
  } catch (error: any) {
    console.error('索引完成后处理错误:', error)
  } finally {
    indexing.value = false
    progressEventSource?.close()
    progressEventSource = null
  }
}

async function handleCancelIndex() {
  if (!selectedResource.value) return
  
  try {
    const result = await cancelIndexDocument(selectedResource.value.id)
    if (result.success) {
      ElMessage.info('索引已取消')
    } else {
      ElMessage.warning(result.message || '没有正在进行的索引任务')
    }
  } catch (error: any) {
    ElMessage.error('取消失败')
  }
}

onMounted(() => {
  loadResources()
})
</script>

<style scoped>
.resources-page {
  padding: 20px;
  width: 100%;
  box-sizing: border-box;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
}

.resources-tabs {
  margin-top: 10px;
}

.resources-tabs :deep(.el-tabs__content) {
  padding: 20px 0;
}

.chat-container {
  min-height: 75vh;
  height: calc(100vh - 200px);
  width: 100%;
  display: flex;
}

.status-card {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-item .el-icon {
  font-size: 24px;
  color: #667eea;
}

.status-info {
  display: flex;
  flex-direction: column;
}

.status-value {
  font-size: 20px;
  font-weight: 600;
  color: #333;
}

.status-label {
  font-size: 12px;
  color: #909399;
}

.search-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
  align-items: center;
}

.search-input {
  width: 250px;
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.filter-label {
  font-size: 14px;
  color: #606266;
  font-weight: 500;
}

.subject-filter {
  width: 160px;
}

.subject-tag {
  display: inline-block;
  padding: 1px 6px;
  background: #ecf5ff;
  color: #409eff;
  border-radius: 4px;
  font-size: 12px;
  margin-right: 0;
  white-space: nowrap;
  flex-shrink: 0;
}

.upload-subject-select {
  width: 100%;
  margin-top: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.upload-subject-label {
  font-size: 14px;
  color: #606266;
  white-space: nowrap;
}

.upload-subject-picker {
  flex: 1;
}

.resources-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.resource-card {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  transition: box-shadow 0.2s;
}

.resource-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.resource-icon {
  font-size: 32px;
}

.resource-info {
  flex: 1;
  min-width: 0;
}

.resource-name {
  font-size: 14px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.resource-meta {
  display: flex;
  flex-wrap: nowrap;
  gap: 8px;
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  white-space: nowrap;
  overflow: hidden;
}

.resource-meta span {
  white-space: nowrap;
  flex-shrink: 0;
}

.indexed-badge {
  background: #67c23a;
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.not-indexed {
  color: #f56c6c;
  font-weight: 500;
}

.resource-actions {
  display: flex;
  gap: 8px;
}

.empty-tip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 40px;
  background: #f5f7fa;
  border-radius: 8px;
  color: #909399;
  justify-content: center;
}

.detail-content {
  padding: 10px 0;
}

.detail-row {
  display: flex;
  margin-bottom: 12px;
  font-size: 14px;
}

.detail-label {
  font-weight: 600;
  width: 100px;
  color: #666;
}

.index-progress {
  margin-top: 20px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
}

.progress-label {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

.progress-bar {
  margin-top: 8px;
}

.cancel-btn {
  margin-top: 12px;
}

.hidden-input {
  display: none;
}

.upload-dialog-content {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 0;
}

.upload-icon {
  font-size: 48px;
}

.upload-info {
  flex: 1;
}

.upload-filename {
  font-size: 16px;
  font-weight: 500;
  color: #333;
}

.upload-size {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}

.upload-progress {
  width: 100%;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #eee;
}

.upload-progress-text {
  display: block;
  text-align: center;
  margin-top: 8px;
  font-size: 14px;
  color: #666;
}

.knowledge-search-results {
  margin-top: 20px;
}

.knowledge-search-results h3 {
  margin-bottom: 16px;
  font-size: 16px;
  color: #333;
}

.ai-answer-card {
  margin-bottom: 20px;
  padding: 20px;
}

.ai-answer-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.ai-icon {
  font-size: 24px;
}

.ai-label {
  font-size: 16px;
  font-weight: 600;
  color: #667eea;
}

.ai-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px;
  color: #666;
}

.ai-answer-content {
  font-size: 15px;
  line-height: 1.8;
  color: #333;
}

.ai-answer-content h1,
.ai-answer-content h2,
.ai-answer-content h3,
.ai-answer-content h4,
.ai-answer-content h5,
.ai-answer-content h6 {
  font-weight: 600;
  margin-top: 20px;
  margin-bottom: 10px;
  color: #333;
}

.ai-answer-content h1 { font-size: 24px; }
.ai-answer-content h2 { font-size: 20px; }
.ai-answer-content h3 { font-size: 18px; }
.ai-answer-content h4 { font-size: 16px; }

.ai-answer-content p {
  margin-bottom: 12px;
}

.ai-answer-content ul,
.ai-answer-content ol {
  margin-bottom: 12px;
  padding-left: 24px;
}

.ai-answer-content li {
  margin-bottom: 6px;
}

.ai-answer-content strong {
  font-weight: 600;
  color: #333;
}

.ai-answer-content em {
  font-style: italic;
}

.ai-answer-content blockquote {
  border-left: 4px solid #667eea;
  padding-left: 16px;
  margin: 16px 0;
  color: #666;
  background: #f5f7fa;
  padding: 12px 16px;
  border-radius: 0 8px 8px 0;
}

.ai-answer-content code {
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 14px;
}

.ai-answer-content pre {
  background: #f5f7fa;
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin-bottom: 12px;
}

.ai-answer-content pre code {
  background: none;
  padding: 0;
}

.ai-answer-content a {
  color: #667eea;
  text-decoration: none;
}

.ai-answer-content a:hover {
  text-decoration: underline;
}

.ai-answer-content hr {
  border: none;
  border-top: 1px solid #eee;
  margin: 20px 0;
}

.ai-answer-content .latex-formula {
  font-family: 'KaTeX_Main', 'Times New Roman', serif;
}

.ai-answer-content .latex-formula.block {
  display: block;
  text-align: center;
  margin: 16px 0;
  font-size: 18px;
}

.ai-answer-content .katex {
  font-size: 1.1em;
}

.ai-answer-content .katex-display {
  display: block;
  margin: 16px 0;
  text-align: center;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 4px 0;
}

.ai-answer-content .katex-display::-webkit-scrollbar {
  height: 6px;
}

.ai-answer-content .katex-display::-webkit-scrollbar-track {
  background: #f0f0f0;
}

.ai-answer-content .katex-display::-webkit-scrollbar-thumb {
  background: #ccc;
  border-radius: 3px;
}

.ai-answer-content .katex-display::-webkit-scrollbar-thumb:hover {
  background: #999;
}

.ai-answer-content .math-error {
  color: #e74c3c;
  font-family: monospace;
  background: #fff5f5;
  padding: 2px 6px;
  border-radius: 3px;
}

.knowledge-sources-section {
  margin-top: 20px;
}

.sources-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.sources-header h4 {
  margin: 0;
  font-size: 14px;
  color: #666;
}

.knowledge-results-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.knowledge-result-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.result-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chunk-info {
  font-size: 12px;
  color: #999;
}

.source-tag {
  margin-left: 8px;
}

.knowledge-score {
  width: 120px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  color: #333;
  border-radius: 6px;
  flex-shrink: 0;
}

.knowledge-content {
  flex: 1;
}

.knowledge-filename {
  font-size: 14px;
  font-weight: 500;
  color: #667eea;
  margin-bottom: 8px;
}

.knowledge-text {
  font-size: 14px;
  color: #666;
  line-height: 1.6;
  max-height: 80px;
  overflow: hidden;
  transition: max-height 0.3s ease;
}

.knowledge-text.collapsed {
  max-height: 80px;
}

.knowledge-text:not(.collapsed) {
  max-height: none;
}

.search-progress-container {
  margin-bottom: 20px;
  padding: 16px;
  background: #f0f9ff;
  border-radius: 8px;
  border: 1px solid #b3d9ff;
}

.search-progress {
  max-width: 500px;
  margin: 0 auto;
}

.search-progress .progress-text {
  font-size: 13px;
  color: #fff;
}

.progress-message {
  text-align: center;
  margin-top: 10px;
  font-size: 14px;
  color: #409eff;
  font-weight: 500;
}
</style>
