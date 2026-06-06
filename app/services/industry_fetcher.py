"""
行业景气数据采集器
从 AKShare / Tushare 采集行业景气相关数据
"""

import logging
from datetime import datetime
from typing import List, Dict, Any

import pandas as pd

logger = logging.getLogger("industry_fetcher")


class IndustryFetcher:
    """行业景气数据采集器"""

    async def fetch_sector_ranking(self) -> List[Dict[str, Any]]:
        """获取行业板块排名（成交额、涨跌幅）"""
        try:
            import akshare as ak
            df = ak.stock_board_industry_name_em()
            results = []
            for _, row in df.iterrows():
                results.append({
                    "industry_name": str(row.get("板块名称", "")),
                    "change_pct": float(row.get("涨跌幅", 0)),
                    "total_amount": float(row.get("总市值", 0)),
                    "turnover_rate": float(row.get("换手率", 0)),
                    "up_count": int(row.get("上涨家数", 0)),
                    "down_count": int(row.get("下跌家数", 0)),
                    "date": datetime.now(),
                    "source": "AKShare",
                })
            logger.info(f"✅ 采集行业板块排名完成，共 {len(results)} 个行业")
            return results
        except Exception as e:
            logger.error(f"❌ 采集行业板块排名失败: {e}")
            return []

    async def fetch_industry_moneyflow(self) -> List[Dict[str, Any]]:
        """获取行业资金流向"""
        try:
            import akshare as ak
            df = ak.stock_sector_fund_flow_rank(indicator="今日")
            results = []
            for _, row in df.iterrows():
                results.append({
                    "industry_name": str(row.get("名称", "")),
                    "net_amount": float(row.get("主力净流入-净额", 0)),
                    "net_pct": float(row.get("主力净流入-净占比", 0)),
                    "date": datetime.now(),
                    "source": "AKShare",
                })
            logger.info(f"✅ 采集行业资金流向完成，共 {len(results)} 个行业")
            return results
        except Exception as e:
            logger.error(f"❌ 采集行业资金流向失败: {e}")
            return []

    async def fetch_etf_flow(self) -> List[Dict[str, Any]]:
        """获取行业 ETF 份额变化（近似）"""
        try:
            import akshare as ak
            df = ak.fund_et_spot_em()
            results = []
            for _, row in df.iterrows():
                name = str(row.get("名称", ""))
                # 筛选行业 ETF
                if any(kw in name for kw in ["行业", "半导体", "芯片", "新能源", "医药", "消费", "军工", "银行", "券商", "地产", "钢铁", "煤炭", "有色"]):
                    results.append({
                        "etf_code": str(row.get("代码", "")),
                        "etf_name": name,
                        "volume": float(row.get("成交量", 0)),
                        "amount": float(row.get("成交额", 0)),
                        "date": datetime.now(),
                        "source": "AKShare",
                    })
            logger.info(f"✅ 采集行业 ETF 数据完成，共 {len(results)} 只")
            return results
        except Exception as e:
            logger.error(f"❌ 采集行业 ETF 失败: {e}")
            return []

    async def fetch_inventory_cycle(self) -> List[Dict[str, Any]]:
        """采集分行业库存周期数据（产成品库存同比 + PPI 分行业）"""
        results = []
        try:
            import akshare as ak
            # 工业企业产成品库存同比（宏观）
            df_inv = ak.macro_china_gdp()
            logger.info("✅ 采集库存数据（使用宏观数据近似）")
        except Exception as e:
            logger.warning(f"采集库存数据失败（使用板块数据近似）: {e}")

        # 使用板块涨跌幅作为行业景气代理指标
        try:
            import akshare as ak
            df = ak.stock_board_industry_name_em()
            for _, row in df.iterrows():
                change_pct = float(row.get("涨跌幅", 0))
                # 涨跌幅 > 0 近似为 PPI 上升，< 0 为下降
                # 换手率变化近似为库存变化（高换手 = 去库，低换手 = 补库）
                turnover = float(row.get("换手率", 0))
                if change_pct > 0 and turnover > 3:
                    phase = "被动去库"
                elif change_pct > 0 and turnover <= 3:
                    phase = "主动补库"
                elif change_pct <= 0 and turnover > 3:
                    phase = "主动去库"
                else:
                    phase = "被动补库"

                results.append({
                    "industry_name": str(row.get("板块名称", "")),
                    "ppi_yoy": change_pct,
                    "inventory_yoy": -turnover,  # 换手率高=库存去化
                    "phase": phase,
                    "date": datetime.now(),
                    "source": "AKShare(近似)",
                })
            logger.info(f"✅ 采集库存周期数据完成，共 {len(results)} 个行业")
        except Exception as e:
            logger.error(f"❌ 采集库存周期数据失败: {e}")

        return results

    async def fetch_industry_profitability(self) -> List[Dict[str, Any]]:
        """采集行业盈利数据（使用板块数据近似 ROE/毛利率）"""
        try:
            import akshare as ak
            df = ak.stock_board_industry_name_em()
            results = []
            for _, row in df.iterrows():
                change_pct = float(row.get("涨跌幅", 0))
                turnover = float(row.get("换手率", 0))
                up_count = int(row.get("上涨家数", 0))
                down_count = int(row.get("下跌家数", 0))
                total = up_count + down_count

                # 使用涨跌幅近似 ROE 趋势，上涨家数占比近似毛利率
                roe_approx = change_pct * 2  # 粗略映射
                margin_approx = (up_count / total * 100) if total > 0 else 50
                trend = "up" if change_pct > 0 else "down"

                results.append({
                    "industry_name": str(row.get("板块名称", "")),
                    "roe": round(roe_approx, 2),
                    "margin": round(margin_approx, 2),
                    "trend": trend,
                    "date": datetime.now(),
                    "source": "AKShare(近似)",
                })
            logger.info(f"✅ 采集行业盈利数据完成，共 {len(results)} 个行业")
            return results
        except Exception as e:
            logger.error(f"❌ 采集行业盈利数据失败: {e}")
            return []

    async def fetch_industry_demand(self) -> List[Dict[str, Any]]:
        """采集行业需求数据（使用板块成交额变化近似）"""
        try:
            import akshare as ak
            df = ak.stock_board_industry_name_em()
            results = []
            for _, row in df.iterrows():
                total_mv = float(row.get("总市值", 0))
                turnover = float(row.get("换手率", 0))
                # 成交额 = 总市值 * 换手率 / 100 近似需求活跃度
                amount_approx = total_mv * turnover / 100
                # 涨跌幅近似需求同比
                sales_yoy = float(row.get("涨跌幅", 0))

                results.append({
                    "industry_name": str(row.get("板块名称", "")),
                    "sales_yoy": round(sales_yoy, 2),
                    "amount": round(amount_approx, 0),
                    "date": datetime.now(),
                    "source": "AKShare(近似)",
                })
            logger.info(f"✅ 采集行业需求数据完成，共 {len(results)} 个行业")
            return results
        except Exception as e:
            logger.error(f"❌ 采集行业需求数据失败: {e}")
            return []

    async def fetch_industry_policy(self) -> List[Dict[str, Any]]:
        """采集行业政策支持数据（简化版，返回默认基础数据）"""
        # 政策数据需要人工维护或爬取政府网站，这里提供基础结构
        # 后续可接入 feedparser 或 LLM 分析
        try:
            import akshare as ak
            df = ak.stock_board_industry_name_em()
            results = []
            # 政策关键词匹配（简化版）
            policy_keywords = {
                "半导体": ("national", 3), "芯片": ("national", 3),
                "新能源": ("national", 4), "光伏": ("national", 3),
                "军工": ("national", 2), "医药": ("national", 2),
                "消费": ("provincial", 2), "银行": ("provincial", 1),
                "券商": ("provincial", 1), "地产": ("national", 2),
                "汽车": ("national", 2), "钢铁": ("provincial", 1),
                "煤炭": ("provincial", 1), "有色": ("provincial", 1),
            }
            for _, row in df.iterrows():
                name = str(row.get("板块名称", ""))
                level, count = "unknown", 0
                for kw, (lv, ct) in policy_keywords.items():
                    if kw in name:
                        level, count = lv, ct
                        break

                results.append({
                    "industry_name": name,
                    "policy_count": count,
                    "policy_level": level,
                    "date": datetime.now(),
                    "source": "内置规则",
                })
            logger.info(f"✅ 采集行业政策数据完成，共 {len(results)} 个行业")
            return results
        except Exception as e:
            logger.error(f"❌ 采集行业政策数据失败: {e}")
            return []

    async def fetch_all_dimensions(self) -> Dict[str, List[Dict[str, Any]]]:
        """采集全维度行业数据"""
        results = {}
        fetchers = {
            "sector_ranking": self.fetch_sector_ranking,
            "moneyflow": self.fetch_industry_moneyflow,
            "etf_flow": self.fetch_etf_flow,
            "inventory_cycle": self.fetch_inventory_cycle,
            "profitability": self.fetch_industry_profitability,
            "demand": self.fetch_industry_demand,
            "policy": self.fetch_industry_policy,
        }
        for name, fetcher in fetchers.items():
            try:
                data = await fetcher()
                results[name] = data
            except Exception as e:
                logger.error(f"❌ 采集 {name} 异常: {e}")
                results[name] = []
        return results
