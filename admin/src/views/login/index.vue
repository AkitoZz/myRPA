<template>
  <div class="login-container">
    <div class="login-bg">
      <div class="login-card">
        <div class="login-header">
          <el-icon :size="40" color="#409EFF">
            <ChatDotRound />
          </el-icon>
          <h1 class="login-title">微信RPA管理后台</h1>
          <p class="login-subtitle">WeChat RPA Management System</p>
        </div>

        <el-form
          ref="loginFormRef"
          :model="loginForm"
          :rules="loginRules"
          size="large"
          @keyup.enter="handleLogin"
        >
          <el-form-item prop="phone">
            <el-input
              v-model="loginForm.phone"
              placeholder="请输入手机号"
              :prefix-icon="Iphone"
              clearable
            />
          </el-form-item>

          <el-form-item prop="password">
            <el-input
              v-model="loginForm.password"
              type="password"
              placeholder="请输入密码"
              :prefix-icon="Lock"
              show-password
              clearable
            />
          </el-form-item>

          <div class="login-options">
            <el-checkbox v-model="rememberMe">记住我</el-checkbox>
          </div>

          <el-form-item>
            <el-button
              type="primary"
              :loading="loading"
              class="login-btn"
              @click="handleLogin"
            >
              {{ loading ? '登录中...' : '登 录' }}
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </div>

    <div class="login-footer">
      <span>微信RPA管理系统 &copy; {{ new Date().getFullYear() }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'
import { ElMessage } from 'element-plus'
import { ChatDotRound, Iphone, Lock } from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()

const loginFormRef = ref(null)
const loading = ref(false)
const rememberMe = ref(false)

const loginForm = reactive({
  phone: '',
  password: ''
})

const loginRules = {
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不少于6位', trigger: 'blur' }
  ]
}

onMounted(() => {
  const savedPhone = localStorage.getItem('remembered_phone')
  if (savedPhone) {
    loginForm.phone = savedPhone
    rememberMe.value = true
  }
})

async function handleLogin() {
  if (!loginFormRef.value) return

  await loginFormRef.value.validate(async (valid) => {
    if (!valid) return

    loading.value = true
    try {
      await userStore.login({
        phone: loginForm.phone,
        password: loginForm.password
      })

      if (rememberMe.value) {
        localStorage.setItem('remembered_phone', loginForm.phone)
      } else {
        localStorage.removeItem('remembered_phone')
      }

      ElMessage.success('登录成功')
      router.push('/dashboard')
    } catch (error) {
      ElMessage.error(error?.response?.data?.message || '登录失败，请检查账号密码')
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.login-container {
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.login-bg {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  position: relative;
  overflow: hidden;
}

.login-bg::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 60%);
  animation: float 6s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(30px, -30px); }
}

.login-card {
  width: 420px;
  background: #fff;
  border-radius: 16px;
  padding: 48px 40px 36px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
  position: relative;
  z-index: 1;
}

.login-header {
  text-align: center;
  margin-bottom: 36px;
}

.login-title {
  font-size: 24px;
  font-weight: 700;
  color: #303133;
  margin: 12px 0 6px;
  letter-spacing: 2px;
}

.login-subtitle {
  font-size: 13px;
  color: #909399;
  letter-spacing: 0.5px;
}

.login-options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.login-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
  letter-spacing: 4px;
  border-radius: 8px;
}

.login-footer {
  text-align: center;
  padding: 16px;
  color: #909399;
  font-size: 12px;
  background: #f5f7fa;
}

@media (max-width: 480px) {
  .login-card {
    width: 90%;
    padding: 36px 24px 28px;
  }
}
</style>
