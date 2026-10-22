"""Alertas por correo configurables mediante variables de entorno."""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage


def enviar_alerta_email(asunto: str, cuerpo: str) -> tuple[bool, str]:
    """Envía una alerta SMTP o devuelve un error explícito si no está configurado."""
    host = os.getenv("AGRO_SMTP_HOST")
    destinatario = os.getenv("AGRO_ALERT_EMAIL")
    if not host or not destinatario:
        return False, "SMTP no configurado (AGRO_SMTP_HOST/AGRO_ALERT_EMAIL)."
    mensaje = EmailMessage()
    mensaje["Subject"] = asunto
    mensaje["From"] = os.getenv("AGRO_SMTP_USER", destinatario)
    mensaje["To"] = destinatario
    mensaje.set_content(cuerpo)
    try:
        with smtplib.SMTP(host, int(os.getenv("AGRO_SMTP_PORT", "587")), timeout=10) as smtp:
            smtp.starttls()
            user = os.getenv("AGRO_SMTP_USER")
            password = os.getenv("AGRO_SMTP_PASSWORD")
            if user and password:
                smtp.login(user, password)
            smtp.send_message(mensaje)
    except (OSError, smtplib.SMTPException, ValueError) as exc:
        return False, f"No se pudo enviar la alerta: {exc}"
    return True, "Alerta enviada."
