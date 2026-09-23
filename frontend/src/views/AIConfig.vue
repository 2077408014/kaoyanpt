<template>
  <div class="ai-config-page">
    <div class="page-header">
      <h2>AI配置</h2>
      <el-button type="primary" @click="goBack">返回AI问答</el-button>
    </div>

    <!-- 已保存的配置列表 -->
    <div class="config-card">
      <div class="section-header">
        <h3>已保存的配置</h3>
        <el-tag v-if="activeConfigId" type="success">当前已选择厂商</el-tag>
        <el-tag v-else type="info">未选择厂商（使用默认配置）</el-tag>
      </div>

      <div v-if="configs.length > 0" class="config-list">
        <el-card
          v-for="config in configs"
          :key="config.id"
          class="config-item-card"
          :class="{ active: config.id === activeConfigId }"
          shadow="hover"
        >
          <div class="config-header">
            <div class="config-title">
              <el-tag :type="getProviderTagType(config.provider)">{{ getProviderLabel(config.provider) }}</el-tag>
              <span class="config-name">{{ config.name }}</span>
              <el-tag v-if="config.id === activeConfigId" type="success" effect="dark" size="small">当前使用</el-tag>
            </div>
            <div class="config-model">{{ config.model }}</div>
          </div>
          <div class="config-meta">
            <span class="config-date">创建于 {{ formatDate(config.created_at) }}</span>
          </div>
          <div class="config-actions">
            <el-button
              v-if="config.id !== activeConfigId"
              type="primary"
              size="small"
              :loading="switchingId === config.id"
              @click="handleSwitch(config.id)"
            >
              <el-icon><Check /></el-icon>使用
            </el-button>
            <el-button
              v-else
              type="warning"
              size="small"
              :loading="switchingId === config.id"
              @click="handleDeactivate"
            >
              <el-icon><CircleClose /></el-icon>停用
            </el-button>
            <el-button
              size="small"
              @click="handleEdit(config)"
            >
              <el-icon><Edit /></el-icon>编辑
            </el-button>
            <el-button
              type="danger"
              plain
              size="small"
              :loading="deletingId === config.id"
              @click="handleDelete(config)"
            >
              <el-icon><Delete /></el-icon>删除
            </el-button>
          </div>
        </el-card>
      </div>
      <div v-else class="empty-tip">
        <el-icon><InfoFilled /></el-icon>
        <span>暂无配置，点击下方按钮添加</span>
      </div>
    </div>

    <!-- 添加配置 -->
    <div class="config-card">
      <div class="section-header">
        <h3>添加新配置</h3>
      </div>
      <el-form :model="form" label-width="120px" class="config-form">
        <el-form-item label="配置名称">
          <el-input v-model="form.name" placeholder="如：我的DeepSeek" />
        </el-form-item>
        <el-form-item label="服务提供商">
          <el-radio-group v-model="form.provider" @change="onProviderChange">
            <el-radio-button label="deepseek">DeepSeek</el-radio-button>
            <el-radio-button label="zhipu">智谱AI</el-radio-button>
            <el-radio-button label="openai">OpenAI</el-radio-button>
            <el-radio-button label="custom">自定义</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="API Key">
          <el-input
            v-model="form.apiKey"
            type="password"
            placeholder="请输入您的API Key"
            show-password
          />
        </el-form-item>
        <el-form-item label="API Base URL">
          <el-input v-model="form.baseUrl" placeholder="API接口地址" />
        </el-form-item>
        <el-form-item label="模型名称">
          <el-input v-model="form.model" placeholder="模型名称" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="saving" @click="handleSave">
            <el-icon><Plus /></el-icon>保存配置
          </el-button>
          <el-button @click="resetForm">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 编辑对话框 -->
    <el-dialog v-model="editDialogVisible" title="编辑配置" width="560px">
      <el-form :model="editForm" label-width="120px">
        <el-form-item label="配置名称">
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="服务提供商">
          <el-radio-group v-model="editForm.provider" @change="onEditProviderChange">
            <el-radio-button label="deepseek">DeepSeek</el-radio-button>
            <el-radio-button label="zhipu">智谱AI</el-radio-button>
            <el-radio-button label="openai">OpenAI</el-radio-button>
            <el-radio-button label="custom">自定义</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="API Key">
          <el-input v-model="editForm.apiKey" type="password" show-password />
        </el-form-item>
        <el-form-item label="API Base URL">
          <el-input v-model="editForm.baseUrl" />
        </el-form-item>
        <el-form-item label="模型名称">
          <el-input v-model="editForm.model" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="updating" @click="handleUpdate">保存</el-button>
      </template>
    </el-dialog>

    <div class="tips-card">
      <h3>使用说明</h3>
      <ul>
        <li>您可以保存多个不同厂商的 AI 配置，随时切换使用</li>
        <li>点击<strong>使用</strong>按钮即可将该配置设为当前活跃的 AI 服务</li>
        <li>点击<strong>停用</strong>按钮可停用当前配置，系统将使用环境变量中的默认配置</li>
        <li><strong>DeepSeek</strong>：默认 https://api.deepseek.com/v1，模型 deepseek-chat</li>
        <li><strong>智谱AI</strong>：默认 https://open.bigmodel.cn/api/paas/v4，模型 glm-4</li>
        <li><strong>OpenAI</strong>：默认 https://api.openai.com/v1，模型 gpt-3.5-turbo</li>
        <li><strong>自定义</strong>：支持其他兼容 OpenAI 接口的 AI 服务</li>
        <li>API Key 是您的个人密钥，请妥善保管</li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Check, Delete, Edit, Plus, InfoFilled, CircleClose } from '@element-plus/icons-vue'
