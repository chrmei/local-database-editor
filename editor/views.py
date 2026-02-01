import json
from decimal import Decimal
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, JsonResponse
from django.conf import settings
from django.core.paginator import Paginator
from django.urls import reverse
from django.middleware.csrf import get_token
from django.db import transaction
from django.db.utils import OperationalError, ProgrammingError

from .introspection import (
    get_schemas,
    get_tables,
    get_columns,
    get_primary_key_columns,
    get_table_meta,
    get_pk_sequence_columns,
)

_DATE_TYPES = {"date"}
_TS_TYPES = {"timestamp with time zone", "timestamp without time zone"}
_TIME_TYPES = {"time with time zone", "time without time zone"}
_BOOL_TYPES = {"boolean"}
_INT_TYPES = {"integer", "bigint", "smallint", "serial", "bigserial"}
_FLOAT_TYPES = {"real", "double precision"}
_DECIMAL_TYPES = {"numeric", "decimal"}


def _coerce_value(val, data_type):
    """Coerce a value for DB write based on PostgreSQL data_type."""
    if data_type is None:
        return val
    dt = (data_type or "").strip().lower()
    if dt in _DATE_TYPES or dt in _TS_TYPES or dt in _TIME_TYPES:
        if val is None or (isinstance(val, str) and val.strip() == ""):
            return None
    if dt in _BOOL_TYPES:
        if val is None or (isinstance(val, str) and val.strip() == ""):
            return None
        if isinstance(val, bool):
            return val
        s = str(val).strip().lower()
        if s in ("t", "true", "1", "yes", "on"):
            return True
        if s in ("f", "false", "0", "no", "off"):
            return False
        return None
    if dt in _INT_TYPES and val is not None and (isinstance(val, str) and val.strip() != "" or isinstance(val, (int, float))):
        try:
            return int(val) if not isinstance(val, int) else val
        except (ValueError, TypeError):
            return val
    if dt in _FLOAT_TYPES and val is not None and (isinstance(val, str) and val.strip() != "" or isinstance(val, (int, float))):
        try:
            return float(val) if not isinstance(val, float) else val
        except (ValueError, TypeError):
            return val
    if dt in _DECIMAL_TYPES and val is not None and (isinstance(val, str) and val.strip() != "" or isinstance(val, (int, float, Decimal))):
        try:
            return Decimal(str(val))
        except (ValueError, TypeError, Exception):
            return val
    return val


def home_redirect(request):
    return redirect("database_list")


@login_required
def database_list(request):
    databases = settings.EDITABLE_DATABASES
    return render(
        request,
        "editor/database_list.html",
        {"databases": databases},
    )


@login_required
def schema_list(request, db_alias):
    if db_alias not in settings.EDITABLE_DATABASES:
        return HttpResponseBadRequest("Unknown database")
    refresh = request.GET.get("refresh") == "1"
    try:
        schemas = get_schemas(db_alias, refresh=refresh)
    except (OperationalError, ProgrammingError) as e:
        return render(
            request,
            "editor/error.html",
            {"message": "Could not connect to database or list schemas.", "detail": str(e), "back_url": reverse("database_list")},
            status=502,
        )
    return render(
        request,
        "editor/schema_list.html",
        {"db_alias": db_alias, "schemas": schemas},
    )


@login_required
def table_list(request, db_alias, schema_name):
    if db_alias not in settings.EDITABLE_DATABASES:
        return HttpResponseBadRequest("Unknown database")
    try:
        valid_schemas = get_schemas(db_alias, refresh=False)
    except (OperationalError, ProgrammingError) as e:
        return render(
            request,
            "editor/error.html",
            {"message": "Could not connect to database.", "detail": str(e), "back_url": reverse("database_list")},
            status=502,
        )
    if schema_name not in valid_schemas:
        return HttpResponseBadRequest("Unknown schema")
    refresh = request.GET.get("refresh") == "1"
    try:
        tables = get_tables(db_alias, schema_name, refresh=refresh)
    except (OperationalError, ProgrammingError) as e:
        return render(
            request,
            "editor/error.html",
            {"message": "Could not list tables.", "detail": str(e), "back_url": reverse("schema_list", args=[db_alias])},
            status=502,
        )
    return render(
        request,
        "editor/table_list.html",
        {"db_alias": db_alias, "schema_name": schema_name, "tables": tables},
    )


