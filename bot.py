# CheersBot v2 - A Discord bot by Wubbity. Cheers!

import os
import json
import platform
import asyncio
import random
import pytz
import discord
import math
import importlib.util
from discord.ext import commands, tasks
from discord import app_commands, ui, ButtonStyle, Interaction
from discord.ui import View, Button
from discord.ext.commands import AutoShardedBot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from discord import app_commands
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
MASTER_GUILD_ID = int(os.getenv('MASTER_GUILD_ID'))

# Config directory for each server
CONFIG_DIR = 'configs'
if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)

# Detect the current operating system
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(BASE_DIR, "config.json")
SOUND_FOLDER = os.path.abspath(os.path.join(BASE_DIR, "cheers_sounds"))
current_os = platform.system()

# Server logs directory
SERVER_LOG_DIR = os.path.join(BASE_DIR, "server_logs")
if not os.path.exists(SERVER_LOG_DIR):
    os.makedirs(SERVER_LOG_DIR)

SERVER_LIST_PATH = os.path.join(SERVER_LOG_DIR, "ServerList.log")
MASTER_SERVER_LIST_PATH = os.path.join(SERVER_LOG_DIR, "MASTERServerList.log")

# Define the path for the UserData folder
USER_DATA_FOLDER = os.path.join(BASE_DIR, "UserData")
if not os.path.exists(USER_DATA_FOLDER):
    os.makedirs(USER_DATA_FOLDER)

# Path to store feedback bans
FEEDBACK_BANS_PATH = os.path.join(SERVER_LOG_DIR, "FeedbackBans.json")

def load_feedback_bans():
    if os.path.exists(FEEDBACK_BANS_PATH):
        with open(FEEDBACK_BANS_PATH, 'r') as f:
            return json.load(f)
    return {}

def save_feedback_bans(feedback_bans):
    with open(FEEDBACK_BANS_PATH, 'w') as f:
        json.dump(feedback_bans, f, indent=4)

# Path to store blacklisted servers
BLACKLISTED_SERVERS_PATH = os.path.join(SERVER_LOG_DIR, "BlacklistedServers.json")

def load_blacklisted_servers():
    if os.path.exists(BLACKLISTED_SERVERS_PATH):
        with open(BLACKLISTED_SERVERS_PATH, 'r') as f:
            return json.load(f)
    return []

def save_blacklisted_servers(blacklisted_servers):
    with open(BLACKLISTED_SERVERS_PATH, 'w') as f:
        json.dump(blacklisted_servers, f, indent=4)

def is_server_blacklisted(guild_id):
    blacklisted_servers = load_blacklisted_servers()
    return any(server['id'] == str(guild_id) for server in blacklisted_servers)

async def handle_blacklisted_server(interaction):
    blacklisted_servers = load_blacklisted_servers()
    server_info = next((server for server in blacklisted_servers if server['id'] == str(interaction.guild.id)), None)
    reason = server_info['reason'] if server_info else "No reason provided."
    
    with open(config_path, 'r') as f:
        global_config = json.load(f)
    developer_id = global_config.get("bot_developer_ids", [])[0]  # Get the first developer ID

    embed = discord.Embed(
        title="Server Blacklisted",
        description=f"This server has been blacklisted from CheersBot.\n\nReason: {reason}\n\nJoin [HomiesHouse](https://discord.gg/HomiesHouse) and DM <@{developer_id}> for assistance.",
        color=discord.Color.red()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Load developer IDs from config.json
def load_developer_ids():
    with open(config_path, 'r') as f:
        global_config = json.load(f)
    return global_config.get("bot_developer_ids", [])

# Update ffmpeg path for Windows and Linux dynamically based on the detected OS
if current_os == "Windows":
    ffmpeg_path = os.path.join(BASE_DIR, "FFMPEG", "ffmpeg.exe")  # Windows executable
#elif current_os == "Linux":
#   ffmpeg_path = os.path.join("/usr/bin/", "ffmpeg")  # Default for Linux in /usr/bin
elif current_os == "Linux":
    ffmpeg_path = os.path.join(BASE_DIR, "FFMPEG", "ffmpeg")  # Linux in-folder installation
else:
    raise OSError(f"Unsupported operating system: {current_os}")

print(f"Sound folder path: {SOUND_FOLDER}")
print(f"FFmpeg path: {ffmpeg_path}")

# Helper Functions for Configurations
def get_config_filepath(guild_id):
    return os.path.join(CONFIG_DIR, f'config_{guild_id}.json')

def load_or_create_server_config(guild_id):
    """Load or create a server-specific configuration."""
    config_file = os.path.join(BASE_DIR, f"configs/config_{guild_id}.json")
    
    # If the config file exists, load it
    if (os.path.exists(config_file)):
        with open(config_file, 'r') as f:
            config = json.load(f)
    else:
        # Default configuration for new servers
        config = {
            "log_channel_id": None,
            "admin_roles": [],
            "mode": "single",  # Default mode is 'single'
            "default_sound": "Cheers_Bitch.mp3"
        }
        save_config(guild_id, config)

    # Ensure all keys exist in case config file is missing any of them
    config.setdefault("log_channel_id", None)
    config.setdefault("admin_roles", [])
    config.setdefault("mode", "single")
    config.setdefault("default_sound", "Cheers_Bitch.mp3")
    config.setdefault("blacklist_channels", [])
    config.setdefault("local_cheers_count", 0)

    return config

async def update_server_list():
    try:
        with open(SERVER_LIST_PATH, 'w') as f:
            for guild in bot.guilds:
                owner_id = guild.owner_id if guild.owner else "Unknown"
                total_members = guild.member_count
                total_bots = sum(1 for member in guild.members if member.bot)
                join_date = guild.me.joined_at.astimezone(pytz.timezone('America/Chicago')).strftime("%Y-%m-%d %H:%M:%S CST")
                invite_url = "No invite available"
                try:
                    invites = await guild.invites()
                    invite = next((i for i in invites if not i.max_age and not i.max_uses), None)
                    if invite:
                        invite_url = invite.url
                    else:
                        invite_url = "No Invites"
                except discord.Forbidden:
                    if debug_mode:
                        print(f"Could not retrieve invites for {guild.name}")
                    invite_url = "No Permission"
                f.write(f"{guild.name} (ID: {guild.id}) | Joined: {join_date} | Server Owner ID: {owner_id} | Total Members: {total_members} | Total Bots: {total_bots} | Invite: {invite_url}\n")
    except Exception as e:
        print(f"Error updating ServerList.log: {e}")

def update_master_server_summary():
    """Updates the summary at the bottom of the MASTERServerList.log."""
    try:
        with open(MASTER_SERVER_LIST_PATH, 'r') as f:
            lines = f.readlines()

        # Filter valid server entries (ignoring summary lines)
        server_entries = [line for line in lines if 'ID:' in line]

        total_servers_ever = len(set(line.split('ID: ')[1].split(')')[0] for line in server_entries))
        current_servers = len(bot.guilds)

        summary = f"\nTotal Servers Joined Ever: {total_servers_ever}\nCurrent Active Servers: {current_servers}\n"

        # Rewrite the log file without previous summaries
        with open(MASTER_SERVER_LIST_PATH, 'w') as f:
            f.writelines(server_entries)  # Write all valid entries
            f.write(summary)  # Append the updated summary

    except Exception as e:
        print(f"Error updating MASTERServerList summary: {e}")

def log_to_master_server_list(action, guild, reason=None, invite=None):
    existing_servers = load_master_server_list()

    if str(guild.id) not in existing_servers:
        timestamp = datetime.now(pytz.timezone('America/Chicago')).strftime("%Y-%m-%d %H:%M:%S CST")
        entry = f"[{timestamp}] {action}: {guild.name} (ID: {guild.id})"
        if reason:
            entry += f" | Reason: {reason}"
        if invite:
            entry += f" | Invite: {invite}"

        try:
            with open(MASTER_SERVER_LIST_PATH, 'a') as f:
                f.write(entry + "\n")
        except Exception as e:
            print(f"Error logging to MASTERServerList.log: {e}")
    else:
        # Update existing entry with new join time if reinvited
        timestamp = datetime.now(pytz.timezone('America/Chicago')).strftime("%Y-%m-%d %H:%M:%S CST")
        entry = f"[{timestamp}] {action}: {guild.name} (ID: {guild.id})"
        if reason:
            entry += f" | Reason: {reason}"
        if invite:
            entry += f" | Invite: {invite}"

        try:
            with open(MASTER_SERVER_LIST_PATH, 'r') as f:
                lines = f.readlines()

            with open(MASTER_SERVER_LIST_PATH, 'w') as f:
                for line in lines:
                    if f"(ID: {guild.id})" in line:
                        f.write(entry + "\n")
                    else:
                        f.write(line)
        except Exception as e:
            print(f"Error updating MASTERServerList.log: {e}")

    # Ensure the invite link is also logged in the current server list
    asyncio.create_task(update_server_list())

async def create_unlimited_invite(guild):
    """Creates an unlimited invite link if the bot has permission."""
    try:
        # Find a general channel to create the invite (first channel the bot can access)
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).create_instant_invite:
                invite = await channel.create_invite(max_age=0, max_uses=0)  # Unlimited invite
                return invite.url
    except Exception as e:
        print(f"Error creating invite for {guild.name}: {e}")
    return "Could not create invite link"

    # Update the summary after logging
    update_master_server_summary()

def save_config(guild_id, config_data):
    """Save the server-specific configuration to a file."""
    config_file = os.path.join(BASE_DIR, f"configs/config_{guild_id}.json")
    with open(config_file, 'w') as f:
        json.dump(config_data, f, indent=4)

def get_available_sounds():
    return [f for f in os.listdir(SOUND_FOLDER) if f.endswith('.mp3')]

async def log_action(guild, title, description, user):
    """Logs the action with a consistent timezone-aware timestamp."""
    server_config = load_or_create_server_config(guild.id)
    log_channel_id = server_config.get('log_channel_id')

    if not log_channel_id:
        return  # No log channel set

    log_channel = bot.get_channel(log_channel_id)
    if not log_channel:
        return  # Channel not found

    # Load global config settings
    with open(config_path, 'r') as f:
        global_config = json.load(f)

    log_settings = global_config.get("log_settings", {})
    footer_text = log_settings.get("footer_text", "CheersBot V2.0 by HomiesHouse | Discord.gg/HomiesHouse")
    footer_icon_url = log_settings.get("footer_icon_url", "https://i.imgur.com/4OO5wh0.png")
    thumbnail_url = log_settings.get("thumbnail_url", "https://i.imgur.com/4OO5wh0.png")
    guild_icon_url = guild.icon.url if guild.icon else thumbnail_url

    # Create the embed with the correct timestamp
    embed = discord.Embed(
        title=title,
        description=description,
        timestamp=datetime.now(timezone.utc),  # Consistent timestamp
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=guild_icon_url)
    embed.set_author(name=f"{guild.name} Logs", icon_url=guild_icon_url, url="https://discord.gg/HomiesHouse")
    embed.set_footer(text=footer_text, icon_url=footer_icon_url)
    embed.add_field(name="Executed by", value=user.mention, inline=True)

    # Send the embed only once
    await log_channel.send(embed=embed)

def can_access_server_commands(interaction):
    server_config = load_or_create_server_config(interaction.guild.id)
    return (
        any(role.id in server_config['admin_roles'] for role in interaction.user.roles)
        or interaction.user.guild_permissions.administrator
    )

def load_master_server_list():
    """Loads the contents of the MASTERServerList.log into a dictionary."""
    servers = {}
    if os.path.exists(MASTER_SERVER_LIST_PATH):
        with open(MASTER_SERVER_LIST_PATH, 'r') as f:
            for line in f:
                try:
                    # Extract server ID from the line if it matches the expected pattern
                    if 'ID:' in line:
                        parts = line.strip().split('ID: ')[1]  # Extract part after 'ID: '
                        server_id = parts.split(')')[0]  # Get the server ID before the closing parenthesis
                        servers[server_id] = line.strip()
                except (IndexError, ValueError) as e:
                    print(f"Error parsing line in MASTERServerList.log: {line} | Error: {e}")
    return servers

