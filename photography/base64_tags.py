# myapp/templatetags/base64_tags.py

import base64
import os
from django import template
from django.contrib.staticfiles import finders
from django.conf import settings

register = template.Library()

@register.simple_tag
def static_base64(image_path):
    """Convert a static image to base64 data URI - works in dev and production"""
    
    # Method 1: Try staticfiles finders (works in dev)
    full_path = finders.find(image_path)
    
    # Method 2: Try STATIC_ROOT directly (works in production after collectstatic)
    if not full_path:
        full_path = os.path.join(settings.STATIC_ROOT, image_path)
        if not os.path.exists(full_path):
            full_path = None
    
    if not full_path:
        return ''
    
    try:
        with open(full_path, 'rb') as f:
            encoded = base64.b64encode(f.read()).decode('utf-8')
        ext = image_path.rsplit('.', 1)[-1].lower()
        mime = {'jpg': 'jpeg', 'jpeg': 'jpeg', 'png': 'png', 'gif': 'gif', 'svg': 'svg+xml'}.get(ext, 'png')
        return f"data:image/{mime};base64,{encoded}"
    except Exception:
        return ''