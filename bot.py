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

# Helper function to load or create a player profile
def load_or_create_profile(user_id):
    profile_path = os.path.join(GAME_FOLDER, f"{user_id}.json")
    if os.path.exists(profile_path):
        with open(profile_path, 'r') as f:
            return json.load(f)
    else:
        profile = {
            "trap_house_name": "My First Trap",
            "balance": 0,
            "income_per_hour": 0,
            "total_joints_rolled": 0,
            "rolling_skill": 1,
            "trap_house_age": 0,
            "last_check_in": datetime.now().isoformat()
        }
        save_profile(user_id, profile)
        return profile

# Helper function to save a player profile
def save_profile(user_id, profile):
    profile_path = os.path.join(GAME_FOLDER, f"{user_id}.json")
    with open(profile_path, 'w') as f:
        json.dump(profile, f, indent=4)

# Task to update trap house age and passive income
@tasks.loop(hours=1)
async def update_profiles_task():
    for filename in os.listdir(GAME_FOLDER):
        if filename.endswith(".json"):
            user_id = filename.split(".")[0]
            profile = load_or_create_profile(user_id)
            profile['trap_house_age'] += 1
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
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
    else:
        # Default configuration for new servers
        config = {
            "log_channel_id": None,
            "admin_roles": [],
            "mode": "single",  # Default mode is 'single'
            "default_sound": "cheers_bitch.mp3"
        }
        save_config(guild_id, config)

    # Ensure all keys exist in case config file is missing any of them
    config.setdefault("log_channel_id", None)
    config.setdefault("admin_roles", [])
    config.setdefault("mode", "single")
    config.setdefault("default_sound", "cheers_bitch.mp3")

    return config

def update_server_list():
    try:
        with open(SERVER_LIST_PATH, 'w') as f:
            for guild in bot.guilds:
                owner_id = guild.owner_id if guild.owner else "Unknown"
                total_members = guild.member_count
                total_bots = sum(1 for member in guild.members if member.bot)
                join_date = guild.me.joined_at.astimezone(pytz.timezone('America/Chicago')).strftime("%Y-%m-%d %H:%M:%S CST")
                f.write(f"{guild.name} (ID: {guild.id}) | Joined: {join_date} | Server Owner ID: {owner_id} | Total Members: {total_members} | Total Bots: {total_bots}\n")
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

bot = commands.Bot(command_prefix="!", intents=intents)

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

# Task to update trap house age and passive income
@tasks.loop(hours=1)
async def update_profiles_task():
    for filename in os.listdir(GAME_FOLDER):
        if filename.endswith(".json"):
            user_id = filename.split(".")[0]
            profile = load_or_create_profile(user_id)
            profile['trap_house_age'] += 1
            profile['balance'] += profile['income_per_hour']
            save_profile(user_id, profile)

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
    
    auto_join_task.start()  # Start the auto join task
    log_current_time_task.start()  # Start the time logging task
    update_profiles_task.start()  # Start the profile update task

    # Sync game commands
    await bot.tree.sync()

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
    update_server_list()
    await send_intro_message(guild)

@bot.event
async def on_guild_remove(guild):
    print(f"Left server: {guild.name} (ID: {guild.id})")
    update_server_list()

    # Log server removal with reason (if available)
    reason = "Kicked or Banned"  # Modify if you can track specific reasons
    log_to_master_server_list("Left", guild, reason=reason)

# Auto-Join Task
@tasks.loop(seconds=1)
async def auto_join_task():
    """Check every second and trigger at X:15:00 UTC to join voice channels and X:20:00 to play sound."""
    now = datetime.now(timezone.utc)
    if now.minute == 15 and now.second == 0:  # Trigger exactly at X:15:00
        await join_all_populated_voice_channels()
    elif now.minute == 20 and now.second == 0:  # Trigger exactly at X:20:00
        await play_sound_in_all_channels()

async def join_all_populated_voice_channels():
    """Join the most populated voice channels in all guilds concurrently."""
    tasks = []  # Store tasks for concurrent execution

    for guild in bot.guilds:
        voice_channel = max(
            (vc for vc in guild.voice_channels if len(vc.members) > 0),
            key=lambda vc: len(vc.members),
            default=None
        )
        if voice_channel:
            print(f"Scheduling join for {voice_channel.name} in {guild.name}...")
            tasks.append(join_voice_channel(guild, voice_channel, bot.user))  # Add join task

    if tasks:
        await asyncio.gather(*tasks)  # Run all join tasks concurrently

async def play_sound_in_all_channels():
    """Play the configured sound in all voice channels where the bot is connected."""
    tasks = []  # Store tasks for concurrent execution

    for guild in bot.guilds:
        if guild.voice_client and guild.voice_client.is_connected():
            tasks.append(play_sound_and_leave(guild, guild.voice_client, bot.user))  # Add play sound task

    if tasks:
        await asyncio.gather(*tasks)  # Run all play sound tasks concurrently

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

