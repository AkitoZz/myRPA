<template>
  <div class="wechat-page">
    <!-- Filter Bar -->
    <div class="page-card">
      <div class="flex-between" style="flex-wrap: wrap; gap: 12px;">
        <el-form :inline="true" :model="filters" class="filter-form">
          <el-form-item label="微信昵称">
            <el-input
              v-model="filters.nickname"
              placeholder="请输入昵称"
              clearable
              style="width: 180px"
              @clear="handleSearch"
            />
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="filters.status" placeholder="全部" clearable style="width: 130px" @change="handleSearch">
              <el-option label="在线" value="online" />
              <el-option label="离线" value="offline" />
              <el-option label="异常" value="abnormal" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :icon="Search" @click="handleSearch">搜索</el-button>
            <el-button :icon="Refresh" @click="handleReset">重置</el-button>
          </el-form-item>
        </el-form>
        <el-button type="primary" :icon="Plus" @click="handleAdd">
          添加账号
        </el-button>
      </div>
    </div>

    <!-- Table -->
    <div class="table-wrapper">
      <el-table :data="tableData" v-loading="loading" stripe border style="width: 100%">
        <el-table-column prop="wxid" label="微信ID" width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="wxid-text">{{ row.wxid || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="nickname" label="昵称" min-width="120" show-overflow-tooltip />
        <el-table-column prop="deviceName" label="所属设备" width="140" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.deviceName || row.device?.deviceName || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" size="small">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="todayFriendAdded" label="今日加好友" width="110" align="center">
          <template #default="{ row }">
            <span :class="{ 'text-bold': (row.todayFriendAdded || 0) > 0 }">
              {{ row.todayFriendAdded || 0 }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="todayGroupSent" label="今日群发" width="100" align="center">
          <template #default="{ row }">
            <span :class="{ 'text-bold': (row.todayGroupSent || 0) > 0 }">
              {{ row.todayGroupSent || 0 }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleEdit(row)">
              <el-icon><Edit /></el-icon> 编辑
            </el-button>
            <el-popconfirm
              title="确定要删除该微信账号吗？"
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
          @size-change="fetchAccounts"
          @current-change="fetchAccounts"
        />
      </div>
    </div>

    <!-- Add/Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑微信账号' : '添加微信账号'"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="formRules"
        label-width="85px"
      >
        <el-form-item label="微信ID" prop="wxid">
          <el-input v-model="form.wxid" placeholder="请输入微信ID" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="昵称" prop="nickname">
          <el-input v-model="form.nickname" placeholder="请输入昵称" />
        </el-form-item>
        <el-form-item label="所属设备" prop="deviceId">
          <el-input v-model="form.deviceId" placeholder="请输入设备ID" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="form.status" style="width: 100%">
            <el-option label="在线" value="online" />
            <el-option label="离线" value="offline" />
            <el-option label="异常" value="abnormal" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { getAccounts, createAccount, updateAccount, deleteAccount } from '@/api/wechatAccount'
import { ElMessage } from 'element-plus'
import { Search, Refresh, Plus, Edit, Delete } from '@element-plus/icons-vue'

const loading = ref(false)
const submitLoading = ref(false)
const tableData = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref(null)

const filters = reactive({
  nickname: '',
  status: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const form = reactive({
  id: null,
  wxid: '',
  nickname: '',
  deviceId: '',
  status: 'online'
})

const formRules = {
  wxid: [{ required: true, message: '请输入微信ID', trigger: 'blur' }],
  nickname: [{ required: true, message: '请输入昵称', trigger: 'blur' }]
}

function statusLabel(status) {
  const map = { online: '在线', offline: '离线', abnormal: '异常' }
  return map[status] || '离线'
}

function statusTag(status) {
  const map = { online: 'success', offline: 'info', abnormal: 'danger' }
  return map[status] || 'info'
}

async function fetchAccounts() {
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
    const res = await getAccounts(params)
    const data = res.data || res
    tableData.value = data.list || data.accounts || data.rows || []
    pagination.total = data.total || 0
  } catch (error) {
    console.error('获取微信账号列表失败:', error)
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.page = 1
  fetchAccounts()
}

function handleReset() {
  filters.nickname = ''
  filters.status = ''
  pagination.page = 1
  fetchAccounts()
}

function resetForm() {
  form.id = null
  form.wxid = ''
  form.nickname = ''
  form.deviceId = ''
  form.status = 'online'
}

function handleAdd() {
  isEdit.value = false
  resetForm()
  dialogVisible.value = true
}

function handleEdit(row) {
  isEdit.value = true
  form.id = row.id
  form.wxid = row.wxid || ''
  form.nickname = row.nickname || ''
  form.deviceId = row.deviceId || ''
  form.status = row.status || 'online'
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitLoading.value = true
    try {
      const payload = {
        wxid: form.wxid,
        nickname: form.nickname,
        deviceId: form.deviceId || undefined,
        status: form.status
      }
      if (isEdit.value) {
        await updateAccount(form.id, payload)
        ElMessage.success('更新成功')
      } else {
        await createAccount(payload)
        ElMessage.success('添加成功')
      }
      dialogVisible.value = false
      fetchAccounts()
    } catch (error) {
      console.error('操作失败:', error)
    } finally {
      submitLoading.value = false
    }
  })
}

async function handleDelete(row) {
  try {
    await deleteAccount(row.id)
    ElMessage.success('删除成功')
    fetchAccounts()
  } catch (error) {
    console.error('删除微信账号失败:', error)
  }
}

onMounted(() => {
  fetchAccounts()
})
</script>

<style scoped>
.wechat-page {
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

.wxid-text {
  font-family: 'Courier New', monospace;
  font-size: 13px;
  color: #606266;
}
</style>
