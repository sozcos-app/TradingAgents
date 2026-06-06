<template>
  <el-card shadow="hover">
    <div class="chart-title">涨跌家数对比</div>
    <v-chart v-if="option" :option="option" :autoresize="true" style="height: 280px;" />
    <el-empty v-else description="暂无涨跌数据" :image-size="60" />
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
  const upData = sorted.map(d => d.up_count ?? 0)
  const downData = sorted.map(d => d.down_count ?? 0)

  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['上涨', '下跌'], top: 0 },
    grid: { top: 30, bottom: 30, left: 50, right: 20 },
    xAxis: { type: 'category', data: dates },
    yAxis: { type: 'value' },
    series: [
      { name: '上涨', type: 'bar', stack: 'total', data: upData, itemStyle: { color: '#f56c6c' } },
      { name: '下跌', type: 'bar', stack: 'total', data: downData, itemStyle: { color: '#67c23a' } },
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
