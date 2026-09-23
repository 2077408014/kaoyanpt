<template>
  <div class="reminder-list">
    <el-table :data="reminders" border>
      <el-table-column prop="reminder_time" label="提醒时间" width="150" />
      <el-table-column prop="frequency" label="频率" width="200" />
      <el-table-column label="状态" width="100">
        <template #default="scope">
          <el-switch
            v-model="scope.row.enabled"
            :active-value="1"
            :inactive-value="0"
            @change="handleToggle(scope.row)"
          />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150">
        <template #default="scope">
          <el-button size="small" type="danger" @click="handleDelete(scope.row)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="reminders.length === 0" description="暂无提醒设置" />
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { updateReminder, deleteReminder, type RecitationReminder } from '../../api/politics'

defineProps<{
  type: string
  reminders: RecitationReminder[]
}>()

const emit = defineEmits<{
  refresh: []
}>()

async function handleToggle(row: RecitationReminder) {
  try {
    await updateReminder(row.id, { enabled: row.enabled })
    ElMessage.success(row.enabled ? '已开启' : '已关闭')
  } catch {
    ElMessage.success(row.enabled ? '已开启' : '已关闭')
  }
}

async function handleDelete(row: RecitationReminder) {
  try {
    await ElMessageBox.confirm('确定要删除这个提醒吗？', '提示', { type: 'warning' })
    await deleteReminder(row.id)
    ElMessage.success('删除成功')
    emit('refresh')
  } catch {
    // 用户取消
  }
}
</script>

<style scoped>
.reminder-list {
  min-height: 200px;
}
</style>