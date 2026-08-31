"""Send account verification emails via SMTP.BZ HTTP API, classic SMTP, or dev-logging."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr, parseaddr

import requests

from ..core.config import Settings, get_settings

logger = logging.getLogger(__name__)

VERIFICATION_EMAIL_SUBJECT = "CubeLearn — подтвердите вашу почту"


def _build_verification_bodies(username, verification_url, expire_hours):
    display_name = username or "кубербер"
    text_body = (
        f"Привет, {display_name}!\n\n"
        "Вы зарегистрировались на CubeLearn. Чтобы активировать аккаунт, "
        "подтвердите почту по ссылке:\n"
        f"{verification_url}\n\n"
        f"Ссылка действует {expire_hours} ч. Если вы не регистрировались — просто проигнорируйте это письмо.\n\n"
        "— команда CubeLearn"
    )
    html_body = f"""\
<div style="font-family:Segoe UI,Arial,sans-serif;max-width:520px;margin:0 auto;padding:32px;background:#ffffff;border-radius:12px;">
  <h1 style="margin:0 0 16px;color:#1a1a2e;font-size:22px;">Подтвердите почту</h1>
  <p style="margin:0 0 20px;color:#333;font-size:15px;line-height:1.5;">
    Привет, <b>{display_name}</b>! Вы создали аккаунт на CubeLearn.<br/>
    Нажмите кнопку ниже, чтобы подтвердить почту и начать учить OLL и PLL алгоритмы.
  </p>
  <p style="margin:0 0 20px;">
    <a href="{verification_url}"
       style="display:inline-block;padding:12px 28px;background:#e21a37;color:#ffffff;text-decoration:none;border-radius:8px;font-size:15px;font-weight:600;">
      Подтвердить почту
    </a>
  </p>
  <p style="margin:0 0 8px;color:#666;font-size:13px;">Или скопируйте ссылку в браузер:</p>
  <p style="margin:0;color:#0044cc;font-size:13px;word-break:break-all;">{verification_url}</p>
  <hr style="border:none;border-top:1px solid #eeeeee;margin:24px 0;"/>
  <p style="margin:0;color:#999;font-size:12px;">
    Ссылка действует {expire_hours} ч. Если вы не регистрировались на CubeLearn — проигнорируйте это письмо.
  </p>
</div>"""
    return text_body, html_body


def _compose_message(to_email, text_body, html_body):
    message = EmailMessage()
    message["Subject"] = VERIFICATION_EMAIL_SUBJECT
    message["To"] = to_email

    sender = parseaddr(get_settings().smtp_from)[1] or "no-reply@cubelearn.local"
    display_name = "CubeLearn"
    message["From"] = formataddr((display_name, sender))

    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")
    return message


def _smtp_send(message):
    settings = get_settings()
    use_ssl = settings.smtp_use_ssl or settings.smtp_port == 465
    server_cls = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
    with server_cls(settings.smtp_host, settings.smtp_port, timeout=20) as server:
        if not use_ssl and settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_user and settings.smtp_password:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(message)


def _api_send(from_email, to_email, subject, text_body, html_body):
    """Отправка через HTTP API SMTP.BZ. Работает там, где закрыты SMTP-порты (например, Render.com)."""
    settings = get_settings()
    payload = {
        "from": from_email,
        "to": to_email,
        "subject": subject,
        "text": text_body,
        "html": html_body,
    }
    response = requests.post(
        settings.email_api_url,
        json=payload,
        headers={"Authorization": settings.email_api_key},
        timeout=20,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"SMTP.BZ API ответила {response.status_code}: {response.text[:300]}")
    body = response.json() if response.content else {}
    if body.get("result") is not True:
        raise RuntimeError(f"SMTP.BZ API отклонила письмо: {str(body)[:300]}")


def send_verification_email(to_email, username, verification_url):
    """Транспорт: 1) EMAIL_API_KEY задан, HTTP API SMTP.BZ; 2) SMTP_HOST задан, SMTP; 3) иначе dev-лог."""
    settings = get_settings()
    expire_hours = max(1, settings.email_verification_expire_minutes // 60)
    text_body, html_body = _build_verification_bodies(username, verification_url, expire_hours)

    try:
        if settings.email_api_key:
            _api_send(
                from_email=parseaddr(settings.smtp_from)[1] or "no-reply@cubelearn.local",
                to_email=to_email,
                subject=VERIFICATION_EMAIL_SUBJECT,
                text_body=text_body,
                html_body=html_body,
            )
        elif settings.smtp_host:
            _smtp_send(_compose_message(to_email, text_body, html_body))
        else:
            logger.info(
                "[email] EMAIL_API_KEY и SMTP_HOST не заданы — dev-режим, письмо не отправлено.\n"
                "олучатель: %s\nСсылка подтверждения: %s",
                to_email,
                verification_url,
            )
            return
        logger.info("[email] исьмо подтверждения отправлено на %s", to_email)
    except Exception:  # noqa: BLE001 - фоновой задачей логируем и продолжаем работу API
        logger.exception("[email] е удалось отправить письмо на %s", to_email)
