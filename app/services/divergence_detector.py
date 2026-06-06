"""
背离检测引擎
检测宏观评分与二级市场指标之间的背离信号
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("divergence_detector")


class DivergenceDetector:
    """背离检测引擎"""

    def detect_macro_market_divergence(
        self,
        macro_score: float,
        macro_direction: str,
        market_data: Dict[str, Any],
        market_history: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        检测宏观与市场的背离信号

        Args:
            macro_score: 最新宏观评分 (0~100)
            macro_direction: 宏观评分趋势 "up" / "down" / "stable"
            market_data: 最新市场数据 (含 volume, limit_up, advance/decline 等)
            market_history: 近期市场数据列表 (用于趋势判断)

        Returns:
            背离信号列表
        """
        signals = []

        # 规则1: 宏观评分下降 + 成交额连续3天放量 → "虚假繁荣"预警
        if macro_direction == "down":
            volume_increasing = self._check_volume_increasing(market_history, days=3)
            if volume_increasing:
                signals.append({
                    "type": "谎言",
                    "severity": "高",
                    "rule": "虚假繁荣",
                    "message": f"宏观评分下降({macro_score}分)但成交额连续放量，可能为虚假繁荣",
                    "macro_score": macro_score,
                    "detail": "宏观基本面恶化，但市场资金仍在涌入，需警惕情绪驱动行情",
                })

        # 规则2: 宏观评分下降 + 涨停数增加 → "情绪与基本面背离"
        if macro_direction == "down":
            limit_up_rising = self._check_limit_up_rising(market_history, days=3)
            if limit_up_rising:
                signals.append({
                    "type": "谎言",
                    "severity": "中",
                    "rule": "情绪与基本面背离",
                    "message": f"宏观评分下降({macro_score}分)但涨停数增加，市场情绪与基本面背离",
                    "macro_score": macro_score,
                    "detail": "市场投机情绪高涨但宏观环境不支持，存在回调风险",
                })

        # 规则3: 宏观评分上升 + 市场缩量下跌 → "机会信号"提示
        if macro_direction == "up":
            volume_decreasing = self._check_volume_decreasing(market_history, days=3)
            decline_dominant = self._check_decline_dominant(market_data)
            if volume_decreasing and decline_dominant:
                signals.append({
                    "type": "机会",
                    "severity": "中",
                    "rule": "缩量下跌中的机会",
                    "message": f"宏观评分上升({macro_score}分)但市场缩量下跌，可能为布局机会",
                    "macro_score": macro_score,
                    "detail": "宏观环境改善但市场尚未反应，缩量下跌往往预示底部接近",
                })

        return signals

    def detect_lie_opportunity(self, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        综合输出"谎言"/"机会"判断

        Args:
            signals: 背离信号列表

        Returns:
            综合判断结果
        """
        if not signals:
            return {
                "judgment": "无明显背离",
                "description": "宏观与市场走势基本一致，无显著背离信号",
                "action": "维持当前策略",
                "signals": [],
            }

        lie_signals = [s for s in signals if s["type"] == "谎言"]
        opportunity_signals = [s for s in signals if s["type"] == "机会"]

        # 计算综合评分
        lie_severity_score = sum(3 if s["severity"] == "高" else 2 if s["severity"] == "中" else 1 for s in lie_signals)
        opp_severity_score = sum(3 if s["severity"] == "高" else 2 if s["severity"] == "中" else 1 for s in opportunity_signals)

        if lie_severity_score > opp_severity_score:
            judgment = "谎言风险"
            description = f"检测到 {len(lie_signals)} 个谎言信号，市场可能存在虚假繁荣"
            action = "建议减仓或保持谨慎，等待市场验证"
        elif opp_severity_score > lie_severity_score:
            judgment = "潜在机会"
            description = f"检测到 {len(opportunity_signals)} 个机会信号，市场可能被过度悲观"
            action = "可适度关注，分批布局"
        else:
            judgment = "信号矛盾"
            description = "同时存在谎言和机会信号，建议观望"
            action = "等待信号明确后再操作"

        return {
            "judgment": judgment,
            "description": description,
            "action": action,
            "signals": signals,
            "lie_count": len(lie_signals),
            "opportunity_count": len(opportunity_signals),
        }

    def _check_volume_increasing(self, history: List[Dict[str, Any]], days: int = 3) -> bool:
        """检查成交额是否连续N天增加"""
        if len(history) < days:
            return False
        volumes = []
        for item in history[-days:]:
            vol = item.get("total_amount") or item.get("volume")
            if vol is None:
                return False
            volumes.append(float(vol))
        return all(volumes[i] > volumes[i - 1] for i in range(1, len(volumes)))

    def _check_volume_decreasing(self, history: List[Dict[str, Any]], days: int = 3) -> bool:
        """检查成交额是否连续N天减少"""
        if len(history) < days:
            return False
        volumes = []
        for item in history[-days:]:
            vol = item.get("total_amount") or item.get("volume")
            if vol is None:
                return False
            volumes.append(float(vol))
        return all(volumes[i] < volumes[i - 1] for i in range(1, len(volumes)))

    def _check_limit_up_rising(self, history: List[Dict[str, Any]], days: int = 3) -> bool:
        """检查涨停数是否呈上升趋势"""
        if len(history) < days:
            return False
        counts = []
        for item in history[-days:]:
            cnt = item.get("limit_up_count") or item.get("limit_up")
            if cnt is None:
                return False
            counts.append(int(cnt))
        return all(counts[i] > counts[i - 1] for i in range(1, len(counts)))

    def _check_decline_dominant(self, market_data: Dict[str, Any]) -> bool:
        """检查是否下跌家数占优"""
        up = market_data.get("up_count", 0)
        down = market_data.get("down_count", 0)
        if up + down == 0:
            return False
        return down > up * 1.5
