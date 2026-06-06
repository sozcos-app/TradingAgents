"""
宏观数据采集器
从 AKShare / Tushare / 央行官网采集宏观经济指标
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

import pandas as pd

logger = logging.getLogger("macro_fetcher")


class MacroDataFetcher:
    """宏观数据采集器"""

    @staticmethod
    def _parse_month_date(date_str) -> Optional[datetime]:
        """解析 AKShare 返回的月份字符串，兼容多种格式"""
        if date_str is None:
            return None
        s = str(date_str).strip()
        # 2026年05月份 / 2026年5月份
        for fmt in ("%Y年%m月份", "%Y年%m月"):
            try:
                return pd.to_datetime(s, format=fmt).to_pydatetime()
            except ValueError:
                continue
        # 201501 纯数字格式
        try:
            return pd.to_datetime(s, format="%Y%m").to_pydatetime()
        except ValueError:
            pass
        # 最后尝试自动解析
        try:
            return pd.to_datetime(s).to_pydatetime()
        except Exception:
            return None

    # 可采集的指标列表
    INDICATORS = [
        "PMI",           # 制造业采购经理指数
        "CPI",           # 居民消费价格指数
        "PPI",           # 工业生产者出厂价格指数
        "M2",            # 广义货币供应量
        "社融规模增量",    # 社会融资规模增量
        "DR007",         # 银行间存款类金融机构7天期回购利率
        "人民币汇率",     # 美元兑人民币
        "北向资金",       # 北向资金净流入
    ]

    async def fetch_pmi(self) -> List[Dict[str, Any]]:
        """采集 PMI（制造业 + 非制造业）"""
        try:
            import akshare as ak
            df = ak.macro_china_pmi()
            indicators = []
            for _, row in df.iterrows():
                date_val = self._parse_month_date(row.get("月份"))
                if date_val is None:
                    continue
                # 制造业PMI
                indicators.append({
                    "indicator_name": "PMI",
                    "value": float(row.get("制造业-指数", 0)),
                    "unit": "",
                    "date": date_val,
                    "source": "AKShare",
                })
                # 非制造业PMI
                if "非制造业-指数" in row:
                    indicators.append({
                        "indicator_name": "非制造业PMI",
                        "value": float(row.get("非制造业-指数", 0)),
                        "unit": "",
                        "date": date_val,
                        "source": "AKShare",
                    })
            logger.info(f"✅ 采集 PMI 完成，共 {len(indicators)} 条")
            return indicators
        except Exception as e:
            logger.error(f"❌ 采集 PMI 失败: {e}")
            return []

    async def fetch_cpi(self) -> List[Dict[str, Any]]:
        """采集 CPI 同比"""
        try:
            import akshare as ak
            df = ak.macro_china_cpi()
            indicators = []
            for _, row in df.iterrows():
                date_val = self._parse_month_date(row.get("月份"))
                if date_val is None:
                    continue
                indicators.append({
                    "indicator_name": "CPI",
                    "value": float(row.get("全国-当月", 0)),
                    "unit": "",
                    "date": date_val,
                    "source": "AKShare",
                })
                # 同比增长
                if "全国-同比增长" in row:
                    indicators[-1]["year_on_year"] = float(row.get("全国-同比增长", 0))
            logger.info(f"✅ 采集 CPI 完成，共 {len(indicators)} 条")
            return indicators
        except Exception as e:
            logger.error(f"❌ 采集 CPI 失败: {e}")
            return []

    async def fetch_ppi(self) -> List[Dict[str, Any]]:
        """采集 PPI 同比"""
        try:
            import akshare as ak
            df = ak.macro_china_ppi()
            indicators = []
            for _, row in df.iterrows():
                date_val = self._parse_month_date(row.get("月份"))
                if date_val is None:
                    continue
                indicators.append({
                    "indicator_name": "PPI",
                    "value": float(row.get("当月", 0)),
                    "unit": "",
                    "date": date_val,
                    "source": "AKShare",
                })
            logger.info(f"✅ 采集 PPI 完成，共 {len(indicators)} 条")
            return indicators
        except Exception as e:
            logger.error(f"❌ 采集 PPI 失败: {e}")
            return []

    async def fetch_m2(self) -> List[Dict[str, Any]]:
        """采集 M2 同比"""
        try:
            import akshare as ak
            df = ak.macro_china_money_supply()
            indicators = []
            for _, row in df.iterrows():
                date_val = self._parse_month_date(row.get("月份"))
                if date_val is None:
                    continue
                m2_yoy = row.get("货币和准货币(M2)-同比增长", None)
                if m2_yoy is not None and not (isinstance(m2_yoy, float) and pd.isna(m2_yoy)):
                    indicators.append({
                        "indicator_name": "M2",
                        "value": float(m2_yoy),
                        "unit": "%",
                        "date": date_val,
                        "source": "AKShare",
                    })
            logger.info(f"✅ 采集 M2 完成，共 {len(indicators)} 条")
            return indicators
        except Exception as e:
            logger.error(f"❌ 采集 M2 失败: {e}")
            return []

    async def fetch_social_financing(self) -> List[Dict[str, Any]]:
        """采集社融规模增量"""
        try:
            import akshare as ak
            df = ak.macro_china_shrzgm()
            indicators = []
            for _, row in df.iterrows():
                date_val = self._parse_month_date(row.get("月份"))
                if date_val is None:
                    continue
                indicators.append({
                    "indicator_name": "社融规模增量",
                    "value": float(row.get("社会融资规模增量", 0)),
                    "unit": "亿元",
                    "date": date_val,
                    "source": "AKShare",
                })
            logger.info(f"✅ 采集社融规模增量完成，共 {len(indicators)} 条")
            return indicators
        except Exception as e:
            logger.error(f"❌ 采集社融规模增量失败: {e}")
            return []

    async def fetch_dr007(self) -> List[Dict[str, Any]]:
        """采集 DR007 利率（使用 Shibor 1周作为替代指标）"""
        try:
            import akshare as ak
            df = ak.rate_interbank(
                market="上海银行同业拆借市场",
                symbol="Shibor人民币",
                indicator="1周",
            )
            indicators = []
            for _, row in df.iterrows():
                indicators.append({
                    "indicator_name": "DR007",
                    "value": float(row.get("利率", 0)),
                    "unit": "%",
                    "date": pd.to_datetime(row.get("报告日", datetime.now())).to_pydatetime(),
                    "source": "AKShare",
                })
            logger.info(f"✅ 采集 DR007 完成，共 {len(indicators)} 条")
            return indicators
        except Exception as e:
            logger.error(f"❌ 采集 DR007 失败: {e}")
            return []

    async def fetch_exchange_rate(self) -> List[Dict[str, Any]]:
        """采集人民币汇率（美元兑人民币中间价）"""
        try:
            import akshare as ak
            df = ak.currency_boc_safe()
            indicators = []
            for _, row in df.iterrows():
                usd_val = row.get("美元", None)
                if usd_val is None or pd.isna(usd_val):
                    continue
                indicators.append({
                    "indicator_name": "人民币汇率",
                    "value": float(usd_val) / 100.0,
                    "unit": "",
                    "date": pd.to_datetime(row.get("日期", datetime.now())).to_pydatetime(),
                    "source": "AKShare",
                })
            logger.info(f"✅ 采集人民币汇率完成，共 {len(indicators)} 条")
            return indicators
        except Exception as e:
            logger.error(f"❌ 采集人民币汇率失败: {e}")
            return []

    async def fetch_northbound_flow(self) -> List[Dict[str, Any]]:
        """采集北向资金净流入（沪股通 + 深股通）"""
        try:
            import akshare as ak
            df_sh = ak.stock_hsgt_hist_em(symbol="沪股通")
            df_sz = ak.stock_hsgt_hist_em(symbol="深股通")

            # 合并沪股通和深股通数据
            sh_dict = {}
            for _, row in df_sh.iterrows():
                dt = str(row.get("日期", ""))[:10]
                if dt:
                    sh_dict[dt] = float(row.get("当日成交净买额", 0))

            sz_dict = {}
            for _, row in df_sz.iterrows():
                dt = str(row.get("日期", ""))[:10]
                if dt:
                    sz_dict[dt] = float(row.get("当日成交净买额", 0))

            all_dates = sorted(set(sh_dict.keys()) | set(sz_dict.keys()))
            indicators = []
            for dt in all_dates:
                total = sh_dict.get(dt, 0) + sz_dict.get(dt, 0)
                indicators.append({
                    "indicator_name": "北向资金",
                    "value": total,
                    "unit": "亿元",
                    "date": pd.to_datetime(dt).to_pydatetime(),
                    "source": "AKShare",
                })
            logger.info(f"✅ 采集北向资金完成，共 {len(indicators)} 条")
            return indicators
        except Exception as e:
            logger.error(f"❌ 采集北向资金失败: {e}")
            return []

    async def fetch_all(self) -> Dict[str, List[Dict[str, Any]]]:
        """采集所有指标"""
        results = {}
        fetchers = {
            "PMI": self.fetch_pmi,
            "CPI": self.fetch_cpi,
            "PPI": self.fetch_ppi,
            "M2": self.fetch_m2,
            "社融规模增量": self.fetch_social_financing,
            "DR007": self.fetch_dr007,
            "人民币汇率": self.fetch_exchange_rate,
            "北向资金": self.fetch_northbound_flow,
        }
        for name, fetcher in fetchers.items():
            try:
                data = await fetcher()
                results[name] = data
            except Exception as e:
                logger.error(f"❌ 采集 {name} 异常: {e}")
                results[name] = []
        return results
