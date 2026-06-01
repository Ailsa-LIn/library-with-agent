const state = {
  books: [],
  searchKeyword: "",
};

const els = {
  bookCount: document.querySelector("#bookCount"),
  totalStock: document.querySelector("#totalStock"),
  soldQuantity: document.querySelector("#soldQuantity"),
  salesAmount: document.querySelector("#salesAmount"),
  booksTbody: document.querySelector("#booksTbody"),
  bookForm: document.querySelector("#bookForm"),
  bookId: document.querySelector("#bookId"),
  title: document.querySelector("#title"),
  author: document.querySelector("#author"),
  category: document.querySelector("#category"),
  price: document.querySelector("#price"),
  stock: document.querySelector("#stock"),
  saveBookBtn: document.querySelector("#saveBookBtn"),
  cancelEditBtn: document.querySelector("#cancelEditBtn"),
  searchInput: document.querySelector("#searchInput"),
  searchBtn: document.querySelector("#searchBtn"),
  lowStockBtn: document.querySelector("#lowStockBtn"),
  refreshBtn: document.querySelector("#refreshBtn"),
  tradeBook: document.querySelector("#tradeBook"),
  tradeQuantity: document.querySelector("#tradeQuantity"),
  purchaseBtn: document.querySelector("#purchaseBtn"),
  saleBtn: document.querySelector("#saleBtn"),
  topSalesList: document.querySelector("#topSalesList"),
  lowStockList: document.querySelector("#lowStockList"),
  chatLog: document.querySelector("#chatLog"),
  agentForm: document.querySelector("#agentForm"),
  agentInput: document.querySelector("#agentInput"),
  agentStatus: document.querySelector("#agentStatus"),
  toast: document.querySelector("#toast"),
};

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.message || "请求失败");
  }
  return payload;
}

function money(value) {
  return Number(value || 0).toFixed(2);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function showToast(message) {
  els.toast.textContent = message;
  els.toast.hidden = false;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => {
    els.toast.hidden = true;
  }, 2200);
}

async function loadAll() {
  await Promise.all([loadBooks(), loadStats()]);
}

async function loadBooks(options = {}) {
  const params = new URLSearchParams();
  if (options.lowStock) {
    params.set("low_stock", options.lowStock);
  } else if (state.searchKeyword) {
    params.set("keyword", state.searchKeyword);
  }

  const query = params.toString() ? `?${params}` : "";
  const payload = await requestJson(`/api/books${query}`);
  state.books = payload.data || [];
  renderBooks();
  renderTradeOptions();
}

async function loadStats() {
  const payload = await requestJson("/api/stats");
  const dashboard = payload.data.dashboard || {};
  els.bookCount.textContent = dashboard.book_count || 0;
  els.totalStock.textContent = dashboard.total_stock || 0;
  els.soldQuantity.textContent = dashboard.sold_quantity || 0;
  els.salesAmount.textContent = money(dashboard.sales_amount);
  renderTopSales(payload.data.top_sales || []);
  renderLowStock(payload.data.low_stock || []);
}

function renderBooks() {
  if (!state.books.length) {
    els.booksTbody.innerHTML = `<tr><td colspan="7" class="empty">暂无数据</td></tr>`;
    return;
  }

  els.booksTbody.innerHTML = state.books
    .map(
      (book) => `
        <tr>
          <td>${escapeHtml(book.title)}</td>
          <td>${escapeHtml(book.author || "-")}</td>
          <td>${escapeHtml(book.category || "-")}</td>
          <td>￥${money(book.price)}</td>
          <td><span class="stock-badge ${book.stock < 10 ? "low" : ""}">${book.stock}</span></td>
          <td>${book.sold_quantity || 0}</td>
          <td>
            <div class="row-actions">
              <button type="button" data-edit="${book.id}">编辑</button>
              <button type="button" class="delete" data-delete="${book.id}">删除</button>
            </div>
          </td>
        </tr>
      `,
    )
    .join("");
}

function renderTradeOptions() {
  els.tradeBook.innerHTML = state.books
    .map((book) => `<option value="${book.id}">${escapeHtml(book.title)}（库存 ${book.stock}）</option>`)
    .join("");
}

function renderTopSales(rows) {
  if (!rows.length) {
    els.topSalesList.innerHTML = `<li class="empty">暂无销售记录</li>`;
    return;
  }
  els.topSalesList.innerHTML = rows
    .map((row) => `<li>${escapeHtml(row.title)}：${row.sold_quantity} 本，￥${money(row.sales_amount)}</li>`)
    .join("");
}

function renderLowStock(rows) {
  if (!rows.length) {
    els.lowStockList.innerHTML = `<li class="empty">库存充足</li>`;
    return;
  }
  els.lowStockList.innerHTML = rows.map((row) => `<li>${escapeHtml(row.title)}：${row.stock} 本</li>`).join("");
}

function resetBookForm() {
  els.bookId.value = "";
  els.bookForm.reset();
  els.saveBookBtn.textContent = "添加图书";
  els.cancelEditBtn.hidden = true;
}

function fillBookForm(book) {
  els.bookId.value = book.id;
  els.title.value = book.title;
  els.author.value = book.author || "";
  els.category.value = book.category || "";
  els.price.value = book.price;
  els.stock.value = book.stock;
  els.saveBookBtn.textContent = "保存修改";
  els.cancelEditBtn.hidden = false;
  els.title.focus();
}

