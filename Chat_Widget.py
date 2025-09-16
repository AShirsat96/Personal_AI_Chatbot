import os
import streamlit as st
from typing import List, Dict, Optional
from datetime import datetime, timezone
import json
import re
import requests
import pytz

# Environment setup
from dotenv import load_dotenv
load_dotenv()

# Updated OpenAI import (v1.0+ compatible)
from openai import OpenAI

# EDT timezone setup
EDT = pytz.timezone('US/Eastern')

def get_edt_timestamp() -> str:
    """Get current timestamp in EDT timezone"""
    return datetime.now(EDT).isoformat()

def get_edt_datetime() -> datetime:
    """Get current datetime in EDT timezone"""
    return datetime.now(EDT)

# OpenAI client setup
@st.cache_resource
def get_openai_client():
    """Get OpenAI client instance"""
    api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
    if api_key:
        return OpenAI(api_key=api_key)
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
    """Free shared database using GitHub Gist with EDT timezone support"""
    
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
            "messages_for_aniket": [],
            "conversation_threads": [],
            "last_updated": get_edt_timestamp()
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
        """Save user interaction with EDT timestamp"""
        try:
            data = self._load_gist_data()
            
            edt_now = get_edt_datetime()
            
            user_entry = {
                "timestamp": get_edt_timestamp(),
                "timestamp_edt": edt_now.strftime('%Y-%m-%d %H:%M:%S %Z'),
                "name": name,
                "email": email,
                "session_id": session_id
            }
            
            data["user_interactions"].append(user_entry)
            data["last_updated"] = get_edt_timestamp()
            
            return self._save_gist_data(data)
            
        except Exception as e:
            st.error(f"Error saving user interaction: {str(e)}")
            return False
    
    def log_conversation(self, session_id: str, user_message: str, bot_response: str, intent: str, user_name: str = "", user_email: str = "") -> bool:
        """Log conversation for analytics with EDT timestamp"""
        try:
            data = self._load_gist_data()
            
            edt_now = get_edt_datetime()
            
            conversation_entry = {
                "timestamp": get_edt_timestamp(),
                "timestamp_edt": edt_now.strftime('%Y-%m-%d %H:%M:%S %Z'),
                "date": edt_now.strftime('%Y-%m-%d'),
                "time": edt_now.strftime('%H:%M:%S'),
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
            data["last_updated"] = get_edt_timestamp()
            
            return self._save_gist_data(data)
            
        except Exception as e:
            return False
    
    def save_message_for_aniket(self, user_name: str, user_email: str, message_content: str, contact_info: str = "") -> bool:
        """Save messages left for Aniket with EDT timestamp"""
        try:
            data = self._load_gist_data()
            
            edt_now = get_edt_datetime()
            
            message_entry = {
                "timestamp": get_edt_timestamp(),
                "timestamp_edt": edt_now.strftime('%Y-%m-%d %H:%M:%S %Z'),
                "user_name": user_name,
                "user_email": user_email,
                "message_content": message_content,
                "contact_info": contact_info,
                "status": "unread",
                "session_id": st.session_state.get('session_id', '')
            }
            
            if "messages_for_aniket" not in data:
                data["messages_for_aniket"] = []
            
            data["messages_for_aniket"].append(message_entry)
            data["last_updated"] = get_edt_timestamp()
            
            return self._save_gist_data(data)
            
        except Exception as e:
            st.error(f"Error saving message: {str(e)}")
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

def save_message_for_aniket(user_name: str, user_email: str, message_content: str, contact_info: str = "") -> bool:
    """Save message for Aniket to shared database"""
    db = get_shared_db()
    return db.save_message_for_aniket(user_name, user_email, message_content, contact_info)

def get_shared_avatar() -> Optional[str]:
    """Get avatar from shared database"""
    db = get_shared_db()
    return db.get_avatar()

class SmartHybridChatbot:
    """Intelligent hybrid chatbot with OpenAI integration"""
    
    def __init__(self):
        # Comprehensive knowledge base about Aniket
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
            "unique_value": "Combines academic excellence with proven ability to deliver quantifiable business results",
            "contact": {
                "email": "ashirsat@iu.edu",
                "phone": "+1 463 279 6071",
                "linkedin": "https://www.linkedin.com/in/aniketshirsatsg/",
                "github": "https://github.com/AShirsat96"
            }
        }
        
        # System prompt for OpenAI
        self.system_prompt = """You are Aniket Shirsat's AI assistant. Your role is to help people learn about Aniket's professional background and qualifications in a natural, conversational way.

Key guidelines:
- Keep responses concise and natural (2-3 sentences max)
- Sound like a helpful human assistant, not an AI
- Focus on the specific question asked
- Always base responses on the provided data about Aniket
- Be professional but conversational
- If asked about topics not covered in Aniket's data, politely redirect to his areas of expertise

You should help with questions about:
- His skills and technical abilities
- Educational background  
- Work experience and projects
- Why someone should hire him
- His availability and contact information
- Personal interests and leadership experience

Always use the factual information provided about Aniket to answer questions accurately."""
        
        # Conversation patterns for natural interaction
        self.conversation_patterns = {
            "greetings": ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"],
            "thanks": ["thank", "thanks", "appreciate", "grateful"],
            "goodbye": ["bye", "goodbye", "see you", "farewell", "take care"],
            "satisfaction": ["perfect", "great", "excellent", "awesome", "got it", "understood", "clear", "helpful"],
            "conversation_enders": ["that's all", "that covers it", "no more questions", "nothing else", "all set", "that's everything"]
        }
        
        # Question intent patterns
        self.intent_patterns = {
            "hiring": ["hire", "why", "recommend", "choose", "recruit", "employ", "candidate", "fit", "right person"],
            "skills": ["skill", "technical", "programming", "tech", "abilities", "competencies", "expertise", "tools", "technologies"],
            "education": ["education", "school", "degree", "gpa", "university", "academic", "study", "learn", "college"],
            "experience": ["experience", "work", "job", "employment", "career", "professional", "background", "history"],
            "projects": ["project", "research", "built", "created", "developed", "worked on", "achievement", "accomplishment"],
            "personal": ["hobby", "hobbies", "interest", "interests", "personal", "outside work", "free time", "activities"],
            "contact": ["contact", "reach", "connect", "email", "phone", "linkedin", "get in touch", "hire him"],
            "availability": ["available", "start", "when", "timeline", "notice", "free", "open to"],
            "salary": ["salary", "compensation", "pay", "money", "cost", "rate", "price"],
            "location": ["location", "where", "based", "remote", "relocate", "move"],
            "company_culture": ["culture", "team", "environment", "fit", "values", "work style"],
            "future": ["future", "goals", "plans", "career path", "ambition", "vision"]
        }
    
    def get_openai_response(self, user_question: str, intent: str, context: Dict[str, bool]) -> str:
        """Generate response using OpenAI API"""
        try:
            client = get_openai_client()
            if not client:
                return self.get_fallback_response(intent)
                
            # Create context-specific prompt based on intent
            if intent == "skills":
                context_data = f"""Technical Skills: {', '.join(self.aniket_data['technical_skills']['programming'])}, {', '.join(self.aniket_data['technical_skills']['cloud_platforms'])}, {', '.join(self.aniket_data['technical_skills']['ai_ml'])}
Business Impact: His ML projects have delivered over $1 million in annual savings"""
            
            elif intent == "education":
                context_data = f"""Current: {self.aniket_data['education']['current']['degree']} at {self.aniket_data['education']['current']['university']} (GPA: {self.aniket_data['education']['current']['gpa']})
Previous: {self.aniket_data['education']['previous']['degree']} from {self.aniket_data['education']['previous']['university']}"""
            
            elif intent == "experience":
                context_data = f"""Current Role: {self.aniket_data['experience']['current_role']}
Key Projects: 
1. {self.aniket_data['experience']['key_projects'][0]['name']} - {self.aniket_data['experience']['key_projects'][0]['result']}
2. {self.aniket_data['experience']['key_projects'][1]['name']} - {self.aniket_data['experience']['key_projects'][1]['result']}
Leadership: {', '.join(self.aniket_data['leadership'])}"""
            
            elif intent == "projects":
                context_data = f"""Projects:
1. Cultural Ambiguity Detection: {self.aniket_data['experience']['key_projects'][0]['result']} using ML and NLP
2. Vessel Fuel Optimization: {self.aniket_data['experience']['key_projects'][1]['result']} with {self.aniket_data['experience']['key_projects'][1]['impact']}"""
            
            elif intent == "hiring":
                context_data = f"""Why hire Aniket:
- Perfect {self.aniket_data['education']['current']['gpa']} GPA while working as {self.aniket_data['experience']['current_role']}
- Proven business impact: {self.aniket_data['experience']['key_projects'][1]['result']}
- Technical skills: {', '.join(self.aniket_data['technical_skills']['programming'])}, {', '.join(self.aniket_data['technical_skills']['cloud_platforms'])}
- Leadership: {self.aniket_data['leadership'][0]}"""
            
            elif intent == "contact":
                context_data = f"""Contact Information:
Email: {self.aniket_data['contact']['email']}
Phone: {self.aniket_data['contact']['phone']}
LinkedIn: {self.aniket_data['contact']['linkedin']}
GitHub: {self.aniket_data['contact']['github']}"""
            
            elif intent == "personal":
                context_data = f"""Personal/Leadership:
- {self.aniket_data['leadership'][0]}
- {self.aniket_data['leadership'][1]}
- Interests: AI/ML applications, solving complex business challenges"""
            
            elif intent == "availability":
                context_data = f"""Availability: {self.aniket_data['career_goals']}
Currently completing Master's degree while working as Research Assistant
Available for interviews immediately, flexible with start dates"""
            
            else:
                # General context for other intents
                context_data = f"""Aniket Shirsat Overview:
- {self.aniket_data['personal_info']['current_status']} (GPA: {self.aniket_data['personal_info']['gpa']})
- {self.aniket_data['personal_info']['current_role']}
- Key achievement: {self.aniket_data['experience']['key_projects'][1]['result']}
- Skills: {', '.join(self.aniket_data['technical_skills']['programming'])}, {', '.join(self.aniket_data['technical_skills']['cloud_platforms'])}"""
            
            # Create the prompt
            prompt = f"""Based on this information about Aniket:

{context_data}

User question: "{user_question}"

Provide a natural, conversational response (2-3 sentences max) that directly answers their question. Sound like a helpful human assistant recommending Aniket."""

            # Call OpenAI API with updated format
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            # Fallback to predefined responses if OpenAI fails
            st.warning(f"OpenAI API error: {str(e)}")
            return self.get_fallback_response(intent)
    
    def get_fallback_response(self, intent: str) -> str:
        """Fallback responses when OpenAI API fails"""
        fallback_responses = {
            "skills": "Aniket is proficient in Python, R, and SQL, with experience in AWS, Azure, and Google Cloud. His ML projects have delivered over $1 million in annual savings.",
            "education": "Aniket has a Master's in Applied Data Science from Indiana University Indianapolis with a 4.0 GPA, plus a Master's in Management from Singapore Management University.",
            "experience": "Aniket works as a Research Assistant at Indiana University. His vessel optimization project saved over $1 million annually, and his cultural detection models achieve 90% accuracy.",
            "projects": "Aniket built cultural ambiguity detection models with 90% accuracy and vessel optimization algorithms that save $1M+ annually across 50+ vessels.",
            "hiring": "I'd recommend Aniket for his perfect 4.0 GPA, proven $1M+ business impact from ML projects, and strong technical skills in Python, R, SQL, and cloud platforms.",
            "contact": f"You can reach Aniket at {self.aniket_data['contact']['email']}, call {self.aniket_data['contact']['phone']}, or connect on LinkedIn at {self.aniket_data['contact']['linkedin']}",
            "personal": "Aniket leads the Data Science Club and rows for Indiana University. The combination of leadership and athletic discipline shows he works well under pressure.",
            "availability": "Aniket is available immediately for interviews and flexible with start dates. He's actively seeking data science opportunities."
        }
        
        return fallback_responses.get(intent, "I'd be happy to tell you more about Aniket's background. What specific aspect interests you?")
    
    def use_openai_for_response(self) -> bool:
        """Check if OpenAI API should be used"""
        client = get_openai_client()
        return client is not None
    
    def should_offer_conversation_closure(self, user_input: str, message_count: int) -> bool:
        """Determine if we should offer to end the conversation"""
        input_lower = user_input.lower().strip()
        
        # Check for satisfaction/completion signals
        satisfaction_signals = any(word in input_lower for word in self.conversation_patterns["satisfaction"])
        thanks_signals = any(word in input_lower for word in self.conversation_patterns["thanks"])
        ending_signals = any(phrase in input_lower for phrase in self.conversation_patterns["conversation_enders"])
        
        # Check for conversation length (offer closure after comprehensive responses)
        long_conversation = message_count >= 8
        
        # Check for specific closure indicators
        closure_phrases = [
            "that answers my question", "that helps", "that's what I needed",
            "got all the info", "all the information", "covers everything",
            "that's sufficient", "that works", "sounds good"
        ]
        specific_closure = any(phrase in input_lower for phrase in closure_phrases)
        
        return (satisfaction_signals and thanks_signals) or ending_signals or specific_closure or long_conversation
    
    def detect_conversation_ending_intent(self, user_input: str) -> str:
        """Detect if user wants to end conversation"""
        input_lower = user_input.lower().strip()
        
        # Strong ending signals
        ending_phrases = [
            "no", "no more", "no other", "no further", "nothing else", "nothing more",
            "that's all", "that's it", "all set", "i'm good", "i'm all set",
            "end conversation", "end chat", "stop", "quit", "exit", "done",
            "that covers it", "that's everything", "sufficient", "enough"
        ]
        
        if any(phrase in input_lower for phrase in ending_phrases):
            return "end_conversation"
        
        # Continuation signals
        continue_phrases = [
            "yes", "yeah", "yep", "sure", "actually", "also", "one more",
            "another question", "what about", "can you tell me", "i'd like to know"
        ]
        
        if any(phrase in input_lower for phrase in continue_phrases):
            return "continue_conversation"
        
        return "unclear"
    
    def get_conversation_closure_offer(self) -> str:
        """Offer to close the conversation naturally"""
        return """Is there anything else you'd like to know about Aniket? 

Or if you have all the information you need, I can end our conversation here."""
    
    def get_conversation_ending_response(self, user_name: str = "") -> str:
        """Provide a natural conversation ending"""
        name_part = f" {user_name}" if user_name else ""
        
        return f"""Perfect! Thank you{name_part} for your interest in Aniket Shirsat. 

To connect with him directly:
📧 Email: ashirsat@iu.edu
🔗 LinkedIn: https://www.linkedin.com/in/aniketshirsatsg/

Feel free to start a new conversation anytime. Have a great day! 👋"""
    
    def get_conversation_continuation_response(self) -> str:
        """Response when user wants to continue"""
        return """Great! What else would you like to know about Aniket?"""
    
    def analyze_intent(self, user_input: str) -> str:
        """Analyze user intent from input with enhanced natural language understanding"""
        input_lower = user_input.lower().strip()
        
        # Handle empty or very short inputs
        if len(input_lower) < 2:
            return "general"
        
        # Enhanced message for contact detection - moved higher in priority
        if (any(phrase in input_lower for phrase in [
            "leave a message", "message for him", "ask him to contact", "have him call",  
            "get back to me", "follow up", "reach out to me", "contact me back",
            "call me back", "email me back", "get in touch with me", "message me",
            "have him reach out", "ask him to reach out", "tell him to call",
            "let him know", "pass along", "forward this", "send this to him"
        ]) or 
        (any(word in input_lower for word in ["my number", "my phone", "call me", "reach me", "contact me"]) and 
         any(char.isdigit() for char in user_input)) or
        (re.search(r'(\+?\d{1,4}[-.\s]?\(?\d{1,3}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9})', user_input) and
         any(word in input_lower for word in ["call", "contact", "reach", "message", "text"]))):
            return "message_for_contact"
        
        # First check for specific question patterns - be more specific about greetings
        elif any(word in input_lower for word in ["hello", "hi", "hey"]) and len(input_lower.split()) <= 3 and not any(word in input_lower for word in ["skill", "project", "hire", "experience", "hobby", "personal"]):
            return "greeting"
        elif any(pattern in input_lower for pattern in ["thank", "thanks", "appreciate", "grateful"]) and not any(word in input_lower for word in ["skill", "project", "hire", "experience", "hobby", "personal"]):
            return "thanks"
        elif any(pattern in input_lower for pattern in ["bye", "goodbye", "see you", "farewell", "take care", "exit", "quit"]):
            return "goodbye"
        
        # Enhanced question patterns - check PERSONAL/HOBBIES FIRST before other patterns
        elif any(word in input_lower for word in ["hobby", "hobbies", "interest", "interests", "personal", "outside work", "free time", "activities", "personality", "rowing", "sports", "extracurricular", "club", "clubs", "passion", "enjoys", "recreation", "leisure"]):
            return "personal"
        
        # Hiring and recommendation questions - expanded keywords
        elif any(word in input_lower for word in ["hire", "hiring", "recruit", "recruiting", "employment", "why choose", "why select", "recommend", "recommendation", "choose", "employ", "candidate", "should we", "should i", "good choice", "worth it", "benefit", "advantages", "why him", "best fit", "suitable", "right person", "good candidate", "hire him", "employ him"]):
            return "hiring"
        
        # Skills and technical abilities - expanded
        elif any(word in input_lower for word in ["skill", "skills", "technical", "programming", "tech", "abilities", "competencies", "expertise", "tools", "technologies", "what can he do", "good at", "proficient", "capabilities", "knowledge", "knows", "familiar with", "experienced in", "coding", "development", "software", "languages", "frameworks", "platforms"]):
            return "skills"
        
        # Education and academic background - expanded
        elif any(word in input_lower for word in ["education", "educational", "school", "degree", "degrees", "gpa", "university", "academic", "academics", "study", "studied", "college", "qualification", "qualifications", "background", "learning", "courses", "curriculum", "major", "minor", "thesis", "research", "graduate", "undergraduate", "masters", "bachelor"]):
            return "education"
        
        # Work experience and career - expanded
        elif any(word in input_lower for word in ["experience", "work", "job", "jobs", "employment", "career", "professional", "background", "history", "worked at", "previous", "past", "role", "roles", "position", "positions", "employer", "company", "companies", "internship", "internships"]):
            return "experience"
        
        # Projects and achievements - expanded
        elif any(word in input_lower for word in ["project", "projects", "research", "built", "created", "developed", "worked on", "achievement", "achievements", "accomplishment", "accomplishments", "portfolio", "examples", "work samples", "case study", "success", "results", "outcomes", "impact", "contribution", "contributions"]):
            return "projects"
        
        # Contact and reaching out - expanded
        elif any(word in input_lower for word in ["contact", "reach", "connect", "email", "phone", "linkedin", "get in touch", "how to reach", "communication", "contact info", "contact information", "reach out", "get hold", "find him", "connect with"]):
            return "contact"
        
        # Conversation flow management - NEW
        elif st.session_state.get('awaiting_closure_response', False):
            ending_intent = self.detect_conversation_ending_intent(user_input)
            if ending_intent == "end_conversation":
                return "end_conversation"
            elif ending_intent == "continue_conversation":
                return "continue_conversation"
            else:
                return "general"
        
        # Availability and timing - expanded
        elif any(word in input_lower for word in ["available", "availability", "start", "starting", "when", "timeline", "notice", "free", "ready to work", "ready", "can start", "join", "begin", "commence", "timing", "schedule"]):
            return "availability"
        
        # Salary and compensation - expanded
        elif any(word in input_lower for word in ["salary", "compensation", "pay", "payment", "money", "cost", "rate", "price", "how much", "budget", "wage", "income", "package", "benefits", "remuneration", "fee", "charge"]):
            return "salary"
        
        # Location and work arrangement - expanded
        elif any(word in input_lower for word in ["location", "where", "based", "remote", "relocate", "move", "lives", "located", "office", "onsite", "hybrid", "work from home", "place", "city", "country", "address", "geography", "willing to relocate"]):
            return "location"
        
        # Company culture and fit - expanded
        elif any(word in input_lower for word in ["culture", "team", "environment", "fit", "values", "work style", "team player", "collaborative", "personality", "attitude", "work ethic", "cultural fit", "team fit", "working style", "approach"]):
            return "company_culture"
        
        # Future goals and career plans - expanded
        elif any(word in input_lower for word in ["future", "goals", "plans", "career path", "ambition", "ambitions", "vision", "aspirations", "long term", "growth", "objectives", "aims", "direction", "next steps", "where see himself", "5 years", "10 years"]):
            return "future"
        
        # Catch common question words that might not fit other categories
        elif any(word in input_lower for word in ["who is", "what is", "tell me about", "describe", "explain", "information", "details", "about him", "about aniket", "overview", "summary", "profile"]):
            return "general"
        
        else:
            return "general"
    
    def extract_context(self, user_input: str) -> Dict[str, bool]:
        """Extract additional context from user input"""
        input_lower = user_input.lower()
        
        return {
            "wants_details": any(word in input_lower for word in ["detail", "specific", "more", "tell me more", "elaborate"]),
            "is_comparison": any(word in input_lower for word in ["vs", "versus", "compare", "better than", "different"]),
            "is_urgent": any(word in input_lower for word in ["urgent", "asap", "immediate", "quickly", "soon"]),
            "is_formal": any(word in input_lower for word in ["professional", "formal", "business", "corporate"]),
            "wants_examples": any(word in input_lower for word in ["example", "instance", "case", "sample"])
        }
    
    def generate_response(self, user_input: str) -> tuple[str, str]:
        """Generate intelligent response using OpenAI or fallback methods"""
        intent = self.analyze_intent(user_input)
        context = self.extract_context(user_input)
        
        # Add conversational context awareness
        input_lower = user_input.lower()
        is_casual = any(word in input_lower for word in ["hey", "hi", "what's up", "sup", "cool", "awesome", "nice"])
        is_formal = any(word in input_lower for word in ["please", "could you", "would you", "may I", "thank you very much"])
        
        # Use OpenAI for main conversation intents, fallback for system intents
        system_intents = ["greeting", "thanks", "goodbye", "end_conversation", "continue_conversation"]
        
        if intent in system_intents:
            # Use predefined responses for system interactions
            if intent == "greeting":
                response = self.get_greeting_response(is_casual)
            elif intent == "thanks":
                response = self.get_thanks_response(is_casual)
            elif intent == "goodbye":
                response = self.get_goodbye_response(is_casual)
            elif intent == "end_conversation":
                response = self.get_conversation_ending_response(st.session_state.get('user_display_name', ''))
            elif intent == "continue_conversation":
                response = self.get_conversation_continuation_response()
                st.session_state.awaiting_closure_response = False
        else:
            # Use OpenAI for content-based responses
            if self.use_openai_for_response():
                try:
                    response = self.get_openai_response(user_input, intent, context)
                except Exception as e:
                    st.warning(f"OpenAI error, using fallback: {str(e)}")
                    response = self.get_fallback_response(intent)
            else:
                # Use predefined responses if no OpenAI API
                response = self.get_predefined_response(intent, context, is_casual, is_formal)
        
        # Check if we should offer conversation closure after the response
        message_count = len(st.session_state.messages) // 2
        if (self.should_offer_conversation_closure(user_input, message_count) and 
            not st.session_state.get('awaiting_closure_response', False)):
            response += "\n\n" + self.get_conversation_closure_offer()
            st.session_state.awaiting_closure_response = True
            
        return response, intent
    
    def get_predefined_response(self, intent: str, context: Dict[str, bool], is_casual: bool, is_formal: bool) -> str:
        """Get predefined response when OpenAI is not available"""
        if intent == "hiring":
            return self.get_hiring_response(context, is_casual, is_formal)
        elif intent == "skills":
            return self.get_skills_response(context, is_casual, is_formal)
        elif intent == "education":
            return self.get_education_response(context, is_casual, is_formal)
        elif intent == "experience":
            return self.get_experience_response(context, is_casual, is_formal)
        elif intent == "projects":
            return self.get_projects_response(context, is_casual, is_formal)
        elif intent == "personal":
            return self.get_personal_response(context, is_casual, is_formal)
        elif intent == "contact":
            return self.get_contact_response(context, is_casual, is_formal)
        elif intent == "message_for_contact":
            return self.handle_message_for_contact(user_input)
        elif intent == "availability":
            return self.get_availability_response(context, is_casual, is_formal)
        elif intent == "salary":
            return self.get_salary_response(context, is_casual, is_formal)
        elif intent == "location":
            return self.get_location_response(context, is_casual, is_formal)
        elif intent == "company_culture":
            return self.get_culture_response(context, is_casual, is_formal)
        elif intent == "future":
            return self.get_future_response(context, is_casual, is_formal)
        else:
            return self.get_general_response(is_casual)
    
    # SHORT AND NATURAL RESPONSE METHODS
    def get_greeting_response(self, is_casual: bool = False) -> str:
        return """Hello! I'm Aniket's AI assistant. 

Aniket is pursuing his Master's in Applied Data Science at Indiana University Indianapolis with a 4.0 GPA while working as a Research Assistant.

What would you like to know about him?"""
    
    def get_thanks_response(self, is_casual: bool = False) -> str:
        return """You're welcome! Happy to help you learn more about Aniket.

Is there anything else you'd like to know about his background or skills?"""
    
    def get_goodbye_response(self, is_casual: bool = False) -> str:
        return """Thank you for your interest in Aniket!

Feel free to reach out to him directly at ashirsat@iu.edu or connect on LinkedIn at https://www.linkedin.com/in/aniketshirsatsg/

Have a great day!"""
    
    def get_hiring_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return """I'd strongly recommend Aniket. He maintains a perfect 4.0 GPA while working as a Research Assistant, which shows he can handle multiple demanding responsibilities.

Most importantly, his ML projects have delivered real business impact - over $1 million in annual savings from vessel optimization work. He's proficient in Python, R, SQL, and cloud platforms like AWS and Azure.

He also brings leadership experience as Head of the Data Science Club. It's rare to find someone who combines academic excellence with proven business results."""
    
    def get_skills_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return """Aniket is proficient in Python, R, and SQL for programming. He has experience with AWS, Azure, and Google Cloud Platform for cloud computing.

His AI and machine learning expertise includes computer vision, natural language processing, and advanced analytics. What sets him apart is that he applies these skills to create real business value - his optimization projects have saved over $1 million annually."""
    
    def get_education_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return """Aniket is currently pursuing his Master's in Applied Data Science at Indiana University Indianapolis with a perfect 4.0 GPA. He also has a Master's in Management from Singapore Management University.

This combination gives him both technical depth and business strategy perspective, which is pretty uncommon among data science candidates."""
    
    def get_experience_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return """Aniket currently works as a Research Assistant at Indiana University while completing his Master's degree. He's developed cultural ambiguity detection models that achieve 90% accuracy for analyzing advertisements.

His most impressive project is vessel fuel optimization - he created predictive algorithms that generate over $1 million in annual savings and 5% fuel reduction across 50+ vessels. He's also Head of the Data Science Club and rows for the university team."""
    
    def get_projects_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return """Aniket has two standout projects. First, he built cultural ambiguity detection models using advanced NLP that achieve 90% accuracy for analyzing cultural sensitivity in advertisements.

Second, his vessel fuel optimization project uses predictive algorithms to optimize maritime fleet fuel consumption. This system operates across 50+ vessels and delivers over $1 million in annual savings with 5% fuel reduction. Both show he can turn technical skills into real business impact."""
    
    def get_personal_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return """Beyond his technical work, Aniket serves as Head of Outreach and Project Committee for the Data Science Club, showing his leadership abilities. He's also a member of the Indiana University Jaguars Rowing Club.

The combination of athletic discipline, community leadership, and technical expertise suggests someone who can perform under pressure and work well in teams."""
    
    def get_contact_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return """You can reach Aniket at ashirsat@iu.edu or call him at +1 463 279 6071. He's also on LinkedIn at https://www.linkedin.com/in/aniketshirsatsg/ and GitHub at https://github.com/AShirsat96.

He typically responds to professional inquiries within 1-2 business days."""
    
    def handle_message_for_contact(self, user_input: str) -> str:
        """Handle cases where users leave messages for Aniket to contact them"""
        # This will be overridden by the message collection flow in main()
        phone_pattern = r'(\+?\d{1,4}[-.\s]?\(?\d{1,3}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9})'
        phone_match = re.search(phone_pattern, user_input)
        
        if phone_match:
            phone_number = phone_match.group(1)
            return f"""I'd be happy to have Aniket contact you at {phone_number}! 

What message would you like me to pass along to him?"""
        else:
            return """I'd be happy to have Aniket contact you! 

What message would you like me to pass along to him, and what's the best way for him to reach you?"""
    
    def get_availability_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return """Aniket is available immediately for interviews and discussions. He's flexible with start dates and can accommodate your timeline.

Since he's actively job searching and ready to move quickly for the right opportunity, I'd recommend reaching out soon if you're interested."""
    
    def get_salary_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return """Aniket takes a professional approach to compensation. He focuses on finding the right role and growth opportunities rather than just maximizing salary.

Given his track record of delivering over $1 million in documented business impact, he's open to discussing competitive packages appropriate for his experience level."""
    
    def get_location_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return """Aniket is currently in Indianapolis for his studies at Indiana University, but he's very flexible with location. He's open to remote work, hybrid arrangements, or relocating for the right opportunity.

His international experience from Singapore Management University shows he adapts well to different environments."""
    
    def get_culture_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return """Aniket would fit well in data-driven organizations that value both innovation and measurable results. His perfect 4.0 GPA while doing research shows high performance standards, and his leadership roles demonstrate he works well collaboratively.

His international background and diverse experiences make him adaptable to different team cultures."""
    
    def get_future_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return """Short-term, Aniket wants to transition from academia into industry data science roles. Long-term, he's interested in technical leadership positions where he can bridge cutting-edge research with practical business solutions.

His management background combined with technical skills positions him well for future leadership roles."""
    
    def get_general_response(self, is_casual: bool = False) -> str:
        return f"""Aniket Shirsat is pursuing his Master's in Applied Data Science at Indiana University Indianapolis with a perfect 4.0 GPA while working as a Research Assistant.

His key highlights include over $1 million in business impact from ML projects, skills in Python, R, SQL, AWS, Azure, and GCP, plus leadership experience with the Data Science Club and rowing team.

He's currently seeking data science and machine learning opportunities where he can apply his combination of technical expertise and business understanding."""

