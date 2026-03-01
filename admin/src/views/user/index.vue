<template>
  <div class="user-page">
    <!-- Search / Filter Bar -->
    <div class="page-card">
      <el-form :inline="true" :model="filters" class="filter-form">
        <el-form-item label="手机号">
          <el-input
            v-model="filters.phone"
            placeholder="请输入手机号"
            clearable
            style="width: 180px"
            @clear="handleSearch"
          />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="filters.role" placeholder="全部" clearable style="width: 130px" @change="handleSearch">
            <el-option label="管理员" value="admin" />
            <el-option label="普通用户" value="user" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable style="width: 130px" @change="handleSearch">
            <el-option label="正常" value="active" />
            <el-option label="禁用" value="disabled" />
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
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column prop="nickname" label="昵称" min-width="100" show-overflow-tooltip />
        <el-table-column prop="role" label="角色" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : ''">
              {{ row.role === 'admin' ? '管理员' : '普通用户' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="memberLevel" label="会员等级" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="memberLevelTag(row.memberLevel)">
              {{ memberLevelLabel(row.memberLevel) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'danger'">
              {{ row.status === 'active' ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="注册时间" width="170">
          <template #default="{ row }">
            {{ formatTime(row.createdAt) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleEdit(row)">
              <el-icon><Edit /></el-icon> 编辑
            </el-button>
            <el-button
              :type="row.status === 'active' ? 'warning' : 'success'"
              link
              size="small"
              @click="handleToggleStatus(row)"
            >
              <el-icon><component :is="row.status === 'active' ? 'Lock' : 'Unlock'" /></el-icon>
              {{ row.status === 'active' ? '禁用' : '启用' }}
            </el-button>
            <el-popconfirm
              title="确定要删除该用户吗？"
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
          @size-change="fetchUsers"
          @current-change="fetchUsers"
        />
      </div>
    </div>

    <!-- Edit Dialog -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑用户"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="editFormRef"
        :model="editForm"
        :rules="editRules"
        label-width="85px"
      >
        <el-form-item label="手机号">
          <el-input :model-value="editForm.phone" disabled />
        </el-form-item>
        <el-form-item label="昵称" prop="nickname">
          <el-input v-model="editForm.nickname" placeholder="请输入昵称" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="editForm.role" style="width: 100%">
            <el-option label="管理员" value="admin" />
            <el-option label="普通用户" value="user" />
          </el-select>
        </el-form-item>
        <el-form-item label="会员等级" prop="memberLevel">
          <el-select v-model="editForm.memberLevel" style="width: 100%">
            <el-option label="免费用户" :value="0" />
            <el-option label="基础会员" :value="1" />
            <el-option label="高级会员" :value="2" />
            <el-option label="企业会员" :value="3" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="editForm.status" style="width: 100%">
            <el-option label="正常" value="active" />
            <el-option label="禁用" value="disabled" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmitEdit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { getUsers, updateUser, deleteUser } from '@/api/user'
import { ElMessage } from 'element-plus'
import { Search, Refresh, Edit, Delete, Lock, Unlock } from '@element-plus/icons-vue'

const loading = ref(false)
const submitLoading = ref(false)
const tableData = ref([])
const editDialogVisible = ref(false)
const editFormRef = ref(null)

const filters = reactive({
  phone: '',
  role: '',
  status: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const editForm = reactive({
  id: null,
  phone: '',
  nickname: '',
  role: '',
  memberLevel: 0,
  status: ''
})

const editRules = {
  nickname: [{ required: true, message: '请输入昵称', trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }]
}

const memberLevelMap = { 0: '免费用户', 1: '基础会员', 2: '高级会员', 3: '企业会员' }
function memberLevelLabel(level) {
  return memberLevelMap[level] || '免费用户'
}
function memberLevelTag(level) {
  const map = { 0: 'info', 1: '', 2: 'warning', 3: 'danger' }
  return map[level] || 'info'
}

function formatTime(time) {
  if (!time) return '-'
  const d = new Date(time)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

async function fetchUsers() {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      pageSize: pagination.pageSize,
      ...filters
    }
    // Remove empty params
    Object.keys(params).forEach(key => {
      if (params[key] === '' || params[key] === null || params[key] === undefined) {
        delete params[key]
      }
    })
    const res = await getUsers(params)
    const data = res.data || res
    tableData.value = data.list || data.users || data.rows || []
    pagination.total = data.total || 0
  } catch (error) {
    console.error('获取用户列表失败:', error)
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.page = 1
  fetchUsers()
}

function handleReset() {
  filters.phone = ''
  filters.role = ''
  filters.status = ''
  pagination.page = 1
  fetchUsers()
}

function handleEdit(row) {
  editForm.id = row.id
  editForm.phone = row.phone
  editForm.nickname = row.nickname || ''
  editForm.role = row.role || 'user'
  editForm.memberLevel = row.memberLevel ?? 0
  editForm.status = row.status || 'active'
  editDialogVisible.value = true
}

async function handleSubmitEdit() {
  if (!editFormRef.value) return
  await editFormRef.value.validate(async (valid) => {
    if (!valid) return
    submitLoading.value = true
    try {
      await updateUser(editForm.id, {
        nickname: editForm.nickname,
        role: editForm.role,
        memberLevel: editForm.memberLevel,
        status: editForm.status
      })
      ElMessage.success('更新成功')
      editDialogVisible.value = false
      fetchUsers()
    } catch (error) {
      console.error('更新用户失败:', error)
    } finally {
      submitLoading.value = false
    }
  })
}

async function handleToggleStatus(row) {
  const newStatus = row.status === 'active' ? 'disabled' : 'active'
  try {
    await updateUser(row.id, { status: newStatus })
    ElMessage.success(newStatus === 'active' ? '已启用' : '已禁用')
    fetchUsers()
  } catch (error) {
    console.error('切换状态失败:', error)
  }
}

async function handleDelete(row) {
  try {
    await deleteUser(row.id)
    ElMessage.success('删除成功')
    fetchUsers()
  } catch (error) {
    console.error('删除用户失败:', error)
  }
}

onMounted(() => {
  fetchUsers()
})
</script>

<style scoped>
.user-page {
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
</style>
