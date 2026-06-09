"""巨潮资讯(cninfo.com.cn)公告搜索服务"""

import logging
from typing import List, Optional

import httpx

from app.schemas.dcf import CninfoAnnouncement, CninfoSearchResponse

logger = logging.getLogger("webapi")

# 巨潮资讯全文搜索接口
CNINFO_SEARCH_URL = "https://www.cninfo.com.cn/new/fulltextSearch/full"

# 巨潮搜索股票名称接口（用于获取 orgId 和股票名称）
CNINFO_SEARCH_STOCK_URL = "https://www.cninfo.com.cn/new/information/topSearch/query"

# 公告类型 category -> 搜索关键词
CATEGORY_KEYWORD_MAP = {
    "annual": "年度报告",
    "quarter1": "第一季度报告",
    "semi": "半年度报告",
    "quarter3": "第三季度报告",
}


def _extract_pure_code(stock_code: str) -> str:
    """从用户输入的股票代码中提取纯数字部分

    Examples:
        sz000977 -> 000977
        sh600000 -> 600000
        000977 -> 000977
    """
    code = stock_code.strip().lower()
    for prefix in ("sz", "sh", "bj"):
        if code.startswith(prefix):
            code = code[len(prefix):]
            break
    return code


class CninfoService:
    """巨潮资讯公告搜索服务"""

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json, text/plain, */*",
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": "https://www.cninfo.com.cn/new/fulltext",
                },
            )
            # 先 GET 一次获取 JSESSIONID cookie（fulltextSearch 接口需要 session）
            try:
                await self._client.get(CNINFO_SEARCH_URL)
            except Exception:
                pass
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _lookup_stock_name(self, pure_code: str) -> str:
        """通过巨潮搜索接口获取股票简称"""
        client = await self._get_client()
        try:
            resp = await client.post(
                CNINFO_SEARCH_STOCK_URL,
                data=f"keyWord={pure_code}&maxSecNum=3&maxListNum=3",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            results = resp.json()
            if isinstance(results, list):
                for item in results:
                    if item.get("code") == pure_code:
                        return item.get("zwjc", "")
        except Exception as e:
            logger.warning(f"查询股票名称失败: {e}")
        return ""

    async def _search_with_pagination(
        self, client: httpx.AsyncClient, searchkey: str, pure_code: str, max_items: int, max_pages: int = 5
    ) -> list:
        """带翻页的巨潮搜索，按 secCode 过滤，直到找够或翻完"""
        filtered: list = []
        for page_num in range(1, max_pages + 1):
            payload = {
                "searchkey": searchkey,
                "sdate": "",
                "edate": "",
                "isfulltext": "false",
                "sortName": "pubdate",
                "sortType": "desc",
                "pageNum": page_num,
                "pageSize": 100,
                "column": "szse",
                "tabName": "fulltext",
                "plate": "",
                "stock": "",
                "searchkeySecond": "",
                "category": "",
                "trade": "",
                "seDate": "",
                "sortfield": "pubdate",
                "sortfieldtype": "desc",
            }
            try:
                resp = await client.post(CNINFO_SEARCH_URL, data=payload)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.warning(f"巨潮搜索第{page_num}页失败: {e}")
                break

            raw_list = data.get("announcements", []) or []
            if not raw_list:
                break

            page_matched = [
                item for item in raw_list
                if (item.get("secCode") or "").strip() == pure_code
            ]
            filtered.extend(page_matched)
            if len(filtered) >= max_items:
                break

            total = data.get("totalAnnouncement", 0) or 0
            has_more = data.get("hasMore", False)
            if not has_more or page_num * 100 >= total:
                break

        return filtered

    async def search_announcements(
        self,
        stock_code: str,
        category: str = "annual",
        page: int = 1,
        page_size: int = 20,
    ) -> CninfoSearchResponse:
        """搜索巨潮资讯公告

        策略：fulltextSearch 全文搜索 + 后端按 secCode 过滤

        Args:
            stock_code: 股票代码，如 sz000977 或 000977
            category: 公告类型 annual/quarter1/semi/quarter3
            page: 页码
            page_size: 每页条数
        """
        pure_code = _extract_pure_code(stock_code)
        keyword = CATEGORY_KEYWORD_MAP.get(category, "年度报告")

        # 先查股票简称用于搜索
        stock_name = await self._lookup_stock_name(pure_code)
        client = await self._get_client()

        # 依次尝试两组 searchkey，每组最多翻 5 页
        search_keys = []
        if stock_name:
            search_keys.append(f"{stock_name} {keyword}")  # 组合搜索
        search_keys.append(keyword)  # 纯关键词兜底

        filtered: list = []
        for sk in search_keys:
            filtered = await self._search_with_pagination(client, sk, pure_code, page_size)
            if filtered:
                break

        # 截取到 page_size
        filtered = filtered[:page_size]

        announcements: List[CninfoAnnouncement] = []
        for item in filtered:
            adjunct_url = item.get("adjunctUrl", "") or ""
            sec_code = item.get("secCode", "") or ""

            # 巨潮返回的 announcementTime 是毫秒时间戳
            pub_ts = item.get("announcementTime")
            pub_date = ""
            if pub_ts:
                try:
                    from datetime import datetime
                    pub_date = datetime.fromtimestamp(int(pub_ts) / 1000).strftime("%Y-%m-%d")
                except Exception:
                    pub_date = str(pub_ts)

            # 清理 title 中的 <em> 标签
            title = (item.get("announcementTitle") or "").replace("<em>", "").replace("</em>", "")

            announcements.append(
                CninfoAnnouncement(
                    title=title,
                    announcement_id=str(item.get("announcementId", "")),
                    announcement_type=item.get("announcementTypeName") or "",
                    stock_code=pure_code,
                    sec_name=item.get("secName", "") or "",
                    sec_code=sec_code,
                    pub_date=pub_date,
                    adjunct_url=adjunct_url,
                    adjunct_size=item.get("adjunctSize", 0) or 0,
                    download_url=f"http://static.cninfo.com.cn/{adjunct_url}" if adjunct_url else "",
                )
            )

        return CninfoSearchResponse(total=len(announcements), announcements=announcements)


# 单例
cninfo_service = CninfoService()
