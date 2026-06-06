/**
 * 交易日历 - Pinia Store
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { calendarApi } from '@/api/calendar'
import type {
  MacroIndicator,
  MacroScore,
  IndustryProsperity,
  StockHealthCheck,
  MarketEvent,
  MarketIndicatorOverview,
  DivergenceSignal,
  InventoryCycleMapPoint,
} from '@/types/calendar'

export const useCalendarStore = defineStore('calendar', () => {
  // ============ State ============
  const loading = ref(false)
  const activeTab = ref('macro')

  // 宏观
  const macroIndicators = ref<MacroIndicator[]>([])
  const macroScore = ref<MacroScore | null>(null)

  // 行业
  const industryRanking = ref<IndustryProsperity[]>([])
  const inventoryCycleMap = ref<InventoryCycleMapPoint[]>([])

  // 个股
  const stockReport = ref<StockHealthCheck | null>(null)

  // 事件
  const events = ref<MarketEvent[]>([])
  const eventsTotal = ref(0)

  // 二级市场指标
  const marketIndicatorOverview = ref<MarketIndicatorOverview | null>(null)
  const divergenceSignal = ref<DivergenceSignal | null>(null)

  // ============ Getters ============
  const macroLevel = computed(() => macroScore.value?.level || '暂无评分')
  const topIndustries = computed(() => industryRanking.value.slice(0, 5))

  // ============ Actions ============
  async function fetchMacroIndicators() {
    loading.value = true
    try {
      const res = await calendarApi.macro.getIndicators()
      macroIndicators.value = res.data || []
    } finally {
      loading.value = false
    }
  }

  async function triggerMacroScore() {
    loading.value = true
    try {
      const res = await calendarApi.macro.triggerScore()
      macroScore.value = res.data
    } finally {
      loading.value = false
    }
  }

  async function fetchLatestScore() {
    try {
      const res = await calendarApi.macro.getLatestScore()
      macroScore.value = res.data
    } catch {
      macroScore.value = null
    }
  }

  async function fetchIndustryRanking() {
    loading.value = true
    try {
      const res = await calendarApi.industry.getRanking()
      industryRanking.value = res.data || []
    } finally {
      loading.value = false
    }
  }

  async function fetchInventoryCycleMap() {
    try {
      const res = await calendarApi.industry.getInventoryCycleMap()
      inventoryCycleMap.value = res.data || []
    } catch {
      inventoryCycleMap.value = []
    }
  }

  async function fetchEvents(params?: Record<string, any>) {
    loading.value = true
    try {
      const res = await calendarApi.events.list(params)
      events.value = res.data?.items || []
      eventsTotal.value = res.data?.total || 0
    } finally {
      loading.value = false
    }
  }

  async function checkStock(tsCode: string) {
    loading.value = true
    try {
      const res = await calendarApi.stockHealth.check(tsCode)
      stockReport.value = res.data
    } finally {
      loading.value = false
    }
  }

  async function fetchMarketIndicators() {
    loading.value = true
    try {
      const res = await calendarApi.marketIndicator.getOverview()
      marketIndicatorOverview.value = res.data || null
    } finally {
      loading.value = false
    }
  }

  async function detectDivergence() {
    loading.value = true
    try {
      const res = await calendarApi.marketIndicator.detectLieOpportunity()
      divergenceSignal.value = res.data
    } finally {
      loading.value = false
    }
  }

  async function fetchDivergence() {
    try {
      const res = await calendarApi.marketIndicator.getDivergence()
      divergenceSignal.value = res.data || null
    } catch {
      divergenceSignal.value = null
    }
  }

  return {
    loading,
    activeTab,
    macroIndicators,
    macroScore,
    industryRanking,
    inventoryCycleMap,
    stockReport,
    events,
    eventsTotal,
    marketIndicatorOverview,
    divergenceSignal,
    macroLevel,
    topIndustries,
    fetchMacroIndicators,
    triggerMacroScore,
    fetchLatestScore,
    fetchIndustryRanking,
    fetchInventoryCycleMap,
    fetchEvents,
    checkStock,
    fetchMarketIndicators,
    detectDivergence,
    fetchDivergence,
  }
})
