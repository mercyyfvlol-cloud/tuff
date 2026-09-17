import discord
from discord import app_commands
from discord.ext import commands

from logsutil import send_log

MAX_LOGGED_CONTENT = 1000  # embed field/description length safety margin


def _content_or_placeholder(content: str) -> str:
    return content if content else "*(no text content -- likely just an attachment or embed)*"


class EventLogs(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._last_deleted: dict[int, discord.Message] = {}  # channel_id -> most recently deleted message, for /snipe

    # ---------------- Deleted messages ----------------

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        self._last_deleted[message.channel.id] = message

        embed = discord.Embed(
            title="🗑️ Message Deleted",
            description=(
                f"**Author:** {message.author.mention}\n"
                f"**Channel:** {message.channel.mention}\n\n"
                f"{_content_or_placeholder(message.content)[:MAX_LOGGED_CONTENT]}"
            ),
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow(),
        )
        if message.attachments:
            embed.add_field(name="Attachments", value="\n".join(a.filename for a in message.attachments)[:1024], inline=False)
        embed.set_footer(text=f"Author ID: {message.author.id}")
        await send_log(self.bot, embed)

    # ---------------- Edited messages ----------------

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild:
            return
        if before.content == after.content:
            return  # e.g. a link embed loading in afterward -- not a real content edit

        embed = discord.Embed(
            title="📝 Message Edited",
            description=f"**Author:** {before.author.mention}\n**Channel:** {before.channel.mention}",
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="Before", value=_content_or_placeholder(before.content)[:MAX_LOGGED_CONTENT], inline=False)
        embed.add_field(name="After", value=_content_or_placeholder(after.content)[:MAX_LOGGED_CONTENT], inline=False)
        embed.add_field(name="Jump to message", value=f"[Click here]({after.jump_url})", inline=False)
        embed.set_footer(text=f"Author ID: {before.author.id}")
        await send_log(self.bot, embed)

    # ---------------- /snipe ----------------

    def _snipe_embed(self, channel_id: int) -> discord.Embed | None:
        message = self._last_deleted.get(channel_id)
        if message is None:
            return None
        embed = discord.Embed(
            description=_content_or_placeholder(message.content)[:MAX_LOGGED_CONTENT],
            color=discord.Color.blurple(),
            timestamp=message.created_at,
        )
        embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)
        if message.attachments:
            embed.add_field(name="Attachments", value="\n".join(a.filename for a in message.attachments)[:1024], inline=False)
        embed.set_footer(text="Last deleted message in this channel")
        return embed

    @app_commands.command(name="snipe", description="Show the last deleted message in this channel")
    async def snipe(self, interaction: discord.Interaction):
        embed = self._snipe_embed(interaction.channel_id)
        if embed is None:
            await interaction.response.send_message("Nothing to snipe -- no deleted messages here since I started running.", ephemeral=True)
            return
        await interaction.response.send_message(embed=embed)

    @commands.command(name="snipe")
    async def snipe_text(self, ctx: commands.Context):
        embed = self._snipe_embed(ctx.channel.id)
        if embed is None:
            await ctx.reply("Nothing to snipe -- no deleted messages here since I started running.", mention_author=False)
            return
        await ctx.reply(embed=embed, mention_author=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(EventLogs(bot))
