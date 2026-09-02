# -*- coding: utf-8 -*-
"""Проверка JSON-LD в собранном dist/index.html."""
import json
import re

html = open("frontend/dist/index.html", encoding="utf-8").read()
match = re.search(r'application/ld\+json">(.*?)</script>', html, re.S)
data = json.loads(match.group(1))
types = [item["@type"] for item in data["@graph"]]
faq_count = len(data["@graph"][1]["mainEntity"])
print(f"JSON-LD OK: {types}, вопросов в FAQPage: {faq_count}")
print("BOM в начале файла:", html.startswith("\ufeff"))
print("Canonical:", re.search(r'rel="canonical" href="([^"]+)"', html).group(1))
