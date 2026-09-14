import asyncio
import logging
import os
import shutil

import discord
from discord.ext import commands
from dotenv import load_dotenv

from database import init_db, DB_PATH
from permissions import install_permission_bypass

load_dotenv()

# -----------------------------
# Logging
# -----------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

log = logging.getLogger("bot")

# -----------------------------
# Configuration
# -----------------------------

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("COMMAND_PREFIX", "?")

# -----------------------------
# Discord Intents
# -----------------------------

intents = discord.Intents.default()

intents.message_content = True
intents.members = True
intents.voice_states = True

# -----------------------------
# Bot
# -----------------------------

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None,
)

# Process start time
bot.start_time = discord.utils.utcnow()

# -----------------------------
# Extensions
# -----------------------------

STARTUP_EXTENSIONS = (
    "general",
    "music",
    "leveling",
    "moderation",
    "voice",
    "eventlogs",
    "giveaways",
    "emoji",
    "autorole",
    "polls",
    "roles",
    "fun",
    "modapps",
    "afk",
    "automod",
    "confessions",
    "suggestions",
    "spam67",
    "xpboost",
    "superadmin",
    "crisis",
    "boosts",
    "commandtoggle",
)

# -----------------------------
# Ready Event
# -----------------------------

@bot.event
async def on_ready():
    log.info(
        f"Logged in as {bot.user} "
        f"(ID: {bot.user.id})"
    )

    try:
        synced = await bot.tree.sync()

        log.info(
            f"Synced {len(synced)} slash command(s)"
        )

    except Exception as e:
        log.exception(
            f"Failed to sync slash commands: {e}"
        )

    try:
        await bot.change_presence(
            status=discord.Status.dnd,
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="/play | /rank",
            ),
        )
    except Exception as e:
        log.exception(
            f"Failed to change presence: {e}"
        )


# -----------------------------
# Command Error Handler
# -----------------------------

@bot.event
async def on_command_error(ctx, error):

    # Ignore unknown commands
    if isinstance(error, commands.CommandNotFound):
        return

    # Let cog-specific handlers handle their own errors
    if ctx.cog and ctx.cog.has_error_handler():
        return

    # Let command-specific handlers handle their own errors
    if ctx.command and ctx.command.has_error_handler():
        return

    # Missing permissions
    if isinstance(error, commands.MissingPermissions):
        try:
            await ctx.send(
                "You don't have permission to do that."
            )
        except discord.Forbidden:
            pass

        return

    # Missing argument
    if isinstance(error, commands.MissingRequiredArgument):

        try:
            await ctx.send(
                f"Missing argument: `{error.param.name}`. "
                f"Check `{ctx.prefix}help {ctx.command}`."
            )
        except discord.Forbidden:
            pass

        return

    # Other errors
    log.exception(
        "Unhandled command error",
        exc_info=error,
    )

    try:
        await ctx.send(
            f"Something went wrong: `{error}`"
        )
    except discord.Forbidden:
        pass


# -----------------------------
# Main
# -----------------------------

async def main():

    # -------------------------
    # Token check
    # -------------------------

    if not TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN is not set. "
            "Add it to your .env or Railway environment variables."
        )

    # -------------------------
    # FFmpeg check
    # -------------------------

    ffmpeg_path = shutil.which("ffmpeg")

    if ffmpeg_path is None:

        log.warning(
            "ffmpeg was not found on PATH -- "
            "/play will fail with 'ffmpeg was not found' "
            "until this is fixed. "
            "On Railway, install ffmpeg through nixpacks.toml "
            "and redeploy with the build cache cleared. "
            "Locally: apt install ffmpeg / brew install ffmpeg."
        )

    else:

        log.info(
            f"ffmpeg found at {ffmpeg_path}"
        )

    # -------------------------
    # Database check
    # -------------------------

    if DB_PATH == "bot.db":

        log.warning(
            "DB_PATH is not set -- using the default "
            "'bot.db' in the container's own filesystem. "
            "This can be wiped on redeploy/restart. "
            "For a Railway Volume, set DB_PATH to "
            "/data/bot.db in the service Variables."
        )

    elif not DB_PATH.startswith("/"):

        log.warning(
            f"DB_PATH is set to '{DB_PATH}', "
            "which isn't an absolute path. "
            "For a Railway Volume it should normally be "
            "/data/bot.db."
        )

    else:

        log.info(
            f"Using database at {DB_PATH}"
        )

    # -------------------------
    # Initialize database
    # -------------------------

    try:

        init_db()

        log.info(
            "Database initialized successfully."
        )

    except Exception as e:

        log.exception(
            f"Database initialization failed: {e}"
        )

        raise

    # -------------------------
    # Permission system
    # -------------------------

    try:

        install_permission_bypass()

        log.info(
            "Permission system initialized."
        )

    except Exception as e:

        log.exception(
            f"Failed to initialize permission system: {e}"
        )

        raise

    # -------------------------
    # Load extensions
    # -------------------------

    async with bot:

        for ext in STARTUP_EXTENSIONS:

            try:

                await bot.load_extension(ext)

                log.info(
                    f"Loaded extension: {ext}"
                )

            except commands.ExtensionNotFound:

                # Missing file/module
                log.error(
                    f"Extension not found: {ext} "
                    f"-- skipping."
                )

            except commands.ExtensionAlreadyLoaded:

                log.warning(
                    f"Extension already loaded: {ext} "
                    f"-- skipping."
                )

            except commands.ExtensionFailed as e:

                log.exception(
                    f"Extension failed to load: {ext}: {e}"
                )

            except commands.NoEntryPointError:

                log.error(
                    f"Extension has no setup() function: "
                    f"{ext} -- skipping."
                )

            except Exception as e:

                log.exception(
                    f"Unexpected error loading extension "
                    f"{ext}: {e}"
                )

        # -------------------------
        # Start bot
        # -------------------------

        log.info(
            "Starting Discord bot..."
        )

        await bot.start(TOKEN)


# -----------------------------
# Entry Point
# -----------------------------

if __name__ == "__main__":

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        log.info(
            "Bot stopped by user."
        )

    except Exception as e:

        log.exception(
            f"Bot stopped because of an error: {e}"
        )
