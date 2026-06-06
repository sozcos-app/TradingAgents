"""
市场洞察 AI 分析服务
利用 LLM 对宏观/行业/个股/事件进行深度分析
"""

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from pymongo import MongoClient

from app.core.config import settings
from app.core.database import get_mongo_db
from tradingagents.llm_clients import create_llm_client
from tradingagents.llm_clients.provider_keys import normalize_provider_key, env_key_for_provider, default_backend_url

logger = logging.getLogger("market_insight_service")


def _get_llm_config_from_db() -> Optional[Dict[str, Any]]:
    """从数据库 system_configs 获取第一个可用的 LLM 配置"""
    try:
        client = MongoClient(settings.MONGO_URI)
        db = client[settings.MONGO_DB]

        doc = db.system_configs.find_one({"is_active": True}, sort=[("version", -1)])
        if not doc or "llm_configs" not in doc:
            # 尝试从 llm_providers 获取
            provider = db.llm_providers.find_one({"is_enabled": True})
            if provider:
                api_key = provider.get("api_key")
                if not api_key or api_key == "your-api-key":
                    env_key = env_key_for_provider(normalize_provider_key(provider["name"]))
                    api_key = __import__("os").getenv(env_key) if env_key else None
                result = {
                    "provider": normalize_provider_key(provider["name"]),
                    "model": provider.get("default_model", "gpt-4o-mini"),
                    "base_url": provider.get("default_base_url") or default_backend_url(normalize_provider_key(provider["name"])),
                    "api_key": api_key,
                }
                client.close()
                return result if result.get("api_key") else None

            client.close()
            return None

        llm_configs = doc["llm_configs"]
        if not llm_configs:
            client.close()
            return None

        # 取第一个有 API Key 的配置
        for config in llm_configs:
            provider = config.get("provider", "")
            model_name = config.get("model_name", "")
            api_base = config.get("api_base", "")
            api_key = config.get("api_key", "")

            if not api_key or api_key == "your-api-key":
                # 从环境变量获取
                env_key = env_key_for_provider(normalize_provider_key(provider))
                api_key = __import__("os").getenv(env_key) if env_key else None

            if not api_key:
                continue

            provider_key = normalize_provider_key(provider)
            if not api_base:
                api_base = default_backend_url(provider_key)

            client.close()
            return {
                "provider": provider_key,
                "model": model_name,
                "base_url": api_base,
                "api_key": api_key,
            }

        client.close()
        return None
    except Exception as e:
        logger.error(f"获取 LLM 配置失败: {e}")
        return None


