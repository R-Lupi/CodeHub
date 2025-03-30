from django import template
import json

register = template.Library()

@register.filter
def json_dumps(value):
    return json.dumps(value)

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, '')