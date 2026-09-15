import logging

import discord
from discord import app_commands
from discord.ext import commands

import database as db

log = logging.getLogger("bot.logsutil")

FALLBACK_LOGS_CHANNEL_ID = 1543459712731844768  # used only until /logssetup is run at least once


async def send_log(bot, embed: discord.Embed):
    """Send an embed to the configured logs channel. Never raises --
    logging should never be the thing that breaks a command -- but logs
    both success and failure to the console, so it's never ambiguous
    whether this actually ran, and if it succeeded, exactly which channel
    it posted to (in case that's not the channel you expect)."""
    channel_id = db.get_log_channel() or FALLBACK_LOGS_CHANNEL_ID
    channel = bot.get_channel(channel_id)
    if channel is None:
        log.warning(
            f"Can't find logs channel {channel_id} -- either it doesn't exist, the bot isn't in the "
            "server that has it, or nobody's run /logssetup yet to point this at a real channel."
        )
        return
    try:
        await channel.send(embed=embed)
        log.info(f"Sent log to #{channel.name} ({channel_id}) in {channel.guild.name}.")
    except discord.Forbidden:
        log.warning(
            f"Missing permission to send in logs channel #{channel.name} ({channel_id}) -- "
            "check the bot's role has View Channel + Send Messages there."
        )
    except discord.HTTPException as e:
        log.warning(f"Failed to send to logs channel #{channel.name} ({channel_id}): {e}")


class LogsConfig(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _confirm_and_test(self, channel: discord.TextChannel) -> str | None:
        """Sets the channel and sends a test message. Returns an error string, or None on success."""
        db.set_log_channel(channel.id)
        embed = discord.Embed(
            title="✅ Logs Channel Set",
            description="Mod actions, role changes, and other bot logs will post here from now on.",
            color=discord.Color.green(),
        )
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            return f"Saved, but I don't have permission to post in {channel.mention} -- check my access there."
        return None

    @app_commands.command(name="logssetup", description="[Admin] Set the channel mod-action logs get posted to")
    @app_commands.describe(channel="The channel to post logs in")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def logssetup(self, interaction: discord.Interaction, channel: discord.TextChannel):
        error = await self._confirm_and_test(channel)
        if error:
            await interaction.response.send_message(error, ephemeral=True)
            return
        await interaction.response.send_message(f"✅ Logs will now post in {channel.mention}.", ephemeral=True)

    @commands.command(name="logssetup")
    @commands.has_permissions(manage_guild=True)
    async def logssetup_text(self, ctx: commands.Context, channel: discord.TextChannel):
        error = await self._confirm_and_test(channel)
        if error:
            await ctx.reply(error, mention_author=False)
            return
        await ctx.reply(f"✅ Logs will now post in {channel.mention}.", mention_author=False)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("You need the Manage Server permission to do that.", ephemeral=True)
        else:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"Error: {error}", ephemeral=True)

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply("You need the Manage Server permission to do that.", mention_author=False)
        elif isinstance(error, commands.ChannelNotFound):
            await ctx.reply("Couldn't find that channel.", mention_author=False)
        else:
            print(f"LogsConfig prefix command error: {error}")


async def setup(bot: commands.Bot):
    await bot.add_cog(LogsConfig(bot))
