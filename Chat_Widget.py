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

# Add OpenAI import
import openai

# Set OpenAI API key
openai.api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))

def extract_name_from_input(user_input: str) -> Optional[str]:
    """Extract name from natural language input - SUPPORTS FULL NAMES"""
    input_lower = user_input.lower().strip()
    
    # Remove common greetings and punctuation
    input_clean = re.sub(r'[^\w\s]', '', input_lower)
    
    # Names to exclude (Aniket's name variations)
    excluded_names = {'aniket', 'aniket shirsat'}
    
    # Common patterns for name introduction - UPDATED TO CAPTURE FULL NAMES
    name_patterns = [
        r'(?:hello|hi|hey)\s+(?:my\s+name\s+is|i\s*am|i\'m)\s+(.+)',
        r'(?:my\s+name\s+is|i\s*am|i\'m)\s+(.+)',
        r'(?:hello|hi|hey)\s+(.+?)(?:\s+here)?$',
        r'(?:this\s+is|its)\s+(.+)',
        r'(.+?)\s+here$'
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
            
            # Check if it's a valid name (not just non-name words)
            name_words = potential_name.split()
            valid_name_words = [word for word in name_words if word not in non_names and len(word) >= 2 and word.lower() not in excluded_names]
            
            if valid_name_words:
                # Capitalize each word properly
                extracted_name = ' '.join(word.capitalize() for word in valid_name_words)
                # Final check: don't return if it matches excluded names
                if extracted_name.lower() in excluded_names:
                    continue
                return extracted_name
    
    # If no pattern matches, check if it's just a name without intro words
    words = input_clean.split()
    non_names = {
        'hello', 'hi', 'hey', 'good', 'morning', 'afternoon', 'evening',
        'my', 'name', 'is', 'am', 'im', 'this', 'its', 'here', 'there',
        'yes', 'no', 'ok', 'okay', 'sure', 'thanks', 'thank', 'you',
        'please', 'can', 'could', 'would', 'will', 'the', 'a', 'an'
    }
    
    # Filter out non-name words and keep valid name parts
    valid_words = [word for word in words if word not in non_names and len(word) >= 2 and word.lower() not in excluded_names]
    
    if valid_words:
        extracted_name = ' '.join(word.capitalize() for word in valid_words)
        # Final check: don't return if it matches excluded names
        if extracted_name.lower() in excluded_names:
            return None
        return extracted_name
    
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

            # Call OpenAI API
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",  # or "gpt-4" if you have access
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
        # Check if API key is available
        api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
        return bool(api_key)
    
    def should_offer_conversation_closure(self, user_input: str, message_count: int) -> bool:
        """Determine if we should offer to end the conversation"""
        input_lower = user_input.lower().strip()
        
        # Check for satisfaction/completion signals
        satisfaction_signals = any(word in input_lower for word in self.conversation_patterns["satisfaction"])
        thanks_signals = any(word in input_lower for word in self.conversation_patterns["thanks"])
        ending_signals = any(phrase in input_lower for phrase in self.conversation_patterns["conversation_enders"])
        
        # Check for conversation length (offer closure after comprehensive responses)
        long_conversation = message_count >= 8  # After 4 exchanges
        
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
        
        # First check for specific question patterns - be more specific about greetings
        if any(word in input_lower for word in ["hello", "hi", "hey"]) and len(input_lower.split()) <= 3 and not any(word in input_lower for word in ["skill", "project", "hire", "experience", "hobby", "personal"]):
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
        
        # Message for contact - NEW: Detect when someone leaves a message with contact info
        elif any(phrase in input_lower for phrase in ["leave a message", "message for him", "ask him to contact", "have him call", "get back to me", "follow up", "reach out to me", "contact me"]) or (any(word in input_lower for word in ["my number", "my phone", "call me", "reach me"]) and any(char.isdigit() for char in user_input)):
            return "message_for_contact"
        
        # Conversation flow management - NEW
        elif st.session_state.get('awaiting_closure_response', False):
            ending_intent = self.detect_conversation_ending_intent(user_input)
            if ending_intent == "end_conversation":
                return "end_conversation"
            elif ending_intent == "continue_conversation":
                return "continue_conversation"
            else:
                return "general"  # Treat unclear responses as new questions
        
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
        """Generate intelligent response based on intent analysis"""
        intent = self.analyze_intent(user_input)
        context = self.extract_context(user_input)
        
        # Add conversational context awareness
        input_lower = user_input.lower()
        is_casual = any(word in input_lower for word in ["hey", "hi", "what's up", "sup", "cool", "awesome", "nice"])
        is_formal = any(word in input_lower for word in ["please", "could you", "would you", "may I", "thank you very much"])
        
        # Generate base response with natural conversation flow
        if intent == "greeting":
            response = self.get_greeting_response(is_casual)
        elif intent == "thanks":
            response = self.get_thanks_response(is_casual)
        elif intent == "goodbye":
            response = self.get_goodbye_response(is_casual)
        elif intent == "hiring":
            response = self.get_hiring_response(context, is_casual, is_formal)
        elif intent == "skills":
            response = self.get_skills_response(context, is_casual, is_formal)
        elif intent == "education":
            response = self.get_education_response(context, is_casual, is_formal)
        elif intent == "experience":
            response = self.get_experience_response(context, is_casual, is_formal)
        elif intent == "projects":
            response = self.get_projects_response(context, is_casual, is_formal)
        elif intent == "personal":
            response = self.get_personal_response(context, is_casual, is_formal)
        elif intent == "contact":
            response = self.get_contact_response(context, is_casual, is_formal)
        elif intent == "message_for_contact":
            response = self.handle_message_for_contact(user_input)
        elif intent == "end_conversation":
            response = self.get_conversation_ending_response(st.session_state.get('user_display_name', ''))
        elif intent == "continue_conversation":
            response = self.get_conversation_continuation_response()
            st.session_state.awaiting_closure_response = False  # Reset state
        elif intent == "availability":
            response = self.get_availability_response(context, is_casual, is_formal)
        elif intent == "salary":
            response = self.get_salary_response(context, is_casual, is_formal)
        elif intent == "location":
            response = self.get_location_response(context, is_casual, is_formal)
        elif intent == "company_culture":
            response = self.get_culture_response(context, is_casual, is_formal)
        elif intent == "future":
            response = self.get_future_response(context, is_casual, is_formal)
        else:
            response = self.get_general_response(is_casual)
        
        # Check if we should offer conversation closure after the response
        message_count = len(st.session_state.messages) // 2  # Approximate exchange count
        if (self.should_offer_conversation_closure(user_input, message_count) and 
            not st.session_state.get('awaiting_closure_response', False)):
            # Add the closure offer to the response
            response += "\n\n" + self.get_conversation_closure_offer()
            st.session_state.awaiting_closure_response = True
            
        return response, intent
    
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
        phone_pattern = r'(\+?\d{1,4}[-.\s]?\(?\d{1,3}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9})'
        phone_match = re.search(phone_pattern, user_input)
        
        if phone_match:
            phone_number = phone_match.group(1)
            return f"""Got it! I'll let Aniket know to contact you at {phone_number}. He'll follow up within 1-2 business days.

You can also reach him directly at ashirsat@iu.edu or on LinkedIn at https://www.linkedin.com/in/aniketshirsatsg/"""
        else:
            return """I'll make sure Aniket sees your message. He'll follow up within 1-2 business days.

You can also reach him directly at ashirsat@iu.edu, call +1 463 279 6071, or connect on LinkedIn at https://www.linkedin.com/in/aniketshirsatsg/"""
    
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
    """Simple chatbot with required name and optional email"""
    st.set_page_config(
        page_title="Chat with Aniket's AI Assistant",
        page_icon="💬",
        layout="centered"
    )
    
    # Clean CSS
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
        st.session_state.session_id = f"simple_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Simple initialization - name required, email optional
    if "asking_for_name" not in st.session_state:
        st.session_state.asking_for_name = False
    if "asking_for_name_confirmation" not in st.session_state:
        st.session_state.asking_for_name_confirmation = False
    if "asking_for_email" not in st.session_state:
        st.session_state.asking_for_email = False
    if "user_name" not in st.session_state:
        st.session_state.user_name = ""
    if "user_email" not in st.session_state:
        st.session_state.user_email = ""
    if "user_display_name" not in st.session_state:
        st.session_state.user_display_name = ""
    
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
    
    # Dynamic chat input placeholders
    if st.session_state.asking_for_name:
        placeholder = "Enter your name..."
    elif st.session_state.asking_for_name_confirmation:
        placeholder = "Please let me know how you'd like to be addressed..."
    elif st.session_state.asking_for_email:
        placeholder = "Enter your email address (or type 'skip' to continue without email)..."
    else:
        placeholder = "Ask about Aniket's skills, experience, projects, or why you should hire him..."
    
    if prompt := st.chat_input(placeholder):
        # Check if we need to reset conversation first
        if check_and_reset_if_needed():
            st.rerun()
            return
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        if st.session_state.asking_for_name:
            extracted_name = extract_name_from_input(prompt)
            
            if extracted_name:
                st.session_state.user_name = extracted_name
                st.session_state.asking_for_name = False
                st.session_state.asking_for_name_confirmation = True
                
                # Extract first name for simple confirmation
                name_parts = extracted_name.split()
                first_name = name_parts[0]
                
                response = f"Thank you! Should I call you {first_name}?"
                
                st.session_state.messages.append({"role": "assistant", "content": response})
            else:
                response = "I didn't catch your name clearly. Could you please tell me your full name? You can say something like 'My name is John Smith' or just 'John Smith'."
                st.session_state.messages.append({"role": "assistant", "content": response})
        
        elif st.session_state.asking_for_name_confirmation:
            # Handle name confirmation/correction with simple logic
            confirmation_lower = prompt.lower().strip()
            
            # Check if they said yes/agreed to the suggested first name
            if any(word in confirmation_lower for word in ["yes", "yeah", "yep", "sure", "ok", "okay", "that's fine", "sounds good", "correct", "right"]):
                # Use the first name as suggested
                name_parts = st.session_state.user_name.split()
                st.session_state.user_display_name = name_parts[0]
                response = f"Perfect, {st.session_state.user_display_name}! Could you please share your email address? (You can also type 'skip' if you prefer not to share it)"
            
            elif any(word in confirmation_lower for word in ["no", "nope", "actually", "call me", "prefer"]):
                # They want to be called something different
                corrected_name = None
                
                # Look for "call me [name]" pattern
                call_me_match = re.search(r'call me (\w+)', confirmation_lower)
                if call_me_match:
                    corrected_name = call_me_match.group(1).title()
                
                # Look for "prefer [name]" pattern
                prefer_match = re.search(r'prefer (\w+)', confirmation_lower)
                if prefer_match:
                    corrected_name = prefer_match.group(1).title()
                
                # Look for "actually [name]" pattern
                actually_match = re.search(r'actually (\w+)', confirmation_lower)
                if actually_match:
                    corrected_name = actually_match.group(1).title()
                
                # If no pattern found, try to extract any name from the response
                if not corrected_name:
                    extracted = extract_name_from_input(prompt)
                    if extracted:
                        corrected_name = extracted.split()[0]  # Take first word of extracted name
                
                # If still no name found, ask for clarification
                if not corrected_name:
                    response = "What would you prefer I call you?"
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    st.rerun()
                    return
                
                st.session_state.user_display_name = corrected_name
                response = f"Perfect, {st.session_state.user_display_name}! Could you please share your email address? (You can also type 'skip' if you prefer not to share it)"
            
            else:
                # They probably just said their preferred name directly
                corrected_name = extract_name_from_input(prompt)
                if corrected_name:
                    st.session_state.user_display_name = corrected_name.split()[0]  # Take first word
                else:
                    # Use their response as-is (cleaned up)
                    st.session_state.user_display_name = prompt.strip().title()
                
                response = f"Perfect, {st.session_state.user_display_name}! Could you please share your email address? (You can also type 'skip' if you prefer not to share it)"
            
            st.session_state.asking_for_name_confirmation = False
            st.session_state.asking_for_email = True
            st.session_state.messages.append({"role": "assistant", "content": response})
        
        elif st.session_state.asking_for_email:
            # Handle email collection with skip option
            if prompt.lower().strip() in ['skip', 'no', 'no thanks', 'not now', 'maybe later', 'pass']:
                st.session_state.asking_for_email = False
                response = f"No problem, {st.session_state.user_display_name}! I'm ready to answer questions about Aniket's professional background. What would you like to know?"
                st.session_state.messages.append({"role": "assistant", "content": response})
            else:
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
                    response = "That doesn't look like a valid email address. Please enter your email (e.g., john@company.com) or type 'skip' to continue without email."
                    st.session_state.messages.append({"role": "assistant", "content": response})
        
        else:
            # Normal chat - standard response system
            with st.spinner("🤖 Analyzing your question..."):
                response, intent = st.session_state.chatbot.generate_response(prompt)
            
            st.session_state.messages.append({"role": "assistant", "content": response})
            
            # Handle conversation ending
            if intent == "end_conversation":
                # End the conversation and reset for fresh start
                st.session_state.conversation_ending = True
                
                # Save final conversation thread
                if hasattr(st.session_state, 'conversation_thread') and st.session_state.conversation_thread:
                    # Add final user message to thread
                    st.session_state.conversation_thread.append({
                        'role': 'user',
                        'content': prompt,
                        'timestamp': datetime.now().isoformat()
                    })
                    # Add final bot response to thread
                    st.session_state.conversation_thread.append({
                        'role': 'assistant',
                        'content': response,
                        'intent': intent,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    save_complete_conversation(
                        st.session_state.session_id,
                        st.session_state.get('user_name', ''),
                        st.session_state.get('user_email', ''),
                        st.session_state.conversation_thread
                    )
                
                # Schedule reset for next interaction
                st.session_state.reset_on_next_message = True
            else:
                # Enhanced logging with conversation threads
                log_conversation_with_thread(
                    st.session_state.session_id,
                    prompt,
                    response,
                    intent,
                    st.session_state.user_name,
                    st.session_state.user_email
                )
        
        st.rerun()

# Reset check function
def check_and_reset_if_needed():
    """Check if we need to reset the conversation"""
    if st.session_state.get('reset_on_next_message', False):
        reset_conversation_session()
        st.session_state.reset_on_next_message = False
        return True
    return False

# Conversation thread tracking functions
def log_conversation_with_thread(session_id: str, user_message: str, bot_response: str, intent: str, user_name: str = "", user_email: str = ""):
    """Enhanced logging that maintains conversation threads"""
    
    # Log individual message (existing functionality)
    log_conversation_to_dashboard(session_id, user_message, bot_response, intent, user_name, user_email)
    
    # Build conversation thread
    if 'conversation_thread' not in st.session_state:
        st.session_state.conversation_thread = []
    
    # Add user message
    st.session_state.conversation_thread.append({
        'role': 'user',
        'content': user_message,
        'timestamp': datetime.now().isoformat()
    })
    
    # Add bot response
    st.session_state.conversation_thread.append({
        'role': 'assistant',
        'content': bot_response,
        'intent': intent,
        'timestamp': datetime.now().isoformat()
    })
    
    # Save thread periodically (every 10 messages) or when session ends
    if len(st.session_state.conversation_thread) % 10 == 0:  # Every 5 exchanges
        save_complete_conversation(
            session_id, 
            user_name, 
            user_email, 
            st.session_state.conversation_thread.copy()
        )

def reset_conversation_session():
    """Reset the conversation session for a fresh start"""
    # Save the current conversation thread before resetting
    if hasattr(st.session_state, 'conversation_thread') and st.session_state.conversation_thread:
        save_complete_conversation(
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
    
    # Create new session ID
    st.session_state.session_id = f"simple_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Reset conversation state
    st.session_state.awaiting_closure_response = False
    st.session_state.conversation_thread = []
    st.session_state.asking_for_email = False
    
    # Set fresh greeting message
    greeting_name = f" {user_display_name}" if user_display_name else ""
    st.session_state.messages = [
        {
            "role": "assistant", 
            "content": f"Hello{greeting_name}! I'm ready to help with any new questions about Aniket's background, skills, or experience. What would you like to know?"
        }
    ]

def save_complete_conversation(session_id: str, user_name: str, user_email: str, conversation_messages: List[Dict]):
    """Save complete conversation thread"""
    try:
        db = get_shared_db()
        data = db._load_gist_data()
        
        # Create conversation thread entry
        conversation_thread = {
            "session_id": session_id,
            "user_name": user_name,
            "user_email": user_email,
            "start_time": conversation_messages[0]['timestamp'] if conversation_messages else datetime.now().isoformat(),
            "end_time": conversation_messages[-1]['timestamp'] if conversation_messages else datetime.now().isoformat(),
            "total_messages": len(conversation_messages),
            "conversation_flow": conversation_messages,  # Complete conversation
            "saved_at": datetime.now().isoformat()
        }
        
        # Add to conversation threads
        if "conversation_threads" not in data:
            data["conversation_threads"] = []
        
        data["conversation_threads"].append(conversation_thread)
        data["last_updated"] = datetime.now().isoformat()
        
        return db._save_gist_data(data)
        
    except Exception as e:
        return False

if __name__ == "__main__":
    main()
