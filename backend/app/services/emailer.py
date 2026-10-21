import html
import logging
import smtplib
from email.message import EmailMessage

from jinja2 import Template
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models import AlertLog, Job, Match, Preferences

logger = logging.getLogger(__name__)

ALERT_TEMPLATE = Template(
    """
<!doctype html>
<html lang="es">
  <body style="margin:0;background:#f4f7fb;font-family:Inter,Arial,sans-serif;color:#0f172a;">
    <div style="max-width:640px;margin:0 auto;padding:28px 18px;">
      <div style="background:#0b1220;border-radius:18px;padding:22px 24px;color:#e5eefc;">
        <div style="font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:#34d399;">{{ app_name }} · alerta de match</div>
        <h1 style="margin:10px 0 4px;font-size:24px;line-height:1.25;">{{ score }}% · {{ job.title }}</h1>
        <p style="margin:0;color:#9fb0c7;">{{ job.company }} · {{ job.location_text }}</p>
      </div>

      <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:18px;padding:22px 24px;margin-top:14px;">
        <p style="margin:0 0 14px;font-size:15px;color:#334155;">{{ recommendation }}</p>

        <h2 style="font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:#64748b;margin:18px 0 8px;">Por qué encajas</h2>
        <ul style="margin:0;padding-left:18px;color:#0f172a;font-size:14px;line-height:1.7;">
          {% for reason in reasons %}<li>{{ reason }}</li>{% endfor %}
        </ul>

        {% if gaps %}
        <h2 style="font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:#64748b;margin:18px 0 8px;">Brechas a revisar</h2>
        <ul style="margin:0;padding-left:18px;color:#475569;font-size:14px;line-height:1.7;">
          {% for gap in gaps %}<li>{{ gap }}</li>{% endfor %}
        </ul>
        {% endif %}

        <div style="margin-top:22px;">
          <a href="{{ app_url }}" style="display:inline-block;background:#10b981;color:#04140f;text-decoration:none;font-weight:700;padding:11px 18px;border-radius:10px;">Ver en {{ app_name }}</a>
          <a href="{{ job.url }}" style="display:inline-block;margin-left:8px;color:#0f766e;text-decoration:none;font-weight:600;padding:11px 12px;">Oferta original</a>
        </div>
      </div>

      <p style="font-size:12px;color:#94a3b8;line-height:1.6;margin-top:16px;">
        Recibes este correo porque configuraste alertas en {{ app_name }}. Puedes desactivarlas en Ajustes.
      </p>
    </div>
  </body>
</html>
"""
)


DIGEST_TEMPLATE = Template(
    """
<!doctype html>
<html lang="es">
  <body style="margin:0;background:#f4f7fb;font-family:Inter,Arial,sans-serif;color:#0f172a;">
    <div style="max-width:680px;margin:0 auto;padding:28px 18px;">
      <div style="background:#0b1220;border-radius:18px;padding:22px 24px;color:#e5eefc;">
        <div style="font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:#34d399;">{{ app_name }} · resumen diario</div>
        <h1 style="margin:10px 0 4px;font-size:24px;line-height:1.25;">{{ count }} vacantes para revisar</h1>
        <p style="margin:0;color:#9fb0c7;">Buenos matches que aún no has guardado ni postulado.</p>
      </div>

      {% for item in items %}
      <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:18px;padding:18px 22px;margin-top:12px;">
        <div style="display:flex;justify-content:space-between;gap:12px;">
          <div>
            <div style="font-size:12px;font-weight:700;color:#0f766e;">{{ item.score }}% de compatibilidad</div>
            <h2 style="margin:6px 0 2px;font-size:18px;line-height:1.3;">{{ item.job.title }}</h2>
            <p style="margin:0;color:#64748b;font-size:13px;">{{ item.job.company }} · {{ item.job.location_text }}</p>
          </div>
        </div>
        <p style="margin:12px 0 0;color:#334155;font-size:14px;line-height:1.6;">{{ item.recommendation }}</p>
        <div style="margin-top:14px;">
          <a href="{{ app_url }}/jobs/{{ item.job.id }}" style="display:inline-block;background:#10b981;color:#04140f;text-decoration:none;font-weight:700;padding:9px 15px;border-radius:9px;font-size:13px;">Ver vacante</a>
        </div>
      </div>
      {% endfor %}

      <p style="font-size:12px;color:#94a3b8;line-height:1.6;margin-top:16px;">
        Recibes este resumen porque configuraste alertas en {{ app_name }}. Puedes cambiar el umbral y la hora en Ajustes.
      </p>
    </div>
  </body>
</html>
"""
)


