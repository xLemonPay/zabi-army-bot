# Zabi Army Bot 😈

Bot de Discord para **Zabi Army**, preparado para desplegarse en Northflank.

## Funciones

- 🎬 Publicación automática de clips nuevos de Twitch en `🎬・clips-de-zabi`.
- 💡 Sugerencias mediante botón + formulario + votos 👍/👎.
- 🎫 Tickets privados con botón de apertura y cierre.
- 🧱 `/setup` crea o migra la estructura del servidor **sin borrar canales existentes**.
- 🌐 Health endpoint en `/health` para Northflank.

## Estructura

```text
╭・🚪 ANTES DE ENTRAR
├ 📍・por-donde-empiezo
├ 📜・las-reglas-del-juego
├ 📣・zabi-dice
└ 🔗・cosas-utiles

╭・😈 ZABI ARMY
├ 💬・la-plaza
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
```

El setup reconoce y reutiliza varios canales actuales (`general`, `clips`, `musiquita`, `los-delincuentes`, `CONFESIONARIO 😈`, `hellfire club 😈`, `sotano`, etc.) para conservar su historial.

## Variables de entorno

Copiar `.env.example` o cargarlas directamente en Northflank:

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

## Northflank

- Source: `xLemonPay/zabi-army-bot`
- Branch: `main`
- Build: Dockerfile
- Dockerfile: `/Dockerfile`
- Build context: `/`
- Instances: `1`
- Port interno del health server: `8080`

## Primera instalación

1. Desplegar el servicio.
2. Verificar en logs `✅ Conectado como ...`.
3. Ejecutar `/setup` una sola vez en Discord.
4. Comprobar `/bot-estado`.
5. Probar Twitch con `/clips-revisar`.

## Comandos

- `/setup` — instala/migra la estructura sin borrar canales.
- `/bot-estado` — estado básico.
- `/clips-revisar` — revisa Twitch manualmente.
- `/sugerencia-estado` — cambia el estado de una sugerencia.

Creado por **xLemonPay**.
