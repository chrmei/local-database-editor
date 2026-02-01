import json
from datetime import date, datetime, time
from decimal import Decimal
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


def _json_serial(val):
    """Convert common DB types to JSON-serializable form for data-pk."""
    if val is None:
        return None
    if isinstance(val, (datetime, date, time)):
        return val.isoformat()
    if isinstance(val, Decimal):
        return str(val)
    return val


@register.filter
def get_item(d, key):
    """Get dict value by key: {{ row|get_item:col_name }}"""
    if d is None:
        return ""
    val = d.get(key)
    return "" if val is None else str(val)


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
