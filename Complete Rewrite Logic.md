I want to completely rewrite the discord bot. The bot should have simular functions. We'll name this CheersBot V2. The bot should be written in a way so one person can host the discord bot and it can join multiple discord servers and function the same way across all servers at the same time.

CheersBot V2 will have the following features.
___
Features:


# Main Dev Bot Stuff
Bot token: The bot token should be in the .env file.

Bot Dev ID: This ID will be given to the bot so provide FULL access over the bot within any server its in. If the Bot Dev has types a command in a server they do not have admin in, they should still be able to run all commands without fault. This allows developer invention if problems with the bot arise. Allow for multiple discord ID's to be put here. This should be in the config.json file.

Master Guild (Main Discord Server): There should be a config option (We'll use a config.json file) to determine the main bots server. This server (with the correct roles) will have bot administrator. We'll use discord guild ID for this. This should also be in the .env file.
___
Autojoin Function (Main Bot Function): Joins the most populated channel (In each/every discord that the bot is in at the same time). Play a "Cheers" sound. Then leave after the cheers sound is over. The bot should join every single hour at X:15, wait 5 minutes, then play the sound at X:20. The bot should be written in a way so that the sound can be any length and the bot will wait until the sound has completely played before leaving the channel.

Configs for seperate servers: There should be a seperate config aside from the main master guilds config. This config should be editable from whatever discord server the bot is sitting in. Only certain commands will be allowed from servers seperate from the master guild.

Command Access block: Block commands for those who are unable to run them. Commands should not show up if the user is not able to run the command.

Default Sound: A default .mp3 file should be able to be put into the config.json file. Setting this .mp3 will allow the bot to know what default sound should play when the bot joins any server.

Debug: The config.json file should have a Debug=true/false option. This option will enable or disable certain logs. We'll configure those logs later. While debug is enabled, on startup, the bot should list all servers its currently in along with the server ID next to its name. If the bot is in over 50 servers, It should only list the first 50 servers the bot has ever joined, and list ALL (Including the 50 listed in console) of the servers, server IDs, and when the bot joined the server in a file named ServerList.log.

Error Handling: The bot should be able to handle errors for each problem that may arise.

Per Server Logs: The bot should ask the user on /setup what channel the bot should log to. This channel should be the per-discord logs for each server. The bot should send a message in the form of an embed. The Embed Title should be "{ServerName} Cheers Bot Logs". The footer text should be configuarable in the config.json file. The Thumbnail image should be the icon as the server that the bot is sitting in. The thumbnail link should be configuarable in the config.json file. The Footer icon should be also configurable in the config.json file and it should be defaulted as "https://i.imgur.com/SKICBLv.png"

Commands:

    - /Setup [Channel] - Channel is where the bot will start the setup questions. Default permission for this command should be Discord Server Administrator. The setup questions should be as follows:
        - What discord channel do you want the bot to log to? (If any- Leave blank for none.) When setting this command, it should only log the actions that happen in the guild that the bot is in.
        - What role ID(s) should be allowed to use the admin bot commands.
            * Admin bot commands here refers to all commands that are only allowed in non-master discord server servers. Allow for multiple role IDs if the user wants.
        - What Mode should the bot start off in in your server?
            - Single (Plays the same sound every single X:20)
                If the user choses single during setup, the bot should use the default sound, enable it, and disable every other sound in the sounds folder from this specific server.
            - Random (Plays a random enabled sound every single X:20)
                If random is chosen during the /setup command, the bot should enable all sounds in the sounds folder, set the bot to random, and random mode should play a random sound on the auto join function.

    - /Join [Channel] (Should work seperately in all servers.) Example: If an admin in Main Server types /Join CHANNELNAME it should only join that channel name. Users should not be able to make a bot join a channel from one server to another server. An admin from Server 2 typing /Join CHANNELNAME (With a channel name thats in Server 3), should not join/be allowed. Admins should only be able to make the bot join from their own server. This comes with the exception of the bot Developers.

    - /Leave [Channel] (Should work seperately in all servers.) Example: If an admin in Server 1 types /Leave CHANNELNAME (A channel name from Server 2) - It should not allow the user to do so. It should only be able to /Leave channels in the server that the command was typed in.

    - /Cheers [Channel] [SOUNDNAME - If None, use single sound or pick random sound depending on mode.]- This command should make the bot join the channel listed, play the sound, then leave shortly after the sound completely plays.

    - /Sounds - This command should list all the sounds CheersBot has in the vault. Because CheersBot is able to be in multiple servers, we're still going to use all of the sounds in each server.

    - /Sounds [Enable/Disable] [SOUNDNAME] - This option should work indepentantly on all servers and only be allowed by server administrators and any role ID's listed during the /setup command. This command should enable specific sounds or disable specific sounds based on preferance. 

    - /Mode [Single/Random] [SOUNDNAME (Only for Single Option)]- This command should work independantly in all servers. It should only be accessable by server administrators and roles allowed within the /setup command. This command will allow the user to choose a different mode that CheersBot runs in. 
        - Single Mode: Single mode plays the same chosen sound every X:20.
        - Random Mode: Random mode plays a random enabled sound from the sounds folder every X:20.

    - /AutoJoin - This command should be a toggle. When the bot is invited to the server for the first time, auto join should always be enabled. If this command is typed by a server admin or a role ID that was allowed permissions in the /setup command - The bot will not join during the automatic times. Typing the command again should reenable the auto join function for this server.

    - /TestSound [Channel] [SOUNDNAME] - This command should be able to be used by server admins or roles allowed during /setup. This command makes the bot join a specific discord channel (within the server) and play a specific sound. This allows the server admins to listen to all of the sounds listed in the /sounds command since the .mp3's are hosted on my system.

    - /Reload - THIS IS A BOT DEV COMMAND ONLY. This command updates all command changes, bot changes, config.json changes, serverlist.log changes, ALL CHANGES and pushes it live to every server.