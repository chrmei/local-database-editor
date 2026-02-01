(function () {
  var configEl = document.getElementById("edit-grid-config");
  if (!configEl) return;
  var config = JSON.parse(configEl.textContent);
  var pkColumns = config.pkColumns || [];
  var saveUrl = config.saveUrl;
  var csrfToken = config.csrfToken;

  var dirtyRows = new Map();

  function showToast(message, type) {
    type = type || "info";
    var container = document.getElementById("toast-container");
    if (!container) return;
    var toast = document.createElement("div");
    toast.className = "toast " + type;
    toast.textContent = message;
    container.appendChild(toast);
    // Trigger reflow then add show class for animation
    toast.offsetHeight;
    toast.classList.add("show");
    setTimeout(function () {
      toast.classList.remove("show");
      setTimeout(function () { toast.remove(); }, 300);
    }, 3000);
  }

  function getRowPk(rowEl) {
    var pkJson = rowEl.getAttribute("data-pk");
    if (!pkJson) return null;
    try {
      return JSON.parse(pkJson);
    } catch (e) {
      return null;
    }
  }

  function getCellValue(cell) {
    var input = cell.querySelector(".cell-edit");
    if (!input) return cell.getAttribute("data-original") || "";
    if (input.type === "checkbox") return input.checked ? "true" : "false";
    return input.value;
  }

  function getRowData(rowEl) {
    var pk = getRowPk(rowEl);
    if (!pk) return null;
    var cells = rowEl.querySelectorAll("td[data-column]");
    var columns = {};
    for (var i = 0; i < cells.length; i++) {
      var cell = cells[i];
      var col = cell.getAttribute("data-column");
      columns[col] = getCellValue(cell);
    }
    return { pk: pk, columns: columns };
  }

  function markDirty(rowEl) {
    var pk = getRowPk(rowEl);
    if (!pk) return;
    var key = JSON.stringify(pk);
    dirtyRows.set(key, rowEl);
    rowEl.classList.add("dirty");
    updateDirtyCount();
    document.getElementById("save-changes").disabled = false;
  }

  function unmarkDirty(rowEl) {
    var pk = getRowPk(rowEl);
    if (pk) {
      dirtyRows.delete(JSON.stringify(pk));
      rowEl.classList.remove("dirty");
    }
    updateDirtyCount();
    document.getElementById("save-changes").disabled = dirtyRows.size === 0;
  }

  function updateDirtyCount() {
    var el = document.getElementById("dirty-count");
    if (el) el.textContent = dirtyRows.size > 0 ? dirtyRows.size + " row(s) modified" : "";
  }

  function showEdit(cellEl) {
    var display = cellEl.querySelector(".cell-display");
    var input = cellEl.querySelector(".cell-edit");
    if (!display || !input) return;
    display.style.display = "none";
    input.style.display = "block";
    input.focus();
    input.select();
  }

  function getDisplayValue(cellEl) {
    var input = cellEl.querySelector(".cell-edit");
    if (!input) return "";
    if (input.type === "checkbox") return input.checked ? "true" : "false";
    return input.value;
  }

  function hideEdit(cellEl) {
    var display = cellEl.querySelector(".cell-display");
    var input = cellEl.querySelector(".cell-edit");
    if (!display || !input) return;
    var newVal = getDisplayValue(cellEl);
    display.textContent = newVal;
    display.style.display = "";
    input.style.display = "none";
    // Note: data-original is NOT updated here - it preserves the original DB value
    // It's only updated after a successful save or on revert
  }

  var grid = document.getElementById("data-grid");
  if (!grid) return;

  grid.addEventListener("click", function (e) {
    var cell = e.target.closest("td[data-column]");
    if (!cell || e.target.classList.contains("cell-edit")) return;
    e.preventDefault();
    showEdit(cell);
  });

  grid.addEventListener("focusout", function (e) {
    var input = e.target;
    if (input.classList.contains("cell-edit")) {
      var cell = input.closest("td");
      if (cell && !cell.contains(document.activeElement)) {
        hideEdit(cell);
        var row = cell.closest("tr");
        var original = cell.getAttribute("data-original");
        var current = getCellValue(cell);
        if (original !== current) markDirty(row);
      }
    }
  });

  grid.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && e.target.classList.contains("cell-edit")) {
      e.target.blur();
    }
    if (e.key === "Escape") {
      var input = e.target;
      if (input.classList.contains("cell-edit")) {
        var cell = input.closest("td");
        var original = cell.getAttribute("data-original");
        if (input.type === "checkbox") {
          input.checked = original === "true";
        } else {
          input.value = original;
        }
        hideEdit(cell);
      }
    }
  });

  document.getElementById("revert-changes").addEventListener("click", function () {
    dirtyRows.forEach(function (rowEl) {
      var cells = rowEl.querySelectorAll("td[data-column]");
      cells.forEach(function (cell) {
        var input = cell.querySelector(".cell-edit");
        var original = cell.getAttribute("data-original");
        if (input) {
          if (input.type === "checkbox") {
            input.checked = original === "true";
          } else {
            input.value = original;
          }
          cell.querySelector(".cell-display").textContent = original;
        }
      });
      unmarkDirty(rowEl);
    });
    dirtyRows.clear();
    updateDirtyCount();
    document.getElementById("save-changes").disabled = true;
  });

  document.getElementById("save-changes").addEventListener("click", function () {
    if (dirtyRows.size === 0) return;
    var rows = [];
    dirtyRows.forEach(function (rowEl) {
      var data = getRowData(rowEl);
      if (data) rows.push(data);
    });
    var body = JSON.stringify({ rows: rows });
    var xhr = new XMLHttpRequest();
    xhr.open("POST", saveUrl);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.setRequestHeader("X-CSRFToken", csrfToken);
    xhr.onload = function () {
      var res;
      try {
        res = JSON.parse(xhr.responseText);
      } catch (e) {
        showToast("Save failed: invalid response", "error");
        return;
      }
      if (res.ok) {
        dirtyRows.forEach(function (rowEl) {
          var cells = rowEl.querySelectorAll("td[data-column]");
          cells.forEach(function (cell) {
            var val = getCellValue(cell);
            cell.setAttribute("data-original", val);
            var disp = cell.querySelector(".cell-display");
            if (disp) disp.textContent = val;
          });
          unmarkDirty(rowEl);
        });
        dirtyRows.clear();
        updateDirtyCount();
        document.getElementById("save-changes").disabled = true;
        if (res.updated !== undefined) showToast("Saved " + res.updated + " row(s).", "success");
      } else {
        showToast("Save failed: " + (res.error || (res.errors && res.errors.length ? res.errors[0].error : "Unknown error")), "error");
      }
    };
    xhr.onerror = function () {
      showToast("Save failed: network error", "error");
    };
    xhr.send(body);
  });
})();
