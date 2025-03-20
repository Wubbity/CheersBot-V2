# CheersBot V2

The Public Version of CheersBot - A complete rewrite!

## Table of Contents

- [Introduction](#introduction)
- [Features](#features)
- [Commands](#commands)
  - [/setup](#setup)
  - [/sounds](#sounds)
  - [/mode](#mode)
  - [/setup-info](#setup-info)
  - [/cheers](#cheers)
  - [/blacklist](#blacklist)
  - [/permissions](#permissions)
  - [/cheers-count](#cheers-count)
  - [/meetthedev](#meetthedev)
  - [/partners](#partners)
  - [/feedback](#feedback)
  - [/uptime](#uptime)
- [Developer Commands](#developer-commands)
  - [/server-blacklist](#server-blacklist)
  - [/feedback-ban](#feedback-ban)
  - [/reload](#reload)
  - [/update](#update)
  - [/test](#test)
  - [c.sync](#csync)
  - [partners_edit](#partners_edit)
  - [DM_ban](#dm_ban)
  - [DM_unban](#dm_unban)
  - [DM_toggle](#dm_toggle)
- [Configuration](#configuration)
- [Logging](#logging)
- [Developer Information](#developer-information)
- [Installation](#installation)
- [Contributing](#contributing)
- [Support](#support)

## Introduction

CheersBot V2 is a Discord bot designed to bring fun and utility to your server. It can join voice channels to play sounds, manage server-specific configurations, log actions, and provide detailed feedback mechanisms. Built with Python and the Discord.py library, it’s highly customizable and packed with features for both users and developers.

## Features

- Automatically joins voice channels and plays sounds at configurable times (e.g., every hour at X:15 or at 4:20 in specified timezones).
- Supports two sound modes: `single` (plays a default sound) or `random` (selects from enabled sounds).
- Configurable server settings, including log channels, admin roles, and blacklisted channels.
- Detailed logging system with server lists and action logs.
- Feedback system allowing users to submit text, images, and audio files to developers.
- Blacklist management for servers and channels.
- Partner server showcase with dynamic member counts.
- Developer tools for testing, updating, and managing the bot across all servers.
- Direct message (DM) handling with ban and toggle options.
- Permissions checker to ensure proper bot setup.
- Cheers count tracking (global and local).

## Commands

### /setup

**Description**: Initializes the bot for your server by setting up logging and admin roles.

**Usage**: `/setup channel:<TextChannel>`

**Permissions**: Administrator

**Steps**:
1. Specify a text channel for logging bot actions.
2. Assign admin roles for managing bot settings.

### /sounds

**Description**: Manage available sounds for the server. In `random` mode, enable/disable sounds; in `single` mode, view the default sound.

**Usage**: `/sounds`

### /mode

**Description**: Switch between `single` (one default sound) and `random` (randomly selected enabled sounds) modes.

**Usage**: `/mode mode:<single|random>`

**Permissions**: Administrator

### /setup-info

**Description**: Displays the current bot configuration for the server, including log channel, admin roles, mode, and join frequency.

**Usage**: `/setup-info`

### /cheers

**Description**: Manually triggers the bot to join a specified voice channel and play a sound.

**Usage**: `/cheers channel:<VoiceChannel>`

### /blacklist

**Description**: Manage a list of voice channels the bot won’t auto-join.

**Usage**: `/blacklist action:<add|remove|list> channel:<VoiceChannel>`

**Permissions**: Administrator

### /permissions

**Description**: Checks the bot’s permissions in the server and highlights missing ones.

**Usage**: `/permissions`

### /cheers-count

**Description**: Shows the total number of cheers played globally and locally, including breakdowns for automated and manual triggers, and sound-specific counts.

**Usage**: `/cheers-count`

### /meetthedev

**Description**: Provides information about the bot’s developers and links to their Discord and website.

**Usage**: `/meetthedev`

### /partners

**Description**: Lists partner servers with invite links, member counts, and owner details.

**Usage**: `/partners`

### /feedback

**Description**: Allows users to send feedback, images, or audio files (.mp3, .m4a, .wav, .ogg) to developers for review.

**Usage**: `/feedback`

### /uptime

**Description**: Allows users to check how long the bot has been online for as well as the longest uptime.

**Usage**: `/uptime`

## Developer Commands

These commands are restricted to developers listed in `config.json`.

### /server-blacklist

**Description**: Manages the server blacklist (add, remove, or list).

**Usage**: `/server-blacklist action:<add|remove|list> server_id:<ServerID> reason:<Reason>`

### /feedback-ban

**Description**: Bans a user from using the `/feedback` command.

**Usage**: `/feedback-ban user:<User> reason:<Reason>`

### /reload

**Description**: Reloads and syncs all commands globally.

**Usage**: `/reload`

### /update

**Description**: Sends an update message to a specific server or all servers.

**Usage**: `/update server_id:<ServerID>`

### /test

**Description**: Manually triggers the bot to join and play sounds in all servers’ most populated voice channels for testing.

**Usage**: `/test`

### c.sync

**Description**: Syncs commands globally and updates the server list.

**Usage**: `c.sync`

**Prefix**: `c.`

### partners_edit

**Description**: Adds or removes servers from the partners list.

**Usage**: `c.partners_edit action:<add|remove>`

**Prefix**: `c.`

### DM_ban

**Description**: Bans a user from sending DMs to the bot.

**Usage**: `c.DM_ban`

**Prefix**: `c.`

### DM_unban

**Description**: Unbans a user from sending DMs to the bot.

**Usage**: `c.DM_unban`

**Prefix**: `c.`

### DM_toggle

**Description**: Toggles DM functionality globally with an optional reason.

**Usage**: `c.DM_toggle`

**Prefix**: `c.`

## Configuration

CheersBot uses a global `config.json` file and server-specific `config_<guild_id>.json` files. Below is an example of each:

### Global Config (`config.json`)

```json
{
    "bot_developer_ids": ["171091643510816768"],
    "master_server_id": "YOUR_MASTER_SERVER_ID",
    "developer_dm_channel_id": "1315133468337770578",
    "developer_dm_role_id": "YOUR_ROLE_ID",
    "discord_link": "https://discord.gg/HomiesHouse",
    "website": "https://HomiesHouse.net",
    "log_settings": {
        "footer_text": "CheersBot V2.0 by HomiesHouse | Discord.gg/HomiesHouse",
        "footer_icon_url": "https://i.imgur.com/4OO5wh0.png",
        "thumbnail_url": "https://i.imgur.com/4OO5wh0.png"
    },
    "debug": true
}
```

### Server Config (`config_<guild_id>.json`)

```json
{
    "log_channel_id": 801086900403306527,
    "admin_roles": [329836453561630720],
    "mode": "random",
    "default_sound": "cheers_bitch.mp3",
    "blacklist_channels": [],
    "local_cheers_count": 42,
    "join_frequency": "every_hour",
    "join_timezones": []
}
```

- Replace placeholders like `YOUR_MASTER_SERVER_ID` and `YOUR_ROLE_ID` with actual values.
- Environment variables (e.g., `DISCORD_BOT_TOKEN`, `MASTER_GUILD_ID`) are loaded via a `.env` file.

## Logging

CheersBot maintains detailed logs in the `server_logs` directory:

- `ServerList.log`: Current list of servers with details like member counts and invites.
- `MASTERServerList.log`: Historical log of server joins/leaves with summaries.
- `FeedbackBans.json`: List of users banned from feedback.
- `BlacklistedServers.json`: List of blacklisted servers.
- `DM_Bans.json`: List of users banned from DMing the bot.
- `DM_Global_Toggle.json`: DM toggle status and reason.
- `ConsoleLogs/YYYY-MM-DD.log`: Daily console logs.

Server-specific actions are logged to the configured log channel.

## Developer Information

Developed by the HomiesHouse team. Contact us via:

- Discord: [Discord.gg/HomiesHouse](https://discord.gg/HomiesHouse)
- Website: [HomiesHouse.net](https://HomiesHouse.net)

Developer IDs are defined in `config.json` under `bot_developer_ids`.

## Installation

1. **Prerequisites**:
   - Python 3.8+
   - FFmpeg installed (Windows: place in `FFMPEG/` folder; Linux: ensure in PATH or `FFMPEG/` folder)
   - Discord bot token

2. **Setup**:
   ```bash
   git clone https://github.com/yourusername/CheersBotV2.git
   cd CheersBotV2
   pip install -r requirements.txt
   ```

3. **Configuration**:
   - Create a `.env` file with:
     ```
     DISCORD_BOT_TOKEN=your_token_here
     MASTER_GUILD_ID=your_master_guild_id
     ```
   - Edit `config.json` with your settings.

4. **Run**:
   ```bash
   python bot.py
   ```

## Contributing

Contributions are welcome! Please:

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/YourFeature`).
3. Commit your changes (`git commit -m "Add YourFeature"`).
4. Push to the branch (`git push origin feature/YourFeature`).
5. Open a pull request.

For feedback or audio submissions, use the `/feedback` command in Discord.

## Support

For issues or questions, join our Discord server: [Discord.gg/HomiesHouse](https://discord.gg/HomiesHouse).

---

CheersBot V2.0 by HomiesHouse | [Discord.gg/HomiesHouse](https://discord.gg/HomiesHouse)
