import os
import streamlit as st
from typing import List, Dict, Optional
from datetime import datetime
import json
import re
import requests

# Environment setup
from dotenv import load_dotenv
load_dotenv()

def extract_name_from_input(user_input: str) -> Optional[str]:
    """Extract name from natural language input"""
    input_lower = user_input.lower().strip()
    
    # Remove common greetings and punctuation
    input_clean = re.sub(r'[^\w\s]', '', input_lower)
    
    # Common patterns for name introduction
    name_patterns = [
        r'(?:hello|hi|hey)\s+(?:my\s+name\s+is|i\s*am|i\'m)\s+(\w+)',
        r'(?:my\s+name\s+is|i\s*am|i\'m)\s+(\w+)',
        r'(?:hello|hi|hey)\s+(\w+)(?:\s+here)?',
        r'(?:this\s+is|its)\s+(\w+)',
        r'(\w+)\s+here',
        r'^(\w+)$'  # Just a single word (likely a name)
    ]
    
    for pattern in name_patterns:
        match = re.search(pattern, input_clean)
        if match:
            potential_name = match.group(1).strip()
            # Filter out common non-name words
            non_names = {
                'hello', 'hi', 'hey', 'good', 'morning', 'afternoon', 'evening',
                'my', 'name', 'is', 'am', 'im', 'this', 'its', 'here', 'there',
                'yes', 'no', 'ok', 'okay', 'sure', 'thanks', 'thank', 'you',
                'please', 'can', 'could', 'would', 'will', 'the', 'a', 'an'
            }
            
            if potential_name not in non_names and len(potential_name) >= 2:
                return potential_name.capitalize()
    
    return None

def extract_email_from_input(user_input: str) -> Optional[str]:
    """Extract email from natural language input"""
    # Look for email patterns
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    match = re.search(email_pattern, user_input)
    if match:
        return match.group(0).lower()
    
    return None

def is_valid_email(email: str) -> bool:
    """Simple email validation"""
    email = email.strip()
    if len(email) < 5 or email.count('@') != 1 or '.' not in email:
        return False
    parts = email.split('@')
    if len(parts) != 2:
        return False
    local, domain = parts
    return len(local) >= 1 and len(domain) >= 3 and '.' in domain

