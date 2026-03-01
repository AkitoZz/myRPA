import { defineStore } from 'pinia'
import { ref } from 'vue'
import { login as loginApi } from '@/api/auth'
import { getUsers } from '@/api/user'
import router from '@/router'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref(null)

  async function login(credentials) {
    try {
      const res = await loginApi(credentials)
      const data = res.data || res
      token.value = data.token
      localStorage.setItem('token', data.token)
      if (data.user) {
        userInfo.value = data.user
      }
      return data
    } catch (error) {
      throw error
    }
  }

  function logout() {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('token')
    router.push('/login')
  }

  async function getUserInfo() {
    try {
      const res = await getUsers({ page: 1, pageSize: 1 })
      const data = res.data || res
      if (data.user) {
        userInfo.value = data.user
      }
      return data
    } catch (error) {
      console.error('获取用户信息失败', error)
    }
  }

  function setToken(newToken) {
    token.value = newToken
    localStorage.setItem('token', newToken)
  }

  return {
    token,
    userInfo,
    login,
    logout,
    getUserInfo,
    setToken
  }
})
