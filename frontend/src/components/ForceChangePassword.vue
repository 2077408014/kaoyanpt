<template>
  <el-dialog
    v-model="visible"
    title="首次登录请修改密码"
    width="420px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="false"
    align-center
  >
    <el-alert
      title="这是管理员为你创建的初始密码，为保证账号安全，请先修改密码后再使用系统。"
      type="warning"
      :closable="false"
      show-icon
      style="margin-bottom: 18px"
    />
    <el-form label-width="90px" @submit.prevent>
      <el-form-item label="原密码">
        <el-input v-model="oldPassword" type="password" show-password placeholder="请输入原密码" />
      </el-form-item>
      <el-form-item label="新密码">
        <el-input v-model="newPassword" type="password" show-password placeholder="至少 6 位" />
      </el-form-item>
      <el-form-item label="确认新密码">
        <el-input v-model="confirmPassword" type="password" show-password placeholder="再次输入新密码" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="handleLogout">退出登录</el-button>
      <el-button type="primary" :loading="saving" @click="handleSubmit">确认修改</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { changePassword } from '../api/auth'
import { useUserStore } from '../stores/user'

const store = useUserStore()
const route = useRoute()
const router = useRouter()

const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const saving = ref(false)

const visible = computed({
  get: () => store.mustChangePassword && !!store.token && route.path !== '/login',
  set: () => {},
})

watch(visible, (v) => {
  if (!v) {
    oldPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
  }
})

async function handleSubmit() {
  if (!oldPassword.value) {
    ElMessage.warning('请输入原密码')
    return
  }
  if (newPassword.value.length < 6) {
    ElMessage.warning('新密码至少 6 位')
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  saving.value = true
  try {
    await changePassword({
      old_password: oldPassword.value,
      new_password: newPassword.value,
    })
    store.clearMustChangePassword()
    ElMessage.success('密码修改成功')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '修改失败')
  } finally {
    saving.value = false
  }
}

function handleLogout() {
  store.logout()
  router.push('/login')
}
</script>
