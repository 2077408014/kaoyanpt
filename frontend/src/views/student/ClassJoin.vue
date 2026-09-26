<template>
  <div class="my-classes-page">
    <div class="page-card">
      <div class="page-header">
        <h2 class="page-title">我的班级</h2>
        <p class="page-subtitle">输入老师提供的入班码即可加入班级</p>
      </div>

      <el-card class="join-card" shadow="never">
        <div class="join-row">
          <el-input
            v-model="code"
            placeholder="请输入 6 位入班码"
            maxlength="8"
            clearable
            class="join-input"
            @keyup.enter="handleJoin"
          />
          <el-button type="primary" :loading="joining" @click="handleJoin">加入班级</el-button>
        </div>
      </el-card>

      <div class="class-list">
        <el-empty v-if="!loading && classes.length === 0" description="你还没有加入任何班级" />
        <el-card
          v-for="cls in classes"
          :key="cls.id"
          class="class-card"
          shadow="hover"
        >
          <div class="class-card-body">
            <div>
              <div class="class-name">
                {{ cls.name }}
                <el-tag
                  v-if="cls.status === 'suspended'"
                  type="danger"
                  effect="dark"
                  size="small"
                  style="margin-left: 8px"
                >已暂停</el-tag>
              </div>
              <div class="class-meta">
                <el-tag size="small" type="info" effect="plain">{{ cls.institution_name }}</el-tag>
                <el-tag size="small" effect="plain">入班码 {{ cls.join_code }}</el-tag>
              </div>
              <div class="teacher-names">
                任课教师：{{ cls.teachers.length ? cls.teachers.map(t => t.username).join('、') : '暂未分配' }}
              </div>
            </div>
            <el-button
              type="primary"
              :disabled="cls.status === 'suspended'"
              @click="$router.push(`/dashboard/classes/${cls.id}`)"
            >
              {{ cls.status === 'suspended' ? '已暂停访问' : '进入班级' }}
            </el-button>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { studentClassApi, type MyClass } from '../../api/organization'

const code = ref('')
const joining = ref(false)
const loading = ref(false)
const classes = ref<MyClass[]>([])

async function loadClasses() {
  loading.value = true
  try {
    classes.value = await studentClassApi.my()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '加载班级失败')
  } finally {
    loading.value = false
  }
}

async function handleJoin() {
  if (!code.value.trim()) {
    ElMessage.warning('请输入入班码')
    return
  }
  joining.value = true
  try {
    const cls = await studentClassApi.join(code.value)
    ElMessage.success(`已加入「${cls.name}」`)
    code.value = ''
    await loadClasses()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '加入失败')
  } finally {
    joining.value = false
  }
}

onMounted(loadClasses)
</script>

<style scoped>
.my-classes-page {
  padding: 24px;
}
.page-header {
  margin-bottom: 20px;
}
.page-title {
  font-size: 24px;
  font-weight: 700;
  color: #1f2937;
  margin: 0 0 6px;
}
.page-subtitle {
  color: #6b7280;
  font-size: 14px;
  margin: 0;
}
.join-card {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  margin-bottom: 20px;
}
.join-row {
  display: flex;
  gap: 12px;
}
.join-input {
  max-width: 320px;
}
.class-card {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  margin-bottom: 12px;
}
.class-card-body {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.class-name {
  font-size: 17px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 8px;
}
.class-meta {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}
.teacher-names {
  font-size: 13px;
  color: #6b7280;
}
</style>
