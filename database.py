import sqlite3
import os
from datetime import datetime

DB_PATH = "neet_bot.db"

def init_database():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_date TIMESTAMP,
            total_quiz_attempts INTEGER DEFAULT 0,
            total_correct_answers INTEGER DEFAULT 0
        )
    ''')
    
    # Quiz Questions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quiz_questions (
            question_id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_text TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_answer TEXT NOT NULL,
            category TEXT,
            difficulty TEXT
        )
    ''')
    
    # User Quiz Results table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quiz_results (
            result_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            question_id INTEGER,
            user_answer TEXT,
            is_correct BOOLEAN,
            attempt_date TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (question_id) REFERENCES quiz_questions(question_id)
        )
    ''')
    
    # Messages table for storing user interactions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message_text TEXT,
            message_type TEXT,
            timestamp TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')
    
    conn.commit()
    conn.close()

def add_user(user_id, username, first_name):
    """Add a new user to the database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username, first_name, joined_date)
        VALUES (?, ?, ?, ?)
    ''', (user_id, username, first_name, datetime.now()))
    
    conn.commit()
    conn.close()

def get_user_stats(user_id):
    """Get user's quiz statistics"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT total_quiz_attempts, total_correct_answers
        FROM users WHERE user_id = ?
    ''', (user_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    return result if result else (0, 0)

def add_quiz_question(question_text, option_a, option_b, option_c, option_d, correct_answer, category, difficulty):
    """Add a new quiz question"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO quiz_questions (question_text, option_a, option_b, option_c, option_d, correct_answer, category, difficulty)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (question_text, option_a, option_b, option_c, option_d, correct_answer, category, difficulty))
    
    conn.commit()
    conn.close()

def get_random_question():
    """Get a random quiz question"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM quiz_questions ORDER BY RANDOM() LIMIT 1')
    result = cursor.fetchone()
    conn.close()
    
    return result

def save_quiz_result(user_id, question_id, user_answer, is_correct):
    """Save user's quiz answer"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO quiz_results (user_id, question_id, user_answer, is_correct, attempt_date)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, question_id, user_answer, is_correct, datetime.now()))
    
    # Update user stats
    if is_correct:
        cursor.execute('''
            UPDATE users
            SET total_correct_answers = total_correct_answers + 1,
                total_quiz_attempts = total_quiz_attempts + 1
            WHERE user_id = ?
        ''', (user_id,))
    else:
        cursor.execute('''
            UPDATE users
            SET total_quiz_attempts = total_quiz_attempts + 1
            WHERE user_id = ?
        ''', (user_id,))
    
    conn.commit()
    conn.close()

def save_message(user_id, message_text, message_type):
    """Save user message"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO messages (user_id, message_text, message_type, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (user_id, message_text, message_type, datetime.now()))
    
    conn.commit()
    conn.close()

# Initialize database on import
if not os.path.exists(DB_PATH):
    init_database()
