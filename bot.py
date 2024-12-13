# CheersBot v2 - A Discord bot by Wubbity. Cheers!

import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import json
from dotenv import load_dotenv
import random
import asyncio
from datetime import datetime, timedelta, timezone
import pytz
import platform
from discord import ui, ButtonStyle, Interaction
import math
from discord.ext.commands import AutoShardedBot

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

# Define the path for the 420Game folder
GAME_FOLDER = os.path.join(BASE_DIR, "420Game")
if not os.path.exists(GAME_FOLDER):
    os.makedirs(GAME_FOLDER)

# Define the path for the shop config
SHOP_CONFIG_PATH = os.path.join(GAME_FOLDER, "shop_config.json")

# Define the path for the UserData folder
USER_DATA_FOLDER = os.path.join(BASE_DIR, "UserData")
if not os.path.exists(USER_DATA_FOLDER):
    os.makedirs(USER_DATA_FOLDER)

# Helper function to load or create a player profile
def load_or_create_profile(user_id):
    profile_path = os.path.join(USER_DATA_FOLDER, f"{user_id}.json")
    if os.path.exists(profile_path):
        with open(profile_path, 'r') as f:
            profile = json.load(f)
        # Ensure the profile has all necessary fields
        if 'start_date' not in profile:
            profile['start_date'] = datetime.now().isoformat()
        if 'current_joints' not in profile:
            profile['current_joints'] = 0
        if 'balance' not in profile:
            profile['balance'] = 0
        if 'income_per_hour' not in profile:
            profile['income_per_hour'] = 0
        save_profile(user_id, profile)
        return profile
    else:
        profile = {
            "trap_house_name": "My First Trap",
            "balance": 0,
            "income_per_hour": 0,
            "total_joints_rolled": 0,
            "current_joints": 0,
            "rolling_skill": 1,
            "trap_house_age": 0,
            "start_date": datetime.now().isoformat(),
            "last_check_in": datetime.now().isoformat()
        }
        save_profile(user_id, profile)
        return profile

# Helper function to save a player profile
def save_profile(user_id, profile):
    profile_path = os.path.join(USER_DATA_FOLDER, f"{user_id}.json")
    with open(profile_path, 'w') as f:
        json.dump(profile, f, indent=4)
    save_profile_in_game_folder(user_id, profile)

# Helper function to save a player profile in the 420Game folder
def save_profile_in_game_folder(user_id, profile):
    profile_path = os.path.join(GAME_FOLDER, f"{user_id}.json")
    with open(profile_path, 'w') as f:
        json.dump(profile, f, indent=4)

# Helper function to load or create a temporary profile during maintenance mode
def load_or_create_temp_profile(user_id):
    if user_id in temp_profiles:
        return temp_profiles[user_id]
    else:
        profile = load_or_create_profile(user_id)
        temp_profiles[user_id] = profile.copy()
        return temp_profiles[user_id]

# Helper function to load or create the shop config
def load_or_create_shop_config():
    if os.path.exists(SHOP_CONFIG_PATH):
        try:
            with open(SHOP_CONFIG_PATH, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass  # If there's an error, fall back to creating a new config
    shop_config = {
        "upgrades": {
            "Rolling Papers": {
                "cost": 50,
                "income_per_hour": 5,
                "income_boost_factor": 0.90,
                "cost_multiplier": 1.20
            }
        }
    }
    with open(SHOP_CONFIG_PATH, 'w') as f:
        json.dump(shop_config, f, indent=4)
    return shop_config

# Helper function to load or create user settings
def load_or_create_user_settings(user_id):
    settings_path = os.path.join(USER_DATA_FOLDER, f"{user_id}.json")
    if os.path.exists(settings_path):
        with open(settings_path, 'r') as f:
            return json.load(f)
    else:
        settings = {
            "payment_mode": "over_time"  # Default setting
        }
        save_user_settings(user_id, settings)
        return settings

# Helper function to save user settings
def save_user_settings(user_id, settings):
    settings_path = os.path.join(USER_DATA_FOLDER, f"{user_id}.json")
    with open(settings_path, 'w') as f:
        json.dump(settings, f, indent=4)

# Task to update trap house age and passive income
@tasks.loop(hours=1)
async def update_profiles_task():
    for filename in os.listdir(GAME_FOLDER):
        if filename.endswith(".json"):
            user_id = filename.split(".")[0]
            profile = load_or_create_profile(user_id)
            start_date = datetime.fromisoformat(profile.get('start_date', datetime.now().isoformat()))
            profile['trap_house_age'] = (datetime.now() - start_date).days
            profile['balance'] += profile['income_per_hour']
            save_profile(user_id, profile)

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
                        invite_url = await create_unlimited_invite(guild)
                except discord.Forbidden:
                    if debug_mode:
                        print(f"Could not retrieve invites for {guild.name}")
                    invite_url = await create_unlimited_invite(guild)
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
bot.command_prefix = "."

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

@bot.tree.command(name="inventory", description="View your purchased items and their total income per hour.")
async def inventory(interaction: discord.Interaction):
    if is_server_blacklisted(interaction.guild.id):
        await handle_blacklisted_server(interaction)
        return
    user_id = interaction.user.id

    if not has_started_game(user_id):
        await prompt_start_game(interaction)
        return

    if debug_mode:
        profile = load_or_create_temp_profile(user_id)
    else:
        profile = load_or_create_profile(user_id)
    
    shop_config = load_or_create_shop_config()
    upgrades = shop_config.get("upgrades", {})

    embed = discord.Embed(title=f"{interaction.user.name}'s Inventory", color=discord.Color.blue())
    total_income_per_hour = 0

    for upgrade_name, upgrade_info in upgrades.items():
        purchases = profile.get(f"{upgrade_name}_purchases", 0)
        if purchases > 0:
            income_per_hour = upgrade_info["income_per_hour"]
            income_boost_factor = upgrade_info["income_boost_factor"]
            total_income = sum(income_per_hour * (income_boost_factor ** i) for i in range(purchases))
            total_income_per_hour += total_income
            embed.add_field(
                name=f"{upgrade_name} x{purchases}",
                value=f"Total Income per Hour: ${total_income:.2f}",
                inline=False
            )

    embed.add_field(name="Total Income per Hour", value=f"${total_income_per_hour:.2f}", inline=False)
    await interaction.response.send_message(embed=embed)

# Task to update user settings at the top of the hour
@tasks.loop(seconds=1)
async def update_user_settings_task():
    now = datetime.now(timezone.utc)
    if now.minute == 0 and now.second == 0:
        for filename in os.listdir(USER_DATA_FOLDER):
            if filename.endswith(".json"):
                user_id = filename.split(".")[0]
                settings = load_or_create_user_settings(user_id)
                if settings.get("payment_mode") == "over_time":
                    settings["payment_mode"] = "lump_sum"
                    save_user_settings(user_id, settings)

# Events
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}!")
    try:
        await bot.tree.sync()  # Ensure commands are synced globally
        print("Commands synced successfully.")
    except Exception as e:
        print(f"Failed to sync commands: {str(e)}")
    
    create_and_populate_server_logs()  # Ensure server log files are created and populated

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

    # Sync game commands
    await bot.tree.sync()

