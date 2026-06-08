from __future__ import annotations

from typing import Any

from database import get_conn, row_to_dict, rows_to_dicts


def ok(message: str, data: Any = None) -> dict:
    return {"success": True, "message": message, "data": data}


def fail(message: str, data: Any = None) -> dict:
    return {"success": False, "message": message, "data": data}


def _resolve_book(conn, book_id: int | None = None, title: str | None = None) -> dict | None:
    if book_id:
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return row_to_dict(row)

    if not title:
        return None

    exact = conn.execute("SELECT * FROM books WHERE title = ?", (title.strip(),)).fetchone()
    if exact:
        return row_to_dict(exact)

    fuzzy_rows = conn.execute(
        "SELECT * FROM books WHERE title LIKE ? ORDER BY id LIMIT 2",
        (f"%{title.strip()}%",),
    ).fetchall()
    if len(fuzzy_rows) == 1:
        return row_to_dict(fuzzy_rows[0])
    return None


def add_book(
    title: str,
    price: float,
    stock: int,
    author: str = "",
    category: str = "",
) -> dict:
    title = (title or "").strip()
    if not title:
        return fail("书名不能为空")
    if price < 0 or stock < 0:
        return fail("价格和库存不能为负数")

    try:
        with get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO books (title, author, category, price, stock)
                VALUES (?, ?, ?, ?, ?)
                """,
                (title, author.strip(), category.strip(), float(price), int(stock)),
            )
            book = conn.execute("SELECT * FROM books WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return ok(f"已添加《{title}》", row_to_dict(book))
    except Exception as exc:
        if "UNIQUE" in str(exc).upper():
            return fail(f"《{title}》已经存在，可以改用修改库存或编辑图书")
        return fail(f"添加失败：{exc}")


def list_books(keyword: str = "", low_stock: int | None = None) -> dict:
    params: list[Any] = []
    clauses: list[str] = []

    if keyword:
        clauses.append("(b.title LIKE ? OR b.author LIKE ? OR b.category LIKE ?)")
        pattern = f"%{keyword.strip()}%"
        params.extend([pattern, pattern, pattern])

    if low_stock is not None:
        clauses.append("b.stock < ?")
        params.append(int(low_stock))

    sql = """
        SELECT
            b.*,
            COALESCE(SUM(s.quantity), 0) AS sold_quantity,
            COALESCE(SUM(s.total_price), 0) AS sales_amount
        FROM books b
        LEFT JOIN sales s ON s.book_id = b.id
    """
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " GROUP BY b.id ORDER BY b.id DESC"

    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return ok("查询成功", rows_to_dicts(rows))


def update_book(
    book_id: int,
    title: str,
    price: float,
    stock: int,
    author: str = "",
    category: str = "",
) -> dict:
    title = (title or "").strip()
    if not title:
        return fail("书名不能为空")
    if price < 0 or stock < 0:
        return fail("价格和库存不能为负数")

    try:
        with get_conn() as conn:
            exists = _resolve_book(conn, book_id=book_id)
            if not exists:
                return fail("没有找到要修改的图书")
            conn.execute(
                """
                UPDATE books
                SET title = ?, author = ?, category = ?, price = ?, stock = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (title, author.strip(), category.strip(), float(price), int(stock), int(book_id)),
            )
            book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return ok(f"已修改《{title}》", row_to_dict(book))
    except Exception as exc:
        if "UNIQUE" in str(exc).upper():
            return fail(f"《{title}》已经存在，不能重复命名")
        return fail(f"修改失败：{exc}")


def update_book_info(
    title: str,
    new_title: str | None = None,
    price: float | None = None,
    stock: int | None = None,
    author: str | None = None,
    category: str | None = None,
) -> dict:
    if all(value is None for value in [new_title, price, stock, author, category]):
        return fail("请说明要修改书名、价格、作者或分类中的哪一项")

    with get_conn() as conn:
        book = _resolve_book(conn, title=title)
        if not book:
            return fail("没有找到要修改的图书")

        updated_title = (new_title or book["title"]).strip()
        updated_author = book["author"] if author is None else author.strip()
        updated_category = book["category"] if category is None else category.strip()
        updated_price = book["price"] if price is None else float(price)
        updated_stock = book["stock"] if stock is None else int(stock)

    return update_book(
        book_id=book["id"],
        title=updated_title,
        author=updated_author,
        category=updated_category,
        price=updated_price,
        stock=updated_stock,
    )


