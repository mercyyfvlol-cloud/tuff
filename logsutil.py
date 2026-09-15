import logging

import discord

log = logging.getLogger("bot.logsutil")

LOGS_CHANNEL_ID = 1543459712731844768


async def send_log(bot, embed: discord.Embed):
    """Send an embed to the configured logs channel. Never raises --
    logging should never be the thing that breaks a command -- but logs
    both success and failure to the console, so it's never ambiguous
    whether this actually ran, and if it succeeded, exactly which channel
    it posted to (in case that's not the channel you expect)."""
    channel = bot.get_channel(LOGS_CHANNEL_ID)
    if channel is None:
        log.warning(
            f"Can't find logs channel {LOGS_CHANNEL_ID} -- either it doesn't exist, the bot isn't in "
            "the server that has it, or LOGS_CHANNEL_ID in logsutil.py needs updating to match this "
            "server's actual logs channel."
        )
        return
    try:
        await channel.send(embed=embed)
        log.info(f"Sent log to #{channel.name} ({LOGS_CHANNEL_ID}) in {channel.guild.name}.")
    except discord.Forbidden:
        log.warning(
            f"Missing permission to send in logs channel #{channel.name} ({LOGS_CHANNEL_ID}) -- "
            "check the bot's role has View Channel + Send Messages there."
        )
    except discord.HTTPException as e:
        log.warning(f"Failed to send to logs channel #{channel.name} ({LOGS_CHANNEL_ID}): {e}")
