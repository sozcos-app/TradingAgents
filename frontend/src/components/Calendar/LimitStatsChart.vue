<template>
  <el-card shadow="hover">
    <div class="chart-title">涨停/跌停趋势</div>
    <v-chart v-if="option" :option="option" :autoresize="true" style="height: 280px;" />
    <el-empty v-else description="暂无涨停跌停数据" :image-size="60" />
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
  const limitUp = sorted.map(d => d.limit_up_count ?? 0)
  const limitDown = sorted.map(d => d.limit_down_count ?? 0)

  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['涨停', '跌停'], top: 0 },
    grid: { top: 30, bottom: 30, left: 50, right: 20 },
    xAxis: { type: 'category', data: dates },
    yAxis: { type: 'value' },
    series: [
      { name: '涨停', type: 'line', data: limitUp, smooth: true, itemStyle: { color: '#f56c6c' }, areaStyle: { color: 'rgba(245,108,108,0.15)' } },
      { name: '跌停', type: 'line', data: limitDown, smooth: true, itemStyle: { color: '#67c23a' }, areaStyle: { color: 'rgba(103,194,58,0.15)' } },
    ],
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