class GitHubGistDatabase:
    """Free shared database using GitHub Gist"""
    
    def __init__(self):
        # Get credentials from Streamlit secrets
        self.github_token = st.secrets.get("GITHUB_TOKEN", "")
        self.gist_id = st.secrets.get("GIST_ID", "")
        
        if not self.github_token or not self.gist_id:
            self.use_gist = False
        else:
            self.use_gist = True
            
        self.headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    def _load_gist_data(self) -> Dict:
        """Load current data from GitHub Gist"""
        if not self.use_gist:
            return self._get_local_data()
            
        try:
            response = requests.get(
                f"https://api.github.com/gists/{self.gist_id}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                gist_data = response.json()
                content = gist_data["files"]["chatbot_data.json"]["content"]
                return json.loads(content)
            else:
                return self._get_default_data()
                
        except Exception as e:
            st.warning(f"Error loading gist data: {str(e)}")
            return self._get_local_data()
    
    def _save_gist_data(self, data: Dict) -> bool:
        """Save data to GitHub Gist"""
        if not self.use_gist:
            return self._save_local_data(data)
            
        try:
            payload = {
                "files": {
                    "chatbot_data.json": {
                        "content": json.dumps(data, indent=2, default=str)
                    }
                }
            }
            
            response = requests.patch(
                f"https://api.github.com/gists/{self.gist_id}",
                headers=self.headers,
                json=payload
            )
            
            return response.status_code == 200
            
        except Exception as e:
            st.error(f"Error saving to gist: {str(e)}")
            return self._save_local_data(data)
    
    def _get_default_data(self) -> Dict:
        """Get default data structure"""
        return {
            "user_interactions": [],
            "conversations": [],
            "resume_content": None,
            "avatar_data": None,
            "app_settings": {},
            "last_updated": datetime.now().isoformat()
        }
    
    def _get_local_data(self) -> Dict:
        """Fallback to session state storage"""
        if "gist_data" not in st.session_state:
            st.session_state.gist_data = self._get_default_data()
        return st.session_state.gist_data
    
    def _save_local_data(self, data: Dict) -> bool:
        """Save to session state as fallback"""
        st.session_state.gist_data = data
        return True
    
    def save_user_interaction(self, name: str, email: str, session_id: str) -> bool:
        """Save user interaction"""
        try:
            data = self._load_gist_data()
            
            user_entry = {
                "timestamp": datetime.now().isoformat(),
                "name": name,
                "email": email,
                "session_id": session_id
            }
            
            data["user_interactions"].append(user_entry)
            data["last_updated"] = datetime.now().isoformat()
            
            return self._save_gist_data(data)
            
        except Exception as e:
            st.error(f"Error saving user interaction: {str(e)}")
            return False
    
    def log_conversation(self, session_id: str, user_message: str, bot_response: str, intent: str, user_name: str = "", user_email: str = "") -> bool:
        """Log conversation for analytics"""
        try:
            data = self._load_gist_data()
            
            conversation_entry = {
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id,
                "user_name": user_name,
                "user_email": user_email,
                "user_message": user_message,
                "bot_response": bot_response,
                "detected_intent": intent,
                "response_length": len(bot_response),
                "message_length": len(user_message)
            }
            
            if "conversations" not in data:
                data["conversations"] = []
            
            data["conversations"].append(conversation_entry)
            data["last_updated"] = datetime.now().isoformat()
            
            return self._save_gist_data(data)
            
        except Exception as e:
            return False
    
    def get_avatar(self) -> Optional[str]:
        """Get current avatar from shared database"""
        try:
            data = self._load_gist_data()
            avatar_data = data.get("avatar_data")
            
            if avatar_data:
                return avatar_data.get("avatar_base64")
            return None
            
        except Exception as e:
            return None

@st.cache_resource
def get_shared_db():
    """Get shared database instance"""
    return GitHubGistDatabase()

def save_user_info(name: str, email: str, session_id: str) -> bool:
    """Save user info to shared database"""
    db = get_shared_db()
    return db.save_user_interaction(name, email, session_id)

def log_conversation_to_dashboard(session_id: str, user_message: str, bot_response: str, intent: str, user_name: str = "", user_email: str = "") -> bool:
    """Log conversation to dashboard"""
    db = get_shared_db()
    return db.log_conversation(session_id, user_message, bot_response, intent, user_name, user_email)

def get_shared_avatar() -> Optional[str]:
    """Get avatar from shared database"""
    db = get_shared_db()
    return db.get_avatar()

class SmartHybridChatbot:
    """Intelligent hybrid chatbot"""
    
    def __init__(self):
        self.aniket_data = {
            "personal_info": {
                "name": "Aniket Shirsat",
                "current_status": "Master's student in Applied Data Science at Indiana University Indianapolis",
                "gpa": "4.0",
                "current_role": "Research Assistant at Indiana University"
            },
            "education": {
                "current": {
                    "degree": "Master's in Applied Data Science",
                    "university": "Indiana University Indianapolis", 
                    "gpa": "4.0",
                    "status": "In Progress"
                },
                "previous": {
                    "degree": "Master's in Management",
                    "university": "Singapore Management University",
                    "status": "Completed"
                }
            },
            "experience": {
                "current_role": "Research Assistant at Indiana University",
                "key_projects": [
                    {
                        "name": "Cultural Ambiguity Detection",
                        "result": "90% accuracy in cultural ambiguity detection models",
                        "domain": "Machine Learning, NLP"
                    },
                    {
                        "name": "Vessel Fuel Optimization", 
                        "result": "$1 million annual savings through ML optimization",
                        "impact": "5% fuel reduction across 50+ vessels"
                    }
                ]
            },
            "technical_skills": {
                "programming": ["Python", "R", "SQL"],
                "cloud_platforms": ["AWS", "Azure", "Google Cloud Platform (GCP)"],
                "ai_ml": ["Machine Learning", "Computer Vision", "Natural Language Processing", "Advanced Analytics"],
                "frameworks": ["Machine Learning Frameworks", "Data Analysis Tools"],
                "specializations": ["Cultural Ambiguity Detection", "Vessel Fuel Optimization", "AI-powered Solutions"]
            },
            "achievements": [
                "Perfect 4.0 GPA in Master's program",
                "90% accuracy in cultural ambiguity detection models", 
                "$1 million annual savings through ML optimization",
                "5% fuel reduction across 50+ vessels",
                "Research Assistant position while maintaining academic excellence"
            ],
            "leadership": [
                "Head of Outreach and Project Committee Lead - Data Science and Machine Learning Club",
                "Member of Indiana University Jaguars Rowing Club"
            ],
            "career_goals": "Actively seeking full-time opportunities in data science and machine learning roles",
            "unique_value": "Combines academic excellence with proven ability to deliver quantifiable business results"
        }
    
    def analyze_intent(self, user_input: str) -> str:
        """Analyze user intent"""
        input_lower = user_input.lower()
        
        if any(word in input_lower for word in ["hello", "hi", "hey"]) and len(input_lower.split()) <= 3:
            return "greeting"
        elif any(word in input_lower for word in ["thank", "thanks"]):
            return "thanks"
        elif any(word in input_lower for word in ["bye", "goodbye"]):
            return "goodbye"
        elif any(word in input_lower for word in ["hire", "why", "recommend", "choose"]):
            return "hiring"
        elif any(word in input_lower for word in ["skill", "technical", "programming"]):
            return "skills"
        elif any(word in input_lower for word in ["education", "degree", "gpa", "university"]):
            return "education"
        elif any(word in input_lower for word in ["experience", "work", "job"]):
            return "experience"
        elif any(word in input_lower for word in ["project", "research", "built"]):
            return "projects"
        elif any(word in input_lower for word in ["contact", "reach", "email"]):
            return "contact"
        else:
            return "general"
    
    def generate_response(self, user_input: str) -> tuple[str, str]:
        """Generate response based on intent"""
        intent = self.analyze_intent(user_input)
        
        if intent == "greeting":
            response = """Hello! I'm Aniket's AI assistant. I can help answer questions about his professional background, skills, and experience.

What would you like to know about him?"""
        
        elif intent == "hiring":
            response = f"""You should definitely consider Aniket! He's maintaining a perfect {self.aniket_data['education']['current']['gpa']} GPA while working as a {self.aniket_data['personal_info']['current_role']}.

His vessel fuel optimization project saved {self.aniket_data['experience']['key_projects'][1]['result']} and his cultural ambiguity detection work achieved {self.aniket_data['experience']['key_projects'][0]['result']}.

He's technically solid with {', '.join(self.aniket_data['technical_skills']['programming'])}, {', '.join(self.aniket_data['technical_skills']['cloud_platforms'])}, and hands-on experience with {', '.join(self.aniket_data['technical_skills']['ai_ml'])}."""
        
        elif intent == "skills":
            response = f"""Aniket has strong technical skills in {', '.join(self.aniket_data['technical_skills']['programming'])} and works with {', '.join(self.aniket_data['technical_skills']['cloud_platforms'])}.

His AI/ML experience includes {', '.join(self.aniket_data['technical_skills']['ai_ml'])}, and he's applied these in real projects with measurable business impact."""
        
        elif intent == "projects":
            response = f"""Aniket's working on fascinating projects:

1. Cultural Ambiguity Detection - achieved {self.aniket_data['experience']['key_projects'][0]['result']}
2. Vessel Fuel Optimization - delivering {self.aniket_data['experience']['key_projects'][1]['result']} with {self.aniket_data['experience']['key_projects'][1]['impact']}

Both projects solve real problems with measurable outcomes."""
        
        elif intent == "contact":
            response = f"""Aniket is {self.aniket_data['career_goals'].lower()}, so he's open to conversations about opportunities.

The best way to reach him would be through his professional channels - LinkedIn or university contacts. He's particularly interested in positions where he can apply his ML and optimization skills to real business challenges."""
        
        else:
            response = f"""Aniket Shirsat is currently pursuing his {self.aniket_data['education']['current']['degree']} with a perfect {self.aniket_data['education']['current']['gpa']} GPA while working as a {self.aniket_data['personal_info']['current_role']}.

He's delivered real business impact including {self.aniket_data['achievements'][2]} and {self.aniket_data['achievements'][1]}.

What specific aspect would you like to know more about?"""
            
        return response, intent

def main():
    """Clean chatbot with NO suggested questions"""
    st.set_page_config(
        page_title="Chat with Aniket's AI Assistant",
        page_icon="💬",
        layout="centered"
    )
    
    # Clean CSS - NO suggestion styling
    st.markdown("""
    <style>
        .stApp {
            margin: 0 !important;
            padding: 0 !important;
            background: #f5f7fa;
        }
        
        .stApp > header {
            visibility: hidden !important;
            height: 0 !important;
        }
        
        .block-container {
            padding: 0 !important;
            margin: 0 !important;
            max-width: 100% !important;
        }
        
        .stDeployButton {display: none !important;}
        #MainMenu {visibility: hidden !important;}
        footer {visibility: hidden !important;}
        
        .chat-container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
            max-width: 420px;
            margin: 0 auto;
            border: 1px solid #e1e8ed;
        }
        
        .chat-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .chat-avatar {
            width: 50px;
            height: 50px;
            border-radius: 50%;
            border: 3px solid rgba(255,255,255,0.3);
        }
        
        .chat-title h3 {
            margin: 0;
            font-size: 18px;
            font-weight: 600;
        }
        
        .message-container {
            padding: 15px 20px;
            max-height: 450px;
            overflow-y: auto;
        }
        
        .assistant-message {
            display: flex;
            align-items: flex-start;
            margin-bottom: 15px;
            gap: 10px;
        }
        
        .message-bubble {
            background: #f1f3f5;
            padding: 12px 16px;
            border-radius: 18px;
            max-width: 320px;
            font-size: 14px;
            line-height: 1.4;
        }
        
        .user-message {
            display: flex;
            justify-content: flex-end;
            margin-bottom: 15px;
        }
        
        .user-bubble {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 16px;
            border-radius: 18px;
            max-width: 320px;
            font-size: 14px;
            line-height: 1.4;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize
    if "chatbot" not in st.session_state:
        st.session_state.chatbot = SmartHybridChatbot()
    
    if "session_id" not in st.session_state:
        st.session_state.session_id = f"clean_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    if "user_info_collected" not in st.session_state:
        st.session_state.user_info_collected = False
    if "asking_for_name" not in st.session_state:
        st.session_state.asking_for_name = False
    if "asking_for_email" not in st.session_state:
        st.session_state.asking_for_email = False
    if "user_name" not in st.session_state:
        st.session_state.user_name = ""
    if "user_email" not in st.session_state:
        st.session_state.user_email = ""
    
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant", 
                "content": "Hello! I'm Aniket's AI Assistant. I can help answer questions about his professional background, skills, and experience."
            },
            {
                "role": "assistant", 
                "content": "To get started, may I please have your name?"
            }
        ]
        st.session_state.asking_for_name = True
    
    # Chat UI
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    # Header
    shared_avatar = get_shared_avatar()
    avatar_src = shared_avatar if shared_avatar else "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNTAiIGhlaWdodD0iNTAiIHZpZXdCb3g9IjAgMCA1MCA1MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iMjUiIGN5PSIyNSIgcj0iMjUiIGZpbGw9IiM2NjdlZWEiLz4KPHN2ZyB4PSIxMiIgeT0iMTIiIHdpZHRoPSIyNiIgaGVpZ2h0PSIyNiIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPgo8cGF0aCBkPSJNMTIgMTJDMTQuNzYxNCAxMiAxNyA5Ljc2MTQyIDE3IDdDMTcgNC4yMzg1OCAxNC43NjE0IDIgMTIgMkM5LjIzODU4IDIgNyA0LjIzODU4IDcgN0M3IDkuNzYxNDIgOS4yMzg1OCAxMiAxMiAxMlpNMTIgMTRDOC42ODYyOSAxNCA2IDE2LjIzODYgNiAxOUg2QzYgMjEuNzYxNCA4LjIzODU4IDI0IDExIDI0SDEzQzE1Ljc2MTQgMjQgMTggMjEuNzYxNCAxOCAxOUg2QzYgMTYuMjM4NiA5LjMxMzcxIDE0IDEyIDE0WiIgZmlsbD0id2hpdGUiLz4KPC9zdmc+Cjwvc3ZnPgo="
    
    st.markdown(f"""
    <div class="chat-header">
        <img src="{avatar_src}" class="chat-avatar" alt="Avatar">
        <div class="chat-title">
            <h3>Aniket's AI Assistant</h3>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Messages
    st.markdown('<div class="message-container">', unsafe_allow_html=True)
    
    for message in st.session_state.messages:
        if message["role"] == "assistant":
            bot_avatar = f'<img src="{avatar_src}" style="width: 35px; height: 35px; border-radius: 50%; object-fit: cover;">' if shared_avatar else '<div style="width: 35px; height: 35px; background: #667eea; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 18px;">🤖</div>'
            
            st.markdown(f"""
            <div class="assistant-message">
                {bot_avatar}
                <div class="message-bubble">{message["content"]}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="user-message">
                <div class="user-bubble">{message["content"]}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)  # Close message-container
    st.markdown('</div>', unsafe_allow_html=True)  # Close chat-container
    
    # ============================================
    # CHAT INPUT ONLY - NO SUGGESTED QUESTIONS!!!
    # ============================================
    
    if st.session_state.asking_for_name:
        placeholder = "Enter your name..."
    elif st.session_state.asking_for_email:
        placeholder = "Enter your email address..."
    else:
        placeholder = "Ask about Aniket's skills, experience, projects, or why you should hire him..."
    
    if prompt := st.chat_input(placeholder):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        if st.session_state.asking_for_name:
            extracted_name = extract_name_from_input(prompt)
            
            if extracted_name:
                st.session_state.user_name = extracted_name
                st.session_state.asking_for_name = False
                st.session_state.asking_for_email = True
                response = f"Thank you, {st.session_state.user_name}! Could you please share your email address?"
                st.session_state.messages.append({"role": "assistant", "content": response})
            else:
                response = "I didn't catch your name. Could you please tell me your name?"
                st.session_state.messages.append({"role": "assistant", "content": response})
        
        elif st.session_state.asking_for_email:
            extracted_email = extract_email_from_input(prompt)
            
            if extracted_email and is_valid_email(extracted_email):
                st.session_state.user_email = extracted_email
                st.session_state.asking_for_email = False
                st.session_state.user_info_collected = True
                
                save_user_info(st.session_state.user_name, st.session_state.user_email, st.session_state.session_id)
                
                response = f"Perfect! Thank you, {st.session_state.user_name}. I'm ready to answer questions about Aniket's professional background. What would you like to know?"
                st.session_state.messages.append({"role": "assistant", "content": response})
            
            elif is_valid_email(prompt.strip()):
                st.session_state.user_email = prompt.strip()
                st.session_state.asking_for_email = False
                st.session_state.user_info_collected = True
                
                save_user_info(st.session_state.user_name, st.session_state.user_email, st.session_state.session_id)
                
                response = f"Perfect! Thank you, {st.session_state.user_name}. I'm ready to answer questions about Aniket's professional background. What would you like to know?"
                st.session_state.messages.append({"role": "assistant", "content": response})
            
            else:
                response = "That doesn't look like a valid email address. Please enter your email (e.g., john@company.com)."
                st.session_state.messages.append({"role": "assistant", "content": response})
        
        else:
            # Normal chat
            with st.spinner("🤖 Analyzing your question..."):
                response, intent = st.session_state.chatbot.generate_response(prompt)
            
            st.session_state.messages.append({"role": "assistant", "content": response})
            
            log_conversation_to_dashboard(
                st.session_state.session_id,
                prompt,
                response,
                intent,
                st.session_state.user_name,
                st.session_state.user_email
            )
        
        st.rerun()

if __name__ == "__main__":
    main()
