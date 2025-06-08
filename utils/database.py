import sqlite3
import os
import logging
from typing import Optional, List, Tuple
import datetime

logger = logging.getLogger('discord_bot.database')

class DatabaseManager:
    def __init__(self, db_path: str = 'data/bot_data.db'):
        self.db_path = db_path
        self.ensure_data_dir()
    
    def ensure_data_dir(self):
        """Ensure the data directory exists"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def get_connection(self):
        """Get a database connection"""
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Initialize all database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Warnings table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Guild settings table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                moderator_role_id INTEGER,
                warn_threshold INTEGER DEFAULT 3,
                auto_role_id INTEGER,
                welcome_channel_id INTEGER,
                log_channel_id INTEGER,
                prefix TEXT DEFAULT '!'
            )
            ''')
            
            # Invite tracking table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS invites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                invite_code TEXT NOT NULL,
                inviter_id INTEGER NOT NULL,
                uses INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(guild_id, invite_code)
            )
            ''')
            
            # Verification system table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS verification_config (
                guild_id INTEGER PRIMARY KEY,
                verification_channel_id INTEGER,
                verified_role_id INTEGER,
                verification_type TEXT DEFAULT 'text_captcha',
                two_stage_verification BOOLEAN DEFAULT FALSE,
                welcome_message TEXT,
                verification_timeout INTEGER DEFAULT 300,
                max_attempts INTEGER DEFAULT 3,
                text_captcha_ui TEXT DEFAULT 'both'
            )
            ''')
            
            # Add text_captcha_ui column if it doesn't exist (for existing databases)
            try:
                cursor.execute('ALTER TABLE verification_config ADD COLUMN text_captcha_ui TEXT DEFAULT "both"')
            except:
                pass  # Column already exists
            
            # Verification attempts table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS verification_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                attempt_count INTEGER DEFAULT 0,
                last_attempt DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending',
                verification_code TEXT
            )
            ''')
            
            # Moderation logs table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS mod_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                reason TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            conn.commit()
            logger.info("✅ Database initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    # ============ WARNING SYSTEM ============
    
    def add_warning(self, guild_id: int, user_id: int, moderator_id: int, reason: str) -> int:
        """Add a warning and return the total warning count"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            INSERT INTO warnings (guild_id, user_id, moderator_id, reason)
            VALUES (?, ?, ?, ?)
            ''', (guild_id, user_id, moderator_id, reason))
            
            # Get total warning count
            cursor.execute('''
            SELECT COUNT(*) FROM warnings WHERE guild_id = ? AND user_id = ?
            ''', (guild_id, user_id))
            
            warning_count = cursor.fetchone()[0]
            conn.commit()
            
            logger.info(f"Added warning for user {user_id} in guild {guild_id}. Total: {warning_count}")
            return warning_count
            
        except Exception as e:
            logger.error(f"Failed to add warning: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()
    
    def get_warnings(self, guild_id: int, user_id: int) -> List[Tuple]:
        """Get all warnings for a user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            SELECT reason, timestamp, moderator_id FROM warnings 
            WHERE guild_id = ? AND user_id = ?
            ORDER BY timestamp DESC
            ''', (guild_id, user_id))
            
            return cursor.fetchall()
            
        except Exception as e:
            logger.error(f"Failed to get warnings: {e}")
            return []
        finally:
            conn.close()
    
    def clear_warning(self, guild_id: int, user_id: int, warning_number: int) -> bool:
        """Clear a specific warning (1-indexed)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get all warning IDs for the user
            cursor.execute('''
            SELECT id FROM warnings 
            WHERE guild_id = ? AND user_id = ?
            ORDER BY timestamp DESC
            ''', (guild_id, user_id))
            
            warnings = cursor.fetchall()
            
            if 1 <= warning_number <= len(warnings):
                warning_id = warnings[warning_number - 1][0]
                cursor.execute('DELETE FROM warnings WHERE id = ?', (warning_id,))
                conn.commit()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to clear warning: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    # ============ GUILD SETTINGS ============
    
    def get_guild_setting(self, guild_id: int, setting: str) -> Optional[any]:
        """Get a specific guild setting"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(f'SELECT {setting} FROM guild_settings WHERE guild_id = ?', (guild_id,))
            result = cursor.fetchone()
            return result[0] if result else None
            
        except Exception as e:
            logger.error(f"Failed to get guild setting {setting}: {e}")
            return None
        finally:
            conn.close()
    
    def set_guild_setting(self, guild_id: int, setting: str, value: any) -> bool:
        """Set a specific guild setting"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(f'''
            INSERT OR REPLACE INTO guild_settings (guild_id, {setting})
            VALUES (?, ?)
            ''', (guild_id, value))
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to set guild setting {setting}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    # ============ MODERATION LOGS ============
    
    def log_moderation_action(self, guild_id: int, user_id: int, moderator_id: int, action: str, reason: str = None):
        """Log a moderation action"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            INSERT INTO mod_logs (guild_id, user_id, moderator_id, action, reason)
            VALUES (?, ?, ?, ?, ?)
            ''', (guild_id, user_id, moderator_id, action, reason))
            
            conn.commit()
            logger.info(f"Logged moderation action: {action} by {moderator_id} on {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to log moderation action: {e}")
            conn.rollback()
        finally:
            conn.close() 