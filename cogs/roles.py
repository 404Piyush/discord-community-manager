"""
Carl-bot Style Role Management System
Includes autoroles, timedroles, reaction roles, and comprehensive role management
"""

import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import List, Optional, Union, Dict
import random
import logging

logger = logging.getLogger('discord_bot')

class RoleManager:
    def __init__(self, bot):
        self.bot = bot
    
    async def get_autorole_settings(self, guild_id: int):
        """Get autorole settings for a guild"""
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT autoroles, reassign_roles, blacklisted_roles FROM role_config 
            WHERE guild_id = ? AND config_type = 'autorole'
        """, (guild_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'autoroles': json.loads(result[0]) if result[0] else [],
                'reassign': bool(result[1]),
                'blacklist': json.loads(result[2]) if result[2] else []
            }
        
        return {'autoroles': [], 'reassign': False, 'blacklist': []}
    
    async def update_autorole_settings(self, guild_id: int, autoroles: list, reassign: bool, blacklist: list):
        """Update autorole settings"""
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO role_config (guild_id, config_type, settings)
            VALUES (?, 'autorole', ?)
        """, (guild_id, json.dumps({'autoroles': autoroles, 'reassign_roles': reassign, 'blacklisted_roles': blacklist})))
        conn.commit()
        conn.close()

class ReactionRoleManager:
    def __init__(self, bot):
        self.bot = bot
    
    async def get_reaction_role(self, message_id: int):
        """Get reaction role data for a message"""
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT guild_id, channel_id, emoji_role_pairs, rr_type, settings
            FROM reaction_roles WHERE message_id = ?
        """, (message_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'guild_id': result[0],
                'channel_id': result[1],
                'pairs': json.loads(result[2]),
                'type': result[3],
                'settings': json.loads(result[4]) if result[4] else {}
            }
        return None
    
    async def add_reaction_role(self, message_id: int, guild_id: int, channel_id: int, 
                              emoji: str, role_id: int, rr_type: str = "normal"):
        """Add a reaction role"""
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        
        # Get existing data
        cursor.execute("""
            SELECT emoji_role_pairs FROM reaction_roles WHERE message_id = ?
        """, (message_id,))
        result = cursor.fetchone()
        
        if result:
            pairs = json.loads(result[0])
            pairs[emoji] = role_id
        else:
            pairs = {emoji: role_id}
        
        cursor.execute("""
            INSERT OR REPLACE INTO reaction_roles 
            (message_id, guild_id, channel_id, emoji_role_pairs, rr_type, settings)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (message_id, guild_id, channel_id, json.dumps(pairs), rr_type, "{}"))
        conn.commit()
        conn.close()

