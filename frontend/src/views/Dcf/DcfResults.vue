<template>
  <div class="dcf-results">
    <el-card shadow="hover" class="summary-card">
      <template #header>
        <div class="card-header">
          <span>估值结果 - {{ store.result?.stock_code }} {{ store.result?.stock_name }}</span>
          <el-tag :type="modelTagType">{{ modelLabel }}</el-tag>
        </div>
      </template>

      <!-- 4个摘要卡片 -->
      <el-row :gutter="16">
        <el-col :xs="12" :sm="6">
          <el-statistic title="每股内在价值" :value="store.result?.result?.intrinsic_value_per_share ?? 0" :precision="2" suffix="元" />
        </el-col>
        <el-col :xs="12" :sm="6">
          <el-statistic
            title="安全边际"
            :value="store.result?.result?.safety_margin ?? 0"
            :precision="2"
            suffix="%"
          >
            <template #prefix>
              <span :style="{ color: safetyColor }">
                {{ store.result?.result?.safety_margin && store.result.result.safety_margin > 0 ? '+' : '' }}
              </span>
            </template>
          </el-statistic>
          <div class="stat-sub">
            当前价: {{ store.result?.result?.current_price ?? '-' }}
          </div>
        </el-col>
        <el-col :xs="12" :sm="6">
          <el-statistic title="WACC" :value="store.result?.wacc_detail?.wacc ?? 0" :precision="4" />
        </el-col>
        <el-col :xs="12" :sm="6">
          <el-statistic title="每股FCF" :value="perShareFCF" :precision="4" suffix="元" />
        </el-col>
      </el-row>
    </el-card>

    <!-- 财务指标 + WACC明细 -->
    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :xs="24" :md="12">
        <el-card shadow="hover">
          <template #header>财务指标</template>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="金融资产">
              {{ formatNum(store.result?.financial_metrics?.financial_assets) }}
            </el-descriptions-item>
            <el-descriptions-item label="公司债务">
              {{ formatNum(store.result?.financial_metrics?.company_debt) }}
            </el-descriptions-item>
            <el-descriptions-item label="经营资产自由现金流">
              {{ formatNum(store.result?.financial_metrics?.operating_fcf) }}
            </el-descriptions-item>
            <el-descriptions-item label="实际税率">
              {{ formatPct(store.result?.financial_metrics?.effective_tax_rate) }}
            </el-descriptions-item>
            <el-descriptions-item label="少数股东比例">
              {{ formatPct(store.result?.financial_metrics?.minority_interest_ratio) }}
            </el-descriptions-item>
            <el-descriptions-item label="债务占比">
              {{ formatPct(store.result?.financial_metrics?.debt_ratio) }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
      <el-col :xs="24" :md="12">
        <el-card shadow="hover">
          <template #header>WACC 明细</template>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="WACC">
              {{ formatPct(store.result?.wacc_detail?.wacc) }}
            </el-descriptions-item>
            <el-descriptions-item label="债务资本成本率">
              {{ formatPct(store.result?.wacc_detail?.cost_of_debt) }}
            </el-descriptions-item>
            <el-descriptions-item label="股权资本成本率">
              {{ formatPct(store.result?.wacc_detail?.cost_of_equity) }}
            </el-descriptions-item>
            <el-descriptions-item label="债务权重 D/(D+E)">
              {{ formatPct(store.result?.wacc_detail?.debt_weight) }}
            </el-descriptions-item>
            <el-descriptions-item label="股权权重 E/(D+E)">
              {{ formatPct(store.result?.wacc_detail?.equity_weight) }}
            </el-descriptions-item>
            <el-descriptions-item label="实际所得税税率">
              {{ formatPct(store.result?.wacc_detail?.tax_rate) }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>

    <!-- 估值分解 -->
    <el-card shadow="hover" style="margin-top: 16px">
      <template #header>估值分解</template>
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="FCF 折现值">
          {{ formatNum(store.result?.result?.fcf_present_value) }}
        </el-descriptions-item>
        <el-descriptions-item label="净金融资产(金融资产-债务)">
          {{ formatNum(store.result?.result?.net_asset_value) }}
        </el-descriptions-item>
        <el-descriptions-item label="少数股东扣减">
          {{ formatNum(store.result?.result?.minority_deduction) }}
        </el-descriptions-item>
        <el-descriptions-item label="归属于上市公司股东价值">
          {{ formatNum(store.result?.result?.total_equity_value) }}
        </el-descriptions-item>
        <el-descriptions-item label="总股本">
          {{ formatNum(store.result?.result?.shares_outstanding) }} 股
        </el-descriptions-item>
        <el-descriptions-item label="每股内在价值">
          <span style="font-weight: bold; font-size: 16px; color: var(--el-color-primary)">
            {{ store.result?.result?.intrinsic_value_per_share?.toFixed(2) }} 元
          </span>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 图表区域 -->
    <el-row :gutter="16" style="margin-top: 16px">
      <!-- 预测FCF柱状图 -->
      <el-col :xs="24" :md="12">
        <el-card shadow="hover">
          <template #header>预测 FCF</template>
          <div ref="fcfChartRef" style="height: 320px"></div>
        </el-card>
      </el-col>
      <!-- 历史价格走势（含内在价值标线） -->
      <el-col :xs="24" :md="12">
        <el-card shadow="hover">
          <template #header>历史价格走势</template>
          <div ref="priceChartRef" style="height: 320px"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useDcfStore } from '@/stores/dcf'
import { DCF_MODEL_OPTIONS } from '@/types/dcf'

const store = useDcfStore()
const fcfChartRef = ref<HTMLElement>()
const priceChartRef = ref<HTMLElement>()

const modelLabel = computed(() => {
  const opt = DCF_MODEL_OPTIONS.find(o => o.value === store.result?.model)
  return opt?.label || store.result?.model || ''
})

const modelTagType = computed(() => {
  const map: Record<string, string> = {
    'zero-growth': 'info',
    'constant-growth': 'success',
    'two-stage': 'warning',
    'three-stage': 'danger',
  }
  return (map[store.result?.model || ''] || 'info') as any
})

const safetyColor = computed(() => {
  const margin = store.result?.result?.safety_margin
  if (margin === null || margin === undefined) return 'inherit'
  return margin >= 0 ? 'var(--el-color-success)' : 'var(--el-color-danger)'
})

const perShareFCF = computed(() => {
  if (!store.result) return 0
  const shares = store.result.result?.shares_outstanding || 0
  const fcf = store.result.result?.operating_fcf || 0
  return shares > 0 ? fcf / shares : 0
})

function formatNum(val: number | undefined | null): string {
  if (val === null || val === undefined) return '-'
  if (Math.abs(val) >= 1e8) return (val / 1e8).toFixed(2) + ' 亿'
  if (Math.abs(val) >= 1e4) return (val / 1e4).toFixed(2) + ' 万'
  return val.toFixed(2)
}

function formatPct(val: number | undefined | null): string {
  if (val === null || val === undefined) return '-'
  return (val * 100).toFixed(2) + '%'
}

// ECharts 图表渲染
async function renderCharts() {
  const { default: echarts } = await import('echarts')
  await nextTick()

  renderFCFChart(echarts)
  renderPriceChart(echarts)
}

function renderFCFChart(echarts: any) {
  if (!fcfChartRef.value || !store.result?.forecast_fcf?.length) return
  const chart = echarts.init(fcfChartRef.value)
  const data = store.result.forecast_fcf

  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: data.map(d => `第${d.year}年`),
    },
    yAxis: { type: 'value', name: 'FCF' },
    series: [
      {
        type: 'bar',
        data: data.map(d => ({
          value: d.fcf,
          itemStyle: {
            color: d.is_terminal ? '#E6A23C' : '#409EFF',
          },
        })),
        label: { show: true, position: 'top', formatter: '{c}' },
      },
    ],
  })
}