class MarketInsightService:
    """市场洞察 AI 分析服务"""

    def __init__(self):
        self.db = None

    async def _get_db(self):
        if self.db is None:
            self.db = get_mongo_db()
        return self.db

    async def _call_llm(self, prompt: str) -> str:
        """调用 LLM 生成分析结果"""
        config = _get_llm_config_from_db()
        if not config:
            raise ValueError("未配置可用的 LLM，请先在系统设置中配置 AI 模型")

        client = create_llm_client(
            provider=config["provider"],
            model=config["model"],
            base_url=config["base_url"],
            api_key=config["api_key"],
            temperature=0.7,
        )

        llm = client.get_llm()
        from langchain_core.messages import HumanMessage
        response = await llm.ainvoke([HumanMessage(content=prompt)])

        content = getattr(response, "content", "")
        if isinstance(content, list):
            content = "\n".join(
                item.get("text", "") if isinstance(item, dict) and item.get("type") == "text"
                else str(item) if isinstance(item, str) else ""
                for item in content
            )
        return content

    async def _save_insight(self, insight_type: str, ref_id: str, content: str, metadata: Dict = None):
        """保存分析结果到 MongoDB"""
        db = await self._get_db()
        doc = {
            "insight_type": insight_type,
            "ref_id": ref_id,
            "content": content,
            "metadata": metadata or {},
            "created_at": datetime.utcnow(),
        }
        await db.calendar_insights.insert_one(doc)
        return str(doc.get("_id", ""))

    async def _get_insights(self, insight_type: str = None, ref_id: str = None, limit: int = 10) -> List[Dict]:
        """查询历史分析结果"""
        db = await self._get_db()
        query = {}
        if insight_type:
            query["insight_type"] = insight_type
        if ref_id:
            query["ref_id"] = ref_id

        cursor = db.calendar_insights.find(query).sort("created_at", -1).limit(limit)
        results = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id", ""))
            if isinstance(doc.get("created_at"), datetime):
                doc["created_at"] = doc["created_at"].isoformat()
            results.append(doc)
        return results

    # ============ 宏观谎言/机会分析 ============

    async def analyze_macro_divergence(self) -> Dict[str, Any]:
        """基于最新宏观评分和二级市场数据，分析是否存在虚假繁荣或被低估信号"""
        from app.services.calendar_service import macro_service, market_indicator_service

        # 获取宏观评分
        macro_score = await macro_service.get_latest_score()
        # 获取二级市场指标概览
        market_overview = await market_indicator_service.get_latest_overview()

        if not macro_score:
            return {"error": "暂无宏观评分数据，请先执行宏观评分"}

        prompt = f"""你是一位专业的宏观经济与A股市场分析师。请基于以下数据进行深度分析。

## 当前宏观环境
- 宏观总评分: {macro_score.get('total_score', 'N/A')}
- 评分等级: {macro_score.get('level', 'N/A')}
- 评分详情: {json.dumps(macro_score.get('details', {}), ensure_ascii=False, indent=2)}
- 预警信息: {json.dumps(macro_score.get('alerts', []), ensure_ascii=False, indent=2)}

## 二级市场数据
{json.dumps(market_overview or {}, ensure_ascii=False, indent=2)}

## 分析要求
请从以下角度分析当前市场是否存在"虚假繁荣"或"被低估"的信号：

1. **宏观与市场背离分析**：宏观评分与二级市场表现是否一致？
2. **谎言信号识别**：是否存在表面繁荣但实质恶化的迹象？（如：指数涨但个股普跌、量价背离等）
3. **机会信号识别**：是否存在被市场忽视的积极信号？（如：宏观改善但市场低迷、缩量见底等）
4. **操作建议**：基于分析给出具体操作建议

请用 Markdown 格式输出，包含明确的【谎言】或【机会】判断。"""

        content = await self._call_llm(prompt)
        await self._save_insight("macro", "latest", content, {
            "macro_score": macro_score.get("total_score"),
            "level": macro_score.get("level"),
        })
        return {"content": content, "type": "macro", "ref_id": "latest"}

    # ============ 行业异常分析 ============

    async def analyze_industry_anomaly(self, industry_name: str) -> Dict[str, Any]:
        """分析行业景气评分是否存在异常（虚高或被低估）"""
        from app.services.calendar_service import industry_service

        detail = await industry_service.get_detail(industry_name)
        if not detail:
            return {"error": f"未找到行业 {industry_name} 的数据"}

        prompt = f"""你是一位专业的行业景气度分析师。请基于以下数据进行深度分析。

## 行业: {industry_name}
- 综合评分: {detail.get('score', 'N/A')}
- 五维度指标: {json.dumps(detail.get('five_dimensions', {}), ensure_ascii=False, indent=2)}
- 库存周期: {detail.get('inventory_cycle', 'N/A')}
- 利润趋势: {detail.get('profit_trend', 'N/A')}
- 需求增长: {detail.get('demand_growth', 'N/A')}
- 资金流向: {detail.get('capital_flow', 'N/A')}
- 政策支持: {detail.get('policy_support', 'N/A')}
- 催化剂: {json.dumps(detail.get('catalysts', []), ensure_ascii=False)}

## 分析要求
1. **评分合理性**：当前评分是否合理？是否存在评分虚高或被低估的情况？
2. **维度矛盾**：五维度之间是否存在矛盾？（如政策面好但基本面差）
3. **隐藏风险**：是否存在数据表面看不到的风险？
4. **潜在机会**：是否有被忽视的催化剂或反转信号？
5. **操作建议**：针对该行业的具体操作建议

请用 Markdown 格式输出，明确标注【虚高风险】或【被低估机会】。"""

        content = await self._call_llm(prompt)
        await self._save_insight("industry", industry_name, content, {
            "score": detail.get("score"),
        })
        return {"content": content, "type": "industry", "ref_id": industry_name}

    # ============ 个股风险深度分析 ============

    async def analyze_stock_risk(self, ts_code: str) -> Dict[str, Any]:
        """深度分析个股是否存在财务造假、蹭概念、供应链风险等"""
        from app.services.calendar_service import stock_health_service

        report = await stock_health_service.get_report(ts_code)
        if not report:
            return {"error": f"未找到 {ts_code} 的体检报告，请先执行个股体检"}

        prompt = f"""你是一位专业的上市公司深度研究分析师，擅长识别财务造假和公司治理问题。请基于以下数据进行深度分析。

## 个股: {report.get('stock_name', ts_code)} ({ts_code})
- 体检总分: {report.get('total_score', 'N/A')}
- 风险等级: {report.get('risk_level', 'N/A')}
- 结论: {report.get('conclusion', 'N/A')}

### 五维度评分
1. 主营业务({report.get('main_business_score', 'N/A')}/100): {json.dumps(report.get('main_business_detail', {}), ensure_ascii=False)}
2. 利润含金量({report.get('profit_quality_score', 'N/A')}/100): {json.dumps(report.get('profit_quality_detail', {}), ensure_ascii=False)}
3. 毛利率({report.get('gross_margin_score', 'N/A')}/100): {json.dumps(report.get('gross_margin_detail', {}), ensure_ascii=False)}
4. 信披质量({report.get('disclosure_score', 'N/A')}/100): {json.dumps(report.get('disclosure_detail', {}), ensure_ascii=False)}
5. 供应链({report.get('supply_chain_score', 'N/A')}/100): {json.dumps(report.get('supply_chain_detail', {}), ensure_ascii=False)}

### 扣分项: {report.get('deduction', 0)}
### 预警列表: {json.dumps(report.get('alerts', []), ensure_ascii=False)}

## 分析要求
请深度分析该股票是否存在以下问题：

1. **财务造假嫌疑**：利润含金量低、毛利率异常、收入与现金流背离等红旗信号
2. **蹭概念讲故事**：主营业务不清晰、频繁跨界转型、蹭热点概念
3. **隐藏的供应链风险**：供应商集中度过高、关联交易异常
4. **信披问题**：信息披露不透明、频繁更正公告
5. **综合评估与建议**：给出明确的【关注】或【回避】判断

请用 Markdown 格式输出，用具体数据支撑你的分析。"""

        content = await self._call_llm(prompt)
        await self._save_insight("stock", ts_code, content, {
            "total_score": report.get("total_score"),
            "risk_level": report.get("risk_level"),
        })
        return {"content": content, "type": "stock", "ref_id": ts_code}

    # ============ 事件影响分析 ============

    async def analyze_event_impact(self, event_id: str) -> Dict[str, Any]:
        """评估事件对A股的短期和中期影响"""
        from app.services.calendar_service import event_service

        event = await event_service.get_event_by_id(event_id)
        if not event:
            return {"error": f"事件 {event_id} 不存在"}

        # 获取宏观环境背景
        from app.services.calendar_service import macro_service
        macro_score = await macro_service.get_latest_score()
        macro_brief = ""
        if macro_score:
            macro_brief = f"宏观评分{macro_score.get('total_score')}，等级{macro_score.get('level')}"

        prompt = f"""你是一位专业的市场事件分析师。请基于以下事件信息进行深度影响评估。

## 事件详情
- 标题: {event.get('title', '')}
- 类型: {event.get('event_type', '')}
- 日期: {event.get('event_date', '')}
- 影响方向: {event.get('impact_direction', '')}
- 影响强度: {event.get('impact_strength', '')}
- 影响板块: {json.dumps(event.get('affected_sectors', []), ensure_ascii=False)}
- 描述: {event.get('description', '')}
- 来源: {event.get('source', '')}

## 当前宏观环境
{macro_brief or '暂无宏观评分数据'}

## 分析要求
1. **短期影响（1-5个交易日）**：该事件对市场的即时影响
2. **中期影响（1-3个月）**：持续性影响和后续发酵可能
3. **受益板块**：明确列出可能受益的板块和逻辑
4. **受损板块**：可能受到负面影响的板块
5. **操作建议**：具体可执行的操作建议（包含时机、仓位、标的类型）
6. **风险提示**：需要关注的不确定因素

请用 Markdown 格式输出，给出明确的【利多】或【利空】判断。"""

        content = await self._call_llm(prompt)
        await self._save_insight("event", event_id, content, {
            "event_title": event.get("title"),
            "event_type": event.get("event_type"),
        })
        return {"content": content, "type": "event", "ref_id": event_id}

    # ============ 查询历史分析 ============

    async def get_insights(self, insight_type: str = None, ref_id: str = None, limit: int = 10) -> List[Dict]:
        """查询历史分析结果"""
        return await self._get_insights(insight_type, ref_id, limit)


# 全局实例
market_insight_service = MarketInsightService()
