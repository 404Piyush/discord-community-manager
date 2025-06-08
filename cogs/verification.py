import discord
from discord.ext import commands
import asyncio
import random
import string
import logging
import io
import os
from captcha.image import ImageCaptcha
from utils.permissions import has_permission

logger = logging.getLogger('discord_bot')

class VerificationCog(commands.Cog):
    """🛡️ Advanced verification system with comprehensive setup and multiple captcha types"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.verification_sessions = {}
        self.setup_sessions = {}
        
    @commands.hybrid_command(name="setup-verification", description="🛡️ Setup comprehensive verification system (Admin+)")
    @has_permission("admin")
    async def setup_verification(self, ctx):
        """Interactive verification setup with modern UI"""
        
        if ctx.author.id in self.setup_sessions:
            session = self.setup_sessions[ctx.author.id]
            embed = discord.Embed(
                title="⚠️ Setup Session In Progress",
                description="You already have an active verification setup session!",
                color=0xff9900
            )
            
            if 'message' in session:
                try:
                    message = session['message']
                    embed.add_field(
                        name="🔗 Go to Setup",
                        value=f"[Click here to continue your setup]({message.jump_url})",
                        inline=False
                    )
                except:
                    pass
            
            embed.add_field(
                name="📋 Current Step",
                value=f"Step {session.get('step', 1)}/5",
                inline=True
            )
            
            view = discord.ui.View()
            
            # Add cancel session button
            cancel_button = discord.ui.Button(
                label="🗑️ Cancel Current Session",
                style=discord.ButtonStyle.danger,
                emoji="🗑️"
            )
            
            async def cancel_callback(interaction):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("❌ Only the command user can do this!", ephemeral=True)
                    return
                
                if ctx.author.id in self.setup_sessions:
                    del self.setup_sessions[ctx.author.id]
                
                await interaction.response.edit_message(
                    embed=discord.Embed(
                        title="✅ Session Cancelled",
                        description="You can now start a new setup session with `/setup-verification`",
                        color=0x00ff00
                    ),
                    view=None
                )
            
            cancel_button.callback = cancel_callback
            view.add_item(cancel_button)
            
            await ctx.send(embed=embed, view=view)
            return
            
        self.setup_sessions[ctx.author.id] = {
            'guild_id': ctx.guild.id,
            'config': {},
            'step': 1
        }
        
        try:
            await self._start_setup_ui(ctx)
        except Exception as e:
            if ctx.author.id in self.setup_sessions:
                del self.setup_sessions[ctx.author.id]
            await ctx.send(f"❌ Setup failed: {str(e)}")
    
    async def _start_setup_ui(self, ctx):
        """Start the modern setup wizard with buttons"""
        embed = discord.Embed(
            title="🛡️ Verification Setup Wizard",
            description="I'll guide you through setting up verification in 5 easy steps!",
            color=0x0099ff
        )
        
        embed.add_field(
            name="📋 Setup Process", 
            value="**Step 1/6:** Channel Selection\n**Step 2/6:** Verification Method\n**Step 3/6:** Text Captcha UI\n**Step 4/6:** Role Configuration\n**Step 5/6:** Security Settings\n**Step 6/6:** Review & Activate", 
            inline=False
        )
        
        embed.add_field(
            name="✨ Benefits",
            value="• Stop spam & raids\n• Automated verification\n• Multiple security levels\n• Easy management",
            inline=False
        )
        
        embed.set_footer(text="Click 'Start Setup' to begin or 'Cancel' to exit")
        
        view = SetupWizardView(self, ctx.author)
        message = await ctx.send(embed=embed, view=view)
        
        # Store message for editing
        self.setup_sessions[ctx.author.id]['message'] = message
    
    async def _step_1_channel(self, ctx):
        """Step 1: Channel selection"""
        embed = discord.Embed(
            title="📍 Step 1: Verification Channel",
            description="Choose how to set up your verification channel:",
            color=0x0099ff
        )
        
        embed.add_field(name="1️⃣ Use Existing", value="Select current channel", inline=True)
        embed.add_field(name="2️⃣ Create New", value="Create verification channel", inline=True)
        embed.set_footer(text="Type 1 or 2")
        
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.strip() in ["1", "2"]
        
        try:
            choice = await self.bot.wait_for('message', timeout=60.0, check=check)
            
            if choice.content.strip() == "1":
                await self._select_existing_channel(ctx)
            else:
                await self._create_new_channel(ctx)
                
        except asyncio.TimeoutError:
            del self.setup_sessions[ctx.author.id]
            await ctx.send("⏰ Step timed out.")
    
    async def _select_existing_channel(self, ctx):
        """Select existing channel"""
        channels = [ch for ch in ctx.guild.text_channels if ch.permissions_for(ctx.guild.me).send_messages]
        
        if not channels:
            await ctx.send("❌ No suitable channels. Creating new one...")
            await self._create_new_channel(ctx)
            return
        
        embed = discord.Embed(title="📋 Select Channel", color=0x0099ff)
        
        channel_list = ""
        for i, ch in enumerate(channels[:10]):
            channel_list += f"{i+1}. {ch.mention}\n"
        
        embed.add_field(name="Channels", value=channel_list, inline=False)
        embed.set_footer(text="Type the number")
        
        await ctx.send(embed=embed)
        
        def check(m):
            return (m.author == ctx.author and m.channel == ctx.channel and 
                   m.content.strip().isdigit() and 1 <= int(m.content.strip()) <= len(channels))
        
        try:
            choice = await self.bot.wait_for('message', timeout=60.0, check=check)
            selected = channels[int(choice.content.strip()) - 1]
            
            self.setup_sessions[ctx.author.id]['config']['channel'] = selected
            await ctx.send(f"✅ Selected: {selected.mention}")
            await self._step_2_verification_type(ctx)
            
        except asyncio.TimeoutError:
            del self.setup_sessions[ctx.author.id]
            await ctx.send("⏰ Selection timed out.")
    
    async def _create_new_channel(self, ctx):
        """Create new verification channel"""
        embed = discord.Embed(
            title="🆕 Create Channel",
            description="What should I name the verification channel?",
            color=0x0099ff
        )
        embed.add_field(name="💡 Suggestions", value="`verification`, `verify-here`, `gate`", inline=False)
        embed.set_footer(text="Type the channel name")
        
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and len(m.content.strip()) >= 2
        
        try:
            name_msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            name = name_msg.content.strip().replace(" ", "-").lower()
            
            try:
                overwrites = {
                    ctx.guild.default_role: discord.PermissionOverwrite(
                        read_messages=True, send_messages=False
                    ),
                    ctx.guild.me: discord.PermissionOverwrite(
                        read_messages=True, send_messages=True, manage_messages=True
                    )
                }
                
                new_channel = await ctx.guild.create_text_channel(
                    name=name,
                    topic="🛡️ Server verification - Complete to gain access!",
                    overwrites=overwrites,
                    reason="Verification setup"
                )
                
                self.setup_sessions[ctx.author.id]['config']['channel'] = new_channel
                await ctx.send(f"✅ Created: {new_channel.mention}")
                await self._step_2_verification_type(ctx)
                
            except discord.Forbidden:
                await ctx.send("❌ No permission to create channels!")
                del self.setup_sessions[ctx.author.id]
                
        except asyncio.TimeoutError:
            del self.setup_sessions[ctx.author.id]
            await ctx.send("⏰ Creation timed out.")
    
    async def _step_2_verification_type(self, ctx):
        """Step 2: Verification method selection"""
        embed = discord.Embed(
            title="🎯 Step 2: Verification Method",
            description="Choose your verification security level:",
            color=0x0099ff
        )
        
        methods = [
            "1️⃣ **Simple Button** - One click (fast)",
            "2️⃣ **Image Captcha** - 🔒 Bot-proof image verification",
            "3️⃣ **Math Captcha** - Solve math problems",
            "4️⃣ **Text Captcha** - Type text correctly", 
            "5️⃣ **Emoji Sequence** - Remember emojis",
            "6️⃣ **Word Scramble** - Unscramble words",
            "7️⃣ **Color Buttons** - Click correct color",
            "8️⃣ **Multi-Stage** - Multiple challenges"
        ]
        
        embed.add_field(name="🛡️ Methods", value="\n".join(methods), inline=False)
        embed.add_field(name="💡 Recommendation", value="**🔒 Image Captcha (2)** - Most secure, bot-proof", inline=False)
        embed.set_footer(text="Type 1-7")
        
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.strip() in [str(i) for i in range(1, 8)]
        
        try:
            choice = await self.bot.wait_for('message', timeout=60.0, check=check)
            
            types = {
                "1": "simple_button",
                "2": "image_captcha",
                "3": "math_captcha", 
                "4": "text_captcha",
                "5": "emoji_sequence",
                "6": "word_scramble",
                "7": "color_buttons",
                "8": "multi_stage"
            }
            
            selected_type = types[choice.content.strip()]
            self.setup_sessions[ctx.author.id]['config']['verification_type'] = selected_type
            
            await ctx.send(f"✅ Selected: **{selected_type.replace('_', ' ').title()}**")
            await self._step_3_role(ctx)
            
        except asyncio.TimeoutError:
            del self.setup_sessions[ctx.author.id]
            await ctx.send("⏰ Selection timed out.")
    
    async def _step_3_role(self, ctx):
        """Step 3: Verified role setup"""
        embed = discord.Embed(
            title="👤 Step 3: Verified Role",
            description="What role should verified members get?",
            color=0x0099ff
        )
        
        embed.add_field(name="1️⃣ Use Existing", value="Select current role", inline=True)
        embed.add_field(name="2️⃣ Create New", value="Create 'Verified' role", inline=True)
        embed.set_footer(text="Type 1 or 2")
        
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.strip() in ["1", "2"]
        
        try:
            choice = await self.bot.wait_for('message', timeout=60.0, check=choice)
            
            if choice.content.strip() == "1":
                await self._select_existing_role(ctx)
            else:
                await self._create_verified_role(ctx)
                
        except asyncio.TimeoutError:
            del self.setup_sessions[ctx.author.id]
            await ctx.send("⏰ Step timed out.")
    
    async def _select_existing_role(self, ctx):
        """Select existing role"""
        roles = [r for r in ctx.guild.roles if not r.is_bot_managed() and r != ctx.guild.default_role]
        
        if not roles:
            await ctx.send("❌ No suitable roles. Creating new one...")
            await self._create_verified_role(ctx)
            return
        
        embed = discord.Embed(title="📋 Select Role", color=0x0099ff)
        
        role_list = ""
        for i, role in enumerate(roles[:10]):
            role_list += f"{i+1}. {role.mention}\n"
        
        embed.add_field(name="Roles", value=role_list, inline=False)
        embed.set_footer(text="Type the number")
        
        await ctx.send(embed=embed)
        
        def check(m):
            return (m.author == ctx.author and m.channel == ctx.channel and 
                   m.content.strip().isdigit() and 1 <= int(m.content.strip()) <= len(roles))
        
        try:
            choice = await self.bot.wait_for('message', timeout=60.0, check=check)
            selected = roles[int(choice.content.strip()) - 1]
            
            self.setup_sessions[ctx.author.id]['config']['verified_role'] = selected
            await ctx.send(f"✅ Selected: {selected.mention}")
            await self._step_4_settings(ctx)
            
        except asyncio.TimeoutError:
            del self.setup_sessions[ctx.author.id]
            await ctx.send("⏰ Selection timed out.")
    
    async def _create_verified_role(self, ctx):
        """Create verified role"""
        try:
            role = await ctx.guild.create_role(
                name="✅ Verified",
                color=discord.Color.green(),
                reason="Verification setup"
            )
            
            self.setup_sessions[ctx.author.id]['config']['verified_role'] = role
            await ctx.send(f"✅ Created: {role.mention}")
            await self._step_4_settings(ctx)
            
        except discord.Forbidden:
            await ctx.send("❌ No permission to create roles!")
            del self.setup_sessions[ctx.author.id]
    
    async def _step_4_settings(self, ctx):
        """Step 4: Advanced settings"""
        embed = discord.Embed(
            title="⚙️ Step 4: Settings",
            description="Configure timeout (60-600 seconds):",
            color=0x0099ff
        )
        embed.add_field(name="💡 Recommendation", value="300 seconds (5 minutes)", inline=False)
        embed.set_footer(text="Type number of seconds")
        
        await ctx.send(embed=embed)
        
        def check(m):
            return (m.author == ctx.author and m.channel == ctx.channel and 
                   m.content.strip().isdigit() and 60 <= int(m.content.strip()) <= 600)
        
        try:
            timeout_msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            timeout = int(timeout_msg.content.strip())
            
            self.setup_sessions[ctx.author.id]['config']['timeout'] = timeout
            self.setup_sessions[ctx.author.id]['config']['max_attempts'] = 3  # Default
            
            await ctx.send(f"✅ Timeout set to {timeout} seconds")
            await self._step_5_review(ctx)
            
        except asyncio.TimeoutError:
            del self.setup_sessions[ctx.author.id]
            await ctx.send("⏰ Settings timed out.")
    
    async def _step_5_review(self, ctx):
        """Step 5: Final review"""
        config = self.setup_sessions[ctx.author.id]['config']
        
        embed = discord.Embed(
            title="📋 Step 5: Review Configuration",
            description="Please review your settings:",
            color=0x0099ff
        )
        
        embed.add_field(name="📍 Channel", value=config['channel'].mention, inline=True)
        embed.add_field(name="👤 Role", value=config['verified_role'].mention, inline=True)
        embed.add_field(name="🎯 Method", value=config['verification_type'].replace('_', ' ').title(), inline=True)
        embed.add_field(name="⏰ Timeout", value=f"{config['timeout']} seconds", inline=True)
        
        embed.set_footer(text="React ✅ to save or ❌ to cancel")
        
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        
        def check(reaction, user):
            return (user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and 
                   reaction.message.id == msg.id)
        
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
            
            if str(reaction.emoji) == "❌":
                del self.setup_sessions[ctx.author.id]
                await ctx.send("❌ Setup cancelled.")
                return
            
            await self._save_config(ctx, config)
            
        except asyncio.TimeoutError:
            del self.setup_sessions[ctx.author.id]
            await ctx.send("⏰ Review timed out.")
    
    async def _save_config(self, ctx, config):
        """Save configuration to database"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS verification_config (
                    guild_id INTEGER PRIMARY KEY,
                    verification_channel_id INTEGER,
                    verified_role_id INTEGER,
                    verification_type TEXT,
                    timeout_duration INTEGER,
                    max_attempts INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                INSERT OR REPLACE INTO verification_config 
                (guild_id, verification_channel_id, verified_role_id, verification_type, 
                 timeout_duration, max_attempts)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                ctx.guild.id,
                config['channel'].id,
                config['verified_role'].id,
                config['verification_type'],
                config['timeout'],
                config['max_attempts']
            ))
            
            conn.commit()
            conn.close()
            
            del self.setup_sessions[ctx.author.id]
            
            # Send verification message to channel
            await self._send_verification_message(config['channel'], config)
            
            embed = discord.Embed(
                title="🎉 Verification System Active!",
                description=f"System is now live in {config['channel'].mention}",
                color=0x00ff00
            )
            
            await ctx.send(embed=embed)
            logger.info(f"Verification configured for guild {ctx.guild.id}")
            
        except Exception as e:
            del self.setup_sessions[ctx.author.id]
            await ctx.send(f"❌ Save failed: {str(e)}")
    
    async def _send_verification_message(self, channel, config):
        """Send initial verification message"""
        embed = discord.Embed(
            title="🛡️ Server Verification",
            description="Complete verification to gain access to this server!",
            color=0x0099ff
        )
        
        embed.add_field(
            name="📋 Instructions",
            value=f"**Method:** {config['verification_type'].replace('_', ' ').title()}\n**Timeout:** {config['timeout']} seconds",
            inline=False
        )
        
        embed.set_footer(text="Click 'Start Verification' to begin!")
        
        view = VerificationStartView(self, config)
        await channel.send(embed=embed, view=view)

