import discord
from discord import app_commands, ui
from discord.ext import commands
import json
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from topgg import WebhookManager
from aiohttp import web
import asyncio

class VotingCog(commands.Cog):
    def __init__(self, bot, global_config):
        self.bot = bot
        self.global_config = global_config
        self.cheers_tokens_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'CheersTokens.json')
        self.server_list_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'server_logs', 'CheersServerList.json')
        self.vote_tracking_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'VoteTracking.json')
        self.auth_code = os.getenv('TOPGG_AUTH_CODE')
        self.db_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'voters.db')
        
        # Initialize SQLite database
        self.init_database()
        
        self.load_or_create_cheers_tokens()
        self.load_or_create_server_list()
        self.load_or_create_vote_tracking()

        # Set up Top.gg webhook manager
        self.webhook_manager = WebhookManager(bot)
        self.webhook_manager.dbl_webhook('/webhook/topgg', self.on_topgg_vote_handler)
        self.bot.loop.create_task(self.start_webhook())
        
        # Start background tasks
        self.bot.loop.create_task(self.cleanup_expired_servers())
        self.bot.loop.create_task(self.vote_reminder_task())

    def init_database(self):
        """Initialize the SQLite database and create the voters table if it doesn't exist."""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS voters (
                    user_id TEXT PRIMARY KEY,
                    username TEXT,
                    last_vote_time TEXT,
                    server_name TEXT
                )
            """)
            conn.commit()

    def save_voter(self, user_id, username, last_vote_time, server_name):
        """Save or update voter information in the database."""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO voters (user_id, username, last_vote_time, server_name)
                VALUES (?, ?, ?, ?)
            """, (str(user_id), username, last_vote_time.isoformat(), server_name))
            conn.commit()

    def get_voter(self, user_id):
        """Retrieve voter information from the database."""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM voters WHERE user_id = ?", (str(user_id),))
            result = cursor.fetchone()
            if result:
                return {
                    "user_id": result[0],
                    "username": result[1],
                    "last_vote_time": datetime.fromisoformat(result[2]) if result[2] else None,
                    "server_name": result[3]
                }
        return None

    def load_or_create_cheers_tokens(self):
        if not os.path.exists(self.cheers_tokens_file):
            with open(self.cheers_tokens_file, 'w') as f:
                json.dump({}, f, indent=4)

    def load_cheers_tokens(self):
        print(f"Loading From: {self.cheers_tokens_file}")
        try:
            with open(self.cheers_tokens_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading CheersTokens.json: {e}. Creating a new empty file.")
            self.load_or_create_cheers_tokens()
            return {}

    def save_cheers_tokens(self, data):
        with open(self.cheers_tokens_file, 'w') as f:
            json.dump(data, f, indent=4)

    def load_or_create_server_list(self):
        server_logs_dir = os.path.dirname(self.server_list_file)
        if not os.path.exists(server_logs_dir):
            os.makedirs(server_logs_dir)
        if not os.path.exists(self.server_list_file):
            with open(self.server_list_file, 'w') as f:
                json.dump({"active_servers": [], "inactive_servers": []}, f, indent=4)

    def load_server_list(self):
        try:
            with open(self.server_list_file, 'r') as f:
                data = json.load(f)
                if "active_servers" not in data:
                    data["active_servers"] = []
                if "inactive_servers" not in data:
                    data["inactive_servers"] = []
                return data
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading CheersServerList.json: {e}. Creating a new empty file.")
            self.load_or_create_server_list()
            return {"active_servers": [], "inactive_servers": []}

    def save_server_list(self, data):
        with open(self.server_list_file, 'w') as f:
            json.dump(data, f, indent=4)

    def load_or_create_vote_tracking(self):
        if not os.path.exists(self.vote_tracking_file):
            with open(self.vote_tracking_file, 'w') as f:
                json.dump({}, f, indent=4)

    def load_vote_tracking(self):
        try:
            with open(self.vote_tracking_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading VoteTracking.json: {e}. Creating a new empty file.")
            self.load_or_create_vote_tracking()
            return {}

    def save_vote_tracking(self, data):
        with open(self.vote_tracking_file, 'w') as f:
            json.dump(data, f, indent=4)

    def record_vote_intent(self, user_id, guild_id, channel_id, message_id):
        tracking = self.load_vote_tracking()
        tracking[str(user_id)] = {
            "guild_id": str(guild_id),
            "channel_id": str(channel_id),
            "message_id": str(message_id),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.save_vote_tracking(tracking)

    def get_vote_origin(self, user_id):
        tracking = self.load_vote_tracking()
        user_data = tracking.get(str(user_id))
        if not user_data:
            return None, None, None
        vote_time = datetime.fromisoformat(user_data["timestamp"])
        time_diff = datetime.now(timezone.utc) - vote_time
        if time_diff.total_seconds() > 86400:  # 24 hours
            return None, None, None
        return int(user_data["guild_id"]), int(user_data["channel_id"]), int(user_data["message_id"])

    @app_commands.command(name="vote", description="Learn how to vote for CheersBot and earn Cheers Tokens!")
    async def vote(self, interaction: discord.Interaction):
        if self.bot.is_server_blacklisted(interaction.guild.id):
            await self.bot.handle_blacklisted_server(interaction)
            return

        embed = discord.Embed(
            title="Vote for CheersBot!",
            description=(
                "Support CheersBot by voting on Top.gg! Each vote earns you **1 Cheers Token**, "
                "which you can use to promote your server on the CheersBot Server List.\n\n"
                "1. Click the button below to visit the voting page.\n"
                "2. Log in with Discord and cast your vote.\n"
                "3. Once confirmed, a Cheers Token will be credited to your account!"
                "\n\n"
                "You can use `/tokens` to check your Cheers Tokens balance."
            ),
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=self.global_config.get("thumbnail_url", "https://i.imgur.com/4OO5wh0.png"))
        embed.set_footer(
            text=self.global_config.get("log_settings", {}).get("footer_text", "CheersBot V2.0 by HomiesHouse | Discord.gg/HomiesHouse"),
            icon_url=self.global_config.get("log_settings", {}).get("footer_icon_url", "https://i.imgur.com/4OO5wh0.png")
        )

        view = ui.View()
        view.add_item(ui.Button(
            label="Vote Now",
            style=discord.ButtonStyle.link,
            url=self.global_config.get("voting_url", "https://top.gg/bot/1294444615327285308/vote")
        ))

        message = await interaction.response.send_message(embed=embed, view=view)
        message = await interaction.original_response()
        self.record_vote_intent(interaction.user.id, interaction.guild.id, interaction.channel_id, message.id)

    async def on_topgg_vote_handler(self, request):
        auth_header = request.headers.get("Authorization")
        if auth_header != self.auth_code:
            print(f"Unauthorized webhook request: {auth_header}")
            return web.json_response({"status": "error", "message": "Unauthorized"}, status=401)

        try:
            data = await request.json()
            print(f"Received vote data: {data}")
            user_id = int(data["user"])
            guild_id = int(data.get("guild", 0))

            inferred_guild_id, channel_id, message_id = self.get_vote_origin(user_id)
            if guild_id == 0:
                guild_id = inferred_guild_id if inferred_guild_id else 0

            # Get user and guild information
            user = await self.bot.fetch_user(user_id)
            guild = self.bot.get_guild(guild_id) if guild_id else None
            server_name = guild.name if guild else None

            # Save voter information to database
            self.save_voter(
                user_id=user_id,
                username=user.name,
                last_vote_time=datetime.now(timezone.utc),
                server_name=server_name
            )

            tokens = self.load_cheers_tokens()
            user_id_str = str(user_id)
            tokens[user_id_str] = tokens.get(user_id_str, 0) + 1
            self.save_cheers_tokens(tokens)

            voting_channel_id = int(self.global_config.get("developer_voting_channel_id", "0"))
            voting_channel = self.bot.get_channel(voting_channel_id)
            if voting_channel:
                # Create embed based on whether server is known
                embed = discord.Embed(
                    title="New Vote Received!",
                    color=discord.Color.gold(),
                    timestamp=datetime.now(timezone.utc)
                )
                if guild:
                    embed.description = f"<@{user_id}> voted for CheersBot from **{guild.name}**!"
                else:
                    embed.description = f"<@{user_id}> voted for CheersBot!"
                
                embed.set_footer(
                    text=self.global_config.get("log_settings", {}).get("footer_text", "CheersBot V2.0 by HomiesHouse | Discord.gg/HomiesHouse"),
                    icon_url=self.global_config.get("log_settings", {}).get("footer_icon_url", "https://i.imgur.com/4OO5wh0.png")
                )
                await voting_channel.send(embed=embed)
            else:
                print(f"Developer voting channel {voting_channel_id} not found or inaccessible.")

            if message_id and guild_id and channel_id:
                guild = self.bot.get_guild(guild_id)
                if guild:
                    channel = guild.get_channel(channel_id)
                    if channel:
                        try:
                            message = await channel.fetch_message(message_id)
                            thank_you_embed = discord.Embed(
                                title="Thank You for Voting!",
                                description=f"Thank you for voting for CheersBot, <@{user_id}>! You've earned **1 Cheers Token**. You can vote again in 12 hours!",
                                color=discord.Color.green()
                            )
                            thank_you_embed.set_thumbnail(url=self.global_config.get("thumbnail_url", "https://i.imgur.com/4OO5wh0.png"))
                            thank_you_embed.set_footer(
                                text=self.global_config.get("log_settings", {}).get("footer_text", "CheersBot V2.0 by HomiesHouse | Discord.gg/HomiesHouse"),
                                icon_url=self.global_config.get("log_settings", {}).get("footer_icon_url", "https://i.imgur.com/4OO5wh0.png")
                            )
                            await message.edit(embed=thank_you_embed, view=None)
                        except discord.NotFound:
                            print(f"Message {message_id} not found in channel {channel.id}")
                        except discord.Forbidden:
                            print(f"No permission to edit message {message_id} in channel {channel.id}")

            print("Vote processed successfully")
            return web.json_response({"status": "success"}, status=200)
        except Exception as e:
            print(f"Error in vote handler: {e}")
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def vote_reminder_task(self):
        """Check for users whose 12-hour vote cooldown has expired and send reminders."""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                with sqlite3.connect(self.db_file) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT user_id, username, last_vote_time FROM voters")
                    voters = cursor.fetchall()

                current_time = datetime.now(timezone.utc)
                voting_channel_id = int(self.global_config.get("developer_voting_channel_id", "0"))
                voting_channel = self.bot.get_channel(voting_channel_id)

                for voter in voters:
                    user_id, username, last_vote_time = voter
                    last_vote = datetime.fromisoformat(last_vote_time)
                    time_since_vote = current_time - last_vote

                    if time_since_vote >= timedelta(hours=12):
                        user = await self.bot.fetch_user(int(user_id))
                        if user:
                            # Send DM to user
                            reminder_embed = discord.Embed(
                                title="You Can Vote Again!",
                                description=(
                                    f"Hey {user.mention}, it's been 12 hours since your last vote for CheersBot! "
                                    "You can vote again to earn another Cheers Token!\n\n"
                                    f"[Vote Now]({self.global_config.get('voting_url', 'https://top.gg/bot/1294444615327285308/vote')})"
                                ),
                                color=discord.Color.blue()
                            )
                            reminder_embed.set_thumbnail(url=self.global_config.get("thumbnail_url", "https://i.imgur.com/4OO5wh0.png"))
                            reminder_embed.set_footer(
                                text=self.global_config.get("log_settings", {}).get("footer_text", "CheersBot V2.0 by HomiesHouse | Discord.gg/HomiesHouse"),
                                icon_url=self.global_config.get("log_settings", {}).get("footer_icon_url", "https://i.imgur.com/4OO5wh0.png")
                            )

                            dm_success = False
                            try:
                                await user.send(embed=reminder_embed)
                                dm_success = True
                            except discord.Forbidden:
                                print(f"Cannot send DM to {username} ({user_id}): DMs disabled")
                            except Exception as e:
                                print(f"Error sending DM to {username} ({user_id}): {e}")

                            # Send reminder to developer voting channel
                            if voting_channel:
                                channel_embed = discord.Embed(
                                    title="Vote Reminder Sent",
                                    description=(
                                        f"Reminder sent to <@{user_id}> to vote again."
                                        f"\nDM Successful: {'Yes' if dm_success else 'No'}"
                                    ),
                                    color=discord.Color.blue(),
                                    timestamp=datetime.now(timezone.utc)
                                )
                                channel_embed.set_footer(
                                    text=self.global_config.get("log_settings", {}).get("footer_text", "CheersBot V2.0 by HomiesHouse | Discord.gg/HomiesHouse"),
                                    icon_url=self.global_config.get("log_settings", {}).get("footer_icon_url", "https://i.imgur.com/4OO5wh0.png")
                                )
                                # Ghost ping
                                ping_message = await voting_channel.send(f"<@{user_id}>")
                                await ping_message.delete()
                                await voting_channel.send(embed=channel_embed)

                        # Update last_vote_time to prevent repeated reminders
                        # Set to a future time to avoid immediate re-trigger
                        self.save_voter(
                            user_id=user_id,
                            username=username,
                            last_vote_time=last_vote,  # Keep original time for record
                            server_name=self.get_voter(user_id).get("server_name")
                        )

                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                print(f"Error in vote_reminder_task: {e}")
                await asyncio.sleep(60)  # Wait before retrying on error

    async def start_webhook(self):
        app = web.Application()
        app.router.add_post('/webhook/topgg', self.on_topgg_vote_handler)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 5001)
        await site.start()
        print("Webhook server started on port 5001")

    async def cleanup_expired_servers(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                server_list = self.load_server_list()
                current_time = datetime.now(timezone.utc)
                
                active_servers = server_list["active_servers"]
                updated_active_servers = [
                    server for server in active_servers
                    if datetime.fromisoformat(server["end_time"]) > current_time
                    or server["end_time"] == "9999-12-31T23:59:59+00:00"
                ]
                
                inactive_servers = server_list["inactive_servers"]
                updated_inactive_servers = [
                    server for server in inactive_servers
                    if datetime.fromisoformat(server["end_time"]) > current_time
                ]
                
                if len(updated_active_servers) != len(active_servers) or len(updated_inactive_servers) != len(inactive_servers):
                    server_list["active_servers"] = updated_active_servers
                    server_list["inactive_servers"] = updated_inactive_servers
                    self.save_server_list(server_list)
                    print(f"Cleaned up expired servers. Active: {len(updated_active_servers)}, Inactive: {len(updated_inactive_servers)}")
                
                await asyncio.sleep(3600)  # Check every hour
            except Exception as e:
                print(f"Error in cleanup_expired_servers: {e}")
                await asyncio.sleep(3600)  # Wait before retrying on error

    @app_commands.command(name="serverlist", description="Manage server list visibility (Bot Admins only).")
    @app_commands.choices(action=[
        app_commands.Choice(name="Enable", value="enable"),
        app_commands.Choice(name="Disable", value="disable")
    ])
    async def serverlist(self, interaction: discord.Interaction, action: str):
        if self.bot.is_server_blacklisted(interaction.guild.id):
            await self.bot.handle_blacklisted_server(interaction)
            return
        
        if not await self.bot.ensure_setup(interaction):
            return
        
        if not self.is_bot_admin(interaction):
            await interaction.response.send_message(
                "You must be a bot admin to use this command.", 
                ephemeral=True
            )
            return
        
        server_config = self.bot.load_or_create_server_config(interaction.guild.id)
        server_list = self.load_server_list()
        
        if action == "enable":
            server_config["server_list_enabled"] = True
            existing_server = next((s for s in server_list["inactive_servers"] if s["guild_id"] == interaction.guild.id), None)
            if existing_server:
                end_time = datetime.fromisoformat(existing_server["end_time"])
                if end_time > datetime.now(timezone.utc):
                    invite_url = await self.get_existing_invite(interaction.guild) or "No Invite Available"
                    existing_server["name"] = interaction.guild.name
                    existing_server["owner_id"] = f"<@{interaction.guild.owner_id}>"
                    existing_server["members"] = interaction.guild.member_count
                    existing_server["invite"] = invite_url
                    existing_server["is_premium"] = server_config.get("is_premium", False)
                    server_list["inactive_servers"] = [s for s in server_list["inactive_servers"] if s["guild_id"] != interaction.guild.id]
                    server_list["active_servers"].append(existing_server)
                    await interaction.response.send_message(
                        f"Server list visibility has been enabled. {interaction.guild.name} has been re-added to the server list with remaining time.",
                        ephemeral=True
                    )
                else:
                    server_list["inactive_servers"] = [s for s in server_list["inactive_servers"] if s["guild_id"] != interaction.guild.id]
                    await interaction.response.send_message(
                        "Server list visibility has been enabled. The previous time has expired. Use `/buy servertime` to add time and list your server.",
                        ephemeral=True
                    )
            else:
                existing_server = next((s for s in server_list["active_servers"] if s["guild_id"] == interaction.guild.id), None)
                if existing_server and datetime.fromisoformat(existing_server["end_time"]) > datetime.now(timezone.utc):
                    await interaction.response.send_message(
                        f"Server list visibility has been enabled. {interaction.guild.name} is already on the server list with remaining time.",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        "Server list visibility has been enabled. Use `/buy servertime` to add time and list your server.",
                        ephemeral=True
                    )
        
        elif action == "disable":
            server_config["server_list_enabled"] = False
            existing_server = next((s for s in server_list["active_servers"] if s["guild_id"] == interaction.guild.id), None)
            if existing_server:
                server_list["active_servers"] = [s for s in server_list["active_servers"] if s["guild_id"] != interaction.guild.id]
                server_list["inactive_servers"].append(existing_server)
                await interaction.response.send_message(
                    f"Server list visibility has been disabled. {interaction.guild.name} has been removed from the server list, but its remaining time is preserved.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "Server list visibility has been disabled. The server was not on the list.",
                    ephemeral=True
                )
        
        await self.bot.save_config(interaction.guild.id, server_config)
        self.save_server_list(server_list)

    def is_bot_admin(self, interaction: discord.Interaction) -> bool:
        developer_ids = self.global_config.get("bot_developer_ids", [])
        return (interaction.user.id in developer_ids or 
                interaction.user.guild_permissions.administrator)

    buy_group = app_commands.Group(name="buy", description="Use Cheers Tokens to manage your server listing.")

    @buy_group.command(name="servertime", description="Add server time to the CheersBot Server List.")
    @app_commands.describe(amount="Number of 12-hour increments to buy (default: 1).")
    async def buy_servertime(self, interaction: discord.Interaction, amount: int = 1):
        if self.bot.is_server_blacklisted(interaction.guild.id):
            await self.bot.handle_blacklisted_server(interaction)
            return
        if not await self.bot.ensure_setup(interaction):
            return

        server_config = self.bot.load_or_create_server_config(interaction.guild.id)
        if not server_config.get("server_list_enabled", False):
            await interaction.response.send_message(
                "This server is not enabled for the server list. An admin must use `/serverlist enable` first.",
                ephemeral=True
            )
            return

        tokens = self.load_cheers_tokens()
        user_id_str = str(interaction.user.id)
        user_tokens = tokens.get(user_id_str, 0)
        if user_tokens < amount:
            await interaction.response.send_message(
                f"You need at least `{amount}` Cheers Tokens to buy {amount} server time increments (12 hours each). You currently have `{user_tokens}` tokens. Vote using `/vote` to earn more!",
                ephemeral=True
            )
            return

        tokens[user_id_str] -= amount
        self.save_cheers_tokens(tokens)

        server_list = self.load_server_list()
        guild = interaction.guild
        invite_url = await self.get_existing_invite(guild) or "No Invite Available"

        existing_server = next((s for s in server_list["active_servers"] if s["guild_id"] == guild.id), None)
        if not existing_server:
            existing_server = next((s for s in server_list["inactive_servers"] if s["guild_id"] == guild.id), None)
            if existing_server:
                server_list["inactive_servers"] = [s for s in server_list["inactive_servers"] if s["guild_id"] != guild.id]

        if existing_server:
            current_end_time = datetime.fromisoformat(existing_server["end_time"])
            new_end_time = max(current_end_time, datetime.now(timezone.utc)) + timedelta(hours=12 * amount)
            existing_server["end_time"] = new_end_time.isoformat()
            existing_server["members"] = guild.member_count
            existing_server["invite"] = invite_url
            server_list["active_servers"].append(existing_server)
        else:
            end_time = datetime.now(timezone.utc) + timedelta(hours=12 * amount)
            server_entry = {
                "guild_id": guild.id,
                "name": guild.name,
                "owner_id": f"<@{guild.owner_id}>",
                "members": guild.member_count,
                "invite": invite_url,
                "end_time": end_time.isoformat(),
                "is_premium": server_config.get("is_premium", False)
            }
            server_list["active_servers"].append(server_entry)

        self.save_server_list(server_list)

        hours_added = 12 * amount
        await interaction.response.send_message(
            f"Success! {guild.name} has {'been added to' if not existing_server else 'had its time extended on'} the CheersBot Server List by {hours_added} hours with {amount} Cheers Token{'s' if amount > 1 else ''}. You now have `{tokens[user_id_str]}` tokens remaining."
        )

    async def get_existing_invite(self, guild):
        try:
            if guild.vanity_url_code:
                return f"https://discord.gg/{guild.vanity_url_code}"
            invites = await guild.invites()
            for invite in invites:
                if invite.max_age == 0 and invite.max_uses == 0:
                    return invite.url
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).create_instant_invite:
                    invite = await channel.create_invite(max_age=0, max_uses=0)
                    return invite.url
        except Exception as e:
            print(f"Error getting invite for {guild.name}: {e}")
        return None

    def format_time_left(self, end_time_str):
        end_time = datetime.fromisoformat(end_time_str)
        now = datetime.now(timezone.utc)
        delta = end_time - now

        if delta.total_seconds() <= 0:
            return "Expired"

        years = delta.days // 365
        months = (delta.days % 365) // 30
        days = delta.days % 30
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        seconds = delta.seconds % 60

        time_parts = []
        if years > 0:
            time_parts.append(f"{years}y")
        if months > 0:
            time_parts.append(f"{months}m")
        if days > 0:
            time_parts.append(f"{days}d")
        if hours > 0:
            time_parts.append(f"{hours}hrs")
        if minutes > 0:
            time_parts.append(f"{minutes}m")
        if seconds > 0 or not time_parts:
            time_parts.append(f"{seconds}s")

        return " ".join(time_parts)

    def get_time_left_seconds(self, end_time_str):
        end_time = datetime.fromisoformat(end_time_str)
        now = datetime.now(timezone.utc)
        delta = end_time - now
        return max(delta.total_seconds(), 0)

    @app_commands.command(name="serverlist-view", description="View the CheersBot Server List.")
    async def serverlist_view(self, interaction: discord.Interaction):
        if self.bot.is_server_blacklisted(interaction.guild.id):
            await self.bot.handle_blacklisted_server(interaction)
            return

        await interaction.response.defer()

        try:
            server_list = self.load_server_list()
            current_time = datetime.now(timezone.utc)

            all_servers = server_list["active_servers"]
            updated_servers = []
            for server in all_servers:
                guild = self.bot.get_guild(server["guild_id"])
                if guild:
                    server["members"] = guild.member_count
                updated_servers.append(server)
            server_list["active_servers"] = updated_servers
            self.save_server_list(server_list)

            master_server_id = int(self.global_config.get("master_server_id"))
            master_guild = self.bot.get_guild(master_server_id)
            master_entry = {
                "name": f"⭐ {master_guild.name if master_guild else 'Master Server'}",
                "owner_id": ", ".join([f"<@{id}>" for id in self.global_config.get('bot_developer_ids', [])]),
                "members": master_guild.member_count if master_guild else "Unknown",
                "invite": self.global_config.get("discord_link", "https://discord.gg/HomiesHouse"),
                "end_time": "9999-12-31T23:59:59+00:00"
            }

            premium_servers = [s for s in all_servers if s.get("is_premium", False)]
            regular_servers = [s for s in all_servers if not s.get("is_premium", False) and self.get_time_left_seconds(s["end_time"]) > 0]

            premium_servers.sort(key=lambda x: self.get_time_left_seconds(x["end_time"]), reverse=True)
            regular_servers.sort(key=lambda x: self.get_time_left_seconds(x["end_time"]), reverse=True)

            all_servers_list = [master_entry] + premium_servers + regular_servers
            for server in premium_servers:
                server["name"] = f"⭐ {server['name']}"

            pages = [all_servers_list[i:i + 5] for i in range(0, len(all_servers_list), 5)]
            if not pages:
                await interaction.followup.send("The CheersBot Server List is currently empty.")
                return

            view = ServerListView(pages, interaction, self.bot)
            await interaction.followup.send(embed=await view.create_embed(), view=view)
        except Exception as e:
            print(f"Error in serverlist-view: {e}")
            await interaction.followup.send("An error occurred while loading the server list. Please try again later.", ephemeral=True)

    @app_commands.command(name="tokens", description="Check how many Cheers Tokens a user has.")
    @app_commands.describe(user="The user to check tokens for (optional).")
    async def tokens(self, interaction: discord.Interaction, user: discord.User = None):
        target_user = user if user else interaction.user
        tokens = self.load_cheers_tokens()
        user_id_str = str(target_user.id)
        token_count = tokens.get(user_id_str, 0)

        embed = discord.Embed(
            title="Cheers Tokens",
            description=f"{target_user.mention} has `{token_count}` Cheers Tokens.",
            color=discord.Color.green()
        )
        embed.set_footer(
            text=self.global_config.get("log_settings", {}).get("footer_text", "CheersBot V2.0 by HomiesHouse | Discord.gg/HomiesHouse"),
            icon_url=self.global_config.get("log_settings", {}).get("footer_icon_url", "https://i.imgur.com/4OO5wh0.png")
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ServerListView(ui.View):
    def __init__(self, pages, interaction, bot):
        super().__init__(timeout=300)
        self.pages = pages
        self.current_page = 0
        self.interaction = interaction
        self.bot = bot
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        self.add_item(ui.Button(
            label="Previous",
            style=discord.ButtonStyle.blurple,
            custom_id="prev",
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
            custom_id="next",
            disabled=self.current_page == len(self.pages) - 1
        ))

    async def create_embed(self):
        embed = discord.Embed(
            title="CheersBot Server List",
            description="Explore 420-friendly servers! Vote to add yours with `/vote` and `/buy`.",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        for server in self.pages[self.current_page]:
            if server["end_time"] == "9999-12-31T23:59:59+00:00":
                value = f"Owner: {server['owner_id']}\nMembers: `{server['members']}`\n[Join]({server['invite']})"
            else:
                time_left = self.bot.get_cog("VotingCog").format_time_left(server["end_time"])
                if time_left == "Expired" and not server.get("is_premium", False):
                    value = f"Owner: {server['owner_id']}\nMembers: `{server['members']}`\n[Join]({server['invite']})"
                else:
                    value = f"Owner: {server['owner_id']}\nMembers: `{server['members']}`\nTime Left: `{time_left}`\n[Join]({server['invite']})"
            embed.add_field(
                name=server["name"],
                value=value,
                inline=False
            )
        embed.set_footer(
            text=self.bot.global_config.get("log_settings", {}).get("footer_text", "CheersBot V2.0 by HomiesHouse | Discord.gg/HomiesHouse"),
            icon_url=self.bot.global_config.get("log_settings", {}).get("footer_icon_url", "https://i.imgur.com/4OO5wh0.png")
        )
        return embed

    @ui.button(label="Previous", style=discord.ButtonStyle.blurple, custom_id="prev")
    async def prev_button(self, interaction: discord.Interaction, button: ui.Button):
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=await self.create_embed(), view=self)

    @ui.button(label="Next", style=discord.ButtonStyle.blurple, custom_id="next")
    async def next_button(self, interaction: discord.Interaction, button: ui.Button):
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=await self.create_embed(), view=self)

async def setup(bot):
    cog = VotingCog(bot, bot.global_config)
    await bot.add_cog(cog)
    print("VotingCog loaded successfully")