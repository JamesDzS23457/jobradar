# JobRadar

**Copiloto personal de búsqueda y postulación laboral.**

JobRadar convierte tu CV en un perfil estructurado, busca ofertas compatibles, las puntúa con una explicación y te ayuda a adaptar el CV a cada vacante. Está pensado para una persona ubicada en Bogotá, Colombia: prioriza presencial/híbrido en Bogotá y su área metropolitana, acepta remoto nacional y solo acepta remoto para ofertas fuera de Colombia.

> Este proyecto no postula automáticamente en portales de terceros ni scrapea LinkedIn/Indeed. Prepara el CV y la carta, y tú decides dónde y cuándo aplicar.

![Dashboard de JobRadar](docs/screenshots/dashboard.webp)

## Qué hace

- **Perfil desde el CV:** extrae nombre, contacto, skills, experiencia, educación e idiomas de PDF, DOCX, TXT o Markdown. Si no hay LLM configurado, usa heurísticas locales.
- **Búsqueda con reglas de ubicación:** Bogotá y ciudades cercanas para presencial/híbrido; resto de Colombia solo con reubicación; fuera de Colombia solo remoto.
- **Match explicable:** score de 0 a 100 con desglose por skills, rol, seniority, ubicación, idioma, salario y frescura. Cada resultado incluye razones, brechas y señales de alerta.
- **CV adaptado por vacante:** reescribe el resumen, prioriza skills y reordena experiencia usando solo información real del perfil. Genera DOCX y PDF después de tu aprobación.
- **Tracker de postulaciones:** columnas Guardadas, Postuladas, Entrevistas, Ofertas y Rechazadas.
- **Alertas por Gmail:** correo inmediato para matches excelentes y resumen diario para los buenos.
- **Modo demo:** funciona sin claves, sin red y sin datos reales. Ideal para probar la experiencia o mostrarla en un portafolio.

![Vacantes con score y filtros](docs/screenshots/jobs.webp)

## Demo

- `DEMO_MODE=true` carga un perfil de ejemplo y **18 ofertas curadas** (15 elegibles).
- No requiere claves de LLM, correo ni APIs externas.
- Los correos reales se desactivan en modo demo.
- El botón **Reiniciar demo** de Ajustes restaura perfil, ofertas y postulaciones de ejemplo.

## Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy, SQLite, APScheduler.
- **Frontend:** React 19, Vite, TypeScript, Tailwind CSS, TanStack Query, React Router, Sonner.
- **IA:** proveedor compatible con OpenAI (opcional). Sin clave funciona con heurísticas y plantillas.
- **Correo:** SMTP de Gmail con contraseña de aplicación (opcional).
- **Fuentes:** JSearch, Jooble, Remotive, RemoteOK y dataset demo.

## Inicio rápido

### Requisitos

- Python 3.12+
- Node.js 20+
- `uv` (recomendado) o `pip`

### Backend

```bash
cd backend
cp .env.example .env
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

La API queda en `http://localhost:8000`. Documentación interactiva en `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

La app queda en `http://localhost:5173`. Vite proxya `/api` hacia el backend.

También puedes usar:

```bash
make install   # instala backend y frontend
make backend   # API con reload
make frontend  # Vite
make test      # pytest
make lint      # ruff + build de TypeScript
```

## Variables de entorno

Copia `backend/.env.example` a `backend/.env` y completa solo lo que quieras usar:

