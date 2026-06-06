"""
二级市场指标采集器
从 AKShare 采集成交额、涨跌家数、涨停跌停、融资融券、板块排名等数据
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

import pandas as pd

logger = logging.getLogger("market_indicator_fetcher")


class MarketIndicatorFetcher:
    """二级市场指标采集器"""

    async def fetch_advance_decline(self) -> List[Dict[str, Any]]:
        """采集涨跌家数"""
        try:
            import akshare as ak
            df = ak.stock_market_activity_legu()
            results = []
            if df is not None and not df.empty:
                item_value = {}
                for _, row in df.iterrows():
                    item_value[str(row.get("item", ""))] = row.get("value", 0)

                date_str = item_value.get("统计日期", "")
                date = datetime.now()
                if date_str:
                    try:
                        date = pd.to_datetime(str(date_str).split(" ")[0]).to_pydatetime()
                    except Exception:
                        pass

                results.append({
                    "indicator_type": "advance_decline",
                    "up_count": int(item_value.get("上涨", 0) or 0),
                    "down_count": int(item_value.get("下跌", 0) or 0),
                    "flat_count": int(item_value.get("平盘", 0) or 0),
                    "date": date,
                    "source": "AKShare",
                })
            logger.info(f"采集涨跌家数完成，共 {len(results)} 条")
            return results
        except Exception as e:
            logger.error(f"采集涨跌家数失败: {e}")
            return []

    async def fetch_limit_stats(self) -> List[Dict[str, Any]]:
        """采集涨停跌停统计"""
        results = []
        today = datetime.now().strftime("%Y%m%d")

        # 涨停池
        try:
            import akshare as ak
            zt_df = ak.stock_zt_pool_em(date=today)
            zt_count = len(zt_df) if zt_df is not None and not zt_df.empty else 0
        except Exception as e:
            logger.warning(f"采集涨停数据失败: {e}")
            zt_count = 0

        # 跌停池
        try:
            import akshare as ak
            dt_df = ak.stock_zt_pool_dtgc_em(date=today)
            dt_count = len(dt_df) if dt_df is not None and not dt_df.empty else 0
        except Exception as e:
            logger.warning(f"采集跌停数据失败: {e}")
            dt_count = 0

        if zt_count > 0 or dt_count > 0:
            results.append({
                "indicator_type": "limit_stats",
                "limit_up_count": zt_count,
                "limit_down_count": dt_count,
                "date": datetime.now(),
                "source": "AKShare",
            })
            logger.info(f"采集涨停跌停完成: 涨停 {zt_count}, 跌停 {dt_count}")
        else:
            logger.info("未获取到涨停跌停数据")

        return results

    async def fetch_volume(self) -> List[Dict[str, Any]]:
        """采集全市场成交额（带重试）"""
        last_error = None
        for attempt in range(3):
            try:
                import akshare as ak
                df = ak.stock_zh_a_spot_em()
                if df is None or df.empty:
                    if attempt < 2:
                        import asyncio
                        await asyncio.sleep(2)
                        continue
                    return []

                total_amount = float(df.get("成交额", pd.Series([0])).sum())
                results = [{
                    "indicator_type": "volume",
                    "total_amount": total_amount,
                    "date": datetime.now(),
                    "source": "AKShare",
                }]
                logger.info(f"采集全市场成交额完成: {total_amount / 1e8:.2f} 亿")
                return results
            except Exception as e:
                last_error = e
                if attempt < 2:
                    import asyncio
                    await asyncio.sleep(3)
        logger.error(f"采集全市场成交额失败(重试3次): {last_error}")
        return []

    async def fetch_turnover(self) -> List[Dict[str, Any]]:
        """采集全市场换手率（带重试）"""
        last_error = None
        for attempt in range(3):
            try:
                import akshare as ak
                df = ak.stock_zh_a_spot_em()
                if df is None or df.empty:
                    if attempt < 2:
                        import asyncio
                        await asyncio.sleep(2)
                        continue
                    return []

                turnover_col = None
                for col in df.columns:
                    if "换手率" in str(col):
                        turnover_col = col
                        break

                if turnover_col is None:
                    logger.warning("未找到换手率列")
                    return []

                avg_turnover = float(df[turnover_col].mean())
                results = [{
                    "indicator_type": "turnover",
                    "avg_turnover_rate": round(avg_turnover, 4),
                    "date": datetime.now(),
                    "source": "AKShare",
                }]
                logger.info(f"采集全市场换手率完成: {avg_turnover:.4f}")
                return results
            except Exception as e:
                last_error = e
                if attempt < 2:
                    import asyncio
                    await asyncio.sleep(3)
        logger.error(f"采集全市场换手率失败(重试3次): {last_error}")
        return []

    async def fetch_margin_trading(self) -> List[Dict[str, Any]]:
        """采集融资融券数据"""
        try:
            import akshare as ak
            # 沪深两市融资融券汇总
            df = ak.stock_margin_sse(start_date=(datetime.now() - timedelta(days=30)).strftime("%Y%m%d"),
                                      end_date=datetime.now().strftime("%Y%m%d"))
            results = []
            for _, row in df.iterrows():
                results.append({
                    "indicator_type": "margin_trading",
                    "margin_buy": float(row.get("融资买入额(元)", 0)),
                    "margin_balance": float(row.get("融资余额(元)", 0)),
                    "short_balance": float(row.get("融券余额(元)", 0)),
                    "date": pd.to_datetime(row.get("日期", datetime.now())).to_pydatetime(),
                    "source": "AKShare",
                })
            logger.info(f"采集融资融券完成，共 {len(results)} 条")
            return results
        except Exception as e:
            logger.error(f"采集融资融券失败: {e}")
            return []

    async def fetch_sector_ranking(self) -> List[Dict[str, Any]]:
        """采集板块热度排名"""
        try:
            import akshare as ak
            df = ak.stock_board_industry_name_em()
            results = []
            for _, row in df.iterrows():
                results.append({
                    "indicator_type": "sector_ranking",
                    "sector_name": str(row.get("板块名称", "")),
                    "change_pct": float(row.get("涨跌幅", 0)),
                    "total_amount": float(row.get("总市值", 0)),
                    "turnover_rate": float(row.get("换手率", 0)),
                    "up_count": int(row.get("上涨家数", 0)),
                    "down_count": int(row.get("下跌家数", 0)),
                    "date": datetime.now(),
                    "source": "AKShare",
                })
            logger.info(f"采集板块热度排名完成，共 {len(results)} 个板块")
            return results
        except Exception as e:
            logger.error(f"采集板块热度排名失败: {e}")
            return []

    async def fetch_all(self) -> Dict[str, List[Dict[str, Any]]]:
        """采集所有二级市场指标"""
        results = {}
        fetchers = {
            "advance_decline": self.fetch_advance_decline,
            "limit_stats": self.fetch_limit_stats,
            "volume": self.fetch_volume,
            "turnover": self.fetch_turnover,
            "margin_trading": self.fetch_margin_trading,
            "sector_ranking": self.fetch_sector_ranking,
        }
        for name, fetcher in fetchers.items():
            try:
                data = await fetcher()
                results[name] = data
            except Exception as e:
                logger.error(f"采集 {name} 异常: {e}")
                results[name] = []
        return results