def main():
    """Enhanced chatbot with simplified name collection and EDT timestamps"""
    st.set_page_config(
        page_title="Chat with Aniket's AI Assistant",
        page_icon="💬",
        layout="centered"
    )
    
    # Corrected CSS with more aggressive rules for a clean UI
    st.markdown("""
    <style>
        /* Complete app reset and layout */
        .stApp {
            margin: 0 !important;
            padding: 0 !important;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
        }
        
        /* Hide ALL Streamlit default elements */
        header, #MainMenu, footer, .stDeployButton {
            visibility: hidden !important;
            height: 0 !important;
            display: none !important;
        }
        
        .block-container {
            padding: 10px !important;
            margin: 0 !important;
            max-width: 100% !important;
        }
        
        /* AGGRESSIVE close button hiding - targeting iframe/embed elements */
        button[title="Close"], button[aria-label="Close"], .close-button, .close-btn, [class*="close"], [id*="close"], button:contains("✕"), button:contains("×"), button:contains("X") {
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
            pointer-events: none !important;
            position: absolute !important;
            left: -9999px !important;
            top: -9999px !important;
            width: 0 !important;
            height: 0 !important;
        }

        /* Hide any standalone X symbols */
        div:contains("✕"):not(.message-bubble):not(.user-bubble), div:contains("×"):not(.message-bubble):not(.user-bubble), span:contains("✕"), span:contains("×") {
            display: none !important;
        }

        /* Remove any containers that might hold close buttons */
        .element-container:has(button:contains("✕")), .element-container:has(button:contains("×")), .element-container:has(button[title="Close"]), .element-container:has(button[aria-label="Close"]) {
            display: none !important;
        }
        
        /* Chat container styling */
        .chat-container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.15);
            max-width: 450px;
            width: 100%;
            margin: 0 auto;
            border: 1px solid #e1e8ed;
            overflow: hidden;
        }
        
        .chat-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            display: flex;
            align-items: center;
            gap: 15px;
            position: relative;
        }
        
        .chat-header h3 {
            color: white !important; /* Force the header text color to white */
            margin: 0;
            font-size: 18px;
            font-weight: 600;
        }
        
        .chat-avatar {
            width: 50px;
            height: 50px;
            border-radius: 50%;
            border: 3px solid rgba(255,255,255,0.3);
            object-fit: cover;
        }
        
        .chat-subtitle {
            font-size: 12px;
            opacity: 0.9;
            margin-top: 2px;
        }
        
        .message-container {
            padding: 15px 20px;
            max-height: 450px;
            overflow-y: auto;
            background: #fafbfc;
        }
        
        .assistant-message {
            display: flex;
            align-items: flex-start;
            margin-bottom: 15px;
            gap: 10px;
        }
        
        .message-bubble {
            background: white;
            padding: 12px 16px;
            border-radius: 18px;
            max-width: 320px;
            font-size: 14px;
            line-height: 1.4;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            border: 1px solid #e1e8ed;
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
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        .email-buttons {
            display: flex;
            gap: 10px;
            justify-content: center;
            margin: 15px 0;
            flex-wrap: wrap;
        }
        
        .email-button {
            padding: 12px 24px;
            border: none;
            border-radius: 25px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            min-width: 120px;
            text-align: center;
        }
        
        .email-button.yes {
            background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
            color: white;
        }
        
        .email-button.yes:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(76,175,80,0.3);
        }
        
        .email-button.no {
            background: linear-gradient(135deg, #f44336 0%, #da190b 100%);
            color: white;
        }
        
        .email-button.no:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(244,67,54,0.3);
        }
        
        /* Mobile responsive */
        @media (max-width: 768px) {
            .chat-container {
                max-width: 95%;
                margin: 5px auto;
                border-radius: 15px;
            }
            
            .chat-header {
                padding: 15px;
            }
            
            .chat-avatar {
                width: 40px;
                height: 40px;
            }
            
            .chat-title h3 {
                font-size: 16px;
            }
            
            .message-container {
                max-height: 400px;
                padding: 10px 15px;
            }
            
            .message-bubble, .user-bubble {
                max-width: 280px;
                font-size: 13px;
            }
            
            .email-buttons {
                flex-direction: column;
                align-items: center;
            }
            
            .email-button {
                width: 200px;
            }
        }
    </style>
    
    <script>
        // Ultra-aggressive close button removal script targeting iframe/embed scenarios
        (function() {
            function removeAllCloseElements() {
                // Remove buttons with close-related content
                const buttons = document.querySelectorAll('button, [role="button"], [tabindex], div[onclick], span[onclick]');
                buttons.forEach(button => {
                    const text = button.textContent.trim();
                    const title = button.getAttribute('title');
                    const ariaLabel = button.getAttribute('aria-label');
                    
                    if (text === '✕' || text === '×' || text === 'X' || text === 'x' ||
                        title === 'Close' || ariaLabel === 'Close' ||
                        button.dataset.testid === 'close-button' ||
                        button.dataset.testid === 'closeButton' ||
                        button.classList.contains('close') ||
                        button.id.includes('close')) {
                        button.style.display = 'none';
                        button.style.visibility = 'hidden';
                        button.style.opacity = '0';
                        button.style.pointerEvents = 'none';
                        button.style.position = 'absolute';
                        button.style.left = '-9999px';
                        button.style.top = '-9999px';
                        button.remove();
                    }
                });
                
                // Remove any divs that only contain close symbols
                const divs = document.querySelectorAll('div, span, i, svg');
                divs.forEach(element => {
                    const text = element.textContent.trim();
                    if ((text === '✕' || text === '×' || text === 'X') && 
                        element.children.length === 0 && 
                        !element.classList.contains('message-bubble') && 
                        !element.classList.contains('user-bubble')) {
                        element.style.display = 'none';
                        element.remove();
                    }
                });
                
                // Remove any elements with close-related classes or IDs
                const closeElements = document.querySelectorAll('[class*="close"], [id*="close"], .st-emotion-cache-*[title="Close"]');
                closeElements.forEach(element => {
                    if (!element.classList.contains('message-bubble') && 
                        !element.classList.contains('user-bubble')) {
                        element.style.display = 'none';
                        element.remove();
                    }
                });
                
                // Target iframe parent elements (if this app is embedded)
                try {
                    if (window.parent !== window) {
                        // We're in an iframe, try to access parent
                        const parentDoc = window.parent.document;
                        const parentCloseButtons = parentDoc.querySelectorAll('button, [role="button"]');
                        parentCloseButtons.forEach(btn => {
                            const text = btn.textContent.trim();
                            if (text === '✕' || text === '×' || text === 'X') {
                                btn.style.display = 'none';
                            }
                        });
                    }
                } catch (e) {
                    // Cross-origin restriction, can't access parent
                    console.log('Cannot access parent frame (cross-origin)');
                }
                
                // Hide top-right corner elements specifically
                const topRightElements = document.querySelectorAll('.stApp > div:first-child > div:last-child, [data-testid="stHeader"], [data-testid="stToolbar"]');
                topRightElements.forEach(el => {
                    el.style.display = 'none';
                });
            }
            
            // Enhanced startup sequence
            function initCloseButtonRemoval() {
                removeAllCloseElements();
                
                // Set up mutation observer with enhanced options
                const observer = new MutationObserver(function(mutations) {
                    let shouldClean = false;
                    mutations.forEach(function(mutation) {
                        if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                            shouldClean = true;
                        }
                        if (mutation.type === 'attributes') {
                            const target = mutation.target;
                            if (target.textContent && (target.textContent.includes('✕') || target.textContent.includes('×'))) {
                                shouldClean = true;
                            }
                        }
                    });
                    if (shouldClean) {
                        setTimeout(removeAllCloseElements, 10);
                    }
                });
                
                observer.observe(document.body, { 
                    childList: true, 
                    subtree: true,
                    attributes: true,
                    attributeFilter: ['style', 'class', 'title', 'aria-label', 'data-testid'],
                    characterData: true
                });
                
                // More aggressive periodic cleanup
                setInterval(removeAllCloseElements, 1000); // Every 1 second
            }
            
            // Multiple initialization triggers
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', initCloseButtonRemoval);
            } else {
                initCloseButtonRemoval();
            }
            
            // Additional safety triggers
            window.addEventListener('load', removeAllCloseElements);
            setTimeout(removeAllCloseElements, 100);
            setTimeout(removeAllCloseElements, 500);
            setTimeout(removeAllCloseElements, 1000);
            setTimeout(setTimeout(removeAllCloseElements, 2000), 5000);
        })();
    </script>
    """, unsafe_allow_html=True)
    
    # Initialize
    if "chatbot" not in st.session_state:
        st.session_state.chatbot = SmartHybridChatbot()
    
    if "session_id" not in st.session_state:
        edt_now = get_edt_datetime()
        st.session_state.session_id = f"enhanced_{edt_now.strftime('%Y%m%d_%H%M%S')}_edt"
    
    # Simplified initialization - only ask for name once, no validation
    if "asking_for_name" not in st.session_state:
        st.session_state.asking_for_name = False
    if "showing_email_buttons" not in st.session_state:
        st.session_state.showing_email_buttons = False
    if "asking_for_email" not in st.session_state:
        st.session_state.asking_for_email = False
    if "asking_for_message" not in st.session_state:
        st.session_state.asking_for_message = False
    if "message_contact_info" not in st.session_state:
        st.session_state.message_contact_info = ""
    if "user_name" not in st.session_state:
        st.session_state.user_name = ""
    if "user_email" not in st.session_state:
        st.session_state.user_email = ""
    if "user_display_name" not in st.session_state:
        st.session_state.user_display_name = ""
    if "email_choice_made" not in st.session_state:
        st.session_state.email_choice_made = False
    
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
    
    # Chat UI - Header section with no close functionality
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    # Clean header with no buttons whatsoever
    shared_avatar = get_shared_avatar()
    avatar_src = shared_avatar if shared_avatar else "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNTAiIGhlaWdodD0iNTAiIHZpZXdCb3g9IjAgMCA1MCA1MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnPgo8Y2lyY2xlIGN4PSIyNSIgY3k9IjI1IiByPSIyNSIgZmlsbD0iIzY2N2VlYSIvPgo8c3ZnIHg9IjEyIiB5PSIxMiIgd2lkdGg9IjI2IiBoZWlnaHQ9IjI2IiB2aWV3Qm94PSIwIDAgMjQgMjQiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xMiAxMkMxNC43NjE0IDEyIDE3IDkuNzYxNDIgMTcgN0MxNyA0LjIzODU4IDE0Ljc2MTQgMiAxMiAyQzkuMjM4NTggMiA3IDQuMjM4NTggNyA3QzcgOS43NjE0MiA5LjIzODU4IDEyIDEyIDEyWk0xMiAxNEM4LjY4NjI5IDE0IDYgMTYuMjM4NiA2IDE5SDZDOCAyMS43NjE0IDguMjM4NTggMjQgMTEgMjRINDEzQzE1Ljc2MTQgMjQgMTggMjEuNzYxNCAxOCAxOUg2QzYgMTYuMjM4NiA5LjMxMzcxIDE0IDEyIDE0WiIgZmlsbD0id2hpdGUiLz4KPC9zdmc+Cjwvc3ZnPgo="
    
    st.markdown(f"""
    <div class="chat-header">
        <img src="{avatar_src}" class="chat-avatar" alt="Avatar">
        <div class="chat-title">
            <h3>Aniket's AI Assistant</h3>
            <div class="chat-subtitle">Professional Background & Career Info</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Messages
    st.markdown('<div class="message-container">', unsafe_allow_html=True)
    
    for message in st.session_state.messages:
        if message["role"] == "assistant":
            bot_avatar_src = shared_avatar if shared_avatar else "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNTAiIGhlaWdodD0iNTAiIHZpZXdCb3g9IjAgMCA1MCA1MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnPgo8Y2lyY2xlIGN4PSIyNSIgY3k9IjI1IiByPSIyNSIgZmlsbD0iIzY2N2VlYSIvPgo8c3ZnIHg9IjEyIiB5PSIxMiIgd2lkdGg9IjI2IiBoZWlnaHQ9IjI2IiB2aWV3Qm94PSIwIDAgMjQgMjQiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xMiAxMkMxNC43NjE0IDEyIDE3IDkuNzYxNDIgMTcgN0MxNyA0LjIzODU4IDE0Ljc2MTQgMiAxMiAyQzkuMjM4NTggMiA3IDQuMjM4NTggNyA3QzcgOS43NjE0MiA5LjIzODU4IDEyIDEyIDEyWk0xMiAxNEM4LjY4NjI5IDE0IDYgMTYuMjM4NiA2IDE5SDZDOCAyMS43NjE0IDguMjM4NTggMjQgMTEgMjRINDEzQzE1Ljc2MTQgMjQgMTggMjEuNzYxNCAxOCAxOUg2QzYgMTYuMjM4NiA5LjMxMzcxIDE0IDEyIDE0WiIgZmlsbD0id2hpdGUiLz4KPC9zdmc+Cjwvc3ZnPgo="
            st.markdown(f"""
            <div class="assistant-message">
                <img src="{bot_avatar_src}" style="width: 35px; height: 35px; border-radius: 50%; object-fit: cover;">
                <div class="message-bubble">{message["content"]}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="user-message">
                <div class="user-bubble">{message["content"]}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # **Button-based email collection**
    if st.session_state.showing_email_buttons and not st.session_state.email_choice_made:
        st.markdown("""
        <div class="email-buttons">
            <div style="width: 100%; text-align: center; margin-bottom: 10px; font-weight: 600; color: #333;">
                Would you like to share your email with Aniket?
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✅ Yes, I'll share", key="email_yes", use_container_width=True):
                st.session_state.email_choice_made = True
                st.session_state.showing_email_buttons = False
                st.session_state.asking_for_email = True
                
                # Add user choice to messages
                st.session_state.messages.append({"role": "user", "content": "✅ Yes, I'll share my email"})
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "Perfect! Please enter your email address below:"
                })
                st.rerun()
        
        with col2:
            if st.button("❌ No, skip", key="email_no", use_container_width=True):
                st.session_state.email_choice_made = True
                st.session_state.showing_email_buttons = False
                
                # Add user choice to messages
                st.session_state.messages.append({"role": "user", "content": "❌ No, skip email"})
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"No problem{', ' + st.session_state.user_display_name if st.session_state.user_display_name else ''}! I'm ready to answer questions about Aniket's professional background. What would you like to know?"
                })
                st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Dynamic chat input placeholders
    if st.session_state.asking_for_name:
        placeholder = "Enter your name..."
    elif st.session_state.showing_email_buttons:
        placeholder = "Please use the buttons above to choose..."
        st.chat_input(placeholder, disabled=True)
        return
    elif st.session_state.asking_for_email:
        placeholder = "Enter your email address..."
    elif st.session_state.asking_for_message:
        placeholder = "Type your message for Aniket (or 'cancel' to skip)..."
    else:
        placeholder = "Ask about Aniket's skills, experience, projects, or why you should hire him..."
    
    if prompt := st.chat_input(placeholder):
        if check_and_reset_if_needed():
            st.rerun()
            return
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        if st.session_state.asking_for_name:
            user_input = prompt.strip()
            
            st.session_state.user_name = user_input if user_input else "Guest"
            st.session_state.asking_for_name = False
            
            if user_input:
                name_parts = user_input.split()
                st.session_state.user_display_name = name_parts[0]
            else:
                st.session_state.user_display_name = "Guest"
            
            st.session_state.showing_email_buttons = True
        
        elif st.session_state.asking_for_email:
            extracted_email = extract_email_from_input(prompt)
            
            if extracted_email and is_valid_email(extracted_email):
                st.session_state.user_email = extracted_email
                st.session_state.asking_for_email = False
                
                save_user_info(st.session_state.user_name, st.session_state.user_email, st.session_state.session_id)
                
                response = f"Perfect! Thank you, {st.session_state.user_display_name}. I'm ready to answer questions about Aniket's professional background. What would you like to know?"
                st.session_state.messages.append({"role": "assistant", "content": response})
            
            elif is_valid_email(prompt.strip()):
                st.session_state.user_email = prompt.strip()
                st.session_state.asking_for_email = False
                
                save_user_info(st.session_state.user_name, st.session_state.user_email, st.session_state.session_id)
                
                response = f"Perfect! Thank you, {st.session_state.user_display_name}. I'm ready to answer questions about Aniket's professional background. What would you like to know?"
                st.session_state.messages.append({"role": "assistant", "content": response})
            
            else:
                response = "That doesn't look like a valid email address. Could you please try again? (e.g., john@company.com)"
                st.session_state.messages.append({"role": "assistant", "content": response})
        
        elif st.session_state.asking_for_message:
            message_content = prompt.strip()
            
            if message_content.lower() in ['cancel', 'nevermind', 'skip']:
                st.session_state.asking_for_message = False
                response = f"No problem, {st.session_state.user_display_name}! Is there anything else you'd like to know about Aniket?"
                st.session_state.messages.append({"role": "assistant", "content": response})
            elif len(message_content) < 10:
                response = "Could you please provide a bit more detail in your message? What would you like Aniket to know or follow up about?"
                st.session_state.messages.append({"role": "assistant", "content": response})
            else:
                message_saved = save_message_for_aniket(
                    st.session_state.user_name,
                    st.session_state.user_email,
                    message_content,
                    st.session_state.message_contact_info
                )
                
                st.session_state.asking_for_message = False
                
                if message_saved:
                    response = f"""Perfect! I've saved your message for Aniket:

"{message_content}"

He'll review this and follow up with you within 1-2 business days. You can also reach him directly at ashirsat@iu.edu if you need a faster response."""
                else:
                    response = f"""I've noted your message. Please reach Aniket directly at ashirsat@iu.edu, call +1 463 279 6071, or connect on LinkedIn for the fastest response.

Your message: "{message_content}" """
                
                st.session_state.messages.append({"role": "assistant", "content": response})
        
        else:
            with st.spinner("🤖 Analyzing your question..."):
                response, intent = st.session_state.chatbot.generate_response(prompt)
            
            if intent == "message_for_contact":
                phone_pattern = r'(\+?\d{1,4}[-.\s]?\(?\d{1,3}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9})'
                phone_match = re.search(phone_pattern, prompt)
                email_match = extract_email_from_input(prompt)
                
                contact_info = ""
                if phone_match:
                    contact_info = f"Phone: {phone_match.group(1)}"
                if email_match:
                    if contact_info:
                        contact_info += f", Email: {email_match}"
                    else:
                        contact_info = f"Email: {email_match}"
                
                st.session_state.message_contact_info = contact_info
                st.session_state.asking_for_message = True
                
                contact_part = f" I have your contact info: {contact_info}." if contact_info else ""
                response = f"""I'd be happy to have Aniket contact you!{contact_part}

What message would you like me to pass along to him? Please share what you'd like to discuss or any specific questions you have."""
                
            st.session_state.messages.append({"role": "assistant", "content": response})
            
            if intent == "end_conversation":
                st.session_state.conversation_ending = True
                
                if hasattr(st.session_state, 'conversation_thread') and st.session_state.conversation_thread:
                    st.session_state.conversation_thread.append({
                        'role': 'user',
                        'content': prompt,
                        'timestamp': get_edt_timestamp(),
                        'timestamp_edt': get_edt_datetime().strftime('%Y-%m-%d %H:%M:%S %Z')
                    })
                    st.session_state.conversation_thread.append({
                        'role': 'assistant',
                        'content': response,
                        'intent': intent,
                        'timestamp': get_edt_timestamp(),
                        'timestamp_edt': get_edt_datetime().strftime('%Y-%m-%d %H:%M:%S %Z')
                    })
                    
                    save_complete_conversation(
                        st.session_state.session_id,
                        st.session_state.get('user_name', ''),
                        st.session_state.get('user_email', ''),
                        st.session_state.conversation_thread
                    )
                
                st.session_state.reset_on_next_message = True
            else:
                log_conversation_with_thread(
                    st.session_state.session_id,
                    prompt,
                    response,
                    intent,
                    st.session_state.user_name,
                    st.session_state.user_email
                )
        
        st.rerun()

# Enhanced helper functions
def check_and_reset_if_needed():
    """Check if we need to reset the conversation"""
    if st.session_state.get('reset_on_next_message', False):
        reset_conversation_session()
        st.session_state.reset_on_next_message = False
        return True
    return False

def log_conversation_with_thread(session_id: str, user_message: str, bot_response: str, intent: str, user_name: str = "", user_email: str = ""):
    """Enhanced logging that maintains conversation threads with EDT timestamps"""
    
    log_conversation_to_dashboard(session_id, user_message, bot_response, intent, user_name, user_email)
    
    if 'conversation_thread' not in st.session_state:
        st.session_state.conversation_thread = []
    
    edt_now = get_edt_datetime()
    timestamp_iso = get_edt_timestamp()
    timestamp_readable = edt_now.strftime('%Y-%m-%d %H:%M:%S %Z')
    
    st.session_state.conversation_thread.append({
        'role': 'user',
        'content': user_message,
        'timestamp': timestamp_iso,
        'timestamp_edt': timestamp_readable
    })
    
    st.session_state.conversation_thread.append({
        'role': 'assistant',
        'content': bot_response,
        'intent': intent,
        'timestamp': timestamp_iso,
        'timestamp_edt': timestamp_readable
    })
    
    if len(st.session_state.conversation_thread) % 10 == 0:
        save_complete_conversation(
            session_id,
            user_name,
            user_email,
            st.session_state.conversation_thread.copy()
        )

def reset_conversation_session():
    """Reset the conversation session for a fresh start"""
    if hasattr(st.session_state, 'conversation_thread') and st.session_state.conversation_thread:
        save_complete_conversation(
            st.session_state.session_id,
            st.session_state.get('user_name', ''),
            st.session_state.get('user_email', ''),
            st.session_state.conversation_thread
        )
    
    user_name = st.session_state.get('user_name', '')
    user_email = st.session_state.get('user_email', '')
    user_display_name = st.session_state.get('user_display_name', '')
    
    for key in list(st.session_state.keys()):
        if key not in ['user_name', 'user_email', 'user_display_name', 'chatbot']:
            del st.session_state[key]
    
    st.session_state.user_name = user_name
    st.session_state.user_email = user_email
    st.session_state.user_display_name = user_display_name
    
    edt_now = get_edt_datetime()
    st.session_state.session_id = f"enhanced_{edt_now.strftime('%Y%m%d_%H%M%S')}_edt"
    
    st.session_state.awaiting_closure_response = False
    st.session_state.conversation_thread = []
    st.session_state.asking_for_email = False
    st.session_state.asking_for_message = False
    st.session_state.message_contact_info = ""
    st.session_state.showing_email_buttons = False
    st.session_state.email_choice_made = False
    
    greeting_name = f" {user_display_name}" if user_display_name else ""
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": f"Hello{greeting_name}! I'm ready to help with any new questions about Aniket's background, skills, or experience. What would you like to know?"
        }
    ]