def _send(settings: Settings, subject: str, html_body: str, to: str | None = None) -> tuple[bool, str]:
    if not settings.smtp_configured:
        return False, "SMTP no configurado"
    recipient = to or settings.alert_to or settings.smtp_user
    if not recipient:
        return False, "No hay destinatario configurado"

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_user
    message["To"] = recipient
    message.set_content("Abre este correo en un cliente compatible con HTML.")
    message.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=25) as smtp:
            smtp.starttls()
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)
        return True, ""
    except Exception as exc:  # pragma: no cover - external service
        logger.exception("SMTP send failed")
        return False, str(exc)


def render_alert(job: Job, match: Match, settings: Settings | None = None) -> tuple[str, str]:
    settings = settings or get_settings()
    subject = f"Match {round(match.score)}% · {job.title} en {job.company}"
    body = ALERT_TEMPLATE.render(
        app_name=settings.app_name,
        app_url="http://localhost:5173",
        score=round(match.score),
        job=job,
        recommendation=match.recommendation,
        reasons=match.reasons or [],
        gaps=match.gaps or [],
    )
    return subject, body


def send_match_alerts(db: Session, settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    if not settings.smtp_configured:
        return 0

    matches = list(
        db.scalars(
            select(Match)
            .join(Job, Match.job_id == Job.id)
            .where(
                Match.eligible.is_(True),
                Match.score >= settings.alert_threshold,
                Job.status.notin_(["saved", "applied", "dismissed"]),
            )
            .order_by(Match.score.desc())
            .limit(10)
        ).all()
    )
    sent = 0
    for match in matches:
        already_sent = db.scalar(
            select(AlertLog.id).where(AlertLog.job_id == match.job_id, AlertLog.status == "sent")
        )
        if already_sent:
            continue
        job = db.get(Job, match.job_id)
        if job is None:
            continue
        subject, body = render_alert(job, match, settings)
        ok, error = _send(settings, subject, body)
        db.add(
            AlertLog(
                job_id=job.id,
                match_id=match.id,
                channel="email",
                status="sent" if ok else "error",
                error="" if ok else error,
            )
        )
        db.commit()
        sent += 1 if ok else 0
    return sent


def send_digest(db: Session, settings: Settings | None = None) -> int:
    """Send one daily digest with good matches that have not triggered an alert yet."""
    settings = settings or get_settings()
    if not settings.smtp_configured:
        return 0

    prefs = db.get(Preferences, 1)
    lower = prefs.digest_threshold if prefs else settings.digest_threshold
    upper = prefs.alert_threshold if prefs else settings.alert_threshold

    matches = list(
        db.scalars(
            select(Match)
            .join(Job, Match.job_id == Job.id)
            .where(
                Match.eligible.is_(True),
                Match.score >= lower,
                Match.score < upper,
                Job.status.notin_(["applied", "dismissed"]),
            )
            .order_by(Match.score.desc())
            .limit(20)
        ).all()
    )

    items: list[dict[str, object]] = []
    for match in matches:
        already_sent = db.scalar(
            select(AlertLog.id).where(AlertLog.job_id == match.job_id, AlertLog.status == "sent")
        )
        if already_sent:
            continue
        job = db.get(Job, match.job_id)
        if job is None:
            continue
        items.append(
            {
                "job": job,
                "match_id": match.id,
                "score": round(match.score),
                "recommendation": match.recommendation,
            }
        )

    if not items:
        return 0

    subject = f"{settings.app_name} · {len(items)} vacantes para revisar"
    body = DIGEST_TEMPLATE.render(
        app_name=settings.app_name,
        app_url="http://localhost:5173",
        count=len(items),
        items=items,
    )
    ok, error = _send(settings, subject, body)
    for item in items:
        job = item["job"]
        db.add(
            AlertLog(
                job_id=job.id,
                match_id=item["match_id"],
                channel="digest",
                status="sent" if ok else "error",
                error="" if ok else error,
            )
        )
    db.commit()
    return len(items) if ok else 0


def send_test_email(settings: Settings | None = None) -> tuple[bool, str]:
    settings = settings or get_settings()
    if not settings.smtp_configured:
        return False, "Configura SMTP_USER y SMTP_PASSWORD (contraseña de aplicación de Gmail)."
    subject = f"{settings.app_name} · correo de prueba"
    body = (
        "<html><body style='font-family:Arial,sans-serif;background:#0b1220;color:#e5eefc;padding:28px;'>"
        f"<h2 style='color:#34d399;'>Todo listo</h2>"
        f"<p>Este es un correo de prueba de {html.escape(settings.app_name)}. "
        "Si lo recibiste, las alertas funcionarán.</p></body></html>"
    )
    return _send(settings, subject, body)
