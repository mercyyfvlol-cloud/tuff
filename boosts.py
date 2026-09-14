import discord
from discord import app_commands
from discord.ext import commands


class Boosts(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _send_thank_you(self, member: discord.Member, guild: discord.Guild, *, test: bool = False) -> str | None:
        """Posts the thank-you message. Returns an error string, or None on success."""
        channel = guild.system_channel
        if channel is None:
            return "This server doesn't have a system channel set up -- nowhere to post this. Set one in Server Settings → Overview."

        suffix = " *(test -- nobody actually boosted)*" if test else ""
        try:
            await channel.send(f"🎉 Thank you {member.mention} for boosting **{guild.name}**! We really appreciate it 💜{suffix}")
        except discord.Forbidden:
            return f"I don't have permission to post in {channel.mention}."
        return None

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # premium_since goes from None -> a timestamp the moment someone starts boosting.
        if before.premium_since is not None or after.premium_since is None:
            return
        await self._send_thank_you(after, after.guild)

    @app_commands.command(name="testboost", description="[Admin] Preview the boost thank-you message without needing a real boost")
    @app_commands.describe(member="Who to pretend boosted (defaults to you)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def testboost(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        error = await self._send_thank_you(target, interaction.guild, test=True)
        if error:
            await interaction.response.send_message(error, ephemeral=True)
            return
        await interaction.response.send_message("✅ Sent -- check the system channel.", ephemeral=True)

    @commands.command(name="testboost")
    @commands.has_permissions(manage_guild=True)
    async def testboost_text(self, ctx: commands.Context, member: discord.Member = None):
        target = member or ctx.author
        error = await self._send_thank_you(target, ctx.guild, test=True)
        if error:
            await ctx.reply(error, mention_author=False)
            return
        await ctx.reply("✅ Sent -- check the system channel.", mention_author=False)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("You need the Manage Server permission to do that.", ephemeral=True)
        else:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"Error: {error}", ephemeral=True)

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply("You need the Manage Server permission to do that.", mention_author=False)
        elif isinstance(error, commands.MemberNotFound):
            await ctx.reply("Couldn't find that member.", mention_author=False)
        else:
            print(f"Boosts prefix command error: {error}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Boosts(bot))
