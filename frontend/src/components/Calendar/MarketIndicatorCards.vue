<template>
  <div class="market-indicator-cards">
    <el-row :gutter="12">
      <!-- 成交额 -->
      <el-col :xs="12" :sm="8" :md="4">
        <el-card shadow="hover" class="mi-card">
          <div class="mi-label">全市场成交额</div>
          <div class="mi-value">{{ formatAmount(volume) }}</div>
          <div class="mi-sub">亿元</div>
        </el-card>
      </el-col>
      <!-- 涨跌家数 -->
      <el-col :xs="12" :sm="8" :md="4">
        <el-card shadow="hover" class="mi-card">
          <div class="mi-label">涨跌家数</div>
          <div class="mi-value">
            <span class="up">{{ overview.advance_decline?.up_count ?? '-' }}</span>
            /
            <span class="down">{{ overview.advance_decline?.down_count ?? '-' }}</span>
          </div>
          <div class="mi-sub">
            <span class="up">涨</span> / <span class="down">跌</span>
          </div>
        </el-card>
      </el-col>
      <!-- 涨停/跌停 -->
      <el-col :xs="12" :sm="8" :md="4">
        <el-card shadow="hover" class="mi-card">
          <div class="mi-label">涨停 / 跌停</div>
          <div class="mi-value">
            <span class="up">{{ overview.limit_stats?.limit_up_count ?? '-' }}</span>
            /
            <span class="down">{{ overview.limit_stats?.limit_down_count ?? '-' }}</span>
          </div>
          <div class="mi-sub">涨停 / 跌停</div>
        </el-card>
      </el-col>
      <!-- 融资余额 -->
      <el-col :xs="12" :sm="8" :md="4">
        <el-card shadow="hover" class="mi-card">
          <div class="mi-label">融资余额</div>
          <div class="mi-value">{{ formatAmount(margin) }}</div>
          <div class="mi-sub">亿元</div>
        </el-card>
      </el-col>
      <!-- 换手率 -->
      <el-col :xs="12" :sm="8" :md="4">
        <el-card shadow="hover" class="mi-card">
          <div class="mi-label">平均换手率</div>
          <div class="mi-value">{{ overview.turnover?.avg_turnover_rate?.toFixed(2) ?? '-' }}%</div>
          <div class="mi-sub">全市场</div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { MarketIndicatorOverview } from '@/types/calendar'

const props = defineProps<{
  overview: MarketIndicatorOverview
}>()

const volume = computed(() => props.overview.volume?.total_amount ?? 0)
const margin = computed(() => props.overview.margin_trading?.margin_balance ?? 0)

function formatAmount(val: number): string {
  if (!val) return '-'
  return (val / 1e8).toFixed(0)
}
</script>

<style scoped>
.market-indicator-cards { margin-bottom: 16px; }

.mi-card {
  text-align: center;
  padding: 4px 0;
  min-height: 90px;
}

.mi-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}

.mi-value {
  font-size: 22px;
  font-weight: 700;
  color: #303133;
  line-height: 1.2;
}

.mi-sub {
  font-size: 11px;
  color: #c0c4cc;
  margin-top: 4px;
}

.up { color: #f56c6c; }
.down { color: #67c23a; }
</style>
