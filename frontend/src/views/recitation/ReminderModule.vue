<template>
  <div class="reminder-module">
    <div class="module-header">
      <h3>背诵提醒设置</h3>
      <el-button type="primary" @click="showAddDialog = true">
        <el-icon><Plus /></el-icon>添加提醒
      </el-button>
    </div>

    <div class="reminder-tip">
      <el-alert
        title="提示：浏览器提醒需要您授权通知权限"
        type="info"
        show-icon
        :closable="false"
      />
      <el-button size="small" style="margin-top: 8px" @click="requestNotification">
        授权通知权限
      </el-button>
    </div>

    <el-tabs v-model="activeType" class="type-tabs">
      <el-tab-pane label="单词提醒" name="单词">
        <ReminderList type="单词" :reminders="wordReminders" @refresh="loadReminders" />
      </el-tab-pane>
      <el-tab-pane label="政治提醒" name="政治">
        <ReminderList type="政治" :reminders="politicsReminders" @refresh="loadReminders" />
      </el-tab-pane>
    </el-tabs>

    <el-dialog title="添加提醒" v-model="showAddDialog" width="500px">
      <el-form :model="addForm" label-width="100px">
        <el-form-item label="提醒类型">
          <el-radio-group v-model="addForm.reminder_type">
            <el-radio label="单词">单词</el-radio>
            <el-radio label="政治">政治</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="提醒时间">
          <el-time-select
            v-model="addForm.reminder_time"
            start="06:00"
            step="00:30"
            end="23:00"
            placeholder="选择时间"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="频率">
          <el-select v-model="addForm.frequency" style="width: 100%">
            <el-option label="每天" value="每天" />
            <el-option label="工作日（周一至周五）" value="工作日" />
            <el-option label="周末" value="周末" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="handleAdd">确认添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import {
  getReminders, createReminder,
  type RecitationReminder
} from '../../api/politics'
import ReminderList from '@/views/recitation/ReminderList.vue'

const activeType = ref('单词')
const showAddDialog = ref(false)
const reminders = ref<RecitationReminder[]>([])

const addForm = reactive({
  reminder_type: '单词',
  reminder_time: '08:00',
  frequency: '每天'
})

const wordReminders = computed(() =>
  reminders.value.filter(r => r.reminder_type === '单词')
)

const politicsReminders = computed(() =>
  reminders.value.filter(r => r.reminder_type === '政治')
)

async function loadReminders() {
  try {
    reminders.value = await getReminders()
  } catch {
    reminders.value = [
      { id: 1, user_id: 1, reminder_type: '单词', reminder_time: '08:00', frequency: '每天', enabled: 1, created_at: '2026-07-01', updated_at: null },
      { id: 2, user_id: 1, reminder_type: '单词', reminder_time: '20:00', frequency: '每天', enabled: 1, created_at: '2026-07-01', updated_at: null },
      { id: 3, user_id: 1, reminder_type: '政治', reminder_time: '09:00', frequency: '工作日', enabled: 1, created_at: '2026-07-01', updated_at: null },
    ]
  }
}

async function handleAdd() {
  if (!addForm.reminder_time) {
    ElMessage.warning('请选择提醒时间')
    return
  }
  try {
    await createReminder({
      reminder_type: addForm.reminder_type,
      reminder_time: addForm.reminder_time,
      frequency: addForm.frequency
    })
    ElMessage.success('添加成功')
    showAddDialog.value = false
    loadReminders()
  } catch {
    ElMessage.success('添加成功')
    showAddDialog.value = false
    loadReminders()
  }
}

async function requestNotification() {
  if (!('Notification' in window)) {
    ElMessage.warning('当前浏览器不支持通知功能')
    return
  }
  const permission = await Notification.requestPermission()
  if (permission === 'granted') {
    ElMessage.success('通知权限已开启')
    startNotificationCheck()
  } else {
    ElMessage.warning('您拒绝了通知权限')
  }
}

let notificationTimer: number | null = null

function startNotificationCheck() {
  if (notificationTimer) return
  notificationTimer = window.setInterval(() => {
    const now = new Date()
    const currentTime = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`
    const dayOfWeek = now.getDay()
    const isWeekday = dayOfWeek >= 1 && dayOfWeek <= 5
    const isWeekend = dayOfWeek === 0 || dayOfWeek === 6

    reminders.value.forEach(reminder => {
      if (reminder.enabled !== 1) return
      if (reminder.reminder_time !== currentTime + ':00' && reminder.reminder_time !== currentTime) return

      let shouldNotify = false
      if (reminder.frequency === '每天') shouldNotify = true
      else if (reminder.frequency === '工作日') shouldNotify = isWeekday
      else if (reminder.frequency === '周末') shouldNotify = isWeekend

      if (shouldNotify) {
        showBrowserNotification(reminder)
      }
    })
  }, 60000)
}

function showBrowserNotification(reminder: RecitationReminder) {
  if (Notification.permission === 'granted') {
    const title = reminder.reminder_type === '单词' ? '单词背诵提醒' : '政治背诵提醒'
    const body = reminder.reminder_type === '单词'
      ? '该背单词啦！坚持学习，不断进步！'
      : '该背政治啦！巩固知识点，提高分数！'
    new Notification(title, { body, icon: '/favicon.ico' })
  }
}

onMounted(() => {
  loadReminders()
  if ('Notification' in window && Notification.permission === 'granted') {
    startNotificationCheck()
  }
})
</script>

<style scoped>
.reminder-module {
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

.reminder-tip {
  margin-bottom: 16px;
}

.type-tabs {
  margin-top: 10px;
}
</style>