@login_required
def table_grid(request, db_alias, schema_name, table_name):
    if db_alias not in settings.EDITABLE_DATABASES:
        return HttpResponseBadRequest("Unknown database")
    try:
        valid_schemas = get_schemas(db_alias, refresh=False)
    except (OperationalError, ProgrammingError) as e:
        return render(
            request,
            "editor/error.html",
            {"message": "Could not connect to database.", "detail": str(e), "back_url": reverse("database_list")},
            status=502,
        )
    if schema_name not in valid_schemas:
        return HttpResponseBadRequest("Unknown schema")
    refresh = request.GET.get("refresh") == "1"
    try:
        tables = get_tables(db_alias, schema_name, refresh=refresh)
    except (OperationalError, ProgrammingError) as e:
        return render(
            request,
            "editor/error.html",
            {"message": "Could not list tables.", "detail": str(e), "back_url": reverse("table_list", args=[db_alias, schema_name])},
            status=502,
        )
    if table_name not in tables:
        return HttpResponseBadRequest("Unknown table")
    try:
        columns, pk_columns = get_table_meta(db_alias, schema_name, table_name, refresh=refresh)
    except (OperationalError, ProgrammingError) as e:
        return render(
            request,
            "editor/error.html",
            {"message": "Could not load table metadata.", "detail": str(e), "back_url": reverse("table_list", args=[db_alias, schema_name])},
            status=502,
        )
    column_names = [c["name"] for c in columns]
    col_allowlist = set(column_names)

    sort_col = request.GET.get("sort")
    sort_order = (request.GET.get("order") or "asc").lower()
    if sort_order not in ("asc", "desc"):
        sort_order = "asc"
    if sort_col and sort_col in col_allowlist:
        order_col = sort_col
    else:
        order_col = pk_columns[0] if pk_columns else column_names[0]

    from django.db import connections
    conn = connections[db_alias]
    quoted_schema = conn.ops.quote_name(schema_name)
    quoted_table = conn.ops.quote_name(table_name)
    # Build SELECT with allowlisted WHERE (filters) and ORDER BY
    where_parts = []
    params = []
    for col in column_names:
        val = request.GET.get(f"filter_{col}", "").strip()
        if val:
            where_parts.append(f'{conn.ops.quote_name(col)}::text ILIKE %s')
            params.append(f"%{val}%")
    where_sql = " AND ".join(where_parts) if where_parts else "1=1"
    order_sql = f'{conn.ops.quote_name(order_col)} {sort_order.upper()}'
    per_page = min(int(request.GET.get("per_page", 50) or 50), 200)
    page_num = max(1, int(request.GET.get("page", 1) or 1))
    offset = (page_num - 1) * per_page

    try:
        with conn.cursor() as cur:
            cur.execute(
                f'SELECT * FROM {quoted_schema}.{quoted_table} WHERE {where_sql} ORDER BY {order_sql} LIMIT %s OFFSET %s',
                params + [per_page, offset],
            )
            rows = cur.fetchall()
            column_names = [cur.description[i][0] for i in range(len(cur.description))]
            cur.execute(
                f'SELECT COUNT(*) FROM {quoted_schema}.{quoted_table} WHERE {where_sql}',
                params,
            )
            total = cur.fetchone()[0]
    except (OperationalError, ProgrammingError) as e:
        return render(
            request,
            "editor/error.html",
            {"message": "Could not load table data.", "detail": str(e), "back_url": reverse("table_list", args=[db_alias, schema_name])},
            status=502,
        )

    paginator = Paginator(range(total), per_page)
    page = paginator.page(page_num)
    row_data = [dict(zip(column_names, row)) for row in rows]

    filter_values = {col: request.GET.get(f"filter_{col}", "") for col in column_names}
    has_filters = any(v.strip() for v in filter_values.values())
    pk_uses_sequence = get_pk_sequence_columns(db_alias, schema_name, table_name, refresh=refresh)
    config_json = json.dumps({
        "dbAlias": db_alias,
        "schemaName": schema_name,
        "tableName": table_name,
        "pkColumns": pk_columns,
        "pkUsesSequence": pk_uses_sequence,
        "columns": [{"name": c["name"], "dataType": c["data_type"], "isNullable": c["is_nullable"], "columnDefault": c.get("column_default")} for c in columns],
        "saveUrl": reverse("table_save_rows", args=[db_alias, schema_name, table_name]),
        "insertUrl": reverse("table_insert_row", args=[db_alias, schema_name, table_name]),
        "deleteUrl": reverse("table_delete_rows", args=[db_alias, schema_name, table_name]),
        "csrfToken": get_token(request),
    })

    return render(
        request,
        "editor/table_grid.html",
        {
            "db_alias": db_alias,
            "schema_name": schema_name,
            "table_name": table_name,
            "columns": columns,
            "column_names": column_names,
            "pk_columns": pk_columns,
            "rows": row_data,
            "page": page,
            "sort_col": order_col,
            "sort_order": sort_order,
            "filter_values": filter_values,
            "has_filters": has_filters,
            "config_json": config_json,
        },
    )


