# Configuración de JobRadar

Esta guía explica qué cambiar en `backend/.env` para que JobRadar funcione con datos reales, IA, búsqueda de vacantes y asistente de postulación.

> `backend/.env` es privado y está ignorado por Git. Nunca compartas tus claves ni las pegues en el chat. Para empezar, copia `backend/.env.example` a `backend/.env`.

## 1. Lo mínimo para probar sin configurar nada

Déjalo así:

```env
DEMO_MODE=true
```

Con esto JobRadar carga un perfil, un CV simulado y 18 vacantes de ejemplo. No necesita clave de IA, correo ni APIs externas. Es la forma más rápida de probar la interfaz.

## 2. Lo mínimo para usar tus datos reales

Cambia estos valores:

```env
DEMO_MODE=false
LLM_API_KEY=tu_clave_de_openrouter
```

Después:

1. Reinicia el backend.
2. Si ya tenías datos demo, entra en **Ajustes → Borrar todos mis datos**. Cambiar `DEMO_MODE` no borra automáticamente el perfil ni las vacantes de ejemplo. No uses **Reiniciar demo** si quieres datos reales, porque vuelve a cargar el dataset demo.
3. Entra a **Mi perfil** y sube tu CV real en PDF o DOCX.
4. Revisa los datos detectados y corrige lo que falte.
5. Configura roles, ciudad, salario y modalidad en **Ajustes**.
6. Usa **Buscar ahora** o **Importar por URL**.

Sin clave de IA, JobRadar sigue funcionando con reglas locales y plantillas, pero la extracción del CV, la adaptación y las respuestas abiertas serán más básicas.

## 3. IA: solo OpenRouter

JobRadar usa **OpenRouter como única API de IA**. No usa la API directa de NVIDIA. Los modelos con prefijo `nvidia/...` son modelos de NVIDIA servidos por OpenRouter.

```env
LLM_PROVIDER=openrouter
LLM_API_KEY=tu_clave_de_openrouter
OPENROUTER_API_KEY=
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL_FAST=nvidia/nemotron-3.5-lightning:free
LLM_MODEL_QUALITY=nvidia/nemotron-3-ultra-550b-a55b:free
LLM_MODEL_FALLBACK=nvidia/nemotron-3.5-super-vl:free
LLM_TIMEOUT_SECONDS=90
```

- `LLM_API_KEY`: pega aquí tu clave de OpenRouter.
- `OPENROUTER_API_KEY`: alternativa. Si prefieres usar esta variable, deja `LLM_API_KEY` vacía.
- `LLM_BASE_URL`: no lo cambies si usas OpenRouter.
- `LLM_MODEL_FAST`: modelo rápido para leer CV y ofertas.
- `LLM_MODEL_QUALITY`: modelo de más calidad para adaptar el CV y redactar respuestas.
- `LLM_MODEL_FALLBACK`: se usa si el modelo principal falla o está limitado.
- `LLM_TIMEOUT_SECONDS`: tiempo máximo de espera por respuesta.

Puedes comprobar la conexión en **Ajustes → Integraciones → Probar modelo de IA**, o con:

```bash
curl -X POST http://127.0.0.1:8000/api/llm/test
```

## 4. Búsqueda automática de vacantes

Estas claves son opcionales:

```env
JSEARCH_API_KEY=
JOOBLE_API_KEY=
BRAVE_SEARCH_API_KEY=
```

- `JSEARCH_API_KEY`: RapidAPI JSearch. Útil para vacantes en Colombia.
- `JOOBLE_API_KEY`: Jooble. Útil para empleos locales.
- `BRAVE_SEARCH_API_KEY`: descubrimiento web de ofertas públicas con datos estructurados.


### Importante sobre JSearch

La clave debe ser de la API **JSearch** en RapidAPI, no una clave genérica de otra API. El plan gratuito suele incluir unas 200 solicitudes al mes. En JobRadar cada **Buscar ahora** consume 1 solicitud y usa el endpoint actual `/search-v2`.

