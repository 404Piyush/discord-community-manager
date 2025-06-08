"""
Carl-bot Style Fun Commands
"""

import discord
from discord.ext import commands
from discord import app_commands
import random
import re
import aiohttp
import json
from typing import Optional
import logging

logger = logging.getLogger('discord_bot')

class FunCog(commands.Cog):
    """🎉 Fun Commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        
        # Animal image databases (mock data for now)
        self.animal_images = {
            'cat': ['https://cataas.com/cat'],
            'dog': ['https://dog.ceo/api/breeds/image/random'],
            'aww': ['https://www.reddit.com/r/aww.json']
        }
        
        # 8ball responses
        self.eightball_responses = [
            "It is certain", "Reply hazy, try again", "Don't count on it",
            "It is decidedly so", "Ask again later", "My reply is no",
            "Without a doubt", "Better not tell you now", "My sources say no",
            "Yes definitely", "Cannot predict now", "Outlook not so good",
            "You may rely on it", "Concentrate and ask again", "Very doubtful",
            "As I see it, yes", "Most likely", "Outlook good",
            "Yes", "Signs point to yes"
        ]
        
        # Cat facts
        self.cat_facts = [
            "Cats sleep 70% of their lives",
            "A group of cats is called a 'clowder'",
            "Cats have 32 muscles that control their ears",
            "A cat's purr can heal bones",
            "Cats can't taste sweetness",
            "A cat's nose print is unique, like a human's fingerprint",
            "Cats can run up to 30 mph",
            "A cat's brain is 90% similar to a human's brain",
            "Cats have been domesticated for over 4,000 years",
            "A cat's meow is specifically for humans"
        ]
        
        # Dog facts
        self.dog_facts = [
            "Dogs have an incredible sense of smell",
            "A dog's mouth exerts 150-300 pounds of pressure per square inch",
            "Dogs can be trained to detect diseases",
            "A dog's nose print is unique",
            "Dogs can see in color, but not as many as humans",
            "The average dog can learn 165 words",
            "Dogs sweat through their paw pads",
            "A dog's hearing is twice as sensitive as humans",
            "Dogs have three eyelids",
            "Dogs can fall in love by releasing oxytocin"
        ]
    
    async def cog_unload(self):
        """Clean up when cog is unloaded"""
        await self.session.close()
    
    async def get_animal_image(self, animal_type: str) -> Optional[str]:
        """Get random animal image"""
        try:
            if animal_type == 'cat':
                return "https://cataas.com/cat"
            elif animal_type == 'dog':
                async with self.session.get('https://dog.ceo/api/breeds/image/random') as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data['message']
            return None
        except:
            return None
    
    # Animal Commands
    @app_commands.command(name="cat", description="🐱 Get random cat pictures and facts")
    async def cat(self, interaction: discord.Interaction):
        """Get random cat pictures with facts"""
        await interaction.response.defer()
        
        try:
            # Try to get cat image from API
            try:
                async with self.session.get('https://api.thecatapi.com/v1/images/search') as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        cat_url = data[0]['url']
                    else:
                        cat_url = "https://placekitten.com/400/300"
            except:
                cat_url = "https://placekitten.com/400/300"
            
            embed = discord.Embed(
                title="🐱 Random Cat",
                description=random.choice(self.cat_facts),
                color=0xff69b4
            )
            embed.set_image(url=cat_url)
            embed.set_footer(text="😺 Meow!")
            
            await interaction.followup.send(embed=embed)
        
        except Exception as e:
            await interaction.followup.send(f"❌ Error getting cat: {e}", ephemeral=True)
    
    @app_commands.command(name="dog", description="🐶 Get random dog pictures and facts")
    async def dog(self, interaction: discord.Interaction):
        """Get random dog pictures with facts"""
        await interaction.response.defer()
        
        try:
            # Try to get dog image from API
            try:
                async with self.session.get('https://dog.ceo/api/breeds/image/random') as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        dog_url = data['message']
                    else:
                        dog_url = "https://place-puppy.com/400x300"
            except:
                dog_url = "https://place-puppy.com/400x300"
            
            embed = discord.Embed(
                title="🐶 Random Dog",
                description=random.choice(self.dog_facts),
                color=0x8b4513
            )
            embed.set_image(url=dog_url)
            embed.set_footer(text="🐕 Woof!")
            
            await interaction.followup.send(embed=embed)
        
        except Exception as e:
            await interaction.followup.send(f"❌ Error getting dog: {e}", ephemeral=True)
    
    @app_commands.command(name="catbomb")
    async def catbomb_cmd(self, interaction: discord.Interaction):
        """Get 5 random cat images"""
        await interaction.response.defer()
        
        embeds = []
        for i in range(5):
            image_url = await self.get_animal_image('cat')
            if image_url:
                embed = discord.Embed(title=f"🐱 Cat #{i+1}", color=discord.Color.orange())
                embed.set_image(url=f"{image_url}?{i}")  # Add parameter to make URLs unique
                embeds.append(embed)
        
        if embeds:
            # Send first embed, then edit with all embeds
            await interaction.followup.send(embeds=embeds[:1])
            if len(embeds) > 1:
                for embed in embeds[1:]:
                    await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("❌ Could not fetch cat images!")
    
    # Text Transformation Commands
    @app_commands.command(name="aesthetics", description="✨ Make text aesthetic")
    @app_commands.describe(text="Text to transform")
    async def aesthetics_cmd(self, interaction: discord.Interaction, text: str):
        """Convert text to aesthetic fullwidth characters"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission!", ephemeral=True)
            return
        
        if len(text) > 100:
            await interaction.response.send_message("❌ Text too long! (Max 100 characters)", ephemeral=True)
            return
        
        # Convert to fullwidth characters
        aesthetic_text = ""
        for char in text:
            if 'A' <= char <= 'Z':
                aesthetic_text += chr(ord(char) - ord('A') + ord('Ａ'))
            elif 'a' <= char <= 'z':
                aesthetic_text += chr(ord(char) - ord('a') + ord('ａ'))
            elif '0' <= char <= '9':
                aesthetic_text += chr(ord(char) - ord('0') + ord('０'))
            elif char == ' ':
                aesthetic_text += '　'  # Fullwidth space
            else:
                aesthetic_text += char
        
        await interaction.response.send_message(aesthetic_text)
    
    @app_commands.command(name="clap", description="👏 Add clap emojis between words")
    @app_commands.describe(text="Text to add claps to")
    async def clap_cmd(self, interaction: discord.Interaction, text: str):
        """Add clap emojis between words"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission!", ephemeral=True)
            return
        
        if len(text) > 100:
            await interaction.response.send_message("❌ Text too long! (Max 100 characters)", ephemeral=True)
            return
        
        result = "👏" + "👏".join(text.split()) + "👏"
        
        await interaction.response.send_message(result)
    
    @app_commands.command(name="emojify", description="😀 Convert text to emojis")
    @app_commands.describe(text="Text to convert to emojis")
    async def emojify_cmd(self, interaction: discord.Interaction, text: str):
        """Convert text to regional indicator emojis"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission!", ephemeral=True)
            return
        
        if len(text) > 50:
            await interaction.response.send_message("❌ Text too long! (Max 50 characters)", ephemeral=True)
            return
        
        emoji_text = ""
        for char in text.lower():
            if 'a' <= char <= 'z':
                emoji_text += f":regional_indicator_{char}: "
            elif char == ' ':
                emoji_text += "   "
            elif char.isdigit():
                numbers = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
                emoji_text += f":{numbers[int(char)]}: "
            else:
                emoji_text += char + " "
        
        if len(emoji_text) > 2000:
            await interaction.response.send_message("❌ Result too long!", ephemeral=True)
            return
        
        await interaction.response.send_message(emoji_text or "❌ No valid characters to convert!")
    
    @app_commands.command(name="owofy", description="🥺 Convert text to OwO speak")
    @app_commands.describe(text="Text to owofy")
    async def owofy_cmd(self, interaction: discord.Interaction, text: str):
        """Transform text to owo speech pattern"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission!", ephemeral=True)
            return
        
        if len(text) > 200:
            await interaction.response.send_message("❌ Text too long! (Max 200 characters)", ephemeral=True)
            return
        
        # OwO replacements
        replacements = {
            'r': 'w', 'R': 'W', 'l': 'w', 'L': 'W',
            'na': 'nya', 'Na': 'Nya', 'NA': 'NYA',
            'no': 'nyo', 'No': 'Nyo', 'NO': 'NYO',
            'ni': 'nyi', 'Ni': 'Nyi', 'NI': 'NYI',
            'nu': 'nyu', 'Nu': 'Nyu', 'NU': 'NYU',
            'ne': 'nye', 'Ne': 'Nye', 'NE': 'NYE'
        }
        
        owo_text = text
        for old, new in replacements.items():
            owo_text = owo_text.replace(old, new)
        
        # Add random OwO expressions
        expressions = ['OwO', 'UwU', '>w<', '^w^', '(owo)', '(uwu)']
        if random.random() < 0.3:
            owo_text += ' ' + random.choice(expressions)
        
        await interaction.response.send_message(owo_text)
    
    @app_commands.command(name="space", description="📏 Add spaces between characters")
    @app_commands.describe(character="Character to use", text="Text to space out")
    async def space_cmd(self, interaction: discord.Interaction, character: str, text: str):
        """Add custom character between words"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission!", ephemeral=True)
            return
        
        if len(text) > 50:
            await interaction.response.send_message("❌ Text too long! (Max 50 characters)", ephemeral=True)
            return
        
        result = character + character.join(text.split()) + character
        
        await interaction.response.send_message(result)
    
    @app_commands.command(name="smallcaps", description="🔠 Convert text to small caps")
    @app_commands.describe(text="Text to convert to small caps")
    async def smallcaps_cmd(self, interaction: discord.Interaction, text: str):
        """Convert text to small caps"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission!", ephemeral=True)
            return
        
        smallcaps_map = {
            'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ғ',
            'g': 'ɢ', 'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ',
            'm': 'ᴍ', 'n': 'ɴ', 'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ',
            's': 's', 't': 'ᴛ', 'u': 'ᴜ', 'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x',
            'y': 'ʏ', 'z': 'ᴢ'
        }
        
        result = ''.join(smallcaps_map.get(char.lower(), char) for char in text)
        
        await interaction.response.send_message(result)
    
    # Other Fun Commands
    @app_commands.command(name="echo", description="📢 Make the bot say something")
    @app_commands.describe(message="Message to echo", channel="Channel to send to")
    async def echo_cmd(self, interaction: discord.Interaction, message: str, 
                      channel: discord.TextChannel = None):
        """Make the bot say something"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission!", ephemeral=True)
            return
        
        target_channel = channel or interaction.channel
        
        try:
            await target_channel.send(message)
            if channel:
                await interaction.response.send_message(f"✅ Message sent to {channel.mention}!", ephemeral=True)
            else:
                await interaction.response.send_message("✅ Message sent!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="pick", description="🎯 Pick randomly from options")
    @app_commands.describe(choices="Comma-separated choices")
    async def pick_cmd(self, interaction: discord.Interaction, choices: str):
        """Pick a random choice from a list"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission!", ephemeral=True)
            return
        
        choice_list = [choice.strip() for choice in choices.split(',')]
        
        if len(choice_list) < 2:
            await interaction.response.send_message("❌ Please provide at least 2 choices separated by commas!", ephemeral=True)
            return
        
        chosen = random.choice(choice_list)
        
        embed = discord.Embed(
            title="🎯 Random Choice",
            description=f"I choose: **{chosen}**",
            color=discord.Color.blue()
        )
        embed.add_field(name="Options", value=", ".join(choice_list), inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="coinflip", description="🪙 Flip a coin")
    async def coinflip_cmd(self, interaction: discord.Interaction):
        """Flip a coin"""
        result = random.choice(["Heads", "Tails"])
        emoji = "🪙" if result == "Heads" else "🔘"
        
        embed = discord.Embed(
            title="🪙 Coin Flip",
            description=f"{emoji} **{result}!**",
            color=discord.Color.gold()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="roll", description="🎲 Roll dice")
    @app_commands.describe(dice="Dice notation (e.g., 1d20, 2d6)")
    async def roll_cmd(self, interaction: discord.Interaction, dice: str = "1d6"):
        """Roll dice"""
        try:
            # Parse dice notation (e.g., "2d6", "1d20")
            if 'd' not in dice.lower():
                # Single number, treat as upper bound
                upper = int(dice)
                result = random.randint(1, upper)
                embed = discord.Embed(
                    title="🎲 Dice Roll",
                    description=f"Rolling 1-{upper}: **{result}**",
                    color=discord.Color.green()
                )
            else:
                parts = dice.lower().split('d')
                if len(parts) != 2:
                    raise ValueError("Invalid dice format")
                
                num_dice = int(parts[0]) if parts[0] else 1
                sides = int(parts[1])
                
                if num_dice > 20:
                    await interaction.response.send_message("❌ Maximum 20 dice allowed!", ephemeral=True)
                    return
                
                if sides > 1000:
                    await interaction.response.send_message("❌ Maximum 1000 sides allowed!", ephemeral=True)
                    return
                
                rolls = [random.randint(1, sides) for _ in range(num_dice)]
                total = sum(rolls)
                
                embed = discord.Embed(
                    title="🎲 Dice Roll",
                    description=f"Rolling {num_dice}d{sides}",
                    color=discord.Color.green()
                )
                
                if num_dice == 1:
                    embed.add_field(name="Result", value=f"**{total}**", inline=False)
                else:
                    embed.add_field(name="Rolls", value=" + ".join(map(str, rolls)), inline=False)
                    embed.add_field(name="Total", value=f"**{total}**", inline=False)
            
            await interaction.response.send_message(embed=embed)
            
        except ValueError:
            await interaction.response.send_message("❌ Invalid dice format! Use formats like `1d20`, `2d6`, or just `100`", ephemeral=True)
    
    @app_commands.command(name="8ball", description="🎱 Ask the magic 8-ball a question")
    @app_commands.describe(question="Question to ask the magic 8ball")
    async def eightball_cmd(self, interaction: discord.Interaction, question: str):
        """Ask the magic 8ball a question"""
        response = random.choice(self.eightball_responses)
        
        embed = discord.Embed(
            title="🎱 Magic 8-Ball",
            color=discord.Color.purple()
        )
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=f"**{response}**", inline=False)
        embed.set_thumbnail(url="https://upload.wikimedia.org/wikipedia/commons/f/fd/8-Ball_Pool.svg")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="urbandictionary", description="📖 Look up Urban Dictionary definitions")
    @app_commands.describe(word="Word to look up")
    async def urban_cmd(self, interaction: discord.Interaction, word: str):
        """Look up a word on Urban Dictionary (NSFW channels only)"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission!", ephemeral=True)
            return
        
        if not getattr(interaction.channel, 'nsfw', False):
            await interaction.response.send_message("❌ This command can only be used in NSFW channels!", ephemeral=True)
            return
        
        # Mock response since we can't easily access UrbanDictionary API
        embed = discord.Embed(
            title=f"📚 Urban Dictionary: {word}",
            description="*Feature temporarily unavailable*\n\nThis would normally show Urban Dictionary definitions.",
            color=discord.Color.orange()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="addemoji", description="🖼️ Add an emoji to the server")
    @app_commands.describe(name="Name for the emoji", url="URL of the image")
    async def addemoji_cmd(self, interaction: discord.Interaction, name: str, url: str = None):
        """Add an emoji to the server"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            # Get image from URL or attachment
            image_data = None
            
            if url:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            image_data = await resp.read()
            elif interaction.message and interaction.message.attachments:
                attachment = interaction.message.attachments[0]
                image_data = await attachment.read()
            else:
                await interaction.followup.send("❌ Please provide an image URL or attachment!")
                return
            
            if not image_data:
                await interaction.followup.send("❌ Could not fetch image!")
                return
            
            # Add emoji to server
            emoji = await interaction.guild.create_custom_emoji(name=name, image=image_data)
            await interaction.followup.send(f"✅ Added emoji {emoji} with name `{name}`!")
            
        except discord.HTTPException as e:
            await interaction.followup.send(f"❌ Failed to add emoji: {str(e)}")
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}")

async def setup(bot):
    await bot.add_cog(FunCog(bot)) 