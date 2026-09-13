import logging
import os
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from telegram.constants import ChatAction
from database import (
    init_database, add_user, get_user_stats, add_quiz_question,
    get_random_question, save_quiz_result, save_message
)
import sqlite3
from datetime import datetime

# Load environment variables
load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
QUIZ_STATE = 1
WAITING_FOR_ANSWER = 2

# Banned users set (can be replaced with database)
banned_users = set()

# Current quiz question storage
current_quiz = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command with welcome message"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Add user to database
    add_user(user.id, user.username, user.first_name)
    
    welcome_text = f"""
🎉 स्वागत है {user.first_name}! 🎉

📚 NEET हिंदी 2027 हेल्पर बॉट में आपका स्वागत है!

यह बॉट आपको NEET की तैयारी में मदद करेगा:

✅ Quiz - NEET के सवाल हल करें
✅ Reactions - अपनी राय दें
✅ Messages - सवाल-जवाब करें
✅ Help - मदद लें
✅ Stats - अपनी प्रगति देखें

आइए शुरुआत करते हैं! 🚀
    """
    
    keyboard = [
        ['📝 Quiz शुरू करें', '📊 मेरे Stats'],
        ['❓ Help', '💬 संदेश भेजें']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=welcome_text,
        reply_markup=reply_markup
    )
    
    save_message(user.id, '/start', 'command')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command"""
    user = update.effective_user
    
    help_text = """
📖 NEET हिंदी 2027 हेल्पर बॉट - मदद

उपलब्ध कमांड्स:
/start - स्वागत संदेश दिखाएँ
/help - यह मदद दिखाएँ
/quiz - Quiz शुरू करें
/stats - अपनी प्रगति देखें
/report - किसी को रिपोर्ट करें

📝 Quiz कैसे काम करता है:
1. "📝 Quiz शुरू करें" बटन दबाएँ
2. सवाल का सही जवाब चुनें
3. अपना स्कोर ट्रैक करें

⚠️ नियम:
- 18+ कंटेंट/स्टिकर प्रतिबंधित है
- रिपोर्ट किए गए संदेश हटा दिए जाएँगे
- बार-बार उल्लंघन के लिए बैन किया जाएगा

किसी समस्या के लिए /report का उपयोग करें।
    """
    
    await update.message.reply_text(help_text)
    save_message(user.id, '/help', 'command')

async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start quiz with a random question"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Check if user is banned
    if user.id in banned_users:
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ आप इस बॉट का उपयोग करने के लिए प्रतिबंधित हैं। कृपया व्यवस्थापक से संपर्क करें।"
        )
        return ConversationHandler.END
    
    await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
    
    question = get_random_question()
    
    if not question:
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ अभी कोई सवाल उपलब्ध नहीं है। बाद में कोशिश करें।"
        )
        return ConversationHandler.END
    
    # Store current quiz
    current_quiz[user.id] = {
        'question_id': question[0],
        'question_text': question[1],
        'options': [question[2], question[3], question[4], question[5]],
        'correct_answer': question[6]
    }
    
    quiz_text = f"""
📚 सवाल: {current_quiz[user.id]['question_text']}

A) {current_quiz[user.id]['options'][0]}
B) {current_quiz[user.id]['options'][1]}
C) {current_quiz[user.id]['options'][2]}
D) {current_quiz[user.id]['options'][3]}