| Variable | Descripción |
|---|---|
| `DEMO_MODE` | `true` carga datos de ejemplo y desactiva correos reales. |
| `DATABASE_URL` | Por defecto SQLite en `data/jobradar.db`. |
| `LLM_API_KEY` | Clave del proveedor de IA. Si está vacía, usa fallback heurístico. |
| `LLM_BASE_URL` | Endpoint compatible con OpenAI. |
| `LLM_MODEL_FAST` | Modelo para parsing y extracción. |
| `LLM_MODEL_QUALITY` | Modelo para adaptar el CV. |
| `JSEARCH_API_KEY` | RapidAPI JSearch (ofertas en Colombia). |
| `JOOBLE_API_KEY` | Jooble (ofertas en Colombia). |
| `SMTP_USER` / `SMTP_PASSWORD` | Gmail + contraseña de aplicación. |
| `ALERT_TO` | Correo que recibe las alertas. |
| `ALERT_THRESHOLD` | Score mínimo para alerta inmediata (default 85). |
| `DIGEST_THRESHOLD` | Score mínimo para el resumen diario (default 70). |
| `DIGEST_HOUR` | Hora del resumen diario, en la zona horaria configurada (default 8). |
| `ENABLE_SCHEDULER` | Activa búsquedas periódicas y resumen diario. |
| `SEARCH_INTERVAL_HOURS` | Frecuencia de búsqueda automática (default 6). |
| `TIMEZONE` | Zona horaria del scheduler (default `America/Bogota`). |

### Gmail

1. Activa la verificación en dos pasos en tu cuenta de Google.
2. Ve a **Seguridad → Contraseñas de aplicaciones**.
3. Crea una contraseña para "JobRadar".
4. Usa esa contraseña en `SMTP_PASSWORD` (no tu contraseña normal).

Con `ENABLE_SCHEDULER=true` y SMTP configurado:

- Un match con score ≥ `ALERT_THRESHOLD` dispara un correo inmediato.
- Un resumen diario agrupa los matches entre `DIGEST_THRESHOLD` y `ALERT_THRESHOLD` que aún no hayas guardado o postulado.

## Flujo

1. Sube tu CV en PDF o DOCX.
2. Revisa el perfil y configura roles, ubicación, salario y modalidad.
3. JobRadar busca ofertas y calcula el match.
4. Revisa el dashboard y el detalle de cada vacante.
5. Adapta el CV, revísalo y descarga DOCX/PDF.
6. Marca la postulación en el tracker.

![CV adaptado con guardrails y aprobación](docs/screenshots/tailor.webp)

## Reglas de ubicación

- Presencial/híbrido en Bogotá o ciudades cercanas: elegible.
- Remoto en Colombia: elegible.
- Presencial/híbrido en otra ciudad de Colombia: solo si aceptas reubicarte.
- Remoto en LatAm o global: elegible si la zona horaria es compatible.
- Presencial/híbrido fuera de Colombia: excluido.

## Privacidad

- La base de datos, los CVs subidos y los archivos exportados viven en `data/`, fuera de Git.
- Las claves se leen desde `backend/.env`; nunca se envían al navegador.
- JobRadar es una herramienta personal y local. Si la publicas fuera de tu máquina, ponle autenticación en un reverse proxy.

## Estructura

```text
jobradar/
├── backend/
│   ├── app/
│   │   ├── api/        # rutas FastAPI
│   │   ├── core/       # configuración y base de datos
│   │   ├── data/       # dataset demo y catálogo de skills
│   │   ├── models/     # entidades SQLAlchemy
│   │   ├── schemas/    # contratos Pydantic
│   │   └── services/   # matching, fuentes, CV, correo, scheduler
│   └── tests/
├── frontend/
│   ├── public/
│   └── src/
│       ├── components/
│       ├── lib/
│       └── pages/
├── docs/screenshots/
├── data/               # runtime, no versionado
└── Makefile
```

## Tests y calidad

```bash
cd backend && uv run pytest -q
cd backend && uv run ruff check .
cd frontend && npm run build
```

El backend incluye pruebas de reglas de ubicación, motor de matching, endpoints, exportación y digest de correo. El frontend se valida con TypeScript estricto y build de producción de Vite.

## Estado

MVP local completo:

- [x] Perfil, carga y parsing de CV.
- [x] Preferencias, reglas de ubicación y matching explicable.
- [x] Ingesta demo y fuentes externas opcionales.
- [x] Dashboard, vacantes, detalle y tracker.
- [x] Adaptación de CV con guardrails, aprobación y exportación DOCX/PDF.
- [x] Alertas Gmail inmediatas y resumen diario.
- [x] Modo demo offline y datos de ejemplo.
- [ ] Autenticación y despliegue público (fuera del alcance personal).

## Licencia

MIT.
