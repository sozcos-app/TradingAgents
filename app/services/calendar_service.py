"""
交易日历 - 服务层
"""

import logging

from typing import List, Dict, Any, Optional
from datetime import datetime
from bson import ObjectId

from app.core.database import get_mongo_db
from app.services.macro_data_fetcher import MacroDataFetcher
from app.services.macro_score_engine import MacroScoreEngine
from app.services.industry_fetcher import IndustryFetcher
from app.services.industry_score_engine import IndustryScoreEngine
from app.services.market_indicator_fetcher import MarketIndicatorFetcher
from app.services.divergence_detector import DivergenceDetector
from app.services.stock_health_fetcher import StockHealthFetcher
from app.services.stock_health_score_engine import StockHealthScoreEngine
from app.services.event_fetcher import EventFetcher
from app.services.event_impact_evaluator import EventImpactEvaluator
from app.services.trade_calendar import trade_calendar

logger = logging.getLogger("calendar_service")


class MacroDataService:
    """宏观感知服务"""

    def __init__(self):
        self.db = None
        self.fetcher = MacroDataFetcher()
        self.score_engine = MacroScoreEngine()

    async def _get_db(self):
        if self.db is None:
            self.db = get_mongo_db()
        return self.db

    async def _save_indicators(self, indicators: List[Dict[str, Any]]) -> int:
        """将指标数据入库，按 indicator_name+date 去重"""
        if not indicators:
            return 0
        db = await self._get_db()
        collection = db["macro_indicators"]
        saved = 0
        for item in indicators:
            query = {
                "indicator_name": item["indicator_name"],
                "date": item["date"],
            }
            update = {
                "$set": {
                    "value": item["value"],
                    "unit": item.get("unit", ""),
                    "source": item.get("source", ""),
                    "year_on_year": item.get("year_on_year"),
                    "month_on_month": item.get("month_on_month"),
                    "updated_at": datetime.utcnow(),
                },
                "$setOnInsert": {
                    "score": None,
                    "created_at": datetime.utcnow(),
                },
            }
            result = await collection.update_one(query, update, upsert=True)
            if result.upserted_id or result.modified_count > 0:
                saved += 1
        return saved

    async def fetch_indicators(self, names: Optional[List[str]] = None) -> Dict[str, int]:
        """批量采集宏观指标，返回 {指标名: 新增记录数}"""
        all_data = await self.fetcher.fetch_all()
        results = {}
        for indicator_name, data_list in all_data.items():
            # 如果指定了采集范围，跳过不需要的
            if names and indicator_name not in names:
                continue
            saved = await self._save_indicators(data_list)
            results[indicator_name] = saved
            logger.info(f"📊 {indicator_name}: 采集 {len(data_list)} 条, 入库 {saved} 条")
        return results

    async def get_latest_indicators(self) -> List[Dict[str, Any]]:
        """获取每个指标最新一条"""
        db = await self._get_db()
        collection = db["macro_indicators"]

        # 获取所有不同的指标名
        names = await collection.distinct("indicator_name")
        results = []
        for name in names:
            doc = await collection.find_one(
                {"indicator_name": name},
                sort=[("date", -1)]
            )
            if doc:
                doc["id"] = str(doc.pop("_id"))
                results.append(doc)
        return results

    async def get_indicator_history(
        self, name: str, start: str = None, end: str = None,
        page: int = 1, page_size: int = 20
    ) -> Dict[str, Any]:
        """查询指标历史数据"""
        db = await self._get_db()
        collection = db["macro_indicators"]

        query = {"indicator_name": name}
        if start:
            query["date"] = {"$gte": datetime.fromisoformat(start)}
        if end:
            if "date" in query:
                query["date"]["$lte"] = datetime.fromisoformat(end)
            else:
                query["date"] = {"$lte": datetime.fromisoformat(end)}

        total = await collection.count_documents(query)
        cursor = collection.find(query).sort("date", -1).skip((page - 1) * page_size).limit(page_size)
        items = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            items.append(doc)

        return {"total": total, "page": page, "page_size": page_size, "items": items}

    async def calculate_score(self) -> Dict[str, Any]:
        """计算宏观评分"""
        db = await self._get_db()
        collection = db["macro_indicators"]

        # 1. 从 DB 获取每个指标最新值
        names = ["PMI", "CPI", "PPI", "M2", "社融存量同比", "DR007", "北向资金"]
        indicators = {}
        for name in names:
            doc = await collection.find_one({"indicator_name": name}, sort=[("date", -1)])
            if doc and doc.get("value") is not None:
                indicators[name] = doc["value"]

        if not indicators:
            return {"total_score": 0, "level": "数据不足", "details": {}, "alerts": []}

        # 2. 调用评分引擎
        result = self.score_engine.calculate(indicators)
        result["date"] = datetime.utcnow().isoformat()

        # 3. 存入 macro_scores 集合
        scores_collection = db["macro_scores"]
        score_doc = {
            "total_score": result["total_score"],
            "level": result["level"],
            "details": result["details"],
            "alerts": result["alerts"],
            "date": datetime.utcnow(),
            "created_at": datetime.utcnow(),
        }
        await scores_collection.insert_one(score_doc)
        score_doc["id"] = str(score_doc.pop("_id"))

        logger.info(f"📊 宏观评分: {result['total_score']}分 - {result['level']}")
        return score_doc

    async def get_latest_score(self) -> Optional[Dict[str, Any]]:
        """获取最新评分"""
        db = await self._get_db()
        collection = db["macro_scores"]
        doc = await collection.find_one(sort=[("date", -1)])
        if doc:
            doc["id"] = str(doc.pop("_id"))
        return doc

    async def get_score_history(self, start: str = None, end: str = None) -> List[Dict[str, Any]]:
        """获取评分历史"""
        db = await self._get_db()
        collection = db["macro_scores"]

        query = {}
        if start:
            query["date"] = {"$gte": datetime.fromisoformat(start)}
        if end:
            if "date" in query:
                query["date"]["$lte"] = datetime.fromisoformat(end)
            else:
                query["date"] = {"$lte": datetime.fromisoformat(end)}

        cursor = collection.find(query).sort("date", -1).limit(100)
        results = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            results.append(doc)
        return results


