import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone

class HelpCog(commands.Cog):
    def __init__(self, bot, global_config):
        self.bot = bot
        self.global_config = global_config

    def is_developer(self, user_id):
        """Check if the user is a bot developer based on config.json."""
        developer_ids = self.global_config.get("bot_developer_ids", [])
        return str(user_id) in developer_ids

    def is_server_or_bot_admin(self, interaction):
        """Check if the user is a server admin or bot admin from server config."""
        try:
            # Use the bot's method directly, assuming it's available
            server_config = self.bot.load_or_create_server_config(interaction.guild.id)
            admin_roles = server_config.get('admin_roles', [])
            return (
                interaction.user.guild_permissions.administrator or
                any(role.id in admin_roles for role in interaction.user.roles)
            )
        except AttributeError:
            # Fallback if the method isn’t available (e.g., during testing)
            return interaction.user.guild_permissions.administrator

    @app_commands.command(name="help", description="Display a list of available commands based on your permissions.")
    async def help(self, interaction: discord.Interaction):
        # Defer the response to avoid timeout
        await interaction.response.defer(ephemeral=True)

        if self.bot.is_server_blacklisted(interaction.guild.id):
            await self.bot.handle_blacklisted_server(interaction)
            return

        guild = interaction.guild
        user = interaction.user
        commands_list = []

        # Define command sets based on permission levels
        all_commands = {
            "user": [
                {"name": "/cheers-count", "desc": "Show the count of cheers across all servers."},
                {"name": "/feedback", "desc": "Send feedback to the developers."},
                {"name": "/meetthedev", "desc": "Meet the developer of CheersBot."},
                {"name": "/partners", "desc": "Display the list of partner servers."},
                {"name": "/setup-info", "desc": "Display the current bot settings for this server (if setup is complete)."},
                {"name": "/uptime", "desc": "Check how long the bot has been online."}
            ],
            "admin": [
                {"name": "/cheers", "desc": "Play the cheers sound in a voice channel."},
                {"name": "/blacklist", "desc": "Manage the blacklist of channels for auto-join."},
                {"name": "/mode", "desc": "Change the bot's mode for this server (single or random)."},
                {"name": "/setup", "desc": "Set up the bot for this server (required before use)."},
                {"name": "/sounds", "desc": "Manage sounds: set single sound or toggle random sounds."}
            ],
            "developer": [
                {"name": "/feedback-ban", "desc": "Ban a user from using the /feedback command."},
                {"name": "/reload", "desc": "Reload and sync commands globally."},
                {"name": "/test", "desc": "Manually trigger the join and play functions for all servers."},
                {"name": "/update", "desc": "Send an update message to a specific server or all servers."}
            ],
            "text_developer": [
                {"name": "c.DM_ban", "desc": "Ban a user from directly messaging the bot."},
                {"name": "c.DM_toggle", "desc": "Toggle global DM enable/disable."},
                {"name": "c.DM_unban", "desc": "Unban a user from directly messaging the bot."},
                {"name": "c.feedback_unban", "desc": "Unban a user from using the /feedback command."},
                {"name": "c.partners_edit", "desc": "Edit the partners list (add or remove)."},
                {"name": "c.sync", "desc": "Sync commands globally."}
            ]
        }

        # Determine user's permission level and build command list
        if self.is_developer(user.id):
            # Bot developer sees all commands
            commands_list.extend(all_commands["user"])
            commands_list.extend(all_commands["admin"])
            commands_list.extend(all_commands["developer"])
            commands_list.extend(all_commands["text_developer"])
            title = "CheersBot Help - Developer Menu"
        elif self.is_server_or_bot_admin(interaction):
            # Server or bot admins see user + admin commands
            commands_list.extend(all_commands["user"])
            commands_list.extend(all_commands["admin"])
            title = "CheersBot Help - Admin Menu"
        else:
            # Regular users see only user commands
            commands_list.extend(all_commands["user"])
            title = "CheersBot Help - User Menu"

        # Sort commands alphabetically
        commands_list.sort(key=lambda x: x["name"])

        # Create embed
        embed = discord.Embed(
            title=title,
            description="Here are the commands you can use:",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )

        # Add commands to embed
        for cmd in commands_list:
            embed.add_field(name=cmd["name"], value=cmd["desc"], inline=False)

        # Set server icon as author picture
        guild_icon_url = guild.icon.url if guild.icon else "https://i.imgur.com/4OO5wh0.png"
        embed.set_author(name=guild.name, icon_url=guild_icon_url)

        # Load global footer from config.json
        log_settings = self.global_config.get("log_settings", {})
        footer_text = log_settings.get("footer_text", "CheersBot V2.0 by HomiesHouse | Discord.gg/HomiesHouse")
        footer_icon_url = log_settings.get("footer_icon_url", "https://i.imgur.com/4OO5wh0.png")
        embed.set_footer(text=footer_text, icon_url=footer_icon_url)

        # Send the response
        try:
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            print(f"Error sending help response: {e}")
            await interaction.followup.send("An error occurred while displaying the help menu.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(HelpCog(bot, bot.global_config))