import discord
from discord.ext import commands
from utils.permissions import get_user_permission_level, get_permission_name, PermissionLevel
import os

class CoreCog(commands.Cog):
    """🤖 Core Functions: Core bot functionality and information commands"""
    
    def __init__(self, bot):
        self.bot = bot
        
        # Define all cogs and their commands for the help system
        self.cog_info = {
            "1": {
                "name": "Core",
                "description": "Essential bot commands and information",
                "commands": {
                    "/help": "Interactive help system",
                    "/userinfo": "View user details",
                    "/serverinfo": "Server statistics",
                    "/ping": "Check bot latency",
                    "/about": "Bot information"
                }
            },
            "2": {
                "name": "Moderation",
                "description": "Server moderation and management tools",
                "commands": {
                    "/kick": "Remove member from server",
                    "/ban": "Permanently ban member",
                    "/timeout": "Temporarily mute member",
                    "/clear": "Bulk delete messages",
                    "/lock": "Lock channel from messages",
                    "/slowmode": "Set channel message rate limit"
                }
            },
            "3": {
                "name": "Warnings",
                "description": "Automated warning and discipline tracking",
                "commands": {
                    "/warn": "Issue warning to member",
                    "/checkwarns": "View your warning history",
                    "/clearwarn": "Remove specific warning",
                    "/setwarnthreshold": "Set auto-ban warning limit"
                }
            },
            "4": {
                "name": "Invites",
                "description": "Monitor and manage server invites",
                "commands": {
                    "/invites": "View server invite statistics", 
                    "/deleteinvite": "Remove specific server invite",
                    "/createinvite": "Generate new server invite"
                }
            },
            "5": {
                "name": "Verification", 
                "description": "Advanced member verification and security",
                "commands": {
                    "/setup-verification": "Interactive verification system setup",
                    "/verification-info": "Show verification system status",
                    "/verification-config": "View detailed verification settings",
                    "/verification-stats": "Member verification statistics", 
                    "/disable-verification": "Temporarily disable verification",
                    "/enable-verification": "Re-enable verification system",
                    "/test-verification": "Test verification without role assignment",
                    "/manual-verify": "Manually verify specific member",
                    "/reset-verification": "Reset member verification status",
                    "/bulk-verify": "Verify members by role",
                    "/verification-logs": "View recent verification activity"
                }
            },
            "6": {
                "name": "Automod",
                "description": "Advanced spam detection and automatic moderation",
                "commands": {
                    "/automod": "View automod configuration",
                    "/automod-slowmode": "Set message rate limiting",
                    "/mentionspam": "Configure mention spam protection",
                    "/badwords": "Manage bad words filter",
                    "/linkspam": "Control link spam detection",
                    "/invitespam": "Block invite spam",
                    "/caps": "Configure caps spam detection",
                    "/repeated": "Configure repeated text detection",
                    "/zalgo": "Configure zalgo text detection"
                }
            },
            "7": {
                "name": "Roles",
                "description": "Advanced role management and automation",
                "commands": {
                    "/autorole": "Manage automatic role assignment",
                    "/timedrole": "Set up timed role assignment",
                    "/rr-add": "Add reaction roles",
                    "/role-add": "Assign roles to members",
                    "/role-remove": "Remove roles from members",
                    "/rolemenu": "Create interactive role menus",
                    "/massrole": "Assign roles to multiple members"
                }
            },
            "8": {
                "name": "Starboard",
                "description": "Community-driven message highlighting system",
                "commands": {
                    "/starboard": "Set up starboard channel",
                    "/star-limit": "Configure star threshold",
                    "/star-stats": "View starboard statistics",
                    "/star-config": "Show starboard settings",
                    "/star-random": "Show random starred message",
                    "/star-show": "Show specific starred message",
                    "/star-nsfw": "Toggle NSFW starboard support",
                    "/star-self": "Toggle self-starring"
                }
            },
            "9": {
                "name": "Utilities",
                "description": "Helpful utility commands and tools",
                "commands": {
                    "/member-info": "Detailed user information",
                    "/server-info": "Server statistics",
                    "/avatar": "Get user avatars",
                    "/poll": "Create interactive polls",
                    "/remind": "Set personal reminders",
                    "/highlight": "Keyword highlighting system",
                    "/snipe": "Show recently deleted messages",
                    "/editsnipe": "Show recently edited messages"
                }
            },
            "10": {
                "name": "Fun",
                "description": "Entertainment and text transformation commands",
                "commands": {
                    "/cat": "Random cat images",
                    "/dog": "Random dog images",
                    "/8ball": "Magic 8-ball responses",
                    "/roll": "Dice rolling",
                    "/emojify": "Text to emoji conversion",
                    "/owofy": "OwO text transformation",
                    "/echo": "Make the bot speak",
                    "/pick": "Random choice picker",
                    "/aesthetics": "Aesthetic text transformation",
                    "/clap": "Add clap emojis between words",
                    "/space": "Add spaces between characters",
                    "/reverse": "Reverse text",
                    "/coinflip": "Flip a coin"
                }
            },
            "11": {
                "name": "Logs",
                "description": "Server logging and audit trail",
                "commands": {
                    "/log-channel": "Set channels for different log types",
                    "/log-config": "View current logging configuration",
                    "/log-toggle": "Toggle logging features on/off"
                }
            },
            "12": {
                "name": "Tags & Custom",
                "description": "Custom server commands and responses",
                "commands": {
                    "/tag-create": "Create custom command responses",
                    "/tag-edit": "Modify existing tag content",
                    "/tag-list": "Browse all server tags",
                    "/tag-info": "Get information about a tag",
                    "/tag-alias": "Create aliases for tags",
                    "/tag-raw": "View raw tag content",
                    "/trigger-create": "Set up automatic message triggers",
                    "/trigger-list": "View all triggers"
                }
            },
            "13": {
                "name": "Leveling",
                "description": "XP-based leveling with rewards and leaderboards",
                "commands": {
                    "/rank": "Check your or someone's rank",
                    "/levels": "View server leaderboard",
                    "/givexp": "Give XP to users (admin)",
                    "/setlevel": "Set user level (admin)",
                    "/lvl-toggle": "Enable/disable leveling",
                    "/lvl-channel": "Set level announcement channel",
                    "/lvl-role": "Add level role rewards",
                    "/lvl-config": "View leveling configuration"
                }
            },
            "14": {
                "name": "Economy",
                "description": "Virtual economy with gambling and mini-games",
                "commands": {
                    "/balance": "Check your credit balance",
                    "/daily": "Claim daily credits",
                    "/work": "Work to earn credits",
                    "/coinflip": "Bet credits on coin flips",
                    "/slots": "Play the slot machine",
                    "/rps": "Rock Paper Scissors game",
                    "/guess": "Number guessing game",
                    "/gamestats": "View your game statistics"
                }
            },
            "15": {
                "name": "RSS Feeds",
                "description": "Automated RSS feed monitoring and posting",
                "commands": {
                    "/rss-add": "Add RSS feed to monitor",
                    "/rss-list": "List all configured feeds",
                    "/rss-remove": "Remove RSS feed"
                }
            }
        }
        
        # Detailed command information with all the new verification commands
        self.command_details = {
            # Core Commands
            "help": {
                "usage": "/help [command]",
                "description": "Interactive help system with cog navigation and detailed command information",
                "examples": ["/help", "/help ban", "/help setup-verification"],
                "permissions": "Everyone",
                "best_practices": "• Use without parameters for main menu\n• Use with command name for detailed info\n• Navigate with buttons for better experience"
            },
            "userinfo": {
                "usage": "/userinfo [member]",
                "description": "Display comprehensive information about a server member including roles, join date, and permissions",
                "examples": ["/userinfo", "/userinfo @username", "/userinfo 123456789"],
                "permissions": "Everyone", 
                "best_practices": "• Use without parameters to check your own info\n• Mention users for quick lookup\n• Useful for checking member join dates"
            },
            "serverinfo": {
                "usage": "/serverinfo",
                "description": "Show detailed server statistics including member count, creation date, and bot configuration",
                "examples": ["/serverinfo"],
                "permissions": "Everyone",
                "best_practices": "• Check server overview regularly\n• Monitor member growth\n• Verify bot configuration"
            },
            
            # Moderation Commands  
            "kick": {
                "usage": "/kick <member> [reason]",
                "description": "Remove a member from the server. They can rejoin with a new invite",
                "examples": ["/kick @troublemaker", "/kick @user Spamming in chat"],
                "permissions": "Admin+",
                "best_practices": "• Always provide a clear reason\n• Use for temporary removal\n• Consider timeout for minor issues\n• Document serious violations"
            },
            "ban": {
                "usage": "/ban <member> [reason] [delete_days]",
                "description": "Permanently ban a member from the server with optional message deletion",
                "examples": ["/ban @spammer", "/ban @user Harassment 7"],
                "permissions": "Admin+", 
                "best_practices": "• Use for serious violations only\n• Always document reason\n• Consider delete_days for spam cleanup\n• Review ban list regularly"
            },
            "timeout": {
                "usage": "/timeout <member> <duration> [reason]",
                "description": "Temporarily mute a member for specified duration (1m-28d)",
                "examples": ["/timeout @user 10m", "/timeout @user 1h Breaking rules"],
                "permissions": "Moderator+",
                "best_practices": "• Use for cooling off periods\n• Start with shorter durations\n• Explain timeout reason clearly\n• Monitor behavior after timeout"
            },
            "clear": {
                "usage": "/clear <amount> [member]",
                "description": "Delete multiple messages, optionally from specific member (1-100 messages)",
                "examples": ["/clear 10", "/clear 50 @spammer"],
                "permissions": "Moderator+",
                "best_practices": "• Start with smaller amounts\n• Use member filter for targeted cleanup\n• Be careful in active channels\n• Consider pinned messages"
            },
            
            # Warning System
            "warn": {
                "usage": "/warn <member> <reason>",
                "description": "Issue warning to member. Auto-ban triggers at threshold",
                "examples": ["/warn @user Inappropriate language", "/warn @user Rule violation #3"],
                "permissions": "Moderator+",
                "best_practices": "• Be specific with reasons\n• Use progressive discipline\n• Check existing warnings first\n• Follow up on behavior changes"
            },
            "checkwarns": {
                "usage": "/checkwarns [member]",
                "description": "View warning history for yourself or another member",
                "examples": ["/checkwarns", "/checkwarns @user"],
                "permissions": "Everyone (own) / Moderator+ (others)",
                "best_practices": "• Regular self-checks\n• Monitor member progress\n• Use for accountability\n• Clear expired warnings"
            },
            "clearwarn": {
                "usage": "/clearwarn <member> <warning_id>",
                "description": "Remove a specific warning from member's record",
                "examples": ["/clearwarn @user 1", "/clearwarn @user 3"],
                "permissions": "Admin+",
                "best_practices": "• Use for resolved issues\n• Keep documentation\n• Consider warning age\n• Communicate changes"
            }
        }

    @commands.hybrid_command(name="help", description="📖 Interactive help menu or detailed command info")
    async def help_cmd(self, ctx, command: str = None):
        """Interactive help system with cog navigation and detailed command information"""
        if command:
            await self._show_command_details(ctx, command.lower())
        else:
            await self._show_main_help_menu(ctx)

    async def _show_main_help_menu(self, ctx):
        """Show the main interactive help menu with cog navigation"""
        embed = discord.Embed(
            title="🤖 Community Manager Bot - Help Menu",
            description="Welcome to the interactive help system! Select a category below to explore commands:",
            color=0x2F3136
        )
        
        # Add cog categories
        for cog_num, cog_data in self.cog_info.items():
            if self._is_cog_enabled(cog_num):
                embed.add_field(
                    name=f"{cog_num}️⃣ {cog_data['name']}",
                    value=cog_data['description'],
                    inline=False
                )
        
        embed.add_field(
            name="💡 Quick Tips",
            value="• Use `/help <command>` for detailed command info\n• Click category buttons to browse commands\n• Most commands support `/help` integration",
            inline=False
        )
        
        embed.set_footer(text="🚀 Navigate with buttons below • Commands update automatically")
        
        view = HelpMenuView(self, ctx.author)
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    async def _show_command_details(self, ctx, command_name):
        """Show detailed information about a specific command"""
        if command_name in self.command_details:
            details = self.command_details[command_name]
            
            embed = discord.Embed(
                title=f"📖 Command Details: /{command_name}",
                description=details['description'],
                color=0x00ff00
            )
            
            embed.add_field(
                name="📝 Usage",
                value=f"`{details['usage']}`",
                inline=False
            )
            
            embed.add_field(
                name="🔐 Required Permissions",
                value=details['permissions'],
                inline=True
            )
            
            if 'examples' in details:
                examples_text = "\n".join([f"`{ex}`" for ex in details['examples']])
                embed.add_field(
                    name="💡 Examples",
                    value=examples_text,
                    inline=False
                )
            
            if 'best_practices' in details:
                embed.add_field(
                    name="✨ Best Practices",
                    value=details['best_practices'],
                    inline=False
                )
            
            embed.set_footer(text="💡 Use /help for main menu • Questions? Ask a moderator!")
            
            view = CommandDetailsView(self, ctx.author)
            message = await ctx.send(embed=embed, view=view)
            view.message = message
        else:
            embed = discord.Embed(
                title="❌ Command Not Found",
                description=f"Command `/{command_name}` not found or no detailed help available.",
                color=0xff0000
            )
            embed.add_field(
                name="💡 Suggestion",
                value="Use `/help` without parameters to see all available commands.",
                inline=False
            )
            await ctx.send(embed=embed, ephemeral=True)

    def _is_cog_enabled(self, cog_number):
        """Check if a cog is enabled based on the cog number"""
        cog_mapping = {
            "1": "CoreCog",              # Always enabled
            "2": "ModerationCog",        # Check if moderation is enabled
            "3": "WarningsCog",          # Check if warnings is enabled  
            "4": "InvitesCog",           # Check if invites is enabled
            "5": "VerificationCog",      # Always enabled for verification
            "6": "AutoMod",              # Carl-bot automod
            "7": "CarlBotRoles",         # Carl-bot roles
            "8": "Starboard",            # Carl-bot starboard
            "9": "CarlBotUtils",         # Carl-bot utils
            "10": "CarlBotFun",          # Carl-bot fun
            "11": "CarlBotLogging",      # Carl-bot logging
            "12": "CarlBotTags",         # Carl-bot tags
            "13": "CarlBotLevels",       # Carl-bot levels
            "14": "CarlBotGames",        # Carl-bot games
            "15": "CarlBotFeeds"         # Carl-bot feeds
        }
        
        cog_name = cog_mapping.get(cog_number)
        if not cog_name:
            return False
            
        return cog_name in [cog.__class__.__name__ for cog in self.bot.cogs.values()]

    async def _show_cog_commands(self, interaction, cog_number):
        """Show commands for a specific cog"""
        if cog_number not in self.cog_info:
            await interaction.response.send_message("❌ Invalid category!", ephemeral=True)
            return
            
        if not self._is_cog_enabled(cog_number):
            await interaction.response.send_message("❌ This category is not enabled!", ephemeral=True)
            return
        
        cog_data = self.cog_info[cog_number]
        
        embed = discord.Embed(
            title=f"{cog_data['name']} Commands",
            description=cog_data['description'],
            color=0x2F3136
        )
        
        # Add commands for this cog
        command_text = ""
        for cmd, desc in cog_data['commands'].items():
            command_text += f"**{cmd}** - {desc}\n"
        
        if command_text:
            embed.add_field(
                name="📋 Available Commands",
                value=command_text,
                inline=False
            )
        else:
            embed.add_field(
                name="📋 Available Commands", 
                value="No commands available in this category.",
                inline=False
            )
            
        embed.add_field(
            name="💡 Pro Tip",
            value="Use `/help <command>` to get detailed information about any specific command!",
            inline=False
        )
        
        embed.set_footer(text="🏠 Use the button below to return to the main menu")
        
        view = BackToMenuView(self, interaction.user)
        await interaction.response.edit_message(embed=embed, view=view)

    @commands.hybrid_command(name="commands", description="📋 Show all available commands (legacy)")
    async def commands_cmd(self, ctx):
        """Legacy command list - recommends using the new help system"""
        embed = discord.Embed(
            title="📋 Available Commands (Legacy View)",
            description="This is the legacy command list. For a better experience, try our new interactive help system!",
            color=0xffa500
        )
        
        # Show a simplified command list
        all_commands = []
        for cog_data in self.cog_info.values():
            for cmd in cog_data['commands'].keys():
                all_commands.append(cmd)
        
        # Split into chunks for better display
        chunk_size = 15
        command_chunks = [all_commands[i:i + chunk_size] for i in range(0, len(all_commands), chunk_size)]
        
        for i, chunk in enumerate(command_chunks):
            embed.add_field(
                name=f"Commands {i*chunk_size + 1}-{min((i+1)*chunk_size, len(all_commands))}",
                value="\n".join(chunk),
                inline=True
            )
        
        embed.add_field(
            name="💡 Upgrade Suggestion",
            value="Try `/help` for our new interactive help system with detailed command info!",
            inline=False
        )
        
        view = UpgradeToHelpView(self, ctx.author)
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    @commands.hybrid_command(name="userinfo", description="👤 Show user information")
    async def user_info_cmd(self, ctx, member: discord.Member = None):
        """Display detailed information about a user"""
        if member is None:
            member = ctx.author
            
        embed = discord.Embed(
            title=f"👤 User Information: {member.display_name}",
            color=member.color if member.color != discord.Color.default() else 0x2F3136
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Basic info
        embed.add_field(name="🏷️ Username", value=f"{member.name}#{member.discriminator}", inline=True)
        embed.add_field(name="🆔 User ID", value=member.id, inline=True)
        embed.add_field(name="📅 Account Created", value=f"<t:{int(member.created_at.timestamp())}:F>", inline=False)
        embed.add_field(name="📥 Joined Server", value=f"<t:{int(member.joined_at.timestamp())}:F>", inline=False)
        
        # Roles
        if len(member.roles) > 1:
            roles = [role.mention for role in member.roles[1:]]  # Skip @everyone
            embed.add_field(name="🎭 Roles", value=" ".join(roles), inline=False)
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="serverinfo", description="📊 Show server information")
    async def server_info_cmd(self, ctx):
        """Display detailed information about the server"""
        guild = ctx.guild
        
        embed = discord.Embed(
            title=f"📊 Server Information: {guild.name}",
            color=0x2F3136
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        # Basic server info
        embed.add_field(name="🏷️ Server Name", value=guild.name, inline=True)
        embed.add_field(name="🆔 Server ID", value=guild.id, inline=True)
        embed.add_field(name="👑 Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)
        embed.add_field(name="📅 Created", value=f"<t:{int(guild.created_at.timestamp())}:F>", inline=False)
        
        # Member counts
        total_members = guild.member_count
        bots = len([m for m in guild.members if m.bot])
        humans = total_members - bots
        
        embed.add_field(name="👥 Members", value=f"Total: {total_members}\nHumans: {humans}\nBots: {bots}", inline=True)
        embed.add_field(name="📁 Channels", value=f"Text: {len(guild.text_channels)}\nVoice: {len(guild.voice_channels)}", inline=True)
        embed.add_field(name="🎭 Roles", value=len(guild.roles), inline=True)
        
        # Server features
        if guild.features:
            features = [feature.replace('_', ' ').title() for feature in guild.features]
            embed.add_field(name="✨ Features", value=", ".join(features[:5]), inline=False)
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="createinvite", description="📨 Create a server invite")
    async def create_invite_cmd(self, ctx, max_uses: int = 0, max_age: int = 0):
        """Create a server invite with custom settings"""
        try:
            invite = await ctx.channel.create_invite(max_uses=max_uses, max_age=max_age)
            
            embed = discord.Embed(
                title="📨 Invite Created!",
                description=f"Invite URL: {invite.url}",
                color=0x00ff00
            )
            embed.add_field(name="Max Uses", value=max_uses if max_uses > 0 else "Unlimited", inline=True)
            embed.add_field(name="Expires", value=f"<t:{int((discord.utils.utcnow().timestamp() + max_age))}:R>" if max_age > 0 else "Never", inline=True)
            
            await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to create invites in this channel!", ephemeral=True)

    @commands.hybrid_command(name="ping", description="🏓 Check bot latency")
    async def ping_cmd(self, ctx):
        """Check bot response time and latency"""
        embed = discord.Embed(title="🏓 Pong!", color=0x00ff00)
        embed.add_field(name="Bot Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="about", description="ℹ️ Show bot information")
    async def about_cmd(self, ctx):
        """Show information about the bot"""
        embed = discord.Embed(
            title="🤖 Community Manager Bot",
            description="Advanced Discord community management with verification, moderation, and automation features",
            color=0x2F3136
        )
        
        embed.add_field(
            name="✨ Features",
            value="• 🛡️ Advanced Verification System\n• ⚔️ Comprehensive Moderation\n• ⚠️ Warning System\n• 📨 Invite Tracking\n• 🛡️ Advanced Automod\n• 🎭 Role Management\n• ⭐ Starboard System\n• 🛠️ Utility Commands\n• 🎉 Fun Commands",
            inline=False
        )
        
        embed.add_field(
            name="📊 Statistics",
            value=f"• Servers: {len(self.bot.guilds)}\n• Users: {len(self.bot.users)}\n• Commands: 50+",
            inline=True
        )
        
        embed.add_field(
            name="🔗 Support",
            value="Use `/help` for command assistance\nContact server administrators for support",
            inline=True
        )
        
        embed.set_footer(text=f"Bot Version 2.0 • discord.py {discord.__version__}")
        await ctx.send(embed=embed)


class HelpMenuView(discord.ui.View):
    """Interactive view for the help menu with cog navigation"""
    
    def __init__(self, cog, author):
        super().__init__(timeout=300)
        self.cog = cog
        self.author = author
        self.message = None
        
        # Create buttons for each enabled cog (split into multiple rows)
        # Row 1: Categories 1-5
        for cog_num in ["1", "2", "3", "4", "5"]:
            if self.cog._is_cog_enabled(cog_num):
                cog_data = self.cog.cog_info[cog_num]
                button = discord.ui.Button(
                    label=f"{cog_num}. {cog_data['name']}",
                    style=discord.ButtonStyle.primary,
                    row=0
                )
                button.callback = self.create_cog_callback(cog_num)
                self.add_item(button)
        
        # Row 2: Categories 6-10  
        for cog_num in ["6", "7", "8", "9", "10"]:
            if self.cog._is_cog_enabled(cog_num):
                cog_data = self.cog.cog_info[cog_num]
                button = discord.ui.Button(
                    label=f"{cog_num}. {cog_data['name']}",
                    style=discord.ButtonStyle.secondary,
                    row=1
                )
                button.callback = self.create_cog_callback(cog_num)
                self.add_item(button)
        
        # Row 3: Categories 11-15
        for cog_num in ["11", "12", "13", "14", "15"]:
            if self.cog._is_cog_enabled(cog_num) and cog_num in self.cog.cog_info:
                cog_data = self.cog.cog_info[cog_num]
                button = discord.ui.Button(
                    label=f"{cog_num}. {cog_data['name']}",
                    style=discord.ButtonStyle.success,
                    row=2
                )
                button.callback = self.create_cog_callback(cog_num)
                self.add_item(button)

    def create_cog_callback(self, cog_number):
        async def callback(interaction):
            if interaction.user != self.author:
                await interaction.response.send_message("❌ This menu is not for you!", ephemeral=True)
                return
            await self.cog._show_cog_commands(interaction, cog_number)
        return callback


class BackToMenuView(discord.ui.View):
    """View for returning to the main help menu"""
    
    def __init__(self, cog, author):
        super().__init__(timeout=300)
        self.cog = cog
        self.author = author

    @discord.ui.button(label="⬅️ Back to Menu", style=discord.ButtonStyle.secondary, emoji="🏠")
    async def back_to_menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ This menu is not for you!", ephemeral=True)
            return
        
        # Create a fake context for the help menu
        class FakeContext:
            def __init__(self, interaction):
                self.author = interaction.user
                self.send = interaction.response.edit_message
                self.guild = interaction.guild
                self.channel = interaction.channel
        
        fake_ctx = FakeContext(interaction)
        await self.cog._show_main_help_menu(fake_ctx)


class CommandDetailsView(discord.ui.View):
    """View for command details with back to help option"""
    
    def __init__(self, cog, author):
        super().__init__(timeout=300)
        self.cog = cog
        self.author = author

    @discord.ui.button(label="⬅️ Back to Help", style=discord.ButtonStyle.secondary, emoji="📖")
    async def back_to_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ This menu is not for you!", ephemeral=True)
            return
        
        # Create a fake context for the help menu
        class FakeContext:
            def __init__(self, interaction):
                self.author = interaction.user
                self.send = interaction.response.edit_message
                self.guild = interaction.guild
                self.channel = interaction.channel
        
        fake_ctx = FakeContext(interaction)
        await self.cog._show_main_help_menu(fake_ctx)


class UpgradeToHelpView(discord.ui.View):
    """View for upgrading from legacy commands to new help system"""
    
    def __init__(self, cog, author):
        super().__init__(timeout=300)
        self.cog = cog
        self.author = author

    @discord.ui.button(label="🚀 Try New Help System", style=discord.ButtonStyle.success, emoji="✨")
    async def upgrade_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ This menu is not for you!", ephemeral=True)
            return
        
        # Create a fake context for the help menu
        class FakeContext:
            def __init__(self, interaction):
                self.author = interaction.user
                self.send = interaction.response.edit_message
                self.guild = interaction.guild
                self.channel = interaction.channel
        
        fake_ctx = FakeContext(interaction)
        await self.cog._show_main_help_menu(fake_ctx)


async def setup(bot):
    await bot.add_cog(CoreCog(bot)) 