class RolesCog(commands.Cog):
    """🎭 Role Management System"""
    
    def __init__(self, bot):
        self.bot = bot
        self.role_manager = RoleManager(bot)
        self.rr_manager = ReactionRoleManager(bot)
        self.timedrole_check.start()
        
        # Initialize database
        self.init_database()
    
    def init_database(self):
        """Initialize role management tables"""
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        
        # Autoroles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS role_config (
                guild_id INTEGER,
                config_type TEXT,
                settings TEXT,
                PRIMARY KEY (guild_id, config_type)
            )
        """)
        
        # Timed roles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS timed_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                role_id INTEGER,
                assign_time DATETIME,
                delay_minutes INTEGER
            )
        """)
        
        # Pending timed roles
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pending_timed_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                role_id INTEGER,
                assign_at DATETIME
            )
        """)
        
        # Reaction roles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reaction_roles (
                guild_id INTEGER,
                channel_id INTEGER,
                message_id INTEGER,
                emoji TEXT,
                role_id INTEGER,
                rr_type TEXT DEFAULT 'normal'
            )
        """)
        
        # Member roles backup
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS member_roles_backup (
                guild_id INTEGER,
                user_id INTEGER,
                roles TEXT,
                PRIMARY KEY (guild_id, user_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    @tasks.loop(minutes=1)
    async def timedrole_check(self):
        """Check for timed roles to assign"""
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, guild_id, user_id, role_id FROM pending_timed_roles
            WHERE assign_at <= ?
        """, (datetime.utcnow(),))
        
        pending = cursor.fetchall()
        
        for row in pending:
            try:
                guild = self.bot.get_guild(row[1])
                if guild:
                    member = guild.get_member(row[2])
                    role = guild.get_role(row[3])
                    
                    if member and role:
                        await member.add_roles(role, reason="Timed role assignment")
                
                cursor.execute("DELETE FROM pending_timed_roles WHERE id = ?", (row[0],))
                
            except Exception as e:
                print(f"Error assigning timed role: {e}")
        
        conn.commit()
        conn.close()
    
    @timedrole_check.before_loop
    async def before_timedrole_check(self):
        await self.bot.wait_until_ready()
    
    # Event Listeners
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Handle autoroles and role reassignment"""
        if member.bot:
            config = await self.role_manager.get_autorole_settings(member.guild.id)
            if not config['autoroles']:
                return
        
        config = await self.role_manager.get_autorole_settings(member.guild.id)
        if config['autoroles']:
            roles_to_add = []
            
            # Add autoroles
            for role_id in config['autoroles']:
                role = member.guild.get_role(role_id)
                if role:
                    roles_to_add.append(role)
            
            # Check for role reassignment
            if config['reassign']:
                cursor = self.bot.db.get_connection().cursor()
                cursor.execute("""
                    SELECT roles FROM member_roles_backup 
                    WHERE guild_id = ? AND user_id = ?
                """, (member.guild.id, member.id))
                backup_result = cursor.fetchone()
                
                if backup_result:
                    old_role_ids = json.loads(backup_result[0])
                    for role_id in old_role_ids:
                        if role_id not in config['blacklist']:
                            role = member.guild.get_role(role_id)
                            if role and role not in roles_to_add:
                                roles_to_add.append(role)
            
            # Add timed roles to pending
            cursor.execute("""
                SELECT role_id, delay_minutes FROM timed_roles WHERE guild_id = ?
            """, (member.guild.id,))
            timed_roles = cursor.fetchall()
            
            for role_id, delay in timed_roles:
                assign_at = datetime.utcnow() + timedelta(minutes=delay)
                cursor.execute("""
                    INSERT INTO pending_timed_roles (guild_id, user_id, role_id, assign_at)
                    VALUES (?, ?, ?, ?)
                """, (member.guild.id, member.id, role_id, assign_at))
            
            self.bot.db.commit()
            
            # Assign roles
            if roles_to_add:
                try:
                    await member.add_roles(*roles_to_add, reason="Autorole/Role reassignment")
                except Exception as e:
                    print(f"Error adding autoroles: {e}")
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Backup member roles for reassignment"""
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        
        # Check if reassignment is enabled
        cursor.execute("""
            SELECT reassign_roles FROM role_config WHERE guild_id = ? AND config_type = 'autorole'
        """, (member.guild.id,))
        result = cursor.fetchone()
        
        if result and result[0]:
            role_ids = [role.id for role in member.roles[1:]]  # Exclude @everyone
            
            cursor.execute("""
                INSERT OR REPLACE INTO member_roles_backup (guild_id, user_id, roles)
                VALUES (?, ?, ?)
            """, (member.guild.id, member.id, json.dumps(role_ids)))
            self.bot.db.commit()
        
        conn.close()
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Handle reaction role additions"""
        if payload.user_id == self.bot.user.id:
            return
        
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT guild_id, emoji_role_pairs, rr_type FROM reaction_roles 
            WHERE message_id = ?
        """, (payload.message_id,))
        result = cursor.fetchone()
        
        if not result:
            return
        
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        
        member = guild.get_member(payload.user_id)
        if not member:
            return
        
        pairs = json.loads(result[1])
        rr_type = result[2]
        emoji_str = str(payload.emoji)
        
        if emoji_str not in pairs:
            return
        
        role_id = pairs[emoji_str]
        role = guild.get_role(role_id)
        if not role:
            return
        
        try:
            if rr_type == "verify":
                # Verify type: only add roles, remove reaction
                await member.add_roles(role, reason="Reaction role (verify)")
                channel = guild.get_channel(payload.channel_id)
                message = await channel.fetch_message(payload.message_id)
                await message.remove_reaction(payload.emoji, member)
                
            elif rr_type == "unique":
                # Unique type: remove other roles from this message first
                for other_emoji, other_role_id in pairs.items():
                    if other_emoji != emoji_str:
                        other_role = guild.get_role(other_role_id)
                        if other_role and other_role in member.roles:
                            await member.remove_roles(other_role, reason="Reaction role (unique)")
                
                await member.add_roles(role, reason="Reaction role (unique)")
                
            else:  # normal
                if role not in member.roles:
                    await member.add_roles(role, reason="Reaction role")
                    
        except Exception as e:
            print(f"Error handling reaction role: {e}")
        
        conn.commit()
        conn.close()
    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """Handle reaction role removals"""
        if payload.user_id == self.bot.user.id:
            return
        
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT guild_id, emoji_role_pairs, rr_type FROM reaction_roles 
            WHERE message_id = ?
        """, (payload.message_id,))
        result = cursor.fetchone()
        
        if not result or result[2] != "normal":
            return
        
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        
        member = guild.get_member(payload.user_id)
        if not member:
            return
        
        pairs = json.loads(result[1])
        emoji_str = str(payload.emoji)
        
        if emoji_str not in pairs:
            return
        
        role_id = pairs[emoji_str]
        role = guild.get_role(role_id)
        if not role:
            return
        
        try:
            if role in member.roles:
                await member.remove_roles(role, reason="Reaction role removed")
        except Exception as e:
            print(f"Error removing reaction role: {e}")
        
        conn.commit()
        conn.close()
    
    # Autorole Commands
    @app_commands.command(name="autorole")
    @app_commands.describe(action="show, add, remove, reassign, blacklist", role="Role to manage")
    async def autorole_cmd(self, interaction: discord.Interaction, action: str, role: discord.Role = None):
        """Manage autoroles"""
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("❌ You need Manage Roles permission!", ephemeral=True)
            return
        
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        
        if action.lower() == "show":
            cursor.execute("""
                SELECT autoroles, reassign_roles, blacklisted_roles 
                FROM role_config WHERE guild_id = ? AND config_type = 'autorole'
            """, (interaction.guild.id,))
            result = cursor.fetchone()
            
            embed = discord.Embed(title="🤖 Autorole Settings", color=discord.Color.blue())
            
            if result:
                autoroles = json.loads(result[0]) if result[0] else []
                reassign = bool(result[1])
                blacklist = json.loads(result[2]) if result[2] else []
                
                autorole_mentions = [f"<@&{rid}>" for rid in autoroles]
                embed.add_field(name="Autoroles", value="\n".join(autorole_mentions) or "None", inline=False)
                
                embed.add_field(name="Role Reassignment", 
                              value="✅ Enabled" if reassign else "❌ Disabled", inline=True)
                
                blacklist_mentions = [f"<@&{rid}>" for rid in blacklist]
                embed.add_field(name="Blacklisted Roles", value="\n".join(blacklist_mentions) or "None", inline=False)
            else:
                embed.add_field(name="Autoroles", value="None", inline=False)
                embed.add_field(name="Role Reassignment", value="❌ Disabled", inline=True)
                embed.add_field(name="Blacklisted Roles", value="None", inline=False)
            
            await interaction.response.send_message(embed=embed)
            
        elif action.lower() == "add":
            if not role:
                await interaction.response.send_message("❌ Please specify a role to add!", ephemeral=True)
                return
            
            # Get current settings
            cursor.execute("""
                SELECT autoroles FROM role_config WHERE guild_id = ? AND config_type = 'autorole'
            """, (interaction.guild.id,))
            result = cursor.fetchone()
            
            autoroles = json.loads(result[0]) if result and result[0] else []
            
            if role.id in autoroles:
                await interaction.response.send_message(f"❌ {role.mention} is already an autorole!", ephemeral=True)
                return
            
            autoroles.append(role.id)
            
            cursor.execute("""
                INSERT OR REPLACE INTO role_config (guild_id, config_type, settings)
                VALUES (?, 'autorole', ?)
            """, (interaction.guild.id, json.dumps(autoroles)))
            conn.commit()
            
            await interaction.response.send_message(f"✅ Added {role.mention} to autoroles!")
            
        elif action.lower() == "reassign":
            cursor.execute("""
                SELECT reassign_roles FROM role_config WHERE guild_id = ? AND config_type = 'autorole'
            """, (interaction.guild.id,))
            result = cursor.fetchone()
            
            current = bool(result[0]) if result else False
            new_value = not current
            
            cursor.execute("""
                INSERT OR REPLACE INTO role_config (guild_id, config_type, settings)
                VALUES (?, 'autorole', ?)
            """, (interaction.guild.id, json.dumps({'autoroles': [], 'reassign_roles': new_value, 'blacklisted_roles': []})))
            conn.commit()
            
            status = "enabled" if new_value else "disabled"
            await interaction.response.send_message(f"✅ Role reassignment {status}!")
    
    # Timed Roles Commands
    @app_commands.command(name="timedrole")
    @app_commands.describe(action="show, add, or remove", duration="Duration (e.g., 1h, 30m)", role="Role to assign")
    async def timedrole_cmd(self, interaction: discord.Interaction, action: str, duration: str = None, role: discord.Role = None):
        """Manage timed roles"""
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("❌ You need Manage Roles permission!", ephemeral=True)
            return
        
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        
        if action.lower() == "show":
            cursor.execute("""
                SELECT role_id, delay_minutes FROM timed_roles WHERE guild_id = ?
            """, (interaction.guild.id,))
            timed_roles = cursor.fetchall()
            
            embed = discord.Embed(title="⏰ Timed Roles", color=discord.Color.green())
            
            if timed_roles:
                role_list = []
                for role_id, delay in timed_roles:
                    role = interaction.guild.get_role(role_id)
                    if role:
                        hours = delay // 60
                        minutes = delay % 60
                        time_str = f"{hours}h {minutes}m" if hours else f"{minutes}m"
                        role_list.append(f"{role.mention} - {time_str}")
                
                embed.add_field(name="Active Timed Roles", value="\n".join(role_list), inline=False)
            else:
                embed.add_field(name="Active Timed Roles", value="None", inline=False)
            
            await interaction.response.send_message(embed=embed)
            
        elif action.lower() == "add":
            if not duration or not role:
                await interaction.response.send_message("❌ Please specify both duration and role!", ephemeral=True)
                return
            
            # Parse duration
            delay_minutes = self.parse_duration(duration)
            if delay_minutes is None:
                await interaction.response.send_message("❌ Invalid duration format! Use formats like '1h', '30m', '1h30m'", ephemeral=True)
                return
            
            cursor.execute("""
                INSERT OR REPLACE INTO timed_roles (guild_id, user_id, role_id, assign_time, delay_minutes)
                VALUES (?, ?, ?, datetime('now'), ?)
            """, (interaction.guild.id, interaction.user.id, role.id, delay_minutes))
            conn.commit()
            
            hours = delay_minutes // 60
            minutes = delay_minutes % 60
            time_str = f"{hours}h {minutes}m" if hours else f"{minutes}m"
            
            await interaction.response.send_message(f"✅ Set {role.mention} to be assigned after {time_str}!")
    
    def parse_duration(self, duration_str: str) -> Optional[int]:
        """Parse duration string into minutes"""
        time_regex = re.compile(r'(\d+)([smhd])')
        matches = time_regex.findall(duration_str.lower())
        
        if not matches:
            return None
        
        total_minutes = 0
        for amount, unit in matches:
            amount = int(amount)
            if unit == 's':
                total_minutes += amount // 60
            elif unit == 'm':
                total_minutes += amount
            elif unit == 'h':
                total_minutes += amount * 60
            elif unit == 'd':
                total_minutes += amount * 1440
        
        return total_minutes if total_minutes > 0 else None
    
    # Reaction Role Commands
    @app_commands.command(name="rr-add")
    @app_commands.describe(message_id="Message ID", emoji="Emoji to use", role="Role to assign")
    async def rr_add(self, interaction: discord.Interaction, message_id: str, emoji: str, role: discord.Role):
        """Add a reaction role"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission!", ephemeral=True)
            return
        
        try:
            msg_id = int(message_id)
            
            # Try to find the message
            message = None
            for channel in interaction.guild.text_channels:
                try:
                    message = await channel.fetch_message(msg_id)
                    break
                except:
                    continue
            
            if not message:
                await interaction.response.send_message("❌ Message not found!", ephemeral=True)
                return
            
            # Add to database
            cursor = self.bot.db.get_connection().cursor()
            cursor.execute("""
                SELECT emoji_role_pairs FROM reaction_roles WHERE message_id = ?
            """, (msg_id,))
            result = cursor.fetchone()
            
            if result:
                pairs = json.loads(result[0])
            else:
                pairs = {}
            
            pairs[emoji] = role.id
            
            cursor.execute("""
                INSERT OR REPLACE INTO reaction_roles 
                (guild_id, channel_id, message_id, emoji, role_id, rr_type)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (interaction.guild.id, message.channel.id, msg_id, emoji, role.id, "normal"))
            conn.commit()
            
            # Add reaction to message
            try:
                await message.add_reaction(emoji)
            except:
                pass
            
            await interaction.response.send_message(f"✅ Added {emoji} → {role.mention} to message!")
            
        except ValueError:
            await interaction.response.send_message("❌ Invalid message ID!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    # Role Management Commands
    @app_commands.command(name="role-add")
    @app_commands.describe(member="Member to give role to", role="Role to assign")
    async def role_add(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        """Add a role to a member"""
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("❌ You need Manage Roles permission!", ephemeral=True)
            return
        
        if role in member.roles:
            await interaction.response.send_message(f"❌ {member.mention} already has {role.mention}!", ephemeral=True)
            return
        
        try:
            await member.add_roles(role, reason=f"Role added by {interaction.user}")
            await interaction.response.send_message(f"✅ Added {role.mention} to {member.mention}!")
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="role-remove")
    @app_commands.describe(member="Member to remove role from", role="Role to remove")
    async def role_remove(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        """Remove a role from a member"""
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("❌ You need Manage Roles permission!", ephemeral=True)
            return
        
        if role not in member.roles:
            await interaction.response.send_message(f"❌ {member.mention} doesn't have {role.mention}!", ephemeral=True)
            return
        
        try:
            await member.remove_roles(role, reason=f"Role removed by {interaction.user}")
            await interaction.response.send_message(f"✅ Removed {role.mention} from {member.mention}!")
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(RolesCog(bot)) 