(function () {
  "use strict";

  const config = window.DOD_CONFIG || {
    maxImages: 10,
    maxVideos: 2,
    maxVideoMb: 200,
    stoneTypes: ["Lab Diamond", "Moissanite", "Natural", "Gemstone", "Colored Stone"],
    stoneShapes: [
      "Marquise",
      "Round",
      "Pear",
      "Oval",
      "Emerald",
      "Radiant",
      "Heart",
      "Asscher",
      "Cushion",
      "Custom shape"
    ]
  };

  const IMAGE_EXTS = new Set(["jpg", "jpeg", "png", "webp"]);
  const VIDEO_EXTS = new Set(["mp4", "mov"]);

  const form = document.getElementById("orderForm");
  const alertBox = document.getElementById("formAlert");
  const orderIdInput = document.getElementById("order_id");
  const orderIdStatus = document.getElementById("orderIdStatus");
  const productTypeSelect = document.getElementById("product_type");
  const metalOptionSelect = document.getElementById("metal_option_select");
  const customMetalInput = document.getElementById("custom_metal_option");
  const hiddenMetalInput = document.getElementById("metal_option");
  const sizeClosureSelect = document.getElementById("size_closure_select");
  const customSizeInput = document.getElementById("custom_size_closure");
  const hiddenSizeInput = document.getElementById("size_or_closure");

  const addStoneBtn = document.getElementById("addStoneBtn");
  const stonesContainer = document.getElementById("stonesContainer");
  const noStonesHint = document.getElementById("noStonesHint");

  const imageDropzone = document.getElementById("imageDropzone");
  const imageInput = document.getElementById("imageInput");
  const imageCountText = document.getElementById("imageCountText");
  const imagePreviewGrid = document.getElementById("imagePreviewGrid");

  const videoDropzone = document.getElementById("videoDropzone");
  const videoInput = document.getElementById("videoInput");
  const videoCountText = document.getElementById("videoCountText");
  const videoPreviewList = document.getElementById("videoPreviewList");

  const submitBtn = document.getElementById("submitBtn");
  const resetFormBtn = document.getElementById("resetFormBtn");

  let selectedImages = [];
  let selectedVideos = [];
  let orderIdAvailable = false;
  let orderIdTimer = null;

  function showAlert(type, htmlContent) {
    alertBox.className = `alert alert-${type}`;
    alertBox.innerHTML = htmlContent;
    alertBox.classList.remove("hidden");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function hideAlert() {
    alertBox.classList.add("hidden");
    alertBox.innerHTML = "";
  }

  // --- Conditional Size / Closure Options ---
  function buildRingSizes() {
    const sizes = [];
    for (let whole = 3; whole <= 13; whole++) {
      sizes.push(`US ${whole}`);
      if (whole < 13) {
        sizes.push(`US ${whole}.25`);
        sizes.push(`US ${whole}.5`);
        sizes.push(`US ${whole}.75`);
      }
    }
    return sizes;
  }

  const SIZE_CLOSURE_MAP = {
    "Engagement Ring": buildRingSizes(),
    "Wedding Band": buildRingSizes(),
    "Ring": buildRingSizes(),
    "Bracelet": ['6"', '6.5"', '7"', '7.5"', '8"', "Custom"],
    "Pendant / Necklace": ["Pendant Only", '16" Chain', '18" Chain', '20" Chain', "Custom Bail"],
    "Bracelet / Necklace / Chain": ['6"', '6.5"', '7"', '7.5"', '8"', '16"', '18"', '20"', "Custom"],
    "Pendant": ["Pendant Only", '16" Chain', '18" Chain', "Custom Bail"],
    "Earrings": [
      "Push Back / Friction",
      "Screw Back",
      "La Poussette",
      "Leverback",
      "Hinge / Huggie",
      "Latch Back"
    ],
    "Other (Brooch, Nose Pin, etc.)": [
      "Safety Catch",
      "L-Shape",
      "Nose Bone",
      "Screw Stud",
      "Custom"
    ]
  };

  function syncSizeClosureValue() {
    const selected = sizeClosureSelect.value;
    const isCustom = selected === "Custom" || selected === "Custom Bail";
    if (isCustom) {
      customSizeInput.classList.remove("hidden");
      customSizeInput.required = true;
      const customText = customSizeInput.value.trim();
      hiddenSizeInput.value = customText ? `${selected}: ${customText}` : selected;
    } else {
      customSizeInput.classList.add("hidden");
      customSizeInput.required = false;
      customSizeInput.value = "";
      hiddenSizeInput.value = selected;
    }
  }

  function populateSizeClosureOptions() {
    const ptype = productTypeSelect.value;
    const options = SIZE_CLOSURE_MAP[ptype] || ["Custom"];
    sizeClosureSelect.innerHTML = "";
    options.forEach((opt) => {
      const el = document.createElement("option");
      el.value = opt;
      el.textContent = opt;
      sizeClosureSelect.appendChild(el);
    });
    if (ptype === "Ring" || ptype === "Engagement Ring" || ptype === "Wedding Band") {
      sizeClosureSelect.value = "US 6.5";
    }
    syncSizeClosureValue();
  }

  function syncMetalOptionValue() {
    const selected = metalOptionSelect.value;
    const isCustom = selected === "Custom Metal";
    if (isCustom) {
      customMetalInput.classList.remove("hidden");
      customMetalInput.required = true;
      const customText = customMetalInput.value.trim();
      hiddenMetalInput.value = customText || "Custom Metal";
    } else {
      customMetalInput.classList.add("hidden");
      customMetalInput.required = false;
      customMetalInput.value = "";
      hiddenMetalInput.value = selected;
    }
  }

  metalOptionSelect.addEventListener("change", () => {
    syncMetalOptionValue();
    if (metalOptionSelect.value === "Custom Metal") {
      customMetalInput.focus();
    }
  });
  customMetalInput.addEventListener("input", syncMetalOptionValue);

  productTypeSelect.addEventListener("change", populateSizeClosureOptions);
  sizeClosureSelect.addEventListener("change", syncSizeClosureValue);
  customSizeInput.addEventListener("input", syncSizeClosureValue);

  // --- Real-time Order ID Duplicate Check ---
  async function checkOrderIdAvailability(rawVal) {
    const val = rawVal.trim();
    if (!val) {
      orderIdAvailable = false;
      orderIdStatus.className = "hint";
      orderIdStatus.textContent = "Alphanumeric, max 15 characters.";
      return;
    }
    if (!/^[A-Za-z0-9]{1,15}$/.test(val)) {
      orderIdAvailable = false;
      orderIdStatus.className = "hint err";
      orderIdStatus.textContent = "Only letters and numbers allowed (max 15 chars).";
      return;
    }

    try {
      const resp = await fetch(`/api/check-order-id/${encodeURIComponent(val)}`);
      const data = await resp.json();
      if (data.available) {
        orderIdAvailable = true;
        orderIdStatus.className = "hint ok";
        orderIdStatus.textContent = `Order ID "${val}" is available.`;
      } else {
        orderIdAvailable = false;
        orderIdStatus.className = "hint err";
        orderIdStatus.innerHTML = `Order ID "${val}" already exists in orders.db. <button type="button" id="deleteExistingOrderBtn" class="btn btn-danger-ghost" style="padding:2px 6px;margin-left:4px;">Delete stored entry</button>`;
        const delExistingBtn = document.getElementById("deleteExistingOrderBtn");
        if (delExistingBtn) {
          delExistingBtn.addEventListener("click", async () => {
            if (!window.confirm(`Delete stored order "${val}" and all its files?`)) return;
            const delResp = await fetch(`/api/orders/${encodeURIComponent(val)}`, {
              method: "DELETE"
            });
            if (delResp.ok) {
              showAlert("success", `Stored order <strong>${val}</strong> deleted. You can now reuse this Order ID.`);
              await checkOrderIdAvailability(val);
            } else {
              showAlert("error", `Unable to delete stored order "${val}".`);
            }
          });
        }
      }
    } catch (_err) {
      orderIdStatus.className = "hint";
      orderIdStatus.textContent = "Unable to verify Order ID right now.";
    }
  }

  orderIdInput.addEventListener("input", () => {
    clearTimeout(orderIdTimer);
    orderIdTimer = setTimeout(() => {
      checkOrderIdAvailability(orderIdInput.value);
    }, 220);
  });

  // --- Repeatable Stone Details Rows ---
  function updateStoneRowNumbers() {
    const rows = stonesContainer.querySelectorAll(".stone-row");
    rows.forEach((row, idx) => {
      row.querySelector(".stone-row-title").textContent = `Stone #${idx + 1}`;
    });
    noStonesHint.classList.toggle("hidden", rows.length > 0);
  }

  function addStoneRow(initial = {}) {
    const row = document.createElement("div");
    row.className = "stone-row";

    const stoneTypeOptions = config.stoneTypes
      .map(
        (st) =>
          `<option value="${st}" ${initial.stone_type === st ? "selected" : ""}>${st}</option>`
      )
      .join("");

    const shapesList = config.stoneShapes || [
      "Marquise",
      "Round",
      "Pear",
      "Oval",
      "Emerald",
      "Radiant",
      "Heart",
      "Asscher",
      "Cushion",
      "Custom shape"
    ];
    const initialShape = initial.shape || shapesList[0];
    const isCustomInitial = initial.shape && !shapesList.includes(initial.shape);
    const shapeOptions = shapesList
      .map((sh) => {
        const isSelected = isCustomInitial ? sh === "Custom shape" : initialShape === sh;
        return `<option value="${sh}" ${isSelected ? "selected" : ""}>${sh}</option>`;
      })
      .join("");

    row.innerHTML = `
      <div class="stone-row-header">
        <span class="stone-row-title">Stone</span>
        <button type="button" class="btn btn-danger-ghost remove-stone-btn">Remove</button>
      </div>
      <div class="stone-grid">
        <div class="field">
          <label>Stone Type</label>
          <select class="stone-type">${stoneTypeOptions}</select>
        </div>
        <div class="field">
          <label>Shape</label>
          <select class="stone-shape">${shapeOptions}</select>
          <input
            type="text"
            class="stone-shape-custom ${isCustomInitial || initialShape === "Custom shape" ? "" : "hidden"}"
            placeholder="Specify custom shape"
            value="${isCustomInitial ? initial.shape : ""}"
          />
        </div>
        <div class="field">
          <label>Size (mm)</label>
          <input type="text" class="stone-size" placeholder="e.g. 9.0 x 6.5" value="${initial.size_mm || ""}" />
        </div>
        <div class="field">
          <label>Carat Weight</label>
          <input type="text" class="stone-carat" placeholder="e.g. 2.10 ct" value="${initial.carat_weight || ""}" />
        </div>
        <div class="field">
          <label>Color</label>
          <input type="text" class="stone-color" placeholder="e.g. E-F, D" value="${initial.color || ""}" />
        </div>
        <div class="field">
          <label>Quantity <span class="hint">(Optional)</span></label>
          <input type="number" min="1" class="stone-qty" placeholder="e.g. 1, 18" value="${initial.quantity || ""}" />
        </div>
      </div>
    `;

    const shapeSelect = row.querySelector(".stone-shape");
    const customShapeInput = row.querySelector(".stone-shape-custom");
    shapeSelect.addEventListener("change", () => {
      const showCustom = shapeSelect.value === "Custom shape";
      customShapeInput.classList.toggle("hidden", !showCustom);
      if (!showCustom) {
        customShapeInput.value = "";
      } else {
        customShapeInput.focus();
      }
    });

    row.querySelector(".remove-stone-btn").addEventListener("click", () => {
      row.remove();
      updateStoneRowNumbers();
    });

    stonesContainer.appendChild(row);
    updateStoneRowNumbers();
  }

  addStoneBtn.addEventListener("click", () => addStoneRow());

  function collectStones() {
    const rows = stonesContainer.querySelectorAll(".stone-row");
    const list = [];
    rows.forEach((row) => {
      const selectedShape = row.querySelector(".stone-shape").value.trim();
      const customShape = row.querySelector(".stone-shape-custom").value.trim();
      const resolvedShape =
        selectedShape === "Custom shape" ? customShape || "Custom shape" : selectedShape;

      const stone = {
        stone_type: row.querySelector(".stone-type").value.trim(),
        shape: resolvedShape,
        size_mm: row.querySelector(".stone-size").value.trim(),
        carat_weight: row.querySelector(".stone-carat").value.trim(),
        color: row.querySelector(".stone-color").value.trim(),
        quantity: row.querySelector(".stone-qty").value.trim()
      };
      if (stone.size_mm || stone.carat_weight || stone.color || stone.quantity || customShape || stone.shape) {
        list.push(stone);
      }
    });
    return list;
  }

  // --- Drag & Drop Media Validation & Previews ---
  function getExtension(filename) {
    const idx = filename.lastIndexOf(".");
    return idx >= 0 ? filename.slice(idx + 1).toLowerCase() : "";
  }

  function renderImagePreviews() {
    imageCountText.textContent = `${selectedImages.length} / ${config.maxImages} images selected`;
    imagePreviewGrid.innerHTML = "";
    selectedImages.forEach((file, idx) => {
      const card = document.createElement("div");
      card.className = "preview-item";

      const img = document.createElement("img");
      img.alt = file.name;
      const reader = new FileReader();
      reader.onload = (e) => {
        img.src = e.target.result;
      };
      reader.readAsDataURL(file);

      const removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.className = "remove-chip";
      removeBtn.textContent = "×";
      removeBtn.title = "Remove image";
      removeBtn.addEventListener("click", () => {
        selectedImages.splice(idx, 1);
        renderImagePreviews();
      });

      const nameEl = document.createElement("div");
      nameEl.className = "preview-name";
      nameEl.textContent = file.name;

      card.appendChild(img);
      card.appendChild(removeBtn);
      card.appendChild(nameEl);
      imagePreviewGrid.appendChild(card);
    });
  }

  function renderVideoList() {
    videoCountText.textContent = `${selectedVideos.length} / ${config.maxVideos} videos selected`;
    videoPreviewList.innerHTML = "";
    selectedVideos.forEach((file, idx) => {
      const chip = document.createElement("div");
      chip.className = "video-chip";
      const sizeMb = (file.size / (1024 * 1024)).toFixed(2);
      chip.innerHTML = `
        <span><strong>${file.name}</strong> <span class="hint">(${sizeMb} MB)</span></span>
        <button type="button" class="btn btn-danger-ghost">Remove</button>
      `;
      chip.querySelector("button").addEventListener("click", () => {
        selectedVideos.splice(idx, 1);
        renderVideoList();
      });
      videoPreviewList.appendChild(chip);
    });
  }

  function handleIncomingImages(fileList) {
    const errors = [];
    for (const file of fileList) {
      const ext = getExtension(file.name);
      if (!IMAGE_EXTS.has(ext)) {
        errors.push(`"${file.name}" is not a supported image (.jpg, .jpeg, .png, .webp).`);
        continue;
      }
      if (selectedImages.length >= config.maxImages) {
        errors.push(`Maximum ${config.maxImages} images allowed.`);
        break;
      }
      selectedImages.push(file);
    }
    if (errors.length) {
      showAlert("error", errors.join("<br />"));
    }
    renderImagePreviews();
  }

  function handleIncomingVideos(fileList) {
    const errors = [];
    const maxBytes = config.maxVideoMb * 1024 * 1024;
    for (const file of fileList) {
      const ext = getExtension(file.name);
      if (!VIDEO_EXTS.has(ext)) {
        errors.push(`"${file.name}" is not a supported video (.mp4, .mov).`);
        continue;
      }
      if (file.size > maxBytes) {
        errors.push(`"${file.name}" exceeds the ${config.maxVideoMb} MB size limit.`);
        continue;
      }
      if (selectedVideos.length >= config.maxVideos) {
        errors.push(`Maximum ${config.maxVideos} videos allowed.`);
        break;
      }
      selectedVideos.push(file);
    }
    if (errors.length) {
      showAlert("error", errors.join("<br />"));
    }
    renderVideoList();
  }

  function wireDropzone(dropzone, input, handler) {
    dropzone.addEventListener("click", () => input.click());
    dropzone.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        input.click();
      }
    });
    dropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    });
    dropzone.addEventListener("dragleave", () => {
      dropzone.classList.remove("dragover");
    });
    dropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
      if (e.dataTransfer && e.dataTransfer.files) {
        handler(e.dataTransfer.files);
      }
    });
    input.addEventListener("change", () => {
      if (input.files) {
        handler(input.files);
        input.value = "";
      }
    });
  }

  wireDropzone(imageDropzone, imageInput, handleIncomingImages);
  wireDropzone(videoDropzone, videoInput, handleIncomingVideos);

  // --- Form Submission & Instant PDF Download ---
  function triggerDownload(url, filename) {
    const link = document.createElement("a");
    link.href = url;
    link.download = filename || "workshop_job_sheet.pdf";
    document.body.appendChild(link);
    link.click();
    link.remove();
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideAlert();
    syncMetalOptionValue();
    syncSizeClosureValue();

    if (metalOptionSelect.value === "Custom Metal" && !customMetalInput.value.trim()) {
      showAlert("error", "Please specify the custom metal.");
      customMetalInput.focus();
      return;
    }

    const orderId = orderIdInput.value.trim();
    if (!/^[A-Za-z0-9]{1,15}$/.test(orderId)) {
      showAlert("error", "Please enter a valid alphanumeric Order ID (max 15 characters).");
      orderIdInput.focus();
      return;
    }

    if (!document.getElementById("customer_name").value.trim()) {
      showAlert("error", "Customer Name is required.");
      return;
    }

    if (!document.getElementById("product_sku").value.trim()) {
      showAlert("error", "Product SKU is required.");
      return;
    }

    const formData = new FormData(form);
    formData.set("stone_details_json", JSON.stringify(collectStones()));
    selectedImages.forEach((file) => formData.append("images", file));
    selectedVideos.forEach((file) => formData.append("videos", file));

    submitBtn.disabled = true;
    submitBtn.textContent = "Saving & Generating PDF...";

    try {
      const resp = await fetch("/api/orders", {
        method: "POST",
        body: formData
      });
      const data = await resp.json();

      if (!resp.ok || !data.ok) {
        const msg = (data.errors || ["Failed to save order."]).join("<br />");
        showAlert("error", msg);
        return;
      }

      const warningsHtml =
        data.warnings && data.warnings.length
          ? `<div style="margin-top:6px;font-size:12.5px;">Note: ${data.warnings.join(" ")}</div>`
          : "";

      showAlert(
        "success",
        `Order <strong>${data.order_id}</strong> saved and workshop PDF generated!
         ${warningsHtml}
         <div style="margin-top:10px;display:flex;gap:10px;flex-wrap:wrap;">
           <a href="${data.pdf_url}" class="btn btn-primary">Download Workshop PDF</a>
           <a href="/orders" class="btn btn-outline">View Orders History</a>
           <button type="button" id="deleteSavedOrderBtn" class="btn btn-danger">Delete Stored Entry</button>
         </div>`
      );

      const deleteSavedBtn = document.getElementById("deleteSavedOrderBtn");
      if (deleteSavedBtn) {
        deleteSavedBtn.addEventListener("click", async () => {
          if (!window.confirm(`Delete stored order "${data.order_id}"?`)) return;
          const delResp = await fetch(`/api/orders/${encodeURIComponent(data.order_id)}`, {
            method: "DELETE"
          });
          if (delResp.ok) {
            showAlert("success", `Stored order <strong>${data.order_id}</strong> has been deleted.`);
            checkOrderIdAvailability(orderIdInput.value);
          } else {
            showAlert("error", `Failed to delete order "${data.order_id}".`);
          }
        });
      }

      triggerDownload(data.pdf_url, data.pdf_filename);
    } catch (err) {
      showAlert("error", `Network or server error while saving order: ${err.message}`);
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Save Order & Generate PDF";
    }
  });

  resetFormBtn.addEventListener("click", () => {
    form.reset();
    selectedImages = [];
    selectedVideos = [];
    stonesContainer.innerHTML = "";
    renderImagePreviews();
    renderVideoList();
    updateStoneRowNumbers();
    syncMetalOptionValue();
    populateSizeClosureOptions();
    orderIdStatus.className = "hint";
    orderIdStatus.textContent = "Alphanumeric, max 15 characters.";
    hideAlert();
  });

  // Initialize defaults
  syncMetalOptionValue();
  populateSizeClosureOptions();
  addStoneRow();
})();