import {
  listAIConfigs, createAIConfig, updateAIConfig, deleteAIConfig, switchAIConfig, getAIConfig,
  type AIConfigItem, type AIConfigCreateData
} from '../api/ai_config'
import { getMe, type User } from '../api/auth'

const router = useRouter()

const configs = ref<AIConfigItem[]>([])
const activeConfigId = ref<number | null>(null)
const saving = ref(false)
const updating = ref(false)
const switchingId = ref<number | null>(null)
const deletingId = ref<number | null>(null)
const editDialogVisible = ref(false)
const editingId = ref<number | null>(null)

const form = reactive({
  name: '',
  provider: 'deepseek',
  apiKey: '',
  baseUrl: '',
  model: ''
})

const editForm = reactive({
  name: '',
  provider: 'deepseek',
  apiKey: '',
  baseUrl: '',
  model: ''
})

const providerDefaults: Record<string, { baseUrl: string; model: string; label: string; tagType: string }> = {
  deepseek: {
    baseUrl: 'https://api.deepseek.com/v1',
    model: 'deepseek-v4-pro',
    label: 'DeepSeek',
    tagType: 'primary'
  },
  zhipu: {
    baseUrl: 'https://open.bigmodel.cn/api/paas/v4',
    model: 'glm-4',
    label: '智谱AI',
    tagType: 'warning'
  },
  openai: {
    baseUrl: 'https://api.openai.com/v1',
    model: 'gpt-3.5-turbo',
    label: 'OpenAI',
    tagType: 'success'
  },
  custom: {
    baseUrl: '',
    model: '',
    label: '自定义',
    tagType: 'info'
  }
}

function getProviderLabel(provider: string) {
  return providerDefaults[provider]?.label || provider
}

function getProviderTagType(provider: string) {
  return providerDefaults[provider]?.tagType || 'info'
}

