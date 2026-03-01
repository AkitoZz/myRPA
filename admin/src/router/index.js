import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/components/layout/MainLayout.vue'),
    redirect: '/dashboard',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: { title: '仪表盘', icon: 'Odometer' }
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/user/index.vue'),
        meta: { title: '用户管理', icon: 'User' }
      },
      {
        path: 'devices',
        name: 'Devices',
        component: () => import('@/views/device/index.vue'),
        meta: { title: '设备管理', icon: 'Monitor' }
      },
      {
        path: 'licenses',
        name: 'Licenses',
        component: () => import('@/views/license/index.vue'),
        meta: { title: '授权管理', icon: 'Key' }
      },
      {
        path: 'tasks',
        name: 'Tasks',
        component: () => import('@/views/task/index.vue'),
        meta: { title: '任务管理', icon: 'List' }
      },
      {
        path: 'wechat-accounts',
        name: 'WechatAccounts',
        component: () => import('@/views/wechat-account/index.vue'),
        meta: { title: '微信账号', icon: 'ChatDotRound' }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guard
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')

  if (to.meta.requiresAuth === false) {
    // Login page: if already logged in, go to dashboard
    if (token && to.path === '/login') {
      next('/dashboard')
    } else {
      next()
    }
  } else {
    // Protected route: check token
    if (!token) {
      next('/login')
    } else {
      next()
    }
  }
})

export default router
