<template>
  <div class="forgot-password-container">
    <div class="forgot-password-card">
      <h2>考研复习平台</h2>
      <p class="subtitle">找回密码</p>
      
      <div v-if="step === 1">
        <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
          <el-form-item label="邮箱" prop="email">
            <el-input v-model="form.email" placeholder="请输入注册时的邮箱" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSendCode" :loading="sending" style="width: 100%">
              发送验证码
            </el-button>
          </el-form-item>
        </el-form>
      </div>

      <div v-else>
        <el-form ref="formRef" :model="form" :rules="resetRules" label-width="80px">
          <el-form-item label="邮箱" prop="email">
            <el-input v-model="form.email" placeholder="请输入注册时的邮箱" disabled />
          </el-form-item>
          <el-form-item label="验证码" prop="code">
            <div class="code-input-wrapper">
              <el-input v-model="form.code" placeholder="请输入验证码" />
              <el-button type="primary" @click="handleSendCode" :loading="sending" :disabled="countdown > 0">
                {{ countdown > 0 ? `${countdown}秒` : '重新发送' }}
              </el-button>
            </div>
          </el-form-item>
          <el-form-item label="新密码" prop="new_password">
            <el-input v-model="form.new_password" type="password" placeholder="请输入新密码（至少6位）" />
          </el-form-item>
          <el-form-item label="确认密码" prop="confirm_password">
            <el-input v-model="form.confirm_password" type="password" placeholder="请再次输入新密码" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleResetPassword" :loading="resetting" style="width: 100%">
              重置密码
            </el-button>
          </el-form-item>
        </el-form>
      </div>

      <p class="login-link">
        <router-link to="/login">返回登录</router-link>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { forgotPassword, resetPassword } from '../api/auth'

const router = useRouter()
const formRef = ref()
const sending = ref(false)
const resetting = ref(false)
const step = ref(1)
const countdown = ref(0)
let countdownTimer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  countdown.value = 0
  step.value = 1
})

const form = reactive({
  email: '',
  code: '',
  new_password: '',
  confirm_password: ''
})

const rules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ]
}

const resetRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  code: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { min: 6, max: 6, message: '验证码必须为6位数字', trigger: 'blur' }
  ],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6位', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    {
      validator: (_rule: any, value: string, callback: any) => {
        if (value !== form.new_password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

async function handleSendCode() {
  if (!form.email) {
    ElMessage.error('请输入邮箱')
    return
  }
  
  sending.value = true
  try {
    await forgotPassword({ email: form.email })
    ElMessage.success('验证码已发送到您的邮箱，请查收')
    
    if (step.value === 1) {
      step.value = 2
    }
    
    if (countdownTimer) {
      clearInterval(countdownTimer)
    }
    startCountdown()
  } catch (error: any) {
    countdown.value = 0
    ElMessage.error(error.response?.data?.detail || '发送验证码失败')
  } finally {
    sending.value = false
  }
}

function startCountdown() {
  countdown.value = 60
  countdownTimer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      clearInterval(countdownTimer!)
      countdownTimer = null
      countdown.value = 0
    }
  }, 1000)
}

async function handleResetPassword() {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid: boolean) => {
    if (!valid) return
    
    resetting.value = true
    try {
      await resetPassword({
        email: form.email,
        code: form.code,
        new_password: form.new_password
      })
      
      ElMessage.success('密码重置成功，请使用新密码登录')
      await router.push('/login')
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || '密码重置失败')
    } finally {
      resetting.value = false
    }
  })
}
</script>

<style scoped>
.forgot-password-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.forgot-password-card {
  width: 400px;
  padding: 40px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.forgot-password-card h2 {
  text-align: center;
  margin-bottom: 8px;
  color: #333;
}

.forgot-password-card .subtitle {
  text-align: center;
  color: #999;
  margin-bottom: 30px;
}

.code-input-wrapper {
  display: flex;
  gap: 10px;
}

.code-input-wrapper .el-input {
  flex: 1;
}

.login-link {
  text-align: center;
  margin-top: 20px;
  color: #666;
}

.login-link a {
  color: #667eea;
  text-decoration: none;
}

.login-link a:hover {
  text-decoration: underline;
}
</style>