import discord
from discord import app_commands
from discord.ext import commands  

class PermissionsCog(commands.Cog):  
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="permissions", description="Check the bot's permissions in this server.")
    async def permissions(self, interaction: discord.Interaction):
        if self.bot.is_server_blacklisted(interaction.guild.id):
            await self.bot.handle_blacklisted_server(interaction)
            return
        if not await self.bot.ensure_setup(interaction):
            return

        try:
            guild = interaction.guild
            bot_member = guild.me
            perms = bot_member.guild_permissions
        except Exception as e:
            await interaction.response.send_message(f"Error retrieving permissions: {e}", ephemeral=True)
            return

        embed = discord.Embed(
            title="Bot Permissions",
            description="Here are my current permissions in this server:",
            color=discord.Color.blue()
        )

        permissions_info = {
            "administrator": ("A blanket permission. Ensures the bot has all permissions and no further setup will be required."),
            "manage_guild": ("This permission adds your server to the '420 Servers' log list. The Dev likes to visit servers and this is the only way for the bot to see invite links. This can be safely disabled."),
            "manage_roles": ("⭐️ Used to create a separate role for CheersBot when adding the bot to your server. This permission should automatically create a role with the rest of the given permissions."),
            "view_channel": ("⭐️ The bot must be able to see all channels/voice channels."),
            "view_guild_insights": ("Allows the bot to see how many members the server has. Typically used for partnered servers but how big of servers are using CheersBot."),
            "send_messages": ("⭐️ Used during /setup. Needed."),
            "manage_messages": ("⭐️ The bot edits/deletes its own messages sometimes. This is just to clear bot spam."),
            "embed_links": ("Allows Embeds/Embed Links (There are no embedded links currently)."),
            "read_message_history": ("⭐️ Allows the bot to see the previous messages so it's able to respond."),
            "use_external_emojis": ("Used for Emoji's used in certain embeds."),
            "connect": ("⭐️ The bot must be able to connect to voice channels."),
            "speak": ("⭐️ The bot must be able to speak in voice channels to play the Cheers sound."),
            "use_voice_activation": ("⭐️ Used to ensure that when the sound is played, the bot is always able to speak (If inside a push-to-talk only channel)."),
            "priority_speaker": ("Allows the bot to be more easily heard when the sound plays. (This is currently unused and will most likely be a toggle through a bot command.)")
        }

        for perm, desc in permissions_info.items():
            has_perm = getattr(perms, perm, False)
            status = "✔️" if has_perm else "❌"
            embed.add_field(name=f"{perm.replace('_', ' ').title()} {status}", value=desc, inline=False)

        log_settings = self.bot.global_config.get("log_settings", {})
        footer_text = log_settings.get("footer_text", "CheersBot V2.0 by HomiesHouse | Discord.gg/HomiesHouse")
        footer_icon_url = log_settings.get("footer_icon_url", "https://i.imgur.com/4OO5wh0.png")
        embed.set_footer(text=footer_text, icon_url=footer_icon_url)

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(PermissionsCog(bot))