import discord
from discord.ext import commands
from utils.permissions import has_permission, can_target_member
from utils.database import DatabaseManager
import datetime
import asyncio
import logging

logger = logging.getLogger('discord_bot.moderation')

class ModerationCog(commands.Cog):
    """Moderation commands for server management"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()

    @commands.hybrid_command(name="setmodrole", description="Set the moderator role (Admin only)")
    @has_permission("admin")
    async def set_mod_role(self, ctx, role: discord.Role):
        """Set which role gets moderator permissions"""
        success = self.db.set_guild_setting(ctx.guild.id, 'moderator_role_id', role.id)
        
        if success:
            embed = discord.Embed(title="⚙️ Moderator Role Set", color=0x00ff00)
            embed.add_field(name="Role", value=role.mention)
            embed.add_field(name="Set by", value=ctx.author.mention)
            await ctx.send(embed=embed)
            
            logger.info(f"Set moderator role to {role.name} in guild {ctx.guild.id}")
        else:
            await ctx.send("❌ Failed to set moderator role!")

    @commands.hybrid_command(name="kick", description="Kick a member (Admin+)")
    @has_permission("admin")
    async def kick_cmd(self, ctx, member: discord.Member, *, reason: str = "No reason"):
        """Kick a member from the server"""
        
        # Check if user can target this member
        can_target, error_msg = can_target_member(ctx, member)
        if not can_target:
            return await ctx.send(f"❌ {error_msg}")
        
        try:
            await member.kick(reason=reason)
            
            # Log the action
            self.db.log_moderation_action(ctx.guild.id, member.id, ctx.author.id, "kick", reason)
            
            embed = discord.Embed(title="👢 Member Kicked", description=f"{member.mention} has been kicked", color=0xff9900)
            embed.add_field(name="Reason", value=reason)
            embed.add_field(name="Moderator", value=ctx.author.mention)
            await ctx.send(embed=embed)
            
            logger.info(f"Kicked user {member.id} from guild {ctx.guild.id}")
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to kick this member!")
        except Exception as e:
            await ctx.send(f"❌ Failed to kick member: {e}")
            logger.error(f"Kick failed: {e}")

    @commands.hybrid_command(name="ban", description="Ban a member (Admin+)")
    @has_permission("admin")
    async def ban_cmd(self, ctx, member: discord.Member, *, reason: str = "No reason"):
        """Ban a member from the server"""
        
        # Check if user can target this member
        can_target, error_msg = can_target_member(ctx, member)
        if not can_target:
            return await ctx.send(f"❌ {error_msg}")
        
        try:
            await member.ban(reason=reason)
            
            # Log the action
            self.db.log_moderation_action(ctx.guild.id, member.id, ctx.author.id, "ban", reason)
            
            embed = discord.Embed(title="🔨 Member Banned", description=f"{member.mention} has been banned", color=0xff0000)
            embed.add_field(name="Reason", value=reason)
            embed.add_field(name="Moderator", value=ctx.author.mention)
            await ctx.send(embed=embed)
            
            logger.info(f"Banned user {member.id} from guild {ctx.guild.id}")
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to ban this member!")
        except Exception as e:
            await ctx.send(f"❌ Failed to ban member: {e}")
            logger.error(f"Ban failed: {e}")

    @commands.hybrid_command(name="unban", description="Unban a user (Admin+)")
    @has_permission("admin")
    async def unban_cmd(self, ctx, user_id: int, *, reason: str = "No reason"):
        """Unban a user by their ID"""
        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.unban(user, reason=reason)
            
            # Log the action
            self.db.log_moderation_action(ctx.guild.id, user.id, ctx.author.id, "unban", reason)
            
            embed = discord.Embed(title="✅ User Unbanned", description=f"{user.mention} has been unbanned", color=0x00ff00)
            embed.add_field(name="Reason", value=reason)
            embed.add_field(name="Moderator", value=ctx.author.mention)
            await ctx.send(embed=embed)
            
            logger.info(f"Unbanned user {user.id} from guild {ctx.guild.id}")
            
        except discord.NotFound:
            await ctx.send("❌ User not found or not banned!")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to unban users!")
        except Exception as e:
            await ctx.send(f"❌ Failed to unban user: {e}")
            logger.error(f"Unban failed: {e}")

    @commands.hybrid_command(name="timeout", description="Timeout a member (Moderator+)")
    @has_permission("moderator")
    async def timeout_cmd(self, ctx, member: discord.Member, minutes: int, *, reason: str = "No reason"):
        """Timeout a member for a specified duration"""
        
        # Check if user can target this member
        can_target, error_msg = can_target_member(ctx, member)
        if not can_target:
            return await ctx.send(f"❌ {error_msg}")
        
        if minutes <= 0 or minutes > 40320:  # Discord's maximum is 28 days (40320 minutes)
            return await ctx.send("❌ Timeout duration must be between 1-40320 minutes (28 days max)!")
        
        try:
            timeout_until = discord.utils.utcnow() + datetime.timedelta(minutes=minutes)
            await member.timeout(timeout_until, reason=reason)
            
            # Log the action
            self.db.log_moderation_action(ctx.guild.id, member.id, ctx.author.id, "timeout", f"{minutes}m: {reason}")
            
            embed = discord.Embed(title="🔇 Member Timed Out", description=f"{member.mention} has been timed out", color=0xffaa00)
            embed.add_field(name="Duration", value=f"{minutes} minutes")
            embed.add_field(name="Reason", value=reason)
            embed.add_field(name="Moderator", value=ctx.author.mention)
            embed.add_field(name="Ends", value=f"<t:{int(timeout_until.timestamp())}:F>")
            await ctx.send(embed=embed)
            
            logger.info(f"Timed out user {member.id} for {minutes} minutes in guild {ctx.guild.id}")
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to timeout this member!")
        except Exception as e:
            await ctx.send(f"❌ Failed to timeout member: {e}")
            logger.error(f"Timeout failed: {e}")

    @commands.hybrid_command(name="untimeout", description="Remove timeout from a member (Moderator+)")
    @has_permission("moderator")
    async def untimeout_cmd(self, ctx, member: discord.Member, *, reason: str = "No reason"):
        """Remove timeout from a member"""
        
        if not member.timed_out:
            return await ctx.send(f"❌ {member.mention} is not timed out!")
        
        try:
            await member.timeout(None, reason=reason)
            
            # Log the action
            self.db.log_moderation_action(ctx.guild.id, member.id, ctx.author.id, "untimeout", reason)
            
            embed = discord.Embed(title="✅ Timeout Removed", description=f"{member.mention} is no longer timed out", color=0x00ff00)
            embed.add_field(name="Reason", value=reason)
            embed.add_field(name="Moderator", value=ctx.author.mention)
            await ctx.send(embed=embed)
            
            logger.info(f"Removed timeout from user {member.id} in guild {ctx.guild.id}")
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to remove timeout from this member!")
        except Exception as e:
            await ctx.send(f"❌ Failed to remove timeout: {e}")
            logger.error(f"Untimeout failed: {e}")

    @commands.hybrid_command(name="clear", description="Clear messages (Moderator+)")
    @has_permission("moderator")
    async def clear_cmd(self, ctx, amount: int = 10):
        """Clear a specified number of messages"""
        if amount <= 0 or amount > 100:
            return await ctx.send("❌ Amount must be between 1-100!")
        
        try:
            # Delete the command message and the specified amount of messages
            deleted = await ctx.channel.purge(limit=amount + 1)
            
            # Log the action
            self.db.log_moderation_action(ctx.guild.id, ctx.author.id, ctx.author.id, "clear", f"Cleared {len(deleted)-1} messages")
            
            # Send confirmation message that will auto-delete
            msg = await ctx.send(f"🧹 Cleared {len(deleted)-1} messages")
            await asyncio.sleep(3)
            try:
                await msg.delete()
            except:
                pass  # Message might already be deleted
                
            logger.info(f"Cleared {len(deleted)-1} messages in channel {ctx.channel.id}")
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to delete messages!")
        except Exception as e:
            await ctx.send(f"❌ Failed to clear messages: {e}")
            logger.error(f"Clear failed: {e}")

    @commands.hybrid_command(name="slowmode", description="Set channel slowmode (Moderator+)")
    @has_permission("moderator")
    async def slowmode_cmd(self, ctx, seconds: int = 0):
        """Set slowmode for the current channel"""
        if seconds < 0 or seconds > 21600:  # Discord's maximum is 6 hours
            return await ctx.send("❌ Slowmode must be between 0-21600 seconds (6 hours max)!")
        
        try:
            await ctx.channel.edit(slowmode_delay=seconds)
            
            # Log the action
            self.db.log_moderation_action(ctx.guild.id, ctx.author.id, ctx.author.id, "slowmode", f"Set to {seconds}s")
            
            if seconds == 0:
                embed = discord.Embed(title="⏱️ Slowmode Disabled", color=0x00ff00)
                embed.add_field(name="Channel", value=ctx.channel.mention)
            else:
                embed = discord.Embed(title="⏱️ Slowmode Enabled", color=0xffaa00)
                embed.add_field(name="Channel", value=ctx.channel.mention)
                embed.add_field(name="Delay", value=f"{seconds} seconds")
            
            embed.add_field(name="Set by", value=ctx.author.mention)
            await ctx.send(embed=embed)
            
            logger.info(f"Set slowmode to {seconds}s in channel {ctx.channel.id}")
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to edit this channel!")
        except Exception as e:
            await ctx.send(f"❌ Failed to set slowmode: {e}")
            logger.error(f"Slowmode failed: {e}")

    @commands.hybrid_command(name="lock", description="Lock a channel (Moderator+)")
    @has_permission("moderator")
    async def lock_cmd(self, ctx, reason: str = "No reason"):
        """Lock the current channel"""
        try:
            overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
            overwrite.send_messages = False
            await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
            
            # Log the action
            self.db.log_moderation_action(ctx.guild.id, ctx.author.id, ctx.author.id, "lock_channel", reason)
            
            embed = discord.Embed(title="🔒 Channel Locked", color=0xff0000)
            embed.add_field(name="Channel", value=ctx.channel.mention)
            embed.add_field(name="Reason", value=reason)
            embed.add_field(name="Moderator", value=ctx.author.mention)
            await ctx.send(embed=embed)
            
            logger.info(f"Locked channel {ctx.channel.id} in guild {ctx.guild.id}")
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage this channel!")
        except Exception as e:
            await ctx.send(f"❌ Failed to lock channel: {e}")
            logger.error(f"Lock failed: {e}")

    @commands.hybrid_command(name="unlock", description="Unlock a channel (Moderator+)")
    @has_permission("moderator")
    async def unlock_cmd(self, ctx, reason: str = "No reason"):
        """Unlock the current channel"""
        try:
            overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
            overwrite.send_messages = None  # Reset to default
            await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
            
            # Log the action
            self.db.log_moderation_action(ctx.guild.id, ctx.author.id, ctx.author.id, "unlock_channel", reason)
            
            embed = discord.Embed(title="🔓 Channel Unlocked", color=0x00ff00)
            embed.add_field(name="Channel", value=ctx.channel.mention)
            embed.add_field(name="Reason", value=reason)
            embed.add_field(name="Moderator", value=ctx.author.mention)
            await ctx.send(embed=embed)
            
            logger.info(f"Unlocked channel {ctx.channel.id} in guild {ctx.guild.id}")
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage this channel!")
        except Exception as e:
            await ctx.send(f"❌ Failed to unlock channel: {e}")
            logger.error(f"Unlock failed: {e}")

async def setup(bot):
    await bot.add_cog(ModerationCog(bot)) 