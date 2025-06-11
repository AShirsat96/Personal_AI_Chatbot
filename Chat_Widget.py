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

# 🔗 SHARED DATABASE CLASS (copied from dashboard)
class GitHubGistDatabase:
    """Free shared database using GitHub Gist - SAME as dashboard"""
    
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
            "conversations": [],  # 📊 NEW: Store full conversations
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
    
    # 📊 NEW: Conversation logging for dashboard analytics
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
            # Don't show error to user for conversation logging
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

# Initialize shared database
@st.cache_resource
def get_shared_db():
    """Get shared database instance"""
    return GitHubGistDatabase()

# 🔄 UPDATED: Use shared database instead of session state
def save_user_info(name: str, email: str, session_id: str) -> bool:
    """Save user info to SHARED database (connects to dashboard!)"""
    db = get_shared_db()
    return db.save_user_interaction(name, email, session_id)

def log_conversation_to_dashboard(session_id: str, user_message: str, bot_response: str, intent: str, user_name: str = "", user_email: str = "") -> bool:
    """Log conversation to dashboard for live analytics"""
    db = get_shared_db()
    return db.log_conversation(session_id, user_message, bot_response, intent, user_name, user_email)

def get_shared_avatar() -> Optional[str]:
    """Get avatar from shared database (synced with dashboard)"""
    db = get_shared_db()
    return db.get_avatar()

