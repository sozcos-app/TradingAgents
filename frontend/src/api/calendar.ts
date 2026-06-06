/**
 * 交易日历 - API 接口
 */

import { ApiClient } from './request'
import type {
  MacroIndicator,
  MacroScore,
  IndustryProsperity,
  StockHealthCheck,
  MarketEvent,
  EventType,
  PaginatedResponse,
  MarketIndicatorOverview,
  MarketIndicator,
  DivergenceSignal,
  InventoryCycleMapPoint,
  AiInsight,
} from '@/types/calendar'

export const calendarApi = {
  // ============ 宏观感知 ============
  macro: {
    /** 获取宏观指标最新值 */
    getIndicators: () =>
      ApiClient.get<MacroIndicator[]>('/api/calendar/macro/indicators'),

    /** 获取单个指标历史 */
    getIndicatorHistory: (name: string, params?: { start_date?: string; end_date?: string; page?: number; page_size?: number }) =>
      ApiClient.get<PaginatedResponse<MacroIndicator>>(`/api/calendar/macro/indicators/${name}`, params),

    /** 手动触发数据采集 */
    fetch: (indicators?: string[]) =>
      ApiClient.post('/api/calendar/macro/fetch', { indicators }),

    /** 触发评分计算 */
    triggerScore: () =>
      ApiClient.post('/api/calendar/macro/score'),

    /** 获取最新评分 */
    getLatestScore: () =>
      ApiClient.get<MacroScore>('/api/calendar/macro/score/latest'),

    /** 获取评分历史 */
    getScoreHistory: (params?: { start_date?: string; end_date?: string }) =>
      ApiClient.get<MacroScore[]>('/api/calendar/macro/score/history', params),
  },

  // ============ 行业景气 ============
  industry: {
    /** 获取行业排名 */
    getRanking: () =>
      ApiClient.get<IndustryProsperity[]>('/api/calendar/industry/ranking'),

    /** 获取单行业详情 */
    getDetail: (name: string) =>
      ApiClient.get<IndustryProsperity>(`/api/calendar/industry/${encodeURIComponent(name)}/detail`),

    /** 触发行业评分 */
    triggerScore: (name: string) =>
      ApiClient.post(`/api/calendar/industry/${encodeURIComponent(name)}/score`),

    /** 刷新全行业数据并评分 */
    refresh: () =>
      ApiClient.post('/api/calendar/industry/refresh'),

    /** 全维度采集并完整评分 */
    refreshFull: () =>
      ApiClient.post('/api/calendar/industry/refresh-full'),

    /** 获取单行业评分历史 */
    getHistory: (name: string, params?: { start_date?: string; end_date?: string }) =>
      ApiClient.get<IndustryProsperity[]>(`/api/calendar/industry/${encodeURIComponent(name)}/history`, params),

    /** 获取库存周期象限图数据 */
    getInventoryCycleMap: () =>
      ApiClient.get<InventoryCycleMapPoint[]>('/api/calendar/industry/inventory-cycle-map'),
  },

  // ============ 个股体检 ============
  stockHealth: {
    /** 触发个股体检 */
    check: (tsCode: string) =>
      ApiClient.post<StockHealthCheck>('/api/calendar/stock-health/check', { ts_code: tsCode }),

    /** 获取体检报告 */
    getReport: (tsCode: string) =>
      ApiClient.get<StockHealthCheck>(`/api/calendar/stock-health/${tsCode}`),

    /** 获取预警 */
    getAlerts: (tsCode: string) =>
      ApiClient.get<Record<string, any>[]>(`/api/calendar/stock-health/${tsCode}/alerts`),

    /** 获取体检历史 */
    getHistory: (tsCode: string, params?: { page?: number; page_size?: number }) =>
      ApiClient.get<{ total: number; items: StockHealthCheck[] }>('/api/calendar/stock-health/history', { ts_code: tsCode, ...params }),
  },

  // ============ 市场事件 ============
  events: {
    /** 查询事件列表 */
    list: (params?: {
      start_date?: string
      end_date?: string
      event_type?: string
      impact_direction?: string
      keyword?: string
      page?: number
      page_size?: number
    }) => ApiClient.get<PaginatedResponse<MarketEvent>>('/api/calendar/events', params),

    /** 获取即将到来事件 */
    getUpcoming: (days?: number) =>
      ApiClient.get<MarketEvent[]>('/api/calendar/events/upcoming', { days }),

    /** 获取事件详情 */
    getDetail: (id: string) =>
      ApiClient.get<MarketEvent>(`/api/calendar/events/${id}`),

    /** 创建事件 */
    create: (data: Partial<MarketEvent>) =>
      ApiClient.post<{ id: string }>('/api/calendar/events', data),

    /** 更新事件 */
    update: (id: string, data: Partial<MarketEvent>) =>
      ApiClient.put(`/api/calendar/events/${id}`, data),

    /** 删除事件 */
    delete: (id: string) =>
      ApiClient.delete(`/api/calendar/events/${id}`),

    /** 获取事件类型字典 */
    getTypes: () =>
      ApiClient.get<EventType[]>('/api/calendar/events/types'),

    /** 获取交易日列表 */
    getTradeDays: (start_date: string, end_date: string) =>
      ApiClient.get<string[]>('/api/calendar/trade-days', { start_date, end_date }),

    /** 手动触发事件采集 */
    fetchEvents: (start_date?: string, end_date?: string) =>
      ApiClient.post('/api/calendar/events/fetch', { start_date, end_date }),
  },

  // ============ 二级市场指标 ============
  marketIndicator: {
    /** 获取二级市场指标概览 */
    getOverview: () =>
      ApiClient.get<MarketIndicatorOverview>('/api/calendar/macro/market-indicators'),

    /** 获取历史数据 */
    getHistory: (params?: {
      indicator_type?: string
      start_date?: string
      end_date?: string
      page?: number
      page_size?: number
    }) => ApiClient.get<PaginatedResponse<MarketIndicator>>('/api/calendar/macro/market-indicators/history', params),

    /** 获取最新背离信号 */
    getDivergence: () =>
      ApiClient.get<DivergenceSignal>('/api/calendar/macro/divergence'),

    /** 执行谎言/机会检测 */
    detectLieOpportunity: () =>
      ApiClient.get<DivergenceSignal>('/api/calendar/macro/lie-opportunity'),

    /** 手动采集二级市场指标 */
    fetch: (types?: string[]) =>
      ApiClient.post('/api/calendar/macro/market-indicators/fetch', { types }),
  },

  // ============ AI 洞察分析 ============
  insight: {
    /** 宏观谎言/机会分析 */
    analyzeMacro: () =>
      ApiClient.post<{ content: string; type: string; ref_id: string }>('/api/calendar/macro/insight'),

    /** 行业异常分析 */
    analyzeIndustry: (name: string) =>
      ApiClient.post<{ content: string; type: string; ref_id: string }>(`/api/calendar/industry/${encodeURIComponent(name)}/insight`),

    /** 个股风险分析 */
    analyzeStock: (tsCode: string) =>
      ApiClient.post<{ content: string; type: string; ref_id: string }>(`/api/calendar/stock-health/${tsCode}/insight`),

    /** 事件影响分析 */
    analyzeEvent: (eventId: string) =>
      ApiClient.post<{ content: string; type: string; ref_id: string }>(`/api/calendar/events/${eventId}/insight`),

    /** 查询历史分析 */
    getHistory: (params?: { insight_type?: string; ref_id?: string; limit?: number }) =>
      ApiClient.get<AiInsight[]>('/api/calendar/insights', params),
  },
}
