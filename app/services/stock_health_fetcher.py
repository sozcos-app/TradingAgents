"""
个股体检数据采集器
从 AKShare / Tushare 采集个股体检所需数据
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

import pandas as pd

logger = logging.getLogger("stock_health_fetcher")


class StockHealthFetcher:
    """个股体检数据采集器"""

    async def fetch_basic_info(self, ts_code: str) -> Dict[str, Any]:
        """获取股票基本信息"""
        try:
            import akshare as ak
            # 去掉后缀 .SZ/.SH，AKShare 使用纯数字代码
            code = ts_code.split(".")[0]
            df = ak.stock_individual_info_em(symbol=code)
            info = {}
            for _, row in df.iterrows():
                key = str(row.get("item", "")).strip()
                val = row.get("value", "")
                info[key] = str(val)
            return {
                "ts_code": ts_code,
                "stock_name": info.get("股票简称", ""),
                "industry": info.get("行业", ""),
                "list_date": info.get("上市时间", ""),
                "total_mv": info.get("总市值", ""),
            }
        except Exception as e:
            logger.error(f"获取基本信息失败 {ts_code}: {e}")
            return {"ts_code": ts_code, "stock_name": ""}

    async def fetch_main_business(self, ts_code: str) -> Dict[str, Any]:
        """获取主营业务收入构成"""
        try:
            import akshare as ak
            code = ts_code.split(".")[0]
            # 使用个股信息近似
            df = ak.stock_individual_info_em(symbol=code)
            info = {}
            for _, row in df.iterrows():
                info[str(row.get("item", "")).strip()] = str(row.get("value", ""))

            # 使用行业信息近似主营匹配度
            industry = info.get("行业", "")
            return {
                "ts_code": ts_code,
                "main_ratio": 75.0,  # 默认值，实际需要从年报解析
                "industry": industry,
                "detail": f"行业: {industry}",
            }
        except Exception as e:
            logger.error(f"获取主营业务数据失败 {ts_code}: {e}")
            return {"ts_code": ts_code, "main_ratio": None}

    async def fetch_profit_quality(self, ts_code: str) -> Dict[str, Any]:
        """获取利润含金量数据"""
        try:
            import akshare as ak
            code = ts_code.split(".")[0]
            # 使用财务指标接口
            df = ak.stock_financial_analysis_indicator(symbol=code)
            if df is None or df.empty:
                return {"ts_code": ts_code, "deducted_ratio": None}

            latest = df.iloc[0] if len(df) > 0 else {}
            # 扣非净利润 / 归属净利润
            net_profit = float(latest.get("净利润", 0))
            deducted = float(latest.get("扣除非经常性损益后的净利润", 0))
            ratio = (deducted / net_profit * 100) if net_profit != 0 else 0

            # 趋势
            trend = "stable"
            if len(df) >= 2:
                prev_ratio = 0
                prev_net = float(df.iloc[1].get("净利润", 0))
                prev_ded = float(df.iloc[1].get("扣除非经常性损益后的净利润", 0))
                prev_ratio = (prev_ded / prev_net * 100) if prev_net != 0 else 0
                if ratio > prev_ratio + 5:
                    trend = "up"
                elif ratio < prev_ratio - 5:
                    trend = "down"

            return {
                "ts_code": ts_code,
                "deducted_ratio": round(ratio, 2),
                "net_profit": net_profit,
                "deducted_profit": deducted,
                "trend": trend,
            }
        except Exception as e:
            logger.error(f"获取利润含金量失败 {ts_code}: {e}")
            return {"ts_code": ts_code, "deducted_ratio": None, "trend": "unknown"}

    async def fetch_gross_margin(self, ts_code: str) -> Dict[str, Any]:
        """获取毛利率数据"""
        try:
            import akshare as ak
            code = ts_code.split(".")[0]
            df = ak.stock_financial_analysis_indicator(symbol=code)
            if df is None or df.empty:
                return {"ts_code": ts_code, "gross_margin": None, "industry_avg": None}

            latest = df.iloc[0]
            gross_margin = float(latest.get("销售毛利率", 0))

            # 行业均值近似（使用30%作为A股平均水平）
            industry_avg = 30.0
            deviation = abs(gross_margin - industry_avg) / industry_avg * 100 if industry_avg else 0

            return {
                "ts_code": ts_code,
                "gross_margin": round(gross_margin, 2),
                "industry_avg": industry_avg,
                "deviation": round(deviation, 2),
            }
        except Exception as e:
            logger.error(f"获取毛利率失败 {ts_code}: {e}")
            return {"ts_code": ts_code, "gross_margin": None, "industry_avg": None}

    async def fetch_disclosure_risk(self, ts_code: str) -> Dict[str, Any]:
        """获取信披风险数据（简化版，基于公开数据）"""
        try:
            # 简化版：默认无处罚记录
            # 实际生产需接入巨潮资讯网爬虫
            return {
                "ts_code": ts_code,
                "penalty_count": 0,
                "inquiry_count": 0,
                "investigation": False,
                "detail": "无公开处罚/问询记录(简化版)",
            }
        except Exception as e:
            logger.error(f"获取信披风险失败 {ts_code}: {e}")
            return {"ts_code": ts_code, "penalty_count": 0}

    async def fetch_supply_chain(self, ts_code: str) -> Dict[str, Any]:
        """获取供应链验证数据（简化版）"""
        try:
            return {
                "ts_code": ts_code,
                "in_supply_chain": False,
                "has_contract": False,
                "detail": "供应链数据需人工确认(简化版)",
            }
        except Exception as e:
            logger.error(f"获取供应链数据失败 {ts_code}: {e}")
            return {"ts_code": ts_code, "in_supply_chain": False}

    async def fetch_unlock_pressure(self, ts_code: str) -> Dict[str, Any]:
        """获取解禁压力数据"""
        try:
            import akshare as ak
            code = ts_code.split(".")[0]
            df = ak.stock_restricted_release_summary_em(symbol=code)
            if df is None or df.empty:
                return {"ts_code": ts_code, "unlock_ratio": 0}

            # 未来解禁占总市值比例
            total_unlock = float(df.get("解禁数量", pd.Series([0])).sum())
            # 近似计算
            unlock_ratio = min(total_unlock * 100, 50)  # 上限50%

            return {
                "ts_code": ts_code,
                "unlock_ratio": round(unlock_ratio, 2),
                "detail": f"近期解禁比例: {unlock_ratio:.2f}%",
            }
        except Exception as e:
            logger.error(f"获取解禁数据失败 {ts_code}: {e}")
            return {"ts_code": ts_code, "unlock_ratio": 0}

    async def fetch_all(self, ts_code: str) -> Dict[str, Any]:
        """采集全部体检数据"""
        basic = await self.fetch_basic_info(ts_code)
        main_biz = await self.fetch_main_business(ts_code)
        profit = await self.fetch_profit_quality(ts_code)
        margin = await self.fetch_gross_margin(ts_code)
        disclosure = await self.fetch_disclosure_risk(ts_code)
        supply = await self.fetch_supply_chain(ts_code)
        unlock = await self.fetch_unlock_pressure(ts_code)

        return {
            "basic": basic,
            "main_business": main_biz,
            "profit_quality": profit,
            "gross_margin": margin,
            "disclosure": disclosure,
            "supply_chain": supply,
            "unlock_pressure": unlock,
        }
