"""Send account verification emails over SMTP."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr, parseaddr

from ..core.config import Settings, get_settings

logger = logging.getLogger(__name__)

VERIFICATION_EMAIL_SUBJECT = "CubeLearn — подтвердите вашу почту"


def _build_verification_bodies(username: str, verification_url: str, expire_hours: int) -> tuple[str, str]:
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


def _compose_message(to_email: str, text_body: str, html_body: str) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = VERIFICATION_EMAIL_SUBJECT
    message["To"] = to_email

    sender = parseaddr(get_settings().smtp_from)[1] or "no-reply@cubelearn.local"
    display_name = "CubeLearn"
    message["From"] = formataddr((display_name, sender))

    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")
    return message


def _smtp_send(message: EmailMessage) -> None:
    settings: Settings = get_settings()
    use_ssl = settings.smtp_use_ssl or settings.smtp_port == 465
    server_cls = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
    with server_cls(settings.smtp_host, settings.smtp_port, timeout=20) as server:
        if not use_ssl and settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_user and settings.smtp_password:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(message)


def send_verification_email(*, to_email: str, username: str, verification_url: str) -> None:
    """Отправляет письмо со ссылкой подтверждения.

    Если SMTP не настроен (SMTP_HOST пуст) — печатает ссылку в лог приложения,
    чтобы флоу можно было проверить локально без почтового сервера.
    """
    settings = get_settings()
    expire_hours = max(1, settings.email_verification_expire_minutes // 60)
    text_body, html_body = _build_verification_bodies(username, verification_url, expire_hours)

    if not settings.smtp_host:
        logger.info(
            "[email] SMTP_HOST не задан — письмо не отправлено.\n"
            "Получатель: %s\nСсылка подтверждения: %s",
            to_email,
            verification_url,
        )
        return

    try:
        _smtp_send(_compose_message(to_email, text_body, html_body))
        logger.info("[email] Письмо подтверждения отправлено на %s", to_email)
    except Exception:  # noqa: BLE001 — фоновой задачей логируем и продолжаем работу API
        logger.exception("[email] Не удалось отправить письмо на %s", to_email)