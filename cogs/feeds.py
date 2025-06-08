import discord
from discord.ext import commands, tasks
from discord import app_commands
import sqlite3
import aiohttp
import feedparser
from datetime import datetime

class FeedsCog(commands.Cog):
    """📡 RSS Feeds & Notifications"""
    
    def __init__(self, bot):
        self.bot = bot
        self.init_database()
        self.feed_checker.start()
    
    def init_database(self):
        """Initialize feeds database"""
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        
        # RSS Feeds
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rss_feeds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                channel_id INTEGER,
                url TEXT,
                name TEXT,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                enabled BOOLEAN DEFAULT TRUE,
                created_by INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Feed entries (to track what we've already posted)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feed_entries (
                feed_id INTEGER,
                entry_id TEXT,
                posted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (feed_id, entry_id)
            )
        """)
        
        conn.commit()
        conn.close()

    @app_commands.command(name="rss-add", description="Add an RSS feed")
    @app_commands.describe(url="RSS feed URL", name="Name for this feed", channel="Channel to post in")
    async def rss_add(self, interaction: discord.Interaction, url: str, name: str, channel: discord.TextChannel = None):
        """Add an RSS feed"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission to add RSS feeds.", ephemeral=True)
            return
        
        if channel is None:
            channel = interaction.channel
        
        # Test the RSS feed
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        await interaction.response.send_message("❌ Could not access RSS feed. Check the URL.", ephemeral=True)
                        return
                    
                    content = await response.text()
                    feed = feedparser.parse(content)
                    
                    if not feed.entries:
                        await interaction.response.send_message("❌ No entries found in RSS feed.", ephemeral=True)
                        return
        
        except Exception as e:
            await interaction.response.send_message(f"❌ Error testing RSS feed: {str(e)}", ephemeral=True)
            return
        
        # Add to database
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO rss_feeds (guild_id, channel_id, url, name, created_by)
            VALUES (?, ?, ?, ?, ?)
        """, (interaction.guild.id, channel.id, url, name, interaction.user.id))
        
        feed_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        embed = discord.Embed(title="📡 RSS Feed Added", color=0x27ae60)
        embed.add_field(name="Name", value=name, inline=True)
        embed.add_field(name="Channel", value=channel.mention, inline=True)
        embed.add_field(name="Feed ID", value=feed_id, inline=True)
        embed.add_field(name="URL", value=url[:100] + ("..." if len(url) > 100 else ""), inline=False)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="rss-list", description="List all RSS feeds")
    async def rss_list(self, interaction: discord.Interaction):
        """List all RSS feeds"""
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, url, channel_id, enabled, last_updated
            FROM rss_feeds WHERE guild_id = ?
            ORDER BY created_at DESC
        """, (interaction.guild.id,))
        
        feeds = cursor.fetchall()
        conn.close()
        
        if not feeds:
            await interaction.response.send_message("📭 No RSS feeds configured.")
            return
        
        embed = discord.Embed(title="📡 RSS Feeds", color=0x3498db)
        
        for feed_id, name, url, channel_id, enabled, last_updated in feeds[:10]:
            channel = self.bot.get_channel(channel_id)
            channel_name = channel.mention if channel else "Deleted Channel"
            
            status = "✅ Enabled" if enabled else "❌ Disabled"
            
            embed.add_field(
                name=f"#{feed_id} - {name}",
                value=f"**Channel:** {channel_name}\n**Status:** {status}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="rss-remove", description="Remove an RSS feed")
    @app_commands.describe(feed_id="ID of the feed to remove")
    async def rss_remove(self, interaction: discord.Interaction, feed_id: int):
        """Remove an RSS feed"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission to remove RSS feeds.", ephemeral=True)
            return
        
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        
        # Check if feed exists
        cursor.execute("""
            SELECT name FROM rss_feeds 
            WHERE id = ? AND guild_id = ?
        """, (feed_id, interaction.guild.id))
        
        result = cursor.fetchone()
        if not result:
            await interaction.response.send_message("❌ RSS feed not found.", ephemeral=True)
            conn.close()
            return
        
        feed_name = result[0]
        
        # Remove feed and entries
        cursor.execute("DELETE FROM rss_feeds WHERE id = ?", (feed_id,))
        cursor.execute("DELETE FROM feed_entries WHERE feed_id = ?", (feed_id,))
        
        conn.commit()
        conn.close()
        
        await interaction.response.send_message(f"✅ Removed RSS feed '{feed_name}' (#{feed_id}).")

    @tasks.loop(minutes=15)
    async def feed_checker(self):
        """Check all feeds for updates"""
        await self.check_rss_feeds()

    @feed_checker.before_loop
    async def before_feed_checker(self):
        await self.bot.wait_until_ready()

    async def check_rss_feeds(self):
        """Check RSS feeds for new posts"""
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, guild_id, channel_id, url, name, last_updated
            FROM rss_feeds WHERE enabled = TRUE
        """)
        
        feeds = cursor.fetchall()
        
        for feed_id, guild_id, channel_id, url, name, last_updated in feeds:
            try:
                # Parse feed
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=10) as response:
                        if response.status != 200:
                            continue
                        
                        content = await response.text()
                        feed = feedparser.parse(content)
                
                # Check for new entries
                for entry in feed.entries[:3]:  # Check latest 3
                    entry_id = entry.get('id', entry.get('link', ''))
                    
                    # Check if we've already posted this
                    cursor.execute("""
                        SELECT 1 FROM feed_entries WHERE feed_id = ? AND entry_id = ?
                    """, (feed_id, entry_id))
                    
                    if cursor.fetchone():
                        continue  # Already posted
                    
                    # Post to Discord
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        await self.post_rss_entry(channel, entry, name)
                        
                        # Mark as posted
                        cursor.execute("""
                            INSERT INTO feed_entries (feed_id, entry_id) VALUES (?, ?)
                        """, (feed_id, entry_id))
                
                # Update last checked time
                cursor.execute("""
                    UPDATE rss_feeds SET last_updated = CURRENT_TIMESTAMP WHERE id = ?
                """, (feed_id,))
                
            except Exception as e:
                print(f"Error checking RSS feed {feed_id}: {e}")
        
        conn.commit()
        conn.close()

    async def post_rss_entry(self, channel: discord.TextChannel, entry: dict, feed_name: str):
        """Post an RSS entry to Discord"""
        title = entry.get('title', 'No Title')
        link = entry.get('link', '')
        summary = entry.get('summary', '')
        
        embed = discord.Embed(
            title=title[:256],
            url=link,
            description=summary[:500] + ("..." if len(summary) > 500 else "") if summary else None,
            color=0x3498db
        )
        
        embed.set_author(name=feed_name)
        
        try:
            await channel.send(embed=embed)
        except discord.HTTPException:
            # Fallback to simple message
            await channel.send(f"**{feed_name}**\n{title}\n{link}")

async def setup(bot):
    await bot.add_cog(FeedsCog(bot)) 