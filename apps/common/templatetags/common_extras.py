from django import template


register = template.Library()


@register.filter
def minutes_to_hours(value):
    try:
        hours = float(value) / 60
    except (TypeError, ValueError):
        return value

    formatted = "{0:.2f}".format(hours).rstrip("0").rstrip(".")
    return formatted or "0"
