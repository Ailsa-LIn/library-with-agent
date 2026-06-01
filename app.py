from __future__ import annotations

from flask import Flask, jsonify, render_template, request

import agent
from database import init_db
import tools


app = Flask(__name__)
init_db()


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/books")
def api_books():
    keyword = request.args.get("keyword", "")
    low_stock = request.args.get("low_stock")
    return jsonify(tools.list_books(keyword=keyword, low_stock=int(low_stock) if low_stock else None))


@app.post("/api/books")
def api_add_book():
    data = request.get_json(force=True)
    return jsonify(
        tools.add_book(
            title=data.get("title", ""),
            author=data.get("author", ""),
            category=data.get("category", ""),
            price=float(data.get("price") or 0),
            stock=int(data.get("stock") or 0),
        )
    )


@app.put("/api/books/<int:book_id>")
def api_update_book(book_id: int):
    data = request.get_json(force=True)
    return jsonify(
        tools.update_book(
            book_id=book_id,
            title=data.get("title", ""),
            author=data.get("author", ""),
            category=data.get("category", ""),
            price=float(data.get("price") or 0),
            stock=int(data.get("stock") or 0),
        )
    )


@app.delete("/api/books/<int:book_id>")
def api_delete_book(book_id: int):
    return jsonify(tools.delete_book(book_id))


@app.post("/api/stock")
def api_update_stock():
    data = request.get_json(force=True)
    return jsonify(
        tools.update_stock(
            book_id=data.get("book_id"),
            title=data.get("title"),
            quantity=int(data.get("quantity") or 0),
            mode=data.get("mode", "increase"),
        )
    )


@app.post("/api/purchases")
def api_record_purchase():
    data = request.get_json(force=True)
    return jsonify(
        tools.record_purchase(
            book_id=data.get("book_id"),
            title=data.get("title"),
            quantity=int(data.get("quantity") or 0),
            purchased_at=data.get("purchased_at"),
            note=data.get("note", ""),
        )
    )


@app.post("/api/sales")
def api_record_sale():
    data = request.get_json(force=True)
    return jsonify(
        tools.record_sale(
            book_id=data.get("book_id"),
            title=data.get("title"),
            quantity=int(data.get("quantity") or 0),
            sold_at=data.get("sold_at"),
        )
    )


@app.get("/api/stock/low")
def api_low_stock():
    threshold = int(request.args.get("threshold", 10))
    return jsonify(tools.low_stock_alert(threshold))


@app.get("/api/stats")
def api_stats():
    return jsonify(
        {
            "success": True,
            "message": "统计成功",
            "data": {
                "dashboard": tools.dashboard_stats()["data"],
                "top_sales": tools.top_sales(5)["data"],
                "low_stock": tools.low_stock_alert(10)["data"],
            },
        }
    )


@app.post("/api/agent")
def api_agent():
    data = request.get_json(force=True)
    return jsonify(agent.handle_agent_message(data.get("message", "")))


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