function formatDate(iso: string) {
  if (!iso) return '-'
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function onProviderChange() {
  const defaults = providerDefaults[form.provider]
  if (defaults) {
    form.baseUrl = defaults.baseUrl
    form.model = defaults.model
  }
}

function onEditProviderChange() {
  const defaults = providerDefaults[editForm.provider]
  if (defaults) {
    editForm.baseUrl = defaults.baseUrl
    editForm.model = defaults.model
  }
}

function resetForm() {
  form.name = ''
  form.provider = 'deepseek'
  form.apiKey = ''
  form.baseUrl = providerDefaults.deepseek.baseUrl
  form.model = providerDefaults.deepseek.model
}

async function loadData() {
  try {
    const user: User = await getMe()
    activeConfigId.value = user.active_ai_config_id || null
  } catch {
    // ignore
  }
  try {
    configs.value = await listAIConfigs()
  } catch {
    configs.value = []
  }
}

async function handleSave() {
  if (!form.name.trim()) {
    ElMessage.warning('请输入配置名称')
    return
  }
  if (!form.apiKey.trim()) {
    ElMessage.warning('请输入API Key')
    return
  }
  if (!form.baseUrl.trim()) {
    ElMessage.warning('请输入API Base URL')
    return
  }
  if (!form.model.trim()) {
    ElMessage.warning('请输入模型名称')
    return
  }

  saving.value = true
  try {
    const data: AIConfigCreateData = {
      name: form.name.trim(),
      provider: form.provider,
      api_key: form.apiKey.trim(),
      base_url: form.baseUrl.trim(),
      model: form.model.trim()
    }
    await createAIConfig(data)
    ElMessage.success('配置保存成功')
    resetForm()
    await loadData()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleSwitch(configId: number) {
  switchingId.value = configId
  try {
    await switchAIConfig(configId)
    activeConfigId.value = configId
    ElMessage.success('已切换至该配置')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '切换失败')
  } finally {
    switchingId.value = null
  }
}

async function handleDeactivate() {
  try {
    await ElMessageBox.confirm(
      '确定要停用当前配置吗？停用后将使用系统默认配置（环境变量）。',
      '停用确认',
      { type: 'warning', confirmButtonText: '停用', cancelButtonText: '取消' }
    )
  } catch {
    return
  }

  switchingId.value = activeConfigId.value
  try {
    await switchAIConfig(null)
    activeConfigId.value = null
    ElMessage.success('已停用，将使用系统默认配置')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '停用失败')
  } finally {
    switchingId.value = null
  }
}

async function handleEdit(config: AIConfigItem) {
  editingId.value = config.id
  editForm.name = config.name
  editForm.provider = config.provider
  editForm.apiKey = ''
  editForm.baseUrl = ''
  editForm.model = config.model

  editDialogVisible.value = true

  // 加载完整信息填充表单（含 api_key、base_url）
  try {
    const detail = await getAIConfig(config.id)
    editForm.apiKey = detail.api_key || ''
    editForm.baseUrl = detail.base_url || ''
    editForm.model = detail.model || config.model
    editForm.provider = detail.provider || config.provider
    editForm.name = detail.name || config.name
  } catch {
    // 加载失败则保持已有信息
  }
}

async function handleUpdate() {
  if (!editingId.value) return
  if (!editForm.name.trim()) {
    ElMessage.warning('请输入配置名称')
    return
  }
  if (!editForm.apiKey.trim()) {
    ElMessage.warning('请输入API Key')
    return
  }
  if (!editForm.baseUrl.trim()) {
    ElMessage.warning('请输入API Base URL')
    return
  }
  if (!editForm.model.trim()) {
    ElMessage.warning('请输入模型名称')
    return
  }

  updating.value = true
  try {
    await updateAIConfig(editingId.value, {
      name: editForm.name.trim(),
      provider: editForm.provider,
      api_key: editForm.apiKey.trim(),
      base_url: editForm.baseUrl.trim(),
      model: editForm.model.trim()
    })
    ElMessage.success('配置更新成功')
    editDialogVisible.value = false
    await loadData()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '更新失败')
  } finally {
    updating.value = false
  }
}

async function handleDelete(config: AIConfigItem) {
  try {
    await ElMessageBox.confirm(
      `确定删除配置「${config.name}」吗？删除后无法恢复。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消', confirmButtonClass: 'el-button--danger' }
    )
  } catch {
    return
  }

  deletingId.value = config.id
  try {
    await deleteAIConfig(config.id)
    if (activeConfigId.value === config.id) {
      activeConfigId.value = null
    }
    ElMessage.success('已删除')
    await loadData()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '删除失败')
  } finally {
    deletingId.value = null
  }
}

function goBack() {
  router.push('/dashboard/ai')
}

onMounted(() => {
  resetForm()
  loadData()
})
</script>

<style scoped>
.ai-config-page {
  padding: 20px;
  max-width: 900px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-header h2 {
  margin: 0;
  font-size: 24px;
  color: #333;
}

.config-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  padding: 24px;
  margin-bottom: 20px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.section-header h3 {
  margin: 0;
  font-size: 16px;
  color: #333;
}

.config-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.config-item-card {
  transition: all 0.3s;
}

.config-item-card.active {
  border: 2px solid #67c23a;
  background: #f0f9eb;
}

.config-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.config-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.config-name {
  font-size: 15px;
  font-weight: 600;
  color: #333;
}

.config-model {
  font-size: 13px;
  color: #666;
}

.config-meta {
  margin-bottom: 12px;
}

.config-date {
  font-size: 12px;
  color: #999;
}

.config-actions {
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

.config-form {
  padding: 8px 0;
}

.tips-card {
  background: #fef9f5;
  border-radius: 12px;
  padding: 20px;
  border-left: 4px solid #f5a623;
}

.tips-card h3 {
  margin: 0 0 12px;
  font-size: 16px;
  color: #333;
}

.tips-card ul {
  margin: 0;
  padding-left: 20px;
}

.tips-card li {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

.tips-card li:last-child {
  margin-bottom: 0;
}

.tips-card strong {
  color: #333;
}
</style>
