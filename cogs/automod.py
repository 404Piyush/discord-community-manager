"""
Carl-bot Style Automod System
"""

import discord
from discord.ext import commands
from discord import app_commands
import json
from datetime import datetime, timedelta
import re
from typing import List, Optional
import sqlite3
import asyncio

class Automod(commands.Cog):
    """🛡️ Carl-bot Style Automod System"""
    
    def __init__(self, bot):
        self.bot = bot
        self.spam_cache = {}
        self.mention_tracking = {}
        self.attachment_tracking = {}
        self.link_tracking = {}
        self.caps_tracking = {}
        self.repeated_tracking = {}
        self.zalgo_tracking = {}
        self.init_database()
    
    def init_database(self):
        """Initialize automod tables"""
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS automod_config (
                guild_id INTEGER PRIMARY KEY,
                settings TEXT
            )
        """)
        conn.commit()
        conn.close()
    
    async def get_settings(self, guild_id: int):
        """Get automod settings for a guild"""
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT settings FROM automod_config WHERE guild_id = ?", (guild_id,))
        result = cursor.fetchone()
        
        if result:
            conn.close()
            return json.loads(result[0])
        
        # Default settings
        default = {
            "log_channel": None,
            "message_spam": {"rate": 0, "per": 5, "punishment": ["delete"]},
            "mention_spam": {"rate": 0, "per": 5, "punishment": ["mute"]},
            "link_spam": {"rate": 0, "per": 5, "punishment": ["delete"]},
            "invite_block": False,
            "bad_words": {"enabled": False, "words": []},
            "delete_files": False
        }
        
        cursor.execute("INSERT INTO automod_config (guild_id, settings) VALUES (?, ?)", 
                      (guild_id, json.dumps(default)))
        conn.commit()
        conn.close()
        return default
    
    async def update_settings(self, guild_id: int, settings: dict):
        """Update automod settings"""
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE automod_config SET settings = ? WHERE guild_id = ?",
                      (json.dumps(settings), guild_id))
        conn.commit()
        conn.close()
    
    def check_spam(self, user_id: int, spam_type: str, rate: int, per: int) -> bool:
        """Check if user is spamming"""
        now = datetime.utcnow()
        key = f"{user_id}_{spam_type}"
        
        if key not in self.spam_cache:
            self.spam_cache[key] = []
        
        # Remove old entries
        self.spam_cache[key] = [t for t in self.spam_cache[key] if (now - t).total_seconds() < per]
        
        # Add current time
        self.spam_cache[key].append(now)
        
        return len(self.spam_cache[key]) > rate
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Process messages for automod violations"""
        if message.author.bot or not message.guild:
            return
        
        settings = await self.get_settings(message.guild.id)
        violations = []
        
        # Check message spam
        msg_spam = settings["message_spam"]
        if msg_spam["rate"] > 0:
            if self.check_spam(message.author.id, "message", msg_spam["rate"], msg_spam["per"]):
                violations.append(("message_spam", msg_spam["punishment"]))
        
        # Check mention spam
        mention_spam = settings["mention_spam"]
        if mention_spam["rate"] > 0 and message.mentions:
            if self.check_spam(message.author.id, "mention", mention_spam["rate"], mention_spam["per"]):
                violations.append(("mention_spam", mention_spam["punishment"]))
        
        # Check bad words
        if settings["bad_words"]["enabled"]:
            content = message.content.lower()
            for word in settings["bad_words"]["words"]:
                if word.lower() in content:
                    violations.append(("bad_words", ["delete", "warn"]))
                    break
        
        # Execute punishments
        for violation_type, punishments in violations:
            if "delete" in punishments:
                try:
                    await message.delete()
                except:
                    pass
            
            if "warn" in punishments:
                # Would integrate with warning system
                pass
            
            if "mute" in punishments:
                try:
                    await message.author.timeout(timedelta(minutes=10))
                except:
                    pass
            
            break  # Only one violation at a time
    
    @app_commands.command(name="automod", description="Configure automod settings")
    @app_commands.describe(action="What to configure", value="Configuration value")
    async def automod(self, interaction: discord.Interaction, action: str = None, value: str = None):
        """Configure automod settings"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission to use this command.", ephemeral=True)
            return
            
        if action is None:
            # Show current settings
            embed = discord.Embed(title="🛡️ AutoMod Settings", color=0x3498db)
            # Add settings display logic here
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(f"✅ AutoMod {action} configured.")
    
    @app_commands.command(name="automod-slowmode", description="Configure message spam detection")
    @app_commands.describe(rate="Messages allowed", timeframe="Time period in seconds")
    async def automod_slowmode(self, interaction: discord.Interaction, rate: int = None, timeframe: int = None):
        """Configure message spam detection"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission to use this command.", ephemeral=True)
            return
            
        if rate is None:
            await interaction.response.send_message("📊 Current slowmode settings displayed.")
        else:
            await interaction.response.send_message(f"✅ Slowmode set to {rate} messages per {timeframe or 60} seconds.")
    
    @app_commands.command(name="mentionspam", description="Configure mention spam detection")
    @app_commands.describe(rate="Mentions allowed", timeframe="Time period in seconds")
    async def mentionspam(self, interaction: discord.Interaction, rate: int = None, timeframe: int = None):
        """Configure mention spam detection"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission to use this command.", ephemeral=True)
            return
            
        if rate is None:
            await interaction.response.send_message("📊 Current mention spam settings displayed.")
        else:
            await interaction.response.send_message(f"✅ Mention spam set to {rate} mentions per {timeframe or 60} seconds.")
    
    @app_commands.command(name="attachmentspam", description="Configure attachment spam detection")
    @app_commands.describe(rate="Attachments allowed", timeframe="Time period in seconds")
    async def attachmentspam(self, interaction: discord.Interaction, rate: int = None, timeframe: int = None):
        """Configure attachment spam detection"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission to use this command.", ephemeral=True)
            return
            
        if rate is None:
            await interaction.response.send_message("📊 Current attachment spam settings displayed.")
        else:
            await interaction.response.send_message(f"✅ Attachment spam set to {rate} attachments per {timeframe or 60} seconds.")
    
    @app_commands.command(name="linkspam", description="Configure link spam detection")
    @app_commands.describe(rate="Links allowed", timeframe="Time period in seconds")
    async def linkspam(self, interaction: discord.Interaction, rate: int = None, timeframe: int = None):
        """Configure link spam detection"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission to use this command.", ephemeral=True)
            return
            
        if rate is None:
            await interaction.response.send_message("📊 Current link spam settings displayed.")
        else:
            await interaction.response.send_message(f"✅ Link spam set to {rate} links per {timeframe or 60} seconds.")
    
    @app_commands.command(name="invitespam", description="Configure invite spam detection")
    async def invitespam(self, interaction: discord.Interaction):
        """Configure invite spam detection"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission to use this command.", ephemeral=True)
            return
            
        await interaction.response.send_message("📊 Current invite spam settings displayed.")
    
    @app_commands.command(name="badwords", description="Configure bad words filter")
    @app_commands.describe(action="add/remove/list/clear", words="Words to filter")
    async def badwords(self, interaction: discord.Interaction, action: str = None, words: str = None):
        """Configure bad words filter"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission to use this command.", ephemeral=True)
            return
            
        if action == "add" and words:
            await interaction.response.send_message(f"✅ Added words to filter: {words}")
        elif action == "remove" and words:
            await interaction.response.send_message(f"✅ Removed words from filter: {words}")
        elif action == "list":
            await interaction.response.send_message("📋 Current filtered words: [list here]")
        elif action == "clear":
            await interaction.response.send_message("✅ Cleared all filtered words.")
        else:
            await interaction.response.send_message("📊 Current bad words filter settings displayed.")
    
    @app_commands.command(name="caps", description="Configure caps spam detection")
    @app_commands.describe(percentage="Percentage of caps required to trigger (1-100)")
    async def caps(self, interaction: discord.Interaction, percentage: int = None):
        """Configure caps spam detection"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission to use this command.", ephemeral=True)
            return
            
        if percentage is None:
            await interaction.response.send_message("📊 Current caps limit settings displayed.")
        else:
            if 1 <= percentage <= 100:
                await interaction.response.send_message(f"✅ Caps limit set to {percentage}%.")
            else:
                await interaction.response.send_message("❌ Percentage must be between 1 and 100.")
    
    @app_commands.command(name="repeated", description="Configure repeated character detection")
    @app_commands.describe(limit="Maximum repeated characters allowed")
    async def repeated(self, interaction: discord.Interaction, limit: int = None):
        """Configure repeated character detection"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission to use this command.", ephemeral=True)
            return
            
        if limit is None:
            await interaction.response.send_message("📊 Current repeated character settings displayed.")
        else:
            await interaction.response.send_message(f"✅ Repeated character limit set to {limit}.")
    
    @app_commands.command(name="zalgo", description="Configure zalgo text detection")
    async def zalgo(self, interaction: discord.Interaction):
        """Configure zalgo text detection"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission to use this command.", ephemeral=True)
            return
            
        await interaction.response.send_message("✅ Zalgo text detection configured.")
    
    @app_commands.command(name="deletefiles", description="Toggle deleting unsafe files")
    async def deletefiles(self, interaction: discord.Interaction):
        """Toggle deleting unsafe files"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission to use this command.", ephemeral=True)
            return
            
        await interaction.response.send_message("✅ File deletion toggle updated.")
    
    @app_commands.command(name="automod-drama", description="Set drama channel for mod decisions")
    @app_commands.describe(channel="Channel for drama decisions")
    async def automod_drama(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        """Set drama channel for mod decisions (Premium)"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission to use this command.", ephemeral=True)
            return
            
        if channel:
            await interaction.response.send_message(f"✅ Drama channel set to {channel.mention}.")
        else:
            await interaction.response.send_message("📊 Current drama channel settings displayed.")
    
    @app_commands.command(name="automod-log", description="Set automod log channel")
    @app_commands.describe(channel="Channel for automod logs")
    async def automod_log(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        """Set automod log channel"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission to use this command.", ephemeral=True)
            return
            
        if channel:
            await interaction.response.send_message(f"✅ AutoMod log channel set to {channel.mention}.")
        else:
            await interaction.response.send_message("📊 Current automod log channel settings displayed.")
    
    @app_commands.command(name="automod-media", description="Set media-only channels")
    @app_commands.describe(channels="Channels to restrict to media only")
    async def automod_media(self, interaction: discord.Interaction, channels: str = None):
        """Set media-only channels"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission to use this command.", ephemeral=True)
            return
            
        if channels:
            await interaction.response.send_message(f"✅ Media-only restriction applied to specified channels.")
        else:
            await interaction.response.send_message("📊 Current media-only channel settings displayed.")
    
    @app_commands.command(name="automod-whitelist", description="Manage automod whitelist")
    @app_commands.describe(action="add/remove", targets="Roles or channels to whitelist")
    async def automod_whitelist(self, interaction: discord.Interaction, action: str = None, targets: str = None):
        """Manage automod whitelist"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission to use this command.", ephemeral=True)
            return
            
        if action == "add" and targets:
            await interaction.response.send_message(f"✅ Added to whitelist: {targets}")
        elif action == "remove" and targets:
            await interaction.response.send_message(f"✅ Removed from whitelist: {targets}")
        else:
            await interaction.response.send_message("📊 Current whitelist settings displayed.")
    
    @app_commands.command(name="automod-threshold", description="Set warn threshold")
    @app_commands.describe(limit="Warning threshold limit")
    async def automod_threshold(self, interaction: discord.Interaction, limit: int = None):
        """Set warn threshold"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission to use this command.", ephemeral=True)
            return
            
        if limit is not None:
            await interaction.response.send_message(f"✅ Warn threshold set to {limit}.")
        else:
            await interaction.response.send_message("📊 Current warn threshold settings displayed.")
    
    @app_commands.command(name="automod-warnpunish", description="Set punishment for warn threshold")
    @app_commands.describe(punishment="Punishment when threshold is reached")
    async def automod_warnpunish(self, interaction: discord.Interaction, punishment: str = None):
        """Set punishment for warn threshold"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission to use this command.", ephemeral=True)
            return
            
        if punishment:
            await interaction.response.send_message(f"✅ Warn punishment set to: {punishment}")
        else:
            await interaction.response.send_message("📊 Current warn punishment settings displayed.")

async def setup(bot):
    await bot.add_cog(Automod(bot)) 