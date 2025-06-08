"""
Carl-bot Style Starboard System
"""

import discord
from discord.ext import commands
from discord import app_commands
import json
import random
from datetime import datetime
from typing import Optional
import sqlite3
import logging

logger = logging.getLogger('discord_bot')

class Starboard(commands.Cog):
    """⭐ Carl-bot Style Starboard System"""
    
    def __init__(self, bot):
        self.bot = bot
        self.init_database()
    
    def init_database(self):
        """Initialize starboard tables"""
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        
        # Starboard configuration
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS starboard_config (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER,
                star_limit INTEGER DEFAULT 3,
                star_emoji TEXT DEFAULT '⭐',
                self_star INTEGER DEFAULT 0,
                nsfw_allowed INTEGER DEFAULT 0,
                enabled INTEGER DEFAULT 1
            )
        """)
        
        # Starred messages
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS starred_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                channel_id INTEGER,
                message_id INTEGER,
                author_id INTEGER,
                starboard_message_id INTEGER,
                star_count INTEGER DEFAULT 0,
                created_at INTEGER DEFAULT (strftime('%s', 'now')),
                UNIQUE(guild_id, message_id)
            )
        """)
        
        # Star givers tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS star_givers (
                guild_id INTEGER,
                message_id INTEGER,
                user_id INTEGER,
                PRIMARY KEY (guild_id, message_id, user_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def get_starboard_config(self, guild_id: int):
        """Get starboard configuration for a guild"""
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT channel_id, star_limit, nsfw_allowed, self_star, enabled
            FROM starboard_config WHERE guild_id = ?
        """, (guild_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'channel_id': result[0],
                'star_limit': result[1],
                'nsfw_allowed': bool(result[2]),
                'self_star': bool(result[3]),
                'enabled': bool(result[4])
            }
        return None
    
    async def update_starboard_config(self, guild_id: int, **kwargs):
        """Update starboard configuration"""
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        
        # Get current config or create default
        config = await self.get_starboard_config(guild_id)
        if not config:
            config = {
                'channel_id': None,
                'star_limit': 3,
                'nsfw_allowed': False,
                'self_star': False,
                'enabled': True
            }
        
        # Update with provided values
        config.update(kwargs)
        
        cursor.execute("""
            INSERT OR REPLACE INTO starboard_config 
            (guild_id, channel_id, star_limit, nsfw_allowed, self_star, enabled)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (guild_id, config['channel_id'], config['star_limit'], 
              config['nsfw_allowed'], config['self_star'], config['enabled']))
        conn.commit()
        conn.close()
    
    async def get_starred_message(self, guild_id: int, original_message_id: int):
        """Get starred message data"""
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, starboard_message_id, star_count FROM starred_messages
            WHERE guild_id = ? AND message_id = ?
        """, (guild_id, original_message_id))
        result = cursor.fetchone()
        conn.close()
        return result
    
    async def create_starboard_embed(self, message: discord.Message, star_count: int):
        """Create embed for starboard message"""
        embed = discord.Embed(
            description=message.content or "*No text content*",
            color=0xFFD700,  # Gold color
            timestamp=message.created_at
        )
        
        embed.set_author(
            name=f"{message.author.display_name}",
            icon_url=message.author.display_avatar.url
        )
        
        embed.add_field(
            name="Original Message",
            value=f"[Jump to Message]({message.jump_url})",
            inline=True
        )
        
        embed.add_field(
            name="Channel",
            value=message.channel.mention,
            inline=True
        )
        
        # Handle attachments
        if message.attachments:
            attachment = message.attachments[0]
            if attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                embed.set_image(url=attachment.url)
            else:
                embed.add_field(
                    name="Attachment",
                    value=f"[{attachment.filename}]({attachment.url})",
                    inline=False
                )
        
        # Handle embeds from original message
        if message.embeds:
            original_embed = message.embeds[0]
            if original_embed.image:
                embed.set_image(url=original_embed.image.url)
            elif original_embed.thumbnail:
                embed.set_thumbnail(url=original_embed.thumbnail.url)
        
        embed.set_footer(text=f"⭐ {star_count} | ID: {message.id}")
        
        return embed
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Handle star reactions"""
        if str(payload.emoji) != "⭐":
            return
        
        if payload.user_id == self.bot.user.id:
            return
        
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        
        config = await self.get_starboard_config(guild.id)
        if not config or not config['channel_id'] or not config['enabled']:
            return
        
        channel = guild.get_channel(payload.channel_id)
        if not channel:
            return
        
        # Check if channel is blacklisted
        if payload.channel_id in config['blacklisted_channels']:
            return
        
        # Check NSFW setting
        if not config['nsfw_allowed'] and getattr(channel, 'nsfw', False):
            return
        
        try:
            message = await channel.fetch_message(payload.message_id)
        except:
            return
        
        # Check self-star setting
        if not config['self_star'] and payload.user_id == message.author.id:
            return
        
        # Check if user already starred this message
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 1 FROM star_givers WHERE message_id = ? AND user_id = ?
        """, (payload.message_id, payload.user_id))
        
        if cursor.fetchone():
            conn.close()
            return  # User already starred this message
        
        # Add star giver
        cursor.execute("""
            INSERT INTO star_givers (guild_id, message_id, user_id) VALUES (?, ?, ?)
        """, (guild.id, payload.message_id, payload.user_id))
        
        # Get current star count
        cursor.execute("""
            SELECT COUNT(*) FROM star_givers WHERE message_id = ?
        """, (payload.message_id,))
        star_count = cursor.fetchone()[0]
        
        # Check if message meets star limit
        if star_count >= config['star_limit']:
            await self.add_to_starboard(message, star_count, config)
        
        conn.commit()
        conn.close()
    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """Handle star reaction removal"""
        if str(payload.emoji) != "⭐":
            return
        
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        
        config = await self.get_starboard_config(guild.id)
        if not config or not config['enabled']:
            return
        
        # Remove star giver
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM star_givers WHERE message_id = ? AND user_id = ?
        """, (payload.message_id, payload.user_id))
        
        # Get new star count
        cursor.execute("""
            SELECT COUNT(*) FROM star_givers WHERE message_id = ?
        """, (payload.message_id,))
        star_count = cursor.fetchone()[0]
        
        # Update or remove from starboard
        if star_count >= config['star_limit']:
            await self.update_starboard_message(payload.message_id, star_count, config)
        else:
            # Remove from starboard if below limit
            starred = await self.get_starred_message(guild.id, payload.message_id)
            if starred:
                try:
                    starboard_channel = guild.get_channel(config['channel_id'])
                    if starboard_channel:
                        starboard_message = await starboard_channel.fetch_message(starred[1])
                        await starboard_message.delete()
                except:
                    pass
                
                cursor.execute("""
                    DELETE FROM starred_messages WHERE guild_id = ? AND message_id = ?
                """, (guild.id, payload.message_id))
        
        conn.commit()
        conn.close()
    
    async def add_to_starboard(self, message: discord.Message, star_count: int, config: dict):
        """Add message to starboard"""
        starboard_channel = message.guild.get_channel(config['channel_id'])
        if not starboard_channel:
            return
        
        # Check if already on starboard
        starred = await self.get_starred_message(message.guild.id, message.id)
        if starred:
            await self.update_starboard_message(message.id, star_count, config)
            return
        
        embed = await self.create_starboard_embed(message, star_count)
        
        try:
            starboard_message = await starboard_channel.send(embed=embed)
            
            # Save to database
            conn = self.bot.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO starred_messages 
                (guild_id, channel_id, message_id, author_id, starboard_message_id, star_count)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (message.guild.id, message.channel.id, message.id, message.author.id, 
                  starboard_message.id, star_count))
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error adding to starboard: {e}")
    
    async def update_starboard_message(self, original_message_id: int, star_count: int, config: dict):
        """Update existing starboard message"""
        guild_id = config.get('guild_id')  # Assume guild_id is passed in config
        starred = await self.get_starred_message(guild_id, original_message_id)
        if not starred:
            return
        
        try:
            guild = self.bot.get_guild(guild_id)
            starboard_channel = guild.get_channel(config['channel_id'])
            if not starboard_channel:
                return
            
            starboard_message = await starboard_channel.fetch_message(starred[1])
            
            # Get original message
            original_channel = guild.get_channel(starred[5])  # Assuming channel_id is at index 5
            if original_channel:
                original_message = await original_channel.fetch_message(original_message_id)
                embed = await self.create_starboard_embed(original_message, star_count)
                await starboard_message.edit(embed=embed)
                
                # Update database
                conn = self.bot.db.get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE starred_messages SET star_count = ? 
                    WHERE guild_id = ? AND message_id = ?
                """, (star_count, guild_id, original_message_id))
                conn.commit()
                conn.close()
                
        except Exception as e:
            print(f"Error updating starboard message: {e}")
    
    # Starboard Commands
    @app_commands.command(name="starboard")
    @app_commands.describe(channel="Channel for starboard")
    async def starboard_setup(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        """Set up or configure the starboard"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission!", ephemeral=True)
            return
        
        if channel is None:
            # Show current config
            config = await self.get_starboard_config(interaction.guild.id)
            if config and config['channel_id']:
                starboard_channel = interaction.guild.get_channel(config['channel_id'])
                embed = discord.Embed(title="⭐ Starboard Configuration", color=discord.Color.gold())
                embed.add_field(name="Channel", value=starboard_channel.mention if starboard_channel else "Not found", inline=False)
                embed.add_field(name="Star Limit", value=str(config['star_limit']), inline=True)
                embed.add_field(name="NSFW Allowed", value="Yes" if config['nsfw_allowed'] else "No", inline=True)
                embed.add_field(name="Self Stars", value="Yes" if config['self_star'] else "No", inline=True)
                embed.add_field(name="Enabled", value="Yes" if config['enabled'] else "No", inline=True)
            else:
                embed = discord.Embed(title="⭐ Starboard Not Configured", color=discord.Color.red())
                embed.description = "Use `/starboard #channel` to set up the starboard"
            
            await interaction.response.send_message(embed=embed)
        else:
            # Set starboard channel
            await self.update_starboard_config(interaction.guild.id, channel_id=channel.id)
            await interaction.response.send_message(f"✅ Starboard set to {channel.mention}")
    
    @app_commands.command(name="star-limit")
    @app_commands.describe(limit="Number of stars required")
    async def star_limit(self, interaction: discord.Interaction, limit: int):
        """Set the star limit for starboard"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission!", ephemeral=True)
            return
        
        if limit < 1 or limit > 50:
            await interaction.response.send_message("❌ Star limit must be between 1 and 50!", ephemeral=True)
            return
        
        await self.update_starboard_config(interaction.guild.id, star_limit=limit)
        await interaction.response.send_message(f"✅ Star limit set to {limit}")
    
    @app_commands.command(name="star-nsfw")
    async def star_nsfw(self, interaction: discord.Interaction):
        """Toggle NSFW channel starboard support"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission!", ephemeral=True)
            return
        
        config = await self.get_starboard_config(interaction.guild.id)
        new_value = not (config['nsfw_allowed'] if config else False)
        
        await self.update_starboard_config(interaction.guild.id, nsfw_allowed=new_value)
        status = "enabled" if new_value else "disabled"
        await interaction.response.send_message(f"✅ NSFW starboard {status}")
    
    @app_commands.command(name="star-self")
    async def star_self(self, interaction: discord.Interaction):
        """Toggle self-starring"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission!", ephemeral=True)
            return
        
        config = await self.get_starboard_config(interaction.guild.id)
        new_value = not (config['self_star'] if config else False)
        
        await self.update_starboard_config(interaction.guild.id, self_star=new_value)
        status = "enabled" if new_value else "disabled"
        await interaction.response.send_message(f"✅ Self-starring {status}")
    
    @app_commands.command(name="star-stats")
    @app_commands.describe(member="Member to show stats for")
    async def star_stats(self, interaction: discord.Interaction, member: discord.Member = None):
        """Show starboard statistics"""
        target = member or interaction.user
        
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        
        # Get messages on starboard by user
        cursor.execute("""
            SELECT COUNT(*), SUM(star_count) FROM starred_messages 
            WHERE guild_id = ? AND author_id = ?
        """, (interaction.guild.id, target.id))
        authored_result = cursor.fetchone()
        
        # Get stars given by user
        cursor.execute("""
            SELECT COUNT(*) FROM star_givers sg
            JOIN starred_messages sm ON sg.message_id = sm.message_id
            WHERE sm.guild_id = ? AND sg.user_id = ?
        """, (interaction.guild.id, target.id))
        given_result = cursor.fetchone()
        
        conn.close()
        
        messages_count = authored_result[0] or 0
        total_stars = authored_result[1] or 0
        stars_given = given_result[0] or 0
        
        embed = discord.Embed(
            title=f"⭐ Starboard Stats for {target.display_name}",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        
        embed.add_field(name="Messages on Starboard", value=str(messages_count), inline=True)
        embed.add_field(name="Total Stars Received", value=str(total_stars), inline=True)
        embed.add_field(name="Stars Given", value=str(stars_given), inline=True)
        
        if messages_count > 0:
            avg_stars = total_stars / messages_count
            embed.add_field(name="Average Stars per Message", value=f"{avg_stars:.1f}", inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="star-random")
    async def star_random(self, interaction: discord.Interaction):
        """Show a random starred message"""
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT channel_id, message_id, star_count 
            FROM starred_messages WHERE guild_id = ?
            ORDER BY RANDOM() LIMIT 1
        """, (interaction.guild.id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            await interaction.response.send_message("📭 No starred messages found!", ephemeral=True)
            return
        
        try:
            channel = interaction.guild.get_channel(result[0])
            message = await channel.fetch_message(result[1])
            embed = await self.create_starboard_embed(message, result[2])
            await interaction.response.send_message(embed=embed)
        except:
            await interaction.response.send_message("❌ Could not fetch that message!", ephemeral=True)
    
    @app_commands.command(name="star-show")
    @app_commands.describe(message_id="Message ID to show")
    async def star_show(self, interaction: discord.Interaction, message_id: str):
        """Show a specific starred message"""
        try:
            msg_id = int(message_id)
        except ValueError:
            await interaction.response.send_message("❌ Invalid message ID!", ephemeral=True)
            return
        
        starred = await self.get_starred_message(interaction.guild.id, msg_id)
        if not starred:
            await interaction.response.send_message("❌ Message not found on starboard!", ephemeral=True)
            return
        
        try:
            # Get the original message
            for channel in interaction.guild.channels:
                if isinstance(channel, discord.TextChannel):
                    try:
                        message = await channel.fetch_message(msg_id)
                        embed = await self.create_starboard_embed(message, starred[2])
                        await interaction.response.send_message(embed=embed)
                        return
                    except:
                        continue
            
            await interaction.response.send_message("❌ Could not fetch that message!", ephemeral=True)
        except:
            await interaction.response.send_message("❌ Error fetching message!", ephemeral=True)
    
    @app_commands.command(name="star-config")
    async def star_config(self, interaction: discord.Interaction):
        """Show detailed starboard configuration"""
        config = await self.get_starboard_config(interaction.guild.id)
        
        if not config:
            embed = discord.Embed(title="⭐ Starboard Not Configured", color=discord.Color.red())
            embed.description = "Use `/starboard #channel` to set up the starboard"
        else:
            embed = discord.Embed(title="⭐ Starboard Configuration", color=discord.Color.gold())
            
            channel = interaction.guild.get_channel(config['channel_id']) if config['channel_id'] else None
            embed.add_field(name="Channel", value=channel.mention if channel else "Not set", inline=False)
            embed.add_field(name="Star Limit", value=str(config['star_limit']), inline=True)
            embed.add_field(name="NSFW Allowed", value="Yes" if config['nsfw_allowed'] else "No", inline=True)
            embed.add_field(name="Self Stars", value="Yes" if config['self_star'] else "No", inline=True)
            embed.add_field(name="Enabled", value="Yes" if config['enabled'] else "No", inline=True)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Starboard(bot)) 