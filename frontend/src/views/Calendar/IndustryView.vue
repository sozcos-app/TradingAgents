<template>
  <div class="industry-view">
    <!-- 顶部操作栏 -->
    <div class="industry-header">
      <el-button type="primary" :loading="loading" @click="handleRefresh">
        快速评分
      </el-button>
      <el-button type="success" :loading="loading" @click="handleRefreshFull">
        全维度评分
      </el-button>
      <span class="update-time" v-if="ranking.length && ranking[0].date">
        评分时间: {{ ranking[0].date?.slice(0, 19).replace('T', ' ') }}
      </span>
    </div>

    <!-- 前5名概览卡片 -->
    <el-row :gutter="12" class="top-cards" v-if="topIndustries.length">
      <el-col :xs="12" :sm="8" :md="4" v-for="(item, idx) in topIndustries" :key="item.industry_name">
        <el-card shadow="hover" class="top-card" :class="`rank-${idx + 1}`">
          <div class="top-rank">#{{ idx + 1 }}</div>
          <div class="top-name">{{ item.industry_name }}</div>
          <div class="top-score" :style="{ color: getScoreColor(item.score) }">{{ item.score }}分</div>
          <el-tag :type="getSuggestionType(item.suggestion)" size="small">{{ item.suggestion }}</el-tag>
        </el-card>
      </el-col>
    </el-row>

    <!-- 行业景气排名表格 -->
    <div class="section-title">行业景气排名</div>
    <IndustryRankingTable
      :ranking="ranking"
      @show-detail="showDetail"
    />

    <el-empty v-if="!loading && ranking.length === 0" description="暂无行业数据，请点击评分按钮" />

    <!-- 库存周期象限图 -->
    <div v-if="store.inventoryCycleMap.length" class="section-block">
      <InventoryCycleChart :data="store.inventoryCycleMap" />
    </div>

    <!-- 行业详情弹窗 -->
    <el-dialog v-model="showDetailDialog" :title="detailIndustry + ' - 行业详情'" width="700px">
      <div v-if="detailData">
        <!-- 雷达图 -->
        <IndustryRadar :industry-name="detailIndustry" :data="detailData" />

        <!-- 基本信息和五维度明细 -->
        <el-descriptions :column="2" border style="margin-top: 16px;">
          <el-descriptions-item label="景气评分">
            <span :style="{ color: getScoreColor(detailData.score), fontWeight: 'bold' }">{{ detailData.score }}分</span>
          </el-descriptions-item>
          <el-descriptions-item label="配置建议">
            <el-tag :type="getSuggestionType(detailData.suggestion)">{{ detailData.suggestion }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="库存周期">
            {{ detailData.inventory_cycle || '-' }}
            <span v-if="detailData.inventory_score"> ({{ detailData.inventory_score }}/30)</span>
          </el-descriptions-item>
          <el-descriptions-item label="盈利趋势">
            {{ detailData.profit_trend || '-' }}
            <span v-if="detailData.profit_score"> ({{ detailData.profit_score }}/20)</span>
          </el-descriptions-item>
          <el-descriptions-item label="需求增速">
            {{ detailData.demand_growth || '-' }}
            <span v-if="detailData.demand_score"> ({{ detailData.demand_score }}/20)</span>
          </el-descriptions-item>
          <el-descriptions-item label="资金流向">
            {{ detailData.capital_flow || '-' }}
            <span v-if="detailData.capital_score"> ({{ detailData.capital_score }}/15)</span>
          </el-descriptions-item>
          <el-descriptions-item label="政策支持">
            {{ detailData.policy_support || '-' }}
            <span v-if="detailData.policy_score"> ({{ detailData.policy_score }}/15)</span>
          </el-descriptions-item>
          <el-descriptions-item label="涨跌幅">
            <span :style="{ color: getChangeColor(detailData.change_pct) }">
              {{ detailData.change_pct?.toFixed(2) ?? '-' }}%
            </span>
          </el-descriptions-item>
        </el-descriptions>

        <!-- 催化剂 -->
        <div v-if="detailData.catalysts?.length" style="margin-top: 12px;">
          <div class="catalysts-title">核心催化剂</div>
          <el-tag v-for="(c, idx) in detailData.catalysts" :key="idx" type="info" style="margin-right: 6px; margin-bottom: 4px;">
            {{ c }}
          </el-tag>
        </div>

        <!-- AI 分析 -->
        <div style="margin-top: 16px;">
          <el-button type="primary" :loading="insightLoading" @click="handleIndustryInsight">
            AI 深度分析
          </el-button>
          <AiInsightCard
            v-if="industryInsight"
            :content="industryInsight"
            type="industry"
          />
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useCalendarStore } from '@/stores/calendar'
import { calendarApi } from '@/api/calendar'
import { ElMessage } from 'element-plus'
import type { IndustryProsperity } from '@/types/calendar'
import IndustryRankingTable from '@/components/Calendar/IndustryRankingTable.vue'
import IndustryRadar from '@/components/Calendar/IndustryRadar.vue'
import InventoryCycleChart from '@/components/Calendar/InventoryCycleChart.vue'
import AiInsightCard from '@/components/Calendar/AiInsightCard.vue'

