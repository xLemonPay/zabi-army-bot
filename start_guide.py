from __future__ import annotations

import discord


def install(base) -> None:
    """Agrega/actualiza el canal y la guía de inicio sin renombrar canales existentes."""

    base.CH_START = "📍・por-donde-empiezo"
    aliases = base.TEXT_ALIASES.setdefault(base.CH_START, [])
    for alias in ("por-donde-empiezo", "por donde empiezo", "empieza-aqui", "empieza-aquí"):
        if alias not in aliases:
            aliases.append(alias)

    async def ensure_start_channel(guild: discord.Guild) -> discord.TextChannel | None:
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

    async def ensure_start_guide(guild: discord.Guild) -> None:
        channel = await ensure_start_channel(guild)
        if channel is None:
            return

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
            "### 👹・Bienvenido/a a Zabi Army\n"
            "**Pasala bien, respetá a los demás y disfrutá.**"
        )

        await base.ensure_embed_message(
            channel,
            "👹・¿POR DÓNDE EMPIEZO?",
            description,
            discord.Colour.purple(),
        )

    original_install_channels = base.install_channels
    original_ensure_guides = base.ensure_guides

    async def patched_install_channels(guild: discord.Guild) -> None:
        await original_install_channels(guild)
        await ensure_start_channel(guild)

    async def patched_ensure_guides(guild: discord.Guild):
        result = await original_ensure_guides(guild)
        await ensure_start_guide(guild)
        return result

    base.install_channels = patched_install_channels
    base.ensure_guides = patched_ensure_guides
    base.ensure_start_guide = ensure_start_guide
