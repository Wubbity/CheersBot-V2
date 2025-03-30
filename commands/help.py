import discord
from discord import app_commands, ui
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
            server_config = self.bot.load_or_create_server_config(interaction.guild.id)
            admin_roles = server_config.get('admin_roles', [])
            return (
                interaction.user.guild_permissions.administrator or
                any(role.id in admin_roles for role in interaction.user.roles)
            )
        except AttributeError:
            return interaction.user.guild_permissions.administrator

    @app_commands.command(name="help", description="Display a list of available commands based on your permissions.")
    async def help(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        commands_list = []

        if self.bot.is_server_blacklisted(interaction.guild.id):
            await self.bot.handle_blacklisted_server(interaction)
            return

        # Define command sets based on permission levels
        all_commands = {
            "user": [
                {"name": "/cheers-count", "desc": "Show the count of cheers across all servers."},
                {"name": "/feedback", "desc": "Send feedback to the developers."},
                {"name": "/meetthedev", "desc": "Meet the developer of CheersBot."},
                {"name": "/partners", "desc": "Display the list of partner servers."},
                {"name": "/setup-info", "desc": "Display the current bot settings for this server (if setup is complete)."},
                {"name": "/uptime", "desc": "Check how long the bot has been online."},
                {"name": "/vote", "desc": "Vote for CheersBot on top.gg."},
                {"name": "/tokens", "desc": "Display the number of CheersTokens you have."},
                {"name": "/buy servertime", "desc": "Buy 12 hours of serverlisting time."},
                {"name": "/serverlist-view", "desc": "Find other 420 friendly servers to join."}
            ],
            "admin": [
                {"name": "/cheers", "desc": "Play the cheers sound in a voice channel."},
                {"name": "/blacklist", "desc": "Manage the blacklist of channels for auto-join."},
                {"name": "/mode", "desc": "Change the bot's mode for this server (single or random)."},
                {"name": "/setup", "desc": "Set up the bot for this server (required before use)."},
                {"name": "/sounds", "desc": "Manage sounds: set single sound or toggle random sounds."},
                {"name": "/serverlist [enable/disable]", "desc": "Manage server list visibility (Bot Admins only)."}
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

        if self.is_developer(user.id):
            commands_list.extend(all_commands["user"])
            commands_list.extend(all_commands["admin"])
            commands_list.extend(all_commands["developer"])
            commands_list.extend(all_commands["text_developer"])
            title = "CheersBot Help - Developer Menu"
        elif self.is_server_or_bot_admin(interaction):
            commands_list.extend(all_commands["user"])
            commands_list.extend(all_commands["admin"])
            title = "CheersBot Help - Admin Menu"
        else:
            commands_list.extend(all_commands["user"])
            title = "CheersBot Help - User Menu"

        commands_list.sort(key=lambda x: x["name"])
        commands_per_page = 10
        pages = [commands_list[i:i + commands_per_page] for i in range(0, len(commands_list), commands_per_page)]

        view = HelpView(pages, title, guild, self.global_config, interaction.user.id)
        await interaction.response.send_message(embed=view.create_embed(0), view=view, ephemeral=True)

class HelpView(ui.View):
    def __init__(self, pages, title, guild, global_config, user_id):
        super().__init__(timeout=300)
        self.pages = pages
        self.current_page = 0
        self.title = title
        self.guild = guild
        self.global_config = global_config
        self.user_id = user_id
        self.add_buttons()

    def add_buttons(self):
        self.add_item(ui.Button(
            label="Previous",
            style=discord.ButtonStyle.blurple,
            custom_id=f"help_prev_{self.user_id}",
            disabled=self.current_page == 0
        ))
        self.add_item(ui.Button(
            label=f"Page {self.current_page + 1}/{len(self.pages)}",
            style=discord.ButtonStyle.grey,
            disabled=True
        ))
        self.add_item(ui.Button(
            label="Next",
            style=discord.ButtonStyle.blurple,
            custom_id=f"help_next_{self.user_id}",
            disabled=self.current_page == len(self.pages) - 1
        ))

    def create_embed(self, page_num):
        embed = discord.Embed(
            title=self.title,
            description="Here are the commands you can use:",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        for cmd in self.pages[page_num]:
            embed.add_field(name=cmd["name"], value=cmd["desc"], inline=False)
        guild_icon_url = self.guild.icon.url if self.guild.icon else "https://i.imgur.com/4OO5wh0.png"
        embed.set_author(name=self.guild.name, icon_url=guild_icon_url)
        log_settings = self.global_config.get("log_settings", {})
        footer_text = log_settings.get("footer_text", "CheersBot V2.0 by HomiesHouse | Discord.gg/HomiesHouse")
        footer_icon_url = log_settings.get("footer_icon_url", "https://i.imgur.com/4OO5wh0.png")
        embed.set_footer(text=footer_text, icon_url=footer_icon_url)
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This help menu is for someone else!", ephemeral=True)
            return False
        return True

    @ui.button(label="Previous", style=discord.ButtonStyle.blurple)
    async def prev_button(self, interaction: discord.Interaction, button: ui.Button):
        print(f"Previous button clicked by {interaction.user.id}")
        self.current_page -= 1
        self.children[0].disabled = self.current_page == 0
        self.children[2].disabled = self.current_page == len(self.pages) - 1
        self.children[1].label = f"Page {self.current_page + 1}/{len(self.pages)}"
        await interaction.response.edit_message(embed=self.create_embed(self.current_page), view=self)

    @ui.button(label="Next", style=discord.ButtonStyle.blurple)
    async def next_button(self, interaction: discord.Interaction, button: ui.Button):
        print(f"Next button clicked by {interaction.user.id}")
        self.current_page += 1
        self.children[0].disabled = self.current_page == 0
        self.children[2].disabled = self.current_page == len(self.pages) - 1
        self.children[1].label = f"Page {self.current_page + 1}/{len(self.pages)}"
        await interaction.response.edit_message(embed=self.create_embed(self.current_page), view=self)

async def setup(bot):
    await bot.add_cog(HelpCog(bot, bot.global_config))