class SmartHybridChatbot:
    """Intelligent hybrid chatbot that works without any APIs"""
    
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
            "unique_value": "Combines academic excellence with proven ability to deliver quantifiable business results"
        }
        
        # Conversation patterns for natural interaction
        self.conversation_patterns = {
            "greetings": ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"],
            "thanks": ["thank", "thanks", "appreciate", "grateful"],
            "goodbye": ["bye", "goodbye", "see you", "farewell", "take care"]
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
    
    def analyze_intent(self, user_input: str) -> str:
        """Analyze user intent from input with enhanced natural language understanding"""
        input_lower = user_input.lower()
        
        # Enhanced conversation patterns
        if any(pattern in input_lower for pattern in ["hello", "hi", "hey", "good morning", "good afternoon", "good evening", "what's up", "sup"]):
            return "greeting"
        elif any(pattern in input_lower for pattern in ["thank", "thanks", "appreciate", "grateful", "awesome", "cool", "nice", "great job"]):
            return "thanks"
        elif any(pattern in input_lower for pattern in ["bye", "goodbye", "see you", "farewell", "take care", "gotta go", "talk later"]):
            return "goodbye"
        
        # Enhanced question patterns with more natural language
        enhanced_patterns = {
            "hiring": [
                "hire", "why", "recommend", "choose", "recruit", "employ", "candidate", "fit", "right person",
                "should we", "good choice", "worth it", "value", "benefit", "advantage", "perfect for"
            ],
            "skills": [
                "skill", "technical", "programming", "tech", "abilities", "competencies", "expertise", "tools", "technologies",
                "what can he do", "good at", "proficient", "experienced in", "knows how to"
            ],
            "education": [
                "education", "school", "degree", "gpa", "university", "academic", "study", "learn", "college",
                "where did he study", "educational background", "qualifications"
            ],
            "experience": [
                "experience", "work", "job", "employment", "career", "professional", "background", "history",
                "worked at", "previous", "past experience", "work history"
            ],
            "projects": [
                "project", "research", "built", "created", "developed", "worked on", "achievement", "accomplishment",
                "what has he done", "portfolio", "examples of work", "showcase"
            ],
            "personal": [
                "hobby", "hobbies", "interest", "interests", "personal", "outside work", "free time", "activities",
                "fun", "personality", "character", "who is he", "about him personally"
            ],
            "contact": [
                "contact", "reach", "connect", "email", "phone", "linkedin", "get in touch", "hire him",
                "how to reach", "connect with", "talk to", "meeting"
            ],
            "availability": [
                "available", "start", "when", "timeline", "notice", "free", "open to",
                "can he start", "availability", "ready to work"
            ],
            "salary": [
                "salary", "compensation", "pay", "money", "cost", "rate", "price",
                "how much", "expensive", "budget", "compensation expectations"
            ],
            "location": [
                "location", "where", "based", "remote", "relocate", "move",
                "lives", "located", "willing to move", "work from"
            ],
            "company_culture": [
                "culture", "team", "environment", "fit", "values", "work style",
                "team player", "cultural fit", "personality fit", "collaborative"
            ],
            "future": [
                "future", "goals", "plans", "career path", "ambition", "vision",
                "wants to do", "aspirations", "long term", "growth"
            ]
        }
        
        # Score intents based on enhanced patterns
        intent_scores = {}
        for intent, patterns in enhanced_patterns.items():
            score = sum(1 for pattern in patterns if pattern in input_lower)
            if score > 0:
                intent_scores[intent] = score
        
        # Return the intent with highest score, or general if none
        if intent_scores:
            return max(intent_scores, key=intent_scores.get)
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
        """Generate intelligent response based on intent analysis - Returns (response, intent)"""
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
            
        return response, intent
    
    def get_greeting_response(self, is_casual: bool = False) -> str:
        if is_casual:
            return """Hey there! 👋 Great to meet you!

I'm Aniket's AI assistant, and I'm here to chat about his professional background and what makes him such a great candidate.

He's currently crushing it in his Master's program at Indiana University Indianapolis with a perfect 4.0 GPA while working as a Research Assistant. Pretty impressive, right?

What would you like to know about him? His technical skills? Cool projects he's worked on? Or maybe why he'd be an awesome addition to your team?"""
        else:
            return """Hello! It's wonderful to meet you! 👋 

I'm Aniket's AI assistant, and I'm here to help you learn about his professional background and qualifications. 

Aniket is currently pursuing his Master's in Applied Data Science at Indiana University Indianapolis with a perfect 4.0 GPA while working as a Research Assistant. His combination of academic excellence and practical experience makes him quite remarkable.

What would you like to know about him? I can share details about his skills, experience, projects, or why he'd be an excellent addition to your team!"""
    
    def get_thanks_response(self, is_casual: bool = False) -> str:
        if is_casual:
            return """You're totally welcome! 😊 Happy to help!

I love talking about Aniket - he's got such an impressive background. Got any other questions about his experience or what he's been working on? I'm here for it!"""
        else:
            return """You're very welcome! 😊

I'm delighted I could help you learn more about Aniket. His background really speaks for itself - the combination of academic excellence and real-world impact is quite remarkable.

Please feel free to ask about anything else you'd like to know - his technical expertise, project details, or career aspirations. I'm here to help!"""
    
    def get_goodbye_response(self, is_casual: bool = False) -> str:
        if is_casual:
            return """Thanks for checking out Aniket! 👋

Hope I gave you a good sense of what an awesome candidate he is. If you want to connect with him about opportunities, definitely reach out - he's actively looking and would love to chat!

Catch you later! 🚀"""
        else:
            return """Thank you so much for your interest in Aniket Shirsat! 👋

I sincerely hope our conversation has given you valuable insights into his qualifications and the exceptional value he could bring to your organization. 

If you'd like to connect with Aniket directly, please don't hesitate to reach out through his professional channels. He's actively pursuing new opportunities and would be thrilled to discuss how his skills and experience align with your needs.

Wishing you a wonderful day ahead!"""
    
    def get_hiring_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        base_response = f"""🎯 **Why Aniket Shirsat is an Exceptional Hire**

**🎓 Academic Excellence**
• Perfect {self.aniket_data['education']['current']['gpa']} GPA in {self.aniket_data['education']['current']['degree']}
• {self.aniket_data['personal_info']['current_role']} while maintaining academic excellence
• Previous {self.aniket_data['education']['previous']['degree']} provides business acumen

**💼 Proven Business Impact**
• {self.aniket_data['experience']['key_projects'][1]['result']}
• {self.aniket_data['experience']['key_projects'][1]['impact']}
• {self.aniket_data['experience']['key_projects'][0]['result']}

**🛠️ Technical Expertise**
• Programming: {', '.join(self.aniket_data['technical_skills']['programming'])}
• Cloud Platforms: {', '.join(self.aniket_data['technical_skills']['cloud_platforms'])}
• AI/ML: {', '.join(self.aniket_data['technical_skills']['ai_ml'])}

**🏆 Leadership & Character**
• {self.aniket_data['leadership'][0]}
• {self.aniket_data['leadership'][1]}

**🎯 The Bottom Line**
{self.aniket_data['unique_value']} - a rare combination that makes him invaluable for data science teams looking for both technical depth and business impact."""

        if context["wants_details"]:
            base_response += f"""

**📊 Detailed Impact Metrics:**
• Cultural Ambiguity Detection: Achieved {self.aniket_data['experience']['key_projects'][0]['result']}
• Vessel Optimization: Delivered {self.aniket_data['experience']['key_projects'][1]['impact']} saving {self.aniket_data['experience']['key_projects'][1]['result']}
• Academic Performance: Maintained perfect GPA while conducting active research"""

        return base_response
    
    def get_skills_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        skills = self.aniket_data['technical_skills']
        
        response = f"""💻 **Aniket's Technical Skill Portfolio**

**🔧 Programming Languages**
{', '.join(skills['programming'])} - Production-level proficiency

**☁️ Cloud & Infrastructure** 
{', '.join(skills['cloud_platforms'])} - Full-stack cloud development

**🤖 AI/ML Expertise**
{', '.join(skills['ai_ml'])} - Advanced implementation experience

**🎯 Specialized Capabilities**
{', '.join(skills['specializations'])}

**💡 What Sets Him Apart**
• Combines technical depth with business understanding
• Proven ability to deliver quantifiable results ({self.aniket_data['experience']['key_projects'][1]['result']})
• Academic rigor meets practical application
• Cross-functional collaboration through leadership roles"""

        if context["wants_examples"]:
            response += f"""

**🔍 Skill Application Examples:**
• **Python/ML**: Built cultural ambiguity detection models achieving 90% accuracy
• **Optimization Algorithms**: Developed vessel fuel systems saving $1M+ annually  
• **Cloud Platforms**: Deployed scalable ML solutions for 50+ vessel fleet
• **Research**: Published-quality work while maintaining 4.0 GPA"""

        return response
    
    def get_education_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        edu = self.aniket_data['education']
        
        response = f"""🎓 **Educational Excellence**

**Current Program**
• {edu['current']['degree']} at {edu['current']['university']}
• GPA: Perfect {edu['current']['gpa']} 
• Role: {self.aniket_data['personal_info']['current_role']}

**Previous Education**
• {edu['previous']['degree']} from {edu['previous']['university']}
• International experience providing global perspective

**🏆 Academic Achievements**
• {self.aniket_data['achievements'][0]}
• Active research producing measurable results
• Balancing coursework with practical application

**💼 The Advantage**
This combination of business education + technical depth creates a unique profile - someone who can build sophisticated ML models AND understand their business impact."""

        if context["wants_details"]:
            response += f"""

**📚 Academic Focus Areas:**
• Advanced Machine Learning & AI
• Computer Vision & NLP
• Statistical Analysis & Data Science
• Business Strategy & Management
• Research Methodologies"""

        return response
    
    def get_experience_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        response = f"""💼 **Professional Experience Highlights**

**Current Role**
{self.aniket_data['experience']['current_role']}

**🚀 Key Projects & Results**

**Cultural Ambiguity Detection System**
• Developed ML models for advertisement analysis
• Achieved: {self.aniket_data['experience']['key_projects'][0]['result']}
• Domain: {self.aniket_data['experience']['key_projects'][0]['domain']}

**Vessel Fuel Optimization Platform** 
• Built predictive optimization algorithms
• Impact: {self.aniket_data['experience']['key_projects'][1]['impact']}
• Business Value: {self.aniket_data['experience']['key_projects'][1]['result']}

**🎯 Leadership Experience**
• {self.aniket_data['leadership'][0]}
• {self.aniket_data['leadership'][1]}

**💡 What This Demonstrates**
Aniket doesn't just build models - he delivers solutions that create measurable business value while maintaining the highest academic standards."""

        return response
    
    def get_projects_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        projects = self.aniket_data['experience']['key_projects']
        
        response = f"""🔬 **Research & Project Portfolio**

**Project 1: Cultural Ambiguity Detection**
• **Goal**: Analyze cultural ambiguity in advertisements
• **Approach**: Advanced NLP and ML techniques
• **Result**: {projects[0]['result']}
• **Impact**: Improved ad targeting and cultural sensitivity

**Project 2: Vessel Fuel Optimization**
• **Goal**: Optimize fuel consumption for maritime fleet
• **Approach**: Predictive modeling and optimization algorithms  
• **Result**: {projects[1]['result']}
• **Impact**: {projects[1]['impact']} across 50+ vessels

**🎯 Project Characteristics**
• Real-world business applications
• Quantifiable, measurable outcomes
• Cross-disciplinary approach (AI + Business)
• Scalable solutions"""

        if context["wants_details"]:
            response += f"""

**🔧 Technical Implementation**
• **Data Pipeline**: End-to-end data processing and analysis
• **Model Development**: Custom ML algorithms for specific use cases  
• **Deployment**: Production-ready systems with monitoring
• **Optimization**: Continuous improvement based on performance metrics"""

        return response
    
    def get_personal_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return f"""🚣‍♂️ **Beyond the Resume**

**Athletic Commitment**
{self.aniket_data['leadership'][1]}
• Demonstrates: Teamwork, discipline, physical fitness
• Shows: Ability to balance multiple demanding commitments

**Community Leadership**
{self.aniket_data['leadership'][0]}
• Develops: Communication and mentoring skills
• Builds: Data science community and knowledge sharing

**Personal Interests**
• **Continuous Learning**: Stays current with latest AI/ML developments
• **Research Passion**: Enjoys tackling complex, real-world problems
• **Collaborative Spirit**: Thrives in team environments

**🎯 What This Reveals**
Aniket is a well-rounded individual who excels not just technically, but also in leadership, teamwork, and community building - exactly the type of person who elevates entire teams."""
    
    def get_contact_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return f"""📞 **Getting in Touch with Aniket**

**Current Status**: {self.aniket_data['career_goals']}

**Best Approach**: 
Please reach out through his professional channels for direct contact information. He's actively engaging with potential employers and responds promptly to opportunities.

**What to Mention**:
• Specific role or opportunity details
• How his background aligns with your needs
• Timeline and next steps

**📋 What He Can Provide**:
• Detailed portfolio of projects and results
• References from academic and professional work
• Demonstration of technical capabilities
• Discussion of how he can contribute to your team

Aniket is genuinely excited about opportunities to apply his skills in real-world business contexts and would welcome the chance to discuss how he can contribute to your organization's success."""
    
    def get_availability_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return f"""📅 **Availability & Timeline**

**Current Status**: 
• {self.aniket_data['personal_info']['current_status']}
• {self.aniket_data['experience']['current_role']}
• {self.aniket_data['career_goals']}

**Availability**:
• Open to discussing full-time opportunities
• Can provide flexible start dates based on mutual agreement
• Currently balancing academic and research commitments

**Ideal Timeline**:
• Available for interviews and discussions immediately
• Can accommodate varying start date requirements
• Committed to smooth transition planning

**🎯 Key Point**:
Aniket is seriously pursuing his next career step and is prepared to discuss how his academic schedule can align with the right opportunity. His research experience demonstrates his ability to deliver results even with multiple commitments."""
    
    def get_salary_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return f"""💼 **Compensation Considerations**

**Approach to Compensation**:
Aniket is primarily focused on finding the right role where he can apply his skills and grow professionally. He's open to discussing competitive compensation packages appropriate for his experience level and the value he brings.

**What He Offers**:
• Proven ability to deliver measurable business results ({self.aniket_data['experience']['key_projects'][1]['result']})
• Advanced technical skills in high-demand areas
• Academic excellence and research experience
• Leadership and collaborative capabilities

**Discussion Framework**:
• Open to market-rate compensation for data science roles
• Values opportunities for growth and learning
• Interested in comprehensive packages including development opportunities
• Flexible on structure based on company practices

**💡 Value Perspective**:
Given his track record of delivering $1M+ in business value while maintaining academic excellence, Aniket represents an investment in both immediate capability and long-term potential."""
    
    def get_location_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return f"""📍 **Location & Work Preferences**

**Current Location**: 
Based in Indianapolis, Indiana (Indiana University Indianapolis area)

**Work Flexibility**:
• Open to remote, hybrid, or on-site arrangements
• Willing to relocate for the right opportunity
• Experienced with remote collaboration through research work

**Geographic Considerations**:
• U.S.-based with valid work authorization
• Previous international experience ({self.aniket_data['education']['previous']['university']})
• Comfortable with diverse, global team environments

**🎯 Flexibility**:
Aniket's priority is finding a role where he can make meaningful contributions. He's open to discussing location arrangements that work for both the company and his professional development goals."""
    
    def get_culture_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return f"""🤝 **Cultural Fit & Work Style**

**Demonstrated Values**:
• **Excellence**: Perfect {self.aniket_data['education']['current']['gpa']} GPA while conducting research
• **Impact-Driven**: Focus on measurable business results
• **Collaborative**: {self.aniket_data['leadership'][0]}
• **Balanced**: {self.aniket_data['leadership'][1]}

**Work Style Strengths**:
• **Analytical**: Systematic approach to problem-solving
• **Results-Oriented**: Track record of delivering quantifiable outcomes
• **Continuous Learner**: Stays current with industry developments
• **Team Player**: Experience in leadership and mentoring roles

**Cultural Adaptability**:
• International education background
• Cross-functional project experience
• Academic and business environment navigation
• Diverse team collaboration

**🎯 Ideal Environment**:
Thrives in cultures that value innovation, learning, measurable impact, and collaborative problem-solving. His background suggests he'd excel in data-driven organizations that appreciate both technical depth and business understanding."""
    
    def get_future_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return f"""🚀 **Career Vision & Future Goals**

**Immediate Goals**:
• Transition from academic research to industry application
• Apply ML/AI skills to solve real business challenges
• Join a team where he can make immediate impact while continuing to grow

**Medium-term Aspirations**:
• Become a technical leader in data science/ML
• Build solutions that drive significant business value
• Mentor others and contribute to team development

**Long-term Vision**:
• Establish expertise in specialized areas (Cultural AI, Optimization, etc.)
• Lead strategic data science initiatives
• Bridge the gap between technical innovation and business strategy

**🎯 What Drives Him**:
Based on his track record ({self.aniket_data['experience']['key_projects'][1]['result']}), Aniket is motivated by creating tangible value through advanced analytics. He sees AI/ML as tools for solving meaningful business problems, not just academic exercises.

**💡 Growth Mindset**:
His combination of perfect academic performance with practical results suggests someone who will continue pushing boundaries while delivering consistent value to any organization."""
    
    def get_general_response(self, is_casual: bool = False) -> str:
        return f"""👋 **About Aniket Shirsat**

**🎓 Current Status**
{self.aniket_data['personal_info']['current_status']} with a perfect {self.aniket_data['education']['current']['gpa']} GPA, working as {self.aniket_data['personal_info']['current_role']}

**🏆 Standout Achievements**
• {self.aniket_data['achievements'][1]}
• {self.aniket_data['achievements'][2]}
• {self.aniket_data['achievements'][3]}

**💻 Core Technical Skills**
Programming: {', '.join(self.aniket_data['technical_skills']['programming'])} | Cloud: {', '.join(self.aniket_data['technical_skills']['cloud_platforms'])} | AI/ML: Machine Learning, Computer Vision, NLP

**🎯 Currently Seeking**
{self.aniket_data['career_goals']} where he can apply his unique combination of technical expertise and business impact.

**❓ What would you like to know?**
• Why should we hire him?
• What are his technical skills?
• Tell me about his projects
• What's his educational background?
• How can we get in touch?"""

def main():
    """Hybrid Chatbot - Clean interface for embedding"""
    st.set_page_config(
        page_title="Chat with Aniket's AI Assistant",
        page_icon="💬",
        layout="centered"
    )
    
    # AGGRESSIVE CSS TO REMOVE ALL EMPTY SPACE
    st.markdown("""
    <style>
        /* AGGRESSIVE REMOVAL OF ALL STREAMLIT PADDING/MARGINS */
        .stApp {
            margin: 0 !important;
            padding: 0 !important;
            background: #f5f7fa;
        }
        
        .stApp > header {
            visibility: hidden !important;
            height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        
        .stApp > .main {
            margin: 0 !important;
            padding: 0 !important;
            max-width: 100% !important;
        }
        
        .stApp > .main > div:nth-child(1) {
            padding: 0 !important;
            margin: 0 !important;
        }
        
        /* Remove all Streamlit default spacing */
        .block-container {
            padding: 0 !important;
            margin: 0 !important;
            max-width: 100% !important;
        }
        
        .css-1d391kg, .css-k1ih3n, .css-18e3th9 {
            padding: 0 !important;
            margin: 0 !important;
        }
        
        div[data-testid="stVerticalBlock"] > div:first-child {
            margin-top: 0 !important;
            padding-top: 0 !important;
        }
        
        /* Hide all Streamlit UI elements */
        .stDeployButton {display: none !important;}
        .stDecoration {display: none !important;}
        #MainMenu {visibility: hidden !important;}
        footer {visibility: hidden !important;}
        div[data-testid="stToolbar"] {display: none !important;}
        div[data-testid="stDecoration"] {display: none !important;}
        div[data-testid="stStatusWidget"] {display: none !important;}
        
        /* FIXED: Chat container with NO TOP MARGIN */
        .chat-container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
            overflow: hidden;
            max-width: 420px;
            margin: 0 auto !important;  /* CHANGED: Removed 20px top margin */
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
            object-fit: cover;
        }
        
        .chat-title h3 {
            margin: 0;
            font-size: 18px;
            font-weight: 600;
        }
        
        .chat-subtitle {
            margin: 5px 0 0 0;
            font-size: 14px;
            opacity: 0.9;
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
        
        .assistant-avatar {
            width: 35px;
            height: 35px;
            border-radius: 50%;
            object-fit: cover;
            flex-shrink: 0;
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
        
        .suggested-questions {
            padding: 10px 20px;
            border-top: 1px solid #e1e8ed;
            background: #fafbfc;
        }
        
        .suggestion-chip {
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 6px 12px;
            margin: 3px;
            border-radius: 15px;
            font-size: 12px;
            cursor: pointer;
            border: none;
        }
        
        .suggestion-chip:hover {
            background: #5a6fd8;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize hybrid chatbot
    if "chatbot" not in st.session_state:
        st.session_state.chatbot = SmartHybridChatbot()
    
    # Generate session ID
    if "session_id" not in st.session_state:
        st.session_state.session_id = f"hybrid_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(datetime.now()) % 10000}"
    
    # Initialize user info states
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
    
    # Initialize messages
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
    
    # Main chat container
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    # Chat header - CLEAN VERSION (no subtitle)
    shared_avatar = get_shared_avatar()
    if shared_avatar:
        avatar_src = shared_avatar
    else:
        # Default avatar
        avatar_src = "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNTAiIGhlaWdodD0iNTAiIHZpZXdCb3g9IjAgMCA1MCA1MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iMjUiIGN5PSIyNSIgcj0iMjUiIGZpbGw9IiM2NjdlZWEiLz4KPHN2ZyB4PSIxMiIgeT0iMTIiIHdpZHRoPSIyNiIgaGVpZ2h0PSIyNiIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPgo8cGF0aCBkPSJNMTIgMTJDMTQuNzYxNCAxMiAxNyA5Ljc2MTQyIDE3IDdDMTcgNC4yMzg1OCAxNC43NjE0IDIgMTIgMkM5LjIzODU4IDIgNyA0LjIzODU4IDcgN0M3IDkuNzYxNDIgOS4yMzg1OCAxMiAxMiAxMlpNMTIgMTRDOC42ODYyOSAxNCA2IDE2LjIzODYgNiAxOUg2QzYgMjEuNzYxNCA4LjIzODU4IDI0IDExIDI0SDEzQzE1Ljc2MTQgMjQgMTggMjEuNzYxNCAxOCAxOUg2QzYgMTYuMjM4NiA5LjMxMzcxIDE0IDEyIDE0WiIgZmlsbD0id2hpdGUiLz4KPC9zdmc+Cjwvc3ZnPgo="
    
    st.markdown(f"""
    <div class="chat-header">
        <img src="{avatar_src}" class="chat-avatar" alt="Aniket's Avatar">
        <div class="chat-title">
            <h3>Aniket's AI Assistant</h3>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Messages container
    st.markdown('<div class="message-container">', unsafe_allow_html=True)
    
    # Display messages - FIXED VERSION (no yellow boxes, consistent avatars)
    for message in st.session_state.messages:
        if message["role"] == "assistant":
            # Use the same avatar as header for consistency
            if shared_avatar:
                bot_avatar_display = f'<img src="{shared_avatar}" style="width: 35px; height: 35px; border-radius: 50%; object-fit: cover; flex-shrink: 0;">'
            else:
                bot_avatar_display = '<div style="width: 35px; height: 35px; background: #667eea; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 18px; flex-shrink: 0;">🤖</div>'
            
            message_html = f"""
            <div class="assistant-message">
                {bot_avatar_display}
                <div class="message-bubble">{message["content"]}</div>
            </div>
            """
            st.markdown(message_html, unsafe_allow_html=True)
        else:
            user_html = f"""
            <div class="user-message">
                <div class="user-bubble">{message["content"]}</div>
            </div>
            """
            st.markdown(user_html, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)  # Close message-container
    
    # Suggested questions after info collection
    if st.session_state.user_info_collected:
        st.markdown('<div class="suggested-questions">', unsafe_allow_html=True)
        st.markdown('<p style="margin: 0 0 8px 0; font-size: 12px; color: #666; font-weight: 500;">💡 Popular Questions:</p>', unsafe_allow_html=True)
        
        suggestions = [
            "Why should I hire Aniket?",
            "What are his technical skills?", 
            "Tell me about his projects",
            "What's his educational background?",
            "What are his career goals?",
            "How can we contact him?"
        ]
        
        # Create responsive grid of suggestion buttons
        cols = st.columns(3)
        for i, suggestion in enumerate(suggestions):
            with cols[i % 3]:
                if st.button(suggestion, key=f"suggest_{i}", 
                           help=f"Ask: {suggestion}",
                           use_container_width=True):
                    # Add suggestion as user message and generate response
                    st.session_state.messages.append({"role": "user", "content": suggestion})
                    response, intent = st.session_state.chatbot.generate_response(suggestion)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    
                    # 📊 LOG CONVERSATION TO DASHBOARD
                    log_conversation_to_dashboard(
                        st.session_state.session_id,
                        suggestion,
                        response,
                        intent,
                        st.session_state.user_name,
                        st.session_state.user_email
                    )
                    
                    st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)  # Close chat-container
    
    # Chat input
    if st.session_state.asking_for_name:
        placeholder = "Enter your name..."
    elif st.session_state.asking_for_email:
        placeholder = "Enter your email address..."
    else:
        placeholder = "Ask about Aniket's skills, experience, projects, or why you should hire him..."
    
    if prompt := st.chat_input(placeholder):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        if st.session_state.asking_for_name:
            # Try to extract name from natural language
            extracted_name = extract_name_from_input(prompt)
            
            if extracted_name:
                st.session_state.user_name = extracted_name
                st.session_state.asking_for_name = False
                st.session_state.asking_for_email = True
                
                response = f"Thank you, {st.session_state.user_name}! Could you please share your email address?"
                st.session_state.messages.append({"role": "assistant", "content": response})
            else:
                response = "I didn't catch your name. Could you please tell me your name? You can say something like 'My name is John' or just 'John'."
                st.session_state.messages.append({"role": "assistant", "content": response})
        
        elif st.session_state.asking_for_email:
            # Try to extract email from natural language first
            extracted_email = extract_email_from_input(prompt)
            
            if extracted_email and is_valid_email(extracted_email):
                st.session_state.user_email = extracted_email
                st.session_state.asking_for_email = False
                st.session_state.user_info_collected = True
                
                # 🔗 SAVE USER INFO TO SHARED DATABASE
                save_user_info(st.session_state.user_name, st.session_state.user_email, st.session_state.session_id)
                
                response = f"Perfect! Thank you, {st.session_state.user_name}. I'm ready to answer questions about Aniket's professional background. What would you like to know?"
                
                st.session_state.messages.append({"role": "assistant", "content": response})
            elif is_valid_email(prompt.strip()):
                # Fallback to simple email validation
                st.session_state.user_email = prompt.strip()
                st.session_state.asking_for_email = False
                st.session_state.user_info_collected = True
                
                # 🔗 SAVE USER INFO TO SHARED DATABASE
                save_user_info(st.session_state.user_name, st.session_state.user_email, st.session_state.session_id)
                
                response = f"Perfect! Thank you, {st.session_state.user_name}. I'm ready to answer questions about Aniket's professional background. What would you like to know?"
                
                st.session_state.messages.append({"role": "assistant", "content": response})
            else:
                response = "That doesn't look like a valid email address. Please enter your email (e.g., john@company.com) or include it in a sentence like 'My email is john@company.com'."
                st.session_state.messages.append({"role": "assistant", "content": response})
        
        else:
            # Normal chat using hybrid AI
            with st.spinner("🤖 Analyzing your question..."):
                response, intent = st.session_state.chatbot.generate_response(prompt)
            
            st.session_state.messages.append({"role": "assistant", "content": response})
            
            # 📊 LOG CONVERSATION TO DASHBOARD
            log_conversation_to_dashboard(
                st.session_state.session_id,
                prompt,
                response,
                intent,
                st.session_state.user_name,
                st.session_state.user_email
            )
        
        st.rerun()

    # NO FOOTER - Clean interface ends here

if __name__ == "__main__":
    main()
