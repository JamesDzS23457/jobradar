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
- `WEB_SEARCH_PROVIDER=tavily`: descubre enlaces públicos de Computrabajo, elempleo, Magneto, GetOnBoard y Torre sin tarjeta.
- `TAVILY_KEYLESS=true`: usa Tavily sin clave. Si tienes una clave gratis, añádela en `TAVILY_API_KEY`.
- `BRAVE_SEARCH_API_KEY`: alternativa opcional. Brave ahora requiere tarjeta/créditos, así que no es necesaria.


### Tavily vs Brave

Tavily keyless no necesita cuenta, clave ni tarjeta. Brave cambió su plan gratuito y ahora pide tarjeta/créditos. Por eso el proveedor por defecto es Tavily.

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

Si no tienes estas claves, JobRadar igual consulta Remotive y RemoteOK, y siempre puedes usar **Importar por URL** para cualquier vacante pública. Para buscar empleos presenciales o híbridos en Bogotá, JSearch, Jooble o Tavily ayudan bastante.



### Seniority

En **Ajustes → Búsqueda → Seniority**:

- `Junior`: no muestra Senior ni Lead.
- `Mid`: no muestra Lead.
- `Senior` y `Lead`: permiten niveles iguales o inferiores.
- `Cualquiera`: no aplica este filtro.

El filtro se recalcula al guardar Ajustes o al reiniciar el backend.

### Descripciones

JobRadar limpia las descripciones antes de guardarlas y mostrarlas: elimina etiquetas HTML, entidades (`&amp;`), scripts y texto mal codificado. No deberías ver `<p>`, `<li>` ni `Ã³` en una vacante.

## 4.1 Roles y keywords automáticos desde el CV

Al subir o reemplazar tu CV, JobRadar:

- Detecta roles compatibles con tu experiencia.
- Los guarda en español e inglés en **Ajustes → Búsqueda → Roles objetivo**.
- Completa **Keywords extra** con tus habilidades reales.
- Marca los roles y keywords como editables: puedes borrar, añadir o cambiar el orden.

Ejemplo de roles generados para un perfil backend:

```text
Backend Developer, Desarrollador Backend, Backend Engineer,
Ingeniero Backend, Python Developer, Desarrollador Python
```

Si tu CV dice que solo hablas español, JobRadar no te mostrará como elegibles las vacantes que exijan inglés de forma explícita. Las que digan “English is a plus” o “inglés deseable” no se descartan por ese motivo.


## 4.2 Enlaces de LinkedIn, Computrabajo y otros portales

JobRadar no inicia sesión en portales restringidos ni evade bloqueos. Lo que hace es:

- **JSearch** puede traer enlaces de LinkedIn, Indeed y Glassdoor.
- **Jooble** agrega ofertas de muchos portales de empleo.
- **Tavily** descubre enlaces públicos de Computrabajo, elempleo, Magneto, GetOnBoard y Torre. Funciona keyless, sin tarjeta; también puedes añadir `TAVILY_API_KEY` para más cuota. **Brave** queda como alternativa opcional.
- **Importar por URL** acepta cualquier enlace público.

Si el portal no permite leer la vacante automáticamente o muestra un muro de login:

1. JobRadar guarda el enlace igualmente.
2. La vacante aparece en el dashboard con el aviso **“Requiere iniciar sesión”**.
3. Al abrirla, el detalle te muestra **“Ingresa para postularte: este portal requiere login”**.
4. El botón **Abrir portal** te lleva al enlace original para que te postules allí.

Esto aplica a LinkedIn, Computrabajo, elempleo, Magneto, Indeed, Glassdoor y cualquier portal que bloquee la lectura. No se guardan contraseñas ni se intenta saltar el login.


## 4.3 Plataforma y fuente en cada vacante

Cada tarjeta muestra dos etiquetas:

- **Plataforma**: el portal del enlace, por ejemplo `LinkedIn`, `Computrabajo` o `elempleo`.
- **Fuente**: quién recopiló el enlace, por ejemplo `JSearch`, `Jooble`, `Tavily` o `Importación manual`.

Ejemplo:

```text
[Computrabajo] [Tavily]
[LinkedIn] [JSearch]
[Elempleo] [Importación manual]
```

Así puedes saber si la oferta vino de un agregador o de una importación directa.


## 4.4 Oportunidades potenciales

Además de las coincidencias exactas, JobRadar puede mostrar vacantes donde tu perfil está cerca del nivel pedido.

Se consideran potenciales cuando:

- Pasan ubicación e idioma.
- Están como máximo un nivel por encima de tu seniority configurado.
- La diferencia de experiencia es de 2 años o menos.
- Cubres al menos 60% del stack obligatorio.

Ejemplo con perfil de 2 años y preferencia Junior:

```text
Junior 1-2 años        → exacta
Mid 2-3 años           → potencial
Mid 4 años             → potencial si el stack alcanza
Senior 5+ años         → no elegible
```

En **Vacantes** puedes activar o desactivar **Incluir oportunidades potenciales**. Las potenciales aparecen con etiqueta ámbar y una explicación.

El **auto-envío** ignora las potenciales: solo procesa coincidencias exactas.



### Computrabajo

JobRadar lee la búsqueda pública de Computrabajo para traer vacantes actuales con título, empresa, ubicación y fecha. No inicia sesión, no aplica filtros internos del portal ni envía postulaciones.

La fuente se controla con:

```env
COMPUTRABAJO_PUBLIC_SEARCH=true
```

Si el portal cambia su HTML o bloquea la lectura, JobRadar conserva el enlace y muestra el aviso de login.

### Fechas y Indeed

JSearch consulta Indeed y otros portales con un rango de fecha que depende de tu frescura:

- 24 h → `today`
- 48 h / 3 días → `3days`
- 7 días → `week`
- Más → `month`

Si un portal no publica fecha, la vacante se oculta por defecto. En **Vacantes** aparecerá un aviso con cuántas quedaron ocultas y un botón **Incluir sin fecha**.

Tavily también busca fuera de los portales fijos mediante consultas públicas y guarda como link-only los enlaces que redirigen a listados o requieren login. Nunca inicia sesión ni evade bloqueos.


### Deduplicación

JobRadar calcula una URL canónica por vacante: quita `utm_*`, `trackingId`, `trk`, `refId`, fragmentos y parámetros de seguimiento. Si JSearch, Jooble o Tavily devuelven la misma URL en otra búsqueda, se actualiza la vacante existente en vez de crear otra.

Al iniciar, también limpia duplicados antiguos y conserva la ficha con mejor estado: postulada, guardada o la más antigua.

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
5. Añade JSearch/Jooble/Tavily si quieres búsqueda automática.
6. Configura SMTP si quieres alertas.
7. Instala la extensión y prueba una postulación asistida antes de activar el auto-envío.

## 10. Seguridad

- No subas `backend/.env` a Git.
- No compartas `LLM_API_KEY`, `OPENROUTER_API_KEY`, `SMTP_PASSWORD` ni claves de búsqueda.
- La extensión no guarda contraseñas de portales.
- El auto-envío solo se ejecuta en los ATS permitidos y después de activarlo explícitamente.
- Si publicas JobRadar fuera de tu computador, ponle autenticación en un reverse proxy.
