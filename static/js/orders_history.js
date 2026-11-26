(function () {
  "use strict";

  const searchInput = document.getElementById("searchInput");
  const searchBtn = document.getElementById("searchBtn");
  const clearSearchBtn = document.getElementById("clearSearchBtn");
  const deleteSelectedBtn = document.getElementById("deleteSelectedBtn");
  const selectAllCheckbox = document.getElementById("selectAllOrders");
  const ordersAlert = document.getElementById("ordersAlert");
  const tbody = document.getElementById("ordersTableBody");
  const modal = document.getElementById("orderModal");
  const modalTitle = document.getElementById("modalTitle");
  const modalBody = document.getElementById("modalBody");
  const closeModalBtn = document.getElementById("closeModalBtn");

  function getSelectedOrderIds() {
    return Array.from(tbody.querySelectorAll(".order-select-cb:checked")).map((cb) => cb.value);
  }

  function syncBulkDeleteButton() {
    const selected = getSelectedOrderIds();
    const allCbs = tbody.querySelectorAll(".order-select-cb");
    if (deleteSelectedBtn) {
      deleteSelectedBtn.classList.toggle("hidden", selected.length === 0);
      deleteSelectedBtn.textContent = `Delete Selected (${selected.length})`;
    }
    if (selectAllCheckbox) {
      selectAllCheckbox.checked = allCbs.length > 0 && selected.length === allCbs.length;
    }
  }

  function showOrdersAlert(type, message) {
    if (!ordersAlert) return;
    ordersAlert.className = `alert alert-${type}`;
    ordersAlert.textContent = message;
    ordersAlert.classList.remove("hidden");
  }

  function escapeHtml(val) {
    return String(val ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function renderTableRows(orders) {
    if (!orders.length) {
      tbody.innerHTML = `
        <tr>
          <td colspan="8" style="text-align:center;padding:28px;color:#6b7280;">
            No matching orders found.
          </td>
        </tr>`;
      syncBulkDeleteButton();
      return;
    }

    tbody.innerHTML = orders
      .map(
        (o) => `
      <tr>
        <td>
          <input type="checkbox" class="order-select-cb" value="${escapeHtml(o.order_id)}" aria-label="Select ${escapeHtml(o.order_id)}" />
        </td>
        <td><span class="order-id-pill">${escapeHtml(o.order_id)}</span></td>
        <td>
          <strong>${escapeHtml(o.customer_name)}</strong><br />
          <span class="hint">${escapeHtml(o.mobile_number || "No mobile")}</span>
        </td>
        <td>
          <strong>${escapeHtml(o.product_sku)}</strong><br />
          <span class="hint">${escapeHtml(o.product_type)} (Qty: ${escapeHtml(o.quantity)})</span>
        </td>
        <td>
          ${escapeHtml(o.metal_option)} (${escapeHtml(o.metal_tone)})<br />
          <span class="hint">${escapeHtml(o.size_or_closure)}</span>
        </td>
        <td>${escapeHtml(o.dispatch_date || "—")}</td>
        <td>${o.image_count} img &bull; ${o.video_count} vid</td>
        <td>
          <div style="display:flex;gap:6px;flex-wrap:wrap;">
            <button type="button" class="btn btn-outline view-order-btn" data-order-id="${escapeHtml(o.order_id)}">Details</button>
            <a href="/orders/${encodeURIComponent(o.order_id)}/pdf" class="btn btn-primary">PDF</a>
            <button type="button" class="btn btn-danger delete-order-btn" data-order-id="${escapeHtml(o.order_id)}">Delete</button>
          </div>
        </td>
      </tr>`
      )
      .join("");
    syncBulkDeleteButton();
  }

  async function runSearch(query) {
    const resp = await fetch(`/api/orders?q=${encodeURIComponent(query)}`);
    const data = await resp.json();
    renderTableRows(data.orders || []);
  }

  searchBtn.addEventListener("click", () => runSearch(searchInput.value.trim()));
  searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      runSearch(searchInput.value.trim());
    }
  });
  clearSearchBtn.addEventListener("click", () => {
    searchInput.value = "";
    runSearch("");
  });

  async function openOrderModal(orderId) {
    modalTitle.textContent = `Order ${orderId}`;
    modalBody.innerHTML = "<p>Loading order details...</p>";
    modal.classList.add("open");

    try {
      const resp = await fetch(`/api/orders/${encodeURIComponent(orderId)}`);
      if (!resp.ok) {
        modalBody.innerHTML = "<p>Unable to load order details.</p>";
        return;
      }
      const { order } = await resp.json();
      const item = order.item || {};
      const stones = item.stone_details || [];
      const media = order.media || [];

      const stonesHtml = stones.length
        ? `<table class="data-table" style="margin-top:8px;">
            <thead>
              <tr><th>Type</th><th>Shape</th><th>Size (mm)</th><th>Carat</th><th>Color</th><th>Qty</th></tr>
            </thead>
            <tbody>
              ${stones
                .map(
                  (s) => `
                <tr>
                  <td>${escapeHtml(s.stone_type || "—")}</td>
                  <td>${escapeHtml(s.shape || "—")}</td>
                  <td>${escapeHtml(s.size_mm || "—")}</td>
                  <td>${escapeHtml(s.carat_weight || "—")}</td>
                  <td>${escapeHtml(s.color || "—")}</td>
                  <td>${escapeHtml(s.quantity || "—")}</td>
                </tr>`
                )
                .join("")}
            </tbody>
          </table>`
        : `<p class="hint">No stones logged.</p>`;

      const mediaHtml = media.length
        ? `<ul style="padding-left:18px;margin:8px 0;">
            ${media
              .map((m) => {
                const fileName = (m.local_temp_path || "").split(/[\\/]/).pop() || m.media_type;
                const link = m.drive_view_link
                  ? `<a href="${escapeHtml(m.drive_view_link)}" target="_blank" rel="noopener">Open in Google Drive</a>`
                  : `<a href="/uploads/${encodeURIComponent(order.order_id)}/${encodeURIComponent(fileName)}" target="_blank" rel="noopener">Open Local File</a>`;
                return `<li><strong>${escapeHtml(m.media_type.toUpperCase())}</strong>: ${escapeHtml(fileName)} — ${link}</li>`;
              })
              .join("")}
          </ul>`
        : `<p class="hint">No media attached.</p>`;

      modalBody.innerHTML = `
        <div class="grid-2" style="margin-bottom:14px;">
          <div>
            <h3 style="margin:0 0 8px;color:#3F070C;font-size:14px;">Customer Info (Private Local Record)</h3>
            <p style="margin:4px 0;"><strong>Name:</strong> ${escapeHtml(order.customer_name)}</p>
            <p style="margin:4px 0;"><strong>Mobile:</strong> ${escapeHtml(order.mobile_number || "—")}</p>
            <p style="margin:4px 0;"><strong>Email:</strong> ${escapeHtml(order.email || "—")}</p>
            <p style="margin:4px 0;"><strong>Address:</strong> ${escapeHtml(order.living_address || "—")}</p>
            <p style="margin:4px 0;"><strong>Dispatch Date:</strong> ${escapeHtml(order.dispatch_date || "—")}</p>
          </div>
          <div>
            <h3 style="margin:0 0 8px;color:#3F070C;font-size:14px;">Product Specs</h3>
            <p style="margin:4px 0;"><strong>Type:</strong> ${escapeHtml(item.product_type)}</p>
            <p style="margin:4px 0;"><strong>SKU:</strong> ${escapeHtml(item.product_sku)} (Qty: ${escapeHtml(item.quantity)})</p>
            <p style="margin:4px 0;"><strong>Metal:</strong> ${escapeHtml(item.metal_option)} — ${escapeHtml(item.metal_tone)}</p>
            <p style="margin:4px 0;"><strong>Size / Closure:</strong> ${escapeHtml(item.size_or_closure)}</p>
            <p style="margin:4px 0;"><strong>Engraving:</strong> ${escapeHtml(item.engraving || "—")}</p>
            <p style="margin:4px 0;"><strong>Special Notes:</strong> ${escapeHtml(item.special_requirements || "—")}</p>
          </div>
        </div>
        <h3 style="margin:10px 0 4px;color:#3F070C;font-size:14px;">Stone Details</h3>
        ${stonesHtml}
        <h3 style="margin:14px 0 4px;color:#3F070C;font-size:14px;">Attached Media</h3>
        ${mediaHtml}
        <div class="form-actions" style="margin-top:16px;">
          <button type="button" class="btn btn-danger modal-delete-order-btn" data-order-id="${escapeHtml(order.order_id)}">Delete Order</button>
          <a href="/orders/${encodeURIComponent(order.order_id)}/pdf" class="btn btn-primary">Download Workshop PDF</a>
        </div>
      `;
    } catch (_err) {
      modalBody.innerHTML = "<p>Error fetching order details.</p>";
    }
  }

  async function deleteOrderById(orderId) {
    if (!orderId) return;
    const confirmed = window.confirm(
      `Delete order "${orderId}" and all its stored details? This cannot be undone.`
    );
    if (!confirmed) return;

    try {
      const resp = await fetch(`/api/orders/${encodeURIComponent(orderId)}`, {
        method: "DELETE"
      });
      const data = await resp.json();
      if (!resp.ok || !data.ok) {
        showOrdersAlert("error", data.error || `Failed to delete order "${orderId}".`);
        return;
      }
      modal.classList.remove("open");
      showOrdersAlert("success", `Order "${data.deleted_order_id}" has been deleted.`);
      await runSearch(searchInput.value.trim());
    } catch (err) {
      showOrdersAlert("error", `Error deleting order "${orderId}": ${err.message}`);
    }
  }

  tbody.addEventListener("click", (e) => {
    const viewBtn = e.target.closest(".view-order-btn");
    if (viewBtn) {
      openOrderModal(viewBtn.dataset.orderId);
      return;
    }
    const delBtn = e.target.closest(".delete-order-btn");
    if (delBtn) {
      deleteOrderById(delBtn.dataset.orderId);
    }
  });

  tbody.addEventListener("change", (e) => {
    if (e.target.classList.contains("order-select-cb")) {
      syncBulkDeleteButton();
    }
  });

  if (selectAllCheckbox) {
    selectAllCheckbox.addEventListener("change", () => {
      const checked = selectAllCheckbox.checked;
      tbody.querySelectorAll(".order-select-cb").forEach((cb) => {
        cb.checked = checked;
      });
      syncBulkDeleteButton();
    });
  }

  if (deleteSelectedBtn) {
    deleteSelectedBtn.addEventListener("click", async () => {
      const ids = getSelectedOrderIds();
      if (!ids.length) return;
      const confirmed = window.confirm(
        `Delete ${ids.length} selected stored order(s) and their local files? This cannot be undone.`
      );
      if (!confirmed) return;

      try {
        const resp = await fetch("/api/orders/bulk-delete", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ order_ids: ids })
        });
        const data = await resp.json();
        if (!resp.ok || !data.ok) {
          showOrdersAlert("error", data.error || "Failed to delete selected orders.");
          return;
        }
        showOrdersAlert("success", `Deleted ${data.count} stored order(s).`);
        await runSearch(searchInput.value.trim());
      } catch (err) {
        showOrdersAlert("error", `Error deleting selected orders: ${err.message}`);
      }
    });
  }

  modalBody.addEventListener("click", (e) => {
    const delBtn = e.target.closest(".modal-delete-order-btn");
    if (delBtn) {
      deleteOrderById(delBtn.dataset.orderId);
    }
  });

  closeModalBtn.addEventListener("click", () => modal.classList.remove("open"));
  modal.addEventListener("click", (e) => {
    if (e.target === modal) {
      modal.classList.remove("open");
    }
  });
})();
