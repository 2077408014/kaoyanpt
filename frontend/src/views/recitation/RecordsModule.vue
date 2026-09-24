<template>
  <div class="records-module">
    <div class="module-header">
      <h3>背诵记录</h3>
      <div class="header-actions">
        <el-button type="primary" @click="handleExport">
          <el-icon><Download /></el-icon>导出 Excel
        </el-button>
        <el-button type="success" @click="triggerImport">
          <el-icon><Upload /></el-icon>导入复习
        </el-button>
        <input
          ref="importInput"
          type="file"
          accept=".xlsx,.xls"
          class="hidden-input"
          @change="handleImport"
        />
      </div>
    </div>

    <el-table :data="records" border>
      <el-table-column prop="created_at" label="时间" width="180">
        <template #default="scope">
          {{ scope.row.created_at ? scope.row.created_at.substring(0, 16) : '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="session_id" label="会话ID" width="120" show-overflow-tooltip />
      <el-table-column prop="source" label="来源" width="90">
        <template #default="scope">
          <el-tag>{{ ({ card: '卡片', push: '弹卡', quiz: '测验' } as Record<string, string>)[scope.row.source] || scope.row.source }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="total" label="单词数" width="90" />
      <el-table-column label="忘记" width="70">
        <template #default="scope"><span style="color:#f56c6c">{{ scope.row.forgot }}</span></template>
      </el-table-column>
      <el-table-column label="困难" width="70">
        <template #default="scope"><span style="color:#e6a23c">{{ scope.row.hard }}</span></template>
      </el-table-column>
      <el-table-column label="一般" width="70">
        <template #default="scope"><span style="color:#909399">{{ scope.row.good }}</span></template>
      </el-table-column>
      <el-table-column label="认识" width="70">
        <template #default="scope"><span style="color:#67c23a">{{ scope.row.known }}</span></template>
      </el-table-column>
    </el-table>

    <div class="pagination">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="loadRecords"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, Upload } from '@element-plus/icons-vue'
import {
  getStudyRecords, exportStudyRecords, importStudyRecords,
  type RecordSummaryItem
} from '@/api/words'

const records = ref<RecordSummaryItem[]>([])
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)
const importInput = ref<HTMLInputElement | null>(null)

async function loadRecords() {
  try {
    const res = await getStudyRecords(page.value, pageSize.value)
    records.value = res.items
    total.value = res.total
  } catch {
    records.value = []
    total.value = 0
  }
}

async function handleExport() {
  try {
    await exportStudyRecords()
    ElMessage.success('已导出')
  } catch {
    ElMessage.error('导出失败')
  }
}

function triggerImport() {
  importInput.value?.click()
}

async function handleImport(event: Event) {
  const target = event.target as HTMLInputElement
  if (!target.files?.length) return
  const file = target.files[0]
  try {
    const res = await importStudyRecords(file)
    ElMessage.success(res.message || '导入成功')
    await loadRecords()
  } catch (error: any) {
    const msg = error.response?.data?.detail || error.message || '导入失败'
    ElMessage.error(msg)
  } finally {
    if (importInput.value) importInput.value.value = ''
  }
}

onMounted(loadRecords)
</script>

<style scoped>
.records-module { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06); }
.module-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.module-header h3 { margin: 0; font-size: 16px; color: #333; }
.header-actions { display: flex; gap: 8px; }
.pagination { margin-top: 16px; text-align: right; }
.hidden-input { display: none; }
</style>