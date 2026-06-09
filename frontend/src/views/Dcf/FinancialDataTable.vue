<template>
  <div class="financial-data-table">
    <!-- 股票代码输入 + 获取按钮 -->
    <el-row :gutter="12" align="middle">
      <el-col :span="8">
        <el-input
          v-model="stockCode"
          placeholder="输入股票代码，如 002138"
          clearable
          @keyup.enter="handleFetch"
          @update:model-value="(val: string) => emit('update:modelValue', val)"
        />
      </el-col>
      <el-col :span="4">
        <el-input-number v-model="quarters" :min="2" :max="20" :step="1" controls-position="right" style="width: 100%" />
      </el-col>
      <el-col :span="4">
        <el-button type="primary" :loading="store.fetchLoading" @click="handleFetch">
          自动获取
        </el-button>
      </el-col>
      <el-col :span="8" v-if="store.fetchedData?.stock_name">
        <el-tag type="success">{{ store.fetchedData.stock_name }}</el-tag>
        <span v-if="store.fetchedData.current_price" style="margin-left: 8px; color: var(--el-color-primary)">
          当前价: {{ store.fetchedData.current_price?.toFixed(2) }} 元
        </span>
        <span v-if="store.fetchedData.total_market_cap" style="margin-left: 8px; color: var(--el-text-color-secondary)">
          总市值: {{ formatMarketCap(store.fetchedData.total_market_cap) }}
        </span>
      </el-col>
    </el-row>

    <!-- 无数据提示 -->
    <el-empty v-if="!store.fetchedData" description="输入股票代码后点击「自动获取」" style="margin-top: 20px" />

    <!-- 数据表格区域 -->
    <template v-if="store.fetchedData && store.fetchedData.periods.length">
      <!-- 报告期 Tabs -->
      <el-tabs v-model="activePeriod" type="border-card" style="margin-top: 16px">
        <el-tab-pane
          v-for="(period, pIdx) in store.fetchedData.periods"
          :key="period.report_date"
          :label="formatReportDate(period.report_date)"
          :name="String(pIdx)"
        >
          <!-- 按分类分组显示的可编辑表格 -->
          <template v-for="category in categories" :key="category.key">
            <div class="category-header">{{ category.label }}</div>
            <el-table :data="getItemsByCategory(period, category.key)" border size="small" style="margin-bottom: 12px">
              <el-table-column prop="display_name" label="科目名称" min-width="260">
                <template #default="{ row }">
                  <span>{{ cleanDisplayName(row.display_name) }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="value" label="金额（元）" width="220" align="right">
                <template #default="{ row, $index }">
                  <el-input-number
                    :model-value="row.value"
                    @update:model-value="(val: number | undefined) => updateItemValue(pIdx, category.key, $index, val ?? 0)"
                    :precision="2"
                    :controls="false"
                    size="small"
                    style="width: 100%"
                  />
                </template>
              </el-table-column>
            </el-table>
          </template>

          <!-- 计算后的 7 项指标 -->
          <div class="category-header" style="margin-top: 8px">计算指标</div>
          <el-descriptions v-if="period.metrics" :column="2" border size="small">
            <el-descriptions-item label="金融资产合计">
              {{ formatNum(period.metrics.financial_assets) }}
            </el-descriptions-item>
            <el-descriptions-item label="公司债务合计">
              {{ formatNum(period.metrics.company_debt) }}
            </el-descriptions-item>
            <el-descriptions-item label="经营资产自由现金流">
              {{ formatNum(period.metrics.operating_fcf) }}
            </el-descriptions-item>
            <el-descriptions-item label="实际所得税税率">
              {{ formatPct(period.metrics.effective_tax_rate) }}
            </el-descriptions-item>
            <el-descriptions-item label="少数股东权益比例">
              {{ formatPct(period.metrics.minority_interest_ratio) }}
            </el-descriptions-item>
            <el-descriptions-item label="债务占比">
              {{ formatPct(period.metrics.debt_ratio) }}
            </el-descriptions-item>
            <el-descriptions-item label="债务资本成本总额">
              {{ formatNum(period.metrics.debt_capital_cost) }}
            </el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>
      </el-tabs>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useDcfStore } from '@/stores/dcf'
import type { PeriodFinancialData, RawFinancialItem, FinancialMetrics } from '@/types/dcf'

const store = useDcfStore()

