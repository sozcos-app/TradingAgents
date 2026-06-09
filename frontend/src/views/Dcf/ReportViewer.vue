<template>
  <div class="report-viewer">
    <!-- 搜索栏 -->
    <el-row :gutter="12" align="middle">
      <el-col :span="8">
        <el-input
          v-model="stockCode"
          placeholder="输入股票代码，如 002138"
          clearable
          @keyup.enter="handleSearch"
        />
      </el-col>
      <el-col :span="6">
        <el-select v-model="category" placeholder="报告类型" style="width: 100%">
          <el-option label="年度报告" value="annual" />
          <el-option label="一季报" value="quarter1" />
          <el-option label="半年度报告" value="semi" />
          <el-option label="三季报" value="quarter3" />
        </el-select>
      </el-col>
      <el-col :span="4">
        <el-button type="primary" :loading="store.cninfoLoading" @click="handleSearch">
          搜索公告
        </el-button>
      </el-col>
    </el-row>

    <!-- 搜索结果 -->
    <div v-if="store.cninfoResults" style="margin-top: 16px">
      <div class="result-summary">
        共找到 {{ store.cninfoResults.total }} 条公告，
        当前显示 {{ store.cninfoResults.announcements.length }} 条
      </div>

      <el-table
        :data="store.cninfoResults.announcements"
        border
        size="small"
        style="margin-top: 12px"
      >
        <el-table-column prop="title" label="公告标题" min-width="400" show-overflow-tooltip />
        <el-table-column prop="sec_name" label="公司" width="120" />
        <el-table-column prop="pub_date" label="发布日期" width="120">
          <template #default="{ row }">
            {{ formatPubDate(row.pub_date) }}
          </template>
        </el-table-column>
        <el-table-column prop="adjunct_size" label="大小" width="100" align="right">
          <template #default="{ row }">
            {{ formatFileSize(row.adjunct_size) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              link
              size="small"
              :disabled="!row.download_url"
              @click="openReport(row.download_url)"
            >
              查看
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty
        v-if="store.cninfoResults.announcements.length === 0"
        description="未找到相关公告"
        style="margin-top: 20px"
      />
    </div>

    <el-empty v-if="!store.cninfoResults" description="输入股票代码后点击「搜索公告」" style="margin-top: 40px" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useDcfStore } from '@/stores/dcf'

const store = useDcfStore()

const stockCode = ref('')
const category = ref('annual')

function formatPubDate(timestamp: string | number): string {
  if (!timestamp) return ''
  const ts = typeof timestamp === 'string' ? Number(timestamp) : timestamp
  if (isNaN(ts) || ts === 0) return ''
  const d = new Date(ts)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function formatFileSize(bytes: number): string {
  if (!bytes || bytes === 0) return '-'
  if (bytes >= 1024 * 1024) return (bytes / 1024 / 1024).toFixed(1) + ' MB'
  if (bytes >= 1024) return (bytes / 1024).toFixed(0) + ' KB'
  return bytes + ' B'
}

function openReport(url: string) {
  if (!url) return
  window.open(url, '_blank')
}

async function handleSearch() {
  if (!stockCode.value.trim()) {
    ElMessage.warning('请输入股票代码')
    return
  }
  try {
    await store.searchCninfo(stockCode.value.trim(), category.value)
  } catch {
    ElMessage.error(store.error || '搜索公告失败')
  }
}
</script>

<style lang="scss" scoped>
.report-viewer {
  .result-summary {
    font-size: 13px;
    color: var(--el-text-color-secondary);
  }
}
</style>
