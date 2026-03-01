<template>
  <div class="dashboard" v-loading="loading">
    <!-- Stats Cards -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="flex-between">
          <div>
            <div class="stat-value">{{ stats.totalUsers || 0 }}</div>
            <div class="stat-label">总用户数</div>
          </div>
          <div class="stat-icon" style="background: linear-gradient(135deg, #409EFF, #79bbff)">
            <el-icon><User /></el-icon>
          </div>
        </div>
      </div>

      <div class="stat-card">
        <div class="flex-between">
          <div>
            <div class="stat-value">{{ stats.onlineDevices || 0 }}</div>
            <div class="stat-label">在线设备</div>
          </div>
          <div class="stat-icon" style="background: linear-gradient(135deg, #67c23a, #95d475)">
            <el-icon><Monitor /></el-icon>
          </div>
        </div>
      </div>

      <div class="stat-card">
        <div class="flex-between">
          <div>
            <div class="stat-value">{{ stats.todayTasks || 0 }}</div>
            <div class="stat-label">今日任务</div>
          </div>
          <div class="stat-icon" style="background: linear-gradient(135deg, #e6a23c, #eebe77)">
            <el-icon><List /></el-icon>
          </div>
        </div>
      </div>

      <div class="stat-card">
        <div class="flex-between">
          <div>
            <div class="stat-value">{{ stats.successRate || 0 }}%</div>
            <div class="stat-label">成功率</div>
          </div>
          <div class="stat-icon" style="background: linear-gradient(135deg, #f56c6c, #fab6b6)">
            <el-icon><TrendCharts /></el-icon>
          </div>
        </div>
      </div>
    </div>

    <!-- Charts -->
    <div class="charts-row">
      <div class="chart-card">
        <div class="chart-title">任务趋势（近7天）</div>
        <div ref="trendChartRef" class="chart-container"></div>
      </div>

      <div class="chart-card">
        <div class="chart-title">任务类型分布</div>
        <div ref="pieChartRef" class="chart-container"></div>
      </div>
    </div>

    <!-- Tables Row -->
    <div class="tables-row">
      <div class="table-section">
        <div class="section-header">
          <span class="section-title">最近任务</span>
          <el-button text type="primary" @click="$router.push('/tasks')">查看全部</el-button>
        </div>
        <el-table :data="recentTasks" stripe size="small" class="recent-table">
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="name" label="任务名称" min-width="120" show-overflow-tooltip />
          <el-table-column prop="type" label="类型" width="100">
            <template #default="{ row }">
              <el-tag size="small" :type="taskTypeTag(row.type)">{{ taskTypeLabel(row.type) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="90">
            <template #default="{ row }">
              <el-tag size="small" :type="taskStatusTag(row.status)">{{ taskStatusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="createdAt" label="创建时间" width="160">
            <template #default="{ row }">
              {{ formatTime(row.createdAt) }}
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="table-section">
        <div class="section-header">
          <span class="section-title">在线设备</span>
          <el-button text type="primary" @click="$router.push('/devices')">查看全部</el-button>
        </div>
        <el-table :data="recentDevices" stripe size="small" class="recent-table">
          <el-table-column prop="deviceName" label="设备名称" min-width="120" show-overflow-tooltip />
          <el-table-column prop="os" label="系统" width="90" />
          <el-table-column prop="status" label="状态" width="80">
            <template #default="{ row }">
              <span class="status-dot status-dot--online"></span>
              <span style="color: #67c23a">在线</span>
            </template>
          </el-table-column>
          <el-table-column prop="lastHeartbeat" label="最后心跳" width="160">
            <template #default="{ row }">
              {{ formatTime(row.lastHeartbeat) }}
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getDashboardStats } from '@/api/stats'
import { getTasks } from '@/api/task'
import { getDevices } from '@/api/device'
import { User, Monitor, List, TrendCharts } from '@element-plus/icons-vue'

const loading = ref(false)
const trendChartRef = ref(null)
const pieChartRef = ref(null)
let trendChart = null
let pieChart = null

const stats = ref({
  totalUsers: 0,
  onlineDevices: 0,
  todayTasks: 0,
  successRate: 0
})

const recentTasks = ref([])
const recentDevices = ref([])

// Task type helpers
const taskTypeMap = {
  add_friend: '加好友',
  group_send: '群发消息',
  moments: '朋友圈',
  auto_reply: '自动回复',
  collect: '数据采集'
}
function taskTypeLabel(type) {
  return taskTypeMap[type] || type || '未知'
}
function taskTypeTag(type) {
  const map = { add_friend: '', group_send: 'success', moments: 'warning', auto_reply: 'info', collect: 'danger' }
  return map[type] || 'info'
}

// Task status helpers
const taskStatusMap = {
  pending: '待执行',
  running: '运行中',
  paused: '已暂停',
  completed: '已完成',
  failed: '失败',
  stopped: '已停止'
}
function taskStatusLabel(status) {
  return taskStatusMap[status] || status || '未知'
}
function taskStatusTag(status) {
  const map = { pending: 'info', running: '', paused: 'warning', completed: 'success', failed: 'danger', stopped: 'info' }
  return map[status] || 'info'
}

function formatTime(time) {
  if (!time) return '-'
  const d = new Date(time)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

// Initialize charts
function initTrendChart(data) {
  if (!trendChartRef.value) return
  trendChart = echarts.init(trendChartRef.value)

  const dates = data?.dates || getLast7Days()
  const total = data?.total || [12, 18, 15, 25, 20, 30, 22]
  const success = data?.success || [10, 16, 13, 22, 18, 28, 20]

  const option = {
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#fff',
      borderColor: '#eee',
      borderWidth: 1,
      textStyle: { color: '#303133' }
    },
    legend: {
      data: ['总任务', '成功任务'],
      bottom: 0
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '14%',
      top: '8%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: dates,
      axisLine: { lineStyle: { color: '#dcdfe6' } },
      axisLabel: { color: '#606266' }
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#f0f0f0' } },
      axisLabel: { color: '#606266' }
    },
    series: [
      {
        name: '总任务',
        type: 'line',
        smooth: true,
        data: total,
        lineStyle: { width: 2.5 },
        itemStyle: { color: '#409EFF' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(64,158,255,0.25)' },
            { offset: 1, color: 'rgba(64,158,255,0.02)' }
          ])
        }
      },
      {
        name: '成功任务',
        type: 'line',
        smooth: true,
        data: success,
        lineStyle: { width: 2.5 },
        itemStyle: { color: '#67c23a' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(103,194,58,0.25)' },
            { offset: 1, color: 'rgba(103,194,58,0.02)' }
          ])
        }
      }
    ]
  }

  trendChart.setOption(option)
}

