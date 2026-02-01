(function () {
  var configEl = document.getElementById("edit-grid-config");
  if (!configEl) return;
  var config = JSON.parse(configEl.textContent);
  var pkColumns = config.pkColumns || [];
  var saveUrl = config.saveUrl;
  var csrfToken = config.csrfToken;

  var dirtyRows = new Map();

  function getRowPk(rowEl) {
    var pkJson = rowEl.getAttribute("data-pk");
    if (!pkJson) return null;
    try {
      return JSON.parse(pkJson);
    } catch (e) {
      return null;
    }
  }

  function getRowData(rowEl) {
    var pk = getRowPk(rowEl);
    if (!pk) return null;
    var cells = rowEl.querySelectorAll("td[data-column]");
    var columns = {};
    for (var i = 0; i < cells.length; i++) {
      var cell = cells[i];
      var col = cell.getAttribute("data-column");
      var input = cell.querySelector(".cell-edit");
      columns[col] = input ? input.value : cell.getAttribute("data-original");
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

  function hideEdit(cellEl) {
    var display = cellEl.querySelector(".cell-display");
    var input = cellEl.querySelector(".cell-edit");
    if (!display || !input) return;
    var newVal = input.value;
    display.textContent = newVal;
    display.style.display = "";
    input.style.display = "none";
    cellEl.setAttribute("data-original", newVal);
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
        var current = input.value;
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
        input.value = cell.getAttribute("data-original");
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
          input.value = original;
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
        alert("Save failed: invalid response");
        return;
      }
      if (res.ok) {
        dirtyRows.forEach(function (rowEl) {
          var cells = rowEl.querySelectorAll("td[data-column]");
          cells.forEach(function (cell) {
            var input = cell.querySelector(".cell-edit");
            var val = input ? input.value : cell.getAttribute("data-original");
            cell.setAttribute("data-original", val);
            var disp = cell.querySelector(".cell-display");
            if (disp) disp.textContent = val;
          });
          unmarkDirty(rowEl);
        });
        dirtyRows.clear();
        updateDirtyCount();
        document.getElementById("save-changes").disabled = true;
        if (res.updated !== undefined) alert("Saved " + res.updated + " row(s).");
      } else {
        alert("Save failed: " + (res.error || (res.errors && res.errors.length ? res.errors[0].error : "Unknown error")));
      }
    };
    xhr.onerror = function () {
      alert("Save failed: network error");
    };
    xhr.send(body);
  });
})();
