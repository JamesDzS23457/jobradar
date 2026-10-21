import json
import logging
import re
from typing import Any

from openai import OpenAI

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

PROFILE_SCHEMA = """
Devuelve SOLO un objeto JSON con estas claves:
{
  "name": string,
  "email": string,
  "phone": string,
  "location": string,
  "headline": string,
  "summary": string,
  "skills": [string],
  "experience": [{"company": string, "role": string, "dates": string, "bullets": [string]}],
  "education": [{"institution": string, "degree": string, "dates": string}],
  "languages": {"Idioma": "nivel"},
  "links": {"LinkedIn": string, "GitHub": string, "Portafolio": string},
  "years_experience": number
}
No inventes información. Si un dato no aparece, usa string vacío, lista vacía o 0.
"""

JOB_SCHEMA = """
Devuelve SOLO un objeto JSON con estas claves:
{
  "skills_required": [string],
  "skills_nice": [string],
  "seniority": "junior" | "mid" | "senior" | "lead",
  "years_experience": number,
  "languages": {"Idioma": "nivel mínimo"},
  "red_flags": [string]
}
No inventes requisitos que no estén en la descripción.
"""

TAILOR_SCHEMA = """
Devuelve SOLO un objeto JSON con estas claves:
{
  "headline": string,
  "summary": string,
  "skills_priority": [string],
  "experience": [{"company": string, "role": string, "dates": string, "bullets": [string], "source_bullets": [number]}],
  "education": [{"institution": string, "degree": string, "dates": string}],
  "keywords_added": [string],
  "cover_letter": string,
  "strengths": [string],
  "gaps": [string],
  "warnings": [string]
}
Reglas estrictas:
- No inventes empresas, cargos, fechas, títulos, certificaciones ni métricas.
- Solo reformula y reordena información real del perfil.
- Cada bullet nuevo debe estar respaldado por un bullet del perfil; indica sus índices en source_bullets.
- Si no puedes respaldar un bullet, no lo incluyas.
- Máximo 2 páginas.
- Formato ATS, sin tablas ni columnas.
"""


class LLMService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client: OpenAI | None = None

    @property
    def configured(self) -> bool:
        return self.settings.llm_configured

    def _get_client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(
                api_key=self.settings.llm_api_key,
                base_url=self.settings.llm_base_url,
            )
        return self._client

    def _chat_json(self, system: str, user: str, model: str | None = None) -> dict[str, Any] | None:
        if not self.configured:
            return None
        client = self._get_client()
        try:
            response = client.chat.completions.create(
                model=model or self.settings.llm_model_fast,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_object"},
            )
        except Exception as exc:  # pragma: no cover - provider dependent
            logger.warning("LLM call failed, retrying without response_format: %s", exc)
            try:
                response = client.chat.completions.create(
                    model=model or self.settings.llm_model_fast,
                    temperature=0.2,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                )
            except Exception as retry_exc:  # pragma: no cover
                logger.error("LLM call failed: %s", retry_exc)
                return None

        content = response.choices[0].message.content or ""
        content = re.sub(r"^```(?:json)?\s*", "", content.strip())
        content = re.sub(r"\s*```$", "", content)
        try:
            data = json.loads(content)
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            logger.warning("LLM returned invalid JSON: %s", content[:300])
            return None

    def extract_profile(self, text: str) -> dict[str, Any] | None:
        return self._chat_json(
            "Eres un experto en reclutamiento que estructura hojas de vida. " + PROFILE_SCHEMA,
            text[:20000],
        )

    def extract_job(self, title: str, description: str) -> dict[str, Any] | None:
        return self._chat_json(
            "Eres un analista de ofertas laborales. " + JOB_SCHEMA,
            f"Título: {title}\n\nDescripción:\n{description[:12000]}",
        )

    def tailor_cv(self, profile: dict[str, Any], job: dict[str, Any]) -> dict[str, Any] | None:
        return self._chat_json(
            "Eres un experto en optimización de CV para ATS. " + TAILOR_SCHEMA,
            f"PERFIL:\n{json.dumps(profile, ensure_ascii=False)}\n\nOFERTA:\n{json.dumps(job, ensure_ascii=False)}",
            model=self.settings.llm_model_quality,
        )


llm_service = LLMService()