class IndustryProsperityService:
    """行业景气服务"""

    def __init__(self):
        self.db = None
        self.fetcher = IndustryFetcher()
        self.score_engine = IndustryScoreEngine()

    async def _get_db(self):
        if self.db is None:
            self.db = get_mongo_db()
        return self.db

    async def get_ranking(self) -> List[Dict[str, Any]]:
        """获取行业景气排名"""
        db = await self._get_db()
        collection = db["industry_prosperity"]

        # 获取最新一批评分
        latest = await collection.find_one(sort=[("date", -1)])
        if not latest:
            return []

        cursor = collection.find({"date": latest["date"]}).sort("score", -1)
        results = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            results.append(doc)
        return results

    async def get_detail(self, industry_name: str) -> Optional[Dict[str, Any]]:
        """获取单行业详情"""
        db = await self._get_db()
        collection = db["industry_prosperity"]
        doc = await collection.find_one({"industry_name": industry_name}, sort=[("date", -1)])
        if doc:
            doc["id"] = str(doc.pop("_id"))
        return doc

    async def refresh_and_score(self) -> Dict[str, Any]:
        """刷新行业数据并重新评分"""
        db = await self._get_db()
        collection = db["industry_prosperity"]

        sectors = await self.fetcher.fetch_sector_ranking()
        if not sectors:
            return {"error": "采集板块数据失败", "detail": "AKShare 接口调用失败"}

        result = {}
        now = datetime.utcnow()

        for sector in sectors:
            scored = self.score_engine.quick_score_from_market(sector)
            scored.update({
                "industry_name": sector["industry_name"],
                "date": now,
                "created_at": now,
                "updated_at": now,
            })
            existing = await collection.find_one({"industry_name": sector["industry_name"], "date": now})
            if existing:
                await collection.update_one({"_id": existing["_id"]}, {"$set": scored})
            else:
                await collection.insert_one(scored)

            result[sector["industry_name"]] = scored["score"]

        logger.info(f"📊 行业评分刷新完成，共 {len(result)} 个行业")
        return result

    async def calculate_score(self, industry: str) -> Dict[str, Any]:
        """计算行业评分（快速版，基于市场数据）"""
        db = await self._get_db()

        # 从行业板块数据中查找
        collection = db["industry_prosperity"]
        doc = await collection.find_one({"industry_name": industry}, sort=[("date", -1)])
        if not doc:
            return {"error": f"未找到行业 {industry} 的数据"}

        result = self.score_engine.quick_score_from_market(doc)
        result["industry_name"] = industry
        result["date"] = datetime.utcnow().isoformat()

        # 更新已有记录或新建
        update_doc = {
            "industry_name": industry,
            "inventory_cycle": result.get("inventory_cycle", "-"),
            "inventory_score": result.get("inventory_score", 0),
            "profit_trend": result.get("profit_trend", "-"),
            "profit_score": result.get("profit_score", 0),
            "demand_growth": result.get("demand_growth", "-"),
            "demand_score": result.get("demand_score", 0),
            "capital_flow": result.get("capital_flow", "-"),
            "capital_score": result.get("capital_score", 0),
            "policy_support": result.get("policy_support", "-"),
            "policy_score": result.get("policy_score", 0),
            "score": result["score"],
            "suggestion": result["suggestion"],
            "catalysts": result.get("catalysts", []),
            "is_quick": True,
            "updated_at": datetime.utcnow(),
        }

        if doc:
            await collection.update_one({"_id": doc["_id"]}, {"$set": update_doc})
            update_doc["id"] = str(doc["_id"])
        else:
            update_doc["date"] = datetime.utcnow()
            update_doc["created_at"] = datetime.utcnow()
            result_doc = await collection.insert_one(update_doc)
            update_doc["id"] = str(result_doc)

        logger.info(f"📊 行业评分: {industry} - {result['score']}分 ({result['suggestion']})")
        return update_doc

    async def get_history(self, industry_name: str, start: str = None, end: str = None) -> List[Dict[str, Any]]:
        """获取单行业评分历史"""
        db = await self._get_db()
        collection = db["industry_prosperity"]

        query = {"industry_name": industry_name}
        if start:
            query["date"] = {"$gte": datetime.fromisoformat(start)}
        if end:
            if "date" in query:
                query["date"]["$lte"] = datetime.fromisoformat(end)
            else:
                query["date"] = {"$lte": datetime.fromisoformat(end)}

        cursor = collection.find(query).sort("date", -1).limit(50)
        results = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            results.append(doc)
        return results

    async def get_inventory_cycle_map(self) -> List[Dict[str, Any]]:
        """获取库存周期象限图数据"""
        db = await self._get_db()
        collection = db["industry_prosperity"]

        # 获取最新一批行业数据
        latest = await collection.find_one(sort=[("date", -1)])
        if not latest:
            return []

        cursor = collection.find({"date": latest["date"]})
        results = []
        async for doc in cursor:
            # 获取库存周期相关信息
            inv_cycle = doc.get("inventory_cycle", "-")
            inv_score = doc.get("inventory_score", 0)
            change_pct = doc.get("change_pct", 0)
            turnover = doc.get("turnover_rate", 0)

            results.append({
                "industry_name": doc.get("industry_name", ""),
                "phase": inv_cycle,
                "inventory_score": inv_score,
                "change_pct": change_pct,
                "turnover_rate": turnover,
                "score": doc.get("score", 0),
                "suggestion": doc.get("suggestion", "-"),
            })
        return results

    async def refresh_full_score(self) -> Dict[str, Any]:
        """全维度数据采集并完整评分"""
        db = await self._get_db()
        collection = db["industry_prosperity"]

        # 采集全维度数据
        all_data = await self.fetcher.fetch_all_dimensions()

        # 合并各维度数据到行业维度
        industries = {}
        for sector in all_data.get("sector_ranking", []):
            name = sector["industry_name"]
            industries[name] = {
                "change_pct": sector.get("change_pct", 0),
                "turnover_rate": sector.get("turnover_rate", 0),
                "up_count": sector.get("up_count", 0),
                "down_count": sector.get("down_count", 0),
            }

        # 合并库存周期
        for inv in all_data.get("inventory_cycle", []):
            name = inv.get("industry_name", "")
            if name in industries:
                industries[name]["inventory_yoy"] = inv.get("inventory_yoy")
                industries[name]["ppi_yoy"] = inv.get("ppi_yoy")

        # 合并盈利
        for prof in all_data.get("profitability", []):
            name = prof.get("industry_name", "")
            if name in industries:
                industries[name]["roe"] = prof.get("roe")
                industries[name]["margin"] = prof.get("margin")
                industries[name]["trend"] = prof.get("trend", "unknown")

        # 合并需求
        for dem in all_data.get("demand", []):
            name = dem.get("industry_name", "")
            if name in industries:
                industries[name]["sales_yoy"] = dem.get("sales_yoy")

        # 合并资金流向
        for mf in all_data.get("moneyflow", []):
            name = mf.get("industry_name", "")
            if name in industries:
                industries[name]["net_pct"] = mf.get("net_pct")

        # 合并政策
        for pol in all_data.get("policy", []):
            name = pol.get("industry_name", "")
            if name in industries:
                industries[name]["policy_count"] = pol.get("policy_count", 0)
                industries[name]["policy_level"] = pol.get("policy_level", "unknown")

        # 逐行业评分
        now = datetime.utcnow()
        scored_results = {}
        for name, dim_data in industries.items():
            scored = self.score_engine.full_score_with_details(dim_data)
            scored.update({
                "industry_name": name,
                "change_pct": dim_data.get("change_pct", 0),
                "turnover_rate": dim_data.get("turnover_rate", 0),
                "up_count": dim_data.get("up_count", 0),
                "down_count": dim_data.get("down_count", 0),
                "date": now,
                "created_at": now,
                "updated_at": now,
            })
            # 入库
            existing = await collection.find_one({"industry_name": name, "date": now})
            if existing:
                await collection.update_one({"_id": existing["_id"]}, {"$set": scored})
            else:
                await collection.insert_one(scored)
            scored_results[name] = scored["score"]

        logger.info(f"📊 全维度行业评分完成，共 {len(scored_results)} 个行业")
        return scored_results


