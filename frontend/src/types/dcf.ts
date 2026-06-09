/**
 * DCF 股票估值计算 - 类型定义
 */

/** DCF 折现模型类型 */
export type DCFModel = 'zero-growth' | 'constant-growth' | 'two-stage' | 'three-stage'

/** DCF 模型选项 */
export interface DCFModelOption {
  value: DCFModel
  label: string
  description: string
}

/** 财务指标 */
export interface FinancialMetrics {
  financial_assets: number
  company_debt: number
  operating_fcf: number
  effective_tax_rate: number
  minority_interest_ratio: number
  debt_ratio: number
  debt_capital_cost: number
}

/** WACC 计算明细 */
export interface WACCDetail {
  wacc: number
  cost_of_debt: number
  cost_of_equity: number
  debt_weight: number
  equity_weight: number
  tax_rate: number
}

/** DCF 估值结果 */
export interface DCFResult {
  intrinsic_value_per_share: number
  total_equity_value: number
  operating_fcf: number
  fcf_present_value: number
  financial_assets: number
  company_debt: number
  net_asset_value: number
  minority_deduction: number
  shares_outstanding: number
  current_price: number | null
  safety_margin: number | null
}

/** DCF 估值完整响应 */
export interface DCFValuationResponse {
  stock_code: string
  stock_name: string | null
  model: DCFModel
  wacc_detail: WACCDetail
  financial_metrics: FinancialMetrics
  result: DCFResult
  parameters: Record<string, number>
  forecast_fcf: ForecastFCF[]
  price_history: PriceHistoryPoint[]
}

/** 预测 FCF 数据点 */
export interface ForecastFCF {
  year: number
  fcf: number
  growth_rate: number
  is_terminal?: boolean
}

/** 历史价格数据点 */
export interface PriceHistoryPoint {
  date: string
  price: number
}

/** CSV 校验响应 */
export interface CSVValidationResponse {
  valid: boolean
  file_type: string
  row_count: number
  columns: string[]
  missing_columns: string[]
  errors: string[]
}

/** DCF 模型选项列表 */
export const DCF_MODEL_OPTIONS: DCFModelOption[] = [
  { value: 'zero-growth', label: '零增长模型', description: '适用于成熟稳定、无增长的公司' },
  { value: 'constant-growth', label: '不变增长模型', description: '适用于成熟、缓慢增长的公司' },
  { value: 'two-stage', label: '两阶段模型', description: '高速增长 + 稳定增长' },
  { value: 'three-stage', label: '三阶段模型', description: '成长 + 过渡 + 稳定' },
]

/** 单条原始财务科目 */
export interface RawFinancialItem {
  dcf_column: string
  display_name: string
  value: number
  category: string
}

/** 单期财务数据 */
export interface PeriodFinancialData {
  report_date: string
  raw_items: RawFinancialItem[]
  metrics: FinancialMetrics | null
}

/** 自动获取财务数据响应 */
export interface FetchFinancialDataResponse {
  stock_code: string
  stock_name: string | null
  total_market_cap: number | null
  current_price: number | null
  shares_outstanding: number | null
  periods: PeriodFinancialData[]
  columns_found: string[]
  columns_missing: string[]
}

/** 直接估值请求 */
export interface ValuateDirectRequest {
  stock_code: string
  stock_name?: string | null
  model: DCFModel
  time: number
  g1: number
  g2: number
  g3: number
  t1_years: number
  t2_years: number
  k_e: number
  metrics: FinancialMetrics
  total_market_cap: number
  current_price: number
}

/** 巨潮资讯公告记录 */
export interface CninfoAnnouncement {
  title: string
  announcement_id: string
  announcement_type: string
  stock_code: string
  sec_name: string
  sec_code: string
  pub_date: string
  adjunct_url: string
  adjunct_size: number
  download_url: string
}

/** 巨潮资讯搜索结果 */
export interface CninfoSearchResponse {
  total: number
  announcements: CninfoAnnouncement[]
}
