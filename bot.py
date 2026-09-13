import logging
import os
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from telegram.constants import ChatAction
from database import (
    init_database, add_user, get_user_stats, add_quiz_question,
    get_random_question, save_quiz_result, save_message, 
    get_user_language, set_user_language, add_group_member, get_group_members
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

# Important Links
STUDY_MATERIAL_LINK = "https://t.me/NEET_Hindi_2027_future_Dr"
QUIZ_GROUP_LINK = "https://t.me/NEET_Hindi_imp_Quiz_2027"

# List of 18+ sticker keywords/patterns to detect
EXPLICIT_STICKER_KEYWORDS = [
    'sexy', 'adult', 'nude', 'xxx', '18+', 'porn', 'explicit',
    'hot', 'horny', 'boobs', 'ass', 'sex', 'adult content'
]

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
✅ Language - भाषा बदलें (Hindi/English)

📚 महत्वपूर्ण लिंक्स:
🔗 Study Material: {STUDY_MATERIAL_LINK}
🔗 Quiz Group: {QUIZ_GROUP_LINK}

आइए शुरुआत करते हैं! 🚀
    """
    
    keyboard = [
        ['📝 Quiz शुरू करें', '📊 मेरे Stats'],
        ['❓ Help', '🌐 Language'],
        ['📚 Study Link', '💬 Quiz Group']
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
    
    help_text = f"""
📖 NEET हिंदी 2027 हेल्पर बॉट - मदद

उपलब्ध कमांड्स:
/start - स्वागत संदेश दिखाएँ
/help - यह मदद दिखाएँ
/quiz - Quiz शुरू करें
/stats - अपनी प्रगति देखें
/language - भाषा बदलें
/report - किसी को रिपोर्ट करें
/members - ग्रुप members देखें

📝 Quiz कैसे काम करता है:
1. "📝 Quiz शुरू करें" बटन दबाएँ
2. हिंदी या अंग्रेजी माध्यम चुनें
3. सवाल का सही जवाब चुनें
4. अपना स्कोर ट्रैक करें

📚 महत्वपूर्ण लिंक्स:
🔗 Study Material: {STUDY_MATERIAL_LINK}
🔗 Quiz Group: {QUIZ_GROUP_LINK}

⚠️ नियम:
- 18+ कंटेंट/स्टिकर बिल्कुल प्रतिबंधित है
- Sexy/Adult स्टिकर भेजने वालों को तुरंत BAN किया जाएगा
- रिपोर्ट किए गए संदेश हटा दिए जाएँगे
- बार-बार उल्लंघन के लिए स्थायी बैन

किसी समस्या के लिए /report का उपयोग करें।
    """
    
    await update.message.reply_text(help_text)
    save_message(user.id, '/help', 'command')

async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle language change"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    keyboard = [
        [InlineKeyboardButton("🇮🇳 हिंदी (Hindi)", callback_data="lang_hindi")],
        [InlineKeyboardButton("🇬🇧 अंग्रेजी (English)", callback_data="lang_english")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=chat_id,
        text="🌐 अपनी पसंदीदा भाषा चुनें:\n\n🇮🇳 हिंदी माध्यम\n🇬🇧 अंग्रेजी माध्यम",
        reply_markup=reply_markup
    )

async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle language selection callback"""
    query = update.callback_query
    user = update.effective_user
    
    if query.data == "lang_hindi":
        set_user_language(user.id, "Hindi")
        await query.answer("✅ भाषा बदल दी गई - हिंदी माध्यम")
        await query.edit_message_text(text="✅ आपकी भाषा हिंदी में सेट कर दी गई है!\n\n📝 अब आप हिंदी में सवाल पाएँगे।")
        
    elif query.data == "lang_english":
        set_user_language(user.id, "English")
        await query.answer("✅ Language changed - English Medium")
        await query.edit_message_text(text="✅ Your language has been set to English!\n\nYou will now receive questions in English.")
    
    save_message(user.id, f"Language: {query.data}", 'language_change')

async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start quiz with a random question"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Check if user is banned
    if user.id in banned_users:
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ आप इस बॉट का उपयोग करने के लिए प्रतिबंधित हैं। कृपया व्यवस्थापक से संपर्क करें।\n\n18+ कंटेंट भेजने के लिए आप प्रतिबंधित कर दिए गए हैं।"
        )
        return ConversationHandler.END
    
    await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
    
    # Get user's preferred language
    language = get_user_language(user.id)
    
    question = get_random_question(language)
    
    if not question:
        if language == "Hindi":
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ अभी कोई सवाल उपलब्ध नहीं है। बाद में कोशिश करें।"
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ No questions available right now. Please try later."
            )
        return ConversationHandler.END
    
    # Store current quiz
    current_quiz[user.id] = {
        'question_id': question[0],
        'question_text': question[1],
        'options': [question[2], question[3], question[4], question[5]],
        'correct_answer': question[6],
        'language': language
    }
    
    if language == "Hindi":
        quiz_text = f"""
📚 सवाल: {current_quiz[user.id]['question_text']}

A) {current_quiz[user.id]['options'][0]}
B) {current_quiz[user.id]['options'][1]}
C) {current_quiz[user.id]['options'][2]}
D) {current_quiz[user.id]['options'][3]}

अपना जवाब चुनें (A, B, C, या D):
        """
    else:
        quiz_text = f"""
📚 Question: {current_quiz[user.id]['question_text']}

A) {current_quiz[user.id]['options'][0]}
B) {current_quiz[user.id]['options'][1]}
C) {current_quiz[user.id]['options'][2]}
D) {current_quiz[user.id]['options'][3]}

Choose your answer (A, B, C, or D):
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
        language = get_user_language(user.id)
        if language == "Hindi":
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ पहले Quiz शुरू करें।"
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Please start a quiz first."
            )
        return ConversationHandler.END
    
    if message_text not in ['A', 'B', 'C', 'D']:
        language = get_user_language(user.id)
        if language == "Hindi":
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ कृपया A, B, C, या D दर्ज करें।"
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Please enter A, B, C, or D."
            )
        return WAITING_FOR_ANSWER
    
    quiz = current_quiz[user.id]
    correct_answer = quiz['correct_answer']
    language = quiz['language']
    
    # Map answer to option
    answer_map = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
    is_correct = (quiz['options'][answer_map[message_text]] == correct_answer)
    
    # Save result
    save_quiz_result(user.id, quiz['question_id'], message_text, is_correct)
    
    if language == "Hindi":
        if is_correct:
            result_text = f"✅ सही जवाब! सवाल: {quiz['question_text']}\n\n👉 सही उत्तर: {correct_answer}"
        else:
            result_text = f"❌ गलत जवाब। सवाल: {quiz['question_text']}\n\n👉 सही उत्तर: {correct_answer}\n👉 आपका जवाब: {quiz['options'][answer_map[message_text]]}"
        
        keyboard = [['📝 अगला सवाल', '📊 Stats देखें']]
        next_text = "क्या आप अगला सवाल करना चाहते हैं?"
    else:
        if is_correct:
            result_text = f"✅ Correct Answer! Question: {quiz['question_text']}\n\nCorrect Answer: {correct_answer}"
        else:
            result_text = f"❌ Wrong Answer. Question: {quiz['question_text']}\n\nCorrect Answer: {correct_answer}\nYour Answer: {quiz['options'][answer_map[message_text]]}"
        
        keyboard = [['📝 Next Question', '📊 View Stats']]
        next_text = "Would you like to attempt the next question?"
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=result_text
    )
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=next_text,
        reply_markup=reply_markup
    )
    
    del current_quiz[user.id]
    save_message(user.id, message_text, 'quiz_answer')
    
    return ConversationHandler.END

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user statistics"""
    user = update.effective_user
    language = get_user_language(user.id)
    
    attempts, correct = get_user_stats(user.id)
    
    if attempts == 0:
        accuracy = 0
    else:
        accuracy = (correct / attempts) * 100
    
    if language == "Hindi":
        stats_text = f"""
📊 {user.first_name} के Stats:

📝 कुल सवाल: {attempts}
✅ सही उत्तर: {correct}
❌ गलत उत्तर: {attempts - correct}
📈 सटीकता: {accuracy:.2f}%

💪 अपनी तैयारी जारी रखें!
        """
    else:
        stats_text = f"""
📊 {user.first_name}'s Statistics:

📝 Total Questions: {attempts}
✅ Correct Answers: {correct}
❌ Wrong Answers: {attempts - correct}
📈 Accuracy: {accuracy:.2f}%

💪 Keep up your preparation!
        """
    
    await update.message.reply_text(stats_text)
    save_message(user.id, '/stats', 'command')

