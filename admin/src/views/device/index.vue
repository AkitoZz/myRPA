<template>
  <div class="device-page">
    <!-- Filter Bar -->
    <div class="page-card">
      <el-form :inline="true" :model="filters" class="filter-form">
        <el-form-item label="设备名称">
          <el-input
            v-model="filters.deviceName"
            placeholder="请输入设备名称"
            clearable
            style="width: 180px"
            @clear="handleSearch"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable style="width: 130px" @change="handleSearch">
            <el-option label="在线" value="online" />
            <el-option label="离线" value="offline" />
            <el-option label="封禁" value="banned" />
          </el-select>
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
        <el-table-column prop="deviceName" label="设备名" min-width="120" show-overflow-tooltip />
        <el-table-column prop="fingerprint" label="指纹" width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <el-tooltip :content="row.fingerprint" placement="top" v-if="row.fingerprint">
              <span class="fingerprint-text">{{ row.fingerprint?.substring(0, 16) }}...</span>
            </el-tooltip>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="userName" label="所属用户" width="120" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.userName || row.user?.nickname || row.userId || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="os" label="系统" width="100">
          <template #default="{ row }">
            {{ row.os || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="ip" label="IP地址" width="140">
          <template #default="{ row }">
            {{ row.ip || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)">
              <span class="status-dot" :class="'status-dot--' + (row.status || 'offline')"></span>
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="lastHeartbeat" label="最后心跳" width="170">
          <template #default="{ row }">
            {{ formatTime(row.lastHeartbeat) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleDetail(row)">
              <el-icon><View /></el-icon> 详情
            </el-button>
            <el-button
              :type="row.status === 'banned' ? 'success' : 'warning'"
              link
              size="small"
              @click="handleToggleBan(row)"
            >
              <el-icon><component :is="row.status === 'banned' ? 'CircleCheck' : 'CircleClose'" /></el-icon>
              {{ row.status === 'banned' ? '解封' : '封禁' }}
            </el-button>
            <el-popconfirm
              title="确定要删除该设备吗？"
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
          @size-change="fetchDevices"
          @current-change="fetchDevices"
        />
      </div>
    </div>

    <!-- Detail Dialog -->
    <el-dialog
      v-model="detailDialogVisible"
      title="设备详情"
      width="560px"
    >
      <el-descriptions :column="2" border v-if="currentDevice">
        <el-descriptions-item label="设备ID">{{ currentDevice.id }}</el-descriptions-item>
        <el-descriptions-item label="设备名称">{{ currentDevice.deviceName }}</el-descriptions-item>
        <el-descriptions-item label="设备指纹" :span="2">{{ currentDevice.fingerprint || '-' }}</el-descriptions-item>
        <el-descriptions-item label="所属用户">{{ currentDevice.userName || currentDevice.user?.nickname || currentDevice.userId || '-' }}</el-descriptions-item>
        <el-descriptions-item label="操作系统">{{ currentDevice.os || '-' }}</el-descriptions-item>
        <el-descriptions-item label="IP地址">{{ currentDevice.ip || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusTag(currentDevice.status)">{{ statusLabel(currentDevice.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="系统版本">{{ currentDevice.osVersion || '-' }}</el-descriptions-item>
        <el-descriptions-item label="APP版本">{{ currentDevice.appVersion || '-' }}</el-descriptions-item>
        <el-descriptions-item label="最后心跳" :span="2">{{ formatTime(currentDevice.lastHeartbeat) }}</el-descriptions-item>
        <el-descriptions-item label="注册时间" :span="2">{{ formatTime(currentDevice.createdAt) }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { getDevices, updateDevice, deleteDevice } from '@/api/device'
import { ElMessage } from 'element-plus'
import { Search, Refresh, View, Delete, CircleCheck, CircleClose } from '@element-plus/icons-vue'

const loading = ref(false)
const tableData = ref([])
const detailDialogVisible = ref(false)
const currentDevice = ref(null)
let autoRefreshTimer = null

const filters = reactive({
  deviceName: '',
  status: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

function statusLabel(status) {
  const map = { online: '在线', offline: '离线', banned: '封禁' }
  return map[status] || '离线'
}

function statusTag(status) {
  const map = { online: 'success', offline: 'info', banned: 'danger' }
  return map[status] || 'info'
}

function formatTime(time) {
  if (!time) return '-'
  const d = new Date(time)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

async function fetchDevices() {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      pageSize: pagination.pageSize,
      ...filters
    }
    Object.keys(params).forEach(key => {
      if (params[key] === '' || params[key] === null || params[key] === undefined) {
        delete params[key]
      }
    })
    const res = await getDevices(params)
    const data = res.data || res
    tableData.value = data.list || data.devices || data.rows || []
    pagination.total = data.total || 0
  } catch (error) {
    console.error('获取设备列表失败:', error)
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.page = 1
  fetchDevices()
}

function handleReset() {
  filters.deviceName = ''
  filters.status = ''
  pagination.page = 1
  fetchDevices()
}

function handleDetail(row) {
  currentDevice.value = { ...row }
  detailDialogVisible.value = true
}

async function handleToggleBan(row) {
  const newStatus = row.status === 'banned' ? 'offline' : 'banned'
  const action = newStatus === 'banned' ? '封禁' : '解封'
  try {
    await updateDevice(row.id, { status: newStatus })
    ElMessage.success(`${action}成功`)
    fetchDevices()
  } catch (error) {
    console.error(`${action}失败:`, error)
  }
}

async function handleDelete(row) {
  try {
    await deleteDevice(row.id)
    ElMessage.success('删除成功')
    fetchDevices()
  } catch (error) {
    console.error('删除设备失败:', error)
  }
}

// Auto-refresh every 30s
function startAutoRefresh() {
  autoRefreshTimer = setInterval(() => {
    fetchDevices()
  }, 30000)
}

onMounted(() => {
  fetchDevices()
  startAutoRefresh()
})

onUnmounted(() => {
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer)
    autoRefreshTimer = null
  }
})
</script>

<style scoped>
.device-page {
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

.fingerprint-text {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: #909399;
}
</style>
