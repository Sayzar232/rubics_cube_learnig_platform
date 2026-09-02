# -*- coding: utf-8 -*-
"""Разовая миграция: href="#/path" -> href="/path" (переход с hash-роутинга на History API)."""
from pathlib import Path

FILES = [
    Path("frontend/src/App.vue"),
    Path("frontend/src/landing-body.html"),
    Path("frontend/index.html"),
]

for file in FILES:
    data = file.read_bytes()
    count = data.count(b'href="#/')
    data = data.replace(b'href="#/', b'href="/')
    file.write_bytes(data)
    print(f"{file}: заменено {count}")
