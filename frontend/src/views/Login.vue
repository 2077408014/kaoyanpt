<template>
  <div class="login-container">
    <div class="login-card">
      <h2>考研复习平台</h2>
      <p class="subtitle">助你考研之路更顺畅</p>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleLogin" :loading="loading" style="width: 100%">
            登录
          </el-button>
        </el-form-item>
      </el-form>
      <p class="forgot-link">
        <router-link to="/forgot-password">忘记密码？</router-link>
      </p>
      <p class="register-link">
        还没有账号？<router-link to="/register">立即注册</router-link>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { login } from '../api/auth'

const router = useRouter()
const store = useUserStore()
const formRef = ref()
const loading = ref(false)

const form = reactive({
  email: '',
  password: ''
})

const rules = {
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

async function handleLogin() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid: boolean) => {
    if (!valid) return
    loading.value = true
    try {
      const response = await login(form)
      store.setToken(response.access_token)
      localStorage.setItem('refresh_token', response.refresh_token)
      await router.push('/dashboard')
      ElMessage.success('登录成功')
    } catch (error: any) {
      if (error.response?.status === 401) {
        ElMessage.error('账号或密码错误')
      } else {
        ElMessage.error(error.response?.data?.detail || '登录失败')
      }
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 400px;
  padding: 40px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.login-card h2 {
  text-align: center;
  margin-bottom: 8px;
  color: #333;
}

.login-card .subtitle {
  text-align: center;
  color: #999;
  margin-bottom: 30px;
}

.forgot-link {
  text-align: right;
  margin-top: 10px;
}

.forgot-link a {
  color: #667eea;
  text-decoration: none;
  font-size: 14px;
}

.forgot-link a:hover {
  text-decoration: underline;
}

.register-link {
  text-align: center;
  margin-top: 20px;
  color: #666;
}

.register-link a {
  color: #667eea;
  text-decoration: none;
}

.register-link a:hover {
  text-decoration: underline;
}
</style>