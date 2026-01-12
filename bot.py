# ASHA SAHAYI BOT
# Purpose: Health assistance for ASHA workers (Educational Project)
# Disclaimer: Provides general health information only (No diagnosis / prescription)
import sqlite3
import google.generativeai as genai
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    ConversationHandler, filters, ContextTypes
)

import nest_asyncio
nest_asyncio.apply()


TELEGRAM_TOKEN = "8313544109:AAFCdy85K6h0gGG_M0zCC4KtaOWmG3X816Q"
GEMINI_API_KEY = "AIzaSyDM1NF3RA2iNYby79KysIy36G-pSEYcUmk"

if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY_HERE":
    genai.configure(api_key=GEMINI_API_KEY)
    GEMINI_ENABLED = True
else:
    GEMINI_ENABLED = False
    print("⚠️ Using fallback system - Gemini API key not set")


# DATABASE FOR VISIT LOGGING

class VisitDatabase:
    def __init__(self, db_path='asha_visits.db'):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS visits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id TEXT NOT NULL,
                    age INTEGER NOT NULL,
                    category TEXT NOT NULL,
                    visit_type TEXT NOT NULL,
                    notes TEXT,
                    asha_id TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    language TEXT DEFAULT 'en'
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_pid ON visits(patient_id)')
    
    def log_visit(self, patient_id, age, category, visit_type, notes, asha_id, language='en'):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                INSERT INTO visits (patient_id, age, category, visit_type, notes, asha_id, language)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (patient_id, age, category, visit_type, notes, asha_id, language))
            return cursor.lastrowid
    
    def get_history(self, patient_id):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('SELECT * FROM visits WHERE patient_id = ? ORDER BY timestamp DESC', (patient_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_stats(self, asha_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT COUNT(*) as total, COUNT(DISTINCT patient_id) as unique_patients FROM visits WHERE asha_id = ?', (asha_id,))
            result = cursor.fetchone()
            return {'total_visits': result[0], 'unique_patients': result[1]}


# MULTILINGUAL SYSTEM (ENGLISH & HINDI)

TRANSLATIONS = {
    'en': {
        'welcome': '''*Welcome to ASHA Sahayi Bot!*
 *DISCLAIMER:*
• This bot provides general health information only
• NOT medical advice
• Always consult healthcare professionals
• In emergencies: Call 108

 *Commands:*
/ask <question> - Ask health questions
/log_visit - Log patient visit
/view_logs <ID> - View patient history
/stats - Your statistics
/language - Change language
/help - Show this message
/disclaimer - Medical disclaimer

 *Emergency:*
• Ambulance: 108
• Women Helpline: 1091''',

        'disclaimer': ''' *MEDICAL DISCLAIMER*

This bot provides general health information based on WHO guidelines.
It does NOT provide diagnosis or prescriptions.
Always consult qualified healthcare professionals.
Data is stored locally for privacy.''',

        'emergency': ''' *EMERGENCY DETECTED!*

Call 108 immediately or go to nearest hospital!

Emergency Contacts:
• Ambulance: 108
• Women Helpline: 1091
• Police: 100''',

        'ask_patient_id': '📝 *Enter Patient ID:*\n(Example: PT001)',
        'ask_age': '📝 *Enter Patient Age:*',
        'ask_category': '📋 *Select Visit Category:*\n👇 Tap a button below:',
        'ask_type': '📋 *Select Visit Type:*\n👇 Tap a button below:',
        'ask_notes': '📝 *Enter Visit Notes:*\n(Or type /skip)',
        'visit_logged': '✅ *Visit Logged Successfully!*\nID: {}\nPatient: {}\nCategory: {}\nType: {}',
        'stats': '📊 *Your Statistics*\n\nTotal Visits: {}\nUnique Patients: {}',
        'no_history': '📋 No records found for patient: {}',
        'language_set': '✅ Language set to English',
        'thinking': '🤔 Thinking...',
        'blocked': '❌ I cannot provide diagnosis or prescriptions. Please consult a doctor.',

        'categories': ['🤰 Maternal Care', '👶 Child Health', '🩺 Chronic Disease', '💊 General'],
        'visit_types': ['📅 Routine', '🔄 Follow-up', '🚨 Emergency', '💉 Vaccination']
    },

    'hi': {
        'welcome': '''👋 *आशा सहायी बॉट में स्वागत!*

⚠️ *अस्वीकरण:*
• यह बॉट केवल सामान्य स्वास्थ्य जानकारी देता है
• चिकित्सा सलाह नहीं
• हमेशा डॉक्टर से परामर्श करें
• आपातकाल: 108 पर कॉल करें

📋 *कमांड:*
/ask <प्रश्न> - स्वास्थ्य प्रश्न पूछें
/log_visit - रोगी यात्रा लॉग करें
/view_logs <ID> - रोगी इतिहास देखें
/stats - आंकड़े देखें
/language - भाषा बदलें
/help - यह संदेश दिखाएं
/disclaimer - चिकित्सा अस्वीकरण

🏥 *आपातकाल:*
• एम्बुलेंस: 108
• महिला हेल्पलाइन: 1091''',

        'disclaimer': '''⚠️ *चिकित्सा अस्वीकरण*

यह बॉट डब्ल्यूएचओ दिशानिर्देशों पर आधारित सामान्य जानकारी देता है।
यह निदान या दवा नुस्खे नहीं देता।
हमेशा योग्य डॉक्टर से परामर्श करें।
डेटा निजी रूप से स्थानीय रूप से संग्रहीत है।''',

        'emergency': '''🚨 *आपातकाल का पता चला!*

108 पर तुरंत कॉल करें या नजदीकी अस्पताल जाएं!

आपातकालीन संपर्क:
• एम्बुलेंस: 108
• महिला हेल्पलाइन: 1091
• पुलिस: 100''',

        'ask_patient_id': '📝 *रोगी आईडी दर्ज करें:*\n(उदाहरण: PT001)',
        'ask_age': '📝 *रोगी की आयु दर्ज करें:*',
        'ask_category': '📋 *यात्रा श्रेणी चुनें:*\n👇 नीचे बटन टैप करें:',
        'ask_type': '📋 *यात्रा प्रकार चुनें:*\n👇 नीचे बटन टैप करें:',
        'ask_notes': '📝 *यात्रा नोट्स दर्ज करें:*\n(या /skip टाइप करें)',
        'visit_logged': '✅ *यात्रा सफलतापूर्वक लॉग की गई!*\nआईडी: {}\nरोगी: {}\nश्रेणी: {}\nप्रकार: {}',
        'stats': '📊 *आपके आंकड़े*\n\nकुल यात्राएं: {}\nअद्वितीय रोगी: {}',
        'no_history': '📋 रोगी के लिए कोई रिकॉर्ड नहीं: {}',
        'language_set': '✅ भाषा हिन्दी में सेट की गई',
        'thinking': '🤔 सोच रहा हूँ...',
        'blocked': '❌ मैं निदान या नुस्खे नहीं दे सकता। कृपया डॉक्टर से परामर्श करें।',

        'categories': ['🤰 मातृ देखभाल', '👶 बाल स्वास्थ्य', '🩺 दीर्घकालिक रोग', '💊 सामान्य'],
        'visit_types': ['📅 नियमित', '🔄 फॉलो-अप', '🚨 आपातकाल', '💉 टीकाकरण']
    }
}

def t(key, lang='en'):
    return TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(key, key)

# AI RESPONSE SYSTEM

def get_fallback_response(query, language='en'):
    """Local health knowledge base"""
    knowledge = {
        'en': {
            'fever': "Fever is body's response to infection. Normal temperature: 97-99°F. Drink fluids, rest. If fever >102°F or lasts >3 days, consult doctor.",
            'cough': "Drink warm water, steam inhalation. If cough with fever or breathing difficulty, consult doctor. Avoid self-medication.",
            'cold': "Common cold is viral infection. Rest, drink fluids, steam. If high fever or breathing trouble, see doctor.",
            'headache': "Rest in dark room, stay hydrated. If severe or persistent, seek medical attention.",
            'diarrhea': "Drink ORS solution, eat light foods. If severe dehydration or lasts >2 days, see doctor.",
            'pregnancy': "Regular checkups, iron/folic acid supplements. Watch for swelling, bleeding, severe headaches.",
            'diabetes': "Monitor blood sugar, balanced diet, exercise. Consult doctor for management.",
            'blood pressure': "Normal BP: 120/80 mmHg. High BP needs lifestyle changes: reduce salt, exercise.",
            'general': "For medical concerns, please consult a healthcare provider. This is general information only."
        },
        'hi': {
            'fever': "बुखार संक्रमण के खिलाफ शरीर की प्रतिक्रिया है। सामान्य तापमान: 97-99°F। तरल पदार्थ पिएं, आराम करें। यदि बुखार >102°F या >3 दिन तक रहे, तो डॉक्टर से परामर्श करें।",
            'cough': "गर्म पानी पिएं, भाप लें। यदि खांसी बुखार या सांस लेने में तकलीफ के साथ हो, तो डॉक्टर से परामर्श करें। स्व-दवा से बचें।",
            'cold': "सर्दी वायरल संक्रमण है। आराम करें, तरल पदार्थ पिएं, भाप लें। यदि तेज बुखार या सांस लेने में तकलीफ हो, तो डॉक्टर को दिखाएं।",
            'headache': "अंधेरे कमरे में आराम करें, हाइड्रेटेड रहें। यदि गंभीर या लगातार हो, तो चिकित्सा सहायता लें।",
            'diarrhea': "ORS घोल पिएं, हल्का भोजन खाएं। यदि गंभीर निर्जलीकरण या >2 दिन तक रहे, तो डॉक्टर को दिखाएं।",
            'pregnancy': "नियमित जांच, आयरन/फोलिक एसिड सप्लीमेंट। सूजन, रक्तस्राव, गंभीर सिरदर्द पर नजर रखें।",
            'diabetes': "ब्लड शुगर की निगरानी, संतुलित आहार, व्यायाम। प्रबंधन के लिए डॉक्टर से परामर्श करें।",
            'blood pressure': "सामान्य बीपी: 120/80 mmHg। उच्च बीपी के लिए जीवनशैली में बदलाव: नमक कम करें, व्यायाम करें।",
            'general': "चिकित्सा चिंताओं के लिए, कृपया एक स्वास्थ्य सेवा प्रदाता से परामर्श करें। यह केवल सामान्य जानकारी है।"
        }
    }
    
    query_lower = query.lower()
    lang_data = knowledge.get(language, knowledge['en'])
    
    for keyword, response in lang_data.items():
        if keyword in query_lower:
            return response
    
    return lang_data['general']

def get_ai_response(query, language='en'):
    """Get response from Gemini AI"""
    if not GEMINI_ENABLED:
        return get_fallback_response(query, language)
    
    # Try available models
    model_names = ['gemini-flash-latest', 'gemini-pro-latest', 'gemini-2.0-flash-001']
    
    for model_name in model_names:
        try:
            model = genai.GenerativeModel(model_name)
            prompt = f"""You are a medical information assistant for ASHA workers in India.

STRICT RULES:
- Provide ONLY general health information based on WHO/Indian guidelines
- NEVER diagnose or prescribe
- Always recommend consulting healthcare professionals
- Respond in {'Hindi' if language == 'hi' else 'English'}
- Keep response brief (2-3 sentences)

Question: {query}"""
            
            response = model.generate_content(prompt)
            return response.text
        except:
            continue
    
    return get_fallback_response(query, language)

# TELEGRAM BOT - MAIN CLASS

LOGGING_PATIENT_ID, LOGGING_AGE, LOGGING_CATEGORY, LOGGING_TYPE, LOGGING_NOTES = range(5)

class ASHABot:
    def __init__(self, token):
        self.app = Application.builder().token(token).build()
        self.db = VisitDatabase()
        self.setup_handlers()
    
    #BASIC COMMANDS
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        lang = context.user_data.get('language', 'en')
        await update.message.reply_text(t('welcome', lang), parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        lang = context.user_data.get('language', 'en')
        await update.message.reply_text(t('welcome', lang), parse_mode='Markdown')
    
    async def disclaimer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        lang = context.user_data.get('language', 'en')
        await update.message.reply_text(t('disclaimer', lang), parse_mode='Markdown')
    
    #LANGUAGE
    
    async def set_language(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [['English', 'हिन्दी']]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(
            'Select language / भाषा चुनें:',
            reply_markup=reply_markup
        )
    
    async def language_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        choice = update.message.text
        lang = 'hi' if 'हिन्दी' in choice else 'en'
        context.user_data['language'] = lang
        await update.message.reply_text(
            t('language_set', lang),
            reply_markup=ReplyKeyboardRemove()
        )
    
    #ASK COMMAND
    
    async def ask_medical(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        lang = context.user_data.get('language', 'en')
        query = ' '.join(context.args) if context.args else ''
        
        if not query:
            await update.message.reply_text("Usage: /ask <question>")
            return
        
        # Check for emergency keywords
        emergency_words = ['heart attack', 'stroke', 'bleeding', 'unconscious', 'not breathing',
                          'दिल का दौरा', 'स्ट्रोक', 'रक्तस्राव', 'बेहोश', 'सांस नहीं']
        if any(word in query.lower() for word in emergency_words):
            await update.message.reply_text(t('emergency', lang), parse_mode='Markdown')
            return
        
        # Check for blocked queries
        blocked = ['prescribe', 'diagnose', 'what medicine', 'मुझे दवा दें', 'निदान करें']
        if any(word in query.lower() for word in blocked):
            await update.message.reply_text(t('blocked', lang))
            return
        
        await update.message.reply_text(t('thinking', lang))
        response = get_ai_response(query, lang)
        await update.message.reply_text(response)
    
    #VISIT LOGGING
    
    async def start_log_visit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        lang = context.user_data.get('language', 'en')
        await update.message.reply_text(
            t('ask_patient_id', lang),
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardRemove()
        )
        return LOGGING_PATIENT_ID
    
    async def log_patient_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['patient_id'] = update.message.text
        lang = context.user_data.get('language', 'en')
        await update.message.reply_text(t('ask_age', lang), parse_mode='Markdown')
        return LOGGING_AGE
    
    async def log_age(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            age = int(update.message.text)
            context.user_data['age'] = age
            lang = context.user_data.get('language', 'en')
            categories = t('categories', lang)
            
            # Create keyboard with 2 buttons per row
            keyboard = []
            for i in range(0, len(categories), 2):
                row = categories[i:i+2]
                keyboard.append(row)
            
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=False, resize_keyboard=True)
            await update.message.reply_text(
                t('ask_category', lang),
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            return LOGGING_CATEGORY
        except ValueError:
            await update.message.reply_text("Please enter a valid number for age:")
            return LOGGING_AGE
    
    async def log_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['category'] = update.message.text
        lang = context.user_data.get('language', 'en')
        visit_types = t('visit_types', lang)
        
        keyboard = []
        for i in range(0, len(visit_types), 2):
            row = visit_types[i:i+2]
            keyboard.append(row)
        
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=False, resize_keyboard=True)
        await update.message.reply_text(
            t('ask_type', lang),
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return LOGGING_TYPE
    
    async def log_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['visit_type'] = update.message.text
        lang = context.user_data.get('language', 'en')
        
        await update.message.reply_text(
            t('ask_notes', lang),
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardRemove()
        )
        return LOGGING_NOTES
    
    async def log_notes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        notes = update.message.text if update.message.text != '/skip' else ''
        lang = context.user_data.get('language', 'en')
        
        visit_id = self.db.log_visit(
            patient_id=context.user_data['patient_id'],
            age=context.user_data['age'],
            category=context.user_data['category'],
            visit_type=context.user_data['visit_type'],
            notes=notes,
            asha_id=str(update.effective_user.id),
            language=lang
        )
        
        await update.message.reply_text(
            t('visit_logged', lang).format(
                visit_id,
                context.user_data['patient_id'],
                context.user_data['category'],
                context.user_data['visit_type']
            ),
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    #OTHER COMMANDS
    
    async def view_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("Usage: /view_logs <patient_id>")
            return
        
        patient_id = context.args[0]
        history = self.db.get_history(patient_id)
        
        if not history:
            lang = context.user_data.get('language', 'en')
            await update.message.reply_text(t('no_history', lang).format(patient_id))
            return
        
        response = f"📋 *History for {patient_id}:*\n\n"
        for visit in history:
            response += f"• {visit['timestamp'][:10]}: {visit['category']} ({visit['visit_type']})\n"
            if visit['notes']:
                response += f"  Notes: {visit['notes'][:30]}...\n"
        
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        asha_id = str(update.effective_user.id)
        stats = self.db.get_stats(asha_id)
        lang = context.user_data.get('language', 'en')
        
        await update.message.reply_text(
            t('stats', lang).format(stats['total_visits'], stats['unique_patients']),
            parse_mode='Markdown'
        )
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Operation cancelled.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    
    #SETUP HANDLERS
    
    def setup_handlers(self):
        # Basic commands
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("disclaimer", self.disclaimer))
        self.app.add_handler(CommandHandler("language", self.set_language))
        self.app.add_handler(CommandHandler("ask", self.ask_medical))
        self.app.add_handler(CommandHandler("view_logs", self.view_logs))
        self.app.add_handler(CommandHandler("stats", self.stats))
        
        # Language selection
        self.app.add_handler(MessageHandler(
            filters.Regex('^(English|हिन्दी)$'),
            self.language_selected
        ))
        
        # Visit logging conversation
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("log_visit", self.start_log_visit)],
            states={
                LOGGING_PATIENT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.log_patient_id)],
                LOGGING_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.log_age)],
                LOGGING_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.log_category)],
                LOGGING_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.log_type)],
                LOGGING_NOTES: [MessageHandler(filters.TEXT, self.log_notes)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)]
        )
        self.app.add_handler(conv_handler)
    
    def run(self):
        print("🤖 ASHA Sahayi Bot is starting...")
        print("✅ Bot is running! Test these commands on Telegram:")
        print("   /start - Welcome message")
        print("   /ask fever - Health information")
        print("   /log_visit - Log patient visit")
        print("   /language - Change language")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)

# START THE BOT

print("🔍 Initializing ASHA Sahayi Bot...")
print("=" * 50)

# Check configuration
if TELEGRAM_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
    print("❌ ERROR: Please set your TELEGRAM_TOKEN in the configuration section")
    print("Get it from @BotFather on Telegram")
elif not GEMINI_ENABLED:
    print("⚠️ WARNING: Gemini API key not set")
    print("Bot will use local health knowledge base (still works)")
    print("Get API key from: https://makersuite.google.com/app/apikey")
else:
    print("✅ Configuration: OK")
    print("✅ Telegram Token: Set")
    print("✅ Gemini API: Enabled")

print("\n" + "=" * 50)
print("🚀 Starting bot now...")
print("=" * 50)

try:
    bot = ASHABot(token=TELEGRAM_TOKEN)
    bot.run()
except Exception as e:
    print(f"❌ Error starting bot: {e}")
    print("\n💡 Troubleshooting:")
    print("1. Check your Telegram Token is correct")
    print("2. Make sure you have internet connection")
    print("3. Restart runtime and run again")