class VerificationStartView(discord.ui.View):
    """Start verification button"""
    
    def __init__(self, cog, config):
        super().__init__(timeout=None)
        self.cog = cog
        self.config = config
    
    @discord.ui.button(label="Start Verification", style=discord.ButtonStyle.success, emoji="🛡️")
    async def start_verification(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle verification start"""
        member = interaction.user
        
        # Check if already verified
        verified_role_id = self.config['verified_role'].id
        verified_role = interaction.guild.get_role(verified_role_id)
        
        if verified_role and verified_role in member.roles:
            await interaction.response.send_message("✅ You're already verified!", ephemeral=True)
            return
        
        # Handle different verification types
        verification_type = self.config['verification_type']
        
        if verification_type == "simple_button":
            # Simple button - just give role
            try:
                await member.add_roles(verified_role, reason="Simple button verification")
                
                embed = discord.Embed(
                    title="✅ Verification Complete!",
                    description=f"Welcome to {interaction.guild.name}!",
                    color=0x00ff00
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
            except discord.Forbidden:
                await interaction.response.send_message("❌ Error assigning role. Contact admin.", ephemeral=True)
        
        else:
            # Other verification types - start captcha
            await self._start_captcha(interaction, member, verification_type)
    
    async def _start_captcha(self, interaction, member, verification_type, test_mode=False):
        """Start captcha challenge"""
        
        # Generate challenge based on type
        if verification_type == "image_captcha":
            await self._generate_image_captcha(interaction, member, test_mode)
            return
        elif verification_type == "math_captcha":
            question, answer = self._generate_math_captcha()
        elif verification_type == "text_captcha":
            question, answer = self._generate_text_captcha()
        elif verification_type == "emoji_sequence":
            question, answer = self._generate_emoji_captcha()
            
            # Special handling for emoji sequence - show for 3 seconds then hide
            embed = discord.Embed(
                title="😀 Emoji Memory Challenge",
                description=question,
                color=0xffaa00
            )
            embed.add_field(
                name="⏰ Get Ready!",
                value="The sequence will be hidden in **3 seconds**. Then you'll use buttons to recreate it!",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            await asyncio.sleep(3)
            
            # Now hide the sequence and show buttons
            hidden_embed = discord.Embed(
                title="😀 Emoji Memory Challenge",
                description="**Time to recreate the sequence!**\n\nUse the emoji buttons below to recreate the 3-emoji sequence you just saw.\n\n**Your sequence:** (empty)",
                color=0x0099ff
            )
            
            view = EmojiSequenceView(self, member, answer, self.config)
            await interaction.edit_original_response(embed=hidden_embed, view=view)
            return
            
        elif verification_type == "word_scramble":
            question, answer = self._generate_word_captcha()
        elif verification_type == "color_buttons":
            question, answer = self._generate_color_captcha()
            
            # Special handling for color buttons
            view = ColorButtonView(self, member, answer, self.config)
            
            embed = discord.Embed(
                title="🎨 Color Challenge",
                description=question,
                color=0xffaa00
            )
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            return
        
        else:
            question, answer = self._generate_math_captcha()  # Default
        
        # Store session for text-based challenges
        session_data = {
            'attempts': 0,
            'guild_id': interaction.guild.id,
            'config': self.config,
            'test_mode': test_mode,
            'max_attempts': self.config.get('max_attempts', 3)
        }
        
        # Handle different answer formats
        if isinstance(answer, list):
            session_data['answer'] = [str(a).lower() for a in answer]
        else:
            session_data['answer'] = str(answer).lower()
            
        self.verification_sessions[member.id] = session_data
        
        embed = discord.Embed(
            title="🔐 Verification Challenge",
            description=question,
            color=0xffaa00
        )
        embed.add_field(name="📝 Instructions", value="Use the form below to submit your answer!", inline=False)
        embed.set_footer(text=f"You have {self.config.get('max_attempts', 3)} attempts")
        
        # Check if config specifies UI preference
        ui_preference = self.config.get('text_captcha_ui', 'both')  # 'form', 'dropdown', or 'both'
        
        if ui_preference == 'dropdown':
            # Show dropdown immediately
            view = TextCaptchaDropdownView(self, member, session_data)
        elif ui_preference == 'form':
            # Show form button only
            view = TextCaptchaFormView(self, member, session_data)
        else:
            # Show both options (default)
            view = TextCaptchaView(self, member, session_data)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    def _generate_math_captcha(self):
        """Generate math problem"""
        a, b = random.randint(1, 20), random.randint(1, 20)
        operation = random.choice(['+', '-', '*'])
        
        if operation == '+':
            answer = a + b
            question = f"**Math Challenge:** What is {a} + {b}?"
        elif operation == '-':
            if a < b:
                a, b = b, a
            answer = a - b
            question = f"**Math Challenge:** What is {a} - {b}?"
        else:
            a, b = random.randint(1, 12), random.randint(1, 12)
            answer = a * b
            question = f"**Math Challenge:** What is {a} × {b}?"
        
        return question, str(answer)
    
    def _generate_text_captcha(self):
        """Generate enhanced text captcha with math and visual elements"""
        captcha_types = [
            "math_word", "pattern", "case_sensitive", "simple_word"
        ]
        
        captcha_type = random.choice(captcha_types)
        
        if captcha_type == "math_word":
            # Math problems in words
            problems = [
                ("What is five plus three?", "8", "eight"),
                ("What is ten minus four?", "6", "six"), 
                ("What is two times four?", "8", "eight"),
                ("What is twelve divided by three?", "4", "four"),
                ("What is seven plus two?", "9", "nine"),
                ("What is fifteen minus six?", "9", "nine")
            ]
            problem, num_answer, word_answer = random.choice(problems)
            question = f"**📝 Text Captcha Challenge**\n\n🧮 **Math Question:** {problem}\n\n💡 **Instructions:** Type your answer as a NUMBER (like `8`) or WORD (like `eight`)\n\n**Type your answer below:**"
            return question, [num_answer, word_answer]
            
        elif captcha_type == "pattern":
            # Pattern completion
            patterns = [
                ("A B C D ?", "E"),
                ("1 2 3 4 ?", "5"),
                ("red blue red blue ?", "red"),
                ("cat dog cat dog ?", "cat")
            ]
            pattern, answer = random.choice(patterns)
            question = f"**📝 Text Captcha Challenge**\n\n🔄 **Pattern:** {pattern}\n\n💡 **Instructions:** Complete the pattern by typing the missing item\n\n**Type your answer below:**"
            return question, answer.lower()
            
        elif captcha_type == "case_sensitive":
            # Case sensitive text
            words = ["Discord", "Server", "Member", "Gaming", "Verify"]
            word = random.choice(words)
            question = f"**📝 Text Captcha Challenge**\n\n🔤 **Type exactly:** `{word}`\n\n💡 **Instructions:** Copy the word exactly as shown (including capital letters)\n\n**Type your answer below:**"
            return question, word
            
        else:  # simple_word
            # Simple words to type
            words = ["welcome", "community", "friends", "gaming", "discord", "server"]
            word = random.choice(words)
            question = f"**📝 Text Captcha Challenge**\n\n✏️ **Type this word:** `{word}`\n\n💡 **Instructions:** Type the word shown above\n\n**Type your answer below:**"
            return question, word
    
    def _generate_emoji_captcha(self):
        """Generate emoji sequence for visual memory game"""
        emojis = ["🐶", "🐱", "🐭", "🐰", "🦊", "🐻", "🐼", "🐵", "🐸", "🐯", "🦁", "🐮"]
        sequence = [random.choice(emojis) for _ in range(3)]
        
        question = f"**😀 Emoji Memory Challenge**\n\n📝 **How it works:** Watch the 3 emojis below for 3 seconds, then recreate the sequence using the buttons!\n\n🧠 **Remember this sequence:**\n{' '.join(sequence)}"
        answer = sequence  # Return the actual sequence, not joined
        
        return question, answer
    
    def _generate_word_captcha(self):
        """Generate word scramble with hints"""
        word_hints = {
            "DISCORD": "A popular gaming/community chat platform",
            "SERVER": "A community space with channels and members", 
            "MEMBER": "Someone who joins a community",
            "CHANNEL": "Where conversations happen in Discord",
            "VERIFY": "What you're doing right now!",
            "PYTHON": "A programming language (and a snake 🐍)",
            "GAMING": "Playing video games together",
            "FRIEND": "Someone you enjoy chatting with",
            "CHAT": "Having a conversation online",
            "VOICE": "Talking using your microphone"
        }
        
        word = random.choice(list(word_hints.keys()))
        scrambled = ''.join(random.sample(word, len(word)))
        hint = word_hints[word]
        
        question = f"**🔤 Word Scramble Challenge**\n\n📝 **What is Word Scramble?** Unscramble the letters to form a real word!\n\n🔤 **Scrambled Letters:** `{scrambled}`\n💡 **Hint:** {hint}\n\n**Type the unscrambled word below:**"
        return question, word
    
    def _generate_color_captcha(self):
        """Generate color button challenge"""
        colors = ["🔴", "🟢", "🔵", "🟡", "🟣", "🟠"]
        correct = random.choice(colors)
        
        color_names = {"🔴": "red", "🟢": "green", "🔵": "blue", "🟡": "yellow", "🟣": "purple", "🟠": "orange"}
        
        question = f"**Color Challenge:** Click the **{color_names[correct]}** button!"
        return question, correct

    async def _generate_image_captcha(self, interaction, member, test_mode=False):
        """Generate secure image captcha using the captcha library"""
        try:
            # Create image captcha generator
            image_captcha = ImageCaptcha(width=280, height=90)
            
            # Generate random string (4-6 characters, mix of letters and numbers)
            length = random.randint(4, 6)
            captcha_text = ''.join(random.choices(
                string.ascii_uppercase + string.digits, 
                k=length
            )).replace('0', 'O').replace('1', 'I')  # Remove confusing characters
            
            # Generate image
            image_data = image_captcha.generate(captcha_text)
            
            # Convert to discord file
            image_buffer = io.BytesIO()
            image_buffer.write(image_data.getvalue())
            image_buffer.seek(0)
            
            file = discord.File(image_buffer, filename="captcha.png")
            
            # Store session data
            session_data = {
                'attempts': 0,
                'guild_id': interaction.guild.id,
                'config': self.config,
                'test_mode': test_mode,
                'max_attempts': self.config.get('max_attempts', 3),
                'answer': captcha_text.lower()
            }
            self.cog.verification_sessions[member.id] = session_data
            
            # Create embed
            embed = discord.Embed(
                title="🖼️ Image Captcha Challenge",
                description="🔒 **Bot-Proof Verification!**\n\nType the text you see in the image below. This helps us verify you're a real human!",
                color=0x0099ff
            )
            embed.add_field(
                name="📝 Instructions", 
                value="• Look at the image below\n• Type the text you see\n• Case doesn't matter\n• No spaces needed", 
                inline=False
            )
            embed.add_field(
                name="💡 Tips", 
                value="• Some characters may be slightly distorted\n• Take your time to read carefully\n• Focus on the letters and numbers", 
                inline=False
            )
            embed.set_footer(text=f"Attempts remaining: {self.config.get('max_attempts', 3)}")
            embed.set_image(url="attachment://captcha.png")
            
            await interaction.response.send_message(embed=embed, file=file, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Failed to generate image captcha: {e}")
            # Fallback to text captcha
            embed = discord.Embed(
                title="❌ Image Captcha Error",
                description="Sorry! Image captcha failed to generate. Falling back to text verification.",
                color=0xff5555
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Generate fallback text captcha
            question, answer = self._generate_text_captcha()
            session_data = {
                'attempts': 0,
                'guild_id': interaction.guild.id,
                'config': self.config,
                'test_mode': test_mode,
                'max_attempts': self.config.get('max_attempts', 3),
                'answer': answer if isinstance(answer, str) else answer[0]
            }
            self.cog.verification_sessions[member.id] = session_data
            
            fallback_embed = discord.Embed(
                title="🔐 Fallback Verification",
                description=question,
                color=0xffaa00
            )
            await interaction.followup.send(embed=fallback_embed, ephemeral=True)

class TextCaptchaView(discord.ui.View):
    """Text captcha input view with modal"""
    
    def __init__(self, cog, member, session_data):
        super().__init__(timeout=300)
        self.cog = cog
        self.member = member
        self.session_data = session_data
    
    @discord.ui.button(label="Submit Answer", style=discord.ButtonStyle.primary, emoji="📝")
    async def submit_answer(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("❌ This verification is not for you!", ephemeral=True)
            return
        
        # Show modal for text input
        modal = TextCaptchaModal(self.cog, self.member, self.session_data)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Multiple Choice", style=discord.ButtonStyle.secondary, emoji="📋")
    async def multiple_choice(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("❌ This verification is not for you!", ephemeral=True)
            return
        
        # Generate multiple choice options for certain captcha types
        correct_answers = self.session_data['answer']
        if isinstance(correct_answers, list):
            correct = correct_answers[0]
        else:
            correct = str(correct_answers)
        
        # Create multiple choice options
        options = [correct.lower()]
        
        # Add some wrong options based on the type
        if correct.isdigit():
            # Math answer - add nearby numbers
            num = int(correct)
            wrong_options = [str(num + 1), str(num - 1), str(num + 2), str(num - 2)]
        else:
            # Text answer - add similar words
            wrong_options = ["answer", "response", "solution", "result", "option"]
        
        # Add wrong options that aren't the correct answer
        for option in wrong_options:
            if option.lower() != correct.lower() and len(options) < 4:
                options.append(option.lower())
        
        # Shuffle options
        import random
        random.shuffle(options)
        
        # Create dropdown
        select_options = []
        for i, option in enumerate(options):
            select_options.append(discord.SelectOption(
                label=option.title(),
                value=option.lower(),
                description=f"Choice {i+1}"
            ))
        
        select = discord.ui.Select(
            placeholder="Choose your answer...",
            options=select_options
        )
        
        async def select_callback(select_interaction):
            if select_interaction.user.id != self.member.id:
                await select_interaction.response.send_message("❌ This verification is not for you!", ephemeral=True)
                return
            
            selected = select_interaction.data['values'][0]
            
            # Check if correct
            if isinstance(correct_answers, list):
                is_correct = selected in [str(a).lower() for a in correct_answers]
            else:
                is_correct = selected == str(correct_answers).lower()
            
            if is_correct:
                # Handle correct answer (same as modal)
                config = self.session_data['config']
                verified_role = interaction.guild.get_role(config['verified_role'].id)
                
                if verified_role:
                    try:
                        await self.member.add_roles(verified_role, reason="Verification completed")
                        
                        if self.member.id in self.cog.verification_sessions:
                            del self.cog.verification_sessions[self.member.id]
                        
                        embed = discord.Embed(
                            title="✅ Verification Successful!",
                            description=f"Welcome to **{interaction.guild.name}**! You've been verified and given the {verified_role.mention} role.",
                            color=0x00ff00
                        )
                        embed.add_field(name="🎉 What's Next?", value="You now have access to all server channels and features!", inline=False)
                        
                        await select_interaction.response.edit_message(embed=embed, view=None)
                        
                    except discord.Forbidden:
                        embed = discord.Embed(
                            title="❌ Role Assignment Failed",
                            description="I don't have permission to assign roles. Please contact an administrator.",
                            color=0xff5555
                        )
                        await select_interaction.response.edit_message(embed=embed, view=None)
                else:
                    embed = discord.Embed(
                        title="❌ Role Not Found",
                        description="The verification role was deleted. Please contact an administrator.",
                        color=0xff5555
                    )
                    await select_interaction.response.edit_message(embed=embed, view=None)
            else:
                # Handle wrong answer (same as modal)
                self.session_data['attempts'] += 1
                max_attempts = self.session_data.get('max_attempts', 3)
                
                if self.session_data['attempts'] >= max_attempts:
                    if self.member.id in self.cog.verification_sessions:
                        del self.cog.verification_sessions[self.member.id]
                    
                    embed = discord.Embed(
                        title="❌ Verification Failed",
                        description=f"You've used all {max_attempts} attempts. Please try again later or contact an administrator.",
                        color=0xff5555
                    )
                    await select_interaction.response.edit_message(embed=embed, view=None)
                else:
                    remaining = max_attempts - self.session_data['attempts']
                    embed = discord.Embed(
                        title="❌ Incorrect Answer",
                        description=f"That's not correct. You have **{remaining}** attempts remaining.",
                        color=0xff9900
                    )
                    embed.add_field(name="💡 Tip", value="Try the text input option for more flexibility!", inline=False)
                    
                    view = TextCaptchaView(self.cog, self.member, self.session_data)
                    await select_interaction.response.edit_message(embed=embed, view=view)
        
        select.callback = select_callback
        
        # Create new view with dropdown
        dropdown_view = discord.ui.View(timeout=300)
        dropdown_view.add_item(select)
        
        # Add back button
        back_button = discord.ui.Button(label="Back to Text Input", style=discord.ButtonStyle.secondary, emoji="⬅️")
        
        async def back_callback(back_interaction):
            if back_interaction.user.id != self.member.id:
                await back_interaction.response.send_message("❌ This verification is not for you!", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="🔐 Verification Challenge",
                description="Choose how you'd like to submit your answer:",
                color=0xffaa00
            )
            embed.add_field(name="📝 Instructions", value="Use the form below to submit your answer!", inline=False)
            
            view = TextCaptchaView(self.cog, self.member, self.session_data)
            await back_interaction.response.edit_message(embed=embed, view=view)
        
        back_button.callback = back_callback
        dropdown_view.add_item(back_button)
        
        embed = discord.Embed(
            title="📋 Multiple Choice",
            description="Select your answer from the dropdown below:",
            color=0x0099ff
        )
        embed.add_field(name="💡 Tip", value="If none of these look right, use the 'Back to Text Input' button!", inline=False)
        
        await interaction.response.edit_message(embed=embed, view=dropdown_view)

class TextCaptchaFormView(discord.ui.View):
    """Form-only text captcha view"""
    
    def __init__(self, cog, member, session_data):
        super().__init__(timeout=300)
        self.cog = cog
        self.member = member
        self.session_data = session_data
    
    @discord.ui.button(label="Submit Answer", style=discord.ButtonStyle.primary, emoji="📝")
    async def submit_answer(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("❌ This verification is not for you!", ephemeral=True)
            return
        
        modal = TextCaptchaModal(self.cog, self.member, self.session_data)
        await interaction.response.send_modal(modal)

class TextCaptchaDropdownView(discord.ui.View):
    """Dropdown-only text captcha view"""
    
    def __init__(self, cog, member, session_data):
        super().__init__(timeout=300)
        self.cog = cog
        self.member = member
        self.session_data = session_data
        
        # Generate dropdown immediately
        self._create_dropdown()
    
    def _create_dropdown(self):
        """Create the dropdown with answer options"""
        correct_answers = self.session_data['answer']
        if isinstance(correct_answers, list):
            correct = correct_answers[0]
        else:
            correct = str(correct_answers)
        
        # Create multiple choice options
        options = [correct.lower()]
        
        # Add wrong options based on the type
        if correct.isdigit():
            # Math answer - add nearby numbers
            num = int(correct)
            wrong_options = [str(num + 1), str(num - 1), str(num + 2), str(num - 2)]
        else:
            # Text answer - add similar words
            if len(correct) <= 3:
                wrong_options = ["yes", "no", "ok", "hi", "bye"]
            else:
                wrong_options = ["answer", "response", "solution", "result", "option"]
        
        # Add wrong options that aren't the correct answer
        for option in wrong_options:
            if option.lower() != correct.lower() and len(options) < 4:
                options.append(option.lower())
        
        # Shuffle options
        import random
        random.shuffle(options)
        
        # Create dropdown
        select_options = []
        for i, option in enumerate(options):
            select_options.append(discord.SelectOption(
                label=option.title(),
                value=option.lower(),
                description=f"Choice {i+1}"
            ))
        
        select = discord.ui.Select(
            placeholder="Choose your answer...",
            options=select_options,
            min_values=1,
            max_values=1
        )
        
        # Create a proper callback function
        async def dropdown_callback(select_interaction):
            await self._dropdown_callback(select_interaction)
        
        select.callback = dropdown_callback
        self.add_item(select)
    
    async def _dropdown_callback(self, interaction: discord.Interaction):
        """Handle dropdown selection"""
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("❌ This verification is not for you!", ephemeral=True)
            return
        
        try:
            selected = interaction.data['values'][0]
            correct_answers = self.session_data['answer']
            
            # Check if correct
            if isinstance(correct_answers, list):
                is_correct = selected in [str(a).lower() for a in correct_answers]
            else:
                is_correct = selected == str(correct_answers).lower()
        except (KeyError, IndexError) as e:
            await interaction.response.send_message("❌ Error processing your selection. Please try again.", ephemeral=True)
            return
        
        if is_correct:
            # Handle correct answer
            config = self.session_data['config']
            verified_role = interaction.guild.get_role(config['verified_role'].id)
            
            if verified_role:
                try:
                    await self.member.add_roles(verified_role, reason="Verification completed")
                    
                    if self.member.id in self.cog.verification_sessions:
                        del self.cog.verification_sessions[self.member.id]
                    
                    embed = discord.Embed(
                        title="✅ Verification Successful!",
                        description=f"Welcome to **{interaction.guild.name}**! You've been verified and given the {verified_role.mention} role.",
                        color=0x00ff00
                    )
                    embed.add_field(name="🎉 What's Next?", value="You now have access to all server channels and features!", inline=False)
                    
                    await interaction.response.edit_message(embed=embed, view=None)
                    
                except discord.Forbidden:
                    embed = discord.Embed(
                        title="❌ Role Assignment Failed",
                        description="I don't have permission to assign roles. Please contact an administrator.",
                        color=0xff5555
                    )
                    await interaction.response.edit_message(embed=embed, view=None)
            else:
                embed = discord.Embed(
                    title="❌ Role Not Found",
                    description="The verification role was deleted. Please contact an administrator.",
                    color=0xff5555
                )
                await interaction.response.edit_message(embed=embed, view=None)
        else:
            # Handle wrong answer
            self.session_data['attempts'] += 1
            max_attempts = self.session_data.get('max_attempts', 3)
            
            if self.session_data['attempts'] >= max_attempts:
                if self.member.id in self.cog.verification_sessions:
                    del self.cog.verification_sessions[self.member.id]
                
                embed = discord.Embed(
                    title="❌ Verification Failed",
                    description=f"You've used all {max_attempts} attempts. Please try again later or contact an administrator.",
                    color=0xff5555
                )
                await interaction.response.edit_message(embed=embed, view=None)
            else:
                remaining = max_attempts - self.session_data['attempts']
                embed = discord.Embed(
                    title="❌ Incorrect Answer",
                    description=f"That's not correct. You have **{remaining}** attempts remaining.",
                    color=0xff9900
                )
                embed.add_field(name="💡 Tip", value="Look carefully at the options and try again!", inline=False)
                
                # Create new dropdown with remaining attempts
                view = TextCaptchaDropdownView(self.cog, self.member, self.session_data)
                await interaction.response.edit_message(embed=embed, view=view)

class TextCaptchaModal(discord.ui.Modal):
    """Modal for text captcha input"""
    
    def __init__(self, cog, member, session_data):
        super().__init__(title="🔐 Submit Your Answer")
        self.cog = cog
        self.member = member
        self.session_data = session_data
        
        # Add text input
        self.answer_input = discord.ui.TextInput(
            label="Your Answer",
            placeholder="Type your answer here...",
            max_length=100,
            required=True
        )
        self.add_item(self.answer_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        user_answer = self.answer_input.value.strip()
        
        # Check answer
        correct_answers = self.session_data['answer']
        if isinstance(correct_answers, list):
            is_correct = user_answer.lower() in [str(a).lower() for a in correct_answers]
        else:
            is_correct = user_answer.lower() == str(correct_answers).lower()
        
        if is_correct:
            # Correct answer!
            config = self.session_data['config']
            verified_role = interaction.guild.get_role(config['verified_role'].id)
            
            if verified_role:
                try:
                    await self.member.add_roles(verified_role, reason="Verification completed")
                    
                    # Remove from verification sessions
                    if self.member.id in self.cog.verification_sessions:
                        del self.cog.verification_sessions[self.member.id]
                    
                    # Success message
                    embed = discord.Embed(
                        title="✅ Verification Successful!",
                        description=f"Welcome to **{interaction.guild.name}**! You've been verified and given the {verified_role.mention} role.",
                        color=0x00ff00
                    )
                    embed.add_field(name="🎉 What's Next?", value="You now have access to all server channels and features!", inline=False)
                    
                    await interaction.response.edit_message(embed=embed, view=None)
                    
                    # Log verification
                    if not self.session_data.get('test_mode', False):
                        await self.cog.db.execute(
                            "INSERT INTO verification_logs (guild_id, user_id, verification_type, success, timestamp) VALUES (?, ?, ?, ?, ?)",
                            (interaction.guild.id, self.member.id, "text_captcha", True, discord.utils.utcnow().isoformat())
                        )
                        await self.cog.db.commit()
                    
                except discord.Forbidden:
                    embed = discord.Embed(
                        title="❌ Role Assignment Failed",
                        description="I don't have permission to assign roles. Please contact an administrator.",
                        color=0xff5555
                    )
                    await interaction.response.edit_message(embed=embed, view=None)
            else:
                embed = discord.Embed(
                    title="❌ Role Not Found",
                    description="The verification role was deleted. Please contact an administrator.",
                    color=0xff5555
                )
                await interaction.response.edit_message(embed=embed, view=None)
        else:
            # Wrong answer
            self.session_data['attempts'] += 1
            max_attempts = self.session_data.get('max_attempts', 3)
            
            if self.session_data['attempts'] >= max_attempts:
                # Max attempts reached
                if self.member.id in self.cog.verification_sessions:
                    del self.cog.verification_sessions[self.member.id]
                
                embed = discord.Embed(
                    title="❌ Verification Failed",
                    description=f"You've used all {max_attempts} attempts. Please try again later or contact an administrator.",
                    color=0xff5555
                )
                await interaction.response.edit_message(embed=embed, view=None)
                
                # Log failed verification
                if not self.session_data.get('test_mode', False):
                    await self.cog.db.execute(
                        "INSERT INTO verification_logs (guild_id, user_id, verification_type, success, timestamp) VALUES (?, ?, ?, ?, ?)",
                        (interaction.guild.id, self.member.id, "text_captcha", False, discord.utils.utcnow().isoformat())
                    )
                    await self.cog.db.commit()
            else:
                # Show retry message
                remaining = max_attempts - self.session_data['attempts']
                embed = discord.Embed(
                    title="❌ Incorrect Answer",
                    description=f"That's not correct. You have **{remaining}** attempts remaining.",
                    color=0xff9900
                )
                embed.add_field(name="💡 Tip", value="Double-check your spelling and try again!", inline=False)
                
                # Create new view for retry
                view = TextCaptchaView(self.cog, self.member, self.session_data)
                await interaction.response.edit_message(embed=embed, view=view)

class ColorButtonView(discord.ui.View):
    """Color button verification"""
    
    def __init__(self, cog, member, correct_color, config):
        super().__init__(timeout=60)
        self.cog = cog
        self.member = member
        self.correct_color = correct_color
        self.config = config
        
        colors = ["🔴", "🟢", "🔵", "🟡", "🟣", "🟠"]
        for color in colors:
            button = discord.ui.Button(emoji=color, style=discord.ButtonStyle.secondary)
            button.callback = self.create_callback(color)
            self.add_item(button)
    
    def create_callback(self, color):
        async def callback(interaction):
            if interaction.user.id != self.member.id:
                await interaction.response.send_message("❌ Not for you!", ephemeral=True)
                return
            
            if color == self.correct_color:
                # Correct color!
                verified_role = interaction.guild.get_role(self.config['verified_role'].id)
                
                try:
                    await self.member.add_roles(verified_role, reason="Color button verification")
                    
                    embed = discord.Embed(
                        title="✅ Verification Complete!",
                        description=f"Welcome to {interaction.guild.name}!",
                        color=0x00ff00
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    
                except discord.Forbidden:
                    await interaction.response.send_message("❌ Error assigning role.", ephemeral=True)
            else:
                # Wrong color
                embed = discord.Embed(
                    title="❌ Wrong Color!",
                    description="Try again!",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
        
        return callback

class EmojiSequenceView(discord.ui.View):
    """Emoji sequence memory game"""
    
    def __init__(self, cog, member, correct_sequence, config, show_sequence=True):
        super().__init__(timeout=120)  # 2 minutes to complete
        self.cog = cog
        self.member = member
        self.correct_sequence = correct_sequence
        self.config = config
        self.user_sequence = []
        self.show_sequence = show_sequence
        
        # Available emojis
        emojis = ["🐶", "🐱", "🐭", "🐰", "🦊", "🐻", "🐼", "🐵", "🐸", "🐯", "🦁", "🐮"]
        
        # Add emoji buttons (3 rows of 4)
        for i, emoji in enumerate(emojis):
            button = discord.ui.Button(emoji=emoji, style=discord.ButtonStyle.secondary, row=i//4)
            button.callback = self.create_emoji_callback(emoji)
            self.add_item(button)
        
        # Add Clear and Submit buttons on last row
        clear_button = discord.ui.Button(label="Clear", style=discord.ButtonStyle.danger, emoji="🗑️", row=3)
        clear_button.callback = self.clear_sequence
        self.add_item(clear_button)
        
        submit_button = discord.ui.Button(label="Submit", style=discord.ButtonStyle.success, emoji="✅", row=3)
        submit_button.callback = self.submit_sequence
        self.add_item(submit_button)
    
    def create_emoji_callback(self, emoji):
        async def callback(interaction):
            if interaction.user.id != self.member.id:
                await interaction.response.send_message("❌ Not for you!", ephemeral=True)
                return
            
            if len(self.user_sequence) >= 3:
                await interaction.response.send_message("❌ You can only select 3 emojis! Use Clear to reset.", ephemeral=True)
                return
            
            self.user_sequence.append(emoji)
            
            embed = discord.Embed(
                title="😀 Emoji Memory Challenge",
                description=f"**Your sequence so far:** {' '.join(self.user_sequence)}\n\n**Target length:** 3 emojis\n**Remaining:** {3 - len(self.user_sequence)} emojis",
                color=0x0099ff
            )
            
            if len(self.user_sequence) == 3:
                embed.add_field(
                    name="✅ Ready to Submit!",
                    value="Click **Submit** when you're ready, or **Clear** to start over.",
                    inline=False
                )
            
            await interaction.response.edit_message(embed=embed, view=self)
        
        return callback
    
    async def clear_sequence(self, interaction):
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("❌ Not for you!", ephemeral=True)
            return
        
        self.user_sequence = []
        
        embed = discord.Embed(
            title="😀 Emoji Memory Challenge",
            description="**Your sequence:** (empty)\n\n**Target length:** 3 emojis\nSelect emojis using the buttons below!",
            color=0x0099ff
        )
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def submit_sequence(self, interaction):
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("❌ Not for you!", ephemeral=True)
            return
        
        if len(self.user_sequence) != 3:
            await interaction.response.send_message(f"❌ You need exactly 3 emojis! You have {len(self.user_sequence)}.", ephemeral=True)
            return
        
        # Check if sequence matches
        if self.user_sequence == self.correct_sequence:
            # Correct sequence!
            session = self.cog.verification_sessions.get(self.member.id, {})
            test_mode = session.get('test_mode', False)
            
            if test_mode:
                embed = discord.Embed(
                    title="🧪 Test Complete!",
                    description="**Test successful!** ✅\n\nEmoji memory challenge completed correctly!",
                    color=0x00ff00
                )
                await interaction.response.edit_message(embed=embed, view=None)
                
                if self.member.id in self.cog.verification_sessions:
                    del self.cog.verification_sessions[self.member.id]
                return
            
            # Normal verification
            verified_role = interaction.guild.get_role(self.config['verified_role'].id)
            
            try:
                await self.member.add_roles(verified_role, reason="Emoji sequence verification")
                
                embed = discord.Embed(
                    title="✅ Verification Complete!",
                    description=f"Perfect memory! Welcome to {interaction.guild.name}! 🎉",
                    color=0x00ff00
                )
                await interaction.response.edit_message(embed=embed, view=None)
                
                if self.member.id in self.cog.verification_sessions:
                    del self.cog.verification_sessions[self.member.id]
                
            except discord.Forbidden:
                await interaction.response.send_message("❌ Error assigning role.", ephemeral=True)
        else:
            # Wrong sequence
            session = self.cog.verification_sessions[self.member.id]
            session['attempts'] += 1
            max_attempts = session['max_attempts']
            
            if session['attempts'] >= max_attempts:
                # Failed
                embed = discord.Embed(
                    title="❌ Verification Failed",
                    description="Too many incorrect attempts. Please try again later.",
                    color=0xff0000
                )
                await interaction.response.edit_message(embed=embed, view=None)
                
                if self.member.id in self.cog.verification_sessions:
                    del self.cog.verification_sessions[self.member.id]
            else:
                # Try again
                remaining = max_attempts - session['attempts']
                self.user_sequence = []  # Reset for next attempt
                
                embed = discord.Embed(
                    title="❌ Wrong Sequence!",
                    description=f"**Correct sequence was:** {' '.join(self.correct_sequence)}\n\n**Attempts remaining:** {remaining}\n\nTry again!",
                    color=0xffaa00
                )
                
                await interaction.response.edit_message(embed=embed, view=self)

    # ================================
    # EVENT LISTENERS & TEXT VERIFICATION
    # ================================
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Auto-prompt new members to verify"""
        if member.bot:
            return
            
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT verification_channel_id FROM verification_config WHERE guild_id = ?', (member.guild.id,))
        config = cursor.fetchone()
        conn.close()
        
        if not config:
            return
            
        channel = member.guild.get_channel(config[0])
        if not channel:
            return
            
        # Send welcome DM
        try:
            embed = discord.Embed(
                title=f"Welcome to {member.guild.name}! 🎉",
                description=f"Please complete verification in {channel.mention} to gain access.",
                color=0x0099ff
            )
            await member.send(embed=embed)
        except:
            pass  # DMs disabled
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle text verification responses"""
        if message.author.bot:
            return
            
        if message.author.id not in self.verification_sessions:
            return
            
        session = self.verification_sessions[message.author.id]
        
        if message.guild.id != session['guild_id']:
            return
            
        user_answer = message.content.strip().lower()
        correct_answers = session['answer']
        
        try:
            await message.delete()  # Clean up
        except:
            pass
        
        # Check if answer is correct
        is_correct = False
        if isinstance(correct_answers, list):
            # Multiple valid answers (like math_word captcha)
            is_correct = user_answer in correct_answers
        else:
            # Single answer
            is_correct = user_answer == correct_answers
        
        if is_correct:
            # Correct!
            await self._complete_text_verification(message.author, message.guild, session)
            del self.verification_sessions[message.author.id]
        else:
            # Wrong answer
            session['attempts'] += 1
            max_attempts = session.get('max_attempts', 3)
            
            if session['attempts'] >= max_attempts:
                # Failed
                del self.verification_sessions[message.author.id]
                
                embed = discord.Embed(
                    title="❌ Verification Failed",
                    description=f"Too many incorrect attempts. Please try again later.",
                    color=0xff0000
                )
                
                try:
                    await message.author.send(embed=embed)
                except:
                    await message.channel.send(f"{message.author.mention}", embed=embed, delete_after=15)
            else:
                # Try again
                remaining = max_attempts - session['attempts']
                
                embed = discord.Embed(
                    title="❌ Incorrect Answer",
                    description=f"Wrong! You have {remaining} attempt(s) remaining.",
                    color=0xffaa00
                )
                
                try:
                    await message.author.send(embed=embed)
                except:
                    await message.channel.send(f"{message.author.mention}", embed=embed, delete_after=10)
    
    async def _complete_text_verification(self, member, guild, session):
        """Complete text-based verification"""
        test_mode = session.get('test_mode', False)
        config = session.get('config', {})
        
        if test_mode:
            # Test mode completion - no role assignment
            embed = discord.Embed(
                title="🧪 Test Complete!",
                description="**Test successful!** ✅\n\nThis was a test run. In real verification, users would get the verified role and access to your server.",
                color=0x00ff00
            )
            
            embed.add_field(
                name="✨ Test Results",
                value="• Verification method works correctly\n• Users would receive the verified role\n• Welcome message would be sent",
                inline=False
            )
            
            try:
                await member.send(embed=embed)
            except:
                pass
                
            logger.info(f"Test verification completed by {member.id} in guild {guild.id}")
            return
        
        # Normal verification - assign role
        verified_role_data = config.get('verified_role')
        if not verified_role_data:
            return
            
        # Handle both role objects and role IDs
        if hasattr(verified_role_data, 'id'):
            verified_role = guild.get_role(verified_role_data.id)
        else:
            verified_role = guild.get_role(verified_role_data)
        
        if not verified_role:
            return
            
        try:
            await member.add_roles(verified_role, reason="Text verification completed")
            
            embed = discord.Embed(
                title="✅ Verification Complete!",
                description=f"Welcome to {guild.name}! You now have access to the server.",
                color=0x00ff00
            )
            
            try:
                await member.send(embed=embed)
            except:
                pass
                
            logger.info(f"User {member.id} completed text verification in guild {guild.id}")
            
        except discord.Forbidden:
            logger.error(f"Cannot assign verified role to {member.id}")

    # ================================
    # VERIFICATION MANAGEMENT COMMANDS
    # ================================
    
    @commands.hybrid_command(name="verification-info", description="📊 Show verification system info (Admin+)")
    @has_permission("admin")
    async def verification_info(self, ctx):
        """Display verification system information"""
        
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM verification_config WHERE guild_id = ?', (ctx.guild.id,))
            config = cursor.fetchone()
            conn.close()
            
            if not config:
                embed = discord.Embed(
                    title="❌ No Verification System",
                    description="No verification system configured for this server.",
                    color=0xff0000
                )
                embed.add_field(
                    name="🚀 Get Started",
                    value="Use `/setup-verification` to create your verification system!",
                    inline=False
                )
                await ctx.send(embed=embed)
                return
        except Exception as e:
            await ctx.send(f"❌ Database error: {str(e)}")
            return
        
        # Get channel and role
        channel = ctx.guild.get_channel(config[1]) if config[1] else None
        role = ctx.guild.get_role(config[2]) if config[2] else None
        
        embed = discord.Embed(
            title="🛡️ Verification System Information",
            description="Current configuration:",
            color=0x0099ff
        )
        
        embed.add_field(
            name="📍 Channel", 
            value=channel.mention if channel else "❌ Not found", 
            inline=True
        )
        embed.add_field(
            name="👤 Verified Role", 
            value=role.mention if role else "❌ Not found", 
            inline=True
        )
        embed.add_field(
            name="🎯 Method", 
            value=config[3].replace('_', ' ').title(), 
            inline=True
        )
        embed.add_field(
            name="⏰ Timeout", 
            value=f"{config[4]} seconds", 
            inline=True
        )
        embed.add_field(
            name="🎯 Max Attempts", 
            value=f"{config[5]} attempts", 
            inline=True
        )
        
        # Show text UI preference if available
        if len(config) > 6 and config[6]:
            ui_display = {"form": "📝 Form Only", "dropdown": "📋 Dropdown Only", "both": "🎯 Both Options"}
            embed.add_field(
                name="📱 Text UI",
                value=ui_display.get(config[6], "🎯 Both Options"),
                inline=True
            )
        
        # Statistics
        if role:
            verified_count = len(role.members)
            total_members = len([m for m in ctx.guild.members if not m.bot])
            rate = (verified_count / total_members * 100) if total_members > 0 else 0
            
            embed.add_field(
                name="📊 Statistics",
                value=f"**Verified:** {verified_count}/{total_members}\n**Rate:** {rate:.1f}%",
                inline=False
            )
        
        embed.set_footer(text="Use /setup-verification to modify settings")
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="manual-verify", description="✅ Manually verify a user (Admin+)")
    @has_permission("admin")
    async def manual_verify(self, ctx, member: discord.Member):
        """Manually verify a user"""
        
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT verified_role_id FROM verification_config WHERE guild_id = ?', (ctx.guild.id,))
            config = cursor.fetchone()
            conn.close()
            
            if not config or not config[0]:
                await ctx.send("❌ Verification system not configured!")
                return
        except Exception as e:
            await ctx.send(f"❌ Database error: {str(e)}")
            return
        
        verified_role = ctx.guild.get_role(config[0])
        if not verified_role:
            await ctx.send("❌ Verified role not found!")
            return
        
        if verified_role in member.roles:
            await ctx.send(f"✅ {member.mention} is already verified!")
            return
        
        try:
            await member.add_roles(verified_role, reason=f"Manual verification by {ctx.author}")
            
            embed = discord.Embed(
                title="✅ Manual Verification Complete",
                description=f"{member.mention} has been manually verified!",
                color=0x00ff00
            )
            
            await ctx.send(embed=embed)
            
            # Notify user
            try:
                user_embed = discord.Embed(
                    title="✅ You've Been Verified!",
                    description=f"An admin has verified you in **{ctx.guild.name}**!",
                    color=0x00ff00
                )
                await member.send(embed=user_embed)
            except:
                pass
            
            logger.info(f"Manual verification: {member.id} by {ctx.author.id} in {ctx.guild.id}")
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to assign the verified role!")
    
    @commands.hybrid_command(name="reset-verification", description="🔄 Reset user verification (Admin+)")
    @has_permission("admin")
    async def reset_verification(self, ctx, member: discord.Member):
        """Reset a user's verification status"""
        
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT verified_role_id FROM verification_config WHERE guild_id = ?', (ctx.guild.id,))
            config = cursor.fetchone()
            conn.close()
            
            if not config or not config[0]:
                await ctx.send("❌ Verification system not configured!")
                return
        except Exception as e:
            await ctx.send(f"❌ Database error: {str(e)}")
            return
        
        verified_role = ctx.guild.get_role(config[0])
        if not verified_role:
            await ctx.send("❌ Verified role not found!")
            return
        
        # Remove active session
        if member.id in self.verification_sessions:
            del self.verification_sessions[member.id]
        
        # Remove role if they have it
        if verified_role in member.roles:
            try:
                await member.remove_roles(verified_role, reason=f"Verification reset by {ctx.author}")
                
                embed = discord.Embed(
                    title="🔄 Verification Reset",
                    description=f"{member.mention}'s verification has been reset.",
                    color=0xffaa00
                )
                
                await ctx.send(embed=embed)
                logger.info(f"Verification reset: {member.id} by {ctx.author.id}")
                
            except discord.Forbidden:
                await ctx.send("❌ I don't have permission to remove the verified role!")
        else:
            await ctx.send(f"✅ {member.mention} was not verified.")
    
    @commands.hybrid_command(name="verification-stats", description="📊 Show verification statistics (Admin+)")
    @has_permission("admin")
    async def verification_stats(self, ctx):
        """Show detailed verification statistics"""
        
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT verified_role_id FROM verification_config WHERE guild_id = ?', (ctx.guild.id,))
            config = cursor.fetchone()
            conn.close()
            
            if not config or not config[0]:
                await ctx.send("❌ Verification system not configured!")
                return
        except Exception as e:
            await ctx.send(f"❌ Database error: {str(e)}")
            return
        
        verified_role = ctx.guild.get_role(config[0])
        if not verified_role:
            await ctx.send("❌ Verified role not found!")
            return
        
        # Calculate statistics
        verified_members = verified_role.members
        all_members = [m for m in ctx.guild.members if not m.bot]
        unverified_members = [m for m in all_members if verified_role not in m.roles]
        
        verified_count = len(verified_members)
        total_count = len(all_members)
        unverified_count = len(unverified_members)
        
        embed = discord.Embed(
            title="📊 Verification Statistics",
            description=f"Server verification overview for **{ctx.guild.name}**",
            color=0x0099ff
        )
        
        embed.add_field(name="✅ Verified", value=str(verified_count), inline=True)
        embed.add_field(name="❌ Unverified", value=str(unverified_count), inline=True)
        embed.add_field(name="👥 Total", value=str(total_count), inline=True)
        
        if total_count > 0:
            rate = (verified_count / total_count) * 100
            embed.add_field(name="📈 Verification Rate", value=f"{rate:.1f}%", inline=False)
        
        # Active sessions
        active_sessions = len([s for s in self.verification_sessions.values() if s['guild_id'] == ctx.guild.id])
        embed.add_field(name="⏳ Active Sessions", value=str(active_sessions), inline=True)
        
        embed.set_footer(text="Use /manual-verify to verify users manually")
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="test-verification", description="🧪 Test verification system (Admin+)")
    @has_permission("admin")
    async def test_verification(self, ctx):
        """Test the verification system without getting the role"""
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM verification_config WHERE guild_id = ?', (ctx.guild.id,))
        config = cursor.fetchone()
        conn.close()
        
        if not config:
            await ctx.send("❌ Verification system not configured! Use `/setup-verification` first.")
            return
        
        channel = ctx.guild.get_channel(config[1])
        if not channel:
            await ctx.send("❌ Verification channel not found!")
            return
        
        embed = discord.Embed(
            title="🧪 Testing Verification System",
            description=f"**Test Mode Activated!**\n\nI'll simulate the verification process for you without actually giving you the role.",
            color=0xffaa00
        )
        
        embed.add_field(
            name="📍 Test Channel",
            value=channel.mention,
            inline=True
        )
        
        embed.add_field(
            name="🎯 Method",
            value=config[3].replace('_', ' ').title(),
            inline=True
        )
        
        embed.add_field(
            name="⏰ Timeout",
            value=f"{config[4]} seconds",
            inline=True
        )
        
        embed.add_field(
            name="🔬 What's Different?",
            value="• You won't get the verified role\n• Perfect for testing without side effects\n• Same exact experience as real users",
            inline=False
        )
        
        embed.set_footer(text="Click 'Start Test' to begin the verification process")
        
        view = TestVerificationView(self, ctx.author, config)
        await ctx.send(embed=embed, view=view)
    
    @commands.hybrid_command(name="disable-verification", description="🚫 Temporarily disable verification system (Admin+)")
    @has_permission("admin")
    async def disable_verification(self, ctx):
        """Temporarily disable the verification system"""
        
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Check if verification exists
            cursor.execute('SELECT channel_id FROM verification_config WHERE guild_id = ?', (ctx.guild.id,))
            config = cursor.fetchone()
            
            if not config:
                conn.close()
                await ctx.send("❌ No verification system configured!")
                return
            
            # Update config to mark as disabled
            cursor.execute('''
                UPDATE verification_config 
                SET channel_id = NULL 
                WHERE guild_id = ?
            ''', (ctx.guild.id,))
            conn.commit()
            conn.close()
            
            embed = discord.Embed(
                title="🚫 Verification Disabled",
                description="The verification system has been temporarily disabled.",
                color=0xff9900
            )
            
            embed.add_field(
                name="✅ To Re-enable",
                value="Use `/enable-verification` or run `/setup-verification` again",
                inline=False
            )
            
            await ctx.send(embed=embed)
            logger.info(f"Verification disabled by {ctx.author.id} in {ctx.guild.id}")
            
        except Exception as e:
            await ctx.send(f"❌ Database error: {str(e)}")
    
    @commands.hybrid_command(name="enable-verification", description="✅ Re-enable verification system (Admin+)")
    @has_permission("admin")
    async def enable_verification(self, ctx):
        """Re-enable a previously configured verification system"""
        
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Check for disabled verification (channel_id is NULL but other config exists)
            cursor.execute('''
                SELECT verified_role_id, verification_type, timeout, max_attempts 
                FROM verification_config 
                WHERE guild_id = ? AND channel_id IS NULL
            ''', (ctx.guild.id,))
            config = cursor.fetchone()
            
            if not config:
                conn.close()
                embed = discord.Embed(
                    title="❌ No Disabled System Found",
                    description="No previously configured verification system found to re-enable.",
                    color=0xff0000
                )
                embed.add_field(
                    name="🚀 Get Started",
                    value="Use `/setup-verification` to create a new verification system!",
                    inline=False
                )
                await ctx.send(embed=embed)
                return
            
            # Ask user to select channel
            channels = [ch for ch in ctx.guild.text_channels if ch.permissions_for(ctx.guild.me).send_messages]
            
            if not channels:
                conn.close()
                await ctx.send("❌ No suitable channels found!")
                return
            
            embed = discord.Embed(
                title="📍 Select Verification Channel",
                description="Choose a channel to re-enable verification:",
                color=0x0099ff
            )
            
            channel_list = ""
            for i, ch in enumerate(channels[:10]):
                channel_list += f"`{i+1}.` {ch.mention}\n"
            
            embed.add_field(name="Available Channels", value=channel_list, inline=False)
            embed.set_footer(text="Reply with the channel number (1-10)")
            
            await ctx.send(embed=embed)
            
            def check(m):
                return (m.author == ctx.author and m.channel == ctx.channel and 
                       m.content.strip().isdigit() and 1 <= int(m.content.strip()) <= len(channels))
            
            try:
                choice = await self.bot.wait_for('message', timeout=60.0, check=check)
                selected_channel = channels[int(choice.content.strip()) - 1]
                
                # Update database with selected channel
                cursor.execute('''
                    UPDATE verification_config 
                    SET channel_id = ? 
                    WHERE guild_id = ?
                ''', (selected_channel.id, ctx.guild.id))
                conn.commit()
                conn.close()
                
                embed = discord.Embed(
                    title="✅ Verification Re-enabled",
                    description=f"Verification system has been re-enabled in {selected_channel.mention}!",
                    color=0x00ff00
                )
                
                await ctx.send(embed=embed)
                logger.info(f"Verification re-enabled by {ctx.author.id} in {ctx.guild.id}")
                
            except asyncio.TimeoutError:
                conn.close()
                await ctx.send("⏰ Channel selection timed out.")
                
        except Exception as e:
            await ctx.send(f"❌ Database error: {str(e)}")
    
    @commands.hybrid_command(name="verification-logs", description="📋 View recent verification activity (Admin+)")
    @has_permission("admin")
    async def verification_logs(self, ctx, limit: int = 10):
        """View recent verification activity"""
        
        if limit > 50:
            limit = 50
        elif limit < 1:
            limit = 10
        
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Check if verification system exists
            cursor.execute('SELECT verified_role_id FROM verification_config WHERE guild_id = ?', (ctx.guild.id,))
            config = cursor.fetchone()
            
            if not config:
                conn.close()
                await ctx.send("❌ No verification system configured!")
                return
            
            verified_role = ctx.guild.get_role(config[0])
            if not verified_role:
                conn.close()
                await ctx.send("❌ Verified role not found!")
                return
            
            # Get recent verified members (those with the role)
            verified_members = []
            for member in verified_role.members:
                if not member.bot:
                    # Try to get join date
                    join_date = member.joined_at
                    verified_members.append((member, join_date))
            
            # Sort by join date (most recent first)
            verified_members.sort(key=lambda x: x[1] if x[1] else discord.utils.utcnow(), reverse=True)
            verified_members = verified_members[:limit]
            
            if not verified_members:
                embed = discord.Embed(
                    title="📋 Verification Logs",
                    description="No verified members found.",
                    color=0xff9900
                )
                await ctx.send(embed=embed)
                return
            
            embed = discord.Embed(
                title="📋 Recent Verification Activity",
                description=f"Showing last {len(verified_members)} verified members:",
                color=0x0099ff
            )
            
            log_text = ""
            for i, (member, join_date) in enumerate(verified_members, 1):
                join_str = f"<t:{int(join_date.timestamp())}:R>" if join_date else "Unknown"
                log_text += f"`{i}.` {member.mention} - Joined {join_str}\n"
            
            embed.add_field(name="Verified Members", value=log_text, inline=False)
            embed.set_footer(text=f"Total verified: {len(verified_role.members)}")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error retrieving logs: {str(e)}")
    
    @commands.hybrid_command(name="bulk-verify", description="👥 Bulk verify users by role (Admin+)")
    @has_permission("admin")
    async def bulk_verify(self, ctx, role: discord.Role = None):
        """Bulk verify all members with a specific role"""
        
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT verified_role_id FROM verification_config WHERE guild_id = ?', (ctx.guild.id,))
            config = cursor.fetchone()
            conn.close()
            
            if not config or not config[0]:
                await ctx.send("❌ Verification system not configured!")
                return
        except Exception as e:
            await ctx.send(f"❌ Database error: {str(e)}")
            return
        
        verified_role = ctx.guild.get_role(config[0])
        if not verified_role:
            await ctx.send("❌ Verified role not found!")
            return
        
        if role is None:
            # Show available roles to bulk verify
            roles = [r for r in ctx.guild.roles if r != verified_role and r != ctx.guild.default_role and not r.managed]
            
            if not roles:
                await ctx.send("❌ No suitable roles found for bulk verification!")
                return
            
            embed = discord.Embed(
                title="👥 Select Role for Bulk Verification",
                description="Choose a role to verify all its members:",
                color=0x0099ff
            )
            
            role_list = ""
            for i, r in enumerate(roles[:10]):
                member_count = len([m for m in r.members if not m.bot and verified_role not in m.roles])
                role_list += f"`{i+1}.` {r.mention} ({member_count} unverified)\n"
            
            embed.add_field(name="Available Roles", value=role_list, inline=False)
            embed.set_footer(text="Reply with the role number")
            
            await ctx.send(embed=embed)
            
            def check(m):
                return (m.author == ctx.author and m.channel == ctx.channel and 
                       m.content.strip().isdigit() and 1 <= int(m.content.strip()) <= len(roles))
            
            try:
                choice = await self.bot.wait_for('message', timeout=60.0, check=check)
                role = roles[int(choice.content.strip()) - 1]
            except asyncio.TimeoutError:
                await ctx.send("⏰ Role selection timed out.")
                return
        
        # Get members to verify
        members_to_verify = [m for m in role.members if not m.bot and verified_role not in m.roles]
        
        if not members_to_verify:
            await ctx.send(f"✅ All members in {role.mention} are already verified!")
            return
        
        # Confirmation
        embed = discord.Embed(
            title="⚠️ Bulk Verification Confirmation",
            description=f"This will verify **{len(members_to_verify)}** members from {role.mention}",
            color=0xff9900
        )
        
        embed.add_field(
            name="Members to Verify",
            value=f"{len(members_to_verify)} unverified members",
            inline=True
        )
        
        embed.add_field(
            name="Action",
            value=f"Add {verified_role.mention} role",
            inline=True
        )
        
        embed.set_footer(text="React ✅ to confirm or ❌ to cancel")
        
        message = await ctx.send(embed=embed)
        await message.add_reaction("✅")
        await message.add_reaction("❌")
        
        def reaction_check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == message.id
        
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=reaction_check)
            
            if str(reaction.emoji) == "❌":
                await ctx.send("❌ Bulk verification cancelled.")
                return
            
        except asyncio.TimeoutError:
            await ctx.send("⏰ Confirmation timed out.")
            return
        
        # Perform bulk verification
        verified_count = 0
        failed_count = 0
        
        status_embed = discord.Embed(
            title="🔄 Bulk Verification in Progress",
            description=f"Verifying {len(members_to_verify)} members...",
            color=0x0099ff
        )
        
        status_message = await ctx.send(embed=status_embed)
        
        for member in members_to_verify:
            try:
                await member.add_roles(verified_role, reason=f"Bulk verification by {ctx.author}")
                verified_count += 1
            except:
                failed_count += 1
        
        # Final result
        result_embed = discord.Embed(
            title="✅ Bulk Verification Complete",
            color=0x00ff00 if failed_count == 0 else 0xff9900
        )
        
        result_embed.add_field(name="✅ Verified", value=str(verified_count), inline=True)
        result_embed.add_field(name="❌ Failed", value=str(failed_count), inline=True)
        result_embed.add_field(name="📊 Total", value=str(len(members_to_verify)), inline=True)
        
        await status_message.edit(embed=result_embed)
        logger.info(f"Bulk verification: {verified_count} verified, {failed_count} failed by {ctx.author.id}")
    
    @commands.hybrid_command(name="verification-config", description="⚙️ Show current verification configuration (Admin+)")
    @has_permission("admin")
    async def verification_config(self, ctx):
        """Show detailed verification configuration"""
        
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM verification_config WHERE guild_id = ?', (ctx.guild.id,))
            config = cursor.fetchone()
            conn.close()
            
            if not config:
                embed = discord.Embed(
                    title="❌ No Configuration Found",
                    description="No verification system configured for this server.",
                    color=0xff0000
                )
                embed.add_field(
                    name="🚀 Get Started",
                    value="Use `/setup-verification` to create your verification system!",
                    inline=False
                )
                await ctx.send(embed=embed)
                return
        except Exception as e:
            await ctx.send(f"❌ Database error: {str(e)}")
            return
        
        # Parse configuration
        guild_id, channel_id, role_id, method, timeout, max_attempts = config[:6]
        text_ui = config[6] if len(config) > 6 else "both"
        
        channel = ctx.guild.get_channel(channel_id) if channel_id else None
        role = ctx.guild.get_role(role_id) if role_id else None
        
        embed = discord.Embed(
            title="⚙️ Verification Configuration",
            description="Current system settings:",
            color=0x0099ff
        )
        
        # Basic settings
        embed.add_field(
            name="📍 Channel",
            value=channel.mention if channel else "❌ **DISABLED**",
            inline=True
        )
        
        embed.add_field(
            name="👤 Verified Role",
            value=role.mention if role else "❌ Not found",
            inline=True
        )
        
        embed.add_field(
            name="🎯 Method",
            value=method.replace('_', ' ').title(),
            inline=True
        )
        
        # Advanced settings
        embed.add_field(
            name="⏰ Timeout",
            value=f"{timeout} seconds ({timeout//60}m {timeout%60}s)",
            inline=True
        )
        
        embed.add_field(
            name="🔄 Max Attempts",
            value=f"{max_attempts} attempts",
            inline=True
        )
        
        # Text UI settings for text captcha
        if method == "text_captcha":
            ui_display = {
                "form": "📝 Form Only",
                "dropdown": "📋 Dropdown Only", 
                "both": "🎯 Both Options"
            }
            embed.add_field(
                name="📱 Text UI Style",
                value=ui_display.get(text_ui, "🎯 Both Options"),
                inline=True
            )
        
        # Status
        status = "🟢 **ACTIVE**" if channel else "🔴 **DISABLED**"
        embed.add_field(
            name="📊 Status",
            value=status,
            inline=False
        )
        
        # Statistics
        if role:
            verified_count = len(role.members)
            total_members = len([m for m in ctx.guild.members if not m.bot])
            rate = (verified_count / total_members * 100) if total_members > 0 else 0
            
            embed.add_field(
                name="📈 Statistics",
                value=f"**Verified:** {verified_count}/{total_members} ({rate:.1f}%)",
                inline=False
            )
        
        embed.set_footer(text="Use /setup-verification to modify settings")
        
        await ctx.send(embed=embed)

