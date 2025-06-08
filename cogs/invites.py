import discord
from discord.ext import commands
from utils.permissions import has_permission
import logging

logger = logging.getLogger('discord_bot.invites')

class InvitesCog(commands.Cog):
    """Invite tracking and management"""
    
    def __init__(self, bot):
        self.bot = bot
        # Store invite data in memory for now
        self.invite_cache = {}
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Cache existing invites when bot starts"""
        for guild in self.bot.guilds:
            try:
                invites = await guild.invites()
                self.invite_cache[guild.id] = {invite.code: invite.uses for invite in invites}
                logger.info(f"Cached {len(invites)} invites for guild {guild.name}")
            except discord.Forbidden:
                logger.warning(f"No permission to view invites in guild {guild.name}")
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Track which invite was used when someone joins"""
        try:
            guild = member.guild
            new_invites = await guild.invites()
            
            if guild.id not in self.invite_cache:
                self.invite_cache[guild.id] = {}
            
            # Find which invite was used
            used_invite = None
            for invite in new_invites:
                old_uses = self.invite_cache[guild.id].get(invite.code, 0)
                if invite.uses > old_uses:
                    used_invite = invite
                    break
            
            # Update cache
            self.invite_cache[guild.id] = {invite.code: invite.uses for invite in new_invites}
            
            if used_invite:
                logger.info(f"User {member.id} joined {guild.name} using invite {used_invite.code} by {used_invite.inviter}")
                
                # You could log this to database or send to a log channel here
                
        except discord.Forbidden:
            pass  # No permission to view invites
        except Exception as e:
            logger.error(f"Error tracking invite usage: {e}")
    
    @commands.hybrid_command(name="invites", description="Show server invites (Admin+)")
    @has_permission("admin")
    async def list_invites(self, ctx):
        """List all server invites"""
        try:
            invites = await ctx.guild.invites()
            
            if not invites:
                return await ctx.send("❌ No invites found!")
            
            embed = discord.Embed(title="📨 Server Invites", color=0x0099ff)
            
            for invite in invites[:10]:  # Show first 10
                inviter = invite.inviter.display_name if invite.inviter else "Unknown"
                
                embed.add_field(
                    name=f"Code: {invite.code}",
                    value=f"**Inviter:** {inviter}\n**Uses:** {invite.uses}/{invite.max_uses or '∞'}\n**Expires:** {'Never' if invite.max_age == 0 else f'<t:{int((invite.created_at.timestamp() + invite.max_age))}:R>'}",
                    inline=True
                )
            
            if len(invites) > 10:
                embed.set_footer(text=f"Showing 10 of {len(invites)} invites")
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to view invites!")
        except Exception as e:
            await ctx.send(f"❌ Failed to get invites: {e}")
    
    @commands.hybrid_command(name="deleteinvite", description="Delete an invite (Admin+)")
    @has_permission("admin")
    async def delete_invite(self, ctx, invite_code: str):
        """Delete an invite by code"""
        try:
            invite = await self.bot.fetch_invite(invite_code)
            
            if invite.guild != ctx.guild:
                return await ctx.send("❌ That invite is not for this server!")
            
            await invite.delete()
            
            # Update cache
            if ctx.guild.id in self.invite_cache:
                self.invite_cache[ctx.guild.id].pop(invite_code, None)
            
            embed = discord.Embed(title="🗑️ Invite Deleted", color=0xff0000)
            embed.add_field(name="Code", value=invite_code)
            embed.add_field(name="Deleted by", value=ctx.author.mention)
            await ctx.send(embed=embed)
            
            logger.info(f"Deleted invite {invite_code} in guild {ctx.guild.id}")
            
        except discord.NotFound:
            await ctx.send("❌ Invite not found!")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to delete invites!")
        except Exception as e:
            await ctx.send(f"❌ Failed to delete invite: {e}")

async def setup(bot):
    await bot.add_cog(InvitesCog(bot)) 