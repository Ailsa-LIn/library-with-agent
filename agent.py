from __future__ import annotations

import json
import os
import re
from typing import Any

try:
    import requests
except ImportError:  # DeepSeek is optional; local rules still work without requests.
    requests = None

import tools


LAST_DEEPSEEK_ERROR = ""


TOOL_DESCRIPTIONS = {
    "add_book": "添加图书，参数：title, price, stock, author, category",
    "search_book": "查询图书，参数：keyword",
    "update_book_info": "修改图书信息，参数：title, new_title, price, author, category",
    "delete_book": "删除图书，参数：title 或 book_id",
    "update_stock": "修改库存，参数：title 或 book_id, quantity, mode(increase/decrease/set)",
    "record_purchase": "记录进货，参数：title 或 book_id, quantity",
    "multi_record_purchase": "批量记录进货，参数：actions，数组元素包含 title 和 quantity",
    "record_sale": "记录销售，参数：title 或 book_id, quantity",
    "multi_record_sale": "批量记录销售，参数：actions，数组元素包含 title 和 quantity",
    "low_stock_alert": "库存预警，参数：threshold",
    "top_sales": "销量统计，参数：limit",
}


def handle_agent_message(message: str) -> dict:
    command = (message or "").strip()
    if not command:
        return tools.fail("请输入要执行的指令")

    multi_parsed = _parse_multi_command(command)
    deepseek_parsed = None if multi_parsed else _parse_with_deepseek(command)
    parsed = multi_parsed or deepseek_parsed or _parse_locally(command)
    result = _run_tool(parsed)
    result["agent"] = {
        "input": command,
        "intent": parsed.get("intent", "unknown"),
        "params": parsed.get("params", {}),
        "source": parsed.get("source", "local_rules"),
    }
    if os.getenv("DEEPSEEK_API_KEY") and parsed.get("source") != "deepseek":
        result["agent"]["deepseek_error"] = LAST_DEEPSEEK_ERROR or "DeepSeek 未返回可用 JSON，已退回本地规则"
    return result


def _parse_with_deepseek(command: str) -> dict | None:
    global LAST_DEEPSEEK_ERROR
    LAST_DEEPSEEK_ERROR = ""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        LAST_DEEPSEEK_ERROR = "未设置 DEEPSEEK_API_KEY"
        return None
    if requests is None:
        LAST_DEEPSEEK_ERROR = "Python 环境未安装 requests，请运行 pip install -r requirements.txt"
        return None

    prompt = f"""
你是图书进销存系统的意图识别 Agent。只能返回 JSON，不能返回解释文字。
可用工具：
{json.dumps(TOOL_DESCRIPTIONS, ensure_ascii=False, indent=2)}

用户输入：{command}

返回格式：
{{"intent":"工具名","params":{{...}}}}
如果无法识别，intent 返回 "unknown"。
"""
    try:
        response = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
            },
            timeout=15,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()
        parsed = _extract_json(content)
        if parsed:
            parsed["source"] = "deepseek"
        else:
            LAST_DEEPSEEK_ERROR = f"DeepSeek 返回内容不是 JSON：{content[:80]}"
        return parsed
    except Exception as exc:
        LAST_DEEPSEEK_ERROR = str(exc)
        return None


def _extract_json(text: str) -> dict | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


