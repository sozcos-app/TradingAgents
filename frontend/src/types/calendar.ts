/**
 * 交易日历 - 类型定义
 */

// 宏观指标
export interface MacroIndicator {
  id?: string
  indicator_name: string
  value: number
  unit: string
  date: string
  source: string
  year_on_year?: number
  month_on_month?: number
  score?: number
}

// 宏观评分
export interface MacroScore {
  id?: string
  total_score: number
  level: string
  details: Record<string, any>
  alerts: Array<Record<string, any>>
  date: string
}

// 行业景气
export interface IndustryProsperity {
  id?: string
  industry_name: string
  inventory_cycle: string
  inventory_score: number
  profit_trend: string
  profit_score: number
  demand_growth: string
  demand_score: number
  capital_flow: string
  capital_score: number
  policy_support: string
  policy_score: number
  score: number
  suggestion: string
  catalysts: string[]
  five_dimensions?: Record<string, any>
  date: string
  // 市场数据
  change_pct?: number
  turnover_rate?: number
  up_count?: number
  down_count?: number
  rank?: number
  is_quick?: boolean
}

// 个股体检
export interface StockHealthCheck {
  id?: string
  ts_code: string
  stock_name: string
  main_business_score: number
  main_business_detail: Record<string, any>
  profit_quality_score: number
  profit_quality_detail: Record<string, any>
  gross_margin_score: number
  gross_margin_detail: Record<string, any>
  disclosure_score: number
  disclosure_detail: Record<string, any>
  supply_chain_score: number
  supply_chain_detail: Record<string, any>
  deduction: number
  total_score: number
  risk_level: string
  conclusion: string
  alerts: Array<Record<string, any>>
  date: string
}

// 市场事件
export interface MarketEvent {
  id?: string
  title: string
  event_type: string
  event_date: string
  impact_direction: string
  impact_strength: string
  affected_sectors: string[]
  action_suggestion: string
  source: string
  description: string
  is_auto: boolean
  created_by: string
}

// 事件类型
export interface EventType {
  value: string
  label: string
}

// 分页响应
export interface PaginatedResponse<T> {
  total: number
  page: number
  page_size: number
  items: T[]
}

// 二级市场指标
export interface MarketIndicator {
  id?: string
  indicator_type: string
  date: string
  source: string
  // 涨跌家数
  up_count?: number
  down_count?: number
  flat_count?: number
  // 涨停跌停
  limit_up_count?: number
  limit_down_count?: number
  // 成交额
  total_amount?: number
  // 换手率
  avg_turnover_rate?: number
  // 融资融券
  margin_buy?: number
  margin_balance?: number
  short_balance?: number
  // 板块
  sector_name?: string
  change_pct?: number
  turnover_rate?: number
}

// 二级市场指标概览
export interface MarketIndicatorOverview {
  advance_decline?: MarketIndicator
  limit_stats?: MarketIndicator
  volume?: MarketIndicator
  turnover?: MarketIndicator
  margin_trading?: MarketIndicator
  sector_ranking?: MarketIndicator[]
}

// 背离信号
export interface DivergenceSignal {
  id?: string
  judgment: string
  description: string
  action: string
  signals: Array<Record<string, any>>
  lie_count: number
  opportunity_count: number
  macro_score?: number
  date: string
}

// 库存周期象限图数据点
export interface InventoryCycleMapPoint {
  industry_name: string
  phase: string
  inventory_score: number
  change_pct: number
  turnover_rate: number
  score: number
  suggestion: string
}

// AI 洞察分析
export interface AiInsight {
  id?: string
  insight_type: 'macro' | 'industry' | 'stock' | 'event'
  ref_id: string
  content: string
  metadata: Record<string, any>
  created_at: string
}
