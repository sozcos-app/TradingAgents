<template>
  <el-card shadow="hover">
    <div class="chart-title">全市场成交额趋势</div>
    <v-chart v-if="option" :option="option" :autoresize="true" style="height: 280px;" />
    <el-empty v-else description="暂无成交额数据" :image-size="60" />
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import type { MarketIndicator } from '@/types/calendar'

const props = defineProps<{
  data: MarketIndicator[]
}>()

const option = computed(() => {
  if (!props.data?.length) return null
  const sorted = [...props.data].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
  const dates = sorted.map(d => d.date?.slice(0, 10) || '')
  const amounts = sorted.map(d => {
    const val = d.total_amount ?? 0
    return +(val / 1e8).toFixed(0)
  })

  return {
    tooltip: { trigger: 'axis', formatter: (params: any) => `${params[0].axisValue}<br/>成交额: ${params[0].value} 亿` },
    grid: { top: 20, bottom: 30, left: 60, right: 20 },
    xAxis: { type: 'category', data: dates },
    yAxis: { type: 'value', name: '亿元', axisLabel: { formatter: '{value}' } },
    series: [{
      type: 'bar',
      data: amounts,
      itemStyle: { color: '#409eff' },
      areaStyle: { color: 'rgba(64,158,255,0.15)' },
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