function bookPayload() {
  return {
    title: els.title.value.trim(),
    author: els.author.value.trim(),
    category: els.category.value.trim(),
    price: Number(els.price.value),
    stock: Number(els.stock.value),
  };
}

async function saveBook(event) {
  event.preventDefault();
  const id = els.bookId.value;
  const payload = bookPayload();
  const result = await requestJson(id ? `/api/books/${id}` : "/api/books", {
    method: id ? "PUT" : "POST",
    body: JSON.stringify(payload),
  });
  showToast(result.message);
  if (!result.success) return;
  resetBookForm();
  await loadAll();
}

async function deleteBook(id) {
  const book = state.books.find((item) => item.id === id);
  const title = book ? `《${book.title}》` : "这本书";
  if (!confirm(`确定删除${title}吗？`)) return;
  const result = await requestJson(`/api/books/${id}`, { method: "DELETE" });
  showToast(result.message);
  if (!result.success) return;
  await loadAll();
}

async function recordTrade(type) {
  const bookId = Number(els.tradeBook.value);
  const quantity = Number(els.tradeQuantity.value);
  if (!bookId || quantity <= 0) {
    showToast("请选择图书并输入有效数量");
    return;
  }

  const endpoint = type === "purchase" ? "/api/purchases" : "/api/sales";
  const result = await requestJson(endpoint, {
    method: "POST",
    body: JSON.stringify({ book_id: bookId, quantity }),
  });
  showToast(result.message);
  if (!result.success) return;
  await loadAll();
}

function appendMessage(role, html, failed = false) {
  const node = document.createElement("div");
  node.className = `message ${role}${failed ? " failed" : ""}`;
  node.innerHTML = html;
  els.chatLog.appendChild(node);
  els.chatLog.scrollTop = els.chatLog.scrollHeight;
}

function formatAgentData(data) {
  if (!data) return "";
  if (Array.isArray(data)) {
    if (!data.length) return "<small>没有匹配数据</small>";
    const items = data
      .slice(0, 6)
      .map((item) => {
        const stock = item.stock !== undefined ? `，库存 ${item.stock}` : "";
        const sold = item.sold_quantity !== undefined ? `，已售 ${item.sold_quantity}` : "";
        const price = item.price !== undefined ? `，价格 ￥${money(item.price)}` : "";
        return `<li>${escapeHtml(item.title || item.name || JSON.stringify(item))}${price}${stock}${sold}</li>`;
      })
      .join("");
    return `<ul>${items}</ul>`;
  }

  if (data.title) {
    const sold = data.sold_quantity !== undefined ? `，已售 ${data.sold_quantity}` : "";
    return `<small>《${escapeHtml(data.title)}》 价格 ￥${money(data.price)}，库存 ${data.stock}${sold}</small>`;
  }

  return `<small>${escapeHtml(JSON.stringify(data))}</small>`;
}

async function sendAgentMessage(event) {
  event.preventDefault();
  const message = els.agentInput.value.trim();
  if (!message) return;

  appendMessage("user", escapeHtml(message));
  els.agentInput.value = "";
  els.agentStatus.textContent = "处理中";

  try {
    const result = await requestJson("/api/agent", {
      method: "POST",
      body: JSON.stringify({ message }),
    });
    const intent = result.agent?.intent ? `<small>调用工具：${escapeHtml(result.agent.intent)}</small>` : "";
    appendMessage("agent", `${escapeHtml(result.message)}${formatAgentData(result.data)}${intent}`, !result.success);
    await loadAll();
  } catch (error) {
    appendMessage("agent", escapeHtml(error.message), true);
  } finally {
    els.agentStatus.textContent = "就绪";
  }
}

els.bookForm.addEventListener("submit", saveBook);
els.cancelEditBtn.addEventListener("click", resetBookForm);
els.searchBtn.addEventListener("click", async () => {
  state.searchKeyword = els.searchInput.value.trim();
  await loadBooks();
});
els.lowStockBtn.addEventListener("click", async () => {
  state.searchKeyword = "";
  els.searchInput.value = "";
  await loadBooks({ lowStock: 10 });
});
els.refreshBtn.addEventListener("click", loadAll);
els.purchaseBtn.addEventListener("click", () => recordTrade("purchase"));
els.saleBtn.addEventListener("click", () => recordTrade("sale"));
els.agentForm.addEventListener("submit", sendAgentMessage);

els.booksTbody.addEventListener("click", (event) => {
  const editId = event.target.dataset.edit;
  const deleteId = event.target.dataset.delete;
  if (editId) {
    const book = state.books.find((item) => item.id === Number(editId));
    if (book) fillBookForm(book);
  }
  if (deleteId) {
    deleteBook(Number(deleteId));
  }
});

document.querySelectorAll("[data-example]").forEach((button) => {
  button.addEventListener("click", () => {
    els.agentInput.value = button.dataset.example;
    els.agentInput.focus();
  });
});

appendMessage("agent", "你好，我可以帮你查询、添加、改库存、记录销售和做库存预警。");
loadAll().catch((error) => showToast(error.message));