# ================================
# MODERN UI CLASSES FOR SETUP WIZARD
# ================================

class SetupWizardView(discord.ui.View):
    """Modern setup wizard with buttons and embed editing"""
    
    def __init__(self, cog, author):
        super().__init__(timeout=300)
        self.cog = cog
        self.author = author
    
    @discord.ui.button(label="Start Setup", style=discord.ButtonStyle.success, emoji="🚀")
    async def start_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Only the command user can use this!", ephemeral=True)
            return
        
        await self._show_step_1_channel(interaction)
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="🚫")
    async def cancel_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Only the command user can use this!", ephemeral=True)
            return
        
        if self.author.id in self.cog.setup_sessions:
            del self.cog.setup_sessions[self.author.id]
        
        embed = discord.Embed(
            title="❌ Setup Cancelled",
            description="Verification setup has been cancelled.",
            color=0xff0000
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    async def _show_step_1_channel(self, interaction):
        """Step 1: Channel Selection with buttons"""
        embed = discord.Embed(
            title="🛡️ Verification Setup - Step 1/5",
            description="**📍 Channel Selection**\nWhere should new members verify themselves?",
            color=0x0099ff
        )
        
        embed.add_field(
            name="💡 Options",
            value="**📺 Use Existing Channel:** Select from your current text channels (recommended for most servers)\n**🆕 Create New Channel:** I'll create a dedicated `#verification` channel with proper permissions",
            inline=False
        )
        
        embed.set_footer(text="Choose an option below")
        
        view = ChannelSelectionView(self.cog, self.author)
        await interaction.response.edit_message(embed=embed, view=view)

class ChannelSelectionView(discord.ui.View):
    """Channel selection step"""
    
    def __init__(self, cog, author):
        super().__init__(timeout=300)
        self.cog = cog
        self.author = author
    
    @discord.ui.button(label="Use Existing Channel", style=discord.ButtonStyle.primary, emoji="📺")
    async def use_existing_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Only the command user can use this!", ephemeral=True)
            return
        
        await self._show_channel_list(interaction)
    
    @discord.ui.button(label="Create New Channel", style=discord.ButtonStyle.success, emoji="🆕")
    async def create_new_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Only the command user can use this!", ephemeral=True)
            return
        
        await self._create_channel(interaction)
    
    async def _show_channel_list(self, interaction):
        """Show list of existing channels"""
        channels = [ch for ch in interaction.guild.text_channels if ch.permissions_for(interaction.guild.me).send_messages]
        
        if not channels:
            await self._create_channel(interaction)
            return
        
        embed = discord.Embed(
            title="🛡️ Verification Setup - Step 1/5",
            description="**📺 Select Existing Channel**\nChoose from your available channels:",
            color=0x0099ff
        )
        
        view = ChannelListView(self.cog, self.author, channels[:25])
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def _create_channel(self, interaction):
        """Create new verification channel"""
        try:
            # Base permissions - verified role will be added after role creation
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(
                    read_messages=True, send_messages=False
                ),
                interaction.guild.me: discord.PermissionOverwrite(
                    read_messages=True, send_messages=True, manage_messages=True
                )
            }
            
            new_channel = await interaction.guild.create_text_channel(
                name="verification",
                topic="🛡️ Server verification - Complete to gain access!",
                overwrites=overwrites,
                reason="Verification setup"
            )
            
            self.cog.setup_sessions[self.author.id]['config']['channel'] = new_channel
            
            await self._show_step_2_method(interaction, f"✅ Created {new_channel.mention}")
            
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Permission Error",
                description="I don't have permission to create channels!\n\nPlease give me the 'Manage Channels' permission and try again.",
                color=0xff0000
            )
            
            view = ChannelSelectionView(self.cog, self.author)
            await interaction.response.edit_message(embed=embed, view=view)
    
    async def _show_step_2_method(self, interaction, status_message=""):
        """Show verification method selection"""
        embed = discord.Embed(
            title="🛡️ Verification Setup - Step 2/5",
            description="**🎯 Verification Method**\nChoose your security level:",
            color=0x0099ff
        )
        
        if status_message:
            embed.add_field(name="📍 Channel", value=status_message, inline=False)
        
        embed.add_field(
            name="🛡️ Available Methods",
            value="**🔘 Simple Button** - One click verification (fastest, basic security)\n**🧮 Math Captcha** - Solve arithmetic problems (medium security)\n**📝 Text Captcha** - Type exact text shown (high security)\n**😀 Emoji Sequence** - Remember and click emoji patterns (fun)\n**🔤 Word Scramble** - Unscramble words (engaging)\n**🎨 Color Buttons** - Click the correct color (visual)",
            inline=False
        )
        
        embed.set_footer(text="💡 Tip: Math Captcha and Text Captcha offer the best security")
        
        view = MethodSelectionView(self.cog, self.author)
        await interaction.response.edit_message(embed=embed, view=view)

