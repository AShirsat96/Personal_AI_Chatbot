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

# Updated OpenAI import (v1.0+ compatible)
from openai import OpenAI

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
    """Free shared database using GitHub Gist - SYNCHRONIZED WITH ADMIN DASHBOARD"""

    def __init__(self):
        self.github_token = st.secrets.get("GITHUB_TOKEN", "")
        self.gist_id = st.secrets.get("GIST_ID", "")

        self.use_gist = bool(self.github_token and self.gist_id)

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
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                gist_data = response.json()
                if "chatbot_data.json" in gist_data["files"]:
                    content = gist_data["files"]["chatbot_data.json"]["content"]
                    return json.loads(content)
                else:
                    return self._get_default_data()
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
                json=payload,
                timeout=10
            )

            return response.status_code == 200

        except Exception as e:
            st.error(f"Error saving to gist: {str(e)}")
            return self._save_local_data(data)
    
    def _get_default_data(self) -> Dict:
        """Get default data structure - MATCHES ADMIN DASHBOARD"""
        return {
            "user_interactions": [],
            "conversations": [],
            "conversation_threads": [],
            "resume_content": None,
            "avatar_data": None,
            "app_settings": {},
            "messages_for_aniket": [],
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
        """Save user interaction - MATCHES ADMIN DASHBOARD FORMAT"""
        try:
            data = self._load_gist_data()
            user_entry = {
                "timestamp": datetime.now().isoformat(),
                "name": name,
                "email": email,
                "session_id": session_id
            }
            if "user_interactions" not in data:
                data["user_interactions"] = []
            data["user_interactions"].append(user_entry)
            data["last_updated"] = datetime.now().isoformat()
            return self._save_gist_data(data)
        except Exception as e:
            st.error(f"Error saving user interaction: {str(e)}")
            return False

    def log_conversation(self, session_id: str, user_message: str, bot_response: str, intent: str, user_name: str = "", user_email: str = "") -> bool:
        """Log conversation for analytics - EXACTLY MATCHES ADMIN DASHBOARD FORMAT"""
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
            st.error(f"Error logging conversation: {str(e)}")
            return False

    def save_conversation_thread(self, session_id: str, user_name: str, user_email: str, conversation_messages: list) -> bool:
        """Save complete conversation thread - MATCHES ADMIN DASHBOARD FORMAT"""
        try:
            data = self._load_gist_data()
            conversation_thread = {
                "session_id": session_id,
                "user_name": user_name,
                "user_email": user_email,
                "start_time": conversation_messages[0]['timestamp'] if conversation_messages else datetime.now().isoformat(),
                "end_time": conversation_messages[-1]['timestamp'] if conversation_messages else datetime.now().isoformat(),
                "total_messages": len(conversation_messages),
                "conversation_flow": conversation_messages,
                "saved_at": datetime.now().isoformat()
            }
            if "conversation_threads" not in data:
                data["conversation_threads"] = []
            data["conversation_threads"].append(conversation_thread)
            data["last_updated"] = datetime.now().isoformat()
            return self._save_gist_data(data)
        except Exception as e:
            st.error(f"Error saving conversation thread: {str(e)}")
            return False
    
    def save_message_for_aniket(self, user_name: str, user_email: str, message_content: str, contact_info: str = "") -> bool:
        """Save messages left for Aniket"""
        try:
            data = self._load_gist_data()
            message_entry = {
                "timestamp": datetime.now().isoformat(),
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
            data["last_updated"] = datetime.now().isoformat()
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

    def get_resume(self) -> Optional[Dict]:
        """Get current resume from shared database"""
        try:
            data = self._load_gist_data()
            return data.get("resume_content")
        except Exception as e:
            return None

# Shared instance accessors
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

def save_conversation_thread_to_dashboard(session_id: str, user_name: str, user_email: str, messages: list) -> bool:
    """Save complete conversation thread to dashboard"""
    db = get_shared_db()
    return db.save_conversation_thread(session_id, user_name, user_email, messages)

def save_message_for_aniket(user_name: str, user_email: str, message_content: str, contact_info: str = "") -> bool:
    """Save message for Aniket to shared database"""
    db = get_shared_db()
    return db.save_message_for_aniket(user_name, user_email, message_content, contact_info)

def get_shared_avatar() -> Optional[str]:
    """Get avatar from shared database"""
    db = get_shared_db()
    return db.get_avatar()

def get_shared_resume() -> Optional[Dict]:
    """Get resume from shared database"""
    db = get_shared_db()
    return db.get_resume()

class SmartHybridChatbot:
    """Intelligent hybrid chatbot with OpenAI integration"""

    def __init__(self):
        # Load resume content from shared database
        self.resume_data = get_shared_resume()

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

        # Enhance with resume data if available
        if self.resume_data:
            self.enhance_with_resume_data()

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

    def enhance_with_resume_data(self):
        """Enhance knowledge base with resume content"""
        if not self.resume_data:
            return

        resume_content = self.resume_data.get('content', '')
        
        # Check if resume_content is not None and not empty
        if resume_content and isinstance(resume_content, str):
            # Add resume info to system prompt
            self.system_prompt += f"\n\nAdditional Resume Information:\n{resume_content[:1000]}..."
    
    def get_openai_response(self, user_input: str, intent: str, context: Dict[str, bool]) -> str:
        """Use OpenAI API to generate a custom response"""
        client = get_openai_client()
        if not client:
            return self.get_fallback_response(intent)

        # Construct messages
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_input}
        ]

        # Call OpenAI
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
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

        satisfaction_signals = any(word in input_lower for word in self.conversation_patterns["satisfaction"])
        thanks_signals = any(word in input_lower for word in self.conversation_patterns["thanks"])
        ending_signals = any(phrase in input_lower for phrase in self.conversation_patterns["conversation_enders"])

        long_conversation = message_count >= 8

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

        ending_phrases = [
            "no", "no more", "no other", "no further", "nothing else", "nothing more",
            "that's all", "that's it", "all set", "i'm good", "i'm all set",
            "end conversation", "end chat", "stop", "quit", "exit", "done",
            "that covers it", "that's everything", "sufficient", "enough"
        ]

        if any(phrase in input_lower for phrase in ending_phrases):
            return "end_conversation"

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
        """Analyze user intent from input"""
        input_lower = user_input.lower().strip()

        if len(input_lower) < 2:
            return "general"

        # Message for contact
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

        elif any(word in input_lower for word in ["hello", "hi", "hey"]) and len(input_lower.split()) <= 3:
            return "greeting"
        elif any(pattern in input_lower for pattern in ["thank", "thanks", "appreciate", "grateful"]):
            return "thanks"
        elif any(pattern in input_lower for pattern in ["bye", "goodbye", "see you", "farewell", "take care", "exit", "quit"]):
            return "goodbye"
        elif any(word in input_lower for word in ["hobby", "hobbies", "interest", "interests", "personal", "outside work", "free time", "activities", "rowing", "sports", "club"]):
            return "personal"
        elif any(word in input_lower for word in ["hire", "hiring", "recruit", "recommend", "choose", "employ", "candidate", "why him", "why choose"]):
            return "hiring"
        elif any(word in input_lower for word in ["skill", "skills", "technical", "programming", "tech", "abilities", "tools", "technologies", "capabilities", "expertise"]):
            return "skills"
        elif any(word in input_lower for word in ["education", "school", "degree", "gpa", "university", "academic", "study", "college", "qualification"]):
            return "education"
        elif any(word in input_lower for word in ["experience", "work", "job", "employment", "career", "professional", "background", "history", "worked at"]):
            return "experience"
        elif any(word in input_lower for word in ["project", "projects", "research", "built", "created", "developed", "achievement", "accomplishment", "portfolio"]):
            return "projects"
        elif any(word in input_lower for word in ["contact", "reach", "connect", "email", "phone", "linkedin", "get in touch", "communication"]):
            return "contact"
        elif st.session_state.get('awaiting_closure_response', False):
            ending_intent = self.detect_conversation_ending_intent(user_input)
            if ending_intent == "end_conversation":
                return "end_conversation"
            elif ending_intent == "continue_conversation":
                return "continue_conversation"
            else:
                return "general"
        elif any(word in input_lower for word in ["available", "availability", "start", "when", "timeline", "free", "ready"]):
            return "availability"
        elif any(word in input_lower for word in ["salary", "compensation", "pay", "money", "cost", "rate", "price", "budget"]):
            return "salary"
        elif any(word in input_lower for word in ["location", "where", "based", "remote", "relocate", "move", "office"]):
            return "location"
        elif any(word in input_lower for word in ["culture", "team", "environment", "fit", "values", "work style"]):
            return "company_culture"
        elif any(word in input_lower for word in ["future", "goals", "plans", "career path", "ambition", "vision", "long term"]):
            return "future"
        elif any(word in input_lower for word in ["who is", "what is", "tell me about", "describe", "explain", "information", "about him"]):
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

        input_lower = user_input.lower()
        is_casual = any(word in input_lower for word in ["hey", "hi", "what's up", "sup", "cool", "awesome", "nice"])
        is_formal = any(word in input_lower for word in ["please", "could you", "would you", "may I", "thank you very much"])

        system_intents = ["greeting", "thanks", "goodbye", "end_conversation", "continue_conversation"]

        if intent in system_intents:
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
            if self.use_openai_for_response():
                try:
                    response = self.get_openai_response(user_input, intent, context)
                except Exception as e:
                    st.warning(f"OpenAI error, using fallback: {str(e)}")
                    response = self.get_fallback_response(intent)
            else:
                response = self.get_predefined_response(intent, context, is_casual, is_formal)

        message_count = len(st.session_state.messages) // 2
        if (self.should_offer_conversation_closure(user_input, message_count) and 
            not st.session_state.get('awaiting_closure_response', False)):
            response += "\n\n" + self.get_conversation_closure_offer()
            st.session_state.awaiting_closure_response = True

        return response, intent

    def get_predefined_response(self, intent: str, context: Dict[str, bool], is_casual: bool, is_formal: bool) -> str:
        """Get predefined response when OpenAI is not available"""
        if intent == "hiring":
            return """I'd strongly recommend Aniket. He maintains a perfect 4.0 GPA while working as a Research Assistant, which shows he can handle multiple demanding responsibilities.

Most importantly, his ML projects have delivered real business impact – over $1 million in annual savings from vessel optimization work. He's proficient in Python, R, SQL, and cloud platforms like AWS and Azure."""
        elif intent == "skills":
            return """Aniket is proficient in Python, R, and SQL for programming. He has experience with AWS, Azure, and Google Cloud Platform for cloud computing.

His AI and machine learning expertise includes computer vision, natural language processing, and advanced analytics. What sets him apart is that he applies these skills to create real business value."""
        elif intent == "education":
            return """Aniket is currently pursuing his Master's in Applied Data Science at Indiana University Indianapolis with a perfect 4.0 GPA. He also has a Master's in Management from Singapore Management University.

This combination gives him both technical depth and business strategy perspective."""
        elif intent == "experience":
            return """Aniket currently works as a Research Assistant at Indiana University, where he's developing a cultural ambiguity detection model with 90%+ accuracy.

Previously, he worked on a vessel fuel optimization project that reduced fuel usage by 5% across 50+ ships, saving over $1 million per year."""
        elif intent == "projects":
            return """Aniket has worked on several impactful projects. One project involved optimizing vessel fuel usage using machine learning, which resulted in $1M+ in annual savings.

Another project used NLP to build a cultural ambiguity detection model, achieving over 90% accuracy in identifying tone misinterpretation in global teams."""
        elif intent == "contact":
            contact = self.aniket_data["contact"]
            return f"""You can reach Aniket via:
📧 Email: {contact["email"]}
📞 Phone: {contact["phone"]}
🔗 LinkedIn: {contact["linkedin"]}
💻 GitHub: {contact["github"]}"""
        elif intent == "personal":
            return """Aniket is an active member of the Indiana University Jaguars Rowing Club, showing his commitment to physical discipline and teamwork.

He's also the Head of Outreach for the Data Science and Machine Learning Club, reflecting strong leadership and communication skills."""
        elif intent == "availability":
            return """Aniket is actively seeking full-time roles and is available immediately. He's flexible with start dates and ready to begin interviews at your convenience."""
        elif intent == "salary":
            return """Salary expectations are flexible and depend on the role, location, and responsibilities. Aniket is primarily focused on finding a position where he can make meaningful contributions."""
        elif intent == "location":
            return """Aniket is currently based in Indianapolis but is open to remote roles or relocation for the right opportunity."""
        elif intent == "company_culture":
            return """Aniket thrives in collaborative, fast-paced environments that value innovation, data-driven decision-making, and continuous learning."""
        elif intent == "future":
            return """Aniket aims to grow into a leadership role in data science, driving impact through applied machine learning and mentoring teams on solving real-world problems."""
        elif intent == "message_for_contact":
            return self.handle_message_for_contact(user_input="")
        else:
            return self.get_general_response(is_casual=is_casual)
    
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

    def handle_message_for_contact(self, user_input: str) -> str:
        """Handle cases where users leave messages for Aniket to contact them"""
        phone_pattern = r'(\+?\d{1,4}[-.\s]?\(?\d{1,3}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9})'
        phone_match = re.search(phone_pattern, user_input)

        if phone_match:
            phone_number = phone_match.group(1)
            return f"""I'd be happy to have Aniket contact you at {phone_number}!

What message would you like me to pass along to him?"""
        else:
            return """I'd be happy to have Aniket contact you!

What message would you like me to pass along to him, and what's the best way for him to reach you?"""

    def get_general_response(self, is_casual: bool = False) -> str:
        return """Aniket Shirsat is pursuing his Master's in Applied Data Science at Indiana University Indianapolis with a perfect 4.0 GPA while working as a Research Assistant.

His key highlights include over $1 million in business impact from ML projects, skills in Python, R, SQL, AWS, Azure, and GCP, plus leadership experience with the Data Science Club and rowing team.

He's currently seeking data science and machine learning opportunities where he can apply his combination of technical expertise and business understanding."""


