<template>
  <div class="role-layout">
    <aside class="sidebar">
      <div class="logo">
        <h1>{{ title }}</h1>
      </div>
      <el-menu :default-active="activeMenu" router>
        <el-menu-item v-for="item in items" :key="item.index" :index="item.index">
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </el-menu-item>
      </el-menu>
      <div class="logout">
        <el-button @click="handleLogout">退出登录</el-button>
      </div>
    </aside>
    <main class="main-content">
      <header class="header">
        <div class="user-info">
          <el-avatar :size="40">{{ username?.charAt(0) }}</el-avatar>
          <span>{{ username }}</span>
        </div>
      </header>
      <div class="content-wrapper">
        <router-view />
      </div>
    </main>
  </div>
</template>

<script setup>import { ref, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { useUserStore } from "../stores/user";
import { getMe } from "../api/auth";
defineProps({
  title: { type: String, required: true },
  items: { type: Array, required: true }
});
const route = useRoute();
const router = useRouter();
const store = useUserStore();
const username = ref(store.user?.username || "");
const activeMenu = ref(route.path);
watch(() => route.path, (p) => {
  activeMenu.value = p;
}, { immediate: true });
onMounted(async () => {
  try {
    const me = await getMe();
    store.setUser(me);
    username.value = me.username;
  } catch {
    store.logout();
    router.push("/login");
  }
});
function handleLogout() {
  store.logout();
  ElMessage.success("已退出登录");
  router.push("/login");
}
</script>

<style scoped>
.role-layout {
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
}
.header {
  height: 60px;
  background: white;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}
.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
}
</style>