class StockHealthService:
    """个股体检服务"""

    def __init__(self):
        self.db = None
        self.fetcher = StockHealthFetcher()
        self.score_engine = StockHealthScoreEngine()

    async def _get_db(self):
        if self.db is None:
            self.db = get_mongo_db()
        return self.db

    async def check_stock(self, ts_code: str) -> Dict[str, Any]:
        """对单只股票进行体检"""
        db = await self._get_db()
        collection = db["stock_health_checks"]

        # 1. 采集数据
        data = await self.fetcher.fetch_all(ts_code)
        basic = data.get("basic", {})

        # 2. 评分
        result = self.score_engine.calculate(data)

        # 3. 组装报告
        report = {
            "ts_code": ts_code,
            "stock_name": basic.get("stock_name", ""),
            "main_business_score": result["main_business_score"],
            "main_business_detail": result["main_business_detail"],
            "profit_quality_score": result["profit_quality_score"],
            "profit_quality_detail": result["profit_quality_detail"],
            "gross_margin_score": result["gross_margin_score"],
            "gross_margin_detail": result["gross_margin_detail"],
            "disclosure_score": result["disclosure_score"],
            "disclosure_detail": result["disclosure_detail"],
            "supply_chain_score": result["supply_chain_score"],
            "supply_chain_detail": result["supply_chain_detail"],
            "deduction": result["deduction"],
            "total_score": result["total_score"],
            "risk_level": result["risk_level"],
            "conclusion": result["conclusion"],
            "alerts": result["alerts"],
            "date": datetime.utcnow(),
            "created_at": datetime.utcnow(),
        }

        # 4. 入库
        await collection.insert_one(report.copy())
        report["id"] = str(report.pop("_id", ""))

        logger.info(f"📋 个股体检: {ts_code} - {result['total_score']}分 ({result['conclusion']})")
        return report

    async def get_report(self, ts_code: str) -> Optional[Dict[str, Any]]:
        """获取最近一次体检报告"""
        db = await self._get_db()
        collection = db["stock_health_checks"]
        doc = await collection.find_one({"ts_code": ts_code}, sort=[("date", -1)])
        if doc:
            doc["id"] = str(doc.pop("_id"))
        return doc

    async def get_alerts(self, ts_code: str) -> List[Dict[str, Any]]:
        """获取预警信息"""
        report = await self.get_report(ts_code)
        if report:
            return report.get("alerts", [])
        return []

    async def get_history(self, ts_code: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """获取体检历史"""
        db = await self._get_db()
        collection = db["stock_health_checks"]

        query = {"ts_code": ts_code}
        total = await collection.count_documents(query)
        cursor = collection.find(query).sort("date", -1).skip((page - 1) * page_size).limit(page_size)
        items = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            items.append(doc)

        return {"total": total, "page": page, "page_size": page_size, "items": items}


class MarketEventService:
    """市场事件服务"""

    def __init__(self):
        self.db = None
        self.fetcher = EventFetcher()
        self.evaluator = EventImpactEvaluator()

    async def _get_db(self):
        if self.db is None:
            self.db = get_mongo_db()
        return self.db

    async def fetch_events(self, start: str, end: str) -> Dict[str, Any]:
        """自动采集事件并入库"""
        db = await self._get_db()
        collection = db["market_events"]

        result = await self.fetcher.fetch_all(start, end)
        events = result.get("events", [])

        now = datetime.utcnow()
        saved = 0
        for evt in events:
            evt_dt = evt.get("event_date")
            if not isinstance(evt_dt, datetime):
                continue
            query = {"title": evt["title"], "event_date": evt_dt}
            update = {k: v for k, v in evt.items() if k != "_id"}
            update["updated_at"] = now
            existing = await collection.find_one(query)
            if existing:
                await collection.update_one({"_id": existing["_id"]}, {"$set": update})
                saved += 1
            else:
                update["created_at"] = now
                await collection.insert_one(update)
                saved += 1

        logger.info(f"📅 事件采集完成: 获取 {len(events)}, 入库 {saved}")
        return {"total": len(events), "saved": saved, "breakdown": result.get("results", {})}

    async def get_trade_days_api(self, start: str, end: str) -> List[str]:
        """获取交易日列表"""
        from datetime import date as date_type
        s = date_type.fromisoformat(start)
        e = date_type.fromisoformat(end)
        days = trade_calendar.get_trade_days(s, e)
        return [d.isoformat() for d in days]

    async def get_events(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """查询事件列表"""
        db = await self._get_db()
        collection = db["market_events"]

        mongo_query = {}
        if query.get("start_date"):
            mongo_query["event_date"] = {"$gte": datetime.fromisoformat(query["start_date"])}
        if query.get("end_date"):
            if "event_date" in mongo_query:
                mongo_query["event_date"]["$lte"] = datetime.fromisoformat(query["end_date"])
            else:
                mongo_query["event_date"] = {"$lte": datetime.fromisoformat(query["end_date"])}
        if query.get("event_type"):
            mongo_query["event_type"] = query["event_type"]
        if query.get("impact_direction"):
            mongo_query["impact_direction"] = query["impact_direction"]
        if query.get("keyword"):
            mongo_query["title"] = {"$regex": query["keyword"], "$options": "i"}

        page = query.get("page", 1)
        page_size = query.get("page_size", 20)

        total = await collection.count_documents(mongo_query)
        cursor = collection.find(mongo_query).sort("event_date", -1).skip((page - 1) * page_size).limit(page_size)
        items = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            items.append(doc)

        return {"total": total, "page": page, "page_size": page_size, "items": items}

    async def get_upcoming(self, days: int = 7) -> List[Dict[str, Any]]:
        """获取即将到来的事件"""
        from datetime import timedelta
        db = await self._get_db()
        collection = db["market_events"]

        now = datetime.utcnow()
        end = now + timedelta(days=days)

        cursor = collection.find({
            "event_date": {"$gte": now, "$lte": end}
        }).sort("event_date", 1)

        results = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            results.append(doc)
        return results

    async def create_event(self, data: Dict[str, Any], created_by: str = "manual") -> str:
        """创建事件"""
        db = await self._get_db()
        collection = db["market_events"]

        doc = {
            **data,
            "event_date": datetime.fromisoformat(data["event_date"]) if isinstance(data["event_date"], str) else data["event_date"],
            "is_auto": False,
            "created_by": created_by,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        result = await collection.insert_one(doc)
        return str(result.inserted_id)

    async def update_event(self, event_id: str, data: Dict[str, Any]) -> bool:
        """更新事件"""
        db = await self._get_db()
        collection = db["market_events"]

        update_doc = {"updated_at": datetime.utcnow()}
        for k, v in data.items():
            if v is not None:
                if k == "event_date" and isinstance(v, str):
                    update_doc[k] = datetime.fromisoformat(v)
                else:
                    update_doc[k] = v

        result = await collection.update_one(
            {"_id": ObjectId(event_id)},
            {"$set": update_doc}
        )
        return result.modified_count > 0

    async def delete_event(self, event_id: str) -> bool:
        """删除事件"""
        db = await self._get_db()
        collection = db["market_events"]
        result = await collection.delete_one({"_id": ObjectId(event_id)})
        return result.deleted_count > 0

    async def get_event_by_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取事件"""
        db = await self._get_db()
        collection = db["market_events"]
        doc = await collection.find_one({"_id": ObjectId(event_id)})
        if doc:
            doc["id"] = str(doc.pop("_id"))
        return doc


class MarketIndicatorService:
    """二级市场指标服务"""

    def __init__(self):
        self.db = None
        self.fetcher = MarketIndicatorFetcher()
        self.detector = DivergenceDetector()

    async def _get_db(self):
        if self.db is None:
            self.db = get_mongo_db()
        return self.db

    async def _save_indicators(self, indicators: List[Dict[str, Any]]) -> int:
        """将二级市场指标入库"""
        if not indicators:
            return 0
        db = await self._get_db()
        collection = db["market_indicators"]
        saved = 0
        for item in indicators:
            # 按 indicator_type + date 去重
            query = {
                "indicator_type": item["indicator_type"],
                "date": item["date"],
            }
            # 板块排名允许同一日期同一类型多条 (sector_name 不同)
            if item["indicator_type"] == "sector_ranking":
                query["sector_name"] = item.get("sector_name", "")
            update = {
                "$set": {k: v for k, v in item.items() if k != "_id"},
                "$setOnInsert": {"created_at": datetime.utcnow()},
            }
            result = await collection.update_one(query, update, upsert=True)
            if result.upserted_id or result.modified_count > 0:
                saved += 1
        return saved

    async def fetch_all_indicators(self, types: Optional[List[str]] = None) -> Dict[str, int]:
        """采集二级市场指标"""
        all_data = await self.fetcher.fetch_all()
        results = {}
        for indicator_type, data_list in all_data.items():
            if types and indicator_type not in types:
                continue
            saved = await self._save_indicators(data_list)
            results[indicator_type] = saved
            logger.info(f"📈 {indicator_type}: 采集 {len(data_list)} 条, 入库 {saved} 条")
        return results

    async def get_latest_overview(self) -> Dict[str, Any]:
        """获取二级市场指标概览 (各类型最新一条)"""
        db = await self._get_db()
        collection = db["market_indicators"]

        overview = {}
        # 逐类型取最新
        for indicator_type in ["advance_decline", "limit_stats", "volume", "turnover", "margin_trading"]:
            doc = await collection.find_one(
                {"indicator_type": indicator_type},
                sort=[("date", -1)]
            )
            if doc:
                doc["id"] = str(doc.pop("_id"))
                overview[indicator_type] = doc

        # 板块排名取最新一批
        latest_sector = await collection.find_one(
            {"indicator_type": "sector_ranking"},
            sort=[("date", -1)]
        )
        if latest_sector:
            cursor = collection.find({
                "indicator_type": "sector_ranking",
                "date": latest_sector["date"]
            }).sort("change_pct", -1).limit(50)
            sectors = []
            async for doc in cursor:
                doc["id"] = str(doc.pop("_id"))
                sectors.append(doc)
            overview["sector_ranking"] = sectors

        return overview

    async def get_history(
        self, indicator_type: str = None, start: str = None, end: str = None,
        page: int = 1, page_size: int = 20
    ) -> Dict[str, Any]:
        """查询二级市场指标历史"""
        db = await self._get_db()
        collection = db["market_indicators"]

        query = {}
        if indicator_type:
            query["indicator_type"] = indicator_type
        if start:
            query["date"] = {"$gte": datetime.fromisoformat(start)}
        if end:
            if "date" in query:
                query["date"]["$lte"] = datetime.fromisoformat(end)
            else:
                query["date"] = {"$lte": datetime.fromisoformat(end)}

        total = await collection.count_documents(query)
        cursor = collection.find(query).sort("date", -1).skip((page - 1) * page_size).limit(page_size)
        items = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            items.append(doc)

        return {"total": total, "page": page, "page_size": page_size, "items": items}

    async def detect_divergence(self) -> Dict[str, Any]:
        """执行背离检测"""
        db = await self._get_db()

        # 获取最新宏观评分
        scores_collection = db["macro_scores"]
        macro_doc = await scores_collection.find_one(sort=[("date", -1)])
        if not macro_doc:
            return {"judgment": "数据不足", "description": "暂无宏观评分数据，无法进行背离检测", "action": "请先采集宏观数据并计算评分", "signals": []}

        macro_score = macro_doc.get("total_score", 0)

        # 判断宏观趋势
        recent_scores = await scores_collection.find().sort("date", -1).limit(3).to_list(3)
        macro_direction = "stable"
        if len(recent_scores) >= 2:
            prev_score = recent_scores[1].get("total_score", 0)
            if macro_score > prev_score + 2:
                macro_direction = "up"
            elif macro_score < prev_score - 2:
                macro_direction = "down"

        # 获取最新市场数据
        collection = db["market_indicators"]

        # 成交额
        volume_doc = await collection.find_one({"indicator_type": "volume"}, sort=[("date", -1)])
        market_data = {}
        if volume_doc:
            market_data["total_amount"] = volume_doc.get("total_amount")

        # 涨跌家数
        ad_doc = await collection.find_one({"indicator_type": "advance_decline"}, sort=[("date", -1)])
        if ad_doc:
            market_data["up_count"] = ad_doc.get("up_count")
            market_data["down_count"] = ad_doc.get("down_count")

        # 涨停跌停
        limit_doc = await collection.find_one({"indicator_type": "limit_stats"}, sort=[("date", -1)])
        if limit_doc:
            market_data["limit_up_count"] = limit_doc.get("limit_up_count")

        # 获取近5天成交额和涨停数历史
        volume_history = await collection.find({"indicator_type": "volume"}).sort("date", -1).limit(5).to_list(5)
        limit_history = await collection.find({"indicator_type": "limit_stats"}).sort("date", -1).limit(5).to_list(5)

        # 合并历史
        market_history = []
        for vh in volume_history:
            market_history.append({"total_amount": vh.get("total_amount"), "date": str(vh.get("date", ""))})
        for lh in limit_history:
            existing = next((h for h in market_history if h.get("date") == str(lh.get("date", ""))), None)
            if existing:
                existing["limit_up_count"] = lh.get("limit_up_count")
            else:
                market_history.append({"limit_up_count": lh.get("limit_up_count"), "date": str(lh.get("date", ""))})

        market_history.sort(key=lambda x: x.get("date", ""), reverse=False)

        # 执行检测
        signals = self.detector.detect_macro_market_divergence(macro_score, macro_direction, market_data, market_history)
        result = self.detector.detect_lie_opportunity(signals)
        result["macro_score"] = macro_score
        result["macro_direction"] = macro_direction

        # 保存检测结果
        divergence_collection = db["divergence_signals"]
        save_doc = {
            "judgment": result["judgment"],
            "description": result["description"],
            "action": result["action"],
            "signals": result.get("signals", []),
            "lie_count": result.get("lie_count", 0),
            "opportunity_count": result.get("opportunity_count", 0),
            "macro_score": macro_score,
            "date": datetime.utcnow(),
            "created_at": datetime.utcnow(),
        }
        await divergence_collection.insert_one(save_doc)
        save_doc["id"] = str(save_doc.pop("_id"))
        result["id"] = save_doc["id"]

        logger.info(f"🔍 背离检测完成: {result['judgment']} (宏观{macro_score}分, 方向{macro_direction})")
        return result

    async def get_latest_divergence(self) -> Optional[Dict[str, Any]]:
        """获取最新背离检测结果"""
        db = await self._get_db()
        collection = db["divergence_signals"]
        doc = await collection.find_one(sort=[("date", -1)])
        if doc:
            doc["id"] = str(doc.pop("_id"))
        return doc
macro_service = MacroDataService()
industry_service = IndustryProsperityService()
stock_health_service = StockHealthService()
event_service = MarketEventService()
market_indicator_service = MarketIndicatorService()
