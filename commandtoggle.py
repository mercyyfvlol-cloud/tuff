import types

import discord
from discord import app_commands
from discord.ext import commands

import database as db
from permissions import SUPER_USER_ID

# Never allow these to be disabled -- disabling them would be a one-way lockout,
# since the only way back would be editing the database directly.
PROTECTED_COMMANDS = {"shutdown", "shutdownlist"}


async def _tree_interaction_check(tree_self, interaction: discord.Interaction) -> bool:
    """Replaces bot.tree's interaction_check (see CommandToggle.__init__) so
    every slash command, in every cog, gets checked against the disabled
    list -- without needing to touch each cog individually."""
    command = interaction.command
    if command is not None and db.is_command_disabled(command.qualified_name):
        await interaction.response.send_message(f"⚠️ `/{command.qualified_name}` is currently disabled.", ephemeral=True)
        return False
    return True


class CommandToggle(commands.Cog):
    """Lets the bot owner kill-switch any single command (slash or prefix)
    bot-wide -- e.g. disabling /play if ffmpeg is broken, without needing
    to take the whole bot offline. Global check for prefix commands (see
    bot.add_check below) + a patched tree.interaction_check for slash
    commands cover every existing and future command automatically."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.add_check(self._check_not_disabled)
        self.bot.tree.interaction_check = types.MethodType(_tree_interaction_check, self.bot.tree)

    def cog_unload(self):
        self.bot.remove_check(self._check_not_disabled)

    async def _check_not_disabled(self, ctx: commands.Context) -> bool:
        if ctx.command is None:
            return True
        if db.is_command_disabled(ctx.command.qualified_name):
            await ctx.reply(f"⚠️ `{ctx.prefix}{ctx.command.qualified_name}` is currently disabled.", mention_author=False)
            return False
        return True

    def _known_command_names(self) -> set[str]:
        names = {c.qualified_name for c in self.bot.commands}
        names |= {c.qualified_name for c in self.bot.tree.walk_commands()}
        return names

    def _apply(self, command: str, action: str, actor_id: int) -> str:
        """Returns the response message."""
        command = command.strip().lstrip("/?")
        if command in PROTECTED_COMMANDS:
            return f"Can't disable `{command}` -- that would lock out managing shutdowns entirely."
        if command not in self._known_command_names():
            return f"I don't recognize a command called `{command}` -- check spelling/case (e.g. `poll create`, not `pollcreate`)."

        if action == "disable":
            db.disable_command(command, actor_id)
            return f"🔴 `{command}` is now disabled bot-wide."
        removed = db.enable_command(command)
        return f"🟢 `{command}` re-enabled." if removed else f"`{command}` wasn't disabled."

    # ---------------- Slash commands ----------------

    @app_commands.command(name="shutdown", description="[Owner] Disable or re-enable a specific command bot-wide")
    @app_commands.describe(command="The command name, e.g. 'play' or 'poll create'", action="Disable or re-enable it")
    @app_commands.choices(action=[
        app_commands.Choice(name="disable", value="disable"),
        app_commands.Choice(name="enable", value="enable"),
    ])
    async def shutdown(self, interaction: discord.Interaction, command: str, action: app_commands.Choice[str]):
        if interaction.user.id != SUPER_USER_ID:
            await interaction.response.send_message("You can't use this command.", ephemeral=True)
            return
        await interaction.response.send_message(self._apply(command, action.value, interaction.user.id), ephemeral=True)

    @app_commands.command(name="shutdownlist", description="[Owner] List every currently-disabled command")
    async def shutdownlist(self, interaction: discord.Interaction):
        if interaction.user.id != SUPER_USER_ID:
            await interaction.response.send_message("You can't use this command.", ephemeral=True)
            return
        names = db.get_disabled_commands()
        if not names:
            await interaction.response.send_message("Nothing is currently disabled.", ephemeral=True)
            return
        await interaction.response.send_message("Disabled: " + ", ".join(f"`{n}`" for n in names), ephemeral=True)

    # ---------------- Prefix commands ----------------

    @commands.command(name="shutdown")
    async def shutdown_text(self, ctx: commands.Context, action: str = None, *, command: str = None):
        if ctx.author.id != SUPER_USER_ID:
            return  # stay quiet, same as say_text/sync_text
        if action is None or command is None or action.lower() not in ("enable", "disable"):
            await ctx.reply(
                f"Usage: `{ctx.prefix}shutdown disable <command>`, `{ctx.prefix}shutdown enable <command>`, or `{ctx.prefix}shutdownlist`",
                mention_author=False,
            )
            return
        await ctx.reply(self._apply(command, action.lower(), ctx.author.id), mention_author=False)

    @commands.command(name="shutdownlist")
    async def shutdownlist_text(self, ctx: commands.Context):
        if ctx.author.id != SUPER_USER_ID:
            return
        names = db.get_disabled_commands()
        if not names:
            await ctx.reply("Nothing is currently disabled.", mention_author=False)
            return
        await ctx.reply("Disabled: " + ", ".join(f"`{n}`" for n in names), mention_author=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(CommandToggle(bot))