def _parse_locally(command: str) -> dict:
    title = _extract_title(command)
    numbers = [int(num) for num in re.findall(r"\d+", command)]

    if re.search(r"删除|删掉|移除|下架", command):
        return {
            "intent": "delete_book",
            "params": {"title": title},
            "source": "local_rules",
        }

    if re.search(r"库存.*(少于|低于|不足)|库存预警|低库存", command):
        return {
            "intent": "low_stock_alert",
            "params": {"threshold": numbers[0] if numbers else 10},
            "source": "local_rules",
        }

    if re.search(r"还剩多少|剩多少|还有多少|库存多少|多少库存|有多少本|有几本", command):
        return {
            "intent": "search_book",
            "params": {"keyword": title or _cleanup_keyword(command)},
            "source": "local_rules",
        }

    if re.search(r"销量.*(最高|排行|前)|销售.*(最高|排行|前)|卖得最好", command):
        return {
            "intent": "top_sales",
            "params": {"limit": numbers[0] if numbers else 5},
            "source": "local_rules",
        }

    if re.search(r"添加|新增|录入|加入", command):
        return {
            "intent": "add_book",
            "params": {
                "title": title,
                "price": _extract_float(command, r"(?:价格|售价)\s*[:：为是]?\s*(\d+(?:\.\d+)?)") or 0,
                "stock": _extract_int(command, r"(?:库存|数量)\s*[:：为是]?\s*(\d+)") or 0,
                "author": _extract_text_after(command, "作者") or "",
                "category": _extract_text_after(command, "分类") or "",
            },
            "source": "local_rules",
        }

    if re.search(r"价格|售价|作者|分类|类别|书名|名称|改名", command) and re.search(r"修改|改为|改成|设置|设为|调整|更新|改名", command):
        params: dict[str, Any] = {"title": title}
        new_title = _extract_new_title(command)
        price = _extract_float(command, r"(?:价格|售价)\s*(?:改为|改成|设置为|设为|调整为|到|[:：为是])?\s*(\d+(?:\.\d+)?)")
        author = _extract_text_after(command, "作者")
        category = _extract_text_after(command, "分类") or _extract_text_after(command, "类别")
        if new_title:
            params["new_title"] = new_title
        if price is not None:
            params["price"] = price
        if author:
            params["author"] = author
        if category:
            params["category"] = category
        return {
            "intent": "update_book_info",
            "params": params,
            "source": "local_rules",
        }

    if re.search(r"卖出|售出|销售|记录销售", command):
        return {
            "intent": "record_sale",
            "params": {"title": title, "quantity": numbers[-1] if numbers else 1},
            "source": "local_rules",
        }

    if re.search(r"进货|入库|补货|采购", command):
        return {
            "intent": "record_purchase",
            "params": {"title": title, "quantity": numbers[-1] if numbers else 0},
            "source": "local_rules",
        }

    if re.search(r"增加", command) and re.search(r"库存|本|增加", command):
        return {
            "intent": "update_stock",
            "params": {"title": title, "quantity": numbers[-1] if numbers else 0, "mode": "increase"},
            "source": "local_rules",
        }

    if re.search(r"减少|扣减|调低", command):
        return {
            "intent": "update_stock",
            "params": {"title": title, "quantity": numbers[-1] if numbers else 0, "mode": "decrease"},
            "source": "local_rules",
        }

    if re.search(r"设置|改成|调整为|设为", command) and re.search(r"库存", command):
        return {
            "intent": "update_stock",
            "params": {"title": title, "quantity": numbers[-1] if numbers else 0, "mode": "set"},
            "source": "local_rules",
        }

    if re.search(r"查询|查找|搜索|看看|显示", command):
        return {
            "intent": "search_book",
            "params": {"keyword": title or _cleanup_keyword(command)},
            "source": "local_rules",
        }

    return {"intent": "unknown", "params": {}, "source": "local_rules"}


def _parse_multi_command(command: str) -> dict | None:
    actions = _extract_book_quantity_pairs(command)
    if len(actions) < 2:
        return None

    if re.search(r"卖|售|销售|卖出|售出", command):
        return {
            "intent": "multi_record_sale",
            "params": {"actions": actions},
            "source": "local_multi_rules",
        }

    if re.search(r"进货|入库|补货|采购", command):
        return {
            "intent": "multi_record_purchase",
            "params": {"actions": actions},
            "source": "local_multi_rules",
        }

    return None


def _extract_book_quantity_pairs(command: str) -> list[dict]:
    actions: list[dict] = []
    seen: set[tuple[str, int]] = set()

    patterns = [
        r"(\d+)\s*本?\s*《([^》]+)》",
        r"《([^》]+)》\s*(\d+)\s*本",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, command):
            if match.group(1).isdigit():
                quantity = int(match.group(1))
                title = match.group(2).strip()
            else:
                title = match.group(1).strip()
                quantity = int(match.group(2))

            key = (title, quantity)
            if key not in seen:
                seen.add(key)
                actions.append({"title": title, "quantity": quantity})

    each_match = re.search(r"各\s*(\d+)\s*本", command)
    if not actions and each_match:
        quantity = int(each_match.group(1))
        for title in re.findall(r"《([^》]+)》", command):
            key = (title.strip(), quantity)
            if key not in seen:
                seen.add(key)
                actions.append({"title": title.strip(), "quantity": quantity})

    return actions


