<template>
  <div class="voice-module">
    <div class="module-header">
      <h3>AI语音朗读</h3>
      <p class="subtitle">使用浏览器内置语音合成技术，支持语速和音量调节</p>
    </div>

    <div class="voice-container">
      <div class="text-section">
        <h4>朗读文本</h4>
        <el-input
          v-model="speakText"
          type="textarea"
          :rows="10"
          placeholder="请输入或粘贴需要朗读的文本内容..."
        />
        <div class="text-presets">
          <span class="preset-label">快速选择：</span>
          <el-button size="small" @click="loadPreset('word')">单词示例</el-button>
          <el-button size="small" @click="loadPreset('politics')">政治示例</el-button>
          <el-button size="small" @click="clearText">清空</el-button>
        </div>
      </div>

      <div class="control-section">
        <h4>朗读控制</h4>
        <div class="control-buttons">
          <el-button type="primary" size="large" :disabled="!speakText.trim()" :loading="isSpeaking" @click="handleSpeak">
            <el-icon><VideoPlay /></el-icon>
            {{ isSpeaking ? '朗读中...' : '开始朗读' }}
          </el-button>
          <el-button size="large" :disabled="!isSpeaking" @click="handlePause">
            <el-icon><Refresh /></el-icon>
            {{ isPaused ? '继续' : '暂停' }}
          </el-button>
          <el-button size="large" type="danger" :disabled="!isSpeaking" @click="handleStop">
            <el-icon><CircleClose /></el-icon>
            停止
          </el-button>
        </div>

        <el-divider />

        <div class="settings">
          <div class="setting-item">
            <label>语速调节</label>
            <div class="setting-control">
              <span>慢</span>
              <el-slider
                v-model="rate"
                :min="0.5"
                :max="2"
                :step="0.1"
                style="width: 200px"
                @change="handleRateChange"
              />
              <span>快</span>
              <span class="value">{{ rate.toFixed(1) }}x</span>
            </div>
          </div>

          <div class="setting-item">
            <label>音量调节</label>
            <div class="setting-control">
              <span>轻</span>
              <el-slider
                v-model="volume"
                :min="0"
                :max="1"
                :step="0.1"
                style="width: 200px"
                @change="handleVolumeChange"
              />
              <span>响</span>
              <span class="value">{{ Math.round(volume * 100) }}%</span>
            </div>
          </div>

          <div class="setting-item">
            <label>语调调节</label>
            <div class="setting-control">
              <span>低</span>
              <el-slider
                v-model="pitch"
                :min="0.5"
                :max="2"
                :step="0.1"
                style="width: 200px"
                @change="handlePitchChange"
              />
              <span>高</span>
              <span class="value">{{ pitch.toFixed(1) }}</span>
            </div>
          </div>
        </div>

        <el-divider />

        <div class="voice-info">
          <h4>使用说明</h4>
          <ul>
            <li>支持中英文混合朗读</li>
            <li>可调节语速（0.5x - 2x）</li>
            <li>可调节音量（0% - 100%）</li>
            <li>可调节语调（0.5 - 2）</li>
            <li>基于浏览器原生语音合成，无需联网</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { VideoPlay, Refresh, CircleClose } from '@element-plus/icons-vue'
import { useSpeech } from '@/composables/useSpeech'

const { speak, stop, pause, resume, setRate, setVolume, setPitch, isSpeaking } = useSpeech()

const speakText = ref('')
const rate = ref(1)
const volume = ref(1)
const pitch = ref(1)
const isPaused = ref(false)

function loadPreset(type: string) {
  if (type === 'word') {
    speakText.value = 'abandon\nv. 放弃，抛弃\n例句：He decided to abandon the project.\n\nability\nn. 能力，才能\n例句：She has the ability to learn quickly.'
  } else if (type === 'politics') {
    speakText.value = '唯物辩证法的三大规律：对立统一规律、质量互变规律、否定之否定规律。对立统一规律是唯物辩证法的实质和核心，它揭示了事物内部对立双方的统一与斗争是事物普遍联系的根本内容，是事物发展的根本动力。'
  }
}

function clearText() {
  speakText.value = ''
  stop()
}

function handleSpeak() {
  if (!speakText.value.trim()) {
    ElMessage.warning('请输入要朗读的文本')
    return
  }
  isPaused.value = false
  speak(speakText.value, {
    rate: rate.value,
    volume: volume.value,
    pitch: pitch.value
  })
}

function handlePause() {
  if (isPaused.value) {
    resume()
    isPaused.value = false
  } else {
    pause()
    isPaused.value = true
  }
}

function handleStop() {
  stop()
  isPaused.value = false
}

function handleRateChange(val: number) {
  setRate(val)
}

function handleVolumeChange(val: number) {
  setVolume(val)
}

function handlePitchChange(val: number) {
  setPitch(val)
}

onMounted(() => {
  if (!('speechSynthesis' in window)) {
    ElMessage.warning('当前浏览器不支持语音合成功能')
  }
})
</script>

<style scoped>
.voice-module {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.module-header {
  margin-bottom: 20px;
}

.module-header h3 {
  margin: 0 0 4px;
  font-size: 16px;
  color: #333;
}

.subtitle {
  margin: 0;
  font-size: 14px;
  color: #999;
}

.voice-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.text-section,
.control-section {
  background: #f5f7fa;
  padding: 20px;
  border-radius: 8px;
}

.text-section h4,
.control-section h4,
.voice-info h4 {
  margin: 0 0 12px;
  font-size: 14px;
  color: #333;
}

.text-presets {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.preset-label {
  font-size: 13px;
  color: #666;
}

.control-buttons {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}

.settings {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.setting-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.setting-item label {
  font-size: 13px;
  color: #666;
  font-weight: 500;
}

.setting-control {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: #999;
}

.setting-control .value {
  min-width: 50px;
  text-align: right;
  color: #333;
  font-weight: 500;
}

.voice-info ul {
  margin: 0;
  padding-left: 20px;
  font-size: 13px;
  color: #666;
  line-height: 2;
}

@media (max-width: 900px) {
  .voice-container {
    grid-template-columns: 1fr;
  }
}
</style>
