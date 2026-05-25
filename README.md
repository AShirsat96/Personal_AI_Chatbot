Personal AI Portfolio Chatbot & Admin Dashboard
An intelligent, dual-application conversational AI system designed to act as a 24/7 recruiter and personal portfolio assistant.

Designed to engage hiring managers, answer detailed questions about professional experience, securely capture lead information, and track conversation analytics.

Overview
Traditional static portfolios rely on recruiters digging through text to find relevant skills. This project modernizes the job search by deploying an interactive, OpenAI-powered chatbot that intelligently retrieves context about my background, skills, and projects. It is paired with a secure, password-protected admin dashboard that tracks user interactions, conversation intents, and engagement metrics in real-time.

Features
Dual-Application Architecture: Separate Streamlit applications for the user-facing chat widget (designed for iframe embedding) and a secure admin panel for analytics and management.

Intelligent Intent Routing: Utilizes natural language understanding to detect user intent (e.g., hiring, skills, salary, contact) to provide highly targeted, conversational responses.

Serverless Cloud Synchronization: Innovatively uses the GitHub Gist API as a free, lightweight NoSQL JSON database to synchronize data (avatars, resumes, chat logs) between the widget and the admin panel.

Lead Generation & Contact Management: Automatically extracts and validates user emails and phone numbers, allowing recruiters to securely leave messages directly within the chat interface.

Robust Analytics Dashboard: Features Pandas-driven visualizations of user engagement (by hour, day, and intent), session tracking, and CSV/JSON export capabilities.

Tech Stack
Language: Python 3

Framework: Streamlit

LLM & NLP: OpenAI API (GPT-3.5-turbo), Regular Expressions

Data Processing & Analytics: Pandas, JSON

Cloud / Database: GitHub API (Gist)

Document Processing: PyPDF2, python-docx, BeautifulSoup4

Project Structure
.
├── Chat_Widget.py          # User-facing conversational AI application
├── admin_dashboard.py      # Secure analytics and configuration panel
├── requirements.txt        # Python dependencies
└── .streamlit/
    └── secrets.toml        # Environment variables and API keys


Installation
Clone the repository and install dependencies:
git clone https://github.com/AShirsat96/Personal_AI_Chatbot.git
cd Personal_AI_Chatbot
pip install -r requirements.txt

Configuration
This project requires Streamlit secrets to manage API keys and database connections. Create a .streamlit/secrets.toml file in your project root:
# .streamlit/secrets.toml
OPENAI_API_KEY = "your_openai_api_key_here"
GITHUB_TOKEN = "your_github_personal_access_token"
GIST_ID = "your_github_gist_id"
ADMIN_PASSWORD = "your_secure_admin_password"

Quick Start
To run the user-facing Chatbot Widget:
streamlit run Chat_Widget.py

To run the secure Admin Dashboard:
streamlit run admin_dashboard.py

Why This Project Matters
This project demonstrates:

- End-to-End Product Ownership: Designing both the client-facing product and the internal analytics tooling.

- Creative Problem Solving: Engineering a serverless, cross-application data synchronization method using GitHub Gists.

- Production-Ready ML Practices: Implementing robust error handling, session state management, and fallback routing to ensure AI systems degrade gracefully without breaking the user experience.
