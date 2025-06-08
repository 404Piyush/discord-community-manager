"""
Carl-bot Style Utilities
"""

import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import re
from datetime import datetime, timedelta
from typing import Optional, List
import asyncio
import urllib.parse
import aiohttp

class UtilsCog(commands.Cog):
    """🛠️ Utility Commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.reminder_check.start()
        self.init_database()
        self.deleted_messages = {}
        self.edited_messages = {}
        self.highlights = {}
        self.giveaways = {}
        self.polls = {}
    
    def init_database(self):
        """Initialize utilities tables"""
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        
        # Reminders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                guild_id INTEGER,
                channel_id INTEGER,
                message TEXT,
                remind_at DATETIME,
                repeat_interval INTEGER DEFAULT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Highlights table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS highlights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                guild_id INTEGER,
                keyword TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Highlight blocks (users/channels to ignore)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS highlight_blocks (
                user_id INTEGER,
                guild_id INTEGER,
                blocked_id INTEGER,
                block_type TEXT, -- 'user' or 'channel'
                PRIMARY KEY (user_id, guild_id, blocked_id, block_type)
            )
        """)
        
        # Poll tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS polls (
                message_id INTEGER PRIMARY KEY,
                guild_id INTEGER,
                creator_id INTEGER,
                question TEXT,
                options TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    @tasks.loop(minutes=1)
    async def reminder_check(self):
        """Check for due reminders"""
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, guild_id, channel_id, message, repeat_interval
            FROM reminders WHERE remind_at <= ?
        """, (datetime.utcnow(),))
        
        due_reminders = cursor.fetchall()
        
        for reminder in due_reminders:
            try:
                user = self.bot.get_user(reminder[1])
                if user:
                    embed = discord.Embed(
                        title="⏰ Reminder",
                        description=reminder[4],
                        color=discord.Color.blue(),
                        timestamp=datetime.utcnow()
                    )
                    
                    try:
                        await user.send(embed=embed)
                    except:
                        # If DM fails, try to send in the original channel
                        if reminder[3]:
                            channel = self.bot.get_channel(reminder[3])
                            if channel:
                                await channel.send(f"{user.mention}", embed=embed)
                
                # Handle repeating reminders
                if reminder[5]:  # repeat_interval
                    new_time = datetime.utcnow() + timedelta(seconds=reminder[5])
                    cursor.execute("""
                        UPDATE reminders SET remind_at = ? WHERE id = ?
                    """, (new_time, reminder[0]))
                else:
                    # Delete one-time reminder
                    cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder[0],))
                
            except Exception as e:
                print(f"Error processing reminder: {e}")
                cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder[0],))
        
        conn.commit()
        conn.close()
    
    @reminder_check.before_loop
    async def before_reminder_check(self):
        await self.bot.wait_until_ready()
    
    def parse_time(self, time_str: str) -> Optional[timedelta]:
        """Parse time string into timedelta"""
        time_regex = re.compile(r'(\d+)([smhd])')
        matches = time_regex.findall(time_str.lower())
        
        if not matches:
            return None
        
        total_seconds = 0
        for amount, unit in matches:
            amount = int(amount)
            if unit == 's':
                total_seconds += amount
            elif unit == 'm':
                total_seconds += amount * 60
            elif unit == 'h':
                total_seconds += amount * 3600
            elif unit == 'd':
                total_seconds += amount * 86400
        
        return timedelta(seconds=total_seconds) if total_seconds > 0 else None
    
    # Information Commands
    @app_commands.command(name="member-info", description="Get information about a member")
    @app_commands.describe(member="Member to get info about")
    async def member_info(self, interaction: discord.Interaction, member: discord.Member = None):
        """Get information about a member"""
        if member is None:
            member = interaction.user
            
        embed = discord.Embed(title=f"Member Information", color=0x3498db)
        embed.set_thumbnail(url=member.display_avatar.url)
        
        embed.add_field(name="Username", value=f"{member.name}#{member.discriminator}", inline=True)
        embed.add_field(name="Display Name", value=member.display_name, inline=True)
        embed.add_field(name="ID", value=member.id, inline=True)
        
        embed.add_field(name="Account Created", value=f"<t:{int(member.created_at.timestamp())}:F>", inline=True)
        embed.add_field(name="Joined Server", value=f"<t:{int(member.joined_at.timestamp())}:F>", inline=True)
        embed.add_field(name="Bot Account", value="Yes" if member.bot else "No", inline=True)
        
        if member.roles[1:]:  # Exclude @everyone
            roles = ", ".join([role.mention for role in member.roles[1:]])
            if len(roles) > 1024:
                roles = roles[:1021] + "..."
            embed.add_field(name=f"Roles ({len(member.roles)-1})", value=roles, inline=False)
        
        if member.premium_since:
            embed.add_field(name="Boosting Since", value=f"<t:{int(member.premium_since.timestamp())}:F>", inline=True)
            
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="server-info", description="Get server information")
    async def server_info(self, interaction: discord.Interaction):
        """Get server information"""
        guild = interaction.guild
        
        embed = discord.Embed(title=f"{guild.name}", color=0x3498db)
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
            
        embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)
        embed.add_field(name="Created", value=f"<t:{int(guild.created_at.timestamp())}:F>", inline=True)
        embed.add_field(name="Members", value=guild.member_count, inline=True)
        
        embed.add_field(name="Channels", value=len(guild.channels), inline=True)
        embed.add_field(name="Roles", value=len(guild.roles), inline=True)
        embed.add_field(name="Emojis", value=len(guild.emojis), inline=True)
        
        embed.add_field(name="Verification Level", value=guild.verification_level.name.title(), inline=True)
        embed.add_field(name="Boost Level", value=guild.premium_tier, inline=True)
        embed.add_field(name="Boost Count", value=guild.premium_subscription_count, inline=True)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="avatar", description="Show a user's avatar")
    @app_commands.describe(user="User to show avatar of", global_avatar="Show global avatar instead of server avatar")
    async def avatar(self, interaction: discord.Interaction, user: discord.Member = None, global_avatar: bool = False):
        """Show a user's avatar"""
        if user is None:
            user = interaction.user
            
        if global_avatar:
            avatar_url = user.avatar.url if user.avatar else user.default_avatar.url
            title = f"{user.display_name}'s Global Avatar"
        else:
            avatar_url = user.display_avatar.url
            title = f"{user.display_name}'s Avatar"
            
        embed = discord.Embed(title=title, color=0x3498db)
        embed.set_image(url=avatar_url)
        
        await interaction.response.send_message(embed=embed)

    # Poll Commands
    @app_commands.command(name="poll", description="Create a poll")
    @app_commands.describe(question="Poll question", choices="Poll choices separated by commas")
    async def poll(self, interaction: discord.Interaction, question: str, choices: str = None):
        """Create a poll"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission to create polls.", ephemeral=True)
            return
            
        embed = discord.Embed(title="📊 Poll", description=question, color=0x3498db)
        
        if choices:
            choice_list = [choice.strip() for choice in choices.split(',')]
            if len(choice_list) > 10:
                await interaction.response.send_message("❌ Maximum 10 choices allowed.", ephemeral=True)
                return
                
            reactions = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
            
            for i, choice in enumerate(choice_list):
                embed.add_field(name=f"{reactions[i]} {choice}", value="\u200b", inline=False)
                
            await interaction.response.send_message(embed=embed)
            message = await interaction.original_response()
            
            for i in range(len(choice_list)):
                await message.add_reaction(reactions[i])
        else:
            # Simple yes/no poll
            await interaction.response.send_message(embed=embed)
            message = await interaction.original_response()
            await message.add_reaction('👍')
            await message.add_reaction('👎')

    # Reminder Commands
    @app_commands.command(name="remind", description="Set a reminder")
    @app_commands.describe(duration="When to remind (e.g., 1h, 30m, 2d)", message="What to remind about")
    async def remind(self, interaction: discord.Interaction, duration: str, message: str = "Reminder"):
        """Set a reminder"""
        # Parse duration
        time_regex = re.compile(r'(\d+)([smhd])')
        matches = time_regex.findall(duration.lower())
        
        if not matches:
            await interaction.response.send_message("❌ Invalid time format. Use format like: 1h, 30m, 2d", ephemeral=True)
            return
            
        total_seconds = 0
        for amount, unit in matches:
            amount = int(amount)
            if unit == 's':
                total_seconds += amount
            elif unit == 'm':
                total_seconds += amount * 60
            elif unit == 'h':
                total_seconds += amount * 3600
            elif unit == 'd':
                total_seconds += amount * 86400
                
        if total_seconds < 60:  # Minimum 1 minute
            await interaction.response.send_message("❌ Minimum reminder time is 1 minute.", ephemeral=True)
            return
            
        if total_seconds > 31536000:  # Maximum 1 year
            await interaction.response.send_message("❌ Maximum reminder time is 1 year.", ephemeral=True)
            return
            
        remind_time = datetime.now() + timedelta(seconds=total_seconds)
        
        # Store reminder in database (simplified for demo)
        reminder_id = len(self.bot.reminders) + 1
        reminder_data = {
            'id': reminder_id,
            'user_id': interaction.user.id,
            'channel_id': interaction.channel.id,
            'message': message,
            'remind_time': remind_time,
            'created_at': datetime.now()
        }
        
        if not hasattr(self.bot, 'reminders'):
            self.bot.reminders = {}
        self.bot.reminders[reminder_id] = reminder_data
        
        # Schedule the reminder
        asyncio.create_task(self.schedule_reminder(reminder_data))
        
        embed = discord.Embed(title="⏰ Reminder Set", color=0x3498db)
        embed.add_field(name="Message", value=message, inline=False)
        embed.add_field(name="Remind Time", value=f"<t:{int(remind_time.timestamp())}:F>", inline=True)
        embed.add_field(name="Reminder ID", value=reminder_id, inline=True)
        
        await interaction.response.send_message(embed=embed)

    async def schedule_reminder(self, reminder_data):
        """Schedule a reminder"""
        now = datetime.now()
        wait_time = (reminder_data['remind_time'] - now).total_seconds()
        
        if wait_time > 0:
            await asyncio.sleep(wait_time)
            
        try:
            channel = self.bot.get_channel(reminder_data['channel_id'])
            user = self.bot.get_user(reminder_data['user_id'])
            
            if channel and user:
                embed = discord.Embed(title="⏰ Reminder", color=0x3498db)
                embed.add_field(name="Message", value=reminder_data['message'], inline=False)
                embed.add_field(name="Set", value=f"<t:{int(reminder_data['created_at'].timestamp())}:R>", inline=True)
                
                await channel.send(f"{user.mention}", embed=embed)
                
            # Remove from reminders
            if hasattr(self.bot, 'reminders') and reminder_data['id'] in self.bot.reminders:
                del self.bot.reminders[reminder_data['id']]
                
        except Exception as e:
            print(f"Error sending reminder: {e}")

    @app_commands.command(name="reminders", description="List your reminders")
    async def reminders(self, interaction: discord.Interaction):
        """List your reminders"""
        if not hasattr(self.bot, 'reminders'):
            self.bot.reminders = {}
            
        user_reminders = [r for r in self.bot.reminders.values() if r['user_id'] == interaction.user.id]
        
        if not user_reminders:
            await interaction.response.send_message("📋 You have no active reminders.")
            return
            
        embed = discord.Embed(title="📋 Your Reminders", color=0x3498db)
        
        for reminder in user_reminders[:10]:  # Show max 10
            embed.add_field(
                name=f"ID: {reminder['id']}",
                value=f"**Message:** {reminder['message']}\n**Time:** <t:{int(reminder['remind_time'].timestamp())}:R>",
                inline=False
            )
            
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="reminder-delete", description="Delete a reminder")
    @app_commands.describe(reminder_id="ID of the reminder to delete")
    async def reminder_delete(self, interaction: discord.Interaction, reminder_id: int):
        """Delete a reminder"""
        if not hasattr(self.bot, 'reminders'):
            self.bot.reminders = {}
            
        if reminder_id not in self.bot.reminders:
            await interaction.response.send_message("❌ Reminder not found.", ephemeral=True)
            return
            
        reminder = self.bot.reminders[reminder_id]
        
        if reminder['user_id'] != interaction.user.id:
            await interaction.response.send_message("❌ You can only delete your own reminders.", ephemeral=True)
            return
            
        del self.bot.reminders[reminder_id]
        await interaction.response.send_message(f"✅ Deleted reminder {reminder_id}.")

    # Highlight Commands
    @app_commands.command(name="highlight", description="Manage highlight keywords")
    @app_commands.describe(action="add/remove/list/clear", keyword="Keyword to highlight")
    async def highlight(self, interaction: discord.Interaction, action: str = "list", keyword: str = None):
        """Manage highlight keywords"""
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ You need Manage Messages permission to use highlights.", ephemeral=True)
            return
            
        user_id = interaction.user.id
        guild_id = interaction.guild.id
        
        if guild_id not in self.highlights:
            self.highlights[guild_id] = {}
        if user_id not in self.highlights[guild_id]:
            self.highlights[guild_id][user_id] = []
            
        if action == "add" and keyword:
            if keyword.lower() not in self.highlights[guild_id][user_id]:
                self.highlights[guild_id][user_id].append(keyword.lower())
                await interaction.response.send_message(f"✅ Added '{keyword}' to your highlights.")
            else:
                await interaction.response.send_message(f"❌ '{keyword}' is already in your highlights.")
                
        elif action == "remove" and keyword:
            if keyword.lower() in self.highlights[guild_id][user_id]:
                self.highlights[guild_id][user_id].remove(keyword.lower())
                await interaction.response.send_message(f"✅ Removed '{keyword}' from your highlights.")
            else:
                await interaction.response.send_message(f"❌ '{keyword}' is not in your highlights.")
                
        elif action == "clear":
            self.highlights[guild_id][user_id] = []
            await interaction.response.send_message("✅ Cleared all your highlights.")
            
        else:  # list
            highlights = self.highlights[guild_id][user_id]
            if highlights:
                highlight_list = ", ".join(highlights)
                await interaction.response.send_message(f"📋 Your highlights: {highlight_list}")
            else:
                await interaction.response.send_message("📋 You have no highlights set.")

    # Snipe Commands
    @app_commands.command(name="snipe", description="Show the last deleted message")
    async def snipe(self, interaction: discord.Interaction):
        """Show the last deleted message"""
        channel_id = interaction.channel.id
        
        if channel_id not in self.deleted_messages:
            await interaction.response.send_message("❌ No deleted messages found in this channel.")
            return
            
        deleted_msg = self.deleted_messages[channel_id]
        
        embed = discord.Embed(
            title="🔍 Deleted Message",
            description=deleted_msg['content'],
            color=0xe74c3c,
            timestamp=deleted_msg['deleted_at']
        )
        embed.set_author(name=deleted_msg['author'], icon_url=deleted_msg['avatar'])
        embed.set_footer(text=f"Deleted")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="editsnipe", description="Show the last edited message")
    async def editsnipe(self, interaction: discord.Interaction):
        """Show the last edited message"""
        channel_id = interaction.channel.id
        
        if channel_id not in self.edited_messages:
            await interaction.response.send_message("❌ No edited messages found in this channel.")
            return
            
        edited_msg = self.edited_messages[channel_id]
        
        embed = discord.Embed(
            title="✏️ Edited Message",
            color=0xf39c12,
            timestamp=edited_msg['edited_at']
        )
        embed.set_author(name=edited_msg['author'], icon_url=edited_msg['avatar'])
        embed.add_field(name="Before", value=edited_msg['before'], inline=False)
        embed.add_field(name="After", value=edited_msg['after'], inline=False)
        embed.set_footer(text="Edited")
        
        await interaction.response.send_message(embed=embed)

    # Member Stats Commands
    @app_commands.command(name="youngest", description="Show youngest members by account creation")
    @app_commands.describe(count="Number of members to show (max 25)")
    async def youngest(self, interaction: discord.Interaction, count: int = 5):
        """Show youngest members by account creation"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission to use this command.", ephemeral=True)
            return
            
        if count > 25:
            count = 25
            
        members = sorted(interaction.guild.members, key=lambda m: m.created_at, reverse=True)[:count]
        
        embed = discord.Embed(title=f"👶 {count} Youngest Accounts", color=0x3498db)
        
        for i, member in enumerate(members, 1):
            embed.add_field(
                name=f"{i}. {member.display_name}",
                value=f"Created: <t:{int(member.created_at.timestamp())}:R>",
                inline=False
            )
            
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="oldest", description="Show oldest members by account creation")
    @app_commands.describe(count="Number of members to show (max 25)")
    async def oldest(self, interaction: discord.Interaction, count: int = 5):
        """Show oldest members by account creation"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission to use this command.", ephemeral=True)
            return
            
        if count > 25:
            count = 25
            
        members = sorted(interaction.guild.members, key=lambda m: m.created_at)[:count]
        
        embed = discord.Embed(title=f"👴 {count} Oldest Accounts", color=0x3498db)
        
        for i, member in enumerate(members, 1):
            embed.add_field(
                name=f"{i}. {member.display_name}",
                value=f"Created: <t:{int(member.created_at.timestamp())}:R>",
                inline=False
            )
            
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="newmembers", description="Show newest members by join date")
    @app_commands.describe(count="Number of members to show (max 25)")
    async def newmembers(self, interaction: discord.Interaction, count: int = 5):
        """Show newest members by join date"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission to use this command.", ephemeral=True)
            return
            
        if count > 25:
            count = 25
            
        members = sorted(interaction.guild.members, key=lambda m: m.joined_at or datetime.min, reverse=True)[:count]
        
        embed = discord.Embed(title=f"🆕 {count} Newest Members", color=0x3498db)
        
        for i, member in enumerate(members, 1):
            join_time = member.joined_at or datetime.min
            embed.add_field(
                name=f"{i}. {member.display_name}",
                value=f"Joined: <t:{int(join_time.timestamp())}:R>",
                inline=False
            )
            
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="oldmembers", description="Show oldest members by join date")
    @app_commands.describe(count="Number of members to show (max 25)")
    async def oldmembers(self, interaction: discord.Interaction, count: int = 5):
        """Show oldest members by join date"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission to use this command.", ephemeral=True)
            return
            
        if count > 25:
            count = 25
            
        members = sorted(interaction.guild.members, key=lambda m: m.joined_at or datetime.max)[:count]
        
        embed = discord.Embed(title=f"⏰ {count} Oldest Members", color=0x3498db)
        
        for i, member in enumerate(members, 1):
            join_time = member.joined_at or datetime.max
            embed.add_field(
                name=f"{i}. {member.display_name}",
                value=f"Joined: <t:{int(join_time.timestamp())}:R>",
                inline=False
            )
            
        await interaction.response.send_message(embed=embed)

    # Giveaway Commands
    @app_commands.command(name="giveaway", description="Create a giveaway")
    @app_commands.describe(duration="Duration (e.g., 1h, 30m)", winners="Number of winners", prize="Prize description")
    async def giveaway(self, interaction: discord.Interaction, duration: str, winners: int, prize: str):
        """Create a giveaway"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission to create giveaways.", ephemeral=True)
            return
            
        # Parse duration (similar to reminders)
        time_regex = re.compile(r'(\d+)([smhd])')
        matches = time_regex.findall(duration.lower())
        
        if not matches:
            await interaction.response.send_message("❌ Invalid time format. Use format like: 1h, 30m, 2d", ephemeral=True)
            return
            
        total_seconds = 0
        for amount, unit in matches:
            amount = int(amount)
            if unit == 's':
                total_seconds += amount
            elif unit == 'm':
                total_seconds += amount * 60
            elif unit == 'h':
                total_seconds += amount * 3600
            elif unit == 'd':
                total_seconds += amount * 86400
                
        if total_seconds < 60:
            await interaction.response.send_message("❌ Minimum giveaway duration is 1 minute.", ephemeral=True)
            return
            
        end_time = datetime.now() + timedelta(seconds=total_seconds)
        
        embed = discord.Embed(title="🎉 GIVEAWAY", description=prize, color=0xe91e63)
        embed.add_field(name="Winners", value=str(winners), inline=True)
        embed.add_field(name="Ends", value=f"<t:{int(end_time.timestamp())}:R>", inline=True)
        embed.add_field(name="Hosted by", value=interaction.user.mention, inline=True)
        embed.set_footer(text="React with 🎉 to enter!")
        
        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()
        await message.add_reaction('🎉')
        
        # Store giveaway data
        giveaway_id = message.id
        self.giveaways[giveaway_id] = {
            'prize': prize,
            'winners': winners,
            'end_time': end_time,
            'host': interaction.user.id,
            'channel': interaction.channel.id,
            'message_id': message.id
        }
        
        # Schedule giveaway end
        asyncio.create_task(self.end_giveaway(giveaway_id))

    async def end_giveaway(self, giveaway_id):
        """End a giveaway and pick winners"""
        if giveaway_id not in self.giveaways:
            return
            
        giveaway = self.giveaways[giveaway_id]
        wait_time = (giveaway['end_time'] - datetime.now()).total_seconds()
        
        if wait_time > 0:
            await asyncio.sleep(wait_time)
            
        try:
            channel = self.bot.get_channel(giveaway['channel'])
            message = await channel.fetch_message(giveaway['message_id'])
            
            # Get reaction users
            reaction = discord.utils.get(message.reactions, emoji='🎉')
            if reaction:
                users = []
                async for user in reaction.users():
                    if not user.bot:
                        users.append(user)
                        
                if len(users) >= giveaway['winners']:
                    import random
                    winners = random.sample(users, giveaway['winners'])
                    winner_mentions = ", ".join([user.mention for user in winners])
                    
                    embed = discord.Embed(title="🎉 Giveaway Ended!", description=giveaway['prize'], color=0x27ae60)
                    embed.add_field(name="Winners", value=winner_mentions, inline=False)
                    
                    await channel.send(embed=embed)
                else:
                    embed = discord.Embed(title="😔 Giveaway Ended", description=giveaway['prize'], color=0xe74c3c)
                    embed.add_field(name="Result", value="Not enough participants", inline=False)
                    
                    await channel.send(embed=embed)
                    
            # Remove from active giveaways
            del self.giveaways[giveaway_id]
            
        except Exception as e:
            print(f"Error ending giveaway: {e}")

    # Event Listeners
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """Track deleted messages for snipe command"""
        if message.author.bot or not message.guild:
            return
            
        self.deleted_messages[message.channel.id] = {
            'content': message.content or "*No content*",
            'author': str(message.author),
            'avatar': message.author.display_avatar.url,
            'deleted_at': datetime.now()
        }

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        """Track edited messages for editsnipe command"""
        if before.author.bot or not before.guild or before.content == after.content:
            return
            
        self.edited_messages[before.channel.id] = {
            'before': before.content or "*No content*",
            'after': after.content or "*No content*",
            'author': str(before.author),
            'avatar': before.author.display_avatar.url,
            'edited_at': datetime.now()
        }

    @commands.Cog.listener()
    async def on_message(self, message):
        """Check for highlight keywords"""
        if message.author.bot or not message.guild:
            return
            
        guild_id = message.guild.id
        if guild_id not in self.highlights:
            return
            
        message_content = message.content.lower()
        
        for user_id, keywords in self.highlights[guild_id].items():
            if user_id == message.author.id:  # Don't highlight own messages
                continue
                
            user = self.bot.get_user(user_id)
            if not user:
                continue
                
            # Check if user has manage messages permission in the channel
            member = message.guild.get_member(user_id)
            if not member or not member.permissions_in(message.channel).manage_messages:
                continue
                
            # Check if user posted recently (within 5 minutes)
            # This is a simplified check - in practice you'd want to track last message times
            
            for keyword in keywords:
                if keyword in message_content:
                    try:
                        embed = discord.Embed(title="🔔 Highlight", color=0xf39c12)
                        embed.add_field(name="Keyword", value=keyword, inline=True)
                        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
                        embed.add_field(name="Author", value=message.author.mention, inline=True)
                        embed.add_field(name="Message", value=message.content[:1000], inline=False)
                        embed.add_field(name="Jump", value=f"[Click here]({message.jump_url})", inline=True)
                        
                        await user.send(embed=embed)
                        break  # Only send one highlight per message per user
                    except discord.Forbidden:
                        pass  # User has DMs disabled

async def setup(bot):
    await bot.add_cog(UtilsCog(bot)) 