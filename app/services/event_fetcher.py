"""
市场事件采集器
从 AKShare / Tushare / 固定日历规则 采集市场事件
"""

import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any

logger = logging.getLogger("event_fetcher")


class EventFetcher:
    """市场事件采集器"""

    async def fetch_earnings_calendar(self, start: str, end: str) -> List[Dict[str, Any]]:
        """采集财报披露日程"""
        try:
            import akshare as ak
            df = ak.stock_disclosure_date_cninfo(date=start.replace("-", ""), end_date=end.replace("-", ""))
            events = []
            for _, row in df.iterrows():
                events.append({
                    "title": f"{row.get('股票简称', '')} 披露{row.get('报告期', '')}财报",
                    "event_type": "财报",
                    "event_date": datetime.strptime(str(row.get("实际披露日期", ""))[:10], "%Y-%m-%d") if row.get("实际披露日期") else None,
                    "impact_direction": "中性",
                    "impact_strength": "中",
                    "affected_sectors": [],
                    "action_suggestion": "关注业绩是否超预期",
                    "source": "巨潮资讯网",
                    "description": f"{row.get('股票简称', '')}({row.get('股票代码', '')}) {row.get('报告期', '')}财报披露",
                    "is_auto": True,
                })
            # 过滤无效日期
            events = [e for e in events if e["event_date"] is not None]
            logger.info(f"采集财报日程完成，共 {len(events)} 条")
            return events
        except Exception as e:
            logger.error(f"采集财报日程失败: {e}")
            return []

    async def fetch_unlock_calendar(self, start: str, end: str) -> List[Dict[str, Any]]:
        """采集解禁日历（过滤解禁市值 > 10亿）"""
        try:
            import akshare as ak
            df = ak.stock_restricted_release_summary_em(symbol="全部")
            events = []
            for _, row in df.iterrows():
                unlock_date_str = str(row.get("解禁日期", ""))
                if not unlock_date_str or len(unlock_date_str) < 10:
                    continue
                try:
                    unlock_date = datetime.strptime(unlock_date_str[:10], "%Y-%m-%d")
                except ValueError:
                    continue

                # 日期范围过滤
                start_dt = datetime.strptime(start, "%Y-%m-%d")
                end_dt = datetime.strptime(end, "%Y-%m-%d")
                if unlock_date < start_dt or unlock_date > end_dt:
                    continue

                amount = float(row.get("解禁市值", 0))
                if amount < 10e8:  # 低于10亿跳过
                    continue

                events.append({
                    "title": f"{row.get('股票简称', '')} 解禁{(amount / 1e8):.1f}亿",
                    "event_type": "解禁",
                    "event_date": unlock_date,
                    "impact_direction": "利空",
                    "impact_strength": "高" if amount > 50e8 else "中",
                    "affected_sectors": [],
                    "action_suggestion": f"解禁{(amount / 1e8):.0f}亿，提前5天回避",
                    "source": "东方财富",
                    "description": f"{row.get('股票简称', '')}({row.get('股票代码', '')}) 解禁{(amount / 1e8):.1f}亿元",
                    "is_auto": True,
                })
            logger.info(f"采集解禁日历完成，共 {len(events)} 条")
            return events
        except Exception as e:
            logger.error(f"采集解禁日历失败: {e}")
            return []

    async def fetch_macro_publish_schedule(self, year: int, month: int) -> List[Dict[str, Any]]:
        """采集宏观数据发布日程"""
        from app.services.trade_calendar import trade_calendar
        return trade_calendar.generate_macro_publish_dates(year, month)

    async def fetch_fixed_events(self, year: int) -> List[Dict[str, Any]]:
        """采集全年固定事件（期指交割、机构考核）"""
        from app.services.trade_calendar import trade_calendar
        return trade_calendar.generate_year_events(year)

    async def fetch_all(self, start: str, end: str) -> Dict[str, int]:
        """采集所有事件"""
        results = {}

        # 财报
        earnings = await self.fetch_earnings_calendar(start, end)
        results["earnings"] = len(earnings)

        # 解禁
        unlocks = await self.fetch_unlock_calendar(start, end)
        results["unlock"] = len(unlocks)

        # 宏观数据发布
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d")
        macro_events = []
        current = start_dt
        while current <= end_dt:
            month_events = await self.fetch_macro_publish_schedule(current.year, current.month)
            macro_events.extend(month_events)
            if current.month == 12:
                current = datetime(current.year + 1, 1, 1)
            else:
                current = datetime(current.year, current.month + 1, 1)
        results["macro"] = len(macro_events)

        # 固定事件
        fixed_events = await self.fetch_fixed_events(start_dt.year)
        results["fixed"] = len(fixed_events)

        return {
            "results": results,
            "events": earnings + unlocks + macro_events + fixed_events,
        }
