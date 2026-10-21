"""Portal capability registry.

The registry is deliberately conservative:

* ``manual_only`` portals are never automated.
* ``auto_submit`` portals must be in the configured allowlist.
* unknown domains can use the user-initiated assistant, but never auto-submit.
* every new/unknown portal starts as assisted-without-auto-submit.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from urllib.parse import urlparse

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class PortalInfo:
    source: str
    label: str
    domain: str
    mode: str
    can_assist: bool
    can_auto_submit: bool
    reason: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PortalRule:
    source: str
    label: str
    domains: tuple[str, ...]
    mode: str = "assisted"


RULES: tuple[PortalRule, ...] = (
    PortalRule("linkedin", "LinkedIn", ("linkedin.com",), "manual_only"),
    PortalRule("indeed", "Indeed", ("indeed.com",), "manual_only"),
    PortalRule("computrabajo", "Computrabajo", ("computrabajo.com",), "manual_only"),
    PortalRule("elempleo", "elempleo", ("elempleo.com",), "manual_only"),
    PortalRule("magneto", "Magneto", ("magneto.com.co", "magneto.co"), "manual_only"),
    PortalRule("glassdoor", "Glassdoor", ("glassdoor.com",), "manual_only"),
    PortalRule("greenhouse", "Greenhouse", ("greenhouse.io",), "auto_submit"),
    PortalRule("lever", "Lever", ("lever.co",), "auto_submit"),
    PortalRule("ashby", "Ashby", ("ashbyhq.com",), "auto_submit"),
    PortalRule("workable", "Workable", ("workable.com",), "auto_submit"),
    PortalRule("breezy", "Breezy HR", ("breezy.hr",), "auto_submit"),
    PortalRule("teamtailor", "Teamtailor", ("teamtailor.com",), "auto_submit"),
    PortalRule("smartrecruiters", "SmartRecruiters", ("smartrecruiters.com",), "assisted"),
    PortalRule("recruitee", "Recruitee", ("recruitee.com",), "assisted"),
    PortalRule("bamboohr", "BambooHR", ("bamboohr.com",), "assisted"),
    PortalRule("workday", "Workday", ("myworkdayjobs.com", "workday.com"), "assisted"),
    PortalRule("getonbrd", "GetOnBoard", ("getonbrd.com",), "assisted"),
    PortalRule("torre", "Torre", ("torre.ai",), "assisted"),
    PortalRule("workana", "Workana", ("workana.com",), "assisted"),
)


def _hostname(url: str) -> str:
    try:
        host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""
    return host


def _match_rule(host: str) -> PortalRule | None:
    for rule in RULES:
        if any(host == domain or host.endswith(f".{domain}") for domain in rule.domains):
            return rule
    return None


def classify_portal(url: str, settings: Settings | None = None) -> PortalInfo:
    settings = settings or get_settings()
    host = _hostname(url)
    rule = _match_rule(host)
    source = rule.source if rule else (host.split(".")[0] if host else "unknown")
    label = rule.label if rule else (source.replace("-", " ").title() or "Portal")
    domain = host or "unknown"

    if not host:
        return PortalInfo(
            source="unknown",
            label="Sin enlace",
            domain="unknown",
            mode="manual_only",
            can_assist=False,
            can_auto_submit=False,
            reason="La vacante no tiene un enlace de postulación.",
        )

    if source in settings.manual_only_portals_list:
        return PortalInfo(
            source=source,
            label=label,
            domain=domain,
            mode="manual_only",
            can_assist=False,
            can_auto_submit=False,
            reason="Este portal prohíbe la automatización. Abre la vacante y postúlate allí.",
        )

    if source in settings.auto_submit_portals_list:
        return PortalInfo(
            source=source,
            label=label,
            domain=domain,
            mode="auto_submit",
            can_assist=True,
            can_auto_submit=True,
            reason="Portal compatible con el asistente y con auto-envío opcional.",
        )

    if rule is not None:
        return PortalInfo(
            source=source,
            label=label,
            domain=domain,
            mode="assisted",
            can_assist=True,
            can_auto_submit=False,
            reason="Portal asistido: la IA puede rellenar, pero tú confirmas el envío.",
        )

    return PortalInfo(
        source=source,
        label=label,
        domain=domain,
        mode="assisted",
        can_assist=True,
        can_auto_submit=False,
        reason="Portal no verificado: puedes usar el asistente, pero el auto-envío está desactivado.",
    )
