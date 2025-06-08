import discord
from discord.ext import commands
import asyncio
import os
import logging
from dotenv import load_dotenv

# Load environment variables from config.env
load_dotenv('config.env')

# Check if file exists
if not os.path.exists('config.env'):
    print("❌ config.env file not found!")
    exit(1)

# Bot Configuration from .env file
TOKEN = os.getenv('DISCORD_TOKEN')

PREFIX = os.getenv('COMMAND_PREFIX', '!')
DATABASE_PATH = os.getenv('DATABASE_PATH', 'data/bot_data.db')
DEFAULT_WARN_THRESHOLD = int(os.getenv('DEFAULT_WARN_THRESHOLD', '3'))

# Feature toggles
ENABLE_WARNING_SYSTEM = os.getenv('ENABLE_WARNING_SYSTEM', 'true').lower() == 'true'
ENABLE_INVITE_TRACKING = os.getenv('ENABLE_INVITE_TRACKING', 'true').lower() == 'true'
ENABLE_MODERATION = os.getenv('ENABLE_MODERATION', 'true').lower() == 'true'
ENABLE_VERIFICATION = os.getenv('ENABLE_VERIFICATION', 'true').lower() == 'true'
ENABLE_AUTOMOD = os.getenv('ENABLE_AUTOMOD', 'true').lower() == 'true'
ENABLE_STARBOARD = os.getenv('ENABLE_STARBOARD', 'true').lower() == 'true'
ENABLE_TAGS = os.getenv('ENABLE_TAGS', 'true').lower() == 'true'
ENABLE_FEEDS = os.getenv('ENABLE_FEEDS', 'true').lower() == 'true'
ENABLE_ROLES = os.getenv('ENABLE_ROLES', 'true').lower() == 'true'
ENABLE_FUN = os.getenv('ENABLE_FUN', 'true').lower() == 'true'
ENABLE_UTILS = os.getenv('ENABLE_UTILS', 'true').lower() == 'true'

# Token validation
if not TOKEN or TOKEN == "your_bot_token_here":
    print("❌ ERROR: Bot token not properly configured!")
    print("📝 Please edit config.env and set DISCORD_TOKEN=your_actual_token")
    input("Press Enter to exit...")
    exit(1)

# Setup logging
log_level = os.getenv('LOG_LEVEL', 'INFO')
log_file = os.getenv('LOG_FILE', 'data/bot.log')

if not os.path.exists('data'):
    os.makedirs('data')

logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('discord_bot')

# Basic intents
intents = discord.Intents.default()
intents.message_content = True

class CommunityManagerBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=PREFIX,
            intents=intents,
            help_command=None
        )
        
        # Initialize database
        from utils.database import DatabaseManager
        self.db = DatabaseManager(DATABASE_PATH)
        self.db.init_database()
        
        logger.info("Bot initialized")
        
    async def setup_hook(self):
        """Load cogs based on feature toggles"""
        try:
            # Always load core functionality
            await self.load_extension('cogs.core')
            logger.info("✅ Core loaded")
            
            # Load moderation if enabled
            if ENABLE_MODERATION:
                await self.load_extension('cogs.moderation')
                logger.info("✅ Moderation loaded")
            
            # Load warning system if enabled
            if ENABLE_WARNING_SYSTEM:
                await self.load_extension('cogs.warnings')
                logger.info("✅ Warnings loaded")
                
            # Load invite tracking if enabled
            if ENABLE_INVITE_TRACKING:
                await self.load_extension('cogs.invites')
                logger.info("✅ Invites loaded")
                
            # Always load verification system (keeping 100% intact)
            if ENABLE_VERIFICATION:
                await self.load_extension('cogs.verification')
                logger.info("✅ Verification loaded")
            
            # Load additional features
            additional_cogs = []
            
            if ENABLE_AUTOMOD:
                additional_cogs.append('cogs.automod')
            if ENABLE_ROLES:
                additional_cogs.append('cogs.roles')
            if ENABLE_STARBOARD:
                additional_cogs.append('cogs.starboard')
            if ENABLE_FUN:
                additional_cogs.append('cogs.fun')
            if ENABLE_UTILS:
                additional_cogs.append('cogs.utils')
            if ENABLE_TAGS:
                additional_cogs.append('cogs.tags')
            if ENABLE_FEEDS:
                additional_cogs.append('cogs.feeds')
            
            for cog in additional_cogs:
                try:
                    await self.load_extension(cog)
                    logger.info(f"✅ {cog} loaded")
                except Exception as e:
                    logger.warning(f"⚠️ Could not load {cog}: {e}")
                
        except Exception as e:
            logger.error(f"❌ Failed to load cog: {e}")
    
    async def on_ready(self):
        logger.info(f'🤖 {self.user} is online!')
        logger.info(f'📊 Connected to {len(self.guilds)} servers')
        
        try:
            synced = await self.tree.sync()
            logger.info(f'✅ Synced {len(synced)} slash commands')
            print(f'🚀 Bot ready! {len(synced)} commands, {len(self.guilds)} servers')
        except Exception as e:
            logger.error(f'❌ Failed to sync commands: {e}')

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: `{error.param.name}`")
        elif isinstance(error, commands.CheckFailure):
            await ctx.send("❌ You don't have permission to use this command!")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("❌ Member not found!")
        elif isinstance(error, commands.RoleNotFound):
            await ctx.send("❌ Role not found!")
        else:
            await ctx.send(f"❌ An error occurred: {str(error)}")
            logger.error(f"Command error: {error}")



# Create and run bot
async def main():
    bot = CommunityManagerBot()
    
    try:
        await bot.start(TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
    finally:
        await bot.close()

if __name__ == "__main__":
    print("🚀 Starting Community Manager Bot...")
    
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")
        input("Press Enter to exit...") 