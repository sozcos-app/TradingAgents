<template>
  <div class="stock-health-view">
    <!-- 搜索栏 -->
    <div class="search-bar">
      <el-input
        v-model="searchCode"
        placeholder="输入股票代码，如 000001.SZ"
        style="width: 300px;"
        clearable
        @keyup.enter="handleCheck"
      >
        <template #append>
          <el-button type="primary" :loading="loading" @click="handleCheck">开始体检</el-button>
        </template>
      </el-input>
    </div>

    <!-- 体检结果 -->
    <div v-if="report">
      <StockHealthReport :report="report" />

      <!-- AI 深度分析 -->
      <div style="margin-top: 16px;">
        <el-button type="primary" :loading="insightLoading" @click="handleStockInsight">
          AI 深度风险分析
        </el-button>
        <AiInsightCard
          v-if="stockInsight"
          :content="stockInsight"
          type="stock"
        />
      </div>

      <!-- 历史趋势 -->
      <el-card v-if="historyItems.length > 1" shadow="hover" style="margin-top: 16px;">
        <div class="history-title">历史体检趋势</div>
        <v-chart v-if="historyOption" :option="historyOption as any" :autoresize="true" style="height: 240px;" />
      </el-card>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" style="text-align: center; padding: 60px 0;">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
      <div style="margin-top: 12px; color: #909399;">正在采集数据并评分...</div>
    </div>

    <!-- 无数据 -->
    <el-empty v-if="!loading && !report" description="输入股票代码开始体检" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { calendarApi } from '@/api/calendar'
import type { StockHealthCheck } from '@/types/calendar'
import StockHealthReport from '@/components/Calendar/StockHealthReport.vue'
import AiInsightCard from '@/components/Calendar/AiInsightCard.vue'
import VChart from 'vue-echarts'

const searchCode = ref('')
const loading = ref(false)
const report = ref<StockHealthCheck | null>(null)
const historyItems = ref<StockHealthCheck[]>([])
const stockInsight = ref('')
const insightLoading = ref(false)

const historyOption = computed(() => {
  if (historyItems.value.length < 2) return null
  const sorted = [...historyItems.value].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
  const dates = sorted.map(h => h.date?.slice(0, 10) || '')
  const scores = sorted.map(h => h.total_score)

  return {
    tooltip: { trigger: 'axis' },
    grid: { top: 20, bottom: 30, left: 50, right: 20 },
    xAxis: { type: 'category', data: dates },
    yAxis: { type: 'value', min: 0, max: 100 },
    series: [{
      type: 'line',
      data: scores,
      smooth: true,
      areaStyle: { color: 'rgba(64,158,255,0.15)' },
      itemStyle: { color: '#409eff' },
      markLine: {
        silent: true,
        data: [
          { yAxis: 80, lineStyle: { color: '#67c23a', type: 'dashed' } },
          { yAxis: 60, lineStyle: { color: '#e6a23c', type: 'dashed' } },
        ],
      },
    }],
  }
})

async function handleCheck() {
  const code = searchCode.value.trim().toUpperCase()
  if (!code) {
    ElMessage.warning('请输入股票代码')
    return
  }

  loading.value = true
  report.value = null
  try {
    const res = await calendarApi.stockHealth.check(code)
    report.value = res.data
    ElMessage.success(`体检完成: ${res.data?.total_score}分 - ${res.data?.conclusion}`)
    // 加载历史
    loadHistory(code)
  } catch (e: any) {
    ElMessage.error(e?.message || '体检失败')
  } finally {
    loading.value = false
  }
}

async function loadHistory(tsCode: string) {
  try {
    const res = await calendarApi.stockHealth.getHistory(tsCode, { page_size: 20 })
    historyItems.value = res.data?.items || []
  } catch {
    historyItems.value = []
  }
}

async function handleStockInsight() {
  if (!report.value?.ts_code) return
  insightLoading.value = true
  stockInsight.value = ''
  try {
    const res = await calendarApi.insight.analyzeStock(report.value.ts_code)
    stockInsight.value = res.data?.content || ''
    if (!stockInsight.value) {
      ElMessage.warning(res.message || '分析结果为空')
    }
  } catch (e: any) {
    ElMessage.error(e?.message || 'AI分析失败')
  } finally {
    insightLoading.value = false
  }
}
</script>

<style scoped>
.stock-health-view {
  padding: 16px 0;
}

.search-bar {
  margin-bottom: 20px;
  display: flex;
  gap: 12px;
}

.history-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}
</style>
