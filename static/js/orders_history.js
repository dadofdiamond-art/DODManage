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
            <a href="/orders/${encodeURIComponent(o.order_id)}/workpdf" class="btn btn-primary">Work PDF</a>
            <a href="/orders/${encodeURIComponent(o.order_id)}/ourpdf" class="btn btn-outline">Our PDF</a>
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
              <tr><th>Category</th><th>Type</th><th>Shape</th><th>Size (mm)</th><th>Carat</th><th>Color</th><th>Clarity</th><th>IGI Cert</th><th>Qty</th><th>Remark</th></tr>
            </thead>
            <tbody>
              ${stones
                .map(
                  (s) => `
                <tr>
                  <td>${escapeHtml(s.stone_category || "Center Stone")}</td>
                  <td>${escapeHtml(s.stone_type || "—")}</td>
                  <td>${escapeHtml(s.shape || "—")}</td>
                  <td>${escapeHtml(s.size_mm || "—")}</td>
                  <td>${escapeHtml(s.carat_weight || "—")}</td>
                  <td>${escapeHtml(s.color || "—")}</td>
                  <td>${escapeHtml(s.clarity || "—")}</td>
                  <td>${escapeHtml(s.igi_certificate || "—")}</td>
                  <td>${escapeHtml(s.quantity || "—")}</td>
                  <td>${escapeHtml(s.other_remark || "—")}</td>
                </tr>`
                )
                .join("")}
            </tbody>
          </table>`
        : `<p class="hint">No stones logged.</p>`;

      const imageMedia = media.filter((m) => m.media_type === "image");
      const imagePreviewsHtml = imageMedia.length
        ? `<div class="preview-grid" style="margin:8px 0 12px;">
            ${imageMedia
              .map((m, idx) => {
                const fileName = (m.local_temp_path || "").split(/[\\/]/).pop() || `image_${idx + 1}.jpg`;
                const localUrl = `/uploads/${encodeURIComponent(order.order_id)}/${encodeURIComponent(fileName)}`;
                const targetUrl = m.drive_view_link || localUrl;
                return `
                  <a href="${escapeHtml(targetUrl)}" target="_blank" rel="noopener" class="preview-item" style="text-decoration:none;color:inherit;" title="${escapeHtml(fileName)}">
                    <img src="${escapeHtml(localUrl)}" alt="${escapeHtml(fileName)}" style="width:100%;height:110px;object-fit:contain;background:#f9fafb;border-radius:4px;" />
                    <div style="font-size:11px;color:#4b5563;text-align:center;margin-top:4px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escapeHtml(fileName)}</div>
                  </a>`;
              })
              .join("")}
          </div>`
        : "";

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
            <p style="margin:4px 0;"><strong>Order Placing Date:</strong> ${escapeHtml(order.order_placing_date || "—")}</p>
            <p style="margin:4px 0;"><strong>Factory Receiving Date:</strong> ${escapeHtml(order.factory_receiving_date || "—")}</p>
            <p style="margin:4px 0;"><strong>Dispatch Date:</strong> ${escapeHtml(order.dispatch_date || "—")}</p>
          </div>
          <div>
            <h3 style="margin:0 0 8px;color:#3F070C;font-size:14px;">Product Specs</h3>
            <p style="margin:4px 0;"><strong>Type:</strong> ${escapeHtml(item.product_type)}</p>
            <p style="margin:4px 0;"><strong>SKU:</strong> ${escapeHtml(item.product_sku)} (Qty: ${escapeHtml(item.quantity)})</p>
            <p style="margin:4px 0;"><strong>Metal:</strong> ${escapeHtml(item.metal_option)} — ${escapeHtml(item.metal_tone)}</p>
            <p style="margin:4px 0;"><strong>Band / Prong / Basket Tone:</strong> ${escapeHtml(item.band_tone || "—")} / ${escapeHtml(item.prong_tone || "—")} / ${escapeHtml(item.basket_tone || "—")}</p>
            <p style="margin:4px 0;"><strong>CAD Image No.:</strong> ${escapeHtml(item.cad_image_no || "—")}</p>
            <p style="margin:4px 0;"><strong>Size / Closure:</strong> ${escapeHtml(item.size_or_closure)}</p>
            <p style="margin:4px 0;"><strong>Center Engraving:</strong> ${escapeHtml(item.engraving || "—")}</p>
            <p style="margin:4px 0;"><strong>Side Engraving:</strong> ${escapeHtml(item.side_engraving || "—")}</p>
            <p style="margin:4px 0;"><strong>Special Notes:</strong> ${escapeHtml(item.special_requirements || "—")}</p>
          </div>
        </div>
        <h3 style="margin:10px 0 4px;color:#3F070C;font-size:14px;">Stone Details</h3>
        ${stonesHtml}
        <h3 style="margin:14px 0 4px;color:#3F070C;font-size:14px;">Attached Media</h3>
        ${imagePreviewsHtml}
        ${mediaHtml}
        <div class="form-actions" style="margin-top:16px;">
          <button type="button" class="btn btn-outline modal-edit-order-btn" data-order-id="${escapeHtml(order.order_id)}">Edit Order</button>
          <button type="button" class="btn btn-danger modal-delete-order-btn" data-order-id="${escapeHtml(order.order_id)}">Delete Order</button>
          <a href="/orders/${encodeURIComponent(order.order_id)}/workpdf" class="btn btn-primary">Download Work PDF</a>
          <a href="/orders/${encodeURIComponent(order.order_id)}/ourpdf" class="btn btn-outline">Download Our PDF</a>
        </div>
      `;
      modalBody._currentOrder = order;
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

  function openEditOrderForm(order) {
    const item = order.item || {};
    const stones = item.stone_details || [];
    modalTitle.textContent = `Edit Order ${order.order_id}`;

    const renderEditStoneRow = (s, idx) => `
      <div class="stone-row" style="margin-bottom:10px;">
        <div class="stone-row-header">
          <span class="stone-row-title">Stone #${idx + 1}</span>
          <button type="button" class="btn btn-danger-ghost edit-remove-stone-btn">Remove</button>
        </div>
        <div class="stone-grid">
          <div class="field">
            <label>Position</label>
            <select class="edit-stone-category">
              <option value="Center Stone" ${(s.stone_category || "Center Stone") === "Center Stone" ? "selected" : ""}>Center Stone</option>
              <option value="Side Stone" ${s.stone_category === "Side Stone" ? "selected" : ""}>Side Stone</option>
            </select>
          </div>
          <div class="field"><label>Type</label><input type="text" class="edit-stone-type" value="${escapeHtml(s.stone_type || "")}" /></div>
          <div class="field"><label>Shape</label><input type="text" class="edit-stone-shape" value="${escapeHtml(s.shape || "")}" /></div>
          <div class="field"><label>Size (mm)</label><input type="text" class="edit-stone-size" value="${escapeHtml(s.size_mm || "")}" /></div>
          <div class="field"><label>Carat</label><input type="text" class="edit-stone-carat" value="${escapeHtml(s.carat_weight || "")}" /></div>
          <div class="field"><label>Color</label><input type="text" class="edit-stone-color" value="${escapeHtml(s.color || "")}" /></div>
          <div class="field"><label>Clarity</label><input type="text" class="edit-stone-clarity" value="${escapeHtml(s.clarity || "")}" /></div>
          <div class="field"><label>IGI Cert No.</label><input type="text" class="edit-stone-igi" value="${escapeHtml(s.igi_certificate || "")}" /></div>
          <div class="field"><label>Qty</label><input type="text" class="edit-stone-qty" value="${escapeHtml(s.quantity || "")}" /></div>
          <div class="field"><label>Other Remark</label><input type="text" class="edit-stone-remark" value="${escapeHtml(s.other_remark || "")}" /></div>
        </div>
      </div>`;

    modalBody.innerHTML = `
      <form id="editOrderForm">
        <div class="grid-3" style="margin-bottom:12px;">
          <div class="field"><label>Customer Name *</label><input type="text" id="edit_customer_name" value="${escapeHtml(order.customer_name)}" required /></div>
          <div class="field"><label>Mobile</label><input type="text" id="edit_mobile_number" value="${escapeHtml(order.mobile_number || "")}" /></div>
          <div class="field"><label>Email</label><input type="email" id="edit_email" value="${escapeHtml(order.email || "")}" /></div>
          <div class="field span-2"><label>Address</label><input type="text" id="edit_living_address" value="${escapeHtml(order.living_address || "")}" /></div>
          <div class="field"><label>Dispatch Date</label><input type="date" id="edit_dispatch_date" value="${escapeHtml(order.dispatch_date || "")}" /></div>
          <div class="field"><label>Order Placing Date</label><input type="date" id="edit_order_placing_date" value="${escapeHtml(order.order_placing_date || "")}" /></div>
          <div class="field"><label>Factory Receiving Date</label><input type="date" id="edit_factory_receiving_date" value="${escapeHtml(order.factory_receiving_date || "")}" /></div>
        </div>
        <div class="grid-3" style="margin-bottom:12px;">
          <div class="field"><label>Product Type *</label><input type="text" id="edit_product_type" value="${escapeHtml(item.product_type || "")}" required /></div>
          <div class="field"><label>Product SKU *</label><input type="text" id="edit_product_sku" value="${escapeHtml(item.product_sku || "")}" required /></div>
          <div class="field"><label>Quantity *</label><input type="number" min="1" id="edit_quantity" value="${escapeHtml(item.quantity || 1)}" required /></div>
          <div class="field"><label>Metal Option *</label><input type="text" id="edit_metal_option" value="${escapeHtml(item.metal_option || "")}" required /></div>
          <div class="field"><label>Metal Tone *</label><input type="text" id="edit_metal_tone" value="${escapeHtml(item.metal_tone || "")}" required /></div>
          <div class="field"><label>Band Tone</label><input type="text" id="edit_band_tone" value="${escapeHtml(item.band_tone || "")}" /></div>
          <div class="field"><label>Prong Tone</label><input type="text" id="edit_prong_tone" value="${escapeHtml(item.prong_tone || "")}" /></div>
          <div class="field"><label>Basket Tone</label><input type="text" id="edit_basket_tone" value="${escapeHtml(item.basket_tone || "")}" /></div>
          <div class="field"><label>CAD Image No.</label><input type="text" id="edit_cad_image_no" value="${escapeHtml(item.cad_image_no || "")}" /></div>
          <div class="field"><label>Size / Closure *</label><input type="text" id="edit_size_or_closure" value="${escapeHtml(item.size_or_closure || "")}" required /></div>
          <div class="field"><label>Center Engraving</label><input type="text" id="edit_engraving" value="${escapeHtml(item.engraving || "")}" /></div>
          <div class="field"><label>Side Engraving</label><input type="text" id="edit_side_engraving" value="${escapeHtml(item.side_engraving || "")}" /></div>
          <div class="field span-3"><label>Special Requirements</label><textarea id="edit_special_requirements" rows="2">${escapeHtml(item.special_requirements || "")}</textarea></div>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;margin:10px 0 6px;">
          <h3 style="margin:0;color:#3F070C;font-size:14px;">Stones</h3>
          <button type="button" id="editAddStoneBtn" class="btn btn-outline">+ Add Stone</button>
        </div>
        <div id="editStonesContainer">${stones.map((s, i) => renderEditStoneRow(s, i)).join("")}</div>
        <div class="form-actions" style="margin-top:14px;">
          <button type="button" id="cancelEditOrderBtn" class="btn btn-outline">Cancel</button>
          <button type="submit" class="btn btn-primary">Save Changes &amp; Update PDF</button>
        </div>
      </form>
    `;

    const editStonesContainer = document.getElementById("editStonesContainer");
    document.getElementById("editAddStoneBtn").addEventListener("click", () => {
      const idx = editStonesContainer.querySelectorAll(".stone-row").length;
      editStonesContainer.insertAdjacentHTML("beforeend", renderEditStoneRow({}, idx));
    });
    editStonesContainer.addEventListener("click", (ev) => {
      const rmBtn = ev.target.closest(".edit-remove-stone-btn");
      if (rmBtn) rmBtn.closest(".stone-row").remove();
    });
    document.getElementById("cancelEditOrderBtn").addEventListener("click", () => {
      openOrderModal(order.order_id);
    });
    document.getElementById("editOrderForm").addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const updatedStones = Array.from(editStonesContainer.querySelectorAll(".stone-row")).map((r) => ({
        stone_category: r.querySelector(".edit-stone-category").value.trim(),
        stone_type: r.querySelector(".edit-stone-type").value.trim(),
        shape: r.querySelector(".edit-stone-shape").value.trim(),
        size_mm: r.querySelector(".edit-stone-size").value.trim(),
        carat_weight: r.querySelector(".edit-stone-carat").value.trim(),
        color: r.querySelector(".edit-stone-color").value.trim(),
        clarity: r.querySelector(".edit-stone-clarity").value.trim(),
        igi_certificate: r.querySelector(".edit-stone-igi").value.trim(),
        quantity: r.querySelector(".edit-stone-qty").value.trim(),
        other_remark: r.querySelector(".edit-stone-remark").value.trim()
      }));
      const body = {
        customer_name: document.getElementById("edit_customer_name").value.trim(),
        mobile_number: document.getElementById("edit_mobile_number").value.trim(),
        email: document.getElementById("edit_email").value.trim(),
        living_address: document.getElementById("edit_living_address").value.trim(),
        dispatch_date: document.getElementById("edit_dispatch_date").value.trim(),
        order_placing_date: document.getElementById("edit_order_placing_date").value.trim(),
        factory_receiving_date: document.getElementById("edit_factory_receiving_date").value.trim(),
        product_type: document.getElementById("edit_product_type").value.trim(),
        product_sku: document.getElementById("edit_product_sku").value.trim(),
        quantity: Number(document.getElementById("edit_quantity").value || 1),
        metal_option: document.getElementById("edit_metal_option").value.trim(),
        metal_tone: document.getElementById("edit_metal_tone").value.trim(),
        band_tone: document.getElementById("edit_band_tone").value.trim(),
        prong_tone: document.getElementById("edit_prong_tone").value.trim(),
        basket_tone: document.getElementById("edit_basket_tone").value.trim(),
        cad_image_no: document.getElementById("edit_cad_image_no").value.trim(),
        size_or_closure: document.getElementById("edit_size_or_closure").value.trim(),
        engraving: document.getElementById("edit_engraving").value.trim(),
        side_engraving: document.getElementById("edit_side_engraving").value.trim(),
        special_requirements: document.getElementById("edit_special_requirements").value.trim(),
        stone_details: updatedStones
      };
      const resp = await fetch(`/api/orders/${encodeURIComponent(order.order_id)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
      const data = await resp.json();
      if (!resp.ok || !data.ok) {
        showOrdersAlert("error", (data.errors || [data.error || "Failed to update order."]).join(" "));
        return;
      }
      showOrdersAlert("success", `Order "${order.order_id}" updated and PDF regenerated.`);
      await runSearch(searchInput.value.trim());
      await openOrderModal(order.order_id);
    });
  }

  modalBody.addEventListener("click", (e) => {
    const editBtn = e.target.closest(".modal-edit-order-btn");
    if (editBtn && modalBody._currentOrder) {
      openEditOrderForm(modalBody._currentOrder);
      return;
    }
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