const props = defineProps<{
  modelValue?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const stockCode = ref(props.modelValue || '')
const quarters = ref(8)
const activePeriod = ref('0')

const categories = [
  { key: 'balance_sheet', label: '资产负债表' },
  { key: 'profit_sheet', label: '利润表' },
  { key: 'cash_flow', label: '现金流量表' },
]

function getItemsByCategory(period: PeriodFinancialData, category: string): RawFinancialItem[] {
  return period.raw_items.filter(item => item.category === category)
}

function cleanDisplayName(name: string): string {
  return name.replace(/^[BRC]_/, '')
}

function formatReportDate(date: string): string {
  if (!date) return ''
  return date.substring(0, 10)
}

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

function formatMarketCap(val: number | null | undefined): string {
  if (!val) return '-'
  if (val >= 1e12) return (val / 1e12).toFixed(2) + ' 万亿'
  if (val >= 1e8) return (val / 1e8).toFixed(2) + ' 亿'
  return val.toFixed(0)
}

/** 前端本地重新计算 7 项指标 */
function recalcMetrics(rawItems: RawFinancialItem[]): FinancialMetrics {
  const itemMap = new Map(rawItems.map(i => [i.dcf_column, i.value]))

  const getVal = (col: string): number => itemMap.get(col) ?? 0
  const safeF = (v: number): number => (isFinite(v) ? v : 0)

  // 金融资产（17项求和）
  const faCols = [
    'B_货币资金', 'B_交易性金融资产', 'B_衍生金融资产',
    'B_应收票据及应收账款', 'B_应收票据', 'B_应收账款',
    'B_应收款项融资', 'B_应收利息', 'B_应收股利',
    'B_其他应收款', 'B_买入返售金融资产', 'B_发放贷款及垫款',
    'B_可供出售金融资产', 'B_持有至到期投资', 'B_长期应收款',
    'B_长期股权投资', 'B_投资性房地产',
  ]
  const financial_assets = faCols.reduce((s, c) => s + getVal(c), 0)

  // 债务（9项求和）
  const debtCols = [
    'B_短期借款', 'B_交易性金融负债', 'B_应付利息',
    'B_应付短期债券', 'B_一年内到期的非流动负债',
    'B_长期借款', 'B_应付债券', 'B_租赁负债', 'B_长期应付款(合计)',
  ]
  const company_debt = debtCols.reduce((s, c) => s + getVal(c), 0)

  // 经营资产自由现金流
  const operating_fcf =
    getVal('C_经营活动产生的现金流量净额')
    - getVal('C_固定资产折旧、油气资产折耗、生产性物资折旧')
    - getVal('C_无形资产摊销')
    - getVal('C_长期待摊费用摊销')
    - getVal('C_处置固定资产、无形资产和其他长期资产的损失')

  // 实际税率
  const totalProfit = getVal('R_四、利润总额')
  const incomeTax = getVal('R_减：所得税费用')
  const effective_tax_rate = totalProfit !== 0
    ? safeF(1 - ((totalProfit - incomeTax) / totalProfit))
    : 0

  // 少数股东比例
  const totalEquity = getVal('B_所有者权益(或股东权益)合计')
  const minority = getVal('B_少数股东权益')
  const minority_interest_ratio = totalEquity !== 0 ? safeF(minority / totalEquity) : 0

  // 债务占比
  const debt_ratio = (company_debt + totalEquity) !== 0
    ? safeF(company_debt / (company_debt + totalEquity))
    : 0

  // 债务资本成本
  const debt_capital_cost = getVal('R_财务费用') + getVal('R_汇兑收益')

  return {
    financial_assets,
    company_debt,
    operating_fcf,
    effective_tax_rate,
    minority_interest_ratio,
    debt_ratio,
    debt_capital_cost,
  }
}

function updateItemValue(periodIdx: number, category: string, itemIdx: number, value: number) {
  if (!store.fetchedData) return
  const period = store.fetchedData.periods[periodIdx]
  if (!period) return

  const catItems = period.raw_items.filter(i => i.category === category)
  const item = catItems[itemIdx]
  if (!item) return

  item.value = value

  // 重新计算该期指标
  period.metrics = recalcMetrics(period.raw_items)
}

async function handleFetch() {
  if (!stockCode.value.trim()) {
    ElMessage.warning('请输入股票代码')
    return
  }
  try {
    const code = stockCode.value.trim()
    await store.fetchFinancialData(code, quarters.value)
    activePeriod.value = '0'
    emit('update:modelValue', code)
    ElMessage.success('财务数据获取成功')
  } catch {
    ElMessage.error(store.error || '获取财务数据失败')
  }
}
</script>

<style lang="scss" scoped>
.financial-data-table {
  .category-header {
    font-weight: 600;
    font-size: 13px;
    color: var(--el-text-color-primary);
    padding: 8px 0 4px;
    border-bottom: 1px solid var(--el-border-color-lighter);
    margin-bottom: 8px;
  }
}
</style>
