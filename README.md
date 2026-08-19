# Zabi Army Bot 😈

Bot completo de Discord para **Zabi Army**, preparado para Northflank.

## Incluye

- ✅ Verificación por botón y rol `✅・Miembro`.
- 👋 Bienvenidas automáticas después de verificarse.
- 🎭 Roles de staff, streamer, VIP, miembro, juegos, plataformas y avisos.
- 🎛️ Panel de self-roles con botones persistentes.
- 💬 Estructura completa de texto y voz con permisos por verificación.
- 🎬 Publicación automática de clips nuevos de Twitch.
- 💡 Sugerencias con formulario, 👍/👎 y estados del staff.
- 🎫 Tickets privados con apertura y cierre por botón.
- 🛡️ Categoría privada de staff con oficina, casos e historial.
- 📜 Logs básicos de entradas, salidas y cambios de roles.
- 🌐 Health endpoint en `/health` para Northflank.
- 🧱 `/setup` es idempotente: crea, migra y actualiza sin borrar canales existentes.

## Estructura

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
├ 🎧・la-rockola
├ 🎬・clips-de-zabi
└ 💡・tira-tu-idea

╭・🎮 SE VINO EL VICIO
├ 🎮・viciando
├ 🔫・ranked-y-lagrimas
├ 👥・busco-gente
└ 🏆・competitivo

╭・🔊 BAJÁ A HABLAR
├ 😈・CONFESIONARIO
├ 🔥・hellfire-club
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

El setup reconoce y reutiliza canales del servidor actual como `bienvenida-y-reglas`, `anuncios`, `recursos`, `general`, `clips`, `musiquita`, `los-delincuentes`, `CONFESIONARIO 😈`, `hellfire club 😈` y `sotano`, conservando su historial.

## Roles principales

```text
👑・Owner
🎥・Zabi
🛡️・Admin
🔨・Moderador
💎・VIP
✅・Miembro
🔔・Avisos de Zabi
🔫・Valorant
⛏️・Minecraft
🎮・Otros juegos
🖥️・PC
🎮・Consola
📱・Mobile
```

El rol del bot debe permanecer por encima de los roles que administra.

## Variables de entorno

```env
DISCORD_TOKEN=
GUILD_ID=
PORT=8080

TWITCH_CLIENT_ID=
TWITCH_CLIENT_SECRET=
TWITCH_CHANNEL=
TWITCH_CLIPS_POLL_SECONDS=60
TWITCH_CLIPS_LOOKBACK_MINUTES=180
```

No subir nunca `.env` ni tokens al repositorio.

## Primera instalación

1. Desplegar en Northflank.
2. Confirmar `✅ Conectado como ...` en logs.
3. Verificar que los slash commands estén sincronizados.
4. Ejecutar `/setup` una sola vez para la instalación completa.
5. Probar una cuenta sin rol en `✅・verificate`.
6. Probar self-roles, sugerencias y tickets.
7. Ejecutar `/clips-revisar` para validar Twitch.

## Comandos

- `/setup` — instala o actualiza todo el servidor sin borrar canales.
- `/actualizar-paneles` — refresca verificación, reglas, roles, sugerencias y tickets.
- `/bot-estado` — muestra el estado básico.
- `/clips-revisar` — revisa Twitch manualmente.
- `/sugerencia-estado` — cambia el estado de una sugerencia.

Creado por **xLemonPay**.
