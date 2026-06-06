<template>
  <el-card shadow="hover">
    <div class="chart-title">{{ industryName }} - 五维度评分</div>
    <v-chart v-if="option" :option="option" :autoresize="true" style="height: 320px;" />
    <el-empty v-else description="暂无评分数据" :image-size="60" />
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import type { IndustryProsperity } from '@/types/calendar'

const props = defineProps<{
  industryName: string
  data: IndustryProsperity | null
}>()

const option = computed(() => {
  if (!props.data) return null
  const d = props.data

  // 五维度数据
  const dims = d.five_dimensions || {}
  const indicators = [
    { name: '库存周期', max: dims['库存周期']?.max || 30 },
    { name: '盈利趋势', max: dims['盈利趋势']?.max || 20 },
    { name: '需求增速', max: dims['需求增速']?.max || 20 },
    { name: '资金流向', max: dims['资金流向']?.max || 15 },
    { name: '政策支持', max: dims['政策支持']?.max || 15 },
  ]
  const values = [
    dims['库存周期']?.score ?? d.inventory_score ?? 0,
    dims['盈利趋势']?.score ?? d.profit_score ?? 0,
    dims['需求增速']?.score ?? d.demand_score ?? 0,
    dims['资金流向']?.score ?? d.capital_score ?? 0,
    dims['政策支持']?.score ?? d.policy_score ?? 0,
  ]

  return {
    tooltip: {},
    radar: {
      indicator: indicators,
      shape: 'polygon',
      splitNumber: 5,
    },
    series: [{
      type: 'radar',
      data: [{
        value: values,
        name: props.industryName,
        areaStyle: { color: 'rgba(64,158,255,0.25)' },
        lineStyle: { color: '#409eff' },
        itemStyle: { color: '#409eff' },
      }],
    }],
  }
})
</script>

<style scoped>
.chart-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #303133;
}
</style>
