<template>
  <el-card shadow="hover">
    <div class="chart-title">库存周期象限图</div>
    <v-chart v-if="option" :option="option" :autoresize="true" style="height: 360px;" />
    <el-empty v-else description="暂无库存周期数据" :image-size="60" />
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import type { InventoryCycleMapPoint } from '@/types/calendar'

const props = defineProps<{
  data: InventoryCycleMapPoint[]
}>()

const option = computed(() => {
  if (!props.data?.length) return null

  // X轴: change_pct (近似PPI), Y轴: -turnover_rate (近似库存)
  const seriesData = props.data.map(d => ({
    value: [d.change_pct ?? 0, -(d.turnover_rate ?? 0)],
    name: d.industry_name,
    score: d.score,
    phase: d.phase,
  }))

  return {
    tooltip: {
      formatter: (params: any) => {
        const d = params.data
        return `${d.name}<br/>涨跌幅: ${d.value[0].toFixed(2)}%<br/>库存代理: ${d.value[1].toFixed(2)}<br/>阶段: ${d.phase}<br/>评分: ${d.score}`
      },
    },
    grid: { top: 20, bottom: 60, left: 60, right: 30 },
    xAxis: {
      type: 'value',
      name: '涨跌幅(近似PPI)',
      nameLocation: 'middle',
      nameGap: 30,
      splitLine: { show: true, lineStyle: { type: 'dashed' } },
    },
    yAxis: {
      type: 'value',
      name: '库存代理(-换手率)',
      nameLocation: 'middle',
      nameGap: 40,
      splitLine: { show: true, lineStyle: { type: 'dashed' } },
    },
    // 四象限标注
    graphic: [
      { type: 'text', left: '20%', top: '10%', style: { text: '主动补库\n(景气高峰)', fill: '#e6a23c', fontSize: 12 } },
      { type: 'text', right: '20%', top: '10%', style: { text: '被动去库\n(景气上行)', fill: '#67c23a', fontSize: 12 } },
      { type: 'text', left: '20%', bottom: '10%', style: { text: '被动补库\n(景气下行)', fill: '#909399', fontSize: 12 } },
      { type: 'text', right: '20%', bottom: '10%', style: { text: '主动去库\n(景气低谷)', fill: '#f56c6c', fontSize: 12 } },
    ],
    series: [{
      type: 'scatter',
      data: seriesData,
      symbolSize: (_val: number[], params: any) => Math.max(12, (params.data.score || 50) / 5),
      label: {
        show: true,
        formatter: (params: any) => params.data.name,
        position: 'right',
        fontSize: 10,
      },
      itemStyle: {
        color: (params: any) => {
          const s = params.data.score || 50
          if (s >= 70) return '#67c23a'
          if (s >= 50) return '#e6a23c'
          return '#f56c6c'
        },
      },
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
