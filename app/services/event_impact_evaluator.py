"""
事件影响力评估引擎
根据事件类型和内容自动评估影响方向、强度、板块和建议
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger("event_impact_evaluator")


class EventImpactEvaluator:
    """事件影响力评估引擎"""

    IMPACT_RULES = {
        "财报": {
            "default_direction": "中性",
            "default_strength": "中",
            "suggestion": "关注业绩是否超预期，超预期可提前3天潜伏",
            "sectors": ["全市场"],
        },
        "政策": {
            "default_direction": "中性",
            "default_strength": "高",
            "suggestion": "政策落地前布局相关板块，落地后观察效果",
            "sectors": ["全市场"],
        },
        "解禁": {
            "default_direction": "利空",
            "default_strength": "高",
            "suggestion": "解禁前5天回避，解禁后观察抛压结束信号",
            "sectors": [],
        },
        "地缘": {
            "default_direction": "利多",
            "default_strength": "高",
            "suggestion": "地缘冲突利多黄金/军工/油气，轻仓参与",
            "sectors": ["军工", "黄金", "油气"],
        },
        "指数调整": {
            "default_direction": "中性",
            "default_strength": "中",
            "suggestion": "尾盘可能异动，提前一天关注调整名单个股",
            "sectors": ["全市场"],
        },
        "宏观数据": {
            "default_direction": "中性",
            "default_strength": "高",
            "suggestion": "数据发布前仓位谨慎，发布后顺势操作",
            "sectors": ["银行", "券商", "消费", "工业"],
        },
        "龙头事件": {
            "default_direction": "中性",
            "default_strength": "中",
            "suggestion": "关注龙头股事件对产业链的传导效应",
            "sectors": [],
        },
        "机构考核": {
            "default_direction": "中性",
            "default_strength": "中",
            "suggestion": "持有机构重仓股不动，不追高；关注排名争夺导致的异动",
            "sectors": [],
        },
        "交易制度": {
            "default_direction": "中性",
            "default_strength": "低",
            "suggestion": "关注制度变更对交易策略的影响",
            "sectors": ["全市场"],
        },
        "其他": {
            "default_direction": "中性",
            "default_strength": "低",
            "suggestion": "",
            "sectors": [],
        },
    }

    def evaluate(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估单个事件影响力
        如果事件已有影响信息，保留原值；否则使用规则填充
        """
        event_type = event.get("event_type", "其他")
        rules = self.IMPACT_RULES.get(event_type, self.IMPACT_RULES["其他"])

        # 只在未设置时填充
        if not event.get("impact_direction") or event["impact_direction"] == "":
            event["impact_direction"] = rules["default_direction"]
        if not event.get("impact_strength") or event["impact_strength"] == "":
            event["impact_strength"] = rules["default_strength"]
        if not event.get("action_suggestion") or event["action_suggestion"] == "":
            event["action_suggestion"] = rules["suggestion"]
        if not event.get("affected_sectors") or len(event["affected_sectors"]) == 0:
            event["affected_sectors"] = rules["sectors"]

        return event

    def batch_evaluate(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量评估事件"""
        return [self.evaluate(e) for e in events]