@bot.event
async def on_resumed():
    print("Bot has resumed connection.")
    if not auto_join_task.is_running():
        auto_join_task.start()  # Ensure the auto join task is running
    if not log_current_time_task.is_running():
        log_current_time_task.start()  # Ensure the time logging task is running
    if not update_profiles_task.is_running():
        update_profiles_task.start()  # Ensure the profile update task is running
    if not update_user_settings_task.is_running():
        update_user_settings_task.start()  # Ensure the user settings update task is running

    # Rejoin voice channels if necessary
    for guild in bot.guilds:
        if guild.voice_client and not guild.voice_client.is_connected():
            await join_all_populated_voice_channels(guild)

async def send_intro_message(guild):
    """Send an introductory message to the appropriate channel."""
    intro_message = (
        "Thank you for adding CheersBot to your server! To start using CheersBot, please run the `/setup` command. "
        "If you need any help, feel free to reach out to the support team."
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

    invite_url = "No invite available"
    try:
        invites = await guild.invites()
        invite = next((i for i in invites if not i.max_age and not i.max_uses), None)
        if invite:
            invite_url = invite.url
        else:
            invite_url = await create_unlimited_invite(guild)
    except discord.Forbidden:
        print(f"Could not retrieve invites for {guild.name}")
        invite_url = await create_unlimited_invite(guild)

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
            color=discord.Color.green()
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

        # Send the feedback embed first
        feedback_channel = bot.get_channel(feedback_channel_id)
        if feedback_channel:
            await feedback_channel.send(embed=feedback_embed)

        # Attach images and audio files
        files = []
        image_count = 0
        audio_count = 0
        for attachment in feedback_msg.attachments:
            if attachment.filename.lower().endswith(('.mp3', '.m4a', '.wav', '.ogg')):
                files.append(await attachment.to_file())
                audio_count += 1
            elif attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                files.append(await attachment.to_file())
                image_count += 1

        if files:
            await feedback_channel.send(files=files)

        # Clean up messages
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

# Auto-Join Task
@tasks.loop(seconds=1)
async def auto_join_task():
    """Check every second and trigger at X:15:00 UTC to join voice channels and X:20:00 to play sound."""
    now = datetime.now(timezone.utc)
    if debug_mode:
        print(f"Checking time: {now.strftime('%H:%M:%S')} UTC")  # Debug print to check current time

    for guild in bot.guilds:
        server_config = load_or_create_server_config(guild.id)
        join_frequency = server_config.get('join_frequency', 'every_hour')

        if join_frequency == 'every_hour':
            if now.minute == 15 and now.second == 0:  # Trigger exactly at X:15:00
                if debug_mode:
                    print(f"Triggering join_all_populated_voice_channels for {guild.name}")  # Debug print for join trigger
                await join_all_populated_voice_channels(guild)
            elif now.minute == 20 and now.second == 0:  # Trigger exactly at X:20:00
                if debug_mode:
                    print(f"Triggering play_sound_in_all_channels for {guild.name}")  # Debug print for play sound trigger
                await play_sound_in_all_channels(guild)
        elif join_frequency == 'timezones':
            join_timezones = server_config.get('join_timezones', [])
            for tz in join_timezones:
                tz_offset = int(tz.split()[1].replace('UTC', '').replace('{', '').replace('}', ''))
                tz_now = datetime.now(timezone(timedelta(hours=tz_offset)))
                if tz_now.minute == 15 and tz_now.second == 0:
                    if debug_mode:
                        print(f"Triggering join_all_populated_voice_channels for {guild.name} in timezone {tz}")  # Debug print for join trigger
                    await join_all_populated_voice_channels(guild)
                elif tz_now.minute == 20 and tz_now.second == 0:
                    if debug_mode:
                        print(f"Triggering play_sound_in_all_channels for {guild.name} in timezone {tz}")  # Debug print for play sound trigger
                    await play_sound_in_all_channels(guild)
        elif join_frequency == 'manual':
            continue  # Skip auto-join for manual mode

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
        print(f"Scheduling join for {voice_channel.name} in {guild.name}...")
        await join_voice_channel(guild, voice_channel, bot.user)  # Join the voice channel
    else:
        if debug_mode:
            print(f"No valid voice channels to join in {guild.name}. Skipping join action.")

async def play_sound_in_all_channels(guild):
    """Play the configured sound in all voice channels where the bot is connected in the specified guild."""
    if guild.voice_client and guild.voice_client.is_connected():
        await play_sound_and_leave(guild, guild.voice_client, bot.user)  # Play sound and leave the voice channel

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
        # Send a message in the first available text channel and ping the administrative role
        server_config = load_or_create_server_config(guild.id)
        admin_roles = server_config.get('admin_roles', [])
        if admin_roles:
            admin_role_mentions = ' '.join([f"<@&{role_id}>" for role_id in admin_roles])
            message = (
                f"Hey! I tried to join the most populated voice channel {voice_channel.name} but didn't have permission to. "
                f"If you want to disallow me from joining a specific voice channel, use the /blacklist command. "
                f"Please make sure I have access to the voice channel so I can play a sound on the world's next 4:20! {admin_role_mentions}"
            )
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

    sound_to_play = (
        os.path.join(SOUND_FOLDER, default_sound)
        if mode == "single"
        else os.path.join(SOUND_FOLDER, random.choice([s for s in available_sounds if server_config.get(f'sound_status_{s[:-4]}', True)]))
    )

    try:
        vc.play(discord.FFmpegPCMAudio(sound_to_play, executable=ffmpeg_path))
        while vc.is_playing():
            await asyncio.sleep(1)
        await log_action(guild, "Playing Sound", f"Played **{os.path.basename(sound_to_play)}** at {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC.", user)
        
        await asyncio.sleep(2)  # 2-second delay after the sound has finished playing
        await vc.disconnect()
        await log_action(guild, "Left Voice Channel", f"Disconnected from **{vc.channel.name}** at {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC.", user)
    except Exception as e:
        print(f"Error playing sound in {vc.channel.name} on {guild.name}: {e}")
        await vc.disconnect()

# Slash Commands
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
    embed = discord.Embed(
        title="Server Blacklisted",
        description="This server has been blacklisted from CheersBot. Join HomiesHouse (Discord.gg/HomiesHouse) and DM @Wubbity for assistance.",
        color=discord.Color.red()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

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

    if mode == 'single':
        default_sound = server_config.get('default_sound', 'Cheers_Bitch.mp3')
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
        # Reload commands globally
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
    server_config = load_or_create_server_config(interaction.guild.id)
    admin_roles = server_config.get('admin_roles', [])
    
    # Load bot developer IDs from config.json
    with open(config_path, 'r') as f:
        global_config = json.load(f)
    developer_ids = global_config.get("bot_developer_ids", [])

    # Check if the user has permission to use the command
    if not (
        interaction.user.guild_permissions.administrator
        or any(role.id in admin_roles for role in interaction.user.roles)
        or str(interaction.user.id) in developer_ids
    ):
        await interaction.response.send_message(
            "You do not have permission to use this command.", ephemeral=True
        )
        return

    try:
        await interaction.response.defer(ephemeral=True)  # Defer the interaction response
        vc = await channel.connect()
        await interaction.followup.send(f"Joined {channel.name} successfully!")

        # Play the sound based on the server's mode
        await play_sound_and_leave(interaction.guild, vc, interaction.user)
    except Exception as e:
        if not interaction.response.is_done():
            await interaction.followup.send(f"Failed to join: {e}", ephemeral=True)
        else:
            print(f"Error during /cheers command: {e}")

@bot.tree.command(name="reset_game_data", description="Reset/delete all user data from the 420Game. Bot developer only command.")
async def reset_game_data(interaction: discord.Interaction):
    if is_server_blacklisted(interaction.guild.id):
        await handle_blacklisted_server(interaction)
        return
    if not is_developer(interaction):
        await interaction.response.send_message("You do not have permission to use this command. Why did you try to do that..", ephemeral=True)
        return

    try:
        # Remove all user profiles from the UserData folder
        for filename in os.listdir(USER_DATA_FOLDER):
            if filename.endswith(".json"):
                file_path = os.path.join(USER_DATA_FOLDER, filename)
                os.remove(file_path)

        # Remove all user profiles from the 420Game folder
        for filename in os.listdir(GAME_FOLDER):
            if filename != "shop_config.json" and filename.endswith(".json"):
                file_path = os.path.join(GAME_FOLDER, filename)
                os.remove(file_path)

        await interaction.response.send_message("All user data from the 420Game has been reset/deleted.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"An error occurred while resetting game data: {e}", ephemeral=True)

class ConfirmUpgradeButton(ui.Button):
    def __init__(self, upgrade_name, user_id):
        super().__init__(label=f"Confirm {upgrade_name}", style=ButtonStyle.green)
        self.upgrade_name = upgrade_name
        self.user_id = user_id

    async def callback(self, interaction: Interaction):
        await handle_buy_upgrade(interaction, self.upgrade_name)

class DenyUpgradeButton(ui.Button):
    def __init__(self):
        super().__init__(label="Cancel", style=ButtonStyle.red)

    async def callback(self, interaction: Interaction):
        await interaction.response.send_message("Upgrade purchase canceled.", ephemeral=True)

class ConfirmUpgradeView(ui.View):
    def __init__(self, upgrade_name, user_id):
        super().__init__(timeout=60)  # 1 minute timeout for interaction
        self.add_item(ConfirmUpgradeButton(upgrade_name, user_id))
        self.add_item(DenyUpgradeButton())

def find_closest_upgrade(upgrade_name, upgrades):
    upgrade_name = upgrade_name.lower()
    closest_match = None
    min_distance = float('inf')
    for name in upgrades:
        distance = sum(1 for a, b in zip(upgrade_name, name.lower()) if a != b) + abs(len(upgrade_name) - len(name))
        if distance < min_distance:
            closest_match = name
    return closest_match

async def handle_buy_upgrade(interaction: discord.Interaction, upgrade_name: str):
    user_id = interaction.user.id

    if not has_started_game(user_id):
        await prompt_start_game(interaction)
        return

    if debug_mode:
        profile = load_or_create_temp_profile(user_id)
    else:
        profile = load_or_create_profile(user_id)
    
    shop_config = load_or_create_shop_config()
    upgrades = shop_config.get("upgrades", {})

    if upgrade_name not in upgrades:
        await interaction.response.send_message("Invalid upgrade name.", ephemeral=True)
        return

    current_purchases = profile.get(f"{upgrade_name}_purchases", 0)
    cost, income_boost = calculate_upgrade_cost_and_boost(upgrade_name, current_purchases)

    if profile["balance"] < cost:
        await interaction.response.send_message(f"Not enough balance to buy {upgrade_name}. You need ${cost:.2f}.", ephemeral=True)
        return

    profile["balance"] -= cost
    profile["income_per_hour"] += income_boost
    profile[f"{upgrade_name}_purchases"] = current_purchases + 1

    if not debug_mode:
        save_profile(user_id, profile)
    else:
        temp_profiles[user_id] = profile

    await interaction.response.send_message(f"Successfully bought {upgrade_name}! Your income per hour is now ${profile['income_per_hour']:.2f}. Next upgrade will cost ${cost:.2f}.")

@bot.tree.command(name="buy_upgrade", description="Buy an upgrade from the shop.")
@app_commands.describe(upgrade_name="The name of the upgrade to buy.")
async def buy_upgrade(interaction: discord.Interaction, upgrade_name: str):
    if is_server_blacklisted(interaction.guild.id):
        await handle_blacklisted_server(interaction)
        return
    user_id = interaction.user.id

    if not has_started_game(user_id):
        await prompt_start_game(interaction)
        return

    if debug_mode:
        profile = load_or_create_temp_profile(user_id)
    else:
        profile = load_or_create_profile(user_id)
    
    shop_config = load_or_create_shop_config()
    upgrades = shop_config.get("upgrades", {})

    if upgrade_name.lower() not in [name.lower() for name in upgrades]:
        closest_match = find_closest_upgrade(upgrade_name, upgrades)
        if closest_match:
            view = ConfirmUpgradeView(closest_match, user_id)
            await interaction.response.send_message(
                f"Did you mean '{closest_match}'? Please confirm or cancel the purchase.",
                view=view,
                ephemeral=True
            )
        else:
            await interaction.response.send_message("Invalid upgrade name.", ephemeral=True)
        return

    # Ensure the upgrade name matches exactly
    upgrade_name = next(name for name in upgrades if name.lower() == upgrade_name.lower())

    await handle_buy_upgrade(interaction, upgrade_name)

# Command to start the game and create a profile
@bot.tree.command(name="start", description="Start the game and create your profile.")
async def start(interaction: discord.Interaction):
    if is_server_blacklisted(interaction.guild.id):
        await handle_blacklisted_server(interaction)
        return
    user_id = interaction.user.id
    profile_path = os.path.join(USER_DATA_FOLDER, f"{user_id}.json")
    
    if os.path.exists(profile_path):
        await interaction.response.send_message("You already have a profile. Use `/profile` to check your stats.", ephemeral=True)
        return
    
    # Ensure the game folder exists
    if not os.path.exists(GAME_FOLDER):
        os.makedirs(GAME_FOLDER)
    
    profile = load_or_create_profile(user_id)
    
    # Create the welcome embed
    welcome_embed = discord.Embed(
        title="Welcome to the game!",
        description=f"Your trap house name is {profile['trap_house_name']}.",
        color=discord.Color.green()
    )
    
    await interaction.response.send_message(embed=welcome_embed, ephemeral=True)
    
    # Check if the BetaGameMessage is enabled in the config
    if global_config.get("BetaGameMessage", False):
        beta_message_embed = discord.Embed(
            title="Note",
            description=(
                "The 420Game is still under heavy development and the bot may restart many times due to the development. "
                "The current state of 420Game does not reflect a finished product. If you have questions or ideas and would like to share them, "
                "use the `/meetthedev` command to get in contact with Wubbity."
            ),
            color=discord.Color.orange()
        )
        await interaction.followup.send(embed=beta_message_embed, ephemeral=True)

# Helper function to check if the user has started the game
def has_started_game(user_id):
    profile_path = os.path.join(GAME_FOLDER, f"{user_id}.json")
    return os.path.exists(profile_path)

# Helper function to prompt the user to start the game
async def prompt_start_game(interaction):
    embed = discord.Embed(
        title="Start the Game",
        description="You need to start the game before using this command. Please run the `/start` command to begin.",
        color=discord.Color.red()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Command to view the profile
@bot.tree.command(name="profile", description="View your game profile.")
async def profile(interaction: discord.Interaction):
    if is_server_blacklisted(interaction.guild.id):
        await handle_blacklisted_server(interaction)
        return
    user_id = interaction.user.id

    if not has_started_game(user_id):
        await prompt_start_game(interaction)
        return

    if debug_mode:
        profile = load_or_create_temp_profile(user_id)
    else:
        profile = load_or_create_profile(user_id)
    
    # Ensure all necessary fields are present in the profile
    required_fields = ["trap_house_name", "balance", "income_per_hour", "rolling_skill", "current_joints", "total_joints_rolled", "trap_house_age", "start_date"]
    for field in required_fields:
        if field not in profile:
            profile[field] = 0 if field != "trap_house_name" else "My First Trap"
    
    embed = discord.Embed(title=f"{interaction.user.name}'s Profile", color=discord.Color.green())
    embed.add_field(name="Trap House Name", value=profile['trap_house_name'], inline=False)
    embed.add_field(name="Balance", value=f"${profile['balance']}", inline=False)
    embed.add_field(name="Income per Hour", value=f"${profile['income_per_hour']}", inline=False)
    embed.add_field(name="Rolling Skill Level", value=profile['rolling_skill'], inline=False)
    embed.add_field(name="Current Joints", value=profile['current_joints'], inline=False)
    embed.add_field(name="Total Joints Rolled", value=profile['total_joints_rolled'], inline=False)
    embed.add_field(name="Trap House Age", value=f"{profile['trap_house_age']} days (Started: <t:{int(datetime.fromisoformat(profile['start_date']).timestamp())}:D>)", inline=False)
    await interaction.response.send_message(embed=embed)

# Dictionary to store user cooldowns
user_cooldowns = {}

# Dictionary to store original profiles before maintenance mode
original_profiles = {}

# Dictionary to store temporary profiles during maintenance mode
temp_profiles = {}

class RollMoreButton(ui.Button):
    def __init__(self):
        super().__init__(label="Roll more", style=ButtonStyle.green)

    async def callback(self, interaction: Interaction):
        await roll.callback(interaction)  # Use the callback method of the command

# Command to roll some J's
@bot.tree.command(name="roll", description="Roll some J's.")
async def roll(interaction: discord.Interaction):
    if is_server_blacklisted(interaction.guild.id):
        await handle_blacklisted_server(interaction)
        return
    user_id = interaction.user.id

    if not has_started_game(user_id):
        await prompt_start_game(interaction)
        return

    now = datetime.now()

    if not debug_mode:
        # Check if the user is on cooldown
        if user_id in user_cooldowns:
            cooldown_end = user_cooldowns[user_id]
            if now < cooldown_end:
                seconds_left = int((cooldown_end - now).total_seconds())
                embed = discord.Embed(
                    title="Cooldown Active",
                    description=f"You can't roll that fast! You can roll again in <t:{int(cooldown_end.timestamp())}:R>.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

    if debug_mode:
        profile = load_or_create_temp_profile(user_id)
    else:
        profile = load_or_create_profile(user_id)
    
    rolled_js = random.randint(1, 5) * profile['rolling_skill']  # Use rolling skill to determine the number of J's rolled
    profile['current_joints'] += rolled_js
    profile['total_joints_rolled'] += rolled_js

    if not debug_mode:
        save_profile(user_id, profile)
    else:
        temp_profiles[user_id] = profile

    view = ui.View()
    view.add_item(RollMoreButton())

    maintenance_message = " The bot is in maintenance mode and your game statistics will not be saved. When this message disappears, your stats will be saving again." if debug_mode else ""
    embed = discord.Embed(
        title="Rolling J's",
        description=f"You rolled {rolled_js} J's! You now have a total of {profile['current_joints']} J's.{maintenance_message}",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, view=view)

# Command to sell J's
@bot.tree.command(name="sell", description="Sell your J's.")
async def sell(interaction: discord.Interaction):
    if is_server_blacklisted(interaction.guild.id):
        await handle_blacklisted_server(interaction)
        return
    user_id = interaction.user.id

    if not has_started_game(user_id):
        await prompt_start_game(interaction)
        return

    if debug_mode:
        profile = load_or_create_temp_profile(user_id)
    else:
        profile = load_or_create_profile(user_id)
    
    sold_js = profile['current_joints']
    base_price = 5
    sale_price = base_price * (1 + profile['rolling_skill'] * 0.10)
    earnings = sold_js * sale_price
    profile['balance'] += earnings
    profile['current_joints'] = 0

    if not debug_mode:
        save_profile(user_id, profile)
    else:
        temp_profiles[user_id] = profile

    await interaction.response.send_message(f"You sold {sold_js} J's for ${earnings:.2f}!")

# Command to upgrade rolling skill
@bot.tree.command(name="upgrade_rolling_skill", description="Upgrade your rolling skill.")
async def upgrade_rolling_skill(interaction: discord.Interaction):
    if is_server_blacklisted(interaction.guild.id):
        await handle_blacklisted_server(interaction)
        return
    user_id = interaction.user.id

    if not has_started_game(user_id):
        await prompt_start_game(interaction)
        return

    if debug_mode:
        profile = load_or_create_temp_profile(user_id)
    else:
        profile = load_or_create_profile(user_id)
    
    current_skill = profile['rolling_skill']
    if current_skill >= 100:
        await interaction.response.send_message("Your rolling skill is already at the maximum level.", ephemeral=True)
        return

    cost = 100 * (1.15 ** current_skill)
    next_cost = 100 * (1.15 ** (current_skill + 1))

    if profile['balance'] >= cost:
        profile['balance'] -= cost
        profile['rolling_skill'] += 1
        new_skill = profile['rolling_skill']
        new_range = f"{new_skill} to {new_skill * 5} J's"

        if not debug_mode:
            save_profile(user_id, profile)
        else:
            temp_profiles[user_id] = profile

        embed = discord.Embed(
            title="Rolling Skill Upgraded",
            description=(
                f"Rolling skill upgraded to level {new_skill}!\n"
                f"New range of J's you can roll: {new_range}\n"
                f"Amount spent: ${cost:.2f}\n"
                f"Next upgrade cost: ${next_cost:.2f}"
            ),
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"Not enough balance to upgrade. You need ${cost:.2f}.", ephemeral=True)

# Command to upgrade trap house
@bot.tree.command(name="upgrade_trap_house", description="Upgrade your trap house.")
async def upgrade_trap_house(interaction: discord.Interaction):
    if is_server_blacklisted(interaction.guild.id):
        await handle_blacklisted_server(interaction)
        return
    user_id = interaction.user.id

    if not has_started_game(user_id):
        await prompt_start_game(interaction)
        return

    if debug_mode:
        profile = load_or_create_temp_profile(user_id)
    else:
        profile = load_or_create_profile(user_id)
    
    current_level = profile.get('trap_house_level', 0)
    if current_level >= 100:
        await interaction.response.send_message("Your trap house is already at the maximum level.", ephemeral=True)
        return

    cost = 500 * (1.20 ** current_level)
    next_cost = 500 * (1.20 ** (current_level + 1))

    if profile['balance'] >= cost:
        profile['balance'] -= cost
        profile['trap_house_level'] = current_level + 1
        profile['income_per_hour'] *= 1.10  # Increase income per hour by 10%

        if not debug_mode:
            save_profile(user_id, profile)
        else:
            temp_profiles[user_id] = profile

        await interaction.response.send_message(f"Trap house upgraded! Income per hour is now ${profile['income_per_hour']:.2f}. Next upgrade will cost ${next_cost:.2f}.")
    else:
        await interaction.response.send_message(f"Not enough balance to upgrade. You need ${cost:.2f}.", ephemeral=True)

# Command for daily check-in bonus
@bot.tree.command(name="daily", description="Claim your daily check-in bonus.")
async def daily(interaction: discord.Interaction):
    if is_server_blacklisted(interaction.guild.id):
        await handle_blacklisted_server(interaction)
        return
    user_id = interaction.user.id

    if not has_started_game(user_id):
        await prompt_start_game(interaction)
        return

    if debug_mode:
        profile = load_or_create_temp_profile(user_id)
    else:
        profile = load_or_create_profile(user_id)
    
    last_check_in = datetime.fromisoformat(profile['last_check_in'])
    now = datetime.now()
    if (now - last_check_in).days >= 1:
        base_reward = 100
        bonus = profile.get('trap_house_level', 0) * 10
        total_reward = base_reward + bonus
        profile['balance'] += total_reward
        profile['last_check_in'] = now.isoformat()

        if not debug_mode:
            save_profile(user_id, profile)
        else:
            temp_profiles[user_id] = profile

        await interaction.response.send_message(f"Daily check-in bonus claimed! You received ${total_reward:.2f}.")
    else:
        next_check_in = last_check_in + timedelta(days=1)
        await interaction.response.send_message(f"You have already claimed your daily bonus. Come back <t:{int(next_check_in.timestamp())}:R>!")

# Command to show balance
@bot.tree.command(name="balance", description="Show your current balance.")
async def balance(interaction: discord.Interaction):
    if is_server_blacklisted(interaction.guild.id):
        await handle_blacklisted_server(interaction)
        return
    user_id = interaction.user.id

    if not has_started_game(user_id):
        await prompt_start_game(interaction)
        return

    if debug_mode:
        profile = load_or_create_temp_profile(user_id)
    else:
        profile = load_or_create_profile(user_id)
    
    embed = discord.Embed(
        title=f"{interaction.user.name}'s Balance",
        description=f"Your current balance is ${profile['balance']}.",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

# Command to view the shop
@bot.tree.command(name="shop", description="View available upgrades in the shop.")
async def shop(interaction: discord.Interaction):
    if is_server_blacklisted(interaction.guild.id):
        await handle_blacklisted_server(interaction)
        return
    user_id = interaction.user.id

    if not has_started_game(user_id):
        await prompt_start_game(interaction)
        return

    shop_config = load_or_create_shop_config()
    upgrades = shop_config.get("upgrades", {})
    
    embed = discord.Embed(title="Shop - Upgrades", color=discord.Color.blue())
    for upgrade_name, upgrade_info in upgrades.items():
        embed.add_field(
            name=upgrade_name,
            value=f"Cost: ${upgrade_info['cost']}\nIncome per Hour: ${upgrade_info['income_per_hour']}",
            inline=False
        )
    await interaction.response.send_message(embed=embed)

# Helper function to calculate the cost and income boost for an upgrade
def calculate_upgrade_cost_and_boost(upgrade_name, current_purchases):
    shop_config = load_or_create_shop_config()
    upgrade_info = shop_config["upgrades"].get(upgrade_name, {})
    initial_cost = upgrade_info.get("cost", 0)
    initial_income_boost = upgrade_info.get("income_per_hour", 0)
    cost_multiplier = upgrade_info.get("cost_multiplier", 1)
    income_boost_factor = upgrade_info.get("income_boost_factor", 1)

    new_cost = initial_cost * (cost_multiplier ** current_purchases)
    new_income_boost = initial_income_boost * (income_boost_factor ** current_purchases)

    return new_cost, new_income_boost

def find_closest_upgrade(upgrade_name, upgrades):
    upgrade_name = upgrade_name.lower()
    closest_match = None
    min_distance = float('inf')
    for name in upgrades:
        distance = sum(1 for a, b in zip(upgrade_name, name.lower()) if a != b) + abs(len(upgrade_name) - len(name))
        if distance < min_distance:
            min_distance = distance
            closest_match = name
    return closest_match

class PaymentModeButton(ui.Button):
    def __init__(self, label, style, user_id, current_mode):
        super().__init__(label=label, style=style)
        self.user_id = user_id
        self.current_mode = current_mode

    async def callback(self, interaction: Interaction):
        new_mode = "lump_sum" if self.label == "Lump Sum" else "over_time"
        if new_mode == "lump_sum" and self.current_mode == "over_time":
            await interaction.response.send_message(
                "Your payment mode will change to Lump Sum at the top of the hour.", ephemeral=True
            )
        else:
            settings = load_or_create_user_settings(self.user_id)
            settings["payment_mode"] = new_mode
            save_user_settings(self.user_id, settings)
            await interaction.response.send_message(f"Payment mode set to {self.label}.", ephemeral=True)

class UserSettingsView(ui.View):
    def __init__(self, user_id, current_mode):
        super().__init__(timeout=180)  # 3 minutes timeout for interaction
        self.user_id = user_id
        self.current_mode = current_mode

        lump_sum_style = ButtonStyle.green if current_mode == "lump_sum" else ButtonStyle.grey
        over_time_style = ButtonStyle.green if current_mode == "over_time" else ButtonStyle.grey

        self.add_item(PaymentModeButton("Lump Sum", lump_sum_style, user_id, current_mode))
        self.add_item(PaymentModeButton("Over Time", over_time_style, user_id, current_mode))

@bot.tree.command(name="usersettings", description="Configure your payment settings.")
async def usersettings(interaction: discord.Interaction):
    if is_server_blacklisted(interaction.guild.id):
        await handle_blacklisted_server(interaction)
        return
    user_id = interaction.user.id
    settings = load_or_create_user_settings(user_id)
    current_mode = settings.get("payment_mode", "over_time")

    embed = discord.Embed(
        title="User Settings",
        description="Choose your payment mode:",
        color=discord.Color.blue()
    )
    embed.add_field(name="Lump Sum", value="Get paid your full hourly pay at the top of each hour.", inline=False)
    embed.add_field(name="Over Time", value="Get paid your full hourly pay gradually over the course of the hour.", inline=False)

    view = UserSettingsView(user_id, current_mode)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    # Command to toggle maintenance mode
@bot.tree.command(name="maintenance", description="This command is restricted to @Wubbity - Puts bot in maintenance mode.")
async def maintenance(interaction: discord.Interaction):
    if is_server_blacklisted(interaction.guild.id):
        await handle_blacklisted_server(interaction)
        return
    if not (is_developer(interaction) or interaction.guild.id == master_server_id):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    global debug_mode
    debug_mode = not debug_mode
    global_config["debug"] = debug_mode

    # Save the updated debug mode to config.json
    with open(config_path, 'w') as f:
        json.dump(global_config, f, indent=4)

    if not debug_mode:
        # Restore original profiles
        for user_id, original_profile in original_profiles.items():
            save_profile(user_id, original_profile)
        original_profiles.clear()
        temp_profiles.clear()

    status = "enabled" if debug_mode else "disabled"
    await interaction.response.send_message(f"Maintenance mode {status}.", ephemeral=True)

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

class BuyUpgradeButton(ui.Button):
    def __init__(self, upgrade_name, user_id, row):
        super().__init__(label=f"Buy {upgrade_name}", style=ButtonStyle.green, row=row)
        self.upgrade_name = upgrade_name
        self.user_id = user_id

    async def callback(self, interaction: Interaction):
        await handle_buy_upgrade(interaction, self.upgrade_name)

class BuyAgainButton(ui.Button):
    def __init__(self, upgrade_name, user_id, row):
        super().__init__(label=f"Buy {upgrade_name} Again", style=ButtonStyle.blurple, row=row)
        self.upgrade_name = upgrade_name
        self.user_id = user_id

    async def callback(self, interaction: Interaction):
        await handle_buy_upgrade(interaction, self.upgrade_name)

class UpgradesView(ui.View):
    def __init__(self, user_id, upgrades, profile):
        super().__init__(timeout=180)  # 3 minutes timeout for interaction
        self.user_id = user_id
        self.upgrades = upgrades
        self.profile = profile

        for idx, (upgrade_name, upgrade_info) in enumerate(upgrades.items()):
            row = idx // 2  # 2 buttons per row
            self.add_item(BuyUpgradeButton(upgrade_name, user_id, row=row))

@bot.tree.command(name="upgrades", description="View and purchase available upgrades.")
async def upgrades(interaction: discord.Interaction):
    if is_server_blacklisted(interaction.guild.id):
        await handle_blacklisted_server(interaction)
        return
    user_id = interaction.user.id

    if not has_started_game(user_id):
        await prompt_start_game(interaction)
        return

    if debug_mode:
        profile = load_or_create_temp_profile(user_id)
    else:
        profile = load_or_create_profile(user_id)
    
    shop_config = load_or_create_shop_config()
    upgrades = shop_config.get("upgrades", {})

    embed = discord.Embed(title="Available Upgrades", color=discord.Color.blue())
    for upgrade_name, upgrade_info in upgrades.items():
        cost = upgrade_info["cost"]
        income_per_hour = upgrade_info["income_per_hour"]
        embed.add_field(
            name=upgrade_name,
            value=f"Cost: ${cost}\nIncome per Hour: +${income_per_hour}",
            inline=False
        )
    embed.add_field(name="Current Balance", value=f"${profile['balance']}", inline=False)

    view = UpgradesView(user_id, upgrades, profile)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class LeaderboardButton(ui.Button):
    def __init__(self, label, style, sort_key, is_global, interaction):
        super().__init__(label=label, style=style)
        self.sort_key = sort_key
        self.is_global = is_global
        self.interaction = interaction

    async def callback(self, interaction: Interaction):
        await display_leaderboard(interaction, self.sort_key, self.is_global)

class LeaderboardView(ui.View):
    def __init__(self, interaction, sort_key, is_global):
        super().__init__(timeout=180)  # 3 minutes timeout for interaction
        self.interaction = interaction
        self.sort_key = sort_key
        self.is_global = is_global

        self.add_item(LeaderboardButton("Balance", ButtonStyle.blurple, "balance", is_global, interaction))
        self.add_item(LeaderboardButton("Income per Hour", ButtonStyle.blurple, "income_per_hour", is_global, interaction))
        self.add_item(LeaderboardButton("Rolling Skill", ButtonStyle.blurple, "rolling_skill", is_global, interaction))
        self.add_item(LeaderboardButton("Current Joints", ButtonStyle.blurple, "current_joints", is_global, interaction))
        self.add_item(LeaderboardButton("Total Joints Rolled", ButtonStyle.blurple, "total_joints_rolled", is_global, interaction))
        self.add_item(LeaderboardButton("Toggle Local/Global", ButtonStyle.green, sort_key, not is_global, interaction))

async def display_leaderboard(interaction: discord.Interaction, sort_key: str, is_global: bool):
    profiles = []
    if is_global:
        for filename in os.listdir(GAME_FOLDER):
            if filename.endswith(".json"):
                user_id = filename.split(".")[0]
                if user_id.isdigit():  # Ensure the user_id is a valid integer
                    profile = load_or_create_profile(user_id)
                    profiles.append((user_id, profile))
    else:
        guild = interaction.guild
        for member in guild.members:
            if not member.bot:
                user_id = str(member.id)
                profile_path = os.path.join(GAME_FOLDER, f"{user_id}.json")
                if os.path.exists(profile_path):
                    profile = load_or_create_profile(user_id)
                    profiles.append((user_id, profile))

    sorted_profiles = sorted(profiles, key=lambda x: x[1].get(sort_key, 0), reverse=True)
    embed = discord.Embed(title=f"Leaderboard - {sort_key.replace('_', ' ').title()} ({'Global' if is_global else 'Local'})", color=discord.Color.blue())

    for idx, (user_id, profile) in enumerate(sorted_profiles[:10], start=1):
        user = interaction.guild.get_member(int(user_id)) if not is_global else bot.get_user(int(user_id))
        if user:  # Ensure the user exists
            embed.add_field(name=f"{idx}. {user.name}", value=f"{sort_key.replace('_', ' ').title()}: {profile.get(sort_key, 0)}", inline=False)

    view = LeaderboardView(interaction, sort_key, is_global)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="leaderboard", description="View the game leaderboard.")
async def leaderboard(interaction: discord.Interaction):
    if is_server_blacklisted(interaction.guild.id):
        await handle_blacklisted_server(interaction)
        return
    await display_leaderboard(interaction, "balance", is_global=False)

# Command to rename the trap house
@bot.tree.command(name="rename", description="Rename your trap house.")
@app_commands.describe(new_name="The new name for your trap house.")
async def rename(interaction: discord.Interaction, new_name: str):
    if is_server_blacklisted(interaction.guild.id):
        await handle_blacklisted_server(interaction)
        return
    user_id = interaction.user.id

    if not has_started_game(user_id):
        await prompt_start_game(interaction)
        return

    if debug_mode:
        profile = load_or_create_temp_profile(user_id)
    else:
        profile = load_or_create_profile(user_id)

    profile['trap_house_name'] = new_name

    if not debug_mode:
        save_profile(user_id, profile)
    else:
        temp_profiles[user_id] = profile

    await interaction.response.send_message(f"Your trap house has been renamed to: {new_name}")

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
                await log_action(
                    guild, "Test Join Voice Channel",
                    f"Joined **{voice_channel.name}** at {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC. (Test command by developer)",
                    interaction.user
                )
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
        embed.add_field(name="Empty", value="\n".join([f"{guild.name} (ID: {guild.id}) | Owner: {guild.owner}" for guild in empty_list]) or "[None]", inline=False)
        embed.add_field(name="Total Servers", value=f"{len(bot.guilds)}", inline=False)
        await log_channel.send(embed=embed)

    await interaction.followup.send("Test command completed. Check logs for details.", ephemeral=True)

class UpdateEmbedView(ui.View):
    def __init__(self, embed, interaction):
        super().__init__(timeout=30)  # 30 seconds timeout for interaction
        self.embed = embed
        self.interaction = interaction

    @ui.button(label="Send", style=ButtonStyle.green)
    async def send_button(self, interaction: Interaction, button: ui.Button):
        await self.send_update_to_all_servers()
        await interaction.response.send_message("Update sent to all servers.", ephemeral=True)

    async def send_update_to_all_servers(self):
        for guild in bot.guilds:
            server_config = load_or_create_server_config(guild.id)
            log_channel_id = server_config.get('log_channel_id')
            if log_channel_id:
                log_channel = bot.get_channel(log_channel_id)
                if log_channel:
                    await log_channel.send(embed=self.embed)

    async def on_timeout(self):
        await self.interaction.edit_original_response(content="The update was not sent due to timeout.", embed=None, view=None)

@bot.tree.command(name="update", description="Send an update message to all servers. Developer only.")
async def update(interaction: discord.Interaction):
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

        view = UpdateEmbedView(embed, interaction)
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

bot.run(BOT_TOKEN)

