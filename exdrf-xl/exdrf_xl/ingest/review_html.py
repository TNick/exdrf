"""Render HTML review pages for Excel import plans.

This module is intentionally standalone: it accepts the import plan as a
duck-typed object (must expose the attributes used below) to avoid tight
coupling / circular imports.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from html import escape
from typing import Any

from exdrf.field_types.date_time import UNKNOWN_DATETIME


def _norm_text(value: Any) -> str:
    """Normalize a value for HTML rendering."""
    if value is None:
        return "null"
    if isinstance(value, str):
        v = value.strip()
        if v == "":
            return ""
        return v
    return str(value)


def _escape_with_newlines(text: str) -> str:
    """Escape text for HTML and preserve newlines as <br/>."""
    return escape(text).replace("\n", "<br/>\n")


def _safe_id(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_\\-]+", "_", value.strip())
    if not normalized:
        return "table"
    return normalized


def _normalize_unknown_datetime(value: Any) -> Any:
    """Normalize unknown date-time sentinel to a canonical representation."""
    if isinstance(value, str) and value.strip().lower() == "x":
        return UNKNOWN_DATETIME
    if isinstance(value, datetime):
        if (
            value.year == 1000
            and value.month == 2
            and value.day == 3
            and value.hour == 4
            and value.minute == 5
            and value.second == 6
        ):
            return UNKNOWN_DATETIME
    return value


def _try_parse_json(value: Any) -> Any | None:
    """Try to parse a string value as JSON; return parsed value or None."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text.startswith("{"):
        return None
    try:
        parsed = json.loads(text)
    except Exception:
        return None
    if isinstance(parsed, (dict, list)):
        return parsed
    return None


def _render_json_html(value: Any, *, depth: int = 0) -> str:
    """Render parsed JSON (dict/list) as nested HTML."""
    if depth >= 6:
        return "<span>%s</span>" % _escape_with_newlines(_norm_text(value))

    if isinstance(value, dict):
        if not value:
            return "<span>%s</span>" % escape("{}")
        items = []
        for k in sorted(value.keys(), key=lambda x: str(x)):
            v = value.get(k)
            k_html = '<span class="json-key">%s</span>' % escape(str(k))
            v_html = _render_json_html(v, depth=depth + 1)
            items.append("<li>%s: %s</li>" % (k_html, v_html))
        return '<ul class="json">%s</ul>' % "".join(items)

    if isinstance(value, list):
        if not value:
            return "<span>%s</span>" % escape("[]")
        items = [
            "<li>%s</li>" % _render_json_html(v, depth=depth + 1) for v in value
        ]
        return '<ul class="json">%s</ul>' % "".join(items)

    if value is None:
        return "<span>%s</span>" % escape("null")

    return "<span>%s</span>" % _escape_with_newlines(_norm_text(value))


def _render_maybe_json_text(value: Any) -> str:
    """Render a value; if it looks like JSON, render as nested list."""
    parsed = _try_parse_json(value)
    if parsed is None:
        return _escape_with_newlines(_norm_text(value))
    return _render_json_html(parsed)


def render_review_html(plan: Any) -> str:
    """Render a self-contained HTML review page for an import plan."""
    css = """
    :root {
      --sidebar-width: 320px;
    }
    body { font-family: sans-serif; margin: 24px; }
    h2 { margin-top: 28px; }
    table { border-collapse: collapse; width: 100%; margin: 12px 0 24px; }
    th, td {
      border: 1px solid #cfcfcf;
      padding: 6px 8px;
      vertical-align: top;
    }
    th {
      background: #f5f5f5;
      text-align: left;
      position: sticky;
      top: 0;
    }
    tr.new-row td { background: #e8f7e8; }
    tr.modified-row td { background: #ffffff; }
    .cell-changed { background: #fff7cc; }
    .cell-old { color: #c00000; font-size: 12px; }
    .cell-new { color: #0a7d0a; font-size: 12px; margin-top: 2px; }
    .cell-null { font-style: italic; color: #444; }
    .cell-null-solo { font-style: italic; color: #b0b0b0; }
    .mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
    .json { margin: 0; padding-left: 16px; }
    .json-key { color: #d07a00; font-weight: 600; }

    /* DataTables tweaks */
    thead tr:first-child th {
      position: sticky;
      top: 0;
      z-index: 3;
      background: #f5f5f5;
    }
    thead tr.filter-row th {
      position: sticky;
      top: var(--filter-row-top, 34px);
      z-index: 2;
      background: #fafafa;
    }
    .col-filter {
      width: 100%;
      box-sizing: border-box;
      padding: 4px 6px;
      border: 1px solid #d8d8d8;
      border-radius: 6px;
      font-size: 12px;
    }

    /* Sidebar + overlay */
    .toc-btn {
      position: fixed;
      top: 12px;
      left: 12px;
      z-index: 1001;
      border: 1px solid #cfcfcf;
      background: white;
      padding: 8px 10px;
      border-radius: 8px;
      cursor: pointer;
      box-shadow: 0 2px 10px rgba(0,0,0,0.10);
    }
    .overlay {
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.20);
      z-index: 1000;
      display: none;
    }
    .overlay.open { display: block; }
    .sidebar {
      position: fixed;
      top: 0;
      left: 0;
      height: 100%;
      width: var(--sidebar-width);
      background: white;
      z-index: 1002;
      transform: translateX(-100%);
      transition: transform 160ms ease;
      border-right: 1px solid #ddd;
      box-shadow: 2px 0 14px rgba(0,0,0,0.12);
      padding: 14px 14px 18px 14px;
      overflow: auto;
    }
    .sidebar.open { transform: translateX(0); }
    .sidebar h3 { margin: 0 0 10px 0; }
    .toc-entry { padding: 8px 0; border-bottom: 1px solid #eee; }
    .toc-entry a { text-decoration: none; color: #0b57d0; }
    .toc-controls { margin-top: 6px; font-size: 13px; color: #333; }
    .toc-controls label { display: block; margin: 2px 0; }

    /* Per-table row visibility toggles */
    .hide-new tr.new-row { display: none; }
    .hide-modified tr.modified-row { display: none; }
    """

    parts: list[str] = [
        "<!doctype html>",
        "<html><head>",
        '<meta charset="utf-8"/>',
        "<title>Excel import review</title>",
        '<link rel="stylesheet" href="https://cdn.datatables.net/2.1.8/css/'
        'dataTables.dataTables.min.css">',
        "<style>%s</style>" % css,
        "</head><body>",
        '<button id="toc-btn" class="toc-btn" type="button">☰</button>',
        '<div id="overlay" class="overlay"></div>',
        '<aside id="sidebar" class="sidebar" aria-label="Table of contents">',
        "<h3>Tables</h3>",
        '<div class="toc-entry">',
        '<div class="toc-controls">',
        '<label><input type="checkbox" id="toggle-all" checked> '
        "<b>show all</b></label>",
        '<label><input type="checkbox" id="toggle-new" checked> '
        "<b>show all new</b></label>",
        '<label><input type="checkbox" id="toggle-modified" checked> '
        "<b>show all modified</b></label>",
        "</div>",
        "</div>",
        "<h1>Excel import review</h1>",
        '<div><b>Source:</b> <span class="mono">%s</span></div>'
        % escape(getattr(plan, "source_path", "")),
    ]

    if not getattr(plan, "has_changes", False):
        parts.append("<p>No changes detected.</p>")
        parts.append("</aside>")
        parts.append("</body></html>")
        return "\n".join(parts)

    # Sidebar TOC.
    for tplan in getattr(plan, "tables", ()):
        table = tplan.table
        table_id = _safe_id(table.xl_name)
        new_count = len(tplan.new_rows)
        mod_count = len(tplan.modified_rows)
        not_modified_count = max(0, int(tplan.existing_rows) - mod_count)
        parts.append('<div class="toc-entry">')
        parts.append(
            '<div><a href="#tbl_%s">%s</a></div>'
            % (escape(table_id), escape(table.xl_name))
        )
        parts.append(
            '<div class="toc-controls">'
            "<div><b>new</b>: %d &nbsp; <b>not modified</b>: %d &nbsp; "
            "<b>modified</b>: %d</div>"
            '<label><input type="checkbox" class="toc-toggle" '
            'data-table="%s" data-kind="new" checked> '
            "show new (%d)</label>"
            '<label><input type="checkbox" class="toc-toggle" '
            'data-table="%s" data-kind="modified" checked> '
            "show modified (%d)</label>"
            "</div>"
            % (
                new_count,
                not_modified_count,
                mod_count,
                escape(table_id),
                new_count,
                escape(table_id),
                mod_count,
            )
        )
        parts.append("</div>")

    parts.append("</aside>")

    # Main sections.
    for tplan in getattr(plan, "tables", ()):
        table = tplan.table
        table_id = _safe_id(table.xl_name)
        new_count = len(tplan.new_rows)
        mod_count = len(tplan.modified_rows)
        not_modified_count = max(0, int(tplan.existing_rows) - mod_count)
        parts.append(
            '<section id="tbl_%s" class="table-section" data-table="%s">'
            % (escape(table_id), escape(table_id))
        )
        parts.append(
            "<h2>%s</h2>"
            % escape(
                "%s (new: %d, not modified: %d, modified: %d)"
                % (
                    table.xl_name,
                    new_count,
                    not_modified_count,
                    mod_count,
                )
            )
        )

        rows = list(tplan.new_rows) + list(tplan.modified_rows)
        if not rows:
            parts.append("<p>No changes.</p>")
            parts.append("</section>")
            continue

        # Show full row content for changed rows: use the table column order
        # (excluding read-only columns), not just the set of changed cells.
        # Only consider columns that are included in the Excel export (same as
        # what the user can actually edit in the workbook). This also avoids
        # "shadowed" columns where an override introduces a read-only column
        # with the same `xl_name` as a relationship placeholder column from the
        # generated base schema.
        table_cols = list(table.get_included_columns())

        cols = [
            c.xl_name
            for c in table_cols
            if not bool(getattr(c, "read_only", False))
        ]
        # Only include columns that exist in at least one Excel row (keeps the
        # review compact and avoids columns that aren't present in the sheet).
        present: set[str] = set()
        for r in rows:
            present.update(getattr(r, "xl_row", {}).keys())
        cols = [c for c in cols if c in present]

        parts.append(
            '<table id="dt_%s" class="review-table" data-table="%s">'
            % (escape(table_id), escape(table_id))
        )
        header_cells = ["kind", "pk"] + cols
        parts.append("<thead>")
        parts.append(
            "<tr>"
            + "".join("<th>%s</th>" % escape(c) for c in header_cells)
            + "</tr>"
        )
        parts.append(
            '<tr class="filter-row">'
            + "".join(
                '<th><input class="col-filter" type="text" '
                'placeholder="filter"/></th>'
                for _ in header_cells
            )
            + "</tr>"
        )
        parts.append("</thead>")
        parts.append("<tbody>")

        def _render_solo_cell(value: Any) -> str:
            if value is None:
                return '<span class="cell-null-solo">null</span>'
            if isinstance(value, str) and value.strip() == "":
                return '<span class="cell-null-solo">(empty)</span>'
            return _render_maybe_json_text(value)

        for r in rows:
            is_new = r.is_new
            tr_class = "new-row" if is_new else "modified-row"
            parts.append('<tr class="%s">' % tr_class)
            parts.append("<td>%s</td>" % ("new" if is_new else "modified"))
            pk_text = ", ".join(
                "%s=%s" % (k, _norm_text(v)) for k, v in r.pk.items()
            )
            parts.append('<td class="mono">%s</td>' % escape(pk_text))

            diff_by_col = {d.column: d for d in r.diffs}
            for c in cols:
                d_opt = diff_by_col.get(c)
                if is_new:
                    v = getattr(r, "xl_row", {}).get(c, None)
                    if v is None:
                        parts.append(
                            '<td><span class="cell-null-solo">null</span>'
                            "</td>"
                        )
                    elif isinstance(v, str) and v.strip() == "":
                        parts.append(
                            '<td><span class="cell-null-solo">'
                            "(empty)</span>"
                            "</td>"
                        )
                    else:
                        parts.append(
                            '<td><span class="cell-new">%s</span></td>'
                            % escape(_norm_text(v))
                        )
                    continue

                # Unchanged cell in a modified row: show current (Excel) value.
                if d_opt is None:
                    v = getattr(r, "xl_row", {}).get(c, None)
                    parts.append("<td>%s</td>" % _render_solo_cell(v))
                    continue

                old_v = d_opt.old_value
                new_v = d_opt.new_value

                old_v = _normalize_unknown_datetime(old_v)
                new_v = _normalize_unknown_datetime(new_v)

                def fmt(v: Any, kind: str) -> str:
                    if v is None:
                        return '<span class="cell-null">null</span>'
                    if isinstance(v, str) and v.strip() == "":
                        return '<span class="cell-null">(empty)</span>'
                    cls = "cell-old" if kind == "old" else "cell-new"
                    return '<span class="%s">%s</span>' % (
                        cls,
                        _render_maybe_json_text(v),
                    )

                parts.append(
                    '<td class="cell-changed">%s<br/>%s</td>'
                    % (fmt(old_v, "old"), fmt(new_v, "new"))
                )

            parts.append("</tr>")

        parts.append("</tbody></table>")
        parts.append("</section>")

    # Behavior (sidebar + globals + DataTables + filters).
    parts.append(
        """
<script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
<script src="https://cdn.datatables.net/2.1.8/js/dataTables.min.js"></script>
<script>
(function () {
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("overlay");
  const btn = document.getElementById("toc-btn");
  const toggleAll = document.getElementById("toggle-all");
  const toggleNewAll = document.getElementById("toggle-new");
  const toggleModifiedAll = document.getElementById("toggle-modified");

  function openSidebar() {
    sidebar.classList.add("open");
    overlay.classList.add("open");
  }
  function closeSidebar() {
    sidebar.classList.remove("open");
    overlay.classList.remove("open");
  }

  btn.addEventListener("click", function (e) {
    e.stopPropagation();
    if (sidebar.classList.contains("open")) {
      closeSidebar();
    } else {
      openSidebar();
    }
  });

  overlay.addEventListener("click", function () {
    closeSidebar();
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeSidebar();
  });

  // Close when clicking away (outside sidebar) while open.
  document.addEventListener("click", function (e) {
    if (!sidebar.classList.contains("open")) return;
    if (sidebar.contains(e.target) || btn.contains(e.target)) return;
    closeSidebar();
  });

  // Wire up per-table show/hide toggles.
  const toggles = document.querySelectorAll("input.toc-toggle");

  function setIndeterminate(el, value) {
    if (!el) return;
    el.indeterminate = Boolean(value);
  }

  function setChecked(el, value) {
    if (!el) return;
    el.checked = Boolean(value);
    setIndeterminate(el, false);
  }

  function updateSection(tableId) {
    const section = document.querySelector(
      'section.table-section[data-table="' + tableId + '"]'
    );
    if (!section) return;
    const showNew = document.querySelector(
      'input.toc-toggle[data-table="' + tableId + '"][data-kind="new"]'
    )?.checked;
    const showMod = document.querySelector(
      'input.toc-toggle[data-table="' + tableId + '"][data-kind="modified"]'
    )?.checked;
    const anyShown = Boolean(showNew) || Boolean(showMod);
    section.style.display = anyShown ? "" : "none";

    // Redraw DataTables if present so it re-evaluates row visibility.
    section.querySelectorAll("table.review-table").forEach(function (tbl) {
      if (tbl._dtInstance) {
        tbl._dtInstance.draw();
      }
    });
  }

  function applyBulk(kind, checked) {
    const selector =
      kind === "all"
        ? "input.toc-toggle"
        : 'input.toc-toggle[data-kind="' + kind + '"]';
    document.querySelectorAll(selector).forEach(function (el) {
      el.checked = Boolean(checked);
      el.dispatchEvent(new Event("change"));
    });
  }

  function syncGlobals() {
    const newToggles = Array.from(
      document.querySelectorAll('input.toc-toggle[data-kind="new"]')
    );
    const modToggles = Array.from(
      document.querySelectorAll('input.toc-toggle[data-kind="modified"]')
    );

    function computeState(arr) {
      const checkedCount = arr.filter((x) => x.checked).length;
      if (checkedCount === 0) return { checked: false, ind: false };
      if (checkedCount === arr.length) return { checked: true, ind: false };
      return { checked: false, ind: true };
    }

    const ns = computeState(newToggles);
    setChecked(toggleNewAll, ns.checked);
    setIndeterminate(toggleNewAll, ns.ind);

    const ms = computeState(modToggles);
    setChecked(toggleModifiedAll, ms.checked);
    setIndeterminate(toggleModifiedAll, ms.ind);

    // "All" is fully checked only when both sets are fully checked.
    const allChecked = ns.checked && ms.checked;
    setChecked(toggleAll, allChecked);
    setIndeterminate(toggleAll, ns.ind || ms.ind);
  }

  toggles.forEach(function (el) {
    el.addEventListener("change", function () {
      const tableId = el.getAttribute("data-table");
      const kind = el.getAttribute("data-kind");
      const section = document.querySelector(
        'section.table-section[data-table="' + tableId + '"]'
      );
      if (!section) return;
      const on = el.checked;
      if (kind === "new") {
        section.classList.toggle("hide-new", !on);
      } else if (kind === "modified") {
        section.classList.toggle("hide-modified", !on);
      }
      updateSection(tableId);
      syncGlobals();
    });
  });

  // Global toggles
  if (toggleAll) {
    toggleAll.addEventListener("change", function () {
      const on = toggleAll.checked;
      setChecked(toggleNewAll, on);
      setChecked(toggleModifiedAll, on);
      applyBulk("new", on);
      applyBulk("modified", on);
      syncGlobals();
    });
  }
  if (toggleNewAll) {
    toggleNewAll.addEventListener("change", function () {
      applyBulk("new", toggleNewAll.checked);
      syncGlobals();
    });
  }
  if (toggleModifiedAll) {
    toggleModifiedAll.addEventListener("change", function () {
      applyBulk("modified", toggleModifiedAll.checked);
      syncGlobals();
    });
  }

  // Default closed.
  closeSidebar();

  // Initialize DataTables for each review table + column filters.
  document.querySelectorAll("table.review-table").forEach(function (tbl) {
    // Keep filter row sticky right under the header row (even if row height
    // changes due to fonts / DataTables).
    try {
      const headerRow = tbl.querySelector("thead tr:first-child");
      if (headerRow) {
        const h = headerRow.getBoundingClientRect().height;
        tbl.style.setProperty("--filter-row-top", Math.ceil(h) + "px");
      }
    } catch (e) {}

    const inputs = Array.from(
      tbl.querySelectorAll("thead tr.filter-row th input")
    );

    function applyManualFilter() {
      const filterValues = inputs.map(function (inp) {
        return (inp.value || "").toLowerCase();
      });
      const rows = tbl.querySelectorAll("tbody tr");
      rows.forEach(function (tr) {
        const cells = tr.querySelectorAll("td");
        let ok = true;
        filterValues.forEach(function (fv, idx) {
          if (!ok) return;
          if (!fv) return;
          const cell = cells[idx];
          const text = (cell ? (cell.innerText || cell.textContent || "") : "")
            .toLowerCase()
            .trim();
          if (text.indexOf(fv) === -1) ok = false;
        });
        tr.style.display = ok ? "" : "none";
      });
    }

    // Always wire inputs: if DataTables can't load (offline/CDN blocked),
    // fallback still works.
    inputs.forEach(function (inp) {
      inp.addEventListener("input", function () {
        if (tbl._dtInstance) {
          // Handled by DT-specific listeners below.
          return;
        }
        applyManualFilter();
      });
    });

    function initDtInstance(dt) {
      tbl._dtInstance = dt;
      inputs.forEach(function (inp, idx) {
        inp.addEventListener("input", function () {
          dt.column(idx).search(inp.value || "");
          dt.draw();
        });
      });
    }

    // Prefer DataTables v2 "vanilla" API if present.
    if (typeof DataTable !== "undefined") {
      try {
        const dt = new DataTable(tbl, {
          paging: false,
          info: true,
          order: [],
          searching: true,
          orderCellsTop: true,
        });
        initDtInstance(dt);
        return;
      } catch (e) {
        // Fall through to try the jQuery plugin / manual.
      }
    }

    // Support jQuery DataTables builds (common CDN bundles).
    if (typeof window.jQuery !== "undefined") {
      try {
        const $ = window.jQuery;
        if ($.fn && ($.fn.DataTable || $.fn.dataTable)) {
          const dt = $(tbl).DataTable({
            paging: false,
            info: true,
            order: [],
            searching: true,
            orderCellsTop: true,
          });
          initDtInstance(dt);
          return;
        }
      } catch (e) {
        // Fall through to manual.
      }
    }

    // No usable DataTables; use manual filters.
    applyManualFilter();
  });

  // Apply initial visibility state.
  const tableIds = new Set();
  toggles.forEach(function (el) {
    const tableId = el.getAttribute("data-table");
    if (tableId) tableIds.add(tableId);
  });
  tableIds.forEach(function (tableId) { updateSection(tableId); });
  syncGlobals();
})();
</script>
        """
    )

    parts.append("</body></html>")
    return "\n".join(parts)