def _run_tool(parsed: dict) -> dict:
    intent = parsed.get("intent")
    params: dict[str, Any] = parsed.get("params") or {}

    if intent == "add_book":
        return tools.add_book(
            title=params.get("title", ""),
            price=float(params.get("price") or 0),
            stock=int(params.get("stock") or 0),
            author=params.get("author", ""),
            category=params.get("category", ""),
        )

    if intent == "search_book":
        return tools.list_books(keyword=params.get("keyword", ""))

    if intent == "update_book_info":
        return tools.update_book_info(
            title=params.get("title", ""),
            new_title=params.get("new_title"),
            price=params.get("price"),
            author=params.get("author"),
            category=params.get("category"),
        )

    if intent == "delete_book":
        return tools.delete_book(
            book_id=params.get("book_id"),
            title=params.get("title"),
        )

    if intent == "update_stock":
        return tools.update_stock(
            book_id=params.get("book_id"),
            title=params.get("title"),
            quantity=int(params.get("quantity") or 0),
            mode=params.get("mode", "increase"),
        )

    if intent == "record_sale":
        return tools.record_sale(
            book_id=params.get("book_id"),
            title=params.get("title"),
            quantity=int(params.get("quantity") or 1),
        )

    if intent == "multi_record_sale":
        return tools.record_sales_batch(params.get("actions") or [])

    if intent == "record_purchase":
        return tools.record_purchase(
            book_id=params.get("book_id"),
            title=params.get("title"),
            quantity=int(params.get("quantity") or 0),
        )

    if intent == "multi_record_purchase":
        return tools.record_purchases_batch(params.get("actions") or [])

    if intent == "low_stock_alert":
        return tools.low_stock_alert(int(params.get("threshold") or 10))

    if intent == "top_sales":
        return tools.top_sales(int(params.get("limit") or 5))

    return tools.fail("暂时没有识别出指令，可以试试：查询《数据结构》、添加一本《算法导论》价格 88 库存 20、把《数据结构》的价格改为 50、删除《算法导论》")


def _extract_title(command: str) -> str:
    bracket = re.search(r"《([^》]+)》", command)
    if bracket:
        return bracket.group(1).strip()

    patterns = [
        r"(?:添加|新增|录入|加入)一本?([\w\s+\-:：]+?)(?:，|,|价格|售价|库存|作者|分类|$)",
        r"(?:查询|查找|搜索|卖出|售出|销售|增加|减少|设置|修改|调整|删除|删掉|移除|下架)(?:一本?)?([\w\s+\-:：]+?)(?:，|,|价格|售价|库存|数量|\d|本|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, command)
        if match:
            return match.group(1).strip(" ：:，,")
    return ""


def _extract_new_title(command: str) -> str:
    titles = re.findall(r"《([^》]+)》", command)
    if len(titles) >= 2:
        return titles[1].strip()
    match = re.search(r"(?:书名|名称|改名)\s*(?:改为|改成|设置为|设为|叫|为)?\s*([^，,。；;\s]+)", command)
    return match.group(1).strip() if match else ""


def _extract_float(command: str, pattern: str) -> float | None:
    match = re.search(pattern, command)
    return float(match.group(1)) if match else None


def _extract_int(command: str, pattern: str) -> int | None:
    match = re.search(pattern, command)
    return int(match.group(1)) if match else None


def _extract_text_after(command: str, label: str) -> str | None:
    match = re.search(rf"{label}\s*(?:改为|改成|设置为|设为|调整为|[:：为是])?\s*([^，,。；;\s]+)", command)
    return match.group(1).strip() if match else None


def _cleanup_keyword(command: str) -> str:
    keyword = re.sub(r"查询|查找|搜索|看看|显示|还剩多少|剩多少|还有多少|库存多少|多少库存|有多少本|有几本|图书|书籍|书", "", command)
    return keyword.strip(" ：:，,。")
