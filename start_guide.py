from __future__ import annotations

import discord
from discord import app_commands


def install(base) -> None:
    """Agrega/actualiza la guía de inicio y ajusta la bienvenida de Zabi Army."""

    base.CH_START = "📍・por-donde-empiezo"
    aliases = base.TEXT_ALIASES.setdefault(base.CH_START, [])
    for alias in (
        "por-donde-empiezo",
        "por donde empiezo",
        "por-donde-comienzo",
        "por donde comienzo",
        "empieza-aqui",
        "empieza-aquí",
    ):
        if alias not in aliases:
            aliases.append(alias)

    async def ensure_start_channel(guild: discord.Guild) -> discord.TextChannel | None:
        # Si el canal ya existe, se reutiliza aunque tenga uno de los nombres alias.
        existing = base.find_text(guild, base.CH_START)
        if existing is not None:
            return existing

        category = base.find_category(guild, base.CAT_ENTRY)
        if category is None:
            return None
        overwrites = base.public_readonly_overwrites(guild)
        return await base.ensure_text(
            guild,
            category,
            base.CH_START,
            overwrites,
            "Guía rápida para saber por dónde empezar en Zabi Army.",
        )

    def mention_text(guild: discord.Guild, channel_name: str, fallback: str) -> str:
        channel = base.find_text(guild, channel_name)
        return channel.mention if channel is not None else fallback

    def mention_voice(guild: discord.Guild, channel_name: str, fallback: str) -> str:
        channel = base.find_voice(guild, channel_name)
        return channel.mention if channel is not None else fallback

    async def ensure_start_guide(guild: discord.Guild) -> bool:
        channel = await ensure_start_channel(guild)
        if channel is None:
            return False

        rules = mention_text(guild, base.CH_RULES, "**las-reglas-del-juego**")
        verify = mention_text(guild, base.CH_VERIFY, "**verificate**")
        roles = mention_text(guild, base.CH_ROLES, "**elegi-tus-roles**")
        general = mention_text(guild, base.CH_GENERAL, "**la-plaza**")
        music = mention_text(guild, base.CH_MUSIC, "**musiquita**")
        clips = mention_text(guild, base.CH_CLIPS, "**clips-de-zabi**")
        suggestions = mention_text(guild, base.CH_SUGGESTIONS, "**tira-tu-idea**")
        lfg = mention_text(guild, base.CH_LFG, "**busco-gente**")
        tickets = mention_text(guild, base.CH_TICKET_PANEL, "**abrir-ticket**")
        create_room = mention_voice(guild, base.VC_CREATE, "**crear-sala**")

        description = (
            "> ¡Bienvenido/a a **Zabi Army**!\n"
            "> Si acabás de llegar y no sabés qué hacer, arrancá por acá. 💜\n\n"
            "### 1️⃣・LEÉ LAS REGLAS\n"
            f"Pasate por {rules} antes de participar.\n\n"
            "Son pocas y simples: respeto, nada de discriminación, política ni peleas, y vení a pasarla bien.\n\n"
            "### 2️⃣・VERIFICATE\n"
            f"Entrá a {verify} y tocá el botón de verificación.\n\n"
            "Esto te dará el rol **✅・Miembro** y desbloqueará el resto de la comunidad.\n\n"
            "### 3️⃣・ELEGÍ TUS ROLES\n"
            f"En {roles} podés personalizar tu perfil reaccionando a los paneles.\n\n"
            "🌎 País\n"
            "🎂 Rango de edad\n"
            "🔫 Rango de Valorant\n"
            "🎮 Juegos\n"
            "🖥️ Plataforma\n"
            "🔔 Avisos de directo y eventos\n\n"
            "### 4️⃣・CAÉ A CHARLAR\n"
            f"Cuando estés listo/a, pasate por {general} y metete en la conversación.\n\n"
            "No hace falta presentación formal. Caé, hablá y listo. 👹\n\n"
            "### 5️⃣・EXPLORÁ LA ARMY\n"
            f"🎵 {music} → compartí lo que estás escuchando.\n"
            f"🎬 {clips} → clips nuevos de Zabi.\n"
            f"💡 {suggestions} → propuestas para mejorar la comunidad.\n"
            f"👥 {lfg} → encontrá gente para jugar.\n"
            f"➕ {create_room} → entrá y el bot te crea una sala de voz propia.\n"
            f"🎫 {tickets} → hablá en privado con el staff.\n\n"
            "> 💜 **Eso es todo.**\n"
            "> No necesitás aprenderte el servidor de memoria. Cada canal tiene su propia explicación para que sepas para qué sirve.\n\n"
            "### Bienvenido/a a Zabi Army\n"
            "**Pasala bien, respetá a los demás y disfrutá.**"
        )

        await base.ensure_embed_message(
            channel,
            "¿POR DÓNDE EMPIEZO?",
            description,
            discord.Colour.purple(),
        )
        return True

    # Bienvenida: se conserva exactamente el contenido y se elimina únicamente
    # el emoji 👹 del título "Un nuevo miembro llegó...".
    async def send_welcome_without_ogre(member: discord.Member) -> None:
        channel = base.find_text(member.guild, base.CH_WELCOME)
        if channel is None:
            return
        general = base.find_text(member.guild, base.CH_GENERAL)
        count = member.guild.member_count or len(member.guild.members)
        embed = discord.Embed(
            title="Un nuevo miembro llegó a Zabi Army",
            description=(
                f"¡Bienvenido/a {member.mention}! Ya sos parte de **Zabi Army**.\n\n"
                + (f"💬 Pasate por {general.mention} y saludá.\n" if general else "")
                + f"✨ Ahora somos **{count} miembros**."
            ),
            colour=discord.Colour.purple(),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        try:
            await channel.send(
                embed=embed,
                allowed_mentions=discord.AllowedMentions(
                    users=[member], roles=False, everyone=False
                ),
            )
        except (discord.Forbidden, discord.HTTPException):
            pass

    base.send_welcome = send_welcome_without_ogre

    original_install_channels = base.install_channels
    original_ensure_guides = base.ensure_guides

    async def patched_install_channels(guild: discord.Guild) -> None:
        await original_install_channels(guild)
        await ensure_start_channel(guild)

    async def patched_ensure_guides(guild: discord.Guild):
        result = await original_ensure_guides(guild)
        published = await ensure_start_guide(guild)
        # Hacemos que /actualizar-guias también contabilice esta guía.
        try:
            updated, missing = result
            return updated + (1 if published else 0), missing
        except Exception:
            return result

    base.install_channels = patched_install_channels
    base.ensure_guides = patched_ensure_guides
    base.ensure_start_guide = ensure_start_guide

    # Refuerzo: al iniciar/reconectar el bot, asegura que la guía exista aunque
    # el canal ya hubiera sido creado manualmente antes del parche.
    async def ensure_start_on_ready() -> None:
        for guild in base.bot.guilds:
            try:
                await ensure_start_guide(guild)
            except (discord.Forbidden, discord.HTTPException) as exc:
                print(f"⚠️ Guía por-donde-empiezo: {type(exc).__name__}: {exc}")

    base.bot.add_listener(ensure_start_on_ready, "on_ready")

    # Comando directo de respaldo/diagnóstico para actualizar solo este mensaje.
    @base.bot.tree.command(
        name="actualizar-inicio",
        description="Publica o actualiza la guía Por dónde empiezo.",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def actualizar_inicio(interaction: discord.Interaction):
        if not await base.require_admin(interaction):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            ok = await ensure_start_guide(interaction.guild)
            if ok:
                await interaction.followup.send(
                    "✅ Guía **Por dónde empiezo** publicada/actualizada.",
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    "❌ No encontré la categoría de entrada ni pude ubicar el canal de inicio.",
                    ephemeral=True,
                )
        except Exception as exc:
            await interaction.followup.send(
                f"❌ `{type(exc).__name__}: {str(exc)[:700]}`",
                ephemeral=True,
            )