async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle stickers and check for 18+ content"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    message = update.message
    
    # Check if user is banned
    if user.id in banned_users:
        await message.delete()
        return
    
    sticker = message.sticker
    
    # Check sticker emoji and title for explicit content
    sticker_emoji = sticker.emoji if hasattr(sticker, 'emoji') else ""
    sticker_set_name = sticker.sticker_set.name if sticker.sticker_set else ""
    
    # Check for 18+ sticker keywords
    is_explicit = any(keyword.lower() in sticker_set_name.lower() for keyword in EXPLICIT_STICKER_KEYWORDS)
    
    if is_explicit:
        # Ban the user
        banned_users.add(user.id)
        
        # Delete the message
        await message.delete()
        
        # Notify user
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"""
❌ ⚠️ आप प्रतिबंधित कर दिए गए हैं! ⚠️

18+ या Sexy/Adult स्टिकर भेजने के लिए आप पर स्थायी बैन लागू कर दिया गया है।

यह एक गंभीर उल्लंघन है।
कृपया व्यवस्थापक से संपर्क करें।

❌ YOU HAVE BEEN BANNED! ❌
You were permanently banned for sending 18+ or sexually explicit content.
            """
        )
        
        # Log this incident
        save_message(user.id, f"BANNED: 18+ Sticker - {sticker_set_name}", 'ban_incident')
    else:
        # Log sticker
        save_message(user.id, f"[Sticker: {sticker.file_id}]", 'sticker')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle regular messages"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    message = update.message
    language = get_user_language(user.id)
    
    # Check if user is banned
    if user.id in banned_users:
        await message.delete()
        return
    
    # Handle button presses
    if message.text == '📝 Quiz शुरू करें' or message.text == '📝 Next Question':
        await start_quiz(update, context)
    elif message.text == '📊 मेरे Stats' or message.text == '📊 View Stats':
        await show_stats(update, context)
    elif message.text == '❓ Help':
        await help_command(update, context)
    elif message.text == '🌐 Language':
        await change_language(update, context)
    elif message.text == '📚 Study Link':
        keyboard = [[InlineKeyboardButton("📚 Study Material Channel", url=STUDY_MATERIAL_LINK)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=chat_id,
            text="📚 सभी Study Material के लिए यहाँ जाएँ:\n\n👇",
            reply_markup=reply_markup
        )
    elif message.text == '💬 Quiz Group':
        keyboard = [[InlineKeyboardButton("💬 Quiz Group (सवाल हल करें)", url=QUIZ_GROUP_LINK)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=chat_id,
            text="💬 हमारे Quiz Group में शामिल हो:\n\n👇",
            reply_markup=reply_markup
        )
    else:
        # Regular message
        save_message(user.id, message.text, 'text')
        
        # Send reaction
        reactions = ['👍', '❤️', '🎉', '😊', '📚']
        keyboard = [[InlineKeyboardButton(reaction, callback_data=f"react_{reaction}") for reaction in reactions]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if language == "Hindi":
            await context.bot.send_message(
                chat_id=chat_id,
                text="👋 आपके संदेश पर प्रतिक्रिया दें:",
                reply_markup=reply_markup
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text="👋 React to your message:",
                reply_markup=reply_markup
            )

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
        await update.message.reply_text("उपयोग: /report [विवरण]")
        return
    
    report_text = ' '.join(context.args)
    
    # Log report
    save_message(user.id, f"REPORT: {report_text}", 'report')
    
    # In a real scenario, this would notify admins
    await update.message.reply_text(
        "✅ आपकी रिपोर्ट दर्ज कर दी गई है। व्यवस्थापक जल्द ही जांच करेंगे।"
    )

async def show_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show group members"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # This is a placeholder - in a real group, you'd fetch actual members
    members_text = """
👥 Group Members:

यह feature group में काम करता है। 
Group में /members command दें।

📝 सभी members को mention करने के लिए:
@member_name या /mention @username
    """
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=members_text
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
    application.add_handler(CommandHandler("language", change_language))
    application.add_handler(CommandHandler("members", show_members))
    
    # Language selection handler
    application.add_handler(CallbackQueryHandler(handle_language_selection, pattern="^lang_"))
    
    # Quiz conversation handler
    quiz_handler = ConversationHandler(
        entry_points=[
            CommandHandler("quiz", start_quiz),
            MessageHandler(filters.Regex(r'^📝 Quiz शुरू करें$|^📝 Next Question$'), start_quiz),
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
    application.add_handler(CallbackQueryHandler(handle_reaction, pattern="^react_"))
    
    # Start polling
    logger.info("🤖 NEET हिंदी 2027 हेल्पर बॉट शुरू हो गया!")
    application.run_polling()

if __name__ == '__main__':
    main()
