<template>
  <div class="macro-view">
    <!-- 顶部操作栏 -->
    <div class="macro-header">
      <el-button type="primary" :loading="store.loading" @click="handleFetch">
        刷新数据
      </el-button>
      <el-button type="success" :loading="store.loading" @click="handleScore">
        计算评分
      </el-button>
      <span class="update-time" v-if="lastUpdate">
        最近更新: {{ lastUpdate }}
      </span>
    </div>

    <!-- 评分仪表盘 + 雷达图 -->
    <el-row :gutter="16" v-if="store.macroScore" class="score-section">
      <el-col :xs="24" :sm="12">
        <el-card shadow="hover">
          <div class="score-gauge">
            <div class="gauge-value" :style="{ color: getScoreColor(store.macroScore.total_score) }">
              {{ store.macroScore.total_score }}
            </div>
            <div class="gauge-label">{{ store.macroScore.level }}</div>
            <el-progress
              :percentage="store.macroScore.total_score"
              :color="getScoreColor(store.macroScore.total_score)"
              :stroke-width="12"
              style="margin-top: 12px;"
            />
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12">
        <el-card shadow="hover">
          <div class="score-details">
            <div class="detail-title">各指标评分</div>
            <div v-for="(info, name) in store.macroScore.details" :key="name" class="detail-item">
              <div class="detail-name">{{ name }}</div>
              <el-progress
                :percentage="info.score"
                :color="getScoreColor(info.score)"
                :stroke-width="8"
                style="flex: 1;"
              />
              <span class="detail-score">{{ info.score }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 预警 -->
    <div v-if="store.macroScore?.alerts?.length" class="alerts-section">
      <el-alert
        v-for="(alert, idx) in store.macroScore.alerts"
        :key="idx"
        :title="`${alert.indicator}: ${alert.message}`"
        :type="alert.severity === '高' ? 'error' : 'warning'"
        show-icon
        style="margin-bottom: 8px;"
      />
    </div>

    <!-- 指标卡片 -->
    <el-row :gutter="16" class="indicator-cards">
      <el-col :xs="12" :sm="8" :md="6" v-for="item in store.macroIndicators" :key="item.indicator_name">
        <el-card shadow="hover" class="indicator-card" :class="getScoreClass(item)">
          <div class="card-header">
            <span class="card-title">{{ item.indicator_name }}</span>
            <el-tag :type="getTagType(item)" size="small">
              {{ item.score !== null && item.score !== undefined ? item.score : '-' }}
            </el-tag>
          </div>
          <div class="card-value">
            {{ item.value }}<span class="card-unit">{{ item.unit }}</span>
          </div>
          <div class="card-meta">
            <span v-if="item.year_on_year != null" class="card-change" :class="{ positive: item.year_on_year > 0, negative: item.year_on_year < 0 }">
              同比 {{ item.year_on_year > 0 ? '+' : '' }}{{ item.year_on_year }}%
            </span>
            <span v-if="item.month_on_month != null" class="card-change" :class="{ positive: item.month_on_month > 0, negative: item.month_on_month < 0 }">
              环比 {{ item.month_on_month > 0 ? '+' : '' }}{{ item.month_on_month }}%
            </span>
          </div>
          <div class="card-source">{{ item.source }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 无数据提示 -->
    <el-empty v-if="!store.loading && store.macroIndicators.length === 0" description="暂无宏观数据，请点击刷新数据采集" />

    <!-- ============ 二级市场指标 ============ -->
    <el-divider content-position="left">二级市场指标</el-divider>

    <div class="market-actions">
      <el-button type="warning" size="small" :loading="store.loading" @click="handleFetchMarket">
        采集市场数据
      </el-button>
      <el-button type="danger" size="small" :loading="store.loading" @click="handleDetectDivergence">
        检测背离信号
      </el-button>
    </div>

    <!-- 背离预警 -->
    <DivergenceAlert :signal="store.divergenceSignal" />

    <!-- 市场指标卡片 -->
    <MarketIndicatorCards v-if="store.marketIndicatorOverview" :overview="store.marketIndicatorOverview" />

    <!-- 图表区域 -->
    <el-row :gutter="16" class="chart-section">
      <el-col :xs="24" :sm="12">
        <AdvanceDeclineChart :data="advanceDeclineHistory" />
      </el-col>
      <el-col :xs="24" :sm="12">
        <LimitStatsChart :data="limitStatsHistory" />
      </el-col>
    </el-row>

    <!-- 成交额图 -->
    <div class="chart-section">
      <VolumeChart :data="volumeHistory" />
    </div>

    <!-- 板块热度图 -->
    <div class="chart-section">
      <SectorHeatmap :data="store.marketIndicatorOverview?.sector_ranking || []" />
    </div>

    <!-- ============ AI 深度分析 ============ -->
    <el-divider content-position="left">AI 深度分析</el-divider>

    <div class="ai-section">
      <el-button type="primary" :loading="insightLoading" @click="handleMacroInsight">
        AI 分析宏观谎言/机会
      </el-button>
      <AiInsightCard
        v-if="macroInsight"
        :content="macroInsight"
        type="macro"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, computed, ref } from 'vue'
import { useCalendarStore } from '@/stores/calendar'
import { ElMessage } from 'element-plus'
import { calendarApi } from '@/api/calendar'
import type { MarketIndicator } from '@/types/calendar'
import MarketIndicatorCards from '@/components/Calendar/MarketIndicatorCards.vue'
import AdvanceDeclineChart from '@/components/Calendar/AdvanceDeclineChart.vue'
import LimitStatsChart from '@/components/Calendar/LimitStatsChart.vue'
import VolumeChart from '@/components/Calendar/VolumeChart.vue'
import SectorHeatmap from '@/components/Calendar/SectorHeatmap.vue'
import DivergenceAlert from '@/components/Calendar/DivergenceAlert.vue'
import AiInsightCard from '@/components/Calendar/AiInsightCard.vue'

const store = useCalendarStore()

// 历史数据 (用于图表)
const advanceDeclineHistory = ref<MarketIndicator[]>([])
const limitStatsHistory = ref<MarketIndicator[]>([])
const volumeHistory = ref<MarketIndicator[]>([])
const macroInsight = ref('')
const insightLoading = ref(false)

const lastUpdate = computed(() => {
  if (store.macroIndicators.length === 0) return null
  const dates = store.macroIndicators.map(i => i.date).filter(Boolean).sort().reverse()
  return dates[0] || null
})

onMounted(() => {
  store.fetchMacroIndicators()
  store.fetchLatestScore()
  store.fetchMarketIndicators()
  store.fetchDivergence()
  loadHistoryData()
})

async function loadHistoryData() {
  try {
    const [adRes, limitRes, volRes] = await Promise.all([
      calendarApi.marketIndicator.getHistory({ indicator_type: 'advance_decline', page_size: 30 }),
      calendarApi.marketIndicator.getHistory({ indicator_type: 'limit_stats', page_size: 30 }),
      calendarApi.marketIndicator.getHistory({ indicator_type: 'volume', page_size: 30 }),
    ])
    advanceDeclineHistory.value = adRes.data?.items || []
    limitStatsHistory.value = limitRes.data?.items || []
    volumeHistory.value = volRes.data?.items || []
  } catch {
    // 历史数据可能为空，不报错
  }
}

async function handleFetch() {
  try {
    await calendarApi.macro.fetch()
    ElMessage.success(`采集完成`)
    await store.fetchMacroIndicators()
  } catch (e: any) {
    ElMessage.error(e?.message || '采集失败')
  }
}

async function handleScore() {
  try {
    const res = await calendarApi.macro.triggerScore()
    store.macroScore = res.data
    ElMessage.success(`评分完成: ${res.data?.total_score}分 - ${res.data?.level}`)
  } catch (e: any) {
    ElMessage.error(e?.message || '评分失败')
  }
}

async function handleFetchMarket() {
  try {
    await calendarApi.marketIndicator.fetch()
    ElMessage.success('市场数据采集完成')
    await store.fetchMarketIndicators()
    await loadHistoryData()
  } catch (e: any) {
    ElMessage.error(e?.message || '市场数据采集失败')
  }
}

async function handleDetectDivergence() {
  try {
    await store.detectDivergence()
    ElMessage.success(`检测完成: ${store.divergenceSignal?.judgment || '无背离'}`)
  } catch (e: any) {
    ElMessage.error(e?.message || '背离检测失败')
  }
}

function getScoreColor(score: number) {
  if (score >= 70) return '#67c23a'
  if (score >= 40) return '#e6a23c'
  return '#f56c6c'
}

function getScoreClass(item: any) {
  if (item.score === null || item.score === undefined) return ''
  if (item.score >= 70) return 'score-good'
  if (item.score >= 40) return 'score-medium'
  return 'score-bad'
}

function getTagType(item: any) {
  if (item.score === null || item.score === undefined) return 'info'
  if (item.score >= 70) return 'success'
  if (item.score >= 40) return 'warning'
  return 'danger'
}

async function handleMacroInsight() {
  insightLoading.value = true
  macroInsight.value = ''
  try {
    const res = await calendarApi.insight.analyzeMacro()
    macroInsight.value = res.data?.content || ''
    if (!macroInsight.value) {
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
.macro-view {
  padding: 16px 0;
}

.macro-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.update-time {
  color: #909399;
  font-size: 13px;
}

/* 评分区域 */
.score-section {
  margin-bottom: 20px;
}

.score-gauge {
  text-align: center;
  padding: 20px 0;
}

.gauge-value {
  font-size: 64px;
  font-weight: 800;
  line-height: 1;
}

.gauge-label {
  font-size: 20px;
  font-weight: 600;
  margin-top: 8px;
  color: #606266;
}

.score-details {
  padding: 12px 0;
}

.detail-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
  color: #303133;
}

.detail-item {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.detail-name {
  width: 100px;
  font-size: 13px;
  color: #606266;
  flex-shrink: 0;
}

.detail-score {
  width: 32px;
  text-align: right;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  flex-shrink: 0;
}

/* 预警 */
.alerts-section {
  margin-bottom: 20px;
}

/* 指标卡片 */
.indicator-cards {
  margin-top: 16px;
}

.indicator-card {
  margin-bottom: 16px;
  transition: transform 0.2s;
}

.indicator-card:hover {
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.card-title {
  font-size: 14px;
  color: #606266;
  font-weight: 500;
}

.card-value {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
  margin-bottom: 8px;
}

.card-unit {
  font-size: 14px;
  font-weight: 400;
  color: #909399;
  margin-left: 4px;
}

.card-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  margin-bottom: 8px;
}

.card-change { color: #909399; }
.card-change.positive { color: #67c23a; }
.card-change.negative { color: #f56c6c; }

.card-source {
  font-size: 11px;
  color: #c0c4cc;
}

.score-good .card-value { color: #67c23a; }
.score-medium .card-value { color: #e6a23c; }
.score-bad .card-value { color: #f56c6c; }

/* 二级市场 */
.market-actions {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.chart-section {
  margin-bottom: 16px;
}

.ai-section {
  padding: 8px 0;
}

.ai-section .el-button {
  margin-bottom: 16px;
}
</style>
