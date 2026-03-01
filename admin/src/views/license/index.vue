<template>
  <div class="license-page">
    <!-- Actions & Filters -->
    <div class="page-card">
      <div class="flex-between" style="flex-wrap: wrap; gap: 12px;">
        <el-form :inline="true" :model="filters" class="filter-form">
          <el-form-item label="类型">
            <el-select v-model="filters.type" placeholder="全部" clearable style="width: 130px" @change="handleSearch">
              <el-option label="试用" value="trial" />
              <el-option label="月卡" value="monthly" />
              <el-option label="季卡" value="quarterly" />
              <el-option label="年卡" value="yearly" />
              <el-option label="终身" value="lifetime" />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="filters.status" placeholder="全部" clearable style="width: 130px" @change="handleSearch">
              <el-option label="未使用" value="unused" />
              <el-option label="已激活" value="activated" />
              <el-option label="已过期" value="expired" />
              <el-option label="已撤销" value="revoked" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :icon="Search" @click="handleSearch">搜索</el-button>
            <el-button :icon="Refresh" @click="handleReset">重置</el-button>
          </el-form-item>
        </el-form>
        <el-button type="primary" :icon="Plus" @click="generateDialogVisible = true">
          生成授权码
        </el-button>
      </div>
    </div>

    <!-- Table -->
    <div class="table-wrapper">
      <el-table :data="tableData" v-loading="loading" stripe border style="width: 100%">
        <el-table-column prop="code" label="授权码" min-width="200">
          <template #default="{ row }">
            <div class="code-cell">
              <span class="code-text">{{ row.code }}</span>
              <el-button type="primary" link size="small" @click="handleCopy(row.code)" class="copy-btn">
                <el-icon><DocumentCopy /></el-icon>
              </el-button>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="type" label="类型" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="typeTag(row.type)" size="small">{{ typeLabel(row.type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="duration" label="时长（天）" width="100" align="center">
          <template #default="{ row }">
            {{ row.duration || durationByType(row.type) }}
          </template>
        </el-table-column>
        <el-table-column prop="userName" label="绑定用户" width="120" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.userName || row.user?.nickname || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="deviceName" label="绑定设备" width="120" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.deviceName || row.device?.deviceName || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="licenseStatusTag(row.status)" size="small">
              {{ licenseStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="activatedAt" label="激活时间" width="170">
          <template #default="{ row }">
            {{ formatTime(row.activatedAt) }}
          </template>
        </el-table-column>
        <el-table-column prop="expiresAt" label="到期时间" width="170">
          <template #default="{ row }">
            {{ formatTime(row.expiresAt) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right" align="center">
          <template #default="{ row }">
            <el-popconfirm
              v-if="row.status === 'activated' || row.status === 'unused'"
              title="确定要撤销该授权码吗？"
              confirm-button-text="确定"
              cancel-button-text="取消"
              @confirm="handleRevoke(row)"
            >
              <template #reference>
                <el-button type="danger" link size="small">
                  <el-icon><CircleClose /></el-icon> 撤销
                </el-button>
              </template>
            </el-popconfirm>
            <span v-else class="text-muted text-sm">-</span>
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
          @size-change="fetchLicenses"
          @current-change="fetchLicenses"
        />
      </div>
    </div>

    <!-- Generate Dialog -->
    <el-dialog
      v-model="generateDialogVisible"
      title="生成授权码"
      width="460px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="generateFormRef"
        :model="generateForm"
        :rules="generateRules"
        label-width="80px"
      >
        <el-form-item label="类型" prop="type">
          <el-select v-model="generateForm.type" style="width: 100%" placeholder="请选择授权类型">
            <el-option label="试用（3天）" value="trial" />
            <el-option label="月卡（30天）" value="monthly" />
            <el-option label="季卡（90天）" value="quarterly" />
            <el-option label="年卡（365天）" value="yearly" />
            <el-option label="终身" value="lifetime" />
          </el-select>
        </el-form-item>
        <el-form-item label="数量" prop="quantity">
          <el-input-number
            v-model="generateForm.quantity"
            :min="1"
            :max="100"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="generateDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="generateLoading" @click="handleGenerate">
          生成
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { getLicenses, generateLicense, revokeLicense } from '@/api/license'
import { ElMessage } from 'element-plus'
import { Search, Refresh, Plus, DocumentCopy, CircleClose } from '@element-plus/icons-vue'

const loading = ref(false)
const generateLoading = ref(false)
const tableData = ref([])
const generateDialogVisible = ref(false)
const generateFormRef = ref(null)

const filters = reactive({
  type: '',
  status: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const generateForm = reactive({
  type: 'monthly',
  quantity: 1
})

const generateRules = {
  type: [{ required: true, message: '请选择授权类型', trigger: 'change' }],
  quantity: [{ required: true, message: '请输入数量', trigger: 'blur' }]
}

const typeMap = { trial: '试用', monthly: '月卡', quarterly: '季卡', yearly: '年卡', lifetime: '终身' }
function typeLabel(type) { return typeMap[type] || type || '未知' }
function typeTag(type) {
  const map = { trial: 'info', monthly: '', quarterly: 'success', yearly: 'warning', lifetime: 'danger' }
  return map[type] || 'info'
}

function durationByType(type) {
  const map = { trial: 3, monthly: 30, quarterly: 90, yearly: 365, lifetime: '永久' }
  return map[type] || '-'
}

const statusMap = { unused: '未使用', activated: '已激活', expired: '已过期', revoked: '已撤销' }
function licenseStatusLabel(status) { return statusMap[status] || status || '未知' }
function licenseStatusTag(status) {
  const map = { unused: 'info', activated: 'success', expired: 'warning', revoked: 'danger' }
  return map[status] || 'info'
}

function formatTime(time) {
  if (!time) return '-'
  const d = new Date(time)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function handleCopy(text) {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制到剪贴板')
  } catch {
    // Fallback
    const textarea = document.createElement('textarea')
    textarea.value = text
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
    ElMessage.success('已复制到剪贴板')
  }
}

async function fetchLicenses() {
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
    const res = await getLicenses(params)
    const data = res.data || res
    tableData.value = data.list || data.licenses || data.rows || []
    pagination.total = data.total || 0
  } catch (error) {
    console.error('获取授权码列表失败:', error)
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.page = 1
  fetchLicenses()
}

function handleReset() {
  filters.type = ''
  filters.status = ''
  pagination.page = 1
  fetchLicenses()
}

async function handleGenerate() {
  if (!generateFormRef.value) return
  await generateFormRef.value.validate(async (valid) => {
    if (!valid) return
    generateLoading.value = true
    try {
      await generateLicense({
        type: generateForm.type,
        quantity: generateForm.quantity
      })
      ElMessage.success(`成功生成 ${generateForm.quantity} 个授权码`)
      generateDialogVisible.value = false
      generateForm.type = 'monthly'
      generateForm.quantity = 1
      fetchLicenses()
    } catch (error) {
      console.error('生成授权码失败:', error)
    } finally {
      generateLoading.value = false
    }
  })
}

async function handleRevoke(row) {
  try {
    await revokeLicense(row.id)
    ElMessage.success('撤销成功')
    fetchLicenses()
  } catch (error) {
    console.error('撤销授权码失败:', error)
  }
}

onMounted(() => {
  fetchLicenses()
})
</script>

<style scoped>
.license-page {
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

.code-cell {
  display: flex;
  align-items: center;
  gap: 4px;
}

.code-text {
  font-family: 'Courier New', monospace;
  font-size: 13px;
  color: #606266;
}

.copy-btn {
  padding: 2px;
  flex-shrink: 0;
}
</style>