const store = useCalendarStore()
const loading = ref(false)
const ranking = ref<IndustryProsperity[]>([])
const showDetailDialog = ref(false)
const detailIndustry = ref('')
const detailData = ref<IndustryProsperity | null>(null)
const industryInsight = ref('')
const insightLoading = ref(false)

const topIndustries = computed(() => ranking.value.slice(0, 5))

onMounted(() => {
  loadRanking()
  store.fetchInventoryCycleMap()
})

async function loadRanking() {
  loading.value = true
  try {
    await store.fetchIndustryRanking()
    ranking.value = store.industryRanking
  } finally {
    loading.value = false
  }
}

async function handleRefresh() {
  loading.value = true
  try {
    await calendarApi.industry.refresh()
    ElMessage.success('行业快速评分完成')
    await loadRanking()
    await store.fetchInventoryCycleMap()
  } catch (e: any) {
    ElMessage.error(e?.message || '刷新失败')
  } finally {
    loading.value = false
  }
}

async function handleRefreshFull() {
  loading.value = true
  try {
    await calendarApi.industry.refreshFull()
    ElMessage.success('全维度行业评分完成')
    await loadRanking()
    await store.fetchInventoryCycleMap()
  } catch (e: any) {
    ElMessage.error(e?.message || '刷新失败')
  } finally {
    loading.value = false
  }
}

async function showDetail(name: string) {
  detailIndustry.value = name
  try {
    const res = await calendarApi.industry.getDetail(name)
    detailData.value = res.data
    showDetailDialog.value = true
  } catch (e: any) {
    ElMessage.error('获取详情失败')
  }
}

function getScoreColor(score: number) {
  if (score >= 70) return '#67c23a'
  if (score >= 50) return '#e6a23c'
  return '#f56c6c'
}

function getSuggestionType(s: string) {
  if (s === '超配') return 'success'
  if (s === '标配') return 'warning'
  return 'danger'
}

function getChangeColor(val?: number) {
  if (!val) return '#909399'
  return val > 0 ? '#f56c6c' : val < 0 ? '#67c23a' : '#909399'
}

async function handleIndustryInsight() {
  if (!detailIndustry.value) return
  insightLoading.value = true
  industryInsight.value = ''
  try {
    const res = await calendarApi.insight.analyzeIndustry(detailIndustry.value)
    industryInsight.value = res.data?.content || ''
    if (!industryInsight.value) {
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
.industry-view {
  padding: 16px 0;
}

.industry-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.update-time {
  color: #909399;
  font-size: 13px;
}

/* 前5名卡片 */
.top-cards {
  margin-bottom: 20px;
}

.top-card {
  text-align: center;
  padding: 4px 0;
  min-height: 100px;
  position: relative;
}

.top-rank {
  font-size: 12px;
  font-weight: 700;
  color: #909399;
  margin-bottom: 4px;
}

.rank-1 .top-rank { color: #f7ba2a; }
.rank-2 .top-rank { color: #c0c4cc; }
.rank-3 .top-rank { color: #cd7f32; }

.top-name {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.top-score {
  font-size: 28px;
  font-weight: 800;
  line-height: 1.2;
  margin-bottom: 4px;
}

/* 区域标题 */
.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 12px;
}

.section-block {
  margin-top: 20px;
}

/* 催化剂 */
.catalysts-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}
</style>