Si RapidAPI responde `Endpoint '/search' does not exist`, estás usando una versión antigua del cliente; en este proyecto ya está corregido a `/search-v2`.

### Importante sobre Jooble

Consigue la clave de Colombia en [co.jooble.org/api/about](https://co.jooble.org/api/about). Una clave generada en `jooble.org` es para Estados Unidos y no sirve para Colombia.

El plan gratuito de Jooble permite **500 solicitudes por clave en total**, no 500 al mes. Es una cuota de por vida: no se restablece mensualmente. Además, cada dominio regional de Jooble necesita su propia clave; una clave de `jooble.org` no sirve automáticamente para otros países.

En JobRadar, si la clave está configurada, cada ejecución de **Buscar ahora** consume **1 solicitud de Jooble** (se envía una sola consulta con tus roles). Una ejecución del programador también consume 1 solicitud. Para cuidar la cuota:

- No actives el programador hasta estar seguro.
- Usa **Importar por URL** para vacantes concretas: no consume Jooble.
- Prueba primero con `DEMO_MODE=true`.
- Si llegas a 500, la clave deja de responder y tendrías que solicitar otra o usar otro proveedor.

Si no tienes estas claves, JobRadar igual consulta Remotive y RemoteOK, y siempre puedes usar **Importar por URL** para cualquier vacante pública. Para buscar empleos presenciales o híbridos en Bogotá, JSearch, Jooble o Brave ayudan bastante.

## 5. Asistente y auto-envío

```env
AUTO_SUBMIT_ENABLED=false
AUTO_SUBMIT_MAX_PER_RUN=5
AUTO_SUBMIT_PORTALS=greenhouse,lever,ashby,workable,breezy,teamtailor
MANUAL_ONLY_PORTALS=linkedin,indeed,computrabajo,magneto,elempleo,glassdoor
DEFAULT_CV_SOURCE=tailored
FRESHNESS_DAYS=2
```

- `AUTO_SUBMIT_ENABLED`: valor inicial del auto-envío. Déjalo en `false` y actívalo desde **Ajustes** cuando quieras. El auto-envío siempre es opcional.
- `AUTO_SUBMIT_MAX_PER_RUN`: máximo de vacantes por ronda. También se puede cambiar en Ajustes.
- `AUTO_SUBMIT_PORTALS`: únicos portales donde se permite auto-envío. No los amplíes a LinkedIn, Indeed, Computrabajo, Magneto, elempleo o Glassdoor.
- `MANUAL_ONLY_PORTALS`: portales que nunca se asisten ni se envían automáticamente.
- `DEFAULT_CV_SOURCE`: `tailored` usa el CV adaptado ATS; `original` usa el archivo que subiste. Siempre puedes cambiarlo en cada postulación.
- `FRESHNESS_DAYS`: frescura inicial del listado. `1` = 24 h, `2` = 48 h, `7` = 7 días.

Para que el auto-envío funcione de verdad:

1. Instala la extensión de Chrome desde `extension/`.
2. Deja el backend en `http://127.0.0.1:8000`.
3. Activa el interruptor **Auto-envío** en **Vacantes** o en **Ajustes**.
4. Pulsa **Realizar auto-envío** en Vacantes.

Las vacantes que no se puedan automatizar aparecerán como cartas manuales con descripción y enlace original. La extensión se detiene ante login, CAPTCHA, 2FA, términos obligatorios o falta de botón de envío. Nunca guarda contraseñas ni evade verificaciones.

## 6. Correo y alertas

Opcional. Para Gmail, el bloque debe quedar así:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tucorreo@gmail.com
SMTP_PASSWORD=abcdefghijklmnop
ALERT_TO=tucorreo@gmail.com
ALERT_THRESHOLD=85
DIGEST_THRESHOLD=70
DIGEST_HOUR=8
```

Qué significa cada campo:

- `SMTP_HOST`: déjalo en `smtp.gmail.com`.
- `SMTP_PORT`: déjalo en `587` para Gmail con STARTTLS.
- `SMTP_USER`: tu dirección completa de Gmail. Ejemplo: `juan@gmail.com`.
- `SMTP_PASSWORD`: una **contraseña de aplicación** de Google, de 16 caracteres. No es tu contraseña normal de Gmail. Pégala sin espacios.
- `ALERT_TO`: correo donde quieres recibir las alertas. Puede ser el mismo `SMTP_USER`.
- `ALERT_THRESHOLD`: score mínimo para un correo inmediato. Por defecto 85.
- `DIGEST_THRESHOLD`: score mínimo para el resumen diario. Por defecto 70. El resumen incluye vacantes con score entre este valor y `ALERT_THRESHOLD`.
- `DIGEST_HOUR`: hora del resumen diario, en formato 0–23. Por defecto 8 (8 a. m.).

### Cómo crear la contraseña de aplicación de Gmail

1. Entra a tu cuenta de Google.
2. Activa la **verificación en dos pasos** si aún no la tienes.
3. Ve a **Seguridad → Contraseñas de aplicaciones**.
4. Crea una para “JobRadar” o “Correo”.
5. Copia la contraseña de 16 caracteres y pégala en `SMTP_PASSWORD`.

### Importante para que los correos salgan

- `DEMO_MODE` debe ser `false` para que las alertas reales se envíen.
- El correo de prueba de **Ajustes → Integraciones → Probar correo** sí funciona aunque estés en modo demo, siempre que SMTP esté configurado.
- Las alertas inmediatas se envían después de una búsqueda (manual o programada).
- El resumen diario necesita `ENABLE_SCHEDULER=true` y el backend encendido.
- Las vacantes guardadas, postuladas o descartadas no generan alertas.

Si dejas estas variables vacías, JobRadar funciona igual; simplemente no envía correos.

## 7. Programador de búsquedas

```env
ENABLE_SCHEDULER=false
SEARCH_INTERVAL_HOURS=6
TIMEZONE=America/Bogota
```

- `ENABLE_SCHEDULER`: `true` activa búsquedas y resúmenes automáticos.
- `SEARCH_INTERVAL_HOURS`: cada cuántas horas busca.
- `TIMEZONE`: zona horaria usada por el programador.

Déjalo en `false` mientras estás probando. Si solo tienes la clave de Jooble, ten en cuenta que cada búsqueda programada consume 1 de las 500 solicitudes totales. Si lo activas, el backend debe quedar corriendo.

## 8. Qué NO necesitas cambiar

Normalmente puedes dejar igual:

```env
APP_NAME=JobRadar
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
DATABASE_URL=sqlite:///../data/jobradar.db
UPLOAD_DIR=../data/uploads
EXPORT_DIR=../data/exports
```

Solo cambia `CORS_ORIGINS` si usas el frontend en otro puerto o dominio.

## 9. Orden recomendado para dejarlo funcionando

1. `DEMO_MODE=true` y prueba la app sin claves.
2. Añade tu clave de OpenRouter y pulsa **Probar modelo de IA**.
3. Cambia `DEMO_MODE=false`, reinicia el backend y sube tu CV real.
4. Configura preferencias y prueba **Importar por URL**.
5. Añade JSearch/Jooble/Brave si quieres búsqueda automática.
6. Configura SMTP si quieres alertas.
7. Instala la extensión y prueba una postulación asistida antes de activar el auto-envío.

## 10. Seguridad

- No subas `backend/.env` a Git.
- No compartas `LLM_API_KEY`, `OPENROUTER_API_KEY`, `SMTP_PASSWORD` ni claves de búsqueda.
- La extensión no guarda contraseñas de portales.
- El auto-envío solo se ejecuta en los ATS permitidos y después de activarlo explícitamente.
- Si publicas JobRadar fuera de tu computador, ponle autenticación en un reverse proxy.