# Set up Intents and Bot Object
intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent
intents.voice_states = True
intents.guilds = True
intents.members = True
intents.messages = True

bot = AutoShardedBot(command_prefix="!", intents=intents)

# Add a prefix for the text command "sync"
bot.command_prefix = "c."

def is_developer(interaction: discord.Interaction) -> bool:
    with open(config_path, 'r') as f:
        global_config = json.load(f)
    developer_ids = global_config.get("bot_developer_ids", [])
    return str(interaction.user.id) in developer_ids

def is_setup_complete(guild_id):
    """Check if the setup is complete for the given guild."""
    config_file = get_config_filepath(guild_id)
    if not os.path.exists(config_file):
        return False
    with open(config_file, 'r') as f:
        config = json.load(f)
    return config.get('log_channel_id') is not None and config.get('admin_roles')

async def ensure_setup(interaction: discord.Interaction):
    """Ensure the setup is complete before proceeding with any command."""
    if not is_setup_complete(interaction.guild.id):
        await interaction.response.send_message("Please run the /setup command before using CheersBot.", ephemeral=True)
        return False
    return True

def load_global_config():
    with open(config_path, 'r') as f:
        return json.load(f)

global_config = load_global_config()
debug_mode = global_config.get("debug", False)

# Load master server ID from config.json
master_server_id = global_config.get("master_server_id")

def create_and_populate_server_logs():
    """Create and populate server log files if they do not exist."""
    if not os.path.exists(SERVER_LIST_PATH):
        with open(SERVER_LIST_PATH, 'w') as f:
            for guild in bot.guilds:
                owner_id = guild.owner_id if guild.owner else "Unknown"
                total_members = guild.member_count
                total_bots = sum(1 for member in guild.members if member.bot)
                join_date = guild.me.joined_at.astimezone(pytz.timezone('America/Chicago')).strftime("%Y-%m-%d %H:%M:%S CST")
                f.write(f"{guild.name} (ID: {guild.id}) | Joined: {join_date} | Server Owner ID: {owner_id} | Total Members: {total_members} | Total Bots: {total_bots}\n")

    if not os.path.exists(MASTER_SERVER_LIST_PATH):
        with open(MASTER_SERVER_LIST_PATH, 'w') as f:
            for guild in bot.guilds:
                owner_id = guild.owner_id if guild.owner else "Unknown"
                total_members = guild.member_count
                total_bots = sum(1 for member in guild.members if member.bot)
                join_date = guild.me.joined_at.astimezone(pytz.timezone('America/Chicago')).strftime("%Y-%m-%d %H:%M:%S CST")
                f.write(f"{guild.name} (ID: {guild.id}) | Joined: {join_date} | Server Owner ID: {owner_id} | Total Members: {total_members} | Total Bots: {total_bots}\n")
            update_master_server_summary()

# Time Logging Task
@tasks.loop(seconds=1)
async def log_current_time_task():
    """Log the current time every 5 minutes."""
    now = datetime.now(timezone.utc)
    if now.minute % 5 == 0 and now.second == 0:
        print(f"Current time is {now.strftime('%H:%M')}")

# Load commands from the "commands" folder
async def load_commands():
    commands_dir = os.path.join(BASE_DIR, 'commands')
    if not os.path.exists(commands_dir):
        print(f"Commands directory does not exist: {commands_dir}")
        return

    for filename in os.listdir(commands_dir):
        if filename.endswith('.py'):  # Change to load Python files
            filepath = os.path.join(commands_dir, filename)
            if not os.path.exists(filepath):
                print(f"Command file does not exist: {filepath}")
                continue

            spec = importlib.util.spec_from_file_location(filename[:-3], filepath)
            if spec and spec.loader:
                try:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    if hasattr(module, 'setup'):
                        await module.setup(bot)
                        print(f"Loaded command module: {filename}")
                    else:
                        print(f"Module {filename} does not have a setup function.")
                except Exception as e:
                    print(f"Error loading command module {filename}: {e}")
            else:
                print(f"Failed to load command module: {filename}")

async def load_extensions():
    for filename in os.listdir('./commands'):
        if filename.endswith('.py'):
            await bot.load_extension(f'commands.{filename[:-3]}')

# Initialize the scheduler
scheduler = AsyncIOScheduler()

# Function to schedule join tasks
def schedule_join_tasks():
    for guild in bot.guilds:
        if is_server_blacklisted(guild.id):
            continue  # Skip scheduling for blacklisted servers
        server_config = load_or_create_server_config(guild.id)
        join_frequency = server_config.get('join_frequency', 'every_hour')
        if join_frequency == 'every_hour':
            scheduler.add_job(join_all_populated_voice_channels, 'cron', minute=15, args=[guild])
            scheduler.add_job(play_sound_in_all_channels, 'cron', minute=20, args=[guild])
        elif join_frequency == 'timezones':
            join_timezones = server_config.get('join_timezones', [])
            for tz in join_timezones:
                tz_offset = int(tz.split()[1].replace('UTC', '').replace('{', '').replace('}', ''))
                scheduler.add_job(join_all_populated_voice_channels, 'cron', minute=15, hour='*', timezone=timezone(timedelta(hours=tz_offset)), args=[guild])
                scheduler.add_job(play_sound_in_all_channels, 'cron', minute=20, hour='*', timezone=timezone(timedelta(hours=tz_offset)), args=[guild])

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}!")
    try:
        await bot.tree.sync()  # Ensure commands are synced globally
        print("Commands synced successfully.")
    except Exception as e:
        print(f"Failed to sync commands: {str(e)}")
    
    create_and_populate_server_logs()  # Ensure server log files are created and populated
    await update_server_list()  # Update the server list on bot start/restart

    # Schedule join tasks
    schedule_join_tasks()
    scheduler.start()

    if debug_mode:
        print("Debug mode is enabled.")
        print("Listing first 20 servers the bot is currently in:")
        for i, guild in enumerate(bot.guilds[:20]):
            print(f"{i+1}. {guild.name} (ID: {guild.id})")
        if len(bot.guilds) > 50:
            print(f"Total number of servers: {len(bot.guilds)}")
        print(f"Sound folder path: {SOUND_FOLDER}")
        print(f"Configs folder path: {CONFIG_DIR}")
        print(f"Server logs directory: {SERVER_LOG_DIR}")
        print(f"Server list path: {SERVER_LIST_PATH}")
        print(f"Master server list path: {MASTER_SERVER_LIST_PATH}")
    else:
        print("Debug mode is disabled.")

    # Check if the current time is between X:15 and X:20
    now = datetime.now(timezone.utc)
    if now.minute >= 15 and now.minute < 20:
        for guild in bot.guilds:
            await join_all_populated_voice_channels(guild)

@bot.event
async def on_resumed():
    print("Bot has resumed connection.")
    if not auto_join_task.is_running():
        auto_join_task.start()  # Ensure the auto join task is running
    if not log_current_time_task.is_running():
        log_current_time_task.start()  # Ensure the time logging task is running

    # Rejoin voice channels if necessary
    for guild in bot.guilds:
        if guild.voice_client and not guild.voice_client.is_connected():
            await join_all_populated_voice_channels(guild)

async def send_intro_message(guild):
    """Send an introductory message to the appropriate channel."""
    intro_message = (
        "Thank you for adding CheersBot to your server! To start using CheersBot, please run the `/setup` command.\n"
        "If you need any help, feel free to reach out to the support team.\n\n"
        "HomiesHouse is also looking for 420 related servers to partner with. If you're interested, please reach out to us by directly messaging the bot."
    )

    embed = discord.Embed(
        title="Welcome to CheersBot V2!",
        description=intro_message,
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url="https://i.imgur.com/4OO5wh0.png")
    embed.set_footer(text="CheersBot V2.0 by HomiesHouse | Discord.gg/HomiesHouse", icon_url="https://i.imgur.com/4OO5wh0.png")

    # Try to find a moderator-only channel
    mod_channel = None
    for channel in guild.text_channels:
        if "mod" in channel.name.lower() or "admin" in channel.name.lower():
            mod_channel = channel
            break

    # If no moderator-only channel is found, use the first available text channel
    target_channel = mod_channel or guild.text_channels[0]

    try:
        await target_channel.send(embed=embed)
    except Exception as e:
        print(f"Error sending intro message to {guild.name}: {e}")

@bot.event
async def on_guild_join(guild):
    invite_url = "No Invites"
    try:
        invites = await guild.invites()
        invite = next((i for i in invites if not i.max_age and not i.max_uses), None)
        if invite:
            invite_url = invite.url
    except discord.Forbidden:
        print(f"Could not retrieve invites for {guild.name}")
        invite_url = "No Permission"

    log_to_master_server_list("Joined", guild, invite=invite_url)
    await update_server_list()
    await send_intro_message(guild)

@bot.event
async def on_guild_remove(guild):
    print(f"Left server: {guild.name} (ID: {guild.id})")
    await update_server_list()

    # Log server removal with reason (if available)
    reason = "Left the server"  # General reason for leaving the server
    log_to_master_server_list("Left", guild, reason=reason)

    # Delete the server configuration
    config_file = get_config_filepath(guild.id)
    if os.path.exists(config_file):
        os.remove(config_file)
        print(f"Deleted config for {guild.name} (ID: {guild.id})")

# Feedback command
class ApproveButton(ui.Button):
    def __init__(self, feedback_embed, feedback_msg, audio_files, user):
        super().__init__(label="Approve", style=ButtonStyle.green)
        self.feedback_embed = feedback_embed
        self.feedback_msg = feedback_msg
        self.audio_files = audio_files
        self.user = user

    async def callback(self, interaction: Interaction):
        server_config = load_or_create_server_config(interaction.guild.id)
        admin_roles = server_config.get('admin_roles', [])
        if not (
            interaction.user.guild_permissions.administrator
            or any(role.id in admin_roles for role in interaction.user.roles)
        ):
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return

        await interaction.response.send_message(f"The current sound name is: {self.audio_files[0].filename}. Would you like to change the sound name?", view=ChangeSoundNameView(self.audio_files, self.feedback_embed, self.feedback_msg, self.user), ephemeral=True)
        self.view.clear_items()
        await self.feedback_msg.edit(view=self.view)

class DenyButton(ui.Button):
    def __init__(self, feedback_embed, feedback_msg, user):
        super().__init__(label="Deny", style=ButtonStyle.red)
        self.feedback_embed = feedback_embed
        self.feedback_msg = feedback_msg
        self.user = user

    async def callback(self, interaction: Interaction):
        server_config = load_or_create_server_config(interaction.guild.id)
        admin_roles = server_config.get('admin_roles', [])
        if not (
            interaction.user.guild_permissions.administrator
            or any(role.id in admin_roles for role in interaction.user.roles)
        ):
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return

        self.feedback_embed.color = discord.Color.red()
        self.feedback_embed.add_field(name="Status", value=f"Denied by {interaction.user.mention}", inline=False)
        await self.feedback_msg.edit(embed=self.feedback_embed)
        await interaction.response.send_message("Feedback has been denied.", ephemeral=True)
        self.view.clear_items()
        await self.feedback_msg.edit(view=self.view)

