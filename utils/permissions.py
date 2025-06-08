import discord
from discord.ext import commands
import logging

logger = logging.getLogger('discord_bot.permissions')

def is_owner(ctx):
    """Check if user is server owner"""
    return ctx.guild.owner_id == ctx.author.id

def is_admin(ctx):
    """Check if user is administrator or owner"""
    return ctx.author.guild_permissions.administrator or is_owner(ctx)

def is_moderator(ctx):
    """Check if user is moderator, admin, or owner"""
    if is_admin(ctx):
        return True
    
    # Check for configured moderator role
    try:
        from utils.database import DatabaseManager
        db = DatabaseManager()
        
        moderator_role_id = db.get_guild_setting(ctx.guild.id, 'moderator_role_id')
        
        if moderator_role_id:
            mod_role = ctx.guild.get_role(moderator_role_id)
            if mod_role and mod_role in ctx.author.roles:
                return True
                
    except Exception as e:
        logger.error(f"Error checking moderator status: {e}")
    
    return False

def has_permission(required_level):
    """Decorator for permission checking"""
    def predicate(ctx):
        if required_level == "owner":
            return is_owner(ctx)
        elif required_level == "admin":
            return is_admin(ctx)
        elif required_level == "moderator":
            return is_moderator(ctx)
        else:
            return True
    return commands.check(predicate)

def can_target_member(ctx, target: discord.Member) -> tuple[bool, str]:
    """Check if the command author can target the specified member"""
    
    # Can't target yourself for moderation actions
    if target.id == ctx.author.id:
        return False, "You can't target yourself!"
    
    # Can't target the bot
    if target.bot:
        return False, "You can't target bots!"
    
    # Server owner can target anyone except other bots
    if is_owner(ctx):
        return True, ""
    
    # Admins can't target server owner
    if target.id == ctx.guild.owner_id:
        return False, "You can't target the server owner!"
    
    # Admins can target anyone except other admins
    if is_admin(ctx):
        if target.guild_permissions.administrator:
            return False, "You can't target other administrators!"
        return True, ""
    
    # Moderators can only target regular members
    if is_moderator(ctx):
        if target.guild_permissions.administrator:
            return False, "You can't target administrators!"
        
        # Check if target is also a moderator
        try:
            from utils.database import DatabaseManager
            db = DatabaseManager()
            
            moderator_role_id = db.get_guild_setting(ctx.guild.id, 'moderator_role_id')
            if moderator_role_id:
                mod_role = ctx.guild.get_role(moderator_role_id)
                if mod_role and mod_role in target.roles:
                    return False, "You can't target other moderators!"
                    
        except Exception as e:
            logger.error(f"Error checking target moderator status: {e}")
        
        return True, ""
    
    # Regular members can't use moderation commands
    return False, "You don't have permission to use this command!"

class PermissionLevel:
    """Constants for permission levels"""
    EVERYONE = 0
    MODERATOR = 1
    ADMIN = 2
    OWNER = 3

def get_user_permission_level(ctx) -> int:
    """Get the permission level of a user"""
    if is_owner(ctx):
        return PermissionLevel.OWNER
    elif is_admin(ctx):
        return PermissionLevel.ADMIN
    elif is_moderator(ctx):
        return PermissionLevel.MODERATOR
    else:
        return PermissionLevel.EVERYONE

def get_permission_name(level: int) -> str:
    """Get the name of a permission level"""
    if level == PermissionLevel.OWNER:
        return "Server Owner"
    elif level == PermissionLevel.ADMIN:
        return "Administrator"
    elif level == PermissionLevel.MODERATOR:
        return "Moderator"
    else:
        return "Member" 