def main():
    """Enhanced chatbot with COMPLETE dashboard synchronization"""
    st.set_page_config(
        page_title="Chat with Aniket's AI Assistant",
        page_icon="💬",
        layout="centered"
    )
    
    # Enhanced CSS with close button removal
    st.markdown("""
    <style>
        .stApp {
            margin: 0 !important;
            padding: 0 !important;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
        }
        
        .stApp > header {
            visibility: hidden !important;
            height: 0 !important;
            display: none !important;
        }
        
        .block-container {
            padding: 10px !important;
            margin: 0 !important;
            max-width: 100% !important;
        }
        
        .stDeployButton {display: none !important;}
        #MainMenu {visibility: hidden !important;}
        footer {visibility: hidden !important;}
        
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
        }
        
        .chat-avatar {
            width: 50px;
            height: 50px;
            border-radius: 50%;
            border: 3px solid rgba(255,255,255,0.3);
            object-fit: cover;
        }
        
        .chat-title h3 {
            margin: 0;
            font-size: 18px;
            font-weight: 600;
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
        
        @media (max-width: 768px) {
            .chat-container {
                max-width: 95%;
                margin: 5px auto;
                border-radius: 15px;
            }
            
            .message-bubble, .user-bubble {
                max-width: 280px;
                font-size: 13px;
            }
        }
    </style>
    """, unsafe_allow_html=True)

    # Initialize session state
    if "chatbot" not in st.session_state:
        st.session_state.chatbot = SmartHybridChatbot()
    
    if "session_id" not in st.session_state:
        st.session_state.session_id = f"enhanced_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Initialize conversation state
    for key, default_value in {
        "asking_for_name": False,
        "showing_email_buttons": False,
        "asking_for_email": False,
        "asking_for_message": False,
        "message_contact_info": "",
        "user_name": "",
        "user_email": "",
        "user_display_name": "",
        "email_choice_made": False,
        "conversation_thread": [],
        "awaiting_closure_response": False
    }.items():
        if key not in st.session_state:
            st.session_state[key] = default_value
    
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
            <div class="chat-subtitle">Professional Background & Career Info</div>
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
    
    # Email collection buttons
    if st.session_state.showing_email_buttons and not st.session_state.email_choice_made:
        st.markdown("""
        <div style="text-align: center; margin: 15px 0;">
            <div style="font-weight: 600; color: #333; margin-bottom: 10px;">
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
                
                st.session_state.messages.append({"role": "user", "content": "❌ No, skip email"})
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": f"No problem{', ' + st.session_state.user_display_name if st.session_state.user_display_name else ''}! I'm ready to answer questions about Aniket's professional background. What would you like to know?"
                })
                st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)  # Close message-container
    st.markdown('</div>', unsafe_allow_html=True)  # Close chat-container

    # Dynamic chat input
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
        # Check if we need to reset conversation first
        if check_and_reset_if_needed():
            st.rerun()
            return
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        if st.session_state.asking_for_name:
            # Accept name input
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
            # Handle email input
            extracted_email = extract_email_from_input(prompt)
            
            if extracted_email and is_valid_email(extracted_email):
                st.session_state.user_email = extracted_email
                st.session_state.asking_for_email = False
                
                # SYNCHRONIZE: Save user info to dashboard
                save_user_info(st.session_state.user_name, st.session_state.user_email, st.session_state.session_id)
                
                response = f"Perfect! Thank you, {st.session_state.user_display_name}. I'm ready to answer questions about Aniket's professional background. What would you like to know?"
                st.session_state.messages.append({"role": "assistant", "content": response})
            
            elif is_valid_email(prompt.strip()):
                st.session_state.user_email = prompt.strip()
                st.session_state.asking_for_email = False
                
                # SYNCHRONIZE: Save user info to dashboard
                save_user_info(st.session_state.user_name, st.session_state.user_email, st.session_state.session_id)
                
                response = f"Perfect! Thank you, {st.session_state.user_display_name}. I'm ready to answer questions about Aniket's professional background. What would you like to know?"
                st.session_state.messages.append({"role": "assistant", "content": response})
            
            else:
                response = "That doesn't look like a valid email address. Could you please try again? (e.g., john@company.com)"
                st.session_state.messages.append({"role": "assistant", "content": response})
        
        elif st.session_state.asking_for_message:
            # Handle message collection
            message_content = prompt.strip()
            
            if message_content.lower() in ['cancel', 'nevermind', 'skip']:
                st.session_state.asking_for_message = False
                response = f"No problem, {st.session_state.user_display_name}! Is there anything else you'd like to know about Aniket?"
                st.session_state.messages.append({"role": "assistant", "content": response})
            elif len(message_content) < 10:
                response = "Could you please provide a bit more detail in your message? What would you like Aniket to know or follow up about?"
                st.session_state.messages.append({"role": "assistant", "content": response})
            else:
                # SYNCHRONIZE: Save message to dashboard
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
            # Normal chat with FULL SYNCHRONIZATION
            with st.spinner("🤖 Analyzing your question..."):
                response, intent = st.session_state.chatbot.generate_response(prompt)
            
            # Special handling for message_for_contact intent
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
            
            # CRITICAL SYNCHRONIZATION: Log EVERY conversation to dashboard
            log_conversation_with_thread(
                st.session_state.session_id,
                prompt,
                response,
                intent,
                st.session_state.user_name,
                st.session_state.user_email
            )
            
            # Handle conversation ending
            if intent == "end_conversation":
                st.session_state.conversation_ending = True
                
                # SYNCHRONIZE: Save final conversation thread to dashboard
                if hasattr(st.session_state, 'conversation_thread') and st.session_state.conversation_thread:
                    st.session_state.conversation_thread.append({
                        'role': 'user',
                        'content': prompt,
                        'timestamp': datetime.now().isoformat()
                    })
                    st.session_state.conversation_thread.append({
                        'role': 'assistant',
                        'content': response,
                        'intent': intent,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    # Save complete conversation thread to dashboard
                    save_conversation_thread_to_dashboard(
                        st.session_state.session_id,
                        st.session_state.get('user_name', ''),
                        st.session_state.get('user_email', ''),
                        st.session_state.conversation_thread
                    )
                
                # Schedule reset for next interaction
                st.session_state.reset_on_next_message = True
        
        st.rerun()

# Enhanced helper functions for COMPLETE SYNCHRONIZATION
def check_and_reset_if_needed():
    """Check if we need to reset the conversation"""
    if st.session_state.get('reset_on_next_message', False):
        reset_conversation_session()
        st.session_state.reset_on_next_message = False
        return True
    return False

def log_conversation_with_thread(session_id: str, user_message: str, bot_response: str, intent: str, user_name: str = "", user_email: str = ""):
    """Enhanced logging that maintains conversation threads and syncs with dashboard"""
    
    # SYNCHRONIZE: Log individual message to dashboard (existing functionality)
    log_conversation_to_dashboard(session_id, user_message, bot_response, intent, user_name, user_email)
    
    # Build conversation thread for complete conversation tracking
    if 'conversation_thread' not in st.session_state:
        st.session_state.conversation_thread = []
    
    # Add user message to thread
    st.session_state.conversation_thread.append({
        'role': 'user',
        'content': user_message,
        'timestamp': datetime.now().isoformat()
    })
    
    # Add bot response to thread
    st.session_state.conversation_thread.append({
        'role': 'assistant',
        'content': bot_response,
        'intent': intent,
        'timestamp': datetime.now().isoformat()
    })
    
    # SYNCHRONIZE: Save thread periodically (every 10 messages) or when session ends
    if len(st.session_state.conversation_thread) % 10 == 0:  # Every 5 exchanges
        save_conversation_thread_to_dashboard(
            session_id, 
            user_name, 
            user_email, 
            st.session_state.conversation_thread.copy()
        )

def reset_conversation_session():
    """Reset the conversation session for a fresh start"""
    # SYNCHRONIZE: Save the current conversation thread before resetting
    if hasattr(st.session_state, 'conversation_thread') and st.session_state.conversation_thread:
        save_conversation_thread_to_dashboard(
            st.session_state.session_id,
            st.session_state.get('user_name', ''),
            st.session_state.get('user_email', ''),
            st.session_state.conversation_thread
        )
    
    # Keep user info but reset conversation state
    user_name = st.session_state.get('user_name', '')
    user_email = st.session_state.get('user_email', '')
    user_display_name = st.session_state.get('user_display_name', '')
    
    # Clear conversation-specific state
    for key in list(st.session_state.keys()):
        if key not in ['user_name', 'user_email', 'user_display_name', 'chatbot']:
            del st.session_state[key]
    
    # Restore user info
    st.session_state.user_name = user_name
    st.session_state.user_email = user_email
    st.session_state.user_display_name = user_display_name
    
    # Create new session ID for fresh conversation tracking
    st.session_state.session_id = f"enhanced_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Reset conversation state
    st.session_state.awaiting_closure_response = False
    st.session_state.conversation_thread = []
    st.session_state.asking_for_email = False
    st.session_state.asking_for_message = False
    st.session_state.message_contact_info = ""
    st.session_state.showing_email_buttons = False
    st.session_state.email_choice_made = False
    
    # Set fresh greeting message
    greeting_name = f" {user_display_name}" if user_display_name else ""
    st.session_state.messages = [
        {
            "role": "assistant", 
            "content": f"Hello{greeting_name}! I'm ready to help with any new questions about Aniket's background, skills, or experience. What would you like to know?"
        }
    ]

if __name__ == "__main__":
    main()
