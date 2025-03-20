import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
import os
import json

class UptimeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.now(timezone.utc)  # Record the time when the cog is initialized
        self.config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config.json')

    def load_longest_uptime(self):
        """Load the longest uptime from config.json."""
        return self.bot.global_config.get('longest_uptime_seconds', 0)

    def save_longest_uptime(self, longest_uptime):
        """Save the longest uptime to config.json."""
        with open(self.config_path, 'r') as f:
            config_data = json.load(f)
        
        config_data['longest_uptime_seconds'] = longest_uptime
        with open(self.config_path, 'w') as f:
            json.dump(config_data, f, indent=4)
        
        # Update the in-memory global_config to reflect the change
        self.bot.global_config['longest_uptime_seconds'] = longest_uptime

    def update_longest_uptime(self, current_uptime_seconds):
        """Update the longest uptime if the current uptime exceeds it."""
        longest_uptime = self.load_longest_uptime()
        if current_uptime_seconds > longest_uptime:
            self.save_longest_uptime(current_uptime_seconds)
            return current_uptime_seconds
        return longest_uptime

    def format_uptime(self, total_seconds):
        """Format uptime in seconds into a human-readable string."""
        days = total_seconds // (24 * 3600)
        hours = (total_seconds % (24 * 3600)) // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        uptime_str = ""
        if days > 0:
            uptime_str += f"{days} day{'s' if days != 1 else ''}, "
        if hours > 0 or days > 0:
            uptime_str += f"{hours} hour{'s' if hours != 1 else ''}, "
        if minutes > 0 or hours > 0 or days > 0:
            uptime_str += f"{minutes} minute{'s' if minutes != 1 else ''}, "
        uptime_str += f"{seconds} second{'s' if seconds != 1 else ''}"
        return uptime_str

    @app_commands.command(name="uptime", description="Check how long the bot has been online and its longest uptime ever.")
    async def uptime(self, interaction: discord.Interaction):
        if self.bot.is_server_blacklisted(interaction.guild.id):
            await self.bot.handle_blacklisted_server(interaction)
            return

        try:
            current_time = datetime.now(timezone.utc)
            uptime_duration = current_time - self.start_time
            current_uptime_seconds = int(uptime_duration.total_seconds())

            # Update and get the longest uptime
            longest_uptime_seconds = self.update_longest_uptime(current_uptime_seconds)

            # Format current and longest uptime
            current_uptime_str = self.format_uptime(current_uptime_seconds)
            longest_uptime_str = self.format_uptime(longest_uptime_seconds)

            # Create embed
            embed = discord.Embed(
                title="Bot Uptime",
                color=discord.Color.blue(),
                timestamp=current_time
            )
            embed.add_field(
                name="Current Uptime",
                value=f"CheersBot has been online for: **{current_uptime_str}**",
                inline=False
            )
            embed.add_field(
                name="Longest Uptime Ever",
                value=f"The longest CheersBot has ever been online: **{longest_uptime_str}**",
                inline=False
            )

            # Load formatting from global config
            log_settings = self.bot.global_config.get("log_settings", {})
            footer_text = log_settings.get("footer_text", "CheersBot V2.0 by HomiesHouse | Discord.gg/HomiesHouse")
            footer_icon_url = log_settings.get("footer_icon_url", "https://i.imgur.com/4OO5wh0.png")
            thumbnail_url = log_settings.get("thumbnail_url", "https://i.imgur.com/4OO5wh0.png")

            embed.set_thumbnail(url=thumbnail_url)
            embed.set_footer(text=footer_text, icon_url=footer_icon_url)

            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error retrieving uptime: {e}", ephemeral=True)
            print(f"Error in uptime command: {e}")

async def setup(bot):
    await bot.add_cog(UptimeCog(bot))