import logging

import discord

log = logging.getLogger("bot.logsutil")

LOGS_CHANNEL_ID = 1543459712731844768


async def send_log(bot, embed: discord.Embed):
    """Send an embed to the configured logs channel. Never raises --
    logging should never be the thing that breaks a command -- but now
    logs WHY it failed to the console instead of failing silently, since
    silent failure here is exactly what made "logs not sending" invisible
    to debug in the first place."""
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
    except discord.Forbidden:
        log.warning(
            f"Missing permission to send in logs channel #{channel.name} ({LOGS_CHANNEL_ID}) -- "
            "check the bot's role has View Channel + Send Messages there."
        )
    except discord.HTTPException as e:
        log.warning(f"Failed to send to logs channel #{channel.name} ({LOGS_CHANNEL_ID}): {e}")
