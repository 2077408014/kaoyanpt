<template>
  <div class="page">
    <div class="head">
      <h2 class="page-title">本机构班级总览</h2>
      <span class="hint">人均口径：仅统计本班在读学生，近 7 天数据；错题、监督异常为累计值</span>
    </div>
    <el-skeleton v-if="loading" :rows="4" animated />
    <el-empty v-else-if="classes.length === 0" description="本机构暂无班级" />
    <div v-else class="card-grid">
      <router-link
        v-for="cls in classes"
        :key="cls.id"
        class="class-card-wrap"
        :to="`/institution/classes/${cls.id}`"
      >
        <el-card class="class-card" shadow="hover">
          <div class="class-head">
            <div class="class-name">{{ cls.name }}</div>
            <el-tag
              :type="cls.supervision_abnormal > 0 ? 'danger' : 'success'"
              effect="plain"
              size="small"
            >
              {{ cls.supervision_abnormal > 0 ? `监督异常 ${cls.supervision_abnormal}` : '监督正常' }}
            </el-tag>
          </div>

          <div class="metric-grid">
            <div class="metric">
              <div class="metric-value">{{ cls.student_count }}</div>
              <div class="metric-label">在读学生</div>
            </div>
            <div class="metric">
              <div class="metric-value">{{ fmt(cls.avg_study_time_7d) }}</div>
              <div class="metric-label">人均学习分钟<span class="dim">/近7天</span></div>
            </div>
            <div class="metric">
              <div class="metric-value">{{ fmt(cls.avg_words_7d) }}</div>
              <div class="metric-label">人均单词<span class="dim">/近7天</span></div>
            </div>
            <div class="metric">
              <div class="metric-value">{{ fmt(cls.avg_questions_7d) }}</div>
              <div class="metric-label">人均做题<span class="dim">/近7天</span></div>
            </div>
            <div class="metric">
              <div class="metric-value">{{ fmt(cls.avg_mistakes) }}</div>
              <div class="metric-label">人均错题<span class="dim">/累计</span></div>
            </div>
          </div>

          <div class="card-foot">
            <span class="enter">查看学生详情 →</span>
          </div>
        </el-card>
      </router-link>
    </div>
  </div>
</template>

<script setup>import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { institutionApi } from "../../api/organization";
const loading = ref(false);
const classes = ref([]);
function fmt(v) {
  return Number.isInteger(v) ? String(v) : v.toFixed(1);
}
onMounted(async () => {
  loading.value = true;
  try {
    classes.value = await institutionApi.classes();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "加载失败");
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.page { padding: 24px; }
.head { display: flex; align-items: baseline; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; }
.page-title { font-size: 22px; font-weight: 700; color: #1f2937; margin: 0; }
.hint { color: #9ca3af; font-size: 12px; }
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}
.class-card-wrap { cursor: pointer; display: block; text-decoration: none; color: inherit; }
.class-card-wrap :deep(.el-card) { height: 100%; }
.class-card { border-radius: 12px; }
.class-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 14px; }
.class-name { font-size: 17px; font-weight: 600; color: #1f2937; }
.metric-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; }
.metric {
  background: #f8fafc;
  border-radius: 8px;
  padding: 10px 6px;
  text-align: center;
}
.metric-value { font-size: 18px; font-weight: 700; color: #2563eb; line-height: 1.2; }
.metric-label { margin-top: 4px; font-size: 11px; color: #6b7280; line-height: 1.3; }
.metric-label .dim { color: #9ca3af; }
.card-foot { margin-top: 12px; text-align: right; }
.enter { font-size: 13px; color: #2563eb; }
</style>
