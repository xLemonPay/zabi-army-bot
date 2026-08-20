# Zabi Army Bot 👹

Bot de comunidad para Discord adaptado a **Zabi Army** y desplegado en Northflank.

## Objetivo

La base funcional sigue el Streamer Bot de s0ftbl4de, pero conserva la identidad y los nombres ya existentes en el servidor de Zabi.

**Importante:** si el bot encuentra un canal existente mediante sus aliases, lo reutiliza, mueve y actualiza permisos/topic si hace falta, pero **no lo renombra**. Esto conserva historial y nombres actuales.

## Funciones incluidas

- ✅ Verificación por botón con `✅・Miembro`.
- 👋 Bienvenida automática después de verificar.
- 🎭 Roles completos: Owner, Co-Owner, Admin, Moderador, Streamer, Subscriber, VIP, Miembro, avisos, país, edad, rango de Valorant, juegos y plataformas.
- 🎛️ Panel persistente de roles.
- 💬 Categorías, canales y permisos por verificación.
- 📌 Guía automática dentro de cada canal de texto explicando para qué sirve.
- 🔊 `➕・crear-sala`: crea una sala temporal, mueve al usuario y la elimina cuando queda vacía.
- 👥 `/party` para buscar gente para Valorant desde el canal LFG.
- 💡 Sugerencias con formulario, votos 👍/👎 y botones de estado para staff.
- 🎫 Tickets privados con apertura/cierre y registro interno.
- 📜 Logs de entradas, salidas, cambios de roles y cambios de canales.
- 🟣 Twitch automático: detecta directo, publica aviso, asigna `🔴・EN DIRECTO`, crea canales temporales y cambia la presencia del bot.
- 🎬 Clips automáticos de Twitch con deduplicación y revisión manual.
- 🌐 Health endpoint `/health` para Northflank.

## Canales que crea si faltan

```text
╭・🚪 ANTES DE ENTRAR
├ ✅・verificate
├ 📜・las-reglas-del-juego
├ 📣・zabi-dice
├ 🔗・cosas-utiles
└ 🎭・elegi-tus-roles

╭・😈 ZABI ARMY
├ 💬・la-plaza
├ 👋・nuevos-delincuentes
├ 😈・los-delincuentes
├ 🌙・charlas-de-madrugada
├ 📸・pruebas-del-delito
├ 😂・meme-del-dia
├ 🎵・musiquita
├ 🎬・clips-de-zabi
└ 💡・tira-tu-idea

╭・🎮 SE VINO EL VICIO
├ 🎮・viciando
├ 🔫・ranked-y-lagrimas
├ 👥・busco-gente
└ 🏆・competitivo

╭・🔊 BAJÁ A HABLAR
├ 👹・CONFESIONARIO
├ 👹・hellfire-club
├ 🕯️・el-sotano
├ 🌙・insomnio
└ ➕・crear-sala

╭・🎫 HABLÁ CON EL STAFF
└ 🎫・abrir-ticket

╭・🛡️ LA OFICINA
├ 🛡️・la-oficina
├ 🚨・casos-abiertos
└ 📜・historial
```

Aliases conocidos permiten reutilizar, entre otros: `bienvenida-y-reglas`, `anuncios`, `recursos`, `general`, `clips`, `musiquita`, `los-delincuentes`, `CONFESIONARIO 😈`, `hellfire club 😈` y `sotano`.

## Reglas configuradas

El panel de reglas usa el texto acordado con la streamer: no discriminación, no backseating, nada de política, respeto, no pedir follows/mod/VIP/suscripción y pasarla bien.

## Roles principales

```text
👑・Owner
💎・Co-Owner
🛡️・Admin
🔨・Moderador
🎥・Streamer
💜・Subscriber
⭐・VIP
✅・Miembro
🔴・EN DIRECTO
🔔・Avisos de directo
🎉・Avisos de eventos
```

También se crean roles de país, edad, rango de Valorant, juegos y plataformas.

El rol del bot debe permanecer por encima de todos los roles que administra.

## Variables de entorno

```env
DISCORD_TOKEN=
GUILD_ID=
PORT=8080
ENABLE_MESSAGE_LOGS=false

TWITCH_CLIENT_ID=
TWITCH_CLIENT_SECRET=
TWITCH_CHANNEL=
STREAMER_DISCORD_ID=0
TWITCH_POLL_SECONDS=60
TWITCH_OFFLINE_DELETE_DELAY=300
TWITCH_CLIPS_POLL_SECONDS=60
TWITCH_CLIPS_LOOKBACK_MINUTES=180
```

## Comandos actuales

```text
/setup
/actualizar-canales
/actualizar-roles
/actualizar-guias
/actualizar-paneles
/actualizar-tickets
/actualizar-twitch
/bot-estado

/party

/clips-revisar
/clips-estado

/twitch-estado
/twitch-preview
/twitch-simular
/twitch-fin-prueba
```

`/setup` se usa para la instalación inicial. Después conviene usar los comandos por sección.

## Prueba recomendada antes del servidor real

1. Ejecutar `/setup` en el servidor de prueba.
2. Probar verificación con una cuenta sin `✅・Miembro`.
3. Comprobar las guías de cada canal.
4. Probar roles desde el panel.
5. Entrar a `➕・crear-sala` y confirmar creación/movimiento/borrado de la voz temporal.
6. Abrir y cerrar un ticket.
7. Enviar y votar una sugerencia.
8. Probar `/party`.
9. Ejecutar `/twitch-simular` y luego `/twitch-fin-prueba`.
10. Ejecutar `/clips-revisar` y `/bot-estado`.

No subir nunca tokens ni `.env` al repositorio.

Creado por **xLemonPay**.