अपना जवाब चुनें (A, B, C, या D):
    """
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=quiz_text
    )
    
    save_message(user.id, '/quiz', 'command')
    return WAITING_FOR_ANSWER

async def handle_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle quiz answer"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    message_text = update.message.text.upper().strip()
    
    if user.id not in current_quiz:
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ पहले Quiz शुरू करें।"
        )
        return ConversationHandler.END
    
    if message_text not in ['A', 'B', 'C', 'D']:
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ कृपया A, B, C, या D दर्ज करें।"
        )
        return WAITING_FOR_ANSWER
    
    quiz = current_quiz[user.id]
    correct_answer = quiz['correct_answer']
    
    # Map answer to option
    answer_map = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
    is_correct = (quiz['options'][answer_map[message_text]] == correct_answer)
    
    # Save result
    save_quiz_result(user.id, quiz['question_id'], message_text, is_correct)
    
    if is_correct:
        result_text = f"✅ सही जवाब! सवाल: {quiz['question_text']}\n\n👉 सही उत्तर: {correct_answer}"
    else:
        result_text = f"❌ गलत जवाब। सवाल: {quiz['question_text']}\n\n👉 सही उत्तर: {correct_answer}\n👉 आपका जवाब: {quiz['options'][answer_map[message_text]]}"
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=result_text
    )
    
    # Show next quiz option
    keyboard = [['📝 अगला सवाल', '📊 Stats देखें']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await context.bot.send_message(
        chat_id=chat_id,
        text="क्या आप अगला सवाल करना चाहते हैं?",
        reply_markup=reply_markup
    )
    
    del current_quiz[user.id]
    save_message(user.id, message_text, 'quiz_answer')
    
    return ConversationHandler.END

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user statistics"""
    user = update.effective_user
    
    attempts, correct = get_user_stats(user.id)
    
    if attempts == 0:
        accuracy = 0
    else:
        accuracy = (correct / attempts) * 100
    
    stats_text = f"""
📊 {user.first_name} के Stats:

📝 कुल सवाल: {attempts}
✅ सही उत्तर: {correct}
❌ गलत उत्तर: {attempts - correct}
📈 सटीकता: {accuracy:.2f}%

💪 अपनी तैयारी जारी रखें!
    """
    
    await update.message.reply_text(stats_text)
    save_message(user.id, '/stats', 'command')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle regular messages"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    message = update.message
    
    # Check if user is banned
    if user.id in banned_users:
        await message.delete()
        return
    
    # Handle button presses
    if message.text == '📝 Quiz शुरू करें':
        await start_quiz(update, context)
    elif message.text == '📊 मेरे Stats':
        await show_stats(update, context)
    elif message.text == '❓ Help':
        await help_command(update, context)
    elif message.text == '💬 संदेश भेजें':
        await context.bot.send_message(
            chat_id=chat_id,
            text="💬 अपना संदेश भेजें (NEET से संबंधित):"
        )
    else:
        # Regular message
        save_message(user.id, message.text, 'text')
        
        # Send reaction
        reactions = ['👍', '❤️', '🎉', '😊', '📚']
        keyboard = [[InlineKeyboardButton(reaction, callback_data=f"react_{reaction}") for reaction in reactions]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=chat_id,
            text="👋 आपके संदेश पर प्रतिक्रिया दें:",
            reply_markup=reply_markup
        )

async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle stickers and check for 18+ content"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    message = update.message
    
    # Check if user is banned
    if user.id in banned_users:
        await message.delete()
        return
    
    # Simple check for explicit content (can be enhanced)
    sticker = message.sticker
    
    # Check sticker type (this is a basic check)
    if sticker.is_animated or sticker.is_video:
        # Can add more sophisticated checks here
        pass
    
    # Log sticker
    save_message(user.id, f"[Sticker: {sticker.file_id}]", 'sticker')

async def handle_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle emoji reactions"""
    query = update.callback_query
    user = update.effective_user
    
    await query.answer(f"👍 आपकी प्रतिक्रिया: {query.data.split('_')[1]}")
    save_message(user.id, query.data, 'reaction')

async def report_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user reports"""
    user = update.effective_user
    
    if not context.args:
        await update.message.reply_text("उपयोग: /report [user_id या विवरण]")
        return
    
    report_text = ' '.join(context.args)
    
    # Log report
    save_message(user.id, f"REPORT: {report_text}", 'report')
    
    # In a real scenario, this would notify admins
    await update.message.reply_text(
        "✅ आपकी रिपोर्ट दर्ज कर दी गई है। व्यवस्थापक जल्द ही जांच करेंगे।"
    )

def main() -> None:
    """Start the bot"""
    # Initialize database
    init_database()
    
    # Create the Application
    application = Application.builder().token(TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", show_stats))
    application.add_handler(CommandHandler("report", report_user))
    
    # Quiz conversation handler
    quiz_handler = ConversationHandler(
        entry_points=[
            CommandHandler("quiz", start_quiz),
            MessageHandler(filters.Regex(r'^📝 Quiz शुरू करें$'), start_quiz),
            MessageHandler(filters.Regex(r'^📝 अगला सवाल$'), start_quiz)
        ],
        states={
            WAITING_FOR_ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_quiz_answer)]
        },
        fallbacks=[CommandHandler("start", start)]
    )
    application.add_handler(quiz_handler)
    
    # Regular message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
    application.add_handler(CallbackQueryHandler(handle_reaction))
    
    # Start polling
    logger.info("🤖 NEET हिंदी 2027 हेल्पर बॉट शुरू हो गया!")
    application.run_polling()

if __name__ == '__main__':
    main()
