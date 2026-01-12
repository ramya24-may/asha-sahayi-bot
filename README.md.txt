ASHA SAHAYI BOT 

Overview
ASHA Sahayi Bot is a Telegram-based health assistance chatbot designed to support ASHA (Accredited Social Health Activist) workers in India.  
The bot provides **general health information**, **patient visit logging**, and **multilingual support** while strictly following ethical medical guidelines.

> Disclaimer: This bot does NOT provide medical diagnosis or prescriptions. It is for educational and informational purposes only.


Key Features
- General health information (WHO / Indian health guidelines)
- Emergency detection with immediate alerts
- Patient visit logging with SQLite database
- ASHA worker statistics (visits & unique patients)
- Multilingual support (English & Hindi)
- Privacy-first (local database, no cloud storage)


Technologies Used
- Python 3.x
- python-telegram-bot
- Google Gemini API (Generative AI)
- SQLite3
- nest-asyncio


Bot Commands
- `/start` – Welcome & instructions
- `/ask <question>` – Ask general health questions
- `/log_visit` – Log a patient visit
- `/view_logs <patient_id>` – View patient history
- `/stats` – View ASHA worker statistics
- `/language` – Switch language
- `/disclaimer` – Medical disclaimer


How to Run the Bot

1. Install dependencies


2. Add API Keys
Edit `bot.py` and add:
- Telegram Bot Token (from @BotFather)
- Gemini API Key (optional – fallback system available)

3. Run the bot


Ethical & Safety Considerations
- No diagnosis or prescription
- Emergency cases are redirected to official helplines (108)
- Medical disclaimer shown to users
- Designed strictly for educational use


Project Purpose
This project was developed as part of an **internship evaluation task** to demonstrate:
- Backend development
- Conversational bot design
- Ethical AI usage
- Healthcare-aware system design


Author
Developed by: Pinnamareddy Ramya Sri  
Role: B.Tech 2nd year Student / Software Engineering Intern Applicant



