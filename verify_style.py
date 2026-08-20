from __future__ import annotations

import discord


def install(base) -> None:
    """Quita el emoji del botón y del título del panel de verificación."""

    class VerifyView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(
            label="Entrar a Zabi Army",
            style=discord.ButtonStyle.success,
            custom_id="zabi:verify",
        )
        async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.guild is None or not isinstance(interaction.user, discord.Member):
                return

            role = base.find_role(interaction.guild, base.ROLE_MEMBER)
            if role is None:
                return await interaction.response.send_message(
                    "No encuentro el rol de Miembro. Un administrador debe ejecutar `/setup`.",
                    ephemeral=True,
                )

            if role in interaction.user.roles:
                return await interaction.response.send_message(
                    "Ya estás verificado/a ✅",
                    ephemeral=True,
                )

            try:
                await interaction.user.add_roles(
                    role,
                    reason="Verificación automática Zabi Army",
                )
            except discord.Forbidden:
                return await interaction.response.send_message(
                    "No pude darte el rol. El rol del bot debe estar por encima de `✅・Miembro`.",
                    ephemeral=True,
                )

            await interaction.response.send_message(
                "✅ Listo. Ya tenés acceso al servidor.",
                ephemeral=True,
            )
            await base.send_welcome(interaction.user)

    base.VerifyView = VerifyView

    async def clean_verify_panel_title(guild: discord.Guild) -> None:
        channel = base.find_text(guild, base.CH_VERIFY)
        if channel is None:
            return

        try:
            async for message in channel.history(limit=100):
                if message.author != guild.me or not message.embeds:
                    continue

                title = message.embeds[0].title or ""
                if title not in {"👹 Bienvenido/a a Zabi Army", "Bienvenido/a a Zabi Army"}:
                    continue

                embed = discord.Embed.from_dict(message.embeds[0].to_dict())
                embed.title = "Bienvenido/a a Zabi Army"
                try:
                    await message.edit(embed=embed, view=VerifyView())
                except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                    pass
                return
        except (discord.Forbidden, discord.HTTPException):
            pass

    original_ensure_panels = base.ensure_panels

    async def patched_ensure_panels(guild: discord.Guild) -> None:
        await original_ensure_panels(guild)
        await clean_verify_panel_title(guild)

    base.ensure_panels = patched_ensure_panels

    async def clean_verify_panel_on_ready() -> None:
        for guild in base.bot.guilds:
            await clean_verify_panel_title(guild)

    base.bot.add_listener(clean_verify_panel_on_ready, "on_ready")