async def play_sound_and_leave(guild, vc, user):
    """Plays the configured sound for the guild and leaves the voice channel."""
    server_config = load_or_create_server_config(guild.id)
    mode = server_config.get("mode", "single")
    default_sound = server_config.get("default_sound", "cheers_bitch.mp3")
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
@bot.tree.command(name="setup", description="Set up the bot for this server.")
@commands.has_permissions(administrator=True)
@app_commands.describe(channel="The channel for logging actions.")
async def setup(interaction: discord.Interaction, channel: discord.TextChannel):
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


    try:
        # Step 2: Ask for Admin Roles
        await log_channel.send("Provide the role ID(s) for admin commands, separated by commas, or ping the roles.")
        try:
            role_msg = await bot.wait_for('message', timeout=60.0, check=check_message)
            role_ids = (
                [role.id for role in role_msg.role_mentions]
                or [int(r.strip()) for r in role_msg.content.split(",") if r.strip().isdigit()]
            )
            if not role_ids:
                await log_channel.send("No valid role IDs provided. Setup canceled.")
                return
            await log_channel.send(f"Admin roles set to: {', '.join(map(str, role_ids))}")
        except asyncio.TimeoutError:
            await log_channel.send("Setup timed out. Please run `/setup` again.")
            return

        # Step 3: Ask for Mode (Single or Random)
        await log_channel.send("What mode should the bot start with? Type `single` or `random`.")
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

        # Step 4: Save Configuration
        server_config = load_or_create_server_config(interaction.guild.id)
        server_config.update({
            'log_channel_id': log_channel_id,
            'admin_roles': role_ids,
            'mode': mode,
        })
        save_config(interaction.guild.id, server_config)

        # Confirmation Message
        await log_channel.send(
            f"Setup complete! Here's the summary:\n"
            f"Log Channel: <#{log_channel_id}>\n"
            f"Admin Roles: {', '.join(map(str, role_ids))}\n"
            f"Mode: {mode.capitalize()}"
        )
    except Exception as e:
        print(f"Error in setup: {e}")
        await log_channel.send(f"An error occurred: {e}")

@bot.tree.command(name="join", description="Make the bot join a voice channel.")
async def join(interaction: discord.Interaction, channel: discord.VoiceChannel):
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
    if not await ensure_setup(interaction):
        return
    server_config = load_or_create_server_config(interaction.guild.id)
    mode = server_config.get('mode', 'single')
    available_sounds = get_available_sounds()

    if mode == 'single':
        default_sound = server_config.get('default_sound', 'cheers_bitch.mp3')
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
@bot.tree.command(name="reload", description="Reload commands for this server.")
async def reload(interaction: discord.Interaction):
    if not await ensure_setup(interaction):
        return
    server_config = load_or_create_server_config(interaction.guild.id)
    admin_roles = server_config.get('admin_roles', [])

    # Load bot developer IDs from config.json
    with open(config_path, 'r') as f:
        global_config = json.load(f)
    developer_ids = global_config.get("bot_developer_ids", [])

    # Check if the user has permission to reload commands
    if not (
        interaction.user.guild_permissions.administrator
        or any(role.id in admin_roles for role in interaction.user.roles)
        or str(interaction.user.id) in developer_ids
    ):
        await interaction.response.send_message(
            "You do not have permission to use this command.", ephemeral=True
        )
        return

    # Acknowledge interaction early
    await interaction.response.defer(ephemeral=True)
    try:
        # Reload commands for the current guild
        await bot.tree.sync(guild=interaction.guild)
        await interaction.followup.send(
            f"Commands reloaded for {interaction.guild.name}.", ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(f"Failed to reload commands: {e}", ephemeral=True)

@bot.tree.command(name="setup-info", description="Display the current bot settings for this server.")
async def setup_info(interaction: discord.Interaction):
    if not await ensure_setup(interaction):
        return
    server_config = load_or_create_server_config(interaction.guild.id)
    
    log_channel_id = server_config.get('log_channel_id')
    admin_roles = server_config.get('admin_roles', [])
    mode = server_config.get('mode', 'single')
    default_sound = server_config.get('default_sound', 'cheers_bitch.mp3')

    log_channel = f"<#{log_channel_id}>" if log_channel_id else "Not set"
    admin_roles_mentions = ', '.join([f"<@&{role_id}>" for role_id in admin_roles]) if admin_roles else "None"
    sound = default_sound if mode == 'single' else "N/A"

    embed = discord.Embed(
        title=f"{interaction.guild.name} Bot Settings",
        color=discord.Color.blue()
    )
    embed.add_field(name="Logging Channel", value=log_channel, inline=False)
    embed.add_field(name="Admin Roles", value=admin_roles_mentions, inline=False)
    embed.add_field(name="Mode", value=mode.capitalize(), inline=False)
    if mode == 'single':
        embed.add_field(name="Sound", value=sound, inline=False)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="cheers", description="Play the cheers sound in a voice channel.")
@app_commands.describe(channel="The voice channel to join and play the sound.")
async def cheers(interaction: discord.Interaction, channel: discord.VoiceChannel):
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

