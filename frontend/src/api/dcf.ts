/**
 * DCF 股票估值计算 - API 接口
 */

import request from './request'
import type {
  DCFValuationResponse,
  CSVValidationResponse,
  FetchFinancialDataResponse,
  ValuateDirectRequest,
  CninfoSearchResponse,
} from '@/types/dcf'

export const dcfApi = {
  /**
   * 执行DCF估值计算
   * 使用 FormData 发送文件 + 参数到 /api/dcf/valuate
   */
  valuate: (params: {
    price_csv: File
    financial_csv: File
    stock_code: string
    model: string
    time?: number
    g1?: number
    g2?: number
    g3?: number
    t1_years?: number
    t2_years?: number
    k_e?: number
  }) => {
    const formData = new FormData()
    formData.append('price_csv', params.price_csv)
    formData.append('financial_csv', params.financial_csv)
    formData.append('stock_code', params.stock_code)
    formData.append('model', params.model)
    if (params.time !== undefined) formData.append('time', String(params.time))
    if (params.g1 !== undefined) formData.append('g1', String(params.g1))
    if (params.g2 !== undefined) formData.append('g2', String(params.g2))
    if (params.g3 !== undefined) formData.append('g3', String(params.g3))
    if (params.t1_years !== undefined) formData.append('t1_years', String(params.t1_years))
    if (params.t2_years !== undefined) formData.append('t2_years', String(params.t2_years))
    if (params.k_e !== undefined) formData.append('k_e', String(params.k_e))

    return request.post('/api/dcf/valuate', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    })
  },

  /**
   * 校验 CSV 格式
   */
  validateCsv: (file: File, fileType: 'price' | 'financial') => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('file_type', fileType)
    return request.post<CSVValidationResponse>('/api/dcf/validate-csv', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  /**
   * 自动获取财务数据
   */
  fetchFinancialData: (params: { stock_code: string; quarters?: number }) => {
    const formData = new FormData()
    formData.append('stock_code', params.stock_code)
    if (params.quarters !== undefined) formData.append('quarters', String(params.quarters))
    return request.post<FetchFinancialDataResponse>('/api/dcf/fetch-financial-data', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    })
  },

  /**
   * 直接估值（跳过 CSV）
   */
  valuateDirect: (params: ValuateDirectRequest) => {
    return request.post<DCFValuationResponse>('/api/dcf/valuate-direct', params, {
      timeout: 120000,
    })
  },

  /**
   * 搜索巨潮资讯公告
   */
  searchCninfo: (params: { stock_code: string; category?: string }) => {
    const formData = new FormData()
    formData.append('stock_code', params.stock_code)
    if (params.category) formData.append('category', params.category)
    return request.post<CninfoSearchResponse>('/api/dcf/cninfo-search', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 30000,
    })
  },

  /**
   * 获取估值历史记录
   */
  getHistory: (params?: { stock_code?: string; page?: number; page_size?: number }) =>
    request.get('/api/dcf/history', { params }),
}
