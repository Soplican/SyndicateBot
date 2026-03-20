import json
from pathlib import Path
import logging
import traceback

import discord
from discord.ext import commands

log = logging.getLogger("Phantom_Bot.modules.welcome")

CFG_PATH = Path("modules") / "welcome" / "welcome_config.json"


def load_cfg(guild_id: int | None = None) -> dict:
    if not CFG_PATH.exists():
        raise FileNotFoundError(f"Config not found: {CFG_PATH}")
    return json.loads(CFG_PATH.read_text(encoding="utf-8"))


def fmt(text: str, member: discord.Member) -> str:
    if not isinstance(text, str):
        return ""
    return (text
            .replace("{mention}", member.mention)
            .replace("{user}", str(member))
            .replace("{name}", member.display_name)
            .replace("{id}", str(member.id))
            .replace("{server}", member.guild.name if member.guild else "")
            .replace("{avatar}", str(member.display_avatar.url)))


class WelcomeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _send_welcome(self, channel: discord.abc.Messageable, member: discord.Member):
        cfg = load_cfg(member.guild.id if member and member.guild else None)
        title = fmt(cfg.get("title", ""), member).strip()
        greeting = fmt(cfg.get("greeting", ""), member).strip()
        footer = fmt(cfg.get("footer_text", ""), member).strip()

        embed = discord.Embed(
            title=title or None,
            description=greeting or None,
            color=discord.Color.green()
        )
        if footer:
            embed.set_footer(text=footer)

        # Добавляем картинку, если есть
        media = cfg.get("media") or {}
        if media.get("url"):
            embed.set_image(url=media["url"])

        await channel.send(embed=embed)

    async def _send_leave(self, channel: discord.abc.Messageable, member: discord.Member):
        cfg = load_cfg(member.guild.id if member and member.guild else None)
        leave_cfg = cfg.get("leave") or {}
        title = fmt(leave_cfg.get("title", ""), member).strip()
        text = fmt(leave_cfg.get("text", ""), member).strip()
        footer = fmt(leave_cfg.get("footer_text", ""), member).strip()

        embed = discord.Embed(
            title=title or None,
            description=text or None,
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=str(member.display_avatar.url))
        if footer:
            embed.set_footer(text=footer)

        await channel.send(embed=embed)

    async def try_assign_roles(self, member: discord.Member, cfg: dict) -> None:
        auto = cfg.get("auto_roles") or {}
        if not auto.get("enabled", False):
            return

        role_ids = auto.get("role_ids") or []
        if not isinstance(role_ids, list) or not role_ids:
            return

        me = member.guild.me
        if me is None or not me.guild_permissions.manage_roles:
            log.warning("[auto_roles] Bot has no Manage Roles permission")
            return

        roles_to_add = []
        for rid in role_ids:
            try:
                rid_int = int(str(rid))
            except Exception:
                log.warning(f"[auto_roles] Bad role id: {rid!r}")
                continue

            role = member.guild.get_role(rid_int)
            if role is None:
                log.warning(f"[auto_roles] Role not found: {rid_int}")
                continue

            if me.top_role <= role:
                log.warning(f"[auto_roles] Can't assign role {role.name} (bot role too low)")
                continue

            if role not in member.roles:
                roles_to_add.append(role)

        if not roles_to_add:
            return

        try:
            await member.add_roles(*roles_to_add, reason="Auto roles on join")
            log.info(f"[auto_roles] Added roles to {member}: {[r.id for r in roles_to_add]}")
        except Exception:
            log.error("AUTO ROLES ERROR:\n" + traceback.format_exc())

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        try:
            cfg = load_cfg(member.guild.id if member and member.guild else None)
            if not cfg.get("enabled", True):
                return

            await self.try_assign_roles(member, cfg)

            channel_id = int(cfg["channel_id"])
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                channel = await self.bot.fetch_channel(channel_id)

            await self._send_welcome(channel, member)
            log.info(f"[welcome] sent for {member}")

        except Exception:
            log.error("WELCOME ERROR:\n" + traceback.format_exc())

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        try:
            cfg = load_cfg(member.guild.id if member and member.guild else None)
            leave_cfg = cfg.get("leave")
            if not leave_cfg or not leave_cfg.get("enabled", False):
                return

            channel_id = int(leave_cfg["channel_id"])
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                channel = await self.bot.fetch_channel(channel_id)

            await self._send_leave(channel, member)
            log.info(f"[leave] sent for {member}")

        except Exception:
            log.error("LEAVE ERROR:\n" + traceback.format_exc())

    @commands.command()
    async def welcome_test(self, ctx: commands.Context):
        try:
            await self._send_welcome(ctx.channel, ctx.author)
        except Exception:
            await ctx.send("Ошибка, смотри консоль.")
            log.error("WELCOME TEST ERROR:\n" + traceback.format_exc())

    @commands.command()
    async def leave_test(self, ctx: commands.Context):
        try:
            await self._send_leave(ctx.channel, ctx.author)
        except Exception:
            await ctx.send("Ошибка, смотри консоль.")
            log.error("LEAVE TEST ERROR:\n" + traceback.format_exc())


async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeCog(bot))
