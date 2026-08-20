from __future__ import annotations

import discord


def install(base) -> None:
    """Reemplaza únicamente la vista de verificación para quitar el emoji del botón."""

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
