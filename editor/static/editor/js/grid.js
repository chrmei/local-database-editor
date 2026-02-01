(function () {
  var configEl = document.getElementById("edit-grid-config");
  if (!configEl) return;
  var config = JSON.parse(configEl.textContent);
  var pkColumns = config.pkColumns || [];
  var pkUsesSequence = config.pkUsesSequence || [];
  var columns = config.columns || [];
  var saveUrl = config.saveUrl;
  var insertUrl = config.insertUrl;
  var deleteUrl = config.deleteUrl;
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

  function valueForNow(inputType) {
    var d = new Date();
    var pad = function (n) { return (n < 10 ? "0" : "") + n; };
    if (inputType === "date") {
      return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
    }
    if (inputType === "datetime-local") {
      return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()) + "T" +
        pad(d.getHours()) + ":" + pad(d.getMinutes()) + ":" + pad(d.getSeconds());
    }
    if (inputType === "time") {
      return pad(d.getHours()) + ":" + pad(d.getMinutes()) + ":" + pad(d.getSeconds());
    }
    return "";
  }

  function showEdit(cellEl) {
    var display = cellEl.querySelector(".cell-display");
    var input = cellEl.querySelector(".cell-edit");
    if (!display || !input) return;
    display.style.display = "none";
    input.style.display = "block";
    var nowBtn = cellEl.querySelector(".cell-now");
    if (nowBtn) nowBtn.style.display = "inline-block";
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
    var nowBtn = cellEl.querySelector(".cell-now");
    if (nowBtn) nowBtn.style.display = "none";
    // Note: data-original is NOT updated here - it preserves the original DB value
    // It's only updated after a successful save or on revert
  }

  var grid = document.getElementById("data-grid");
  if (!grid) return;

  grid.addEventListener("click", function (e) {
    if (e.target.closest(".actions-cell") || e.target.closest(".delete-row") || e.target.closest(".add-row-actions") || e.target.closest(".add-row-now")) return;
    if (e.target.classList.contains("cell-now")) {
      e.preventDefault();
      var cell = e.target.closest("td[data-column]");
      var input = cell && cell.querySelector(".cell-edit");
      if (input && (input.type === "date" || input.type === "datetime-local" || input.type === "time")) {
        input.value = valueForNow(input.type);
        var row = cell.closest("tr");
        if (row && row.getAttribute("data-pk")) markDirty(row);
      }
      return;
    }
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

  function htmlInputType(dataType) {
    if (!dataType) return "text";
    var dt = dataType.trim().toLowerCase();
    if (dt === "date") return "date";
    if (dt.indexOf("timestamp") !== -1) return "datetime-local";
    if (dt.indexOf("time") !== -1 && dt !== "timestamp") return "time";
    if (["integer", "bigint", "smallint", "numeric", "decimal", "real", "double precision", "serial", "bigserial"].indexOf(dt) !== -1) return "number";
    if (dt === "boolean") return "checkbox";
    return "text";
  }

  function isDateTimeColumn(dataType) {
    if (!dataType) return false;
    var dt = dataType.trim().toLowerCase();
    return dt === "date" || dt.indexOf("timestamp") !== -1 || (dt.indexOf("time") !== -1 && dt !== "timestamp");
  }

  document.getElementById("add-row-btn").addEventListener("click", function () {
    var tbody = grid.querySelector("tbody");
    var existing = grid.querySelector("tr.add-row-form");
    if (existing) {
      existing.remove();
      return;
    }
    var tr = document.createElement("tr");
    tr.className = "add-row-form";
    columns.forEach(function (col) {
      var td = document.createElement("td");
      td.setAttribute("data-column", col.name);
      var isAutoPk = pkUsesSequence.indexOf(col.name) !== -1;
      if (isAutoPk) {
        td.innerHTML = '<span class="add-row-auto">(auto)</span>';
      } else if (col.dataType && col.dataType.toLowerCase() === "boolean") {
        td.innerHTML = '<input type="checkbox" class="add-row-input" data-column="' + col.name + '">';
      } else {
        var inputType = htmlInputType(col.dataType);
        var hasNow = isDateTimeColumn(col.dataType);
        td.innerHTML = '<input type="' + inputType + '" class="add-row-input" data-column="' + col.name + '" placeholder="' + (col.isNullable ? "optional" : "required") + '">' +
          (hasNow ? ' <button type="button" class="add-row-now" title="Fill with current date/time">Now</button>' : '');
      }
      tr.appendChild(td);
    });
    var actionsTd = document.createElement("td");
    actionsTd.className = "add-row-actions";
    actionsTd.innerHTML = '<button type="button" class="add-row-submit">Add</button> <button type="button" class="add-row-cancel">Cancel</button>';
    tr.appendChild(actionsTd);
    tbody.insertBefore(tr, tbody.firstChild);

    tr.querySelector(".add-row-cancel").addEventListener("click", function () {
      tr.remove();
    });
    tr.querySelectorAll(".add-row-now").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var td = btn.closest("td");
        var input = td && td.querySelector(".add-row-input");
        if (input && (input.type === "date" || input.type === "datetime-local" || input.type === "time")) {
          input.value = valueForNow(input.type);
        }
      });
    });
    tr.querySelector(".add-row-submit").addEventListener("click", function () {
      var cols = {};
      columns.forEach(function (col) {
        if (pkUsesSequence.indexOf(col.name) !== -1) return;
        var input = tr.querySelector('.add-row-input[data-column="' + col.name + '"]');
        var val = "";
        if (input) {
          val = input.type === "checkbox" ? (input.checked ? "true" : "false") : input.value;
        }
        cols[col.name] = val;
      });
      var xhr = new XMLHttpRequest();
      xhr.open("POST", insertUrl);
      xhr.setRequestHeader("Content-Type", "application/json");
      xhr.setRequestHeader("X-CSRFToken", csrfToken);
      xhr.onload = function () {
        var res;
        try {
          res = JSON.parse(xhr.responseText);
        } catch (e) {
          showToast("Insert failed: invalid response", "error");
          return;
        }
        if (res.ok) {
          showToast("Row inserted.", "success");
          tr.remove();
          window.location.reload();
        } else {
          showToast("Insert failed: " + (res.error || "Unknown error"), "error");
        }
      };
      xhr.onerror = function () {
        showToast("Insert failed: network error", "error");
      };
      xhr.send(JSON.stringify({ columns: cols }));
    });
  });

  grid.addEventListener("click", function (e) {
    var btn = e.target.closest(".delete-row");
    if (!btn) return;
    e.preventDefault();
    var row = btn.closest("tr");
    if (!row || row.classList.contains("add-row-form")) return;
    var pkJson = row.getAttribute("data-pk");
    if (!pkJson) return;
    var pk;
    try {
      pk = JSON.parse(pkJson);
    } catch (err) {
      showToast("Invalid row data", "error");
      return;
    }
    if (!confirm("Hard delete this row? This cannot be undone.")) return;
    var xhr = new XMLHttpRequest();
    xhr.open("POST", deleteUrl);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.setRequestHeader("X-CSRFToken", csrfToken);
    xhr.onload = function () {
      var res;
      try {
        res = JSON.parse(xhr.responseText);
      } catch (e) {
        showToast("Delete failed: invalid response", "error");
        return;
      }
      if (res.ok) {
        showToast("Deleted " + (res.deleted || 1) + " row(s).", "success");
        row.remove();
      } else {
        showToast("Delete failed: " + (res.error || (res.errors && res.errors[0] ? res.errors[0].error : "Unknown error")), "error");
      }
    };
    xhr.onerror = function () {
      showToast("Delete failed: network error", "error");
    };
    xhr.send(JSON.stringify({ pks: [pk] }));
  });
})();