function renderPriceChart(echarts: any) {
  if (!priceChartRef.value || !store.result?.price_history?.length) return
  const chart = echarts.init(priceChartRef.value)
  const data = store.result.price_history
  const intrinsicValue = store.result.result?.intrinsic_value_per_share || 0

  // 取最近最多60条数据
  const sliced = data.length > 60 ? data.slice(-60) : data

  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['收盘价', '内在价值'] },
    xAxis: {
      type: 'category',
      data: sliced.map(d => d.date?.substring(0, 10) || ''),
      axisLabel: { rotate: 45 },
    },
    yAxis: { type: 'value', name: '价格' },
    series: [
      {
        name: '收盘价',
        type: 'line',
        data: sliced.map(d => d.price),
        smooth: true,
        lineStyle: { width: 1 },
      },
      {
        name: '内在价值',
        type: 'line',
        data: sliced.map(() => intrinsicValue),
        lineStyle: { type: 'dashed', color: '#F56C6C', width: 2 },
        symbol: 'none',
      },
    ],
  })
}

onMounted(() => {
  if (store.result) renderCharts()
})

watch(
  () => store.result,
  () => {
    if (store.result) renderCharts()
  }
)
</script>

<style lang="scss" scoped>
.dcf-results {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .stat-sub {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    margin-top: 4px;
  }
}
</style>
