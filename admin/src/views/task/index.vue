<template>
  <div class="task-page">
    <!-- Filters -->
    <div class="page-card">
      <el-form :inline="true" :model="filters" class="filter-form">
        <el-form-item label="任务类型">
          <el-select v-model="filters.type" placeholder="全部" clearable style="width: 130px" @change="handleSearch">
            <el-option label="加好友" value="add_friend" />
            <el-option label="群发消息" value="group_send" />
            <el-option label="朋友圈" value="moments" />
            <el-option label="自动回复" value="auto_reply" />
            <el-option label="数据采集" value="collect" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable style="width: 130px" @change="handleSearch">
            <el-option label="待执行" value="pending" />
            <el-option label="运行中" value="running" />
            <el-option label="已暂停" value="paused" />
            <el-option label="已完成" value="completed" />
            <el-option label="失败" value="failed" />
            <el-option label="已停止" value="stopped" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="filters.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 260px"
            @change="handleSearch"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">搜索</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- Table -->
    <div class="table-wrapper">
      <el-table :data="tableData" v-loading="loading" stripe border style="width: 100%">
        <el-table-column prop="id" label="ID" width="70" align="center" />
        <el-table-column prop="name" label="任务名称" min-width="140" show-overflow-tooltip />
        <el-table-column prop="type" label="类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="taskTypeTag(row.type)" size="small">{{ taskTypeLabel(row.type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="wechatName" label="关联微信" width="120" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.wechatName || row.wechatAccount?.nickname || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="taskStatusTag(row.status)" size="small" effect="dark">
              {{ taskStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="progress" label="进度" width="150">
          <template #default="{ row }">
            <el-progress
              :percentage="row.progress || 0"
              :status="progressStatus(row.status)"
              :stroke-width="8"
            />
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="创建时间" width="170">
          <template #default="{ row }">
            {{ formatTime(row.createdAt) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleViewDetail(row)">
              <el-icon><View /></el-icon> 详情
            </el-button>
            <el-button
              v-if="row.status === 'pending' || row.status === 'paused'"
              type="success"
              link
              size="small"
              @click="handleStart(row)"
            >
              <el-icon><VideoPlay /></el-icon> 启动
            </el-button>
            <el-button
              v-if="row.status === 'running'"
              type="warning"
              link
              size="small"
              @click="handlePause(row)"
            >
              <el-icon><VideoPause /></el-icon> 暂停
            </el-button>
            <el-button
              v-if="row.status === 'running' || row.status === 'paused'"
              type="danger"
              link
              size="small"
              @click="handleStop(row)"
            >
              <el-icon><SwitchButton /></el-icon> 停止
            </el-button>
            <el-popconfirm
              v-if="row.status === 'completed' || row.status === 'failed' || row.status === 'stopped'"
              title="确定要删除该任务吗？"
              confirm-button-text="确定"
              cancel-button-text="取消"
              @confirm="handleDelete(row)"
            >
              <template #reference>
                <el-button type="danger" link size="small">
                  <el-icon><Delete /></el-icon> 删除
                </el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchTasks"
          @current-change="fetchTasks"
        />
      </div>
    </div>

    <!-- Detail Drawer -->
    <el-drawer
      v-model="drawerVisible"
      title="任务详情"
      size="560px"
      :destroy-on-close="true"
    >
      <template v-if="currentTask">
        <el-descriptions :column="1" border class="task-desc">
          <el-descriptions-item label="任务ID">{{ currentTask.id }}</el-descriptions-item>
          <el-descriptions-item label="任务名称">{{ currentTask.name }}</el-descriptions-item>
          <el-descriptions-item label="任务类型">
            <el-tag :type="taskTypeTag(currentTask.type)" size="small">{{ taskTypeLabel(currentTask.type) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="关联微信">{{ currentTask.wechatName || currentTask.wechatAccount?.nickname || '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="taskStatusTag(currentTask.status)" size="small" effect="dark">{{ taskStatusLabel(currentTask.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="进度">
            <el-progress :percentage="currentTask.progress || 0" :status="progressStatus(currentTask.status)" />
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatTime(currentTask.createdAt) }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ formatTime(currentTask.updatedAt) }}</el-descriptions-item>
        </el-descriptions>

        <!-- Config Section -->
        <div class="drawer-section">
          <h4 class="drawer-section-title">任务配置</h4>
          <el-card shadow="never" class="config-card">
            <pre class="config-json">{{ formatConfig(currentTask.config) }}</pre>
          </el-card>
        </div>

        <!-- Logs Section -->
        <div class="drawer-section">
          <h4 class="drawer-section-title">执行日志</h4>
          <el-card shadow="never" class="log-card">
            <div v-if="currentTask.logs && currentTask.logs.length > 0" class="log-list">
              <div v-for="(log, index) in currentTask.logs" :key="index" class="log-item">
                <span class="log-time">{{ formatTime(log.time) }}</span>
                <el-tag :type="logLevelTag(log.level)" size="small" class="log-level">{{ log.level || 'info' }}</el-tag>
                <span class="log-message">{{ log.message }}</span>
              </div>
            </div>
            <el-empty v-else description="暂无日志" :image-size="60" />
          </el-card>
        </div>

        <!-- Result Section -->
        <div class="drawer-section">
          <h4 class="drawer-section-title">执行结果</h4>
          <el-card shadow="never" class="config-card">
            <pre v-if="currentTask.result" class="config-json">{{ formatConfig(currentTask.result) }}</pre>
            <el-empty v-else description="暂无结果" :image-size="60" />
          </el-card>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { getTasks, getTask, startTask, pauseTask, stopTask, deleteTask } from '@/api/task'
import { ElMessage } from 'element-plus'
import {
  Search, Refresh, View, Delete, VideoPlay, VideoPause, SwitchButton
} from '@element-plus/icons-vue'

const loading = ref(false)
const tableData = ref([])
const drawerVisible = ref(false)
const currentTask = ref(null)

const filters = reactive({
  type: '',
  status: '',
  dateRange: null
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

// Task type helpers
const taskTypeMap = {
  add_friend: '加好友',
  group_send: '群发消息',
  moments: '朋友圈',
  auto_reply: '自动回复',
  collect: '数据采集'
}
function taskTypeLabel(type) { return taskTypeMap[type] || type || '未知' }
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
function taskStatusLabel(status) { return taskStatusMap[status] || status || '未知' }
function taskStatusTag(status) {
  const map = { pending: 'info', running: '', paused: 'warning', completed: 'success', failed: 'danger', stopped: 'info' }
  return map[status] || 'info'
}

function progressStatus(status) {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'exception'
  return undefined
}

function logLevelTag(level) {
  const map = { info: 'info', warn: 'warning', error: 'danger', debug: '' }
  return map[level] || 'info'
}

function formatTime(time) {
  if (!time) return '-'
  const d = new Date(time)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function formatConfig(config) {
  if (!config) return '{}'
  if (typeof config === 'string') {
    try { return JSON.stringify(JSON.parse(config), null, 2) } catch { return config }
  }
  return JSON.stringify(config, null, 2)
}

async function fetchTasks() {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      pageSize: pagination.pageSize,
      type: filters.type || undefined,
      status: filters.status || undefined
    }
    if (filters.dateRange && filters.dateRange.length === 2) {
      params.startDate = filters.dateRange[0]
      params.endDate = filters.dateRange[1]
    }
    Object.keys(params).forEach(key => {
      if (params[key] === undefined || params[key] === '') {
        delete params[key]
      }
    })
    const res = await getTasks(params)
    const data = res.data || res
    tableData.value = data.list || data.tasks || data.rows || []
    pagination.total = data.total || 0
  } catch (error) {
    console.error('获取任务列表失败:', error)
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.page = 1
  fetchTasks()
}

function handleReset() {
  filters.type = ''
  filters.status = ''
  filters.dateRange = null
  pagination.page = 1
  fetchTasks()
}

async function handleViewDetail(row) {
  try {
    const res = await getTask(row.id)
    currentTask.value = res.data || res
    drawerVisible.value = true
  } catch (error) {
    // Fallback to row data
    currentTask.value = { ...row }
    drawerVisible.value = true
  }
}

async function handleStart(row) {
  try {
    await startTask(row.id)
    ElMessage.success('任务已启动')
    fetchTasks()
  } catch (error) {
    console.error('启动任务失败:', error)
  }
}

async function handlePause(row) {
  try {
    await pauseTask(row.id)
    ElMessage.success('任务已暂停')
    fetchTasks()
  } catch (error) {
    console.error('暂停任务失败:', error)
  }
}

async function handleStop(row) {
  try {
    await stopTask(row.id)
    ElMessage.success('任务已停止')
    fetchTasks()
  } catch (error) {
    console.error('停止任务失败:', error)
  }
}

async function handleDelete(row) {
  try {
    await deleteTask(row.id)
    ElMessage.success('删除成功')
    fetchTasks()
  } catch (error) {
    console.error('删除任务失败:', error)
  }
}

onMounted(() => {
  fetchTasks()
})
</script>

<style scoped>
.task-page {
  min-height: 100%;
}

.filter-form {
  display: flex;
  flex-wrap: wrap;
  gap: 0;
}

.filter-form .el-form-item {
  margin-bottom: 0;
}

.drawer-section {
  margin-top: 24px;
}

.drawer-section-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 12px;
  padding-left: 8px;
  border-left: 3px solid #409EFF;
}

.task-desc {
  margin-bottom: 8px;
}

.config-card {
  background: #fafafa;
}

.config-json {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: #606266;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
  line-height: 1.6;
}

.log-card {
  background: #fafafa;
  max-height: 300px;
  overflow-y: auto;
}

.log-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.log-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 12px;
  line-height: 1.6;
  padding: 4px 0;
  border-bottom: 1px solid #f0f0f0;
}

.log-item:last-child {
  border-bottom: none;
}

.log-time {
  color: #909399;
  white-space: nowrap;
  font-family: 'Courier New', monospace;
}

.log-level {
  flex-shrink: 0;
}

.log-message {
  color: #606266;
  word-break: break-all;
}
</style>