def save_complete_conversation(session_id: str, user_name: str, user_email: str, conversation_messages: List[Dict]):
    """Save complete conversation thread with EDT timestamps"""
    try:
        db = get_shared_db()
        data = db._load_gist_data()
        
        edt_now = get_edt_datetime()
        
        conversation_thread = {
            "session_id": session_id,
            "user_name": user_name,
            "user_email": user_email,
            "start_time": conversation_messages[0]['timestamp'] if conversation_messages else get_edt_timestamp(),
            "end_time": conversation_messages[-1]['timestamp'] if conversation_messages else get_edt_timestamp(),
            "start_time_edt": edt_now.strftime('%Y-%m-%d %H:%M:%S %Z') if not conversation_messages else conversation_messages[0].get('timestamp_edt', ''),
            "end_time_edt": edt_now.strftime('%Y-%m-%d %H:%M:%S %Z') if not conversation_messages else conversation_messages[-1].get('timestamp_edt', ''),
            "total_messages": len(conversation_messages),
            "conversation_flow": conversation_messages,
            "saved_at": get_edt_timestamp()
        }
        
        if "conversation_threads" not in data:
            data["conversation_threads"] = []
        
        data["conversation_threads"].append(conversation_thread)
        data["last_updated"] = get_edt_timestamp()
        
        return db._save_gist_data(data)
        
    except Exception as e:
        return False

if __name__ == "__main__":
    main()