# Command to start the game and create a profile
@bot.tree.command(name="start", description="Start the game and create your profile.")
async def start(interaction: discord.Interaction):
    user_id = interaction.user.id
    # Ensure the game folder exists
    if not os.path.exists(GAME_FOLDER):
        os.makedirs(GAME_FOLDER)
    profile = load_or_create_profile(user_id)
    await interaction.response.send_message(f"Welcome to the game! Your trap house name is {profile['trap_house_name']}.")

# Command to view the profile
@bot.tree.command(name="profile", description="View your game profile.")
async def profile(interaction: discord.Interaction):
    user_id = interaction.user.id
    profile = load_or_create_profile(user_id)
    embed = discord.Embed(title=f"{interaction.user.name}'s Profile", color=discord.Color.green())
    embed.add_field(name="Trap House Name", value=profile['trap_house_name'], inline=False)
    embed.add_field(name="Balance", value=f"${profile['balance']}", inline=False)
    embed.add_field(name="Income per Hour", value=f"${profile['income_per_hour']}", inline=False)
    embed.add_field(name="Rolling Skill Level", value=profile['rolling_skill'], inline=False)
    embed.add_field(name="Total Joints Rolled", value=profile['total_joints_rolled'], inline=False)
    embed.add_field(name="Trap House Age", value=f"{profile['trap_house_age']} days", inline=False)
    await interaction.response.send_message(embed=embed)

# Command to roll some J's
@bot.tree.command(name="roll", description="Roll some J's.")
async def roll(interaction: discord.Interaction):
    user_id = interaction.user.id
    profile = load_or_create_profile(user_id)
    rolled_js = random.randint(1, 5) * profile['rolling_skill']
    profile['total_joints_rolled'] += rolled_js
    save_profile(user_id, profile)
    await interaction.response.send_message(f"You rolled {rolled_js} J's!")

# Command to sell J's
@bot.tree.command(name="sell", description="Sell your J's.")
async def sell(interaction: discord.Interaction):
    user_id = interaction.user.id
    profile = load_or_create_profile(user_id)
    earnings = profile['total_joints_rolled'] * 5  # Base price $5 per J
    profile['balance'] += earnings
    profile['total_joints_rolled'] = 0
    save_profile(user_id, profile)
    await interaction.response.send_message(f"You sold your J's for ${earnings}!")

# Command to upgrade rolling skill
@bot.tree.command(name="upgrade_rolling_skill", description="Upgrade your rolling skill.")
async def upgrade_rolling_skill(interaction: discord.Interaction):
    user_id = interaction.user.id
    profile = load_or_create_profile(user_id)
    cost = profile['rolling_skill'] * 100  # Example scaling cost
    if profile['balance'] >= cost:
        profile['balance'] -= cost
        profile['rolling_skill'] += 1
        save_profile(user_id, profile)
        await interaction.response.send_message(f"Rolling skill upgraded to level {profile['rolling_skill']}!")
    else:
        await interaction.response.send_message(f"Not enough balance to upgrade. You need ${cost}.")

# Command to upgrade trap house
@bot.tree.command(name="upgrade_trap_house", description="Upgrade your trap house.")
async def upgrade_trap_house(interaction: discord.Interaction):
    user_id = interaction.user.id
    profile = load_or_create_profile(user_id)
    cost = (profile['income_per_hour'] + 1) * 500  # Example scaling cost
    if profile['balance'] >= cost:
        profile['balance'] -= cost
        profile['income_per_hour'] += 10  # Example income increase
        save_profile(user_id, profile)
        await interaction.response.send_message(f"Trap house upgraded! Income per hour is now ${profile['income_per_hour']}.")
    else:
        await interaction.response.send_message(f"Not enough balance to upgrade. You need ${cost}.")

# Command for daily check-in bonus
@bot.tree.command(name="daily_check_in", description="Claim your daily check-in bonus.")
async def daily_check_in(interaction: discord.Interaction):
    user_id = interaction.user.id
    profile = load_or_create_profile(user_id)
    last_check_in = datetime.fromisoformat(profile['last_check_in'])
    now = datetime.now()
    if (now - last_check_in).days >= 1:
        bonus = 100  # Example daily bonus
        profile['balance'] += bonus
        profile['last_check_in'] = now.isoformat()
        save_profile(user_id, profile)
        await interaction.response.send_message(f"Daily check-in bonus claimed! You received ${bonus}.")
    else:
        await interaction.response.send_message("You have already claimed your daily bonus. Come back tomorrow!")

# Task to update trap house age and passive income
@tasks.loop(hours=1)
async def update_profiles_task():
    for filename in os.listdir(GAME_FOLDER):
        if filename.endswith(".json"):
            user_id = filename.split(".")[0]
            profile = load_or_create_profile(user_id)
            profile['trap_house_age'] += 1
            profile['balance'] += profile['income_per_hour']
            save_profile(user_id, profile)

# Ensure the bot starts last
bot.run(BOT_TOKEN)