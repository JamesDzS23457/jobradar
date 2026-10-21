import json
import logging
import re
import time
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
  "years_experience": number,
  "warnings": [string]
}
Reglas:
- Extrae TODA la experiencia, educación, certificaciones, idiomas y enlaces que aparezcan.
- Conserva las fechas tal como aparecen; no las inventes.
- Cada bullet de experiencia debe ser una frase concreta del CV, no una paráfrasis genérica.
- No inventes empresas, cargos, fechas, títulos, tecnologías ni métricas.
- Si un dato no aparece, usa string vacío, lista vacía, objeto vacío o 0.
- "warnings" debe listar datos que no pudiste leer con claridad.
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
- Usa las palabras clave de la oferta solo cuando sean verdaderas en el perfil.
"""

ANSWER_SCHEMA = """
Devuelve SOLO un objeto JSON con esta forma:
{
  "answers": [
    {
      "question": string,
      "answer": string,
      "confidence": "high" | "medium" | "low",
      "needs_user_input": boolean,
      "source": string
    }
  ]
}
Reglas:
- Responde en primera persona, en el idioma de la pregunta.
- Usa únicamente datos del perfil y del CV. No inventes experiencia, salario, disponibilidad,
  autorización de trabajo, discapacidad, veteranía, género ni datos sensibles.
- Si falta un dato, deja "answer" vacío y marca needs_user_input=true.
- Para preguntas de motivación, conecta experiencia real con la vacante.
- Sé breve: máximo 120 palabras por respuesta.
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
            headers: dict[str, str] = {}
            if "openrouter.ai" in self.settings.llm_base_url:
                headers = {
                    "HTTP-Referer": "http://localhost:5173",
                    "X-Title": "JobRadar",
                }
            self._client = OpenAI(
                api_key=self.settings.resolved_llm_api_key,
                base_url=self.settings.llm_base_url,
                timeout=self.settings.llm_timeout_seconds,
                default_headers=headers,
            )
        return self._client

    def _model_chain(self, model: str | None, quality: bool = False) -> list[str]:
        primary = model or (
            self.settings.llm_model_quality if quality else self.settings.llm_model_fast
        )
        chain = [primary]
        for candidate in (self.settings.llm_model_fallback, self.settings.llm_model_quality):
            if candidate and candidate not in chain:
                chain.append(candidate)
        return chain

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any] | None:
        content = (raw or "").strip()
        content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.I)
        content = re.sub(r"\s*```$", "", content)
        # Some providers wrap JSON in a short explanation. Try the first object.
        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            content = content[start : end + 1]
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None

    def _repair_json(self, client: OpenAI, model: str, raw: str) -> dict[str, Any] | None:
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=0,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Eres un reparador de JSON. Devuelve únicamente el objeto JSON válido, "
                            "sin markdown, sin explicaciones y sin cambiar la información."
                        ),
                    },
                    {"role": "user", "content": raw[:30000]},
                ],
            )
            return self._parse_json(response.choices[0].message.content or "")
        except Exception as exc:  # pragma: no cover - provider dependent
            logger.debug("JSON repair failed with %s: %s", model, exc)
            return None

    def _chat_json(
        self,
        system: str,
        user: str,
        model: str | None = None,
        quality: bool = False,
        temperature: float = 0.2,
    ) -> dict[str, Any] | None:
        if not self.configured:
            return None
        client = self._get_client()
        for candidate in self._model_chain(model, quality=quality):
            response = None
            try:
                response = client.chat.completions.create(
                    model=candidate,
                    temperature=temperature,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    response_format={"type": "json_object"},
                )
            except Exception as exc:  # pragma: no cover - provider dependent
                logger.warning("LLM call failed with %s (%s); retrying without JSON mode", candidate, exc)
                try:
                    response = client.chat.completions.create(
                        model=candidate,
                        temperature=temperature,
                        messages=[
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                    )
                except Exception as retry_exc:  # pragma: no cover
                    logger.warning("LLM call failed with %s: %s", candidate, retry_exc)
                    continue

            raw = response.choices[0].message.content or ""
            data = self._parse_json(raw)
            if data is not None:
                return data
            logger.warning("LLM returned invalid JSON with %s: %s", candidate, raw[:300])
            repaired = self._repair_json(client, candidate, raw)
            if repaired is not None:
                return repaired
        return None

    def test_connection(self) -> dict[str, Any]:
        if not self.configured:
            return {
                "ok": False,
                "message": "Configura LLM_API_KEY para probar el proveedor.",
                "provider": self.settings.llm_provider,
            }
        started = time.perf_counter()
        result = self._chat_json(
            "Devuelve SOLO JSON válido.",
            'Devuelve {"ok": true}.',
            model=self.settings.llm_model_fast,
        )
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        if result is None:
            return {
                "ok": False,
                "message": "El proveedor no devolvió JSON válido. Revisa la clave, el modelo o la cuota.",
                "provider": self.settings.llm_provider,
                "model": self.settings.llm_model_fast,
                "elapsed_ms": elapsed_ms,
            }
        return {
            "ok": True,
            "message": "Conexión correcta.",
            "provider": self.settings.llm_provider,
            "model": self.settings.llm_model_fast,
            "elapsed_ms": elapsed_ms,
        }

    def extract_profile(self, text: str) -> dict[str, Any] | None:
        return self._chat_json(
            "Eres un experto en reclutamiento y parsing de hojas de vida. " + PROFILE_SCHEMA,
            f"CV COMPLETO:\n{text[:60000]}",
            model=self.settings.llm_model_quality,
            quality=True,
            temperature=0.1,
        )

    def extract_job(self, title: str, description: str) -> dict[str, Any] | None:
        return self._chat_json(
            "Eres un analista de ofertas laborales. " + JOB_SCHEMA,
            f"Título: {title}\n\nDescripción:\n{description[:20000]}",
        )

    def tailor_cv(self, profile: dict[str, Any], job: dict[str, Any]) -> dict[str, Any] | None:
        return self._chat_json(
            "Eres un experto en optimización de CV para ATS. " + TAILOR_SCHEMA,
            f"PERFIL:\n{json.dumps(profile, ensure_ascii=False)}\n\nOFERTA:\n{json.dumps(job, ensure_ascii=False)[:30000]}",
            model=self.settings.llm_model_quality,
            quality=True,
            temperature=0.15,
        )

    def draft_answers(
        self,
        profile: dict[str, Any],
        job: dict[str, Any],
        questions: list[str],
    ) -> dict[str, Any] | None:
        if not questions:
            return {"answers": []}
        return self._chat_json(
            "Eres un asistente de postulaciones. " + ANSWER_SCHEMA,
            (
                f"PERFIL:\n{json.dumps(profile, ensure_ascii=False)}\n\n"
                f"VACANTE:\n{json.dumps(job, ensure_ascii=False)[:25000]}\n\n"
                f"PREGUNTAS:\n{json.dumps(questions[:30], ensure_ascii=False)}"
            ),
            model=self.settings.llm_model_quality,
            quality=True,
            temperature=0.25,
        )


llm_service = LLMService()
