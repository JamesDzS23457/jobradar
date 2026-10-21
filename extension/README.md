# JobRadar Assistant (Chrome, Manifest V3)

Extensión local para rellenar postulaciones desde JobRadar. Usa la sesión real del navegador y está diseñada para revisión humana.

## Qué hace

- Lee una sesión preparada por JobRadar y rellena campos estándar (nombre, email, teléfono, links, etc.).
- Adjunta el CV elegido: **CV adaptado ATS** o **PDF original**.
- Detecta preguntas abiertas y pide a JobRadar respuestas redactadas sin inventar datos.
- En modo asistido, deja el botón de envío al usuario.
- En `auto_submit`, solo para portales permitidos, puede enviar y reportar el resultado al tracker.
- Si encuentra login, CAPTCHA, 2FA o una casilla de términos obligatoria, marca la vacante como manual.

## Qué NO hace

- No guarda contraseñas de portales.
- No evade CAPTCHA, 2FA, detección de bots ni huellas del navegador.
- No automatiza LinkedIn, Indeed, Computrabajo, Magneto, elempleo ni Glassdoor.
- No envía postulaciones sin que hayas activado el auto-envío en Ajustes.

## Instalación

1. Arranca el backend en `http://127.0.0.1:8000` y el frontend en `http://127.0.0.1:5173`.
2. Abre `chrome://extensions`.
3. Activa **Modo de desarrollador**.
4. Pulsa **Cargar descomprimida** y selecciona la carpeta `extension/`.
5. Fija la extensión en la barra si quieres abrir el panel manualmente con el icono.

## Uso

1. En JobRadar, abre una vacante y pulsa **Preparar postulación**.
2. Revisa los datos y el CV. Pulsa **Abrir portal con asistente**.
3. El panel de JobRadar aparece en la esquina inferior derecha del portal.
4. Revisa los campos y pulsa **Enviar postulación** (asistido) o deja que la cola de auto-envío lo procese.

Para una ronda de auto-envío, activa el interruptor en **Ajustes → Postulaciones y auto-envío**, vuelve a **Vacantes** y pulsa **Realizar auto-envío**. Las vacantes que no se pueden automatizar aparecen como cartas manuales con descripción y enlace original.

## Límites reales

Cada ATS tiene su propio formulario, pasos y validaciones. El asistente es heurístico: puede no reconocer campos personalizados, formularios dentro de iframes o flujos con varios dominios. En esos casos debes completar el paso manualmente. Nunca intentes usar la extensión para saltar verificaciones de seguridad.