@login_required
def table_save_rows(request, db_alias, schema_name, table_name):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    if db_alias not in settings.EDITABLE_DATABASES:
        return HttpResponseBadRequest("Unknown database")
    valid_schemas = get_schemas(db_alias, refresh=False)
    if schema_name not in valid_schemas:
        return HttpResponseBadRequest("Unknown schema")
    tables = get_tables(db_alias, schema_name, refresh=False)
    if table_name not in tables:
        return HttpResponseBadRequest("Unknown table")
    columns, pk_columns = get_table_meta(db_alias, schema_name, table_name, refresh=False)
    column_names = [c["name"] for c in columns]
    col_allowlist = set(column_names)
    pk_set = set(pk_columns)
    if not pk_set:
        return JsonResponse({"ok": False, "error": "Table has no primary key"})

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid JSON"})
    if not isinstance(payload.get("rows"), list):
        return JsonResponse({"ok": False, "error": "Missing or invalid 'rows' array"})

    column_by_name = {c["name"]: c for c in columns}
    from django.db import connections
    conn = connections[db_alias]
    quoted_schema = conn.ops.quote_name(schema_name)
    quoted_table = conn.ops.quote_name(table_name)
    errors = []
    updated = 0
    try:
        with transaction.atomic(using=db_alias):
            with conn.cursor() as cur:
                for row in payload["rows"]:
                    pk = row.get("pk")
                    cols = row.get("columns") or {}
                    if not isinstance(pk, dict) or not pk_set.issubset(set(pk.keys())):
                        errors.append({"row": row, "error": "Invalid or missing primary key"})
                        continue
                    update_cols = {k: v for k, v in cols.items() if k in col_allowlist and k not in pk_set}
                    if not update_cols:
                        continue
                    set_parts = [f'{conn.ops.quote_name(c)} = %s' for c in update_cols]
                    where_parts = [f'{conn.ops.quote_name(k)} = %s' for k in pk_columns]
                    col_types = {c: (column_by_name.get(c) or {}).get("data_type") for c in update_cols}
                    set_vals = [_coerce_value(update_cols[c], col_types.get(c)) for c in update_cols]
                    where_vals = [pk[k] for k in pk_columns]
                    sql = f'UPDATE {quoted_schema}.{quoted_table} SET {", ".join(set_parts)} WHERE {" AND ".join(where_parts)}'
                    try:
                        cur.execute(sql, set_vals + where_vals)
                        updated += cur.rowcount
                    except Exception as e:
                        errors.append({"row": row, "error": str(e)})
            if errors:
                raise ValueError("Row errors")
        return JsonResponse({"ok": True, "updated": updated})
    except ValueError:
        return JsonResponse({"ok": False, "errors": errors})


