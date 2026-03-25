# -*- coding: utf-8 -*-
"""
capt_tier - ИСПРАВЛЕННАЯ ВЕРСИЯ
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional, Dict, Any, List

import discord
from discord.ext import commands
from discord import ui

CFG_PATH = Path(__file__).with_name("config.json")
TOPIC_PREFIX = "capt_creator:"


def load_cfg() -> Dict[str, Any]:
    if not CFG_PATH.exists():
        raise FileNotFoundError(f"Config not found: {CFG_PATH}")
    return json.loads(CFG_PATH.read_text(encoding="utf-8"))


def first_word(display_name: str) -> str:
    return (display_name.split("|", 1)[0].strip() or "user")


def slugify(text: str) -> str:
    t = text.strip().lower()
    t = re.sub(r"\s+", "-", t)
    t = re.sub(r"[^a-z0-9а-яё\-]", "", t, flags=re.IGNORECASE)
    t = re.sub(r"-{2,}", "-", t).strip("-")
    return t or "user"


def topic_for_creator(uid: int) -> str:
    return f"{TOPIC_PREFIX}{uid}"


def parse_creator(topic: Optional[str]) -> Optional[int]:
    if not topic:
        return None
    topic = topic.strip()
    if topic.startswith(TOPIC_PREFIX):
        raw = topic[len(TOPIC_PREFIX):].strip()
        if raw.isdigit():
            return int(raw)
    return None


async def find_existing_channel(guild: discord.Guild, category_id: int, creator_id: int) -> Optional[discord.TextChannel]:
    cat = guild.get_channel(category_id)
    if not isinstance(cat, discord.CategoryChannel):
        return None
    for ch in cat.channels:
        if isinstance(ch, discord.TextChannel) and (ch.topic or "").strip() == topic_for_creator(creator_id):
            return ch
    return None


async def unique_name_in_category(category: discord.CategoryChannel, base: str) -> str:
    existing = {c.name for c in category.channels if isinstance(c, discord.TextChannel)}
    if base not in existing:
        return base
    i = 2
    while f"{base}-{i}" in existing:
        i += 1
    return f"{base}-{i}"


# -------------------------
# MAIN PANEL
# -------------------------
class MainPanel(ui.LayoutView):
    def __init__(self, cfg: Dict[str, Any]):
        super().__init__(timeout=None)
        self.cfg = cfg
        
        parts = []
        
        if cfg.get("main_title"):
            parts.append(ui.TextDisplay(f"📄 **{cfg['main_title']}**"))
        
        if cfg.get("main_desc"):
            parts.append(ui.TextDisplay(cfg['main_desc']))
        
        parts.append(ui.Separator())
        
        # Кнопка для себя
        parts.append(
            ui.Section(
                ui.TextDisplay("**Для себя**"),
                accessory=ui.Button(
                    label=cfg.get("create_button_label", "Создать канал отката"),
                    emoji="➕",
                    style=discord.ButtonStyle.primary,
                    custom_id="capt_tier:create",
                )
            )
        )
        
        # Кнопка для стаффа
        parts.append(
            ui.Section(
                ui.TextDisplay("**Для участника**"),
                accessory=ui.Button(
                    label=cfg.get("staff_create_button_label", "Создать канал для участника"),
                    emoji="👥",
                    style=discord.ButtonStyle.secondary,
                    custom_id="capt_tier:staff_create",
                )
            )
        )
        
        if cfg.get("main_image_url"):
            gallery = ui.MediaGallery()
            gallery.add_item(media=cfg["main_image_url"])
            parts.append(gallery)
        
        if cfg.get("main_footer"):
            parts.append(ui.TextDisplay(cfg['main_footer']))
        
        self.add_item(ui.Container(*parts))


# -------------------------
# USER SELECT VIEW
# -------------------------
class UserSelectView(ui.View):
    def __init__(self, cfg: Dict[str, Any]):
        super().__init__(timeout=60)
        self.cfg = cfg
        self.add_item(UserSelectMenu(cfg))


class UserSelectMenu(ui.UserSelect):
    def __init__(self, cfg: Dict[str, Any]):
        super().__init__(
            custom_id="capt_tier:user_select",
            placeholder="👤 Выберите пользователя...",
            min_values=1,
            max_values=1
        )
        self.cfg = cfg
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.client.get_cog("CaptTier").handle_user_select(interaction, self.values[0])


# -------------------------
# CHANNEL PANEL
# -------------------------
class ChannelPanel(ui.LayoutView):
    def __init__(self, cfg: Dict[str, Any], creator_id: int, ping_role_id: int = 0):
        super().__init__(timeout=None)
        self.cfg = cfg
        
        parts = [
            ui.TextDisplay(f"📄 **{cfg.get('channel_title', 'Панель отката')}**"),
            ui.TextDisplay(cfg.get('channel_desc', 'Выберите Tier или запросите откат.')),
        ]

        if ping_role_id:
            parts.append(ui.TextDisplay(f"<@&{ping_role_id}>"))

        parts.extend([
            ui.Separator(),
            ui.TextDisplay(f"**Создал канал:** <@{creator_id}>"),
            ui.Separator(),
        ])
        
        # Кнопки Tier
        parts.append(
            ui.Section(
                ui.TextDisplay("**S+ Tier**"),
                accessory=ui.Button(
                    label="S+ Tier",
                    style=discord.ButtonStyle.success,
                    custom_id="capt_tier:t1"
                )
            )
        )
        
        parts.append(
            ui.Section(
                ui.TextDisplay("**S Tier**"),
                accessory=ui.Button(
                    label="S Tier",
                    style=discord.ButtonStyle.success,
                    custom_id="capt_tier:t2"
                )
            )
        )
        
        parts.append(
            ui.Section(
                ui.TextDisplay("**A Tier**"),
                accessory=ui.Button(
                    label="A Tier",
                    style=discord.ButtonStyle.success,
                    custom_id="capt_tier:t3"
                )
            )
        )

        parts.append(
            ui.Section(
                ui.TextDisplay("**B Tier**"),
                accessory=ui.Button(
                    label="B Tier",
                    style=discord.ButtonStyle.success,
                    custom_id="capt_tier:t4"
                )
            )
        )
        
        # Кнопка отката
        parts.append(
            ui.Section(
                ui.TextDisplay("**Откат**"),
                accessory=ui.Button(
                    label="Запросить откат",
                    style=discord.ButtonStyle.danger,
                    custom_id="capt_tier:rollback"
                )
            )
        )

        self.add_item(ui.Container(*parts))


# -------------------------
# ALREADY EXISTS VIEW
# -------------------------
class AlreadyExistsView(ui.LayoutView):
    def __init__(self, cfg: Dict[str, Any], channel_id: int, user_id: int = None):
        super().__init__(timeout=None)
        
        if user_id:
            text = cfg.get("already_exists_for_user_text", "У пользователя <@{user}> уже есть открытый канал: <#{channel}>")
            body = text.format(user=user_id, channel=channel_id)
        else:
            text = cfg.get("already_exists_text", "У тебя уже есть открытый канал: <#{channel}>")
            body = text.format(channel=channel_id)

        parts = [
            ui.TextDisplay(f"❗ **{cfg.get('already_exists_title', 'Канал уже создан')}**"),
            ui.TextDisplay(body),
        ]
        
        self.add_item(ui.Container(*parts))


# -------------------------
# ROLLBACK VIEW
# -------------------------
class RollbackView(ui.LayoutView):
    def __init__(self, cfg: Dict[str, Any], creator_id: int, requester_id: int):
        super().__init__(timeout=None)
        
        text = cfg.get("rollback_text", "<@{requester}> запросил у вас откат с последнего мероприятия.")
        body = text.format(requester=requester_id)

        parts = [
            ui.TextDisplay(f"<@{creator_id}>"),
            ui.TextDisplay("📢 **Запрос отката**"),
            ui.Separator(),
            ui.TextDisplay(f"**Для:** <@{creator_id}>"),
            ui.TextDisplay(f"**Запросил:** <@{requester_id}>"),
            ui.Separator(),
            ui.TextDisplay(body),
        ]

        self.add_item(ui.Container(*parts))


# -------------------------
# COG
# -------------------------
class CaptTier(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cfg = load_cfg()
        print(f"✅ CaptTier загружен")
        print(f"📋 Tier роли в конфиге:")
        print(f"  S+ Tier: {self.cfg.get('tier_roles', {}).get('tier1')}")
        print(f"  S Tier: {self.cfg.get('tier_roles', {}).get('tier2')}")
        print(f"  A Tier: {self.cfg.get('tier_roles', {}).get('tier3')}")
        print(f"  B Tier: {self.cfg.get('tier_roles', {}).get('tier4')}")

    def _is_staff(self, member: discord.Member) -> bool:
        staff_config = self.cfg.get("staff_role_id")
        if not staff_config:
            return False

        # Приводим к списку ID (поддерживаем как одиночное число, так и массив)
        if isinstance(staff_config, list):
            staff_ids = [int(x) for x in staff_config]
        else:
            staff_ids = [int(staff_config)]

        # Проверяем, есть ли у участника хотя бы одна из staff-ролей
        return any(r.id in staff_ids for r in member.roles)

    def _tier_role(self, guild: discord.Guild, key: str) -> Optional[discord.Role]:
        tier_roles = self.cfg.get("tier_roles", {})
        role_id = tier_roles.get(key)
        if not role_id:
            print(f"❌ Роль {key} не найдена в конфиге")
            return None
        role = guild.get_role(int(role_id))
        if not role:
            print(f"❌ Роль с ID {role_id} не найдена на сервере")
        else:
            print(f"✅ Найдена роль {key}: {role.name} (ID: {role.id})")
        return role

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
        
        custom_id = interaction.data.get("custom_id", "")
        print(f"📨 Получен interaction: {custom_id}")
        
        try:
            if custom_id == "capt_tier:create":
                await self.handle_create(interaction)
            elif custom_id == "capt_tier:staff_create":
                await self.handle_staff_create(interaction)
            elif custom_id == "capt_tier:t1":
                await self.apply_tier(interaction, "tier1", "S+ Tier")
            elif custom_id == "capt_tier:t2":
                await self.apply_tier(interaction, "tier2", "S Tier")
            elif custom_id == "capt_tier:t3":
                await self.apply_tier(interaction, "tier3", "A Tier")
            elif custom_id == "capt_tier:t4":
                await self.apply_tier(interaction, "tier4", "B Tier")
            elif custom_id == "capt_tier:rollback":
                await self.handle_rollback(interaction)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()
            try:
                await interaction.response.send_message(f"❌ Ошибка: {str(e)[:100]}", ephemeral=True)
            except:
                pass

    async def handle_create(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("❌ Ошибка", ephemeral=True)
        # Убрана проверка на staff — кнопка доступна всем
        await interaction.response.defer(ephemeral=True)
        try:
            guild = interaction.guild
            category = guild.get_channel(int(self.cfg["category_id"]))
            if not isinstance(category, discord.CategoryChannel):
                return await interaction.followup.send("❌ Категория не найдена", ephemeral=True)
            if self.cfg.get("allow_one_active_channel_per_user", True):
                existing = await find_existing_channel(guild, int(self.cfg["category_id"]), interaction.user.id)
                if existing:
                    view = AlreadyExistsView(self.cfg, existing.id)
                    return await interaction.followup.send(view=view, ephemeral=True)
            base = self.cfg.get("channel_name_prefix", "откаты")
            name_base = f"{base}-{slugify(first_word(interaction.user.display_name))}"
            ch_name = await unique_name_in_category(category, name_base)
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
            }
            # Добавляем все staff-роли в права доступа
            staff_role_ids = self.cfg.get("staff_role_id")
            if isinstance(staff_role_ids, list):
                for rid in staff_role_ids:
                    role = guild.get_role(int(rid))
                    if role:
                        overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
            elif staff_role_ids:
                role = guild.get_role(int(staff_role_ids))
                if role:
                    overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

            channel = await guild.create_text_channel(
                name=ch_name,
                category=category,
                overwrites=overwrites,
                topic=topic_for_creator(interaction.user.id)
            )
            view = ChannelPanel(self.cfg, creator_id=interaction.user.id, ping_role_id=int(self.cfg.get("ping_role_id", 0)))
            await channel.send(view=view)
            await interaction.followup.send(f"✅ Канал создан: {channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Ошибка: {str(e)[:100]}", ephemeral=True)

    async def handle_staff_create(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("❌ Ошибка", ephemeral=True)
        if not self._is_staff(interaction.user):
            return await interaction.response.send_message("❌ Нет прав", ephemeral=True)
        view = UserSelectView(self.cfg)
        await interaction.response.send_message(
            content="📋 **Выберите пользователя**\nВыберите участника, для которого нужно создать канал отката",
            view=view,
            ephemeral=True
        )

    async def handle_user_select(self, interaction: discord.Interaction, selected_user: discord.Member):
        if not self._is_staff(interaction.user):
            return await interaction.response.send_message("❌ Нет прав", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        try:
            guild = interaction.guild
            category = guild.get_channel(int(self.cfg["category_id"]))
            if not isinstance(category, discord.CategoryChannel):
                return await interaction.followup.send("❌ Категория не найдена", ephemeral=True)
            if self.cfg.get("allow_one_active_channel_per_user", True):
                existing = await find_existing_channel(guild, int(self.cfg["category_id"]), selected_user.id)
                if existing:
                    view = AlreadyExistsView(self.cfg, existing.id, selected_user.id)
                    return await interaction.followup.send(view=view, ephemeral=True)
            base = self.cfg.get("channel_name_prefix", "откаты")
            name_base = f"{base}-{slugify(first_word(selected_user.display_name))}"
            ch_name = await unique_name_in_category(category, name_base)
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                selected_user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
            }
            # Добавляем все staff-роли в права доступа
            staff_role_ids = self.cfg.get("staff_role_id")
            if isinstance(staff_role_ids, list):
                for rid in staff_role_ids:
                    role = guild.get_role(int(rid))
                    if role:
                        overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
            elif staff_role_ids:
                role = guild.get_role(int(staff_role_ids))
                if role:
                    overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

            channel = await guild.create_text_channel(
                name=ch_name,
                category=category,
                overwrites=overwrites,
                topic=topic_for_creator(selected_user.id)
            )
            view = ChannelPanel(self.cfg, creator_id=selected_user.id, ping_role_id=int(self.cfg.get("ping_role_id", 0)))
            await channel.send(view=view)
            await interaction.followup.send(f"✅ Канал для {selected_user.mention} создан: {channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Ошибка: {str(e)[:100]}", ephemeral=True)

    async def apply_tier(self, interaction: discord.Interaction, key: str, label: str):
        print(f"👉 apply_tier: {key}, {label}")
    
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("❌ Ошибка: не участник", ephemeral=True)
        if not self._is_staff(interaction.user):
            return await interaction.response.send_message("❌ Нет прав", ephemeral=True)
    
        # Определяем владельца канала по топику
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message("❌ Это не текстовый канал", ephemeral=True)
    
        creator_id = parse_creator(channel.topic)
        if not creator_id:
            return await interaction.response.send_message("❌ Не удалось определить владельца канала", ephemeral=True)
    
        target_member = interaction.guild.get_member(creator_id)
        if not target_member:
            return await interaction.response.send_message("❌ Владелец канала не найден на сервере", ephemeral=True)
    
        role_id = self.cfg.get("tier_roles", {}).get(key)
        print(f"🔍 Роль ID из конфига для {key}: {role_id}")
        if not role_id:
            return await interaction.response.send_message(
                f"❌ Роль {label} не найдена в конфиге (проверь ключ '{key}')",
                ephemeral=True
            )
    
        role = interaction.guild.get_role(int(role_id))
        print(f"🔍 Роль на сервере: {role}")
        if not role:
            return await interaction.response.send_message(
                f"❌ Роль с ID {role_id} не существует на сервере",
                ephemeral=True
            )
    
        try:
            # Удаляем другие tier-роли у целевого участника, если нужно
            if self.cfg.get("enforce_single_tier", True):
                tier_keys = ["tier1", "tier2", "tier3", "tier4"]
                for k in tier_keys:
                    if k != key:
                        other_role_id = self.cfg.get("tier_roles", {}).get(k)
                        if other_role_id:
                            other_role = interaction.guild.get_role(int(other_role_id))
                            if other_role and other_role in target_member.roles:
                                await target_member.remove_roles(other_role, reason="capt_tier: enforce single tier")
                                print(f"✅ Удалена роль {other_role.name} у {target_member.display_name}")
    
            # Выдаём роль целевому участнику
            if role not in target_member.roles:
                await target_member.add_roles(role, reason=f"capt_tier: {label} для {target_member.display_name}")
                await interaction.response.send_message(
                    f"✅ Роль {label} выдана {target_member.mention}",
                    ephemeral=True
                )
                print(f"✅ Выдана роль {role.name} пользователю {target_member.display_name} (staff: {interaction.user.display_name})")
            else:
                await interaction.response.send_message(
                    f"ℹ️ У {target_member.mention} уже есть роль {label}",
                    ephemeral=True
                )
    
        except discord.Forbidden:
            print("❌ Ошибка Forbidden: нет прав")
            await interaction.response.send_message(
                "❌ У бота нет прав на управление ролями",
                ephemeral=True
            )
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()
            await interaction.response.send_message(
                f"❌ Ошибка: {str(e)[:100]}",
                ephemeral=True
            )

    async def handle_rollback(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("❌ Ошибка", ephemeral=True)
        if not self._is_staff(interaction.user):
            return await interaction.response.send_message("❌ Нет прав", ephemeral=True)
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message("❌ Ошибка", ephemeral=True)
        creator_id = parse_creator(channel.topic)
        if not creator_id:
            return await interaction.response.send_message("❌ Не удалось определить создателя канала", ephemeral=True)
        await interaction.response.send_message("✅ Запрос отправлен", ephemeral=True)
        view = RollbackView(self.cfg, creator_id, interaction.user.id)
        await channel.send(view=view)

    @commands.command(name="capt_tier_panel")
    @commands.has_permissions(administrator=True)
    async def post_panel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        target = channel or ctx.channel
        view = MainPanel(self.cfg)
        await target.send(view=view)
        await ctx.send("✅ Панель отправлена!", delete_after=3)


async def setup(bot: commands.Bot):
    await bot.add_cog(CaptTier(bot))