def delete_book(book_id: int | None = None, title: str | None = None) -> dict:
    with get_conn() as conn:
        book = _resolve_book(conn, book_id=book_id, title=title)
        if not book:
            return fail("没有找到要删除的图书")
        conn.execute("DELETE FROM books WHERE id = ?", (book["id"],))
    return ok(f"已删除《{book['title']}》")


def update_stock(
    quantity: int,
    book_id: int | None = None,
    title: str | None = None,
    mode: str = "increase",
) -> dict:
    quantity = int(quantity)
    if quantity < 0:
        return fail("库存数量不能为负数")

    with get_conn() as conn:
        book = _resolve_book(conn, book_id=book_id, title=title)
        if not book:
            return fail("没有找到这本书")

        if mode == "set":
            new_stock = quantity
        elif mode == "decrease":
            new_stock = book["stock"] - quantity
        else:
            new_stock = book["stock"] + quantity

        if new_stock < 0:
            return fail(f"库存不足，当前《{book['title']}》只有 {book['stock']} 本")

        conn.execute(
            "UPDATE books SET stock = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_stock, book["id"]),
        )
        updated = conn.execute("SELECT * FROM books WHERE id = ?", (book["id"],)).fetchone()
    return ok(f"《{book['title']}》库存已更新为 {new_stock} 本", row_to_dict(updated))


def record_purchase(
    quantity: int,
    book_id: int | None = None,
    title: str | None = None,
    purchased_at: str | None = None,
    note: str = "",
) -> dict:
    quantity = int(quantity)
    if quantity <= 0:
        return fail("进货数量必须大于 0")

    with get_conn() as conn:
        book = _resolve_book(conn, book_id=book_id, title=title)
        if not book:
            return fail("没有找到这本书，进货前请先添加图书")

        if purchased_at:
            conn.execute(
                "INSERT INTO purchases (book_id, quantity, purchased_at, note) VALUES (?, ?, ?, ?)",
                (book["id"], quantity, purchased_at, note),
            )
        else:
            conn.execute(
                "INSERT INTO purchases (book_id, quantity, note) VALUES (?, ?, ?)",
                (book["id"], quantity, note),
            )
        new_stock = book["stock"] + quantity
        conn.execute(
            "UPDATE books SET stock = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_stock, book["id"]),
        )
        updated = conn.execute("SELECT * FROM books WHERE id = ?", (book["id"],)).fetchone()
    return ok(f"已记录《{book['title']}》进货 {quantity} 本，当前库存 {new_stock} 本", row_to_dict(updated))


def record_purchases_batch(items: list[dict]) -> dict:
    if not items:
        return fail("请提供要进货的图书和数量")

    with get_conn() as conn:
        resolved = []
        for item in items:
            quantity = int(item.get("quantity") or 0)
            if quantity <= 0:
                return fail("进货数量必须大于 0")

            book = _resolve_book(conn, book_id=item.get("book_id"), title=item.get("title"))
            if not book:
                return fail(f"没有找到《{item.get('title', '')}》，进货前请先添加图书")
            resolved.append((book, quantity))

        messages = []
        updated_rows = []
        for book, quantity in resolved:
            conn.execute(
                "INSERT INTO purchases (book_id, quantity, note) VALUES (?, ?, ?)",
                (book["id"], quantity, "Agent 批量进货"),
            )
            new_stock = book["stock"] + quantity
            conn.execute(
                "UPDATE books SET stock = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_stock, book["id"]),
            )
            updated = conn.execute("SELECT * FROM books WHERE id = ?", (book["id"],)).fetchone()
            updated_rows.append(row_to_dict(updated))
            messages.append(f"《{book['title']}》进货 {quantity} 本，当前库存 {new_stock} 本")

    return ok("已批量记录进货：" + "；".join(messages), updated_rows)


