import json
from datetime import date, datetime, time
from decimal import Decimal
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# PostgreSQL information_schema.data_type values that map to HTML input types
DATE_TYPES = {"date"}
TIMESTAMP_TYPES = {"timestamp with time zone", "timestamp without time zone"}
TIME_TYPES = {"time with time zone", "time without time zone"}
NUMERIC_TYPES = {
    "integer", "bigint", "smallint", "numeric", "decimal",
    "real", "double precision", "serial", "bigserial",
}
BOOLEAN_TYPES = {"boolean"}


def _json_serial(val):
    """Convert common DB types to JSON-serializable form for data-pk."""
    if val is None:
        return None
    if isinstance(val, (datetime, date, time)):
        return val.isoformat()
    if isinstance(val, Decimal):
        return str(val)
    return val


def _html_input_type(data_type):
    """Return HTML input type for a PostgreSQL data_type."""
    if not data_type:
        return "text"
    dt = data_type.strip().lower()
    if dt in DATE_TYPES:
        return "date"
    if dt in TIMESTAMP_TYPES:
        return "datetime-local"
    if dt in TIME_TYPES:
        return "time"
    if dt in NUMERIC_TYPES:
        return "number"
    if dt in BOOLEAN_TYPES:
        return "checkbox"
    return "text"


def _format_input_value(val, data_type):
    """Format a value for use in an HTML input (date → YYYY-MM-DD, etc.)."""
    if val is None or (isinstance(val, str) and val.strip() == ""):
        return ""
    if not data_type:
        return str(val)
    dt = data_type.strip().lower()
    if dt in DATE_TYPES:
        if isinstance(val, date):
            return val.isoformat()
        if isinstance(val, datetime):
            return val.date().isoformat()
        return str(val)[:10] if len(str(val)) >= 10 else str(val)
    if dt in TIMESTAMP_TYPES:
        if isinstance(val, datetime):
            # datetime-local expects no timezone; use naive ISO format
            if val.tzinfo:
                val = val.astimezone().replace(tzinfo=None)
            return val.isoformat(" ").replace(" ", "T")[:19]
        if isinstance(val, date) and not isinstance(val, datetime):
            return val.isoformat() + "T00:00:00"
        s = str(val)
        if " " in s:
            s = s.replace(" ", "T", 1)[:19]
        return s
    if dt in TIME_TYPES:
        if isinstance(val, time):
            return val.isoformat()[:12]  # HH:MM:SS or HH:MM:SS.ffffff
        return str(val)[:12]
    if dt in BOOLEAN_TYPES:
        if isinstance(val, bool):
            return "true" if val else "false"
        s = str(val).strip().lower()
        return "true" if s in ("t", "true", "1", "yes", "on") else "false"
    return str(val)


@register.filter
def get_item(d, key):
    """Get dict value by key: {{ row|get_item:col_name }}"""
    if d is None:
        return ""
    val = d.get(key)
    return "" if val is None else str(val)


@register.filter
def input_type_for_column(column):
    """Return HTML input type for a column dict with 'data_type' key."""
    if not column or not isinstance(column, dict):
        return "text"
    return _html_input_type(column.get("data_type") or "")


@register.filter
def input_value_for_column(row, column):
    """Format row value for the column's input (date → YYYY-MM-DD, etc.)."""
    if not column or not isinstance(column, dict):
        return ""
    key = column.get("name")
    if key is None:
        return ""
    val = row.get(key) if row else None
    return _format_input_value(val, column.get("data_type") or "")


@register.filter
def pk_json(row, pk_columns):
    """Serialize primary key from row dict as JSON for data-pk attribute.
    
    Returns unescaped JSON - Django's autoescaping will handle HTML escaping.
    Do NOT use mark_safe here as the quotes need to be escaped for HTML attributes.
    """
    if not row or not pk_columns:
        return "{}"
    pk = {k: _json_serial(row.get(k)) for k in pk_columns}
    return json.dumps(pk)


@register.filter
def to_json(val):
    """Serialize value to JSON (e.g. for script tag)."""
    return mark_safe(json.dumps(val))
