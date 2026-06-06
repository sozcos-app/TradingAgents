<template>
  <el-card shadow="hover">
    <div class="chart-title">板块热度排名</div>
    <v-chart v-if="option" :option="option" :autoresize="true" style="height: 360px;" />
    <el-empty v-else description="暂无板块数据" :image-size="60" />
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
  // 取涨幅前20 和 跌幅前10
  const sorted = [...props.data].sort((a, b) => (b.change_pct ?? 0) - (a.change_pct ?? 0))
  const top20 = sorted.slice(0, 20)
  const bottom10 = sorted.slice(-10)
  const display = [...top20, ...bottom10]

  const treemapData = display.map(s => ({
    name: s.sector_name || '',
    value: Math.abs(s.change_pct ?? 0) * 100,
    change: s.change_pct ?? 0,
    itemStyle: {
      color: (s.change_pct ?? 0) >= 0
        ? `rgba(245, 108, 108, ${Math.min(1, Math.abs(s.change_pct ?? 0) / 5)})`
        : `rgba(103, 194, 58, ${Math.min(1, Math.abs(s.change_pct ?? 0) / 5)})`,
    },
  }))

  return {
    tooltip: {
      formatter: (info: any) => `${info.name}<br/>涨跌幅: ${display.find(s => s.sector_name === info.name)?.change_pct?.toFixed(2) ?? '-'}%`,
    },
    series: [{
      type: 'treemap',
      data: treemapData,
      roam: false,
      nodeClick: false,
      breadcrumb: { show: false },
      label: { show: true, formatter: '{b}', fontSize: 11 },
      itemStyle: { borderColor: '#fff', borderWidth: 2, gapWidth: 2 },
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
