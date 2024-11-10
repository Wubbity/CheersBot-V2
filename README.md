# CheersBot V2

The Public Version of CheersBot - A complete rewrite!

## Table of Contents

- [Introduction](#introduction)
- [Features](#features)
- [Commands](#commands)
  - [/setup](#setup)
  - [/join](#join)
  - [/leave](#leave)
  - [/sounds](#sounds)
  - [/mode](#mode)
  - [/reload](#reload)
  - [/setup-info](#setup-info)
  - [/cheers](#cheers)
- [Configuration](#configuration)
- [Logging](#logging)
- [Developer Information](#developer-information)

## Introduction

CheersBot V2 is a Discord bot designed to enhance your server with fun and useful features. It includes functionalities like playing sounds in voice channels, logging actions, and more.

## Features

- Join and leave voice channels.
- Play sounds in voice channels.
- Configure bot settings per server.
- Log actions to a specified channel.
- Admin role management.
- Developer-specific commands.

## Commands

### /setup

**Description**: Set up the bot for this server.

**Usage**: `/setup channel:<TextChannel>`

**Permissions**: Administrator

**Steps**:
1. Set the logging channel.
2. Provide admin role IDs.
3. Choose the bot mode (`single` or `random`).

### /join

**Description**: Make the bot join a voice channel.

**Usage**: `/join channel:<VoiceChannel>`

### /leave

**Description**: Make the bot leave the voice channel.

**Usage**: `/leave`

### /sounds

**Description**: Enable or disable available sounds for this server.

**Usage**: `/sounds`

### /mode

**Description**: Change the bot's mode for this server.

**Usage**: `/mode mode:<single|random>`

**Permissions**: Administrator

### /reload

**Description**: Reload commands for this server.

**Usage**: `/reload`

### /setup-info

**Description**: Display the current bot settings for this server.

**Usage**: `/setup-info`

### /cheers

**Description**: Play the cheers sound in a voice channel.

**Usage**: `/cheers channel:<VoiceChannel>`

## Configuration

The bot uses a configuration file (`config.json`) to store global settings. Here is an example configuration:

```json
{
    "bot_developer_ids": [
        "YOUR_DEVELOPER_ID_1",
        "YOUR_DEVELOPER_ID_2"
    ],
    "log_settings": {
        "footer_text": "CheersBot V2.0 by HomiesHouse | Discord.gg/HomiesHouse",
        "footer_icon_url": "https://i.imgur.com/4OO5wh0.png",
        "thumbnail_url": "https://i.imgur.com/4OO5wh0.png"
    },
    "default_sound": "YOUR_CHEERS_SOUND.mp3",
    "debug": true,
    "master_server_id": "YOUR_MASTER_SERVER_ID"
}
```

Ensure you replace placeholders like `YOUR_DEVELOPER_ID_1`, `YOUR_DEVELOPER_ID_2`, `YOUR_CHEERS_SOUND.mp3` and `YOUR_MASTER_SERVER_ID` with your actual IDs.

## Logging

The bot logs actions to a specified channel and maintains server logs in the `server_logs` directory. The logs include:

- `ServerList.log`: List of servers the bot has joined.
- `MASTERServerList.log`: Detailed log of actions related to the master server.

## Developer Information

The bot includes developer-specific functionalities and commands. Developer IDs are specified in the `config.json` file.

For any issues or support, please reach out to the support team at [Discord.gg/HomiesHouse](https://discord.gg/HomiesHouse).

---

CheersBot V2.0 by HomiesHouse | [Discord.gg/HomiesHouse](https://discord.gg/HomiesHouse)

