<template>
  <div class="class-detail-page">
    <div class="page-card">
      <el-button link @click="$router.push('/dashboard/my-classes')">&lt; 返回我的班级</el-button>
      <h2 class="page-title">{{ className }}</h2>

      <el-tabs v-model="activeTab" class="tabs">
        <!-- 公告 -->
        <el-tab-pane label="班级公告" name="announcements">
          <el-skeleton v-if="annLoading" :rows="4" animated />
          <el-empty v-else-if="announcements.length === 0" description="暂无公告" />
          <el-collapse v-else v-model="activeAnn">
            <el-collapse-item
              v-for="ann in announcements"
              :key="ann.id"
              :name="ann.id"
            >
              <template #title>
                <div class="ann-title">
                  <span class="ann-name">{{ ann.title }}</span>
                  <span class="ann-meta">
                    {{ ann.author_name }} · {{ formatTime(ann.created_at) }}
                  </span>
                </div>
              </template>
              <div class="ann-content">{{ ann.content }}</div>
            </el-collapse-item>
          </el-collapse>
        </el-tab-pane>

        <!-- 作业 -->
        <el-tab-pane label="作业" name="assignments">
          <el-skeleton v-if="asmLoading" :rows="4" animated />
          <el-empty v-else-if="assignments.length === 0" description="暂无作业" />
          <el-table v-else :data="assignments" stripe border>
            <el-table-column prop="title" label="作业标题" min-width="160" />
            <el-table-column label="截止时间" width="170">
              <template #default="{ row }">
                <span v-if="!row.due_at" class="muted">无截止</span>
                <el-tag v-else :type="isOverdue(row.due_at) ? 'danger' : 'info'" effect="plain" size="small">
                  {{ formatTime(row.due_at) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="我的状态" width="140">
              <template #default="{ row }">
                <el-tag v-if="!row.my_submission" type="info" effect="plain">未提交</el-tag>
                <el-tag v-else-if="row.my_submission.score !== null && row.my_submission.score !== undefined" type="success" effect="dark">
                  {{ row.my_submission.score }} 分
                </el-tag>
                <el-tag v-else type="warning" effect="plain">待批改</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button link type="primary" @click="openAssignment(row)">
                  {{ row.my_submission ? '查看/重做' : '去提交' }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 作业提交弹窗 -->
    <el-dialog
      v-model="asmVisible"
      :title="current?.title || '作业'"
      width="560px"
      @paste="handleSubmitPaste"
    >
      <div v-if="current" class="asm-body">
        <div class="asm-meta">
          <el-tag v-if="!current.due_at" type="info" effect="plain" size="small">无截止时间</el-tag>
          <el-tag v-else :type="overdueCurrent ? 'danger' : 'info'" effect="plain" size="small">
            截止：{{ formatTime(current.due_at) }}
          </el-tag>
          <span v-if="current.my_submission?.submitted_at" class="muted">
            已于 {{ formatTime(current.my_submission.submitted_at) }} 提交
          </span>
        </div>
        <div class="asm-content">{{ current.content }}</div>
        <div v-if="current.images && current.images.length" class="asm-images">
          <el-image
            v-for="p in current.images"
            :key="p"
            :src="'/uploads/' + p"
            :preview-src-list="current.images.map(x => '/uploads/' + x)"
            fit="cover"
            class="asm-img"
          />
        </div>

        <div v-if="current.my_submission" class="graded-box">
          <template v-if="current.my_submission.score !== null && current.my_submission.score !== undefined">
            <div class="score-line">
              得分：<el-tag type="success" effect="dark">{{ current.my_submission.score }}</el-tag>
            </div>
            <div v-if="current.my_submission.feedback" class="feedback">
              教师评语：{{ current.my_submission.feedback }}
            </div>
          </template>
          <div v-else class="muted">教师尚未批改</div>
        </div>

        <el-alert
          v-if="current.my_submission"
          title="重新提交后，原有的分数和评语将被清空。"
          type="warning"
          :closable="false"
          show-icon
          style="margin: 12px 0"
        />

        <el-input
          v-model="submitContent"
          type="textarea"
          :rows="6"
          :disabled="overdueCurrent"
          placeholder="请在此输入作业内容，可直接 Ctrl+V 粘贴图片"
          style="margin-top: 12px"
        />

        <!-- 作业图片 -->
        <div class="sub-img-row">
          <div v-for="(p, i) in submitImages" :key="p" class="img-item">
            <el-image
              :src="'/uploads/' + p"
              :preview-src-list="submitPreviewList"
              :initial-index="i"
              fit="cover"
              class="img-thumb"
            />
            <el-icon
              v-if="!overdueCurrent"
              class="img-del"
              @click="submitImages.splice(i, 1)"
            ><Close /></el-icon>
          </div>
          <el-upload
            v-if="!overdueCurrent && submitImages.length < 9"
            :show-file-list="false"
            :http-request="handleSubImageUpload"
            accept="image/jpeg,image/png,image/webp"
            :disabled="subImgUploading"
          >
            <div class="img-add" v-loading="subImgUploading">
              <el-icon><Plus /></el-icon>
            </div>
          </el-upload>
        </div>
      </div>
      <template #footer>
        <el-button @click="asmVisible = false">关闭</el-button>
        <el-button
          type="primary"
          :loading="submitting"
          :disabled="overdueCurrent"
          @click="handleSubmit"
        >
          {{ overdueCurrent ? '已过截止时间' : (current?.my_submission ? '重新提交' : '提交作业') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { Close, Plus } from '@element-plus/icons-vue';
import { ref, computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  studentClassApi
} from "../../api/organization";
const route = useRoute();
const classId = Number(route.params.classId);
const className = ref("班级详情");
const activeTab = ref("announcements");
const activeAnn = ref([]);
const announcements = ref([]);
const annLoading = ref(false);
const assignments = ref([]);
const asmLoading = ref(false);
const asmVisible = ref(false);
const current = ref(null);
const submitContent = ref("");
const submitImages = ref([]);
const subImgUploading = ref(false);
const submitting = ref(false);
const overdueCurrent = computed(
  () => !!current.value?.due_at && isOverdue(current.value.due_at)
);
const submitPreviewList = computed(() => submitImages.value.map((p) => "/uploads/" + p));
async function loadAll() {
  annLoading.value = true;
  asmLoading.value = true;
  try {
    const [myClasses, anns, asms] = await Promise.all([
      studentClassApi.my(),
      studentClassApi.announcements(classId),
      studentClassApi.assignments(classId)
    ]);
    const mine = myClasses.find((c) => c.id === classId);
    if (mine) className.value = mine.name;
    announcements.value = anns;
    assignments.value = asms;
    if (anns.length) activeAnn.value = [anns[0].id];
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "加载失败");
  } finally {
    annLoading.value = false;
    asmLoading.value = false;
  }
}
function openAssignment(row) {
  current.value = row;
  submitContent.value = row.my_submission?.content || "";
  submitImages.value = [...row.my_submission?.images || []];
  asmVisible.value = true;
}
async function handleSubImageUpload(options) {
  if (options.file.size > 10 * 1024 * 1024) {
    ElMessage.warning("图片不能超过 10MB");
    return;
  }
  subImgUploading.value = true;
  try {
    const { image_path } = await studentClassApi.uploadSubmissionImage(options.file);
    submitImages.value.push(image_path);
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "图片上传失败");
  } finally {
    subImgUploading.value = false;
  }
}
function handleSubmitPaste(e) {
  if (overdueCurrent.value) return;
  const items = e.clipboardData?.items;
  if (!items) return;
  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    if (item.type.startsWith("image/")) {
      e.preventDefault();
      if (submitImages.value.length >= 9) {
        ElMessage.warning("最多 9 张图片");
        return;
      }
      const file = item.getAsFile();
      if (file) {
        handleSubImageUpload({ file });
      }
      return;
    }
  }
}
async function handleSubmit() {
  if (!current.value) return;
  if (!submitContent.value.trim() && submitImages.value.length === 0) {
    ElMessage.warning("作业内容和图片至少填写一项");
    return;
  }
  if (current.value.my_submission) {
    try {
      await ElMessageBox.confirm("重新提交会清空原有评分，确定提交吗？", "确认重新提交", {
        type: "warning"
      });
    } catch {
      return;
    }
  }
  submitting.value = true;
  try {
    const sub = await studentClassApi.submit(current.value.id, submitContent.value, submitImages.value);
    ElMessage.success("提交成功");
    const idx = assignments.value.findIndex((a) => a.id === current.value.id);
    if (idx >= 0) assignments.value[idx] = { ...assignments.value[idx], my_submission: sub };
    current.value = assignments.value[idx];
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "提交失败");
  } finally {
    submitting.value = false;
  }
}
function isOverdue(due) {
  return new Date(due).getTime() <= Date.now();
}
function formatTime(t) {
  if (!t) return "";
  return t.replace("T", " ").slice(0, 16);
}
onMounted(loadAll);
</script>

<style scoped>
.class-detail-page { padding: 24px; }
.page-title { font-size: 22px; font-weight: 700; color: #1f2937; margin: 10px 0 4px; }
.tabs { margin-top: 8px; }
.ann-title { display: flex; align-items: baseline; gap: 14px; width: 100%; }
.ann-name { font-weight: 600; color: #1f2937; }
.ann-meta { color: #9ca3af; font-size: 12px; }
.ann-content { white-space: pre-wrap; color: #374151; line-height: 1.8; padding: 4px 8px 12px; }
.muted { color: #9ca3af; font-size: 13px; }
.asm-meta { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.asm-content {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 14px;
  white-space: pre-wrap;
  line-height: 1.7;
  color: #1f2937;
}
.asm-images { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.asm-img { width: 120px; height: 120px; border-radius: 6px; border: 1px solid #e5e7eb; }
.graded-box {
  margin-top: 14px;
  padding: 12px 14px;
  border: 1px solid #d1fae5;
  background: #ecfdf5;
  border-radius: 8px;
}
.score-line { font-weight: 600; margin-bottom: 6px; }
.feedback { color: #374151; font-size: 14px; margin-top: 4px; }
.sub-img-row { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.img-item { position: relative; }
.img-thumb { width: 96px; height: 96px; border-radius: 6px; border: 1px solid #e5e7eb; display: block; }
.img-del {
  position: absolute; top: -8px; right: -8px;
  width: 20px; height: 20px; border-radius: 50%;
  background: #ef4444; color: #fff; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px;
}
.img-add {
  width: 96px; height: 96px; border-radius: 6px;
  border: 1px dashed #d1d5db; color: #9ca3af;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; font-size: 22px;
}
.img-add:hover { border-color: #409eff; color: #409eff; }
</style>
