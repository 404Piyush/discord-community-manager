import discord
from discord.ext import commands
from utils.permissions import has_permission, can_target_member
from utils.database import DatabaseManager
import os
import logging

logger = logging.getLogger('discord_bot.warnings')

class WarningsCog(commands.Cog):
    """Warning system with auto-ban functionality"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
    
    @commands.hybrid_command(name="warn", description="Warn a user (Moderator+)")
    @has_permission("moderator")
    async def warn_user(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Warn a user with a reason"""
        
        # Check if user can target this member
        can_target, error_msg = can_target_member(ctx, member)
        if not can_target:
            return await ctx.send(f"❌ {error_msg}")
        
        # Add warning to database
        warning_count = self.db.add_warning(ctx.guild.id, member.id, ctx.author.id, reason)
        
        if warning_count == 0:
            return await ctx.send("❌ Failed to add warning!")
        
        # Get warning threshold
        threshold = self.db.get_guild_setting(ctx.guild.id, 'warn_threshold') or int(os.getenv('DEFAULT_WARN_THRESHOLD', '3'))
        
        # Send warning embed
        embed = discord.Embed(title="⚠️ User Warned", color=0xffaa00)
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Reason", value=reason)
        embed.add_field(name="Moderator", value=ctx.author.mention)
        embed.add_field(name="Warning Count", value=f"{warning_count}/{threshold}")
        
        # Log the action
        self.db.log_moderation_action(ctx.guild.id, member.id, ctx.author.id, "warn", reason)
        
        await ctx.send(embed=embed)
        
        # Check if auto-ban threshold reached
        if warning_count >= threshold:
            try:
                # Get all warning reasons for ban reason
                warnings = self.db.get_warnings(ctx.guild.id, member.id)
                reasons = [warning[0] for warning in warnings]  # warning[0] is the reason
                
                ban_reason = f"Auto-ban: {threshold}+ warnings. Reasons: " + " | ".join(reasons)
                
                await member.ban(reason=ban_reason[:512])  # Discord limit
                
                # Log the auto-ban
                self.db.log_moderation_action(ctx.guild.id, member.id, self.bot.user.id, "auto-ban", f"Reached {threshold} warnings")
                
                ban_embed = discord.Embed(title="🔨 Auto-Ban", color=0xff0000)
                ban_embed.add_field(name="User", value=member.mention)
                ban_embed.add_field(name="Reason", value=f"Reached {threshold} warnings")
                ban_embed.add_field(name="All Reasons", value=" | ".join(reasons)[:1024])
                
                await ctx.send(embed=ban_embed)
                
                logger.info(f"Auto-banned user {member.id} in guild {ctx.guild.id} for reaching {threshold} warnings")
                
            except discord.Forbidden:
                await ctx.send(f"❌ Couldn't auto-ban {member.mention}: No permission to ban!")
            except Exception as e:
                await ctx.send(f"❌ Failed to auto-ban user: {e}")
                logger.error(f"Auto-ban failed: {e}")

    @commands.hybrid_command(name="checkwarns", description="Check user warnings")
    async def check_warnings(self, ctx, member: discord.Member = None):
        """Check warnings for a user (or yourself)"""
        if not member:
            member = ctx.author
        
        warnings = self.db.get_warnings(ctx.guild.id, member.id)
        
        embed = discord.Embed(title=f"⚠️ Warnings for {member.display_name}", color=0xffaa00)
        
        if not warnings:
            embed.description = "No warnings found"
        else:
            embed.description = f"**Total Warnings:** {len(warnings)}"
            
            for i, (reason, timestamp, mod_id) in enumerate(warnings[:10], 1):  # Show only first 10
                moderator = ctx.guild.get_member(mod_id)
                mod_name = moderator.display_name if moderator else "Unknown"
                
                embed.add_field(
                    name=f"Warning #{i}",
                    value=f"**Reason:** {reason}\n**By:** {mod_name}\n**Date:** {timestamp}",
                    inline=False
                )
            
            if len(warnings) > 10:
                embed.set_footer(text=f"Showing 10 of {len(warnings)} warnings")
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="clearwarn", description="Clear one warning from a user (Admin+)")
    @has_permission("admin")
    async def clear_warning(self, ctx, member: discord.Member, warning_number: int = 1):
        """Clear a specific warning from a user"""
        
        warnings = self.db.get_warnings(ctx.guild.id, member.id)
        
        if not warnings:
            return await ctx.send(f"❌ {member.display_name} has no warnings!")
        
        if warning_number < 1 or warning_number > len(warnings):
            return await ctx.send(f"❌ Invalid warning number! {member.display_name} has {len(warnings)} warning(s).")
        
        # Clear the warning
        success = self.db.clear_warning(ctx.guild.id, member.id, warning_number)
        
        if success:
            # Log the action
            self.db.log_moderation_action(ctx.guild.id, member.id, ctx.author.id, "clear_warning", f"Cleared warning #{warning_number}")
            
            embed = discord.Embed(title="✅ Warning Cleared", color=0x00ff00)
            embed.add_field(name="User", value=member.mention)
            embed.add_field(name="Warning #", value=str(warning_number))
            embed.add_field(name="Cleared by", value=ctx.author.mention)
            
            await ctx.send(embed=embed)
            logger.info(f"Cleared warning #{warning_number} for user {member.id} in guild {ctx.guild.id}")
        else:
            await ctx.send("❌ Failed to clear warning!")

    @commands.hybrid_command(name="setwarnthreshold", description="Set warning threshold for auto-ban (Admin only)")
    @has_permission("admin")
    async def set_warn_threshold(self, ctx, threshold: int):
        """Set how many warnings trigger an auto-ban"""
        if threshold < 1 or threshold > 10:
            return await ctx.send("❌ Threshold must be between 1-10!")
        
        success = self.db.set_guild_setting(ctx.guild.id, 'warn_threshold', threshold)
        
        if success:
            embed = discord.Embed(title="⚙️ Warning Threshold Set", color=0x00ff00)
            embed.add_field(name="Threshold", value=f"{threshold} warnings")
            embed.add_field(name="Set by", value=ctx.author.mention)
            await ctx.send(embed=embed)
            
            logger.info(f"Set warning threshold to {threshold} in guild {ctx.guild.id}")
        else:
            await ctx.send("❌ Failed to set warning threshold!")

    @commands.hybrid_command(name="warnstats", description="Show warning statistics for the server")
    @has_permission("moderator")
    async def warn_stats(self, ctx):
        """Show warning statistics for the server"""
        # This would require additional database queries to get stats
        # For now, just show basic info
        
        threshold = self.db.get_guild_setting(ctx.guild.id, 'warn_threshold') or int(os.getenv('DEFAULT_WARN_THRESHOLD', '3'))
        
        embed = discord.Embed(title="📊 Warning System Statistics", color=0x0099ff)
        embed.add_field(name="Current Threshold", value=f"{threshold} warnings = auto-ban")
        embed.add_field(name="System Status", value="✅ Active")
        
        # You could add more stats here like:
        # - Total warnings issued
        # - Most warned users
        # - Auto-bans this month
        # etc.
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(WarningsCog(bot)) 