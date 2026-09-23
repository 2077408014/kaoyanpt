<template>
  <div class="dashboard">
    <aside class="sidebar">
      <div class="logo">
        <h1>考研复习平台</h1>
      </div>
      <el-menu :default-active="activeMenu" router>
        <el-menu-item index="/dashboard">
          <el-icon><HomeFilled /></el-icon>
          <span>首页</span>
        </el-menu-item>
        <el-menu-item index="/dashboard/mistakes">
          <el-icon><DocumentDelete /></el-icon>
          <span>错题管理</span>
        </el-menu-item>
        <el-menu-item index="/dashboard/recommend">
          <el-icon><TrendCharts /></el-icon>
          <span>智能推荐</span>
        </el-menu-item>
        <el-menu-item index="/dashboard/resources">
          <el-icon><FolderOpened /></el-icon>
          <span>资料管理</span>
        </el-menu-item>
        <el-menu-item index="/dashboard/words">
          <el-icon><Reading /></el-icon>
          <span>背诵中心</span>
        </el-menu-item>
        <el-menu-item index="/dashboard/ai">
          <el-icon><Service /></el-icon>
          <span>AI问答</span>
        </el-menu-item>
        <el-menu-item index="/dashboard/supervision">
          <el-icon><VideoCamera /></el-icon>
          <span>学习监督</span>
        </el-menu-item>
      </el-menu>
      <div class="logout">
        <el-button @click="handleLogout">退出登录</el-button>
      </div>
    </aside>
    <main class="main-content">
      <header class="header">
        <div class="user-info">
          <el-avatar :size="40">{{ user?.username?.charAt(0) }}</el-avatar>
          <span>{{ user?.username }}</span>
        </div>
        <div class="header-right">
          <el-icon><Bell /></el-icon>
        </div>
      </header>
      <div class="content-wrapper">
        <router-view v-slot="{ Component }">
          <keep-alive :max="5">
            <component :is="Component" />
          </keep-alive>
        </router-view>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '../stores/user'
import { getMe } from '../api/auth'
import { useStudyHeartbeat } from '../composables/useStudyHeartbeat'
import { ElMessage } from 'element-plus'
import {
  HomeFilled,
  DocumentDelete,
  TrendCharts,
  FolderOpened,
  Reading,
  Service,
  Bell,
  VideoCamera
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const store = useUserStore()
const user = ref<any>(null)
const activeMenu = ref(route.path || '/dashboard')

// 启动学习时长心跳跟踪（独立模块）
useStudyHeartbeat()

watch(() => route.path, (newPath) => {
  activeMenu.value = newPath
}, { immediate: true })

onMounted(async () => {
  try {
    const me = await getMe()
    store.setUser(me)
    user.value = me
  } catch (error: any) {
    if (error.response?.status === 401) {
      store.logout()
      router.push('/login')
    }
  }
})

function handleLogout() {
  store.logout()
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>

<style scoped>
.dashboard {
  display: flex;
  height: 100vh;
}

.sidebar {
  width: 240px;
  background: linear-gradient(180deg, #2c3e50 0%, #34495e 100%);
  color: white;
  display: flex;
  flex-direction: column;
}

.logo h1 {
  padding: 20px;
  margin: 0;
  font-size: 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.el-menu {
  border-right: none;
  background: transparent;
  flex: 1;
}

.el-menu-item {
  color: rgba(255, 255, 255, 0.8);
  height: 50px;
  line-height: 50px;
}

.el-menu-item:hover,
.el-menu-item.is-active {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.el-sub-menu .el-menu {
  background: transparent;
}

.el-sub-menu .el-menu-item {
  background: transparent;
  color: rgba(255, 255, 255, 0.8);
}

.el-sub-menu .el-menu-item:hover,
.el-sub-menu .el-menu-item.is-active {
  background: rgba(255, 255, 255, 0.15);
  color: white;
}

.el-menu-item-group {
  background: transparent;
}

.logout {
  padding: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.logout .el-button {
  width: 100%;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
  overflow: hidden;
  min-height: 0;
}

.content-wrapper {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  -webkit-overflow-scrolling: touch;
}

.header {
  height: 60px;
  background: white;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  border-bottom: 1px solid #e0e0e0;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-info span {
  font-size: 14px;
  color: #333;
}

.header-right {
  font-size: 20px;
  color: #666;
  cursor: pointer;
}
</style>