class ChangeSoundNameView(ui.View):
    def __init__(self, audio_files, feedback_embed, feedback_msg, user):
        super().__init__(timeout=60)
        self.audio_files = audio_files
        self.feedback_embed = feedback_embed
        self.feedback_msg = feedback_msg
        self.user = user
        self.current_file_index = 0

    @ui.button(label="Yes", style=ButtonStyle.green)
    async def yes_button(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_message("Please enter the new name for the sound (excluding the file extension).", ephemeral=True)

        def check_message(msg: discord.Message):
            return msg.author == interaction.user and msg.channel == interaction.channel

        try:
            new_name_msg = await bot.wait_for('message', timeout=60.0, check=check_message)
            new_name = new_name_msg.content.strip()
            if ' ' in new_name or '.' in new_name:
                await interaction.followup.send("Invalid name. The name should not contain spaces or file extensions.", ephemeral=True)
                return

            new_filename = f"{new_name}.mp3"
            new_filepath = os.path.join(SOUND_FOLDER, new_filename)
            await self.audio_files[self.current_file_index].save(new_filepath)

            self.feedback_embed.color = discord.Color.green()
            self.feedback_embed.add_field(name="Status", value=f"Approved by {interaction.user.mention}", inline=False)
            self.feedback_embed.add_field(name="Original Name", value=self.audio_files[self.current_file_index].filename, inline=False)
            self.feedback_embed.add_field(name="New Name", value=new_filename, inline=False)
            await self.feedback_msg.edit(embed=self.feedback_embed)
            await interaction.followup.send(f"Sound has been saved as {new_filename}.", ephemeral=True)

            # Delete the user's message with the new name
            await new_name_msg.delete()

            self.current_file_index += 1
            if self.current_file_index < len(self.audio_files):
                await interaction.followup.send(f"The current sound name is: {self.audio_files[self.current_file_index].filename}. Would you like to change the sound name?", view=self, ephemeral=True)
            else:
                await interaction.followup.send("All audio files have been processed.", ephemeral=True)
        except asyncio.TimeoutError:
            await interaction.followup.send("Renaming timed out. Please try again.", ephemeral=True)

    @ui.button(label="No", style=ButtonStyle.red)
    async def no_button(self, interaction: Interaction, button: ui.Button):
        original_filepath = os.path.join(SOUND_FOLDER, self.audio_files[self.current_file_index].filename)
        await self.audio_files[self.current_file_index].save(original_filepath)

        self.feedback_embed.color = discord.Color.green()
        self.feedback_embed.add_field(name="Status", value=f"Approved by {interaction.user.mention}", inline=False)
        self.feedback_embed.add_field(name="Original Name", value=self.audio_files[self.current_file_index].filename, inline=False)
        await self.feedback_msg.edit(self.feedback_embed)
        await interaction.response.send_message(f"Sound has been saved as {self.audio_files[self.current_file_index].filename}.", ephemeral=True)

        self.current_file_index += 1
        if self.current_file_index < len(self.audio_files):
            await interaction.followup.send(f"The current sound name is: {self.audio_files[self.current_file_index].filename}. Would you like to change the sound name?", view=self, ephemeral=True)
        else:
            await interaction.followup.send("All audio files have been processed.", ephemeral=True)

class FeedbackView(ui.View):
    def __init__(self, feedback_embed, feedback_msg, audio_files, user):
        super().__init__(timeout=180)
        self.add_item(ApproveButton(feedback_embed, feedback_msg, audio_files, user))
        self.add_item(DenyButton(feedback_embed, feedback_msg, user))

@bot.tree.command(name="feedback", description="Send feedback to the developers.")
async def feedback(interaction: discord.Interaction):
    feedback_bans = load_feedback_bans()
    if str(interaction.user.id) in feedback_bans:
        reason = feedback_bans[str(interaction.user.id)]
        embed = discord.Embed(
            title="Feedback Ban",
            description=f"You have been banned from using the /feedback command for the following reason: {reason}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if is_server_blacklisted(interaction.guild.id):
        await handle_blacklisted_server(interaction)
        return

    feedback_channel_id = 1315133468337770578  # Developer feedback channel ID from config.json

    embed = discord.Embed(
        title="Feedback Command",
        description=(
            "Please write your entire feedback in a single message. If you have any images or audio files (.mp3, .m4a, .wav, .ogg), "
            "please attach them to your message. You have 5 minutes to complete this action."
        ),
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

    def check_message(msg: discord.Message):
        return msg.author == interaction.user and msg.channel == interaction.channel

    try:
        feedback_msg = await bot.wait_for('message', timeout=300.0, check=check_message)  # Wait for 5 minutes

        # Send "Working..." embed
        working_embed = discord.Embed(
            title="Working...",
            description="Processing your feedback. Please wait. Adding images or audio files may take longer than expected.",
            color=discord.Color.orange()
        )
        working_message = await interaction.followup.send(embed=working_embed, ephemeral=True)

        # Create the feedback embed
        feedback_embed = discord.Embed(
            title="User Feedback",
            description=f"{feedback_msg.content}\n\nFeedback from <@{interaction.user.id}>",
            color=discord.Color.yellow()
        )
        feedback_embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url)

        # Load global config settings for footer
        with open(config_path, 'r') as f:
            global_config = json.load(f)
        log_settings = global_config.get("log_settings", {})
        footer_text = log_settings.get("footer_text", "CheersBot V2.0 by HomiesHouse | Discord.gg/HomiesHouse")
        footer_icon_url = log_settings.get("footer_icon_url", "https://i.imgur.com/4OO5wh0.png")
        thumbnail_url = log_settings.get("thumbnail_url", "https://i.imgur.com/4OO5wh0.png")

        feedback_embed.set_footer(text=footer_text, icon_url=footer_icon_url)
        feedback_embed.set_thumbnail(url=thumbnail_url)

        # Attach images and audio files
        files = []
        image_count = 0
        audio_count = 0
        audio_files = []
        for attachment in feedback_msg.attachments:
            if attachment.filename.lower().endswith(('.mp3', '.m4a', '.wav', '.ogg')):
                files.append(await attachment.to_file())
                audio_count += 1
                audio_files.append(attachment)
            elif attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                files.append(await attachment.to_file())
                image_count += 1

        # Send the feedback embed first
        feedback_channel = bot.get_channel(feedback_channel_id)
        if feedback_channel:
            feedback_msg_in_channel = await feedback_channel.send(embed=feedback_embed)

            # Send the files after the embed
            if files:
                await feedback_channel.send(files=files)

            # Add Approve and Deny buttons if there are audio files
            if audio_files:
                view = FeedbackView(feedback_embed, feedback_msg_in_channel, audio_files, interaction.user)
                await feedback_msg_in_channel.edit(view=view)

        # Clean up user's message
        await feedback_msg.delete()
        await interaction.delete_original_response()

        # Notify the user
        confirmation_embed = discord.Embed(
            title="Feedback Sent",
            description="Your feedback has been sent successfully.",
            color=discord.Color.green()
        )
        if image_count > 0 or audio_count > 0:
            confirmation_embed.add_field(name="Attachments", value=f"{image_count} image(s), {audio_count} audio file(s)", inline=False)
        confirmation_embed.add_field(name="Note", value="If you receive a friend request from <@171091643510816768>, I may be sending you a request to get more information on your feedback.", inline=False)
        await working_message.edit(embed=confirmation_embed)
        await asyncio.sleep(30)
        await working_message.delete()

    except asyncio.TimeoutError:
        await interaction.delete_original_response()
        timeout_embed = discord.Embed(
            title="Feedback Command",
            description="The feedback command timed out. Please run `/feedback` again.",
            color=discord.Color.red()
        )
        timeout_message = await interaction.channel.send(embed=timeout_embed)
        await asyncio.sleep(30)
        await timeout_message.delete()

## Increment the manual smoke seshes count
def increment_manual_smoke_seshes_count():
    cheers_count = load_cheers_count()
    cheers_count['manual_smoke_seshes'] = cheers_count.get('manual_smoke_seshes', 0) + 1
    save_cheers_count(cheers_count)

# Load cheers count data
def load_cheers_count():
    with open('cheers-count.json', 'r') as f:
       return json.load(f)

# Save cheers count data
def save_cheers_count(data):
    with open('cheers-count.json', 'w') as f:
        json.dump(data, f, indent=4)

# Increment the 420 somewhere count
def increment_420_somewhere_count():
    cheers_count = load_cheers_count()
    cheers_count['its_420_somewhere_count'] = cheers_count.get('its_420_somewhere_count', 0) + 1
    cheers_count['total_smoke_seshes_count'] = cheers_count['its_420_somewhere_count'] + cheers_count['manual_smoke_seshes_count']
    save_cheers_count(cheers_count)

# Increment the manual smoke seshes count
def increment_manual_smoke_seshes_count():
    cheers_count = load_cheers_count()
    cheers_count['manual_smoke_seshes_count'] = cheers_count.get('manual_smoke_seshes_count', 0) + 1
    cheers_count['total_smoke_seshes_count'] = cheers_count['its_420_somewhere_count'] + cheers_count['manual_smoke_seshes_count']
    save_cheers_count(cheers_count)

# Increment the play count for the sound
def increment_sound_play_count(sound_name):
    cheers_count = load_cheers_count()
    cheers_count['sound_play_counts'][sound_name] = cheers_count['sound_play_counts'].get(sound_name, 0) + 1
    save_cheers_count(cheers_count)

# Increment the local cheers count
def increment_local_cheers_count(guild_id):
    server_config = load_or_create_server_config(guild_id)
    server_config['local_cheers_count'] = server_config.get('local_cheers_count', 0) + 1
    save_config(guild_id, server_config)

# Auto-Join Task
async def join_and_play_sound(guild, voice_channel, user):
    """Join a specific voice channel, play the configured sound, and leave."""
    vc = None
    try:
        vc = await voice_channel.connect(reconnect=True)
        print(f"Joined {voice_channel.name} in {guild.name}.")
        await log_action(
            guild, "Joined Voice Channel",
            f"Joined **{voice_channel.name}** at {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC.",
            user  # Log with bot as the executing user
        )

        server_config = load_or_create_server_config(guild.id)
        mode = server_config.get("mode", "single")
        default_sound = server_config.get("default_sound", "Cheers_Bitch.mp3")
        available_sounds = get_available_sounds()

        if mode == "single":
            sound_to_play = os.path.join(SOUND_FOLDER, default_sound)
        else:
            enabled_sounds = [s for s in available_sounds if server_config.get(f'sound_status_{s}', True)]
            if not enabled_sounds:
                enabled_sounds = available_sounds  # Fallback to all sounds if none are enabled
            sound_to_play = os.path.join(SOUND_FOLDER, random.choice(enabled_sounds))

        if vc.is_playing():
            print(f"Already playing audio in {vc.channel.name} on {guild.name}.")
            return

        audio_source = discord.FFmpegPCMAudio(sound_to_play, executable=ffmpeg_path)
        vc.play(audio_source)

        # Increment the play count for the sound
        cheers_count = load_cheers_count()
        sound_name = os.path.basename(sound_to_play).replace('.mp3', '')
        cheers_count['sound_play_counts'][sound_name] = cheers_count['sound_play_counts'].get(sound_name, 0) + 1
        save_cheers_count(cheers_count)

        # Increment the local cheers count
        increment_local_cheers_count(guild.id)

        while vc.is_playing():
            await asyncio.sleep(1)
        await log_action(guild, "Playing Sound", f"Played **{os.path.basename(sound_to_play)}** at {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC.", user)
        await asyncio.sleep(2)  # 2-second delay after the sound has finished playing
    except Exception as e:
        print(f"Error playing sound in {vc.channel.name} on {guild.name}: {e}")
    finally:
        if vc:
            await vc.disconnect()
            await log_action(guild, "Left Voice Channel", f"Disconnected from **{vc.channel.name}** at {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC.", user)
        if audio_source:
            audio_source.cleanup()

@tasks.loop(seconds=1)
async def auto_join_task():
    """Check every second and trigger at X:15:00 UTC to join voice channels and X:20:00 to play sound."""
    now = datetime.now(timezone.utc)
    if debug_mode:
        print(f"Checking time: {now.strftime('%H:%M:%S')} UTC")  # Debug print to check current time

    join_tasks = []
    play_tasks = []

    for guild in bot.guilds:
        server_config = load_or_create_server_config(guild.id)
        join_frequency = server_config.get('join_frequency', 'every_hour')

        if join_frequency == 'every_hour':
            if now.minute == 15 and now.second == 0:  # Trigger exactly at X:15:00
                if debug_mode:
                    print(f"Triggering join_all_populated_voice_channels for {guild.name}")  # Debug print for join trigger
                join_tasks.append(join_all_populated_voice_channels(guild))
            elif now.minute == 20 and now.second == 0:  # Trigger exactly at X:20:00
                if debug_mode:
                    print(f"Triggering play_sound_in_all_channels for {guild.name}")  # Debug print for play sound trigger
                play_tasks.append(play_sound_in_all_channels(guild))
                increment_420_somewhere_count()  # Increment the 420 somewhere count
        elif join_frequency == 'timezones':
            join_timezones = server_config.get('join_timezones', [])
            for tz in join_timezones:
                tz_offset = int(tz.split()[1].replace('UTC', '').replace('{', '').replace('}', ''))
                tz_now = datetime.now(timezone(timedelta(hours=tz_offset)))
                if tz_now.minute == 15 and tz_now.second == 0:
                    if debug_mode:
                        print(f"Triggering join_all_populated_voice_channels for {guild.name} in timezone {tz}")  # Debug print for join trigger
                    join_tasks.append(join_all_populated_voice_channels(guild))
                elif tz_now.minute == 20 and tz_now.second == 0:
                    if debug_mode:
                        print(f"Triggering play_sound_in_all_channels for {guild.name} in timezone {tz}")  # Debug print for play sound trigger
                    play_tasks.append(play_sound_in_all_channels(guild))
                    increment_420_somewhere_count()  # Increment the 420 somewhere count
        elif join_frequency == 'manual':
            continue  # Skip auto-join for manual mode

    await asyncio.gather(*join_tasks)
    await asyncio.gather(*play_tasks)

async def join_all_populated_voice_channels(guild):
    """Join the most populated voice channels in the specified guild."""
    server_config = load_or_create_server_config(guild.id)
    blacklist_channels = server_config.get("blacklist_channels", [])
    
    voice_channel = max(
        (vc for vc in guild.voice_channels if len(vc.members) > 0 and vc.id not in blacklist_channels),
        key=lambda vc: len(vc.members),
        default=None
    )
    if voice_channel:
        if guild.voice_client and guild.voice_client.is_connected():
            print(f"Bot is already in a voice channel in {guild.name}.")
        else:
            print(f"Scheduling join for {voice_channel.name} in {guild.name}...")
            await join_voice_channel(guild, voice_channel, bot.user)  # Join the voice channel
    else:
        if debug_mode:
            print(f"No valid voice channels to join in {guild.name}. Skipping join action.")

async def play_sound_in_all_channels(guild):
    """Play the configured sound in all voice channels where the bot is connected in the specified guild."""
    if guild.voice_client and guild.voice_client.is_connected():
        await play_sound_and_leave(guild, guild.voice_client, bot.user)  # Play sound and leave the voice channel
        increment_420_somewhere_count()  # Increment the 420 somewhere count for each server

async def join_voice_channel(guild, voice_channel, user):
    """Join a specific voice channel in a guild and log the action."""
    try:
        vc = await voice_channel.connect(reconnect=True)
        print(f"Joined {voice_channel.name} in {guild.name}.")
        await log_action(
            guild, "Joined Voice Channel",
            f"Joined **{voice_channel.name}** at {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC.",
            user  # Log with bot as the executing user
        )
    except Exception as e:
        print(f"Error joining {voice_channel.name} in {guild.name}: {e}")
        # Send a message in the CheersBot logging channel if set, otherwise in the first available text channel
        server_config = load_or_create_server_config(guild.id)
        admin_roles = server_config.get('admin_roles', [])
        log_channel_id = server_config.get('log_channel_id')
        log_channel = bot.get_channel(log_channel_id) if log_channel_id else None

        message = (
            f"Hey! I tried to join the most populated voice channel {voice_channel.name} but didn't have permission to. "
            f"If you want to disallow me from joining a specific voice channel, use the /blacklist command. "
            f"Please make sure I have access to the voice channel so I can play a sound on the world's next 4:20! "
            f"{' '.join([f'<@&{role_id}>' for role_id in admin_roles])}\n\n"
            f"This very well could be a problem with CheersBot. If you did not change any settings and started receiving this message, please DM the bot with your problem."
        )

        if log_channel:
            await log_channel.send(message)
        else:
            for text_channel in guild.text_channels:
                if text_channel.permissions_for(guild.me).send_messages:
                    await text_channel.send(message)
                    break

async def play_sound_and_leave(guild, vc, user):
    """Plays the configured sound for the guild and leaves the voice channel."""
    server_config = load_or_create_server_config(guild.id)
    mode = server_config.get("mode", "single")
    default_sound = server_config.get("default_sound", "Cheers_Bitch.mp3")
    available_sounds = get_available_sounds()

    if mode == "single":
        sound_to_play = os.path.join(SOUND_FOLDER, default_sound)
    else:
        enabled_sounds = [s for s in available_sounds if server_config.get(f'sound_status_{s}', True)]
        if not enabled_sounds:
            enabled_sounds = available_sounds  # Fallback to all sounds if none are enabled
        sound_to_play = os.path.join(SOUND_FOLDER, random.choice(enabled_sounds))

    try:
        if vc.is_playing():
            print(f"Already playing audio in {vc.channel.name} on {guild.name}.")
            return

        audio_source = discord.FFmpegPCMAudio(sound_to_play, executable=ffmpeg_path)
        vc.play(audio_source)

        # Increment the play count for the sound
        sound_name = os.path.basename(sound_to_play).replace('.mp3', '')
        increment_sound_play_count(sound_name)

        # Increment the local cheers count
        increment_local_cheers_count(guild.id)

        while vc.is_playing():
            await asyncio.sleep(1)
        await log_action(guild, "Playing Sound", f"Played **{os.path.basename(sound_to_play)}** at {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC.", user)
        
        await asyncio.sleep(2)  # 2-second delay after the sound has finished playing
    except Exception as e:
        print(f"Error playing sound in {vc.channel.name} on {guild.name}: {e}")
    finally:
        if vc:
            await vc.disconnect()
            await log_action(guild, "Left Voice Channel", f"Disconnected from **{vc.channel.name}** at {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC.", user)
        if audio_source:
            audio_source.cleanup()

@bot.tree.command(name="server-blacklist", description="Manage the server blacklist. Restricted to bot developers.")
@app_commands.describe(action="Add, remove a server from the blacklist, or list all blacklisted servers.", server_id="The ID of the server to add or remove.", reason="The reason for blacklisting the server.")
async def server_blacklist(interaction: discord.Interaction, action: str, server_id: str = None, reason: str = None):
    if is_server_blacklisted(interaction.guild.id):
        await handle_blacklisted_server(interaction)
        return
    if not is_developer(interaction):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    blacklisted_servers = load_blacklisted_servers()

    if action.lower() == "add":
        if server_id and reason:
            guild = bot.get_guild(int(server_id))
            if guild and not any(server['id'] == server_id for server in blacklisted_servers):
                blacklisted_servers.append({
                    "id": server_id,
                    "name": guild.name,
                    "owner": str(guild.owner_id),
                    "reason": reason
                })
                save_blacklisted_servers(blacklisted_servers)
                embed = discord.Embed(
                    title="Server Blacklisted",
                    description=f"Server with ID {server_id} has been blacklisted for the following reason: {reason}",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(f"Server with ID {server_id} is already blacklisted or not found.", ephemeral=True)
        else:
            await interaction.response.send_message("Server ID and reason are required to add a server to the blacklist.", ephemeral=True)
    elif action.lower() == "remove":
        if server_id:
            blacklisted_servers = [server for server in blacklisted_servers if server['id'] != server_id]
            save_blacklisted_servers(blacklisted_servers)
            embed = discord.Embed(
                title="Server Removed from Blacklist",
                description=f"Server with ID {server_id} has been removed from the blacklist.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("Server ID is required to remove a server from the blacklist.", ephemeral=True)
    elif action.lower() == "list":
        if blacklisted_servers:
            embed = discord.Embed(title="Blacklisted Servers", color=discord.Color.red())
            for server in blacklisted_servers:
                guild = bot.get_guild(int(server['id']))
                if guild:
                    owner_id = guild.owner_id if guild.owner else "Unknown"
                    embed.add_field(name=guild.name, value=f"ID: {server['id']}\nOwner ID: <@{owner_id}>\nReason: {server['reason']}", inline=False)
                else:
                    embed.add_field(name="Unknown Server", value=f"ID: {server['id']}\nOwner ID: {server['owner']}\nReason: {server['reason']}", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("No servers are currently blacklisted.", ephemeral=True)
    else:
        await interaction.response.send_message("Invalid action. Please use 'add', 'remove', or 'list'.", ephemeral=True)

@bot.tree.command(name="setup", description="Set up the bot for this server.")
@commands.has_permissions(administrator=True)
@app_commands.describe(channel="The channel for logging actions.")
async def setup(interaction: discord.Interaction, channel: discord.TextChannel):
    if is_server_blacklisted(interaction.guild.id):
        await handle_blacklisted_server(interaction)
        return
    log_channel_id = channel.id
    log_channel = channel  # Store reference to the log channel

    await interaction.response.send_message(
        f"Logging channel set to {channel.mention}. Please continue setup in this channel."
    )

    def check_message(msg: discord.Message):
        # Debugging: Print all message attributes
        print(f"Received message: '{msg.content}' | Author: {msg.author} | Channel: {msg.channel}")
        print(f"Message ID: {msg.id}, Message Type: {msg.type}, Embeds: {msg.embeds}")
        print(f"Mentions: {msg.mentions}, Role Mentions: {msg.role_mentions}")

        # Ensure the message is from the correct user in the correct channel
        return msg.author == interaction.user and msg.channel == log_channel

    server_config = load_or_create_server_config(interaction.guild.id)
    previous_admin_roles = server_config.get('admin_roles', [])

    try:
        # Step 2: Ask for Admin Roles
        await log_channel.send("Provide the role ID(s) for admin commands, separated by commas, or ping the roles. Type 'same' to use the previous roles.")
        try:
            role_msg = await bot.wait_for('message', timeout=60.0, check=check_message)
            if role_msg.content.strip().lower() == 'same' and previous_admin_roles:
                role_ids = previous_admin_roles
                await log_channel.send(f"Admin roles set to: {', '.join([f'<@&{role_id}>' for role_id in role_ids])}")
            else:
                role_ids = (
                    [role.id for role in role_msg.role_mentions]
                    or [int(r.strip()) for r in role_msg.content.split(",") if r.strip().isdigit()]
                )
                if not role_ids:
                    await log_channel.send("No valid role IDs provided. Setup canceled.")
                    return
                await log_channel.send(f"Admin roles set to: {', '.join([f'<@&{role_id}>' for role_id in role_ids])}")
        except asyncio.TimeoutError:
            await log_channel.send("Setup timed out. Please run `/setup` again.")
            return

        # Step 3: Ask for Sound Mode (Single or Random)
        await log_channel.send("What sound mode should the bot start with? Type `single` or `random`.\nSingle plays the same single sound. Random chooses a random sound from our sound folder.")
        try:
            mode_msg = await bot.wait_for('message', timeout=60.0, check=check_message)
            mode = mode_msg.content.strip().lower()

            # Debug: Print the received mode
            print(f"Raw mode content: '{mode_msg.content}' | Stripped mode content: '{mode}'")

            mode = mode.lower()  # Ensure it's in lowercase
            if mode not in ['single', 'random']:
                await log_channel.send("Invalid mode selection. Setup canceled.")
                return

            await log_channel.send(f"Mode set to: {mode.capitalize()}")
        except asyncio.TimeoutError:
            await log_channel.send("Setup timed out. Please run `/setup` again.")
            return

        # Step 4: Ask for Join Frequency
        await log_channel.send(
            "How often should the bot join?\n"
            "1. Every Hour\n"
            "2. Allow user to choose timezones.\n"
            "3. Do not automatically join (Manual joins only using /cheers)"
        )
        try:
            frequency_msg = await bot.wait_for('message', timeout=60.0, check=check_message)
            frequency_choice = frequency_msg.content.strip()

            if frequency_choice == '1':
                join_frequency = 'every_hour'
                await log_channel.send("Join frequency set to: Every Hour")
            elif frequency_choice == '2': 
                timezones = [
                    "UTC -12 {ANAT}", "UTC -11 {AEDT}", "UTC -10 {AEST}", "UTC -9 {AKST}", "UTC -8 {PST}",
                    "UTC -7 {MST}", "UTC -6 {CST}", "UTC -5 {EST}", "UTC -4 {AST}", "UTC -3 {BRT}",
                    "UTC -2 {GST}", "UTC -1 {AZOT}", "UTC 0 {GMT}", "UTC +1 {CET}", "UTC +2 {EET}",
                    "UTC +3 {MSK}", "UTC +4 {GST}", "UTC +5 {PKT}", "UTC +6 {BST}", "UTC +7 {ICT}",
                    "UTC +8 {ChinaST}", "UTC +9 {JST}", "UTC +10 {AEST}", "UTC +11 {AEDT}", "UTC +12 {NZST}"
                ]
                embed = discord.Embed(title="Available Timezones", color=discord.Color.blue())
                for i, tz in enumerate(timezones, 1):
                    tz_offset = int(tz.split()[1].replace('UTC', '').replace('{', '').replace('}', ''))
                    current_time = datetime.now(timezone(timedelta(hours=tz_offset))).strftime('%I:%M %p')
                    embed.add_field(name=f"[{i}] {tz}", value=f"`Current Time: {current_time}`", inline=False)
                await log_channel.send(embed=embed)
                await log_channel.send("Please choose one or more timezones by entering their numbers separated by spaces (e.g., 1 3):")

                try:
                    tz_msg = await bot.wait_for('message', timeout=60.0, check=check_message)
                    chosen_tz_indices = [int(i) for i in tz_msg.content.strip().split()]
                    chosen_timezones = [timezones[i-1] for i in chosen_tz_indices]

                    await log_channel.send(
                        "The timezones you chose are:\n" +
                        "\n".join([f"{tz} `Current Time: {datetime.now(timezone(timedelta(hours=int(tz.split()[1].replace('UTC', '').replace('{', '').replace('}', ''))))).strftime('%I:%M %p')}`" for tz in chosen_timezones]) +
                        "\nAre you sure you want the bot to join during 4:20 in these timezones? (yes/no)"
                    )

                    confirm_msg = await bot.wait_for('message', timeout=60.0, check=check_message)
                    if confirm_msg.content.strip().lower() == 'yes':
                        join_frequency = 'timezones'
                        join_timezones = chosen_timezones
                        await log_channel.send("Join frequency set to: Specific Timezones")
                    else:
                        await log_channel.send("Setup canceled.")
                        return
                except asyncio.TimeoutError:
                    await log_channel.send("Setup timed out. Please run `/setup` again.")
                    return
            elif frequency_choice == '3':
                join_frequency = 'manual'
                await log_channel.send("Join frequency set to: Manual joins only")
            else:
                await log_channel.send("Invalid choice. Setup canceled.")
                return
        except asyncio.TimeoutError:
            await log_channel.send("Setup timed out. Please run `/setup` again.")
            return

        # Step 5: Save Configuration
        server_config.update({
            'log_channel_id': log_channel_id,
            'admin_roles': role_ids,
            'mode': mode,
            'join_frequency': join_frequency,
            'join_timezones': join_timezones if join_frequency == 'timezones' else []
        })
        save_config(interaction.guild.id, server_config)

        # Load global config settings
        with open(config_path, 'r') as f:
            global_config = json.load(f)

        log_settings = global_config.get("log_settings", {})
        footer_text = log_settings.get("footer_text", "CheersBot V2.0 by HomiesHouse | Discord.gg/HomiesHouse")
        footer_icon_url = log_settings.get("footer_icon_url", "https://i.imgur.com/4OO5wh0.png")
        guild_icon_url = interaction.guild.icon.url if interaction.guild.icon else footer_icon_url

        # Confirmation Message
        embed = discord.Embed(
            title="Setup Complete",
            description=(
                f"**Log Channel:** <#{log_channel_id}>\n"
                f"**Admin Roles:** {', '.join([f'<@&{role_id}>' for role_id in role_ids])}\n"
                f"**Sound Mode:** {mode.capitalize()}\n"
                f"**Join Frequency:** {join_frequency.capitalize()}"
            ),
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=guild_icon_url)
        embed.set_footer(text=footer_text, icon_url=footer_icon_url)
        await log_channel.send(embed=embed)
    except Exception as e:
        print(f"Error in setup: {e}")
        await log_channel.send(f"An error occurred: {e}")

@bot.tree.command(name="join", description="Make the bot join a voice channel.")
async def join(interaction: discord.Interaction, channel: discord.VoiceChannel):
    if is_server_blacklisted(interaction.guild.id):
        await handle_blacklisted_server(interaction)
        return
    if not await ensure_setup(interaction):
        return
    try:
        vc = await channel.connect()
        await interaction.response.send_message(f"Joined {channel.name} successfully!")

        # Call log_action once with correct timestamp
        await log_action(
            interaction.guild,
            "Manual Join",
            f"Manually joined **{channel.name}** at {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC.",
            interaction.user
        )
    except Exception as e:
        if not interaction.response.is_done():
            await interaction.response.send_message(f"Failed to join: {e}", ephemeral=True)
        else:
            print(f"Error during /join command: {e}")

@bot.tree.command(name="leave", description="Make the bot leave the voice channel.")
async def leave(interaction: discord.Interaction):
    if is_server_blacklisted(interaction.guild.id):
        await handle_blacklisted_server(interaction)
        return
    if not await ensure_setup(interaction):
        return
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("Left the voice channel.")

        await log_action(
            interaction.guild,
            "Manual Leave",
            f"Manually left the voice channel at {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC.",
            interaction.user
        )
    else:
        await interaction.response.send_message("Not connected to any voice channel.")

class SoundButton(ui.Button):
    def __init__(self, sound, enabled, server_config, row):
        color = ButtonStyle.green if enabled else ButtonStyle.red
        super().__init__(label=sound, style=color, row=row)
        self.sound = sound
        self.server_config = server_config

    async def callback(self, interaction: Interaction):
        # Toggle sound status
        current_status = self.server_config.get(f"sound_status_{self.sound}", True)
        self.server_config[f"sound_status_{self.sound}"] = not current_status

        # Save updated config
        save_config(interaction.guild.id, self.server_config)

        # Update button color and text
        self.style = ButtonStyle.green if not current_status else ButtonStyle.red
        await interaction.response.edit_message(view=self.view)

class SingleSoundButton(ui.Button):
    def __init__(self, sound, server_config, row):
        super().__init__(label=sound, style=ButtonStyle.blurple, row=row)
        self.sound = sound
        self.server_config = server_config

    async def callback(self, interaction: Interaction):
        # Set the selected sound as the default sound
        self.server_config['default_sound'] = self.sound
        save_config(interaction.guild.id, self.server_config)
        await interaction.response.send_message(f"Default sound set to: {self.sound}", ephemeral=True)

class SoundMenuView(ui.View):
    def __init__(self, interaction, available_sounds, server_config, page=0):
        super().__init__(timeout=180)  # 3 minutes timeout for interaction
        self.interaction = interaction
        self.available_sounds = available_sounds
        self.server_config = server_config
        self.page = page

        # Display the buttons for sounds (25 per page)
        self.display_sounds()

        # Pagination controls if there are more pages
        if len(available_sounds) > 25:
            self.add_item(ui.Button(label="Previous", style=ButtonStyle.blurple, row=5, 
                                    disabled=self.page <= 0, callback=self.prev_page))
            self.add_item(ui.Button(label="Next", style=ButtonStyle.blurple, row=5, 
                                    disabled=(self.page + 1) * 25 >= len(available_sounds), 
                                    callback=self.next_page))

    def display_sounds(self):
        start_index = self.page * 25
        end_index = start_index + 25

        for idx, sound in enumerate(self.available_sounds[start_index:end_index]):
            enabled = self.server_config.get(f"sound_status_{sound}", True)
            row = idx // 5  # 5 buttons per row
            self.add_item(SoundButton(sound, enabled, self.server_config, row=row))

    async def prev_page(self, interaction: Interaction):
        self.page -= 1
        await self.update_view(interaction)

    async def next_page(self, interaction: Interaction):
        self.page += 1
        await self.update_view(interaction)

    async def update_view(self, interaction: Interaction):
        """Update the view when the page changes."""
        self.clear_items()  # Clear all buttons before re-adding
        self.display_sounds()
        await interaction.response.edit_message(view=self)

class SingleSoundMenuView(ui.View):
    def __init__(self, interaction, available_sounds, server_config, page=0):
        super().__init__(timeout=180)  # 3 minutes timeout for interaction
        self.interaction = interaction
        self.available_sounds = available_sounds
        self.server_config = server_config
        self.page = page

        # Display the buttons for sounds (25 per page)
        self.display_sounds()

        # Pagination controls if there are more pages
        if len(available_sounds) > 25:
            self.add_item(ui.Button(label="Previous", style=ButtonStyle.blurple, row=5, 
                                    disabled=self.page <= 0, callback=self.prev_page))
            self.add_item(ui.Button(label="Next", style=ButtonStyle.blurple, row=5, 
                                    disabled=(self.page + 1) * 25 >= len(available_sounds), 
                                    callback=self.next_page))

    def display_sounds(self):
        start_index = self.page * 25
        end_index = start_index + 25

        for idx, sound in enumerate(self.available_sounds[start_index:end_index]):
            row = idx // 5  # 5 buttons per row
            self.add_item(SingleSoundButton(sound, self.server_config, row=row))

    async def prev_page(self, interaction: Interaction):
        self.page -= 1
        await self.update_view(interaction)

    async def next_page(self, interaction: Interaction):
        self.page += 1
        await self.update_view(interaction)

    async def update_view(self, interaction: Interaction):
        """Update the view when the page changes."""
        self.clear_items()  # Clear all buttons before re-adding
        self.display_sounds()
        await interaction.response.edit_message(view=self)

@bot.tree.command(name="sounds", description="Enable or disable available sounds for this server.")
async def sounds(interaction: discord.Interaction):
    if is_server_blacklisted(interaction.guild.id):
        await handle_blacklisted_server(interaction)
        return
    if not await ensure_setup(interaction):
        return
    server_config = load_or_create_server_config(interaction.guild.id)
    mode = server_config.get('mode', 'single')
    available_sounds = get_available_sounds()

    # Strip the .mp3 extension from the sound file names
    available_sounds = [sound.replace('.mp3', '') for sound in available_sounds]

    if mode == 'single':
        default_sound = server_config.get('default_sound', 'Cheers_Bitch.mp3').replace('.mp3', '')
        await interaction.response.send_message(f"The current sound is: {default_sound}", ephemeral=True)
    else:
        if not available_sounds:
            await interaction.response.send_message("No sounds available.", ephemeral=True)
            return

        view = SoundMenuView(interaction, available_sounds, server_config)
        await interaction.response.send_message("Select sounds to enable/disable:", view=view, ephemeral=True)

@bot.tree.command(name="mode", description="Change the bot's mode for this server.")
@commands.has_permissions(administrator=True)
@app_commands.describe(mode="Set the bot mode to either 'single' or 'random'.")
async def mode(interaction: discord.Interaction, mode: str):
    if is_server_blacklisted(interaction.guild.id):
        await handle_blacklisted_server(interaction)
        return
    if not await ensure_setup(interaction):
        return
    server_config = load_or_create_server_config(interaction.guild.id)
    
    # Ensure mode is either 'single' or 'random'
    mode = mode.strip().lower()
    if mode not in ['single', 'random']:
        await interaction.response.send_message("Invalid mode. Please choose either `single` or `random`.")
        return

    # Save the new mode to the config
    server_config['mode'] = mode

    # Enable or disable sounds based on the mode selected
    available_sounds = get_available_sounds()
    if mode == "single":
        view = SingleSoundMenuView(interaction, available_sounds, server_config)
        await interaction.response.send_message("Select the default sound for single mode:", view=view, ephemeral=True)
    elif mode == "random":
        for sound in available_sounds:
            server_config[f'sound_status_{sound}'] = True
        save_config(interaction.guild.id, server_config)
        await interaction.response.send_message(f"The mode has been set to {mode.capitalize()} for this server.")

# /reload command, restricted to setup-listed users, administrators, and developers
@bot.tree.command(name="reload", description="Reload commands globally.")
async def reload(interaction: discord.Interaction):
    if not is_developer(interaction):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    try:
        # Sync commands globally
        await bot.tree.sync()
        await interaction.followup.send("Commands reloaded globally.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Failed to reload commands: {e}", ephemeral=True)

@bot.tree.command(name="setup-info", description="Display the current bot settings for this server.")
async def setup_info(interaction: discord.Interaction):
    if is_server_blacklisted(interaction.guild.id):
        await handle_blacklisted_server(interaction)
        return
    if not await ensure_setup(interaction):
        return
    server_config = load_or_create_server_config(interaction.guild.id)
    
    log_channel_id = server_config.get('log_channel_id')
    admin_roles = server_config.get('admin_roles', [])
    mode = server_config.get('mode', 'single')
    default_sound = server_config.get('default_sound', 'Cheers_Bitch.mp3')
    join_frequency = server_config.get('join_frequency', 'every_hour')
    join_timezones = server_config.get('join_timezones', [])

    log_channel = f"<#{log_channel_id}>" if log_channel_id else "Not set"
    admin_roles_mentions = ', '.join([f"<@&{role_id}>" for role_id in admin_roles]) if admin_roles else "None"
    sound = default_sound if mode == 'single' else "N/A"

    embed = discord.Embed(
        title=f"{interaction.guild.name} Bot Settings",
        color=discord.Color.blue()
    )
    embed.add_field(name="Logging Channel", value=log_channel, inline=False)
    embed.add_field(name="Admin Roles", value=admin_roles_mentions, inline=False)
    embed.add_field(name="Sound Mode", value=mode.capitalize(), inline=False)
    if mode == 'single':
        embed.add_field(name="Sound", value=sound, inline=False)
    embed.add_field(name="Join Frequency", value=join_frequency.capitalize(), inline=False)
    if join_frequency == 'timezones':
        timezones_list = '\n'.join(join_timezones) if join_timezones else "None"
        embed.add_field(name="Enabled Timezones", value=timezones_list, inline=False)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="cheers", description="Play the cheers sound in a voice channel.")
@app_commands.describe(channel="The voice channel to join and play the sound.")
async def cheers(interaction: discord.Interaction, channel: discord.VoiceChannel):
    if is_server_blacklisted(interaction.guild.id):
        await handle_blacklisted_server(interaction)
        return
    if not await ensure_setup(interaction):
        return

    try:
        await interaction.response.defer(ephemeral=True)  # Defer the interaction response

        # Check if the bot is already connected to a voice channel
        if interaction.guild.voice_client and interaction.guild.voice_client.channel != channel:
            await interaction.guild.voice_client.disconnect()

        vc = interaction.guild.voice_client or await channel.connect()
        await interaction.followup.send(f"Joined {channel.name} successfully!")

        # Play the sound based on the server's mode
        await play_sound_and_leave(interaction.guild, vc, interaction.user)
        
        increment_manual_smoke_seshes_count()  # Increment the manual smoke seshes count
    except Exception as e:
        if not interaction.response.is_done():
            await interaction.followup.send(f"Failed to join: {e}", ephemeral=True)
        else:
            print(f"Error during /cheers command: {e}")

@bot.tree.command(name="meetthedev", description="Meet the developer of CheersBot.")
async def meetthedev(interaction: discord.Interaction):
    if is_server_blacklisted(interaction.guild.id):
        await handle_blacklisted_server(interaction)
        return
    with open(config_path, 'r') as f:
        global_config = json.load(f)
    
    discord_link = global_config.get("discord_link", "https://discord.gg/HomiesHouse")
    website = global_config.get("website", "https://HomiesHouse.net")
    developer_ids = global_config.get("bot_developer_ids", [])
    owner_mentions = ', '.join([f"<@{owner_id}>" for owner_id in developer_ids])
    
    embed = discord.Embed(
        title="Meet the Developer",
        description="Learn more about the creators of CheersBot!",
        color=discord.Color.blue()
    )
    embed.add_field(name="Discord Link", value=f"[Join our Discord]({discord_link})", inline=False)
    embed.add_field(name="Website", value=f"[Visit our Website]({website})", inline=False)
    embed.add_field(name="Owners", value=owner_mentions, inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="blacklist", description="Manage the blacklist of channels for auto-join.")
@commands.has_permissions(administrator=True)
@app_commands.describe(action="Add, remove a channel from the blacklist, or list all blacklisted channels.", channel="The channel to add or remove.")
async def blacklist(interaction: discord.Interaction, action: str, channel: discord.VoiceChannel = None):
    if is_server_blacklisted(interaction.guild.id):
        await handle_blacklisted_server(interaction)
        return
    if not await ensure_setup(interaction):
        return

    server_config = load_or_create_server_config(interaction.guild.id)
    blacklist_channels = server_config.get("blacklist_channels", [])

    if action.lower() == "add":
        if channel and channel.id not in blacklist_channels:
            blacklist_channels.append(channel.id)
            server_config["blacklist_channels"] = blacklist_channels
            save_config(interaction.guild.id, server_config)
            await interaction.response.send_message(f"Channel {channel.name} has been added to the blacklist.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Channel {channel.name} is already in the blacklist or not specified.", ephemeral=True)
    elif action.lower() == "remove":
        if channel and channel.id in blacklist_channels:
            blacklist_channels.remove(channel.id)
            server_config["blacklist_channels"] = blacklist_channels
            save_config(interaction.guild.id, server_config)
            await interaction.response.send_message(f"Channel {channel.name} has been removed from the blacklist.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Channel {channel.name} is not in the blacklist or not specified.", ephemeral=True)
    elif action.lower() == "list":
        if blacklist_channels:
            embed = discord.Embed(title="Blacklisted Channels", color=discord.Color.red())
            for channel_id in blacklist_channels:
                channel = interaction.guild.get_channel(channel_id)
                if channel:
                    embed.add_field(name=channel.name, value=f"ID: {channel.id}", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("No channels are currently blacklisted.", ephemeral=True)
    else:
        await interaction.response.send_message("Invalid action. Please use 'add', 'remove', or 'list'.", ephemeral=True)

@bot.command(name="sync")
async def sync(ctx):
    developer_ids = load_developer_ids()
    if str(ctx.author.id) not in developer_ids:
        await ctx.send("You do not have permission to use this command.")
        return

    try:
        # Sync commands globally
        print("Syncing...")
        synced = await bot.tree.sync()
        command_count = len(synced)

        # Update server list and regenerate invite links
        await update_server_list()

        # Generate a summary of the sync operation
        server_count = len(bot.guilds)
        await ctx.send(f"Successfully synced {command_count} commands to {server_count} servers.")
        print(f"Successfully synced {command_count} commands to {server_count} servers.")
    except Exception as e:
        await ctx.send(f"Failed to sync commands: {e}")
        print(f"Failed to sync commands: {e}")

    # Output "Syncing..." every 10 seconds until syncing is complete
    while True:
        print("Syncing...")
        await asyncio.sleep(10)
        if not bot.is_closed():
            break

    print("Syncing complete.")

@bot.event
async def on_command_error(ctx, error):
    with open(config_path, 'r') as f:
        global_config = json.load(f)
    developer_ids = global_config.get("bot_developer_ids", [])
    discord_link = global_config.get("discord_link", "https://discord.gg/HomiesHouse")
    developer_mentions = ', '.join([f"<@{dev_id}>" for dev_id in developer_ids])

    embed = discord.Embed(
        title="Error",
        description=f"An error occurred: {str(error)}",
        color=discord.Color.red()
    )
    embed.add_field(
        name="Need Help?",
        value=f"If you are unsure what went wrong, please contact {developer_mentions} or join the Discord at {discord_link}.",
        inline=False
    )
    await ctx.send(embed=embed)

@bot.tree.command(name="test", description="Manually trigger the join and play functions for all servers.")
async def test(interaction: discord.Interaction):
    if not is_developer(interaction):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    await interaction.response.send_message("Starting test command. Joining all servers' most populated voice channels...", ephemeral=True)

    success_list = []
    failure_list = []
    not_setup_list = []
    empty_list = []

    async def test_join_and_play(guild):
        server_config = load_or_create_server_config(guild.id)
        blacklist_channels = server_config.get("blacklist_channels", [])
        
        voice_channel = max(
            (vc for vc in guild.voice_channels if len(vc.members) > 0 and vc.id not in blacklist_channels),
            key=lambda vc: len(vc.members),
            default=None
        )
        if voice_channel:
            try:
                vc = await voice_channel.connect(reconnect=True)
                await asyncio.sleep(15)  # Wait 15 seconds before playing the sound
                await play_sound_and_leave(guild, vc, interaction.user)
                success_list.append(guild)
            except Exception as e:
                print(f"Error during test join in {voice_channel.name} on {guild.name}: {e}")
                failure_list.append(guild)
        else:
            # Check if there are any voice channels that the bot can join
            if any(vc.id not in blacklist_channels for vc in guild.voice_channels):
                empty_list.append(guild)
            else:
                not_setup_list.append(guild)

    tasks = [test_join_and_play(guild) for guild in bot.guilds]
    await asyncio.gather(*tasks)

    # Create the embed for logging results
    master_guild_id = global_config.get("master_server_id")
    log_guild = bot.get_guild(master_guild_id)
    log_channel_id = load_or_create_server_config(master_guild_id).get("log_channel_id")
    log_channel = bot.get_channel(log_channel_id) if log_channel_id else None

    if log_channel:
        embed = discord.Embed(title="Test Command Results", color=discord.Color.blue())
        embed.add_field(name="Successful Joins", value="\n".join([f"{guild.name} (ID: {guild.id}) | Owner: {guild.owner}" for guild in success_list]) or "[None]", inline=False)
        embed.add_field(name="Failed Joins", value="\n".join([f"{guild.name} (ID: {guild.id}) | Owner: {guild.owner}" for guild in failure_list]) or "[None]", inline=False)
        embed.add_field(name="Not Setup", value="\n".join([f"{guild.name} (ID: {guild.id}) | Owner: {guild.owner}" for guild in not_setup_list]) or "[None]", inline=False)
        embed.add_field(name="Empty", value="\n".join([f"{guild.name} (ID: {guild.id}) | Owner: {guild.owner}" for guild in empty_list]) or "[None]")
        embed.add_field(name="Total Servers", value=f"{len(bot.guilds)}", inline=False)
        await log_channel.send(embed=embed)

    # Send a single embed to all other servers
    for guild in bot.guilds:
        if guild.id != master_guild_id:
            server_config = load_or_create_server_config(guild.id)
            log_channel_id = server_config.get('log_channel_id')
            if log_channel_id:
                log_channel = bot.get_channel(log_channel_id)
                if log_channel:
                    test_embed = discord.Embed(
                        title="Developer Test Join",
                        description=(
                            f"The bot joined a voice channel for testing purposes.\n"
                            f"**Sound Played:** {server_config.get('default_sound', 'Cheers_Bitch.mp3')}\n"
                            f"**Time Played:** {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC\n"
                            f"**Executed by:** {interaction.user.mention}\n\n"
                            "Note: The developer is working on the bot, and it may join at 'off' times."
                        ),
                        color=discord.Color.orange()
                    )
                    await log_channel.send(embed=test_embed)

    await interaction.followup.send("Test command completed. Check logs for details.", ephemeral=True)

class UpdateEmbedView(ui.View):
    def __init__(self, embed, interaction, server_id=None):
        super().__init__(timeout=30)  # 30 seconds timeout for interaction
        self.embed = embed
        self.interaction = interaction
        self.server_id = server_id

    @ui.button(label="Send", style=ButtonStyle.green)
    async def send_button(self, interaction: Interaction, button: ui.Button):
        if self.server_id:
            await self.send_update_to_server(self.server_id)
        else:
            await self.send_update_to_all_servers()
        await interaction.response.send_message("Update sent.", ephemeral=True)

    async def send_update_to_all_servers(self):
        for guild in bot.guilds:
            await self.send_update_to_server(guild.id)

    async def send_update_to_server(self, server_id):
        guild = bot.get_guild(server_id)
        if guild:
            server_config = load_or_create_server_config(guild.id)
            log_channel_id = server_config.get('log_channel_id')
            if log_channel_id:
                log_channel = bot.get_channel(log_channel_id)
                if log_channel:
                    await log_channel.send(embed=self.embed)

    async def on_timeout(self):
        await self.interaction.edit_original_response(content="The update was not sent due to timeout.", embed=None, view=None)

@bot.tree.command(name="update", description="Send an update message to a specific server or all servers. Developer only.")
@app_commands.describe(server_id="The ID of the server to send the update to. Leave empty to send to all servers.")
async def update(interaction: discord.Interaction, server_id: str = None):
    if not is_developer(interaction):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    await interaction.response.send_message("Please enter the title for the update message:", ephemeral=True)

    def check_message(msg: discord.Message):
        return msg.author == interaction.user and msg.channel == interaction.channel

    try:
        title_msg = await bot.wait_for('message', timeout=60.0, check=check_message)
        title = title_msg.content.strip()

        await interaction.followup.send("Please enter the body for the update message:", ephemeral=True)
        body_msg = await bot.wait_for('message', timeout=60.0, check=check_message)
        body = body_msg.content.strip()

        # Load global config settings
        with open(config_path, 'r') as f:
            global_config = json.load(f)

        log_settings = global_config.get("log_settings", {})
        footer_text = log_settings.get("footer_text", "CheersBot V2.0 by HomiesHouse | Discord.gg/HomiesHouse")
        footer_icon_url = log_settings.get("footer_icon_url", "https://i.imgur.com/4OO5wh0.png")
        thumbnail_url = log_settings.get("thumbnail_url", "https://i.imgur.com/4OO5wh0.png")

        # Create the embed
        embed = discord.Embed(
            title=title,
            description=body,
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=thumbnail_url)
        embed.set_footer(text=footer_text, icon_url=footer_icon_url)

        view = UpdateEmbedView(embed, interaction, int(server_id) if server_id else None)
        await interaction.followup.send("Here is the preview of the update message:", embed=embed, view=view, ephemeral=True)

    except asyncio.TimeoutError:
        await interaction.followup.send("Update command timed out. Please run `/update` again.", ephemeral=True)

# Path to store feedback bans
FEEDBACK_BANS_PATH = os.path.join(SERVER_LOG_DIR, "FeedbackBans.json")

def load_feedback_bans():
    if os.path.exists(FEEDBACK_BANS_PATH):
        with open(FEEDBACK_BANS_PATH, 'r') as f:
            return json.load(f)
    return {}

def save_feedback_bans(feedback_bans):
    with open(FEEDBACK_BANS_PATH, 'w') as f:
        json.dump(feedback_bans, f, indent=4)

@bot.tree.command(name="feedback-ban", description="Ban a user from using the /feedback command. Developer only.")
@app_commands.describe(user="The user to ban from using /feedback.", reason="The reason for banning the user.")
async def feedback_ban(interaction: discord.Interaction, user: discord.User, reason: str):
    if not is_developer(interaction):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    feedback_bans = load_feedback_bans()
    feedback_bans[str(user.id)] = reason
    save_feedback_bans(feedback_bans)

    await interaction.response.send_message(f"User {user.mention} has been banned from using the /feedback command for the following reason: {reason}", ephemeral=True)

@bot.tree.command(name="partners", description="Display the list of partner servers.")
async def partners(interaction: discord.Interaction):
    try:
        with open('partners.json', 'r') as f:
            partners = json.load(f)
    except json.JSONDecodeError:
        partners = []
    
    with open(config_path, 'r') as f:
        config = json.load(f)

    master_server_id = config['master_server_id']
    master_server_name = "⭐ Master Server"
    master_server_members = "Unknown"

    # Retrieve the master server name and member count from the server logs
    with open(SERVER_LIST_PATH, 'r') as f:
        for line in f:
            if f"ID: {master_server_id}" in line:
                master_server_name = "⭐ " + line.split(' (ID: ')[0]
                master_server_members = line.split("Total Members: ")[1].split(" | ")[0]
                break

    master_server = {
        'name': master_server_name,
        'invite': config['discord_link'],
        'owner': ', '.join([f"<@{id}>" for id in config['bot_developer_ids']]),
        'members': master_server_members
    }

    # Load global config settings for footer
    log_settings = config.get("log_settings", {})
    footer_text = log_settings.get("footer_text", "CheersBot V2.0 by HomiesHouse | Discord.gg/HomiesHouse")
    footer_icon_url = log_settings.get("footer_icon_url", "https://i.imgur.com/4OO5wh0.png")
    thumbnail_url = log_settings.get("thumbnail_url", "https://i.imgur.com/4OO5wh0.png")

    # Update member counts dynamically
    for partner in partners:
        guild = bot.get_guild(int(partner.get('id', 0)))  # Use .get to handle missing 'id' key
        if guild:
            partner['members'] = guild.member_count
        elif 'members' not in partner:
            partner['members'] = "Unknown"

    # Sort partners by member count, highest to lowest
    partners.sort(key=lambda x: int(str(x['members'])) if str(x['members']).isdigit() else 0, reverse=True)

    # Save the updated partners list
    with open('partners.json', 'w') as f:
        json.dump(partners, f, indent=2)

    embeds = []
    current_page = 0
    current_embed = discord.Embed(
        title='Peep our Partners',
        description='Looking for more friends? Check out our Partners!',
        color=discord.Color.blue()
    )
    current_embed.set_thumbnail(url=thumbnail_url)
    current_embed.set_footer(text=footer_text, icon_url=footer_icon_url)
    current_embed.add_field(
        name=master_server['name'],
        value=f"Invite: {master_server['invite']}\nMembers: `{master_server['members']}`\nOwner: {master_server['owner']}",
        inline=False
    )

    for index, partner in enumerate(partners):
        member_count = partner.get('members', "Unknown")
        if index % 5 == 0 and index != 0:
            embeds.append(current_embed)
            current_embed = discord.Embed(
                title='Partners',
                description='Looking for more friends? Check out our Partners!',
                color=discord.Color.blue()
            )
            current_embed.set_thumbnail(url=thumbnail_url)
            current_embed.set_footer(text=footer_text, icon_url=footer_icon_url)
        current_embed.add_field(
            name=f"{index + 1}. {partner['name']}",
            value=f"Invite: {partner['invite']}\nMembers: `{member_count}`\nOwner: <@{partner['owner']}>",
            inline=False
        )

    embeds.append(current_embed)

    view = discord.ui.View()
    view.add_item(discord.ui.Button(
        custom_id='previous',
        label='Previous',
        style=discord.ButtonStyle.primary,
        disabled=True
    ))
    view.add_item(discord.ui.Button(
        custom_id='next',
        label='Next',
        style=discord.ButtonStyle.primary,
        disabled=len(embeds) == 1
    ))

    message = await interaction.response.send_message(embed=embeds[current_page], view=view)

    def check(interaction):
        return interaction.message and interaction.message.id == message.id and interaction.user == interaction.user

    while True:
        try:
            interaction = await bot.wait_for('interaction', check=check, timeout=60.0)
            if interaction.custom_id == 'previous':
                current_page -= 1
            elif interaction.custom_id == 'next':
                current_page += 1

            view = discord.ui.View()
            view.add_item(discord.ui.Button(
                custom_id='previous',
                label='Previous',
                style=discord.ButtonStyle.primary,
                disabled=current_page == 0
            ))
            view.add_item(discord.ui.Button(
                custom_id='next',
                label='Next',
                style=discord.ButtonStyle.primary,
                disabled=current_page == len(embeds) - 1
            ))

            await interaction.response.edit_message(embed=embeds[current_page], view=view)
        except asyncio.TimeoutError:
            break

@bot.command(name='partners_edit')
async def partners_edit(ctx, action: str):
    """Edit the partners list. Action can be 'add' or 'remove'."""
    with open(config_path, 'r') as f:
        config = json.load(f)

    if str(ctx.author.id) not in config['bot_developer_ids']:
        await ctx.send('You do not have permission to use this command.')
        return

    if action.lower() not in ['add', 'remove']:
        await ctx.send("Invalid action. Please use 'add' or 'remove'.")
        return

    partners_file = 'partners.json'
    if not os.path.exists(partners_file):
        with open(partners_file, 'w') as f:
            json.dump([], f)

    if action.lower() == 'add':
        await ctx.send('Please provide the server ID:')
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await bot.wait_for('message', check=check, timeout=30.0)
            server_id = msg.content.strip()

            guild = bot.get_guild(int(server_id))
            if not guild:
                await ctx.send('Invalid server ID or the bot is not in the server. Please provide the details manually.')

                await ctx.send('Please provide the server name:')
                name_msg = await bot.wait_for('message', check=check, timeout=60.0)
                server_name = name_msg.content.strip()

                await ctx.send('Please provide the invite link:')
                invite_msg = await bot.wait_for('message', check=check, timeout=60.0)
                invite_link = invite_msg.content.strip()

                await ctx.send('Please provide the number of members:')
                members_msg = await bot.wait_for('message', check=check, timeout=60.0)
                members_count = members_msg.content.strip()

                await ctx.send('Please provide the owner ID:')
                owner_msg = await bot.wait_for('message', check=check, timeout=60.0)
                owner_id = owner_msg.content.strip()

                new_partner = {
                    'name': server_name,
                    'invite': invite_link,
                    'owner': owner_id,
                    'members': members_count
                }
            else:
                owner = guild.owner
                invite_url = f"https://discord.gg/{guild.vanity_url_code}" if guild.vanity_url_code else None

                if not invite_url:
                    try:
                        invites = await guild.invites()
                        invite = next((i for i in invites if not i.max_age and not i.max_uses), None)
                        if invite:
                            invite_url = invite.url
                        else:
                            invite_url = await create_unlimited_invite(guild)
                    except discord.Forbidden:
                        invite_url = "No Permission"

                new_partner = {
                    'name': guild.name,
                    'invite': invite_url,
                    'owner': owner.id,
                    'members': guild.member_count,
                    'id': str(guild.id)  # Ensure the 'id' key is included
                }

            with open(partners_file, 'r') as f:
                partners = json.load(f)

            partners.append(new_partner)
            partners.sort(key=lambda x: int(str(x['members'])) if str(x['members']).isdigit() else 0, reverse=True)
            with open(partners_file, 'w') as f:
                json.dump(partners, f, indent=2)

            await ctx.send(f'Successfully added {new_partner["name"]} to the partners list.')
        except asyncio.TimeoutError:
            await ctx.send('You took too long to respond. Please try again.')

    elif action.lower() == 'remove':
        with open(partners_file, 'r') as f:
            partners = json.load(f)

        embed = discord.Embed(
            title='Remove Partner',
            description='Select a partner to remove:',
            color=discord.Color.red()
        )

        for index, partner in enumerate(partners):
            embed.add_field(
                name=f"{index + 1}. {partner['name']}",
                value=f"Invite: {partner['invite']}\nOwner: <@{partner['owner']}>",
                inline=False
            )

        view = discord.ui.View()
        for i in range(min(len(partners), 5)):
            view.add_item(
                discord.ui.Button(
                    custom_id=f'remove_{i}',
                    label=f'{i + 1}',
                    style=discord.ButtonStyle.danger
                )
            )

        message = await ctx.send(embed=embed, view=view)

        def check(interaction):
            return interaction.message and interaction.message.id == message.id and interaction.user == ctx.author

        try:
            interaction = await bot.wait_for('interaction', check=check, timeout=60.0)
            custom_id = interaction.data['custom_id']
            index = int(custom_id.split('_')[1])
            partners.pop(index)
            partners.sort(key=lambda x: int(str(x['members'])) if str(x['members']).isdigit() else 0, reverse=True)
            with open(partners_file, 'w') as f:
                json.dump(partners, f, indent=2)
            await interaction.response.edit_message(content='Partner removed successfully.', embed=None, view=None)
        except asyncio.TimeoutError:
            await ctx.send('You took too long to respond. Please try again.')

    # Update member counts dynamically
    with open(partners_file, 'r') as f:
        partners = json.load(f)

    for partner in partners:
        if 'id' in partner:
            guild = bot.get_guild(int(partner['id']))
            if guild:
                partner['members'] = guild.member_count
            elif 'members' not in partner:
                partner['members'] = "Unknown"

    partners.sort(key=lambda x: int(str(x['members'])) if str(x['members']).isdigit() else 0, reverse=True)
    with open(partners_file, 'w') as f:
        json.dump(partners, f, indent=2)

    await ctx.send('Partners list updated with current member counts.')

CHEERS_COUNT_FILE = 'cheers-count.json'

# Load cheers count data
def load_cheers_count():
    with open('cheers-count.json', 'r') as f:
        return json.load(f)

# Save cheers count data
def save_cheers_count(data):
    with open('cheers-count.json', 'w') as f:
        json.dump(data, f, indent=4)

class CheersCountView(View):
    def __init__(self, seshes_disabled=False, sounds_disabled=False, local_disabled=False):
        super().__init__(timeout=None)
        self.add_item(Button(label="Seshes", style=discord.ButtonStyle.primary, custom_id="seshes_button", disabled=seshes_disabled))
        self.add_item(Button(label="Specific Sounds", style=discord.ButtonStyle.primary, custom_id="specific_sounds_button", disabled=sounds_disabled))
        self.add_item(Button(label="Local", style=discord.ButtonStyle.primary, custom_id="local_button", disabled=local_disabled))

@bot.tree.command(name="cheers-count", description="Show the count of each sound played.")
async def cheers_count(interaction: discord.Interaction):
    cheers_count = load_cheers_count()
    its_420_somewhere_count = cheers_count.get("its_420_somewhere_count", 0)
    manual_smoke_seshes_count = cheers_count.get("manual_smoke_seshes_count", 0)
    total_smoke_seshes_count = cheers_count.get("total_smoke_seshes_count", 0)

    embed = discord.Embed(title="Seshes Count", color=discord.Color.green())
    embed.add_field(name="It's 4:20 Somewhere!", value=f"`{its_420_somewhere_count}` times", inline=False)
    embed.add_field(name="Manual Smoke Seshes Count", value=f"`{manual_smoke_seshes_count}` times", inline=False)
    embed.add_field(name="Total Smoke Seshes Count", value=f"`{total_smoke_seshes_count}` times", inline=False)

    view = CheersCountView(seshes_disabled=True)
    await interaction.response.send_message(embed=embed, view=view)

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        cheers_count = load_cheers_count()
        if interaction.data["custom_id"] == "seshes_button":
            its_420_somewhere_count = cheers_count.get("its_420_somewhere_count", 0)
            manual_smoke_seshes_count = cheers_count.get("manual_smoke_seshes_count", 0)
            total_smoke_seshes_count = cheers_count.get("total_smoke_seshes_count", 0)

            embed = discord.Embed(title="Seshes Count", color=discord.Color.green())
            embed.add_field(name="420 Somewhere Count", value=f"`{its_420_somewhere_count}` times", inline=False)
            embed.add_field(name="Manual Smoke Seshes Count", value=f"`{manual_smoke_seshes_count}` times", inline=False)
            embed.add_field(name="Total Smoke Seshes Count", value=f"`{total_smoke_seshes_count}` times", inline=False)

            view = CheersCountView(seshes_disabled=True)
            await interaction.response.edit_message(embed=embed, view=view)

        elif interaction.data["custom_id"] == "specific_sounds_button":
            sound_play_counts = cheers_count.get('sound_play_counts', {})

            if not sound_play_counts:
                await interaction.response.edit_message(content="No sounds have been played yet.", embed=None, view=None)
                return

            embed = discord.Embed(title="Cheers Sound Play Counts", color=discord.Color.blue())
            for sound, count in sound_play_counts.items():
                embed.add_field(name=sound, value=f"`{count}` times", inline=False)

            view = CheersCountView(sounds_disabled=True)
            await interaction.response.edit_message(embed=embed, view=view)

        elif interaction.data["custom_id"] == "local_button":
            server_config = load_or_create_server_config(interaction.guild.id)
            local_cheers_count = server_config.get("local_cheers_count", 0)

            embed = discord.Embed(
                title=f"{interaction.guild.name} - Cheers Count",
                description=f"Cheers bot has said Cheers in {interaction.guild.name} `{local_cheers_count}` times.",
                color=discord.Color.blue()
            )

            view = CheersCountView(local_disabled=True)
            await interaction.response.edit_message(embed=embed, view=view)

# Load developer DMs channel ID and role ID from config.json
def load_developer_dm_channel_id():
    with open(config_path, 'r') as f:
        global_config = json.load(f)
    return int(global_config.get("developer_dm_channel_id"))

def load_developer_dm_role_id():
    with open(config_path, 'r') as f:
        global_config = json.load(f)
    return int(global_config.get("developer_dm_role_id"))

developer_dm_channel_id = load_developer_dm_channel_id()
developer_dm_role_id = load_developer_dm_role_id()

DM_BANS_PATH = os.path.join(SERVER_LOG_DIR, "DM_Bans.json")

def load_dm_bans():
    if os.path.exists(DM_BANS_PATH):
        with open(DM_BANS_PATH, 'r') as f:
            return json.load(f)
    return {}

def save_dm_bans(dm_bans):
    with open(DM_BANS_PATH, 'w') as f:
        json.dump(dm_bans, f, indent=4)

@bot.command(name='DM_ban', aliases=['dm_ban', 'Dm_ban', 'dM_ban'])
async def dm_ban(ctx):
    """Ban a user from directly messaging the bot."""
    with open(config_path, 'r') as f:
        config = json.load(f)

    if str(ctx.author.id) not in config['bot_developer_ids']:
        await ctx.send('You do not have permission to use this command.')
        return

    await ctx.send('Please provide the user ID to ban:')
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        msg = await bot.wait_for('message', check=check, timeout=30.0)
        user_id = msg.content.strip()

        await ctx.send('Please provide the reason for the ban:')
        reason_msg = await bot.wait_for('message', check=check, timeout=30.0)
        reason = reason_msg.content.strip()

        dm_bans = load_dm_bans()
        dm_bans[user_id] = reason
        save_dm_bans(dm_bans)

        await ctx.send(f'User with ID {user_id} has been banned from directly messaging the bot for the following reason: {reason}')
    except asyncio.TimeoutError:
        await ctx.send('You took too long to respond. Please try again.')

@bot.command(name='DM_unban', aliases=['dm_unban', 'Dm_unban', 'dM_unban'])
async def dm_unban(ctx):
    """Unban a user from directly messaging the bot."""
    with open(config_path, 'r') as f:
        config = json.load(f)

    if str(ctx.author.id) not in config['bot_developer_ids']:
        await ctx.send('You do not have permission to use this command.')
        return

    await ctx.send('Please provide the user ID to unban:')
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        msg = await bot.wait_for('message', check=check, timeout=30.0)
        user_id = msg.content.strip()

        dm_bans = load_dm_bans()
        if user_id in dm_bans:
            del dm_bans[user_id]
            save_dm_bans(dm_bans)
            await ctx.send(f'User with ID {user_id} has been unbanned from directly messaging the bot.')
        else:
            await ctx.send(f'User with ID {user_id} is not banned.')
    except asyncio.TimeoutError:
        await ctx.send('You took too long to respond. Please try again.')

DM_GLOBAL_TOGGLE_PATH = os.path.join(SERVER_LOG_DIR, "DM_Global_Toggle.json")

def load_dm_global_toggle():
    if os.path.exists(DM_GLOBAL_TOGGLE_PATH):
        with open(DM_GLOBAL_TOGGLE_PATH, 'r') as f:
            return json.load(f)
    return {"enabled": True, "reason": ""}

def save_dm_global_toggle(dm_global_toggle):
    with open(DM_GLOBAL_TOGGLE_PATH, 'w') as f:
        json.dump(dm_global_toggle, f, indent=4)

@bot.command(name='DM_toggle', aliases=['dm_toggle', 'Dm_toggle', 'dM_toggle'])
async def dm_toggle(ctx):
    """Toggle global DM enable/disable."""
    with open(config_path, 'r') as f:
        config = json.load(f)

    if str(ctx.author.id) not in config['bot_developer_ids']:
        await ctx.send('You do not have permission to use this command.')
        return

    dm_global_toggle = load_dm_global_toggle()
    if dm_global_toggle["enabled"]:
        await ctx.send('DMs are currently enabled. Do you want to disable them? (yes/no)')
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await bot.wait_for('message', check=check, timeout=30.0)
            if msg.content.strip().lower() == 'yes':
                await ctx.send('Please provide a reason for disabling DMs (type "none" for no reason):')
                reason_msg = await bot.wait_for('message', check=check, timeout=30.0)
                reason = reason_msg.content.strip()
                if reason.lower() == "none":
                    reason = ""
                dm_global_toggle["enabled"] = False
                dm_global_toggle["reason"] = reason
                save_dm_global_toggle(dm_global_toggle)
                await ctx.send(f'DMs have been disabled. Reason: {reason}')
            else:
                await ctx.send('DMs remain enabled.')
        except asyncio.TimeoutError:
            await ctx.send('You took too long to respond. Please try again.')
    else:
        dm_global_toggle["enabled"] = True
        dm_global_toggle["reason"] = ""
        save_dm_global_toggle(dm_global_toggle)
        await ctx.send('DMs have been enabled.')

@bot.event
async def on_message(message):
    if message.guild is None and not message.author.bot:
        dm_global_toggle = load_dm_global_toggle()
        if not dm_global_toggle["enabled"]:
            reason = dm_global_toggle["reason"]
            embed = discord.Embed(
                title="DMs Disabled",
                description=f"DMs are currently disabled. Reason: {reason}" if reason else "DMs are currently disabled.",
                color=discord.Color.red()
            )
            await message.author.send(embed=embed)
            return
        dm_bans = load_dm_bans()
        if str(message.author.id) in dm_bans:
            reason = dm_bans[str(message.author.id)]
            with open(config_path, 'r') as f:
                global_config = json.load(f)
            footer_text = global_config.get("log_settings", {}).get("footer_text", "CheersBot V2.0 by HomiesHouse | Discord.gg/HomiesHouse")
            footer_icon_url = global_config.get("log_settings", {}).get("footer_icon_url", "https://i.imgur.com/4OO5wh0.png")
            thumbnail_url = global_config.get("log_settings", {}).get("thumbnail_url", "https://i.imgur.com/4OO5wh0.png")

            embed = discord.Embed(
                title="DM Ban",
                description=f"You have been banned from directly messaging the bot for the following reason:\n{reason}",
                color=discord.Color.red()
            )
            embed.set_thumbnail(url=thumbnail_url)
            embed.set_footer(text=footer_text, icon_url=footer_icon_url)
            await message.author.send(embed=embed)
            return
        # Handle DMs to the bot
        developer_dm_channel = bot.get_channel(developer_dm_channel_id)
        if developer_dm_channel:
            # Send a role mention and delete it immediately
            role_mention_message = await developer_dm_channel.send(f"<@&{developer_dm_role_id}>")
            await role_mention_message.delete()

            embed = discord.Embed(
                title="New DM Received",
                description=f"**From:** {message.author.name} <@{message.author.id}>\n**Message:** {message.content}",
                color=discord.Color.blue()
            )
            await developer_dm_channel.send(embed=embed)
            if message.attachments:
                files = [await attachment.to_file() for attachment in message.attachments]
                await developer_dm_channel.send(files=files)
        else:
            print(f"Developer DM channel with ID {developer_dm_channel_id} not found.")
    elif message.guild and message.channel.id == developer_dm_channel_id and not message.author.bot:
        # Handle replies from the developer DM channel
        if message.reference and message.reference.message_id:
            ref_message = await message.channel.fetch_message(message.reference.message_id)
            user_id = int(ref_message.embeds[0].description.split('<@')[1].split('>')[0])
            user = bot.get_user(user_id)
            if user:
                embed = discord.Embed(
                    title="Reply from Developer",
                    description=f"**Reply from {message.author.name}:** {message.content}",
                    color=discord.Color.blue()
                )
                await user.send(embed=embed)
                if message.attachments:
                    files = [await attachment.to_file() for attachment in message.attachments]
                    await user.send(files=files)
            else:
                await message.channel.send("User not found.")
    await bot.process_commands(message)

@bot.event
async def on_error(event, *args, **kwargs):
    import traceback
    error = traceback.format_exc()
    if "KeyError: <StickerFormatType.unknown_4: 4>" in error:
        print("Encountered unknown sticker format. Ignoring and continuing.")
    else:
        print(f"An error occurred: {error}")

bot.run(BOT_TOKEN)
