const state = {
  books: [],
};

const els = {
  booksTbody: document.querySelector("#booksTbody"),
  refreshBtn: document.querySelector("#refreshBtn"),
  topSalesList: document.querySelector("#topSalesList"),
  lowStockList: document.querySelector("#lowStockList"),
  chatLog: document.querySelector("#chatLog"),
  agentForm: document.querySelector("#agentForm"),
  agentInput: document.querySelector("#agentInput"),
  shortcutButtons: document.querySelectorAll("[data-template]"),
  shortcutPanel: document.querySelector(".agent-shortcuts"),
  shortcutToggle: document.querySelector("#shortcutToggle"),
  shortcutExtraButtons: document.querySelectorAll(".shortcut-extra"),
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

async function loadBooks() {
  const payload = await requestJson("/api/books");
  state.books = payload.data || [];
  renderBooks();
}

async function loadStats() {
  const payload = await requestJson("/api/stats");
  renderTopSales(payload.data.top_sales || []);
  renderLowStock(payload.data.low_stock || []);
}

function renderBooks() {
  if (!state.books.length) {
    els.booksTbody.innerHTML = `<tr><td colspan="6" class="empty">暂无数据</td></tr>`;
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
        </tr>
      `,
    )
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
  }
}

els.refreshBtn.addEventListener("click", loadAll);
els.agentForm.addEventListener("submit", sendAgentMessage);
els.shortcutButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const templates = {
      query: "查询《》",
      add: "添加图书《》，库存 本，价格为，分类为，作者为",
      purchase: "给《》进货  本",
      sale: "卖出《》 本",
      lowStock: "查询库存少于 10 本的书",
      topSales: "统计销量最高的 5 本书",
      stockIncrease: "把《》的库存增加  本",
      stockDecrease: "把《》的库存减少  本",
      stockSet: "把《》的库存设置为  本",
      changePrice: "把《》的价格改为 ",
      changeAuthor: "把《》的作者改为 ",
      changeCategory: "把《》的分类改为 ",
      renameBook: "把《》的书名改为《》",
      deleteBook: "删除《》",
    };
    const value = templates[button.dataset.template] || "";
    els.agentInput.value = value;
    els.agentInput.focus();
    placeCursorInTemplate(value);
  });
});
els.shortcutToggle.addEventListener("click", () => {
  animateShortcutLayout(() => {
    const expanded = els.shortcutToggle.getAttribute("aria-expanded") === "true";
    els.shortcutExtraButtons.forEach((button) => {
      button.hidden = expanded;
    });
    els.shortcutToggle.setAttribute("aria-expanded", String(!expanded));
    els.shortcutToggle.textContent = expanded ? "展开显示" : "折叠显示";
  });
});

function placeCursorInTemplate(value) {
  const titleEnd = value.indexOf("》");
  if (titleEnd > 0) {
    els.agentInput.setSelectionRange(titleEnd, titleEnd);
    return;
  }

  const doubleSpace = value.indexOf("  ");
  if (doubleSpace >= 0) {
    els.agentInput.setSelectionRange(doubleSpace + 1, doubleSpace + 1);
    return;
  }

  els.agentInput.setSelectionRange(value.length, value.length);
}

function animateShortcutLayout(updateLayout) {
  const before = shortcutRects();
  updateLayout();
  const after = shortcutRects();

  after.forEach((newRect, button) => {
    const oldRect = before.get(button);
    if (!oldRect) {
      button.animate(
        [
          { opacity: 0, transform: "translateY(-4px)" },
          { opacity: 1, transform: "translateY(0)" },
        ],
        { duration: 160, easing: "ease-out" },
      );
      return;
    }

    const dx = oldRect.left - newRect.left;
    const dy = oldRect.top - newRect.top;
    if (dx === 0 && dy === 0) return;

    button.animate(
      [
        { transform: `translate(${dx}px, ${dy}px)` },
        { transform: "translate(0, 0)" },
      ],
      { duration: 240, easing: "cubic-bezier(0.2, 0, 0, 1)" },
    );
  });
}

function shortcutRects() {
  const rects = new Map();
  els.shortcutPanel.querySelectorAll("button").forEach((button) => {
    if (!button.hidden) {
      rects.set(button, button.getBoundingClientRect());
    }
  });
  return rects;
}

appendMessage("agent", "你好，我可以帮你查询、添加、改库存、改价格、进货、销售、删除和做库存预警。");
loadAll().catch((error) => showToast(error.message));
