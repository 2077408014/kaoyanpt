<template>
  <div class="recitation">
    <el-tabs v-model="activeTab" class="main-tabs">
      <el-tab-pane label="单词背诵" name="words">
        <WordModule />
      </el-tab-pane>
      <el-tab-pane label="政治背诵" name="politics">
        <PoliticsModule />
      </el-tab-pane>
      <el-tab-pane label="背诵提醒" name="reminders">
        <ReminderModule />
      </el-tab-pane>
      <el-tab-pane label="AI语音朗读" name="voice">
        <VoiceModule />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import WordModule from './recitation/WordModule.vue'
import PoliticsModule from './recitation/PoliticsModule.vue'
import ReminderModule from './recitation/ReminderModule.vue'
import VoiceModule from './recitation/VoiceModule.vue'

const activeTab = ref('words')
</script>

<style scoped>
.recitation {
  padding: 20px;
}

.main-tabs :deep(.el-tabs__header) {
  margin-bottom: 20px;
}

.main-tabs :deep(.el-tabs__nav-wrap::after) {
  background-color: #e4e7ed;
}
</style>
