import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
from typing import Optional

class TagsCog(commands.Cog):
    """🏷️ Tag System"""
    
    def __init__(self, bot):
        self.bot = bot
        self.init_database()
    
    def init_database(self):
        """Initialize tags database"""
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                name TEXT,
                content TEXT,
                creator_id INTEGER,
                uses INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(guild_id, name)
            )
        """)
        
        conn.commit()
        conn.close()

    @app_commands.command(name="tag", description="Show a tag")
    @app_commands.describe(name="Name of the tag")
    async def tag(self, interaction: discord.Interaction, name: str):
        """Show a tag"""
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT content FROM tags 
            WHERE guild_id = ? AND name = ?
        """, (interaction.guild.id, name.lower()))
        
        result = cursor.fetchone()
        
        if not result:
            await interaction.response.send_message(f"❌ Tag '{name}' not found.", ephemeral=True)
            conn.close()
            return
        
        # Increment usage count
        cursor.execute("""
            UPDATE tags SET uses = uses + 1 
            WHERE guild_id = ? AND name = ?
        """, (interaction.guild.id, name.lower()))
        
        conn.commit()
        conn.close()
        
        await interaction.response.send_message(result[0])

    @app_commands.command(name="tag-create", description="Create a new tag")
    @app_commands.describe(name="Name of the tag", content="Content of the tag")
    async def tag_create(self, interaction: discord.Interaction, name: str, content: str):
        """Create a new tag"""
        if len(name) > 50:
            await interaction.response.send_message("❌ Tag name must be 50 characters or less.", ephemeral=True)
            return
            
        if len(content) > 2000:
            await interaction.response.send_message("❌ Tag content must be 2000 characters or less.", ephemeral=True)
            return
        
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO tags (guild_id, name, content, creator_id)
                VALUES (?, ?, ?, ?)
            """, (interaction.guild.id, name.lower(), content, interaction.user.id))
            
            conn.commit()
            await interaction.response.send_message(f"✅ Tag '{name}' created successfully!")
            
        except sqlite3.IntegrityError:
            await interaction.response.send_message(f"❌ Tag '{name}' already exists.", ephemeral=True)
        
        conn.close()

    @app_commands.command(name="tag-list", description="List all tags")
    async def tag_list(self, interaction: discord.Interaction):
        """List all tags"""
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT name, uses FROM tags 
            WHERE guild_id = ? 
            ORDER BY uses DESC LIMIT 20
        """, (interaction.guild.id,))
        
        tags = cursor.fetchall()
        conn.close()
        
        if not tags:
            await interaction.response.send_message("📭 No tags found.")
            return
        
        embed = discord.Embed(title="🏷️ Server Tags", color=0x3498db)
        
        tag_list = []
        for name, uses in tags:
            tag_list.append(f"**{name}** ({uses} uses)")
        
        embed.description = "\n".join(tag_list)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="tag-delete", description="Delete a tag")
    @app_commands.describe(name="Name of the tag to delete")
    async def tag_delete(self, interaction: discord.Interaction, name: str):
        """Delete a tag"""
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        
        # Check if tag exists and get creator
        cursor.execute("""
            SELECT creator_id FROM tags 
            WHERE guild_id = ? AND name = ?
        """, (interaction.guild.id, name.lower()))
        
        result = cursor.fetchone()
        
        if not result:
            await interaction.response.send_message(f"❌ Tag '{name}' not found.", ephemeral=True)
            conn.close()
            return
        
        creator_id = result[0]
        
        # Check permissions
        if (creator_id != interaction.user.id and 
            not interaction.user.guild_permissions.manage_messages):
            await interaction.response.send_message("❌ You can only delete your own tags (or have Manage Messages permission).", ephemeral=True)
            conn.close()
            return
        
        # Delete tag
        cursor.execute("""
            DELETE FROM tags 
            WHERE guild_id = ? AND name = ?
        """, (interaction.guild.id, name.lower()))
        
        conn.commit()
        conn.close()
        
        await interaction.response.send_message(f"✅ Tag '{name}' deleted successfully!")

async def setup(bot):
    await bot.add_cog(TagsCog(bot)) 