@login_required
def table_insert_row(request, db_alias, schema_name, table_name):
    """POST: insert a new row. PK columns with nextval default are omitted (auto-filled)."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    if db_alias not in settings.EDITABLE_DATABASES:
        return HttpResponseBadRequest("Unknown database")
    valid_schemas = get_schemas(db_alias, refresh=False)
    if schema_name not in valid_schemas:
        return HttpResponseBadRequest("Unknown schema")
    tables = get_tables(db_alias, schema_name, refresh=False)
    if table_name not in tables:
        return HttpResponseBadRequest("Unknown table")
    columns, pk_columns = get_table_meta(db_alias, schema_name, table_name, refresh=False)
    pk_uses_sequence = get_pk_sequence_columns(db_alias, schema_name, table_name, refresh=False)
    column_names = [c["name"] for c in columns]
    col_allowlist = set(column_names)
    pk_set = set(pk_columns)
    column_by_name = {c["name"]: c for c in columns}

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid JSON"})
    cols = payload.get("columns")
    if not isinstance(cols, dict):
        return JsonResponse({"ok": False, "error": "Missing or invalid 'columns' object"})

    # Columns to insert: all columns except PK columns that use nextval (omitted so DB fills them).
    # For other PK columns we require a value. For non-PK, use value or NULL if nullable.
    insert_cols = []
    for c in column_names:
        if c in pk_uses_sequence:
            continue  # omit; PostgreSQL will use nextval
        if c not in col_allowlist:
            continue
        val = cols.get(c)
        is_empty = val is None or (isinstance(val, str) and val.strip() == "")
        if c in pk_set and is_empty:
            return JsonResponse({"ok": False, "error": f"Primary key column '{c}' is required (no sequence)."})
        col_info = column_by_name.get(c) or {}
        if is_empty and not col_info.get("is_nullable"):
            return JsonResponse({"ok": False, "error": f"Non-nullable column '{c}' requires a value."})
        insert_cols.append(c)

    if not insert_cols:
        return JsonResponse({"ok": False, "error": "No columns to insert"})

    from django.db import connections
    conn = connections[db_alias]
    quoted_schema = conn.ops.quote_name(schema_name)
    quoted_table = conn.ops.quote_name(table_name)
    values = []
    for c in insert_cols:
        val = cols.get(c)
        if val is None or (isinstance(val, str) and val.strip() == ""):
            values.append(None)
        else:
            data_type = (column_by_name.get(c) or {}).get("data_type")
            values.append(_coerce_value(val, data_type))

    quoted_cols = [conn.ops.quote_name(c) for c in insert_cols]
    placeholders = ["%s"] * len(insert_cols)
    sql = f'INSERT INTO {quoted_schema}.{quoted_table} ({", ".join(quoted_cols)}) VALUES ({", ".join(placeholders)})'
    try:
        with transaction.atomic(using=db_alias):
            with conn.cursor() as cur:
                cur.execute(sql, values)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)})

    return JsonResponse({"ok": True, "inserted": 1})


@login_required
def table_delete_rows(request, db_alias, schema_name, table_name):
    """POST: hard delete rows by primary key."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    if db_alias not in settings.EDITABLE_DATABASES:
        return HttpResponseBadRequest("Unknown database")
    valid_schemas = get_schemas(db_alias, refresh=False)
    if schema_name not in valid_schemas:
        return HttpResponseBadRequest("Unknown schema")
    tables = get_tables(db_alias, schema_name, refresh=False)
    if table_name not in tables:
        return HttpResponseBadRequest("Unknown table")
    columns, pk_columns = get_table_meta(db_alias, schema_name, table_name, refresh=False)
    if not pk_columns:
        return JsonResponse({"ok": False, "error": "Table has no primary key"})
    pk_set = set(pk_columns)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid JSON"})
    pks = payload.get("pks")
    if not isinstance(pks, list):
        return JsonResponse({"ok": False, "error": "Missing or invalid 'pks' array"})

    from django.db import connections
    conn = connections[db_alias]
    quoted_schema = conn.ops.quote_name(schema_name)
    quoted_table = conn.ops.quote_name(table_name)
    deleted = 0
    errors = []
    try:
        with transaction.atomic(using=db_alias):
            with conn.cursor() as cur:
                for pk in pks:
                    if not isinstance(pk, dict) or not pk_set.issubset(set(pk.keys())):
                        errors.append({"pk": pk, "error": "Invalid or missing primary key"})
                        continue
                    where_parts = [f'{conn.ops.quote_name(k)} = %s' for k in pk_columns]
                    where_vals = [pk[k] for k in pk_columns]
                    sql = f'DELETE FROM {quoted_schema}.{quoted_table} WHERE {" AND ".join(where_parts)}'
                    try:
                        cur.execute(sql, where_vals)
                        deleted += cur.rowcount
                    except Exception as e:
                        errors.append({"pk": pk, "error": str(e)})
            if errors:
                raise ValueError("Delete errors")
        return JsonResponse({"ok": True, "deleted": deleted})
    except ValueError:
        return JsonResponse({"ok": False, "errors": errors})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)})
