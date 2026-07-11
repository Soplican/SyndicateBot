import logging

import discord
from discord.ext import commands

MODULE_NAME = "clearall"
OWNER_ID = 609755494411796511
log = logging.getLogger(f"SyndicateBot.modules.{MODULE_NAME}")


class ClearAllCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="clearall")
    @commands.guild_only()
    async def clearall(self, ctx: commands.Context, category_id: int):
        """Удаляет только категорию по ID. Каналы внутри не удаляются."""
        if ctx.author.id != OWNER_ID:
            return

        category = ctx.guild.get_channel(category_id)
        if category is None:
            try:
                category = await ctx.guild.fetch_channel(category_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                category = None

        if category is None:
            await ctx.send("❌ Категория с таким ID не найдена.")
            return

        if not isinstance(category, discord.CategoryChannel):
            await ctx.send("❌ Указанный ID принадлежит не категории.")
            return

        category_name = category.name
        channel_count = len(category.channels)

        try:
            await category.delete(
                reason=f"Команда !clearall от владельца {ctx.author} ({ctx.author.id})"
            )
        except discord.Forbidden:
            await ctx.send("❌ У бота нет права «Управление каналами».")
            return
        except discord.HTTPException as exc:
            log.exception("Не удалось удалить категорию %s (%s)", category_name, category_id)
            await ctx.send(f"❌ Discord не смог удалить категорию: `{exc}`")
            return

        log.info(
            "Категория %s (%s) удалена пользователем %s (%s); каналов внутри было: %s",
            category_name,
            category_id,
            ctx.author,
            ctx.author.id,
            channel_count,
        )
        await ctx.send(
            f"✅ Категория **{category_name}** удалена. "
            f"Каналы внутри ({channel_count}) остались на сервере без категории."
        )

    @clearall.error
    async def clearall_error(self, ctx: commands.Context, error: commands.CommandError):
        if ctx.author.id != OWNER_ID:
            return

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Использование: `!clearall <ID категории>`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ ID категории должен состоять только из цифр.")
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send("❌ Команда работает только на сервере.")
        else:
            log.exception("Ошибка команды !clearall", exc_info=error)
            await ctx.send(f"❌ Ошибка: `{error}`")


async def setup(bot: commands.Bot):
    await bot.add_cog(ClearAllCog(bot))