class ChannelListView(discord.ui.View):
    """Channel selection dropdown"""
    
    def __init__(self, cog, author, channels):
        super().__init__(timeout=300)
        self.cog = cog
        self.author = author
        
        options = []
        for i, channel in enumerate(channels):
            options.append(discord.SelectOption(
                label=f"#{channel.name}",
                description=f"ID: {channel.id}",
                value=str(channel.id),
                emoji="📺"
            ))
        
        select = discord.ui.Select(
            placeholder="Choose a channel...",
            options=options,
            min_values=1,
            max_values=1
        )
        
        # Create a proper callback function
        async def channel_callback(select_interaction):
            await self.channel_selected(select_interaction)
        
        select.callback = channel_callback
        self.add_item(select)
    
    async def channel_selected(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Only the command user can use this!", ephemeral=True)
            return
        
        try:
            channel_id = int(interaction.data['values'][0])
            channel = interaction.guild.get_channel(channel_id)
            
            if not channel:
                await interaction.response.send_message("❌ Selected channel no longer exists!", ephemeral=True)
                return
        except (KeyError, IndexError, ValueError) as e:
            await interaction.response.send_message("❌ Error processing channel selection. Please try again.", ephemeral=True)
            return
        
        self.cog.setup_sessions[self.author.id]['config']['channel'] = channel
        
        embed = discord.Embed(
            title="🛡️ Verification Setup - Step 2/5",
            description="**🎯 Verification Method**\nChoose your security level:",
            color=0x0099ff
        )
        
        embed.add_field(name="📍 Channel", value=f"✅ Selected {channel.mention}", inline=False)
        
        embed.add_field(
            name="🛡️ Available Methods",
            value="**🔘 Simple Button** - One click verification (fastest, basic security)\n**🧮 Math Captcha** - Solve arithmetic problems (medium security)\n**📝 Text Captcha** - Type exact text shown (high security)\n**😀 Emoji Sequence** - Remember and click emoji patterns (fun)\n**🔤 Word Scramble** - Unscramble words (engaging)\n**🎨 Color Buttons** - Click the correct color (visual)",
            inline=False
        )
        
        embed.set_footer(text="💡 Tip: Math Captcha and Text Captcha offer the best security")
        
        view = MethodSelectionView(self.cog, self.author)
        await interaction.response.edit_message(embed=embed, view=view)

class MethodSelectionView(discord.ui.View):
    """Verification method selection"""
    
    def __init__(self, cog, author):
        super().__init__(timeout=300)
        self.cog = cog
        self.author = author
        
        # Create buttons for each method
        methods = [
            ("Simple Button", "simple_button", discord.ButtonStyle.success, "🔘"),
            ("Image Captcha", "image_captcha", discord.ButtonStyle.danger, "🔒"),
            ("Math Captcha", "math_captcha", discord.ButtonStyle.primary, "🧮"),
            ("Text Captcha", "text_captcha", discord.ButtonStyle.primary, "📝")
        ]
        
        for label, value, style, emoji in methods:
            button = discord.ui.Button(label=label, style=style, emoji=emoji)
            button.callback = self.create_method_callback(value, label)
            self.add_item(button)
        
        # Second row
        methods_2 = [
            ("Emoji Sequence", "emoji_sequence", discord.ButtonStyle.primary, "😀"),
            ("Word Scramble", "word_scramble", discord.ButtonStyle.primary, "🔤"),
            ("Color Buttons", "color_buttons", discord.ButtonStyle.primary, "🎨")
        ]
        
        for label, value, style, emoji in methods_2:
            button = discord.ui.Button(label=label, style=style, emoji=emoji)
            button.callback = self.create_method_callback(value, label)
            self.add_item(button)
    
    def create_method_callback(self, method_value, method_label):
        async def callback(interaction):
            if interaction.user != self.author:
                await interaction.response.send_message("❌ Only the command user can use this!", ephemeral=True)
                return
            
            self.cog.setup_sessions[self.author.id]['config']['verification_type'] = method_value
            
            await self._show_step_3_text_ui(interaction, method_label)
        
        return callback
    
    async def _show_step_3_text_ui(self, interaction, method_name):
        """Show text captcha UI preference step"""
        embed = discord.Embed(
            title="🛡️ Verification Setup - Step 3/6",
            description="**📝 Text Captcha Interface**\nHow should users submit text captcha answers?",
            color=0x0099ff
        )
        
        config = self.cog.setup_sessions[self.author.id]['config']
        embed.add_field(name="📍 Channel", value=config['channel'].mention, inline=True)
        embed.add_field(name="🎯 Method", value=f"✅ {method_name}", inline=True)
        
        embed.add_field(
            name="🎨 Interface Options",
            value="**📝 Form Only** - Users type in a pop-up form (more secure)\n**📋 Dropdown Only** - Multiple choice dropdown (easier)\n**🎯 Both Options** - Let users choose their preferred method",
            inline=False
        )
        
        embed.add_field(
            name="💡 Recommendations",
            value="• **Form** = Harder for bots to bypass, more secure\n• **Dropdown** = Mobile-friendly, easier for users\n• **Both** = Best user experience and flexibility",
            inline=False
        )
        
        embed.set_footer(text="This only affects text-based captchas (Math, Text, Word Scramble)")
        
        view = TextUISelectionView(self.cog, self.author)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def _show_step_4_role(self, interaction, method_name):
        """Show role configuration"""
        embed = discord.Embed(
            title="🛡️ Verification Setup - Step 4/6",
            description="**👤 Verified Role**\nWhat role should verified members receive?",
            color=0x0099ff
        )
        
        config = self.cog.setup_sessions[self.author.id]['config']
        embed.add_field(name="📍 Channel", value=config['channel'].mention, inline=True)
        embed.add_field(name="🎯 Method", value=f"✅ {method_name}", inline=True)
        
        embed.add_field(
            name="💡 Options",
            value="**Use Existing Role:** Select from your current server roles\n**Create New Role:** I'll create a 'Verified' role with green color",
            inline=False
        )
        
        embed.set_footer(text="Choose how to set up the verified role")
        
        view = RoleSelectionView(self.cog, self.author)
        await interaction.response.edit_message(embed=embed, view=view)

class TextUISelectionView(discord.ui.View):
    """Text captcha UI preference selection"""
    
    def __init__(self, cog, author):
        super().__init__(timeout=300)
        self.cog = cog
        self.author = author
    
    @discord.ui.button(label="Form Only", style=discord.ButtonStyle.primary, emoji="📝")
    async def form_only(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Only the command user can use this!", ephemeral=True)
            return
        
        self.cog.setup_sessions[self.author.id]['config']['text_captcha_ui'] = 'form'
        await self._show_step_4_role(interaction)
    
    @discord.ui.button(label="Dropdown Only", style=discord.ButtonStyle.secondary, emoji="📋")
    async def dropdown_only(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Only the command user can use this!", ephemeral=True)
            return
        
        self.cog.setup_sessions[self.author.id]['config']['text_captcha_ui'] = 'dropdown'
        await self._show_step_4_role(interaction)
    
    @discord.ui.button(label="Both Options", style=discord.ButtonStyle.success, emoji="🎯")
    async def both_options(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Only the command user can use this!", ephemeral=True)
            return
        
        self.cog.setup_sessions[self.author.id]['config']['text_captcha_ui'] = 'both'
        await self._show_step_4_role(interaction)
    
    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary, emoji="⬅️")
    async def back_to_method(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Only the command user can use this!", ephemeral=True)
            return
        
        await self._show_method_selection(interaction)
    
    async def _show_step_4_role(self, interaction):
        """Show role configuration"""
        config = self.cog.setup_sessions[self.author.id]['config']
        
        embed = discord.Embed(
            title="🛡️ Verification Setup - Step 4/6",
            description="**👤 Verified Role**\nWhat role should verified members receive?",
            color=0x0099ff
        )
        
        embed.add_field(name="📍 Channel", value=config['channel'].mention, inline=True)
        embed.add_field(name="🎯 Method", value=config['verification_type'].replace('_', ' ').title(), inline=True)
        
        # Show UI preference for text-based captchas
        ui_pref = config.get('text_captcha_ui', 'both')
        ui_display = {"form": "📝 Form Only", "dropdown": "📋 Dropdown Only", "both": "🎯 Both Options"}
        embed.add_field(name="📱 Text UI", value=ui_display[ui_pref], inline=True)
        
        embed.add_field(
            name="💡 Options",
            value="**Use Existing Role:** Select from your current server roles\n**Create New Role:** I'll create a 'Verified' role with green color",
            inline=False
        )
        
        embed.set_footer(text="Choose how to set up the verified role")
        
        view = RoleSelectionView(self.cog, self.author)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def _show_method_selection(self, interaction):
        """Go back to method selection step"""
        embed = discord.Embed(
            title="🛡️ Verification Setup - Step 2/6",
            description="**🎯 Verification Method**\nChoose your verification security level:",
            color=0x0099ff
        )
        
        config = self.cog.setup_sessions[self.author.id]['config']
        embed.add_field(name="📍 Channel", value=config['channel'].mention, inline=True)
        
        embed.add_field(
            name="🛡️ Available Methods",
            value="**🔒 Image Captcha** - Bot-proof (recommended)\n**🧮 Math Captcha** - Simple calculations\n**📝 Text Captcha** - Type correctly\n**😀 Emoji Sequence** - Memory game\n**🔤 Word Scramble** - Unscramble words\n**🎨 Color Buttons** - Click correct color",
            inline=False
        )
        
        view = MethodSelectionView(self.cog, self.author)
        await interaction.response.edit_message(embed=embed, view=view)

class RoleSelectionView(discord.ui.View):
    """Role selection step"""
    
    def __init__(self, cog, author):
        super().__init__(timeout=300)
        self.cog = cog
        self.author = author
    
    @discord.ui.button(label="Use Existing Role", style=discord.ButtonStyle.primary, emoji="👥")
    async def use_existing_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Only the command user can use this!", ephemeral=True)
            return
        
        await self._show_role_list(interaction)
    
    @discord.ui.button(label="Create New Role", style=discord.ButtonStyle.success, emoji="✨")
    async def create_new_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Only the command user can use this!", ephemeral=True)
            return
        
        await self._create_role(interaction)
    
    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary, emoji="⬅️")
    async def back_to_text_ui(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Only the command user can use this!", ephemeral=True)
            return
        
        await self._show_text_ui_selection(interaction)
    
    async def _show_text_ui_selection(self, interaction):
        """Go back to text UI selection step"""
        config = self.cog.setup_sessions[self.author.id]['config']
        
        embed = discord.Embed(
            title="🛡️ Verification Setup - Step 3/6",
            description="**📝 Text Captcha Interface**\nHow should users submit text captcha answers?",
            color=0x0099ff
        )
        
        embed.add_field(name="📍 Channel", value=config['channel'].mention, inline=True)
        embed.add_field(name="🎯 Method", value=config['verification_type'].replace('_', ' ').title(), inline=True)
        
        embed.add_field(
            name="🎨 Interface Options",
            value="**📝 Form Only** - Users type in a pop-up form (more secure)\n**📋 Dropdown Only** - Multiple choice dropdown (easier)\n**🎯 Both Options** - Let users choose their preferred method",
            inline=False
        )
        
        embed.add_field(
            name="💡 Recommendations",
            value="• **Form** = Harder for bots to bypass, more secure\n• **Dropdown** = Mobile-friendly, easier for users\n• **Both** = Best user experience and flexibility",
            inline=False
        )
        
        embed.set_footer(text="This only affects text-based captchas (Math, Text, Word Scramble)")
        
        view = TextUISelectionView(self.cog, self.author)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def _show_role_list(self, interaction):
        """Show existing roles"""
        # Filter out @everyone, bot managed roles, and roles higher than bot's highest role
        roles = []
        bot_top_role = interaction.guild.me.top_role.position
        
        # Debug logging
        logger.info(f"Debugging role detection for guild {interaction.guild.name}")
        logger.info(f"Bot's top role: {interaction.guild.me.top_role.name} (position: {bot_top_role})")
        
        for role in interaction.guild.roles:
            # More lenient filtering - exclude @everyone, bot-managed roles, and roles higher than bot
            if (role != interaction.guild.default_role and  # Not @everyone
                not role.is_bot_managed() and              # Not bot-managed
                role.position <= bot_top_role):            # At or below bot's role
                roles.append(role)
                logger.info(f"✅ Adding role: {role.name} (pos: {role.position}, bot_managed: {role.is_bot_managed()}, managed: {role.managed})")
            else:
                logger.info(f"❌ Filtering out role: {role.name} (pos: {role.position}, is_default: {role == interaction.guild.default_role}, bot_managed: {role.is_bot_managed()}, higher_than_bot: {role.position > bot_top_role})")
        
        # Sort by position (highest first, excluding @everyone)
        roles.sort(key=lambda r: r.position, reverse=True)
        
        if not roles:
            embed = discord.Embed(
                title="❌ No Suitable Roles Found",
                description="I couldn't find any roles that I can assign to users.\n\n**Possible reasons:**\n• All roles are higher than my role\n• All roles are managed by bots\n• I need higher permissions",
                color=0xff9900
            )
            
            embed.add_field(
                name="💡 Solutions",
                value="• Create a new role (recommended)\n• Move my role higher in the hierarchy\n• Check my permissions",
                inline=False
            )
            
            view = discord.ui.View()
            
            # Create new role button
            create_button = discord.ui.Button(
                label="✨ Create New Role",
                style=discord.ButtonStyle.success,
                emoji="✨"
            )
            
            async def create_callback(new_interaction):
                if new_interaction.user != self.author:
                    await new_interaction.response.send_message("❌ Only the command user can do this!", ephemeral=True)
                    return
                await self._create_role(new_interaction)
            
            create_button.callback = create_callback
            
            # Back button
            back_button = discord.ui.Button(
                label="Back",
                style=discord.ButtonStyle.secondary,
                emoji="⬅️"
            )
            
            async def back_callback(new_interaction):
                if new_interaction.user != self.author:
                    await new_interaction.response.send_message("❌ Only the command user can do this!", ephemeral=True)
                    return
                await self._show_method_selection(new_interaction)
            
            back_button.callback = back_callback
            
            view.add_item(create_button)
            view.add_item(back_button)
            
            await interaction.response.edit_message(embed=embed, view=view)
            return
        
        embed = discord.Embed(
            title="🛡️ Verification Setup - Step 4/6",
            description="**👥 Select Existing Role**\nChoose from available roles:",
            color=0x0099ff
        )
        
        # Show some stats
        embed.add_field(
            name="📊 Found Roles",
            value=f"Found **{len(roles)}** suitable roles",
            inline=True
        )
        
        view = RoleListView(self.cog, self.author, roles[:25])
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def _show_method_selection(self, interaction):
        """Go back to method selection step"""
        embed = discord.Embed(
            title="🛡️ Verification Setup - Step 2/6",
            description="**🎯 Verification Method**\nChoose your verification security level:",
            color=0x0099ff
        )
        
        config = self.cog.setup_sessions[self.author.id]['config']
        embed.add_field(name="📍 Channel", value=config['channel'].mention, inline=True)
        
        embed.add_field(
            name="🛡️ Available Methods",
            value="**🔒 Image Captcha** - Bot-proof (recommended)\n**🧮 Math Captcha** - Simple calculations\n**📝 Text Captcha** - Type correctly\n**😀 Emoji Sequence** - Memory game\n**🔤 Word Scramble** - Unscramble words\n**🎨 Color Buttons** - Click correct color",
            inline=False
        )
        
        view = MethodSelectionView(self.cog, self.author)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def _create_role(self, interaction):
        """Create new verified role with custom name"""
        embed = discord.Embed(
            title="🛡️ Verification Setup - Step 4/6",
            description="**✨ Create Verified Role**\nWhat should the verified role be called?",
            color=0x0099ff
        )
        
        embed.add_field(
            name="💡 Popular Choices",
            value="**✅ Verified** - Classic and widely recognized\n**🎯 Member** - Simple and clean approach\n**🌟 Trusted** - Shows elevated trust level\n**👤 Verified User** - Clear and descriptive\n**✨ Custom** - Create your own unique name",
            inline=False
        )
        
        embed.add_field(
            name="🎨 Role Appearance",
            value="Your new role will have a nice **green color** 🟢 to show verified status and appear above unverified members!",
            inline=False
        )
        
        embed.set_footer(text="Choose a preset name or type a custom one")
        
        view = RoleNamingView(self.cog, self.author)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def _show_step_5_settings(self, interaction, status_message=""):
        """Show settings configuration"""
        embed = discord.Embed(
            title="🛡️ Verification Setup - Step 5/6",
            description="**⚙️ Security Settings**\nConfigure verification behavior:",
            color=0x0099ff
        )
        
        config = self.cog.setup_sessions[self.author.id]['config']
        embed.add_field(name="📍 Channel", value=config['channel'].mention, inline=True)
        embed.add_field(name="🎯 Method", value=config['verification_type'].replace('_', ' ').title(), inline=True)
        
        if status_message:
            embed.add_field(name="👤 Role", value=status_message, inline=True)
        
        embed.add_field(
            name="⏰ What is Timeout?",
            value="**Timeout** = How long users have to complete verification before it expires\n\nIf someone doesn't complete verification in time, they'll need to restart.",
            inline=False
        )
        
        embed.add_field(
            name="🚀 Choose Duration",
            value="**⚡ Quick (2 min)** - Active servers, fast-paced\n**⏰ Standard (5 min)** - Most servers, recommended\n**🕐 Extended (10 min)** - Relaxed, mobile-friendly",
            inline=False
        )
        
        embed.set_footer(text="Choose a timeout duration that fits your server")
        
        view = SettingsView(self.cog, self.author)
        await interaction.response.edit_message(embed=embed, view=view)

class RoleListView(discord.ui.View):
    """Role selection dropdown"""
    
    def __init__(self, cog, author, roles):
        super().__init__(timeout=300)
        self.cog = cog
        self.author = author
        
        options = []
        for role in roles:
            options.append(discord.SelectOption(
                label=f"@{role.name}",
                description=f"{len(role.members)} members",
                value=str(role.id),
                emoji="👥"
            ))
        
        select = discord.ui.Select(
            placeholder="Choose a role...",
            options=options,
            min_values=1,
            max_values=1
        )
        
        # Create a proper callback function
        async def role_callback(select_interaction):
            await self.role_selected(select_interaction)
        
        select.callback = role_callback
        self.add_item(select)
        
        # Back button
        back_button = discord.ui.Button(
            label="Back",
            style=discord.ButtonStyle.secondary,
            emoji="⬅️"
        )
        
        async def back_callback(interaction):
            if interaction.user != self.author:
                await interaction.response.send_message("❌ Only the command user can use this!", ephemeral=True)
                return
            
            # Go back to role selection
            embed = discord.Embed(
                title="🛡️ Verification Setup - Step 3/5",
                description="**👤 Verified Role**\nWhat role should verified members receive?",
                color=0x0099ff
            )
            
            config = self.cog.setup_sessions[self.author.id]['config']
            embed.add_field(name="📍 Channel", value=config['channel'].mention, inline=True)
            embed.add_field(name="🎯 Method", value=config['verification_type'].replace('_', ' ').title(), inline=True)
            
            embed.add_field(
                name="💡 Options",
                value="**Use Existing Role:** Select from your current server roles\n**Create New Role:** I'll create a 'Verified' role with green color",
                inline=False
            )
            
            embed.set_footer(text="Choose how to set up the verified role")
            
            view = RoleSelectionView(self.cog, self.author)
            await interaction.response.edit_message(embed=embed, view=view)
        
        back_button.callback = back_callback
        self.add_item(back_button)
    
    async def role_selected(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Only the command user can use this!", ephemeral=True)
            return
        
        try:
            role_id = int(interaction.data['values'][0])
            role = interaction.guild.get_role(role_id)
            
            if not role:
                await interaction.response.send_message("❌ Selected role no longer exists!", ephemeral=True)
                return
        except (KeyError, IndexError, ValueError) as e:
            await interaction.response.send_message("❌ Error processing role selection. Please try again.", ephemeral=True)
            return
        
        self.cog.setup_sessions[self.author.id]['config']['verified_role'] = role
        
        embed = discord.Embed(
            title="🛡️ Verification Setup - Step 4/5",
            description="**⚙️ Security Settings**\nConfigure verification behavior:",
            color=0x0099ff
        )
        
        config = self.cog.setup_sessions[self.author.id]['config']
        embed.add_field(name="📍 Channel", value=config['channel'].mention, inline=True)
        embed.add_field(name="🎯 Method", value=config['verification_type'].replace('_', ' ').title(), inline=True)
        embed.add_field(name="👤 Role", value=f"✅ Selected {role.mention}", inline=True)
        
        embed.add_field(
            name="⏰ What is Timeout?",
            value="**Timeout** = How long users have to complete verification before it expires\n\nIf someone doesn't complete verification in time, they'll need to restart.",
            inline=False
        )
        
        embed.add_field(
            name="🚀 Choose Duration",
            value="**⚡ Quick (2 min)** - Active servers, fast-paced\n**⏰ Standard (5 min)** - Most servers, recommended\n**🕐 Extended (10 min)** - Relaxed, mobile-friendly",
            inline=False
        )
        
        embed.set_footer(text="Choose a timeout duration that fits your server")
        
        view = SettingsView(self.cog, self.author)
        await interaction.response.edit_message(embed=embed, view=view)

class SettingsView(discord.ui.View):
    """Settings configuration"""
    
    def __init__(self, cog, author):
        super().__init__(timeout=300)
        self.cog = cog
        self.author = author
    
    @discord.ui.button(label="Quick (2 min)", style=discord.ButtonStyle.secondary, emoji="⚡")
    async def quick_timeout(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Only the command user can use this!", ephemeral=True)
            return
        
        self.cog.setup_sessions[self.author.id]['config']['timeout'] = 120
        self.cog.setup_sessions[self.author.id]['config']['max_attempts'] = 3
        
        await self._show_step_6_review(interaction)
    
    @discord.ui.button(label="Standard (5 min)", style=discord.ButtonStyle.primary, emoji="⏰")
    async def standard_timeout(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Only the command user can use this!", ephemeral=True)
            return
        
        self.cog.setup_sessions[self.author.id]['config']['timeout'] = 300
        self.cog.setup_sessions[self.author.id]['config']['max_attempts'] = 3
        
        await self._show_step_6_review(interaction)
    
    @discord.ui.button(label="Extended (10 min)", style=discord.ButtonStyle.secondary, emoji="🕐")
    async def extended_timeout(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Only the command user can use this!", ephemeral=True)
            return
        
        self.cog.setup_sessions[self.author.id]['config']['timeout'] = 600
        self.cog.setup_sessions[self.author.id]['config']['max_attempts'] = 5
        
        await self._show_step_6_review(interaction)
    
    async def _show_step_6_review(self, interaction):
        """Show final review"""
        config = self.cog.setup_sessions[self.author.id]['config']
        
        embed = discord.Embed(
            title="🛡️ Verification Setup - Step 6/6",
            description="**📋 Review & Activate**\nPlease review your configuration:",
            color=0x0099ff
        )
        
        embed.add_field(name="📍 Channel", value=config['channel'].mention, inline=True)
        embed.add_field(name="👤 Role", value=config['verified_role'].mention, inline=True)
        embed.add_field(name="🎯 Method", value=config['verification_type'].replace('_', ' ').title(), inline=True)
        
        # Show UI preference for text-based captchas
        ui_pref = config.get('text_captcha_ui', 'both')
        ui_display = {"form": "📝 Form Only", "dropdown": "📋 Dropdown Only", "both": "🎯 Both Options"}
        embed.add_field(name="📱 Text UI", value=ui_display[ui_pref], inline=True)
        
        embed.add_field(name="⏰ Timeout", value=f"{config['timeout']} seconds", inline=True)
        embed.add_field(name="🎯 Max Attempts", value=str(config['max_attempts']), inline=True)
        
        embed.add_field(
            name="🎉 What happens next?",
            value="• System activates immediately\n• Welcome message posted\n• New members auto-prompted\n• Easy management commands",
            inline=False
        )
        
        embed.add_field(
            name="🧪 Want to Test First?",
            value="After activation, use `/test-verification` to see how it works without giving yourself the role!",
            inline=False
        )
        
        embed.set_footer(text="Click 'Activate' to go live or 'Test First' to try it!")
        
        view = FinalReviewView(self.cog, self.author)
        await interaction.response.edit_message(embed=embed, view=view)

class FinalReviewView(discord.ui.View):
    """Final review and activation"""
    
    def __init__(self, cog, author):
        super().__init__(timeout=300)
        self.cog = cog
        self.author = author
    
    @discord.ui.button(label="Activate System", style=discord.ButtonStyle.success, emoji="🚀")
    async def activate_system(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Only the command user can use this!", ephemeral=True)
            return
        
        config = self.cog.setup_sessions[self.author.id]['config']
        
        try:
            # Save to database
            conn = self.cog.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO verification_config 
                (guild_id, verification_channel_id, verified_role_id, verification_type, 
                 verification_timeout, max_attempts, text_captcha_ui)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                interaction.guild.id,
                config['channel'].id,
                config['verified_role'].id,
                config['verification_type'],
                config['timeout'],
                config['max_attempts'],
                config.get('text_captcha_ui', 'both')
            ))
            
            conn.commit()
            conn.close()
            
            # Hide verification channel from verified role
            try:
                await config['channel'].set_permissions(
                    config['verified_role'],
                    read_messages=False,
                    reason="Hide verification channel from verified users"
                )
            except discord.Forbidden:
                pass  # Continue even if we can't set permissions
            
            # Send verification message to channel
            await self.cog._send_verification_message(config['channel'], config)
            
            # Success!
            embed = discord.Embed(
                title="🎉 Verification System Activated!",
                description=f"Your verification system is now **LIVE** in {config['channel'].mention}!",
                color=0x00ff00
            )
            
            embed.add_field(
                name="✅ System Active",
                value=f"• Channel: {config['channel'].mention}\n• Method: {config['verification_type'].replace('_', ' ').title()}\n• Role: {config['verified_role'].mention}",
                inline=False
            )
            
            embed.add_field(
                name="🛠️ Management Commands",
                value="`/verification-info` - View settings\n`/manual-verify @user` - Manual verification\n`/reset-verification @user` - Reset user\n`/verification-stats` - Statistics",
                inline=False
            )
            
            embed.set_footer(text="✨ Setup complete! Test with an alt account.")
            
            await interaction.response.edit_message(embed=embed, view=None)
            
            # Cleanup
            del self.cog.setup_sessions[self.author.id]
            
            logger.info(f"Verification system activated for guild {interaction.guild.id}")
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Activation Failed",
                description=f"Error: {str(e)}",
                color=0xff0000
            )
            
            await interaction.response.edit_message(embed=embed, view=None)

class RoleNamingView(discord.ui.View):
    """Role naming selection"""
    
    def __init__(self, cog, author):
        super().__init__(timeout=300)
        self.cog = cog
        self.author = author
    
    @discord.ui.button(label="Verified", style=discord.ButtonStyle.success, emoji="✅")
    async def verified_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Only the command user can use this!", ephemeral=True)
            return
        
        await self._create_role_with_name(interaction, "✅ Verified")
    
    @discord.ui.button(label="Member", style=discord.ButtonStyle.primary, emoji="🎯")
    async def member_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Only the command user can use this!", ephemeral=True)
            return
        
        await self._create_role_with_name(interaction, "🎯 Member")
    
    @discord.ui.button(label="Trusted", style=discord.ButtonStyle.primary, emoji="🌟")
    async def trusted_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Only the command user can use this!", ephemeral=True)
            return
        
        await self._create_role_with_name(interaction, "🌟 Trusted")
    
    @discord.ui.button(label="Verified User", style=discord.ButtonStyle.secondary, emoji="👤")
    async def verified_user_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Only the command user can use this!", ephemeral=True)
            return
        
        await self._create_role_with_name(interaction, "👤 Verified User")
    
    @discord.ui.button(label="Custom Name", style=discord.ButtonStyle.secondary, emoji="✨")
    async def custom_name(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Only the command user can use this!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="✨ Custom Role Name",
            description="Please type your custom role name in the chat!\n\n**Example:** `Community Member`\n**Note:** Keep it under 100 characters",
            color=0x0099ff
        )
        
        embed.set_footer(text="Type your role name in chat (you have 60 seconds)")
        
        await interaction.response.edit_message(embed=embed, view=None)
        
        # Wait for message
        def check(m):
            return m.author == self.author and m.channel == interaction.channel
        
        try:
            msg = await self.cog.bot.wait_for('message', timeout=60.0, check=check)
            custom_name = msg.content.strip()
            
            if len(custom_name) > 100:
                await interaction.followup.send("❌ Role name too long! Keep it under 100 characters.")
                return
            
            await msg.delete()
            await self._create_role_with_name(interaction, custom_name)
            
        except asyncio.TimeoutError:
            embed = discord.Embed(
                title="⏰ Timeout",
                description="You took too long to respond. Let's go back to role selection.",
                color=0xff0000
            )
            
            view = RoleSelectionView(self.cog, self.author)
            await interaction.edit_original_response(embed=embed, view=view)
    
    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary, emoji="⬅️")
    async def back_to_role_selection(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Only the command user can use this!", ephemeral=True)
            return
        
        # Go back to role selection
        embed = discord.Embed(
            title="🛡️ Verification Setup - Step 3/5",
            description="**👤 Verified Role**\nWhat role should verified members receive?",
            color=0x0099ff
        )
        
        config = self.cog.setup_sessions[self.author.id]['config']
        embed.add_field(name="📍 Channel", value=config['channel'].mention, inline=True)
        embed.add_field(name="🎯 Method", value=config['verification_type'].replace('_', ' ').title(), inline=True)
        
        embed.add_field(
            name="💡 Options",
            value="**Use Existing Role:** Select from your current server roles\n**Create New Role:** I'll create a 'Verified' role with green color",
            inline=False
        )
        
        embed.set_footer(text="Choose how to set up the verified role")
        
        view = RoleSelectionView(self.cog, self.author)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def _create_role_with_name(self, interaction, role_name):
        """Create role with specified name"""
        # Defer the response since role creation might take time
        if not interaction.response.is_done():
            await interaction.response.defer()
        
        try:
            role = await interaction.guild.create_role(
                name=role_name,
                color=discord.Color.green(),
                reason="Verification setup"
            )
            
            self.cog.setup_sessions[self.author.id]['config']['verified_role'] = role
            
            embed = discord.Embed(
                title="🛡️ Verification Setup - Step 4/5",
                description="**⚙️ Security Settings**\nConfigure verification behavior and timeouts:",
                color=0x0099ff
            )
            
            config = self.cog.setup_sessions[self.author.id]['config']
            embed.add_field(name="📍 Channel", value=config['channel'].mention, inline=True)
            embed.add_field(name="🎯 Method", value=config['verification_type'].replace('_', ' ').title(), inline=True)
            embed.add_field(name="👤 Role", value=f"✅ Created {role.mention}", inline=True)
            
            embed.add_field(
                name="⏰ What is Timeout?",
                value="**Timeout** = How long users have to complete verification before it expires.\n\nIf someone doesn't complete verification in time, they'll need to restart the process.",
                inline=False
            )
            
            embed.add_field(
                name="🚀 Choose Duration",
                value="**⚡ Quick (2 min)** - Active gaming/tech servers, fast-paced community\n**⏰ Standard (5 min)** - Most servers, balanced approach (recommended)\n**🕐 Extended (10 min)** - Relaxed communities, mobile-friendly",
                inline=False
            )
            
            embed.set_footer(text="💡 Tip: Most servers work great with Standard (5 min) timeout")
            
            view = SettingsView(self.cog, self.author)
            
            if interaction.response.is_done():
                await interaction.edit_original_response(embed=embed, view=view)
            else:
                await interaction.response.edit_message(embed=embed, view=view)
            
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Permission Error",
                description="I don't have permission to create roles!\n\nPlease give me the 'Manage Roles' permission and try again.",
                color=0xff0000
            )
            
            view = RoleSelectionView(self.cog, self.author)
            
            if interaction.response.is_done():
                await interaction.edit_original_response(embed=embed, view=view)
            else:
                await interaction.response.edit_message(embed=embed, view=view)

class TestVerificationView(discord.ui.View):
    """Test verification system"""
    
    def __init__(self, cog, author, config):
        super().__init__(timeout=300)
        self.cog = cog
        self.author = author
        self.config = config
    
    @discord.ui.button(label="Start Test", style=discord.ButtonStyle.success, emoji="🚀")
    async def start_test(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Only the command user can use this!", ephemeral=True)
            return
        
        # Set test mode
        self.cog.verification_sessions[self.author.id] = {
            'guild_id': interaction.guild.id,
            'verification_type': self.config[3],
            'start_time': asyncio.get_event_loop().time(),
            'test_mode': True
        }
        
        # Get verification message and modify for test
        test_config = {
            'verification_type': self.config[3],
            'timeout': self.config[4],
            'max_attempts': self.config[5]
        }
        
        embed = discord.Embed(
            title="🧪 TEST MODE - Verification Challenge",
            description="**This is a test!** You won't get the verified role.\n\nComplete the challenge below to see how verification works:",
            color=0xffaa00
        )
        
        # Start the same captcha system but in test mode
        await self.cog._start_captcha(interaction, self.author, self.config[3], test_mode=True)
    
    @discord.ui.button(label="Cancel Test", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel_test(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Only the command user can use this!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="❌ Test Cancelled",
            description="Verification test has been cancelled.",
            color=0xff0000
        )
        
        await interaction.response.edit_message(embed=embed, view=None)

async def setup(bot):
    await bot.add_cog(VerificationCog(bot)) 