function initPieChart(data) {
  if (!pieChartRef.value) return
  pieChart = echarts.init(pieChartRef.value)

  const pieData = data?.taskTypes || [
    { name: '加好友', value: 35 },
    { name: '群发消息', value: 28 },
    { name: '朋友圈', value: 18 },
    { name: '自动回复', value: 12 },
    { name: '数据采集', value: 7 }
  ]

  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)',
      backgroundColor: '#fff',
      borderColor: '#eee',
      borderWidth: 1,
      textStyle: { color: '#303133' }
    },
    legend: {
      orient: 'vertical',
      right: '5%',
      top: 'center',
      textStyle: { color: '#606266' }
    },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['35%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 6,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: { show: false },
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold'
          }
        },
        data: pieData,
        color: ['#409EFF', '#67c23a', '#e6a23c', '#f56c6c', '#909399']
      }
    ]
  }

  pieChart.setOption(option)
}

function getLast7Days() {
  const days = []
  for (let i = 6; i >= 0; i--) {
    const d = new Date()
    d.setDate(d.getDate() - i)
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    days.push(`${m}-${day}`)
  }
  return days
}

async function fetchData() {
  loading.value = true
  try {
    const [statsRes, tasksRes, devicesRes] = await Promise.allSettled([
      getDashboardStats(),
      getTasks({ page: 1, pageSize: 10, sort: 'createdAt', order: 'desc' }),
      getDevices({ page: 1, pageSize: 5, status: 'online' })
    ])

    if (statsRes.status === 'fulfilled' && statsRes.value) {
      const data = statsRes.value.data || statsRes.value
      stats.value = {
        totalUsers: data.totalUsers ?? 0,
        onlineDevices: data.onlineDevices ?? 0,
        todayTasks: data.todayTasks ?? 0,
        successRate: data.successRate ?? 0
      }
    }

    if (tasksRes.status === 'fulfilled' && tasksRes.value) {
      const data = tasksRes.value.data || tasksRes.value
      recentTasks.value = data.list || data.tasks || data.rows || []
    }

    if (devicesRes.status === 'fulfilled' && devicesRes.value) {
      const data = devicesRes.value.data || devicesRes.value
      recentDevices.value = data.list || data.devices || data.rows || []
    }

    await nextTick()
    const chartData = statsRes.status === 'fulfilled' ? (statsRes.value?.data || statsRes.value) : null
    initTrendChart(chartData)
    initPieChart(chartData)
  } catch (error) {
    console.error('获取仪表盘数据失败:', error)
    // Still init charts with default data
    await nextTick()
    initTrendChart(null)
    initPieChart(null)
  } finally {
    loading.value = false
  }
}

function handleResize() {
  trendChart?.resize()
  pieChart?.resize()
}

onMounted(() => {
  fetchData()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  pieChart?.dispose()
})
</script>

<style scoped>
.dashboard {
  min-height: 100%;
}

.chart-container {
  width: 100%;
  height: 300px;
}

.tables-row {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: 16px;
}

@media (max-width: 1200px) {
  .tables-row {
    grid-template-columns: 1fr;
  }
}

.table-section {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.recent-table {
  width: 100%;
}
</style>