def record_sale(
    quantity: int,
    book_id: int | None = None,
    title: str | None = None,
    sold_at: str | None = None,
) -> dict:
    quantity = int(quantity)
    if quantity <= 0:
        return fail("销售数量必须大于 0")

    with get_conn() as conn:
        book = _resolve_book(conn, book_id=book_id, title=title)
        if not book:
            return fail("没有找到这本书")
        if book["stock"] < quantity:
            return fail(f"库存不足，当前《{book['title']}》只有 {book['stock']} 本")

        total_price = round(float(book["price"]) * quantity, 2)
        if sold_at:
            conn.execute(
                """
                INSERT INTO sales (book_id, quantity, unit_price, total_price, sold_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (book["id"], quantity, book["price"], total_price, sold_at),
            )
        else:
            conn.execute(
                """
                INSERT INTO sales (book_id, quantity, unit_price, total_price)
                VALUES (?, ?, ?, ?)
                """,
                (book["id"], quantity, book["price"], total_price),
            )
        new_stock = book["stock"] - quantity
        conn.execute(
            "UPDATE books SET stock = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_stock, book["id"]),
        )
        updated = conn.execute("SELECT * FROM books WHERE id = ?", (book["id"],)).fetchone()
    return ok(
        f"已卖出《{book['title']}》{quantity} 本，销售额 {total_price:.2f} 元，剩余库存 {new_stock} 本",
        row_to_dict(updated),
    )


def record_sales_batch(items: list[dict]) -> dict:
    if not items:
        return fail("请提供要销售的图书和数量")

    with get_conn() as conn:
        resolved = []
        for item in items:
            quantity = int(item.get("quantity") or 0)
            if quantity <= 0:
                return fail("销售数量必须大于 0")

            book = _resolve_book(conn, book_id=item.get("book_id"), title=item.get("title"))
            if not book:
                return fail(f"没有找到《{item.get('title', '')}》")
            if book["stock"] < quantity:
                return fail(f"库存不足，当前《{book['title']}》只有 {book['stock']} 本")
            resolved.append((book, quantity))

        messages = []
        updated_rows = []
        for book, quantity in resolved:
            total_price = round(float(book["price"]) * quantity, 2)
            new_stock = book["stock"] - quantity
            conn.execute(
                """
                INSERT INTO sales (book_id, quantity, unit_price, total_price)
                VALUES (?, ?, ?, ?)
                """,
                (book["id"], quantity, book["price"], total_price),
            )
            conn.execute(
                "UPDATE books SET stock = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_stock, book["id"]),
            )
            updated = conn.execute("SELECT * FROM books WHERE id = ?", (book["id"],)).fetchone()
            updated_rows.append(row_to_dict(updated))
            messages.append(f"《{book['title']}》{quantity} 本，销售额 {total_price:.2f} 元，剩余库存 {new_stock} 本")

    return ok("已批量记录销售：" + "；".join(messages), updated_rows)


def low_stock_alert(threshold: int = 10) -> dict:
    threshold = int(threshold)
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
                b.*,
                COALESCE(SUM(s.quantity), 0) AS sold_quantity,
                COALESCE(SUM(s.total_price), 0) AS sales_amount
            FROM books b
            LEFT JOIN sales s ON s.book_id = b.id
            WHERE b.stock < ?
            GROUP BY b.id
            ORDER BY b.stock ASC, b.id DESC
            """,
            (threshold,),
        ).fetchall()
    return ok(f"库存少于 {threshold} 本的图书共有 {len(rows)} 本", rows_to_dicts(rows))


def top_sales(limit: int = 5) -> dict:
    limit = int(limit)
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
                b.id,
                b.title,
                b.author,
                b.category,
                b.stock,
                COALESCE(SUM(s.quantity), 0) AS sold_quantity,
                COALESCE(SUM(s.total_price), 0) AS sales_amount
            FROM books b
            LEFT JOIN sales s ON s.book_id = b.id
            GROUP BY b.id
            ORDER BY sold_quantity DESC, sales_amount DESC, b.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return ok(f"销量最高的 {limit} 本书", rows_to_dicts(rows))


def dashboard_stats() -> dict:
    with get_conn() as conn:
        stats = conn.execute(
            """
            SELECT
                COUNT(*) AS book_count,
                COALESCE(SUM(stock), 0) AS total_stock,
                COALESCE(SUM(price * stock), 0) AS stock_value
            FROM books
            """
        ).fetchone()
        sales = conn.execute(
            """
            SELECT
                COALESCE(SUM(quantity), 0) AS sold_quantity,
                COALESCE(SUM(total_price), 0) AS sales_amount
            FROM sales
            """
        ).fetchone()
    data = row_to_dict(stats)
    data.update(row_to_dict(sales))
    return ok("统计成功", data)
