"""
二级市场指标采集器
从 AKShare 采集成交额、涨跌家数、涨停跌停、融资融券、板块排名等数据
"""

import asyncio
import logging
import random
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple

import pandas as pd
import requests as _requests
from requests.adapters import HTTPAdapter as _HTTPAdapter

logger = logging.getLogger("market_indicator_fetcher")

# ---------------------------------------------------------------------------
# 补丁：AKShare 的 request_with_retry 没有传递浏览器请求头，
# 导致东方财富服务端识别为爬虫直接断连 (RemoteDisconnected)。
# 这里在模块加载时 patch 掉，注入 akshare.utils.cons 中定义的 UA。
# ---------------------------------------------------------------------------
try:
    import akshare.utils.request as _ak_req
    from akshare.utils.cons import headers as _ak_headers

    _orig_request_with_retry = _ak_req.request_with_retry

    def _patched_request_with_retry(
        url: str,
        params: dict = None,
        timeout: int = 15,
        max_retries: int = 3,
        base_delay: float = 1.0,
        random_delay_range: Tuple[float, float] = (0.5, 1.5),
    ):
        last_exception = None
        for attempt in range(max_retries):
            try:
                with _requests.Session() as session:
                    adapter = _HTTPAdapter(pool_connections=1, pool_maxsize=1)
                    session.mount("http://", adapter)
                    session.mount("https://", adapter)
                    session.headers.update(_ak_headers)
                    response = session.get(url, params=params, timeout=timeout)
                    response.raise_for_status()
                    return response
            except (_requests.RequestException, ValueError) as e:
                last_exception = e
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt) + random.uniform(*random_delay_range)
                    time.sleep(delay)
        raise last_exception

    _ak_req.request_with_retry = _patched_request_with_retry
    logger.info("已修补 AKShare request_with_retry: 添加浏览器请求头")
except ImportError:
    logger.warning("未找到 AKShare，跳过请求头补丁")

# ---------------------------------------------------------------------------
# 重试配置（仅用于 AKShare 函数级别的外层重试，AKShare 内部已有 3 次重试）
# ---------------------------------------------------------------------------
_MAX_RETRIES = 2
_INITIAL_DELAY = 3


class MarketIndicatorFetcher:
    """二级市场指标采集器"""

    @staticmethod
    async def _call_sync(fn, label: str, *,
                         max_retries: int = _MAX_RETRIES,
                         initial_delay: float = _INITIAL_DELAY):
        """在线程池中执行同步 AKShare 调用（AKShare 内部已有重试，外层做少量兜底）"""
        last_error = None
        for attempt in range(max_retries):
            try:
                return await asyncio.to_thread(fn)
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = initial_delay * (2 ** attempt) + random.uniform(0, 2)
                    logger.warning(f"{label} 第{attempt + 1}次失败，{delay:.1f}s 后重试: {e}")
                    await asyncio.sleep(delay)
        logger.error(f"{label} 失败(重试{max_retries}次): {last_error}")
        return None

    async def fetch_advance_decline(self) -> List[Dict[str, Any]]:
        """采集涨跌家数"""
        def _do():
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

        result = await self._call_sync(_do, "采集涨跌家数")
        return result or []

    async def fetch_limit_stats(self) -> List[Dict[str, Any]]:
        """采集涨停跌停统计"""
        results = []
        today = datetime.now().strftime("%Y%m%d")

        def _fetch_zt():
            import akshare as ak
            return ak.stock_zt_pool_em(date=today)

        zt_df = await self._call_sync(_fetch_zt, "采集涨停数据")
        zt_count = len(zt_df) if zt_df is not None and not zt_df.empty else 0

        def _fetch_dt():
            import akshare as ak
            return ak.stock_zt_pool_dtgc_em(date=today)

        dt_df = await self._call_sync(_fetch_dt, "采集跌停数据")
        dt_count = len(dt_df) if dt_df is not None and not dt_df.empty else 0

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

    async def _fetch_spot_data(self) -> pd.DataFrame | None:
        """
        采集沪深A股实时行情（共享结果，避免 volume 和 turnover 各调一次）
        """
        def _do():
            import akshare as ak
            return ak.stock_zh_a_spot_em()

        return await self._call_sync(_do, "采集沪深A股行情")

    async def fetch_volume(self) -> List[Dict[str, Any]]:
        """采集全市场成交额"""
        df = await self._fetch_spot_data()
        if df is None or df.empty:
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

    async def fetch_turnover(self) -> List[Dict[str, Any]]:
        """采集全市场换手率"""
        df = await self._fetch_spot_data()
        if df is None or df.empty:
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

    async def fetch_margin_trading(self) -> List[Dict[str, Any]]:
        """采集融资融券数据"""
        def _do():
            import akshare as ak
            df = ak.stock_margin_sse(
                start_date=(datetime.now() - timedelta(days=30)).strftime("%Y%m%d"),
                end_date=datetime.now().strftime("%Y%m%d")
            )
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

        result = await self._call_sync(_do, "采集融资融券")
        return result or []

    async def fetch_sector_ranking(self) -> List[Dict[str, Any]]:
        """采集板块热度排名"""
        def _do():
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

        result = await self._call_sync(_do, "采集板块热度排名")
        return result or []

    async def fetch_all(self) -> Dict[str, List[Dict[str, Any]]]:
        """采集所有二级市场指标（串行，请求间加入间隔避免被远端限流）"""
        results = {}

        # 先把需要共享 spot 数据的合并采集，减少对同一接口的重复请求
        spot_data = await self._fetch_spot_data()

        # volume / turnover 使用缓存的 spot_data，不重复请求
        for name, parser in [
            ("volume", self._parse_volume),
            ("turnover", self._parse_turnover),
        ]:
            try:
                data = parser(spot_data)
                results[name] = data
            except Exception as e:
                logger.error(f"解析 {name} 异常: {e}")
                results[name] = []

        # 其他接口串行请求，间隔 2s
        for name, fetcher in [
            ("advance_decline", self.fetch_advance_decline),
            ("limit_stats", self.fetch_limit_stats),
            ("margin_trading", self.fetch_margin_trading),
            ("sector_ranking", self.fetch_sector_ranking),
        ]:
            try:
                await asyncio.sleep(2)
                data = await fetcher()
                results[name] = data
            except Exception as e:
                logger.error(f"采集 {name} 异常: {e}")
                results[name] = []

        return results

    # ---- 纯解析方法，供 fetch_all 使用缓存的 spot_data ----

    @staticmethod
    def _parse_volume(df) -> List[Dict[str, Any]]:
        if df is None or df.empty:
            return []
        total_amount = float(df.get("成交额", pd.Series([0])).sum())
        logger.info(f"采集全市场成交额完成: {total_amount / 1e8:.2f} 亿")
        return [{
            "indicator_type": "volume",
            "total_amount": total_amount,
            "date": datetime.now(),
            "source": "AKShare",
        }]

    @staticmethod
    def _parse_turnover(df) -> List[Dict[str, Any]]:
        if df is None or df.empty:
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
        logger.info(f"采集全市场换手率完成: {avg_turnover:.4f}")
        return [{
            "indicator_type": "turnover",
            "avg_turnover_rate": round(avg_turnover, 4),
            "date": datetime.now(),
            "source": "AKShare",
        }]
