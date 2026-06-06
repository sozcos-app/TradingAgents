"""
交易日历工具
判断交易日、生成期指交割日、机构考核期等固定日历事件
"""

import calendar
import logging
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional

logger = logging.getLogger("trade_calendar")


class TradeCalendar:
    """交易日历工具"""

    def is_trade_day(self, d: date = None) -> bool:
        """判断是否为交易日"""
        if d is None:
            d = date.today()
        try:
            import chinese_calendar
            return chinese_calendar.is_workday(d)
        except ImportError:
            # 回退：简单判断（排除周末）
            return d.weekday() < 5

    def get_trade_days(self, start: date, end: date) -> List[date]:
        """获取时间段内的交易日列表"""
        trade_days = []
        current = start
        while current <= end:
            if self.is_trade_day(current):
                trade_days.append(current)
            current += timedelta(days=1)
        return trade_days

    def get_next_trade_day(self, d: date = None, n: int = 1) -> date:
        """获取未来第 N 个交易日"""
        if d is None:
            d = date.today()
        count = 0
        current = d + timedelta(days=1)
        while count < n:
            if self.is_trade_day(current):
                count += 1
                if count == n:
                    return current
            current += timedelta(days=1)
        return current

    def generate_futures_expiry(self, year: int) -> List[Dict[str, Any]]:
        """生成期指交割日（每月第三个周五）"""
        events = []
        for month in range(1, 13):
            # 找到该月第三个周五
            c = calendar.monthcalendar(year, month)
            friday_count = 0
            for week in c:
                if week[calendar.FRIDAY] != 0:
                    friday_count += 1
                    if friday_count == 3:
                        expiry_date = date(year, month, week[calendar.FRIDAY])
                        events.append({
                            "title": f"{year}年{month}月期指交割日",
                            "event_type": "其他",
                            "event_date": datetime.combine(expiry_date, datetime.min.time()),
                            "impact_direction": "中性",
                            "impact_strength": "中",
                            "affected_sectors": [],
                            "action_suggestion": "尾盘可能异动，提前一天关注调整名单个股",
                            "source": "固定日历规则",
                            "description": f"{year}年{month}月股指期货交割日，尾盘可能出现被动资金调仓",
                        })
                        break
        return events

    def generate_institution_periods(self, year: int) -> List[Dict[str, Any]]:
        """生成机构考核期（每季末最后两周）"""
        events = []
        quarter_ends = [(3, 31), (6, 30), (9, 30), (12, 31)]
        quarter_names = ["Q1", "Q2", "Q3", "Q4"]

        for i, (month, day) in enumerate(quarter_ends):
            end_date = date(year, month, day)
            # 最后两个周五
            start_date = end_date - timedelta(days=14)
            events.append({
                "title": f"{year}年{quarter_names[i]}机构考核期",
                "event_type": "机构考核",
                "event_date": datetime.combine(start_date, datetime.min.time()),
                "impact_direction": "中性",
                "impact_strength": "中",
                "affected_sectors": [],
                "action_suggestion": "持有机构重仓股不动，不追高；关注排名争夺导致的异动",
                "source": "固定日历规则",
                "description": f"{year}年{quarter_names[i]}末机构排名考核期（{start_date}至{end_date}），可能出现拉升重仓股或砸盘对手股",
            })
        return events

    def generate_macro_publish_dates(self, year: int, month: int) -> List[Dict[str, Any]]:
        """生成宏观数据发布日历（近似日期）"""
        events = []

        # PMI：每月最后一天或次月1日
        if month == 12:
            pmi_date = date(year, month, 31)
        else:
            pmi_date = date(year, month + 1, 1) if month < 12 else date(year, month, 31)
        events.append({
            "title": f"{year}年{month}月PMI数据发布",
            "event_type": "宏观数据",
            "event_date": datetime.combine(pmi_date, datetime.min.time()),
            "impact_direction": "中性",
            "impact_strength": "高",
            "affected_sectors": ["制造业"],
            "action_suggestion": "数据发布前1天仓位谨慎，发布后顺势操作",
            "source": "固定日历规则",
            "description": "统计局公布上月制造业/非制造业PMI数据",
        })

        # CPI/PPI：每月9~10日
        cpi_date = date(year, month, 10)
        events.append({
            "title": f"{year}年{month}月CPI/PPI数据发布",
            "event_type": "宏观数据",
            "event_date": datetime.combine(cpi_date, datetime.min.time()),
            "impact_direction": "中性",
            "impact_strength": "高",
            "affected_sectors": ["消费", "工业"],
            "action_suggestion": "关注通胀数据对货币政策的指引",
            "source": "固定日历规则",
            "description": "统计局公布上月CPI和PPI数据",
        })

        # 社融：每月10~15日
        sf_date = date(year, month, 15)
        events.append({
            "title": f"{year}年{month}月社融数据发布",
            "event_type": "宏观数据",
            "event_date": datetime.combine(sf_date, datetime.min.time()),
            "impact_direction": "中性",
            "impact_strength": "高",
            "affected_sectors": ["银行", "券商"],
            "action_suggestion": "社融超预期利多周期板块，不及预期利空",
            "source": "固定日历规则",
            "description": "央行公布上月社会融资规模数据",
        })

        return events

    def generate_year_events(self, year: int) -> List[Dict[str, Any]]:
        """生成全年固定日历事件"""
        all_events = []
        all_events.extend(self.generate_futures_expiry(year))
        all_events.extend(self.generate_institution_periods(year))
        for month in range(1, 13):
            all_events.extend(self.generate_macro_publish_dates(year, month))
        return all_events


# 全局实例
trade_calendar = TradeCalendar()
