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
    """Extract name from natural language input - SUPPORTS FULL NAMES"""
    input_lower = user_input.lower().strip()
    
    # Remove common greetings and punctuation
    input_clean = re.sub(r'[^\w\s]', '', input_lower)
    
    # Common patterns for name introduction - UPDATED TO CAPTURE FULL NAMES
    name_patterns = [
        r'(?:hello|hi|hey)\s+(?:my\s+name\s+is|i\s*am|i\'m)\s+(.+)',
        r'(?:my\s+name\s+is|i\s*am|i\'m)\s+(.+)',
        r'(?:hello|hi|hey)\s+(.+?)(?:\s+here)?

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
    """Intelligent hybrid chatbot with full response capabilities"""
    
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
        
        # Question intent patterns - RESTORED FULL VERSION
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
        """Analyze user intent from input with enhanced natural language understanding - COMPREHENSIVE VERSION"""
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
        """Generate intelligent response based on intent analysis - FULL VERSION"""
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
    
    # RESTORED ALL DETAILED RESPONSE METHODS
    
    def get_greeting_response(self, is_casual: bool = False) -> str:
        return """Hello! I'm Aniket's AI assistant, here to help you learn about his professional background and qualifications.

Aniket is currently pursuing his Master's in Applied Data Science at Indiana University Indianapolis with a perfect 4.0 GPA while working as a Research Assistant.

What would you like to know about him? I can share details about his skills, experience, projects, or why he'd be an excellent addition to your team."""
    
    def get_thanks_response(self, is_casual: bool = False) -> str:
        return """You're welcome! I'm glad I could help you learn more about Aniket.

If you have any other questions about his background, skills, projects, or qualifications, please feel free to ask. Is there anything specific about his experience or technical expertise you'd like to explore further?"""
    
    def get_goodbye_response(self, is_casual: bool = False) -> str:
        return """Thank you for your interest in Aniket Shirsat.

I hope the information has been helpful in understanding his qualifications and potential value to your organization. If you'd like to connect with Aniket directly, please reach out through his professional channels. He's actively pursuing new opportunities and would be pleased to discuss how his skills and experience align with your needs.

Have a great day!"""
    
    def get_hiring_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        base_response = f"""I would strongly recommend considering Aniket for your organization. He demonstrates an exceptional combination of academic excellence and measurable business impact.

He maintains a perfect {self.aniket_data['education']['current']['gpa']} GPA in his {self.aniket_data['education']['current']['degree']} while serving as a {self.aniket_data['personal_info']['current_role']}. This demonstrates his ability to manage multiple demanding responsibilities effectively.

His business impact is particularly noteworthy. His vessel fuel optimization project delivered {self.aniket_data['experience']['key_projects'][1]['result']} with a {self.aniket_data['experience']['key_projects'][1]['impact']}. Additionally, his cultural ambiguity detection work achieved {self.aniket_data['experience']['key_projects'][0]['result']}.

From a technical perspective, he is proficient in {', '.join(self.aniket_data['technical_skills']['programming'])}, experienced with {', '.join(self.aniket_data['technical_skills']['cloud_platforms'])}, and has hands-on expertise in {', '.join(self.aniket_data['technical_skills']['ai_ml'])}.

Furthermore, he brings leadership experience as {self.aniket_data['leadership'][0]} and maintains active involvement with {self.aniket_data['leadership'][1]}. This combination ensures you would be hiring someone capable of delivering results, leading teams, and applying academic rigor to practical business challenges."""

        if context["wants_details"]:
            base_response += f"""\n\nTo provide specific metrics, the cultural ambiguity detection models he developed are performing at {self.aniket_data['experience']['key_projects'][0]['result']}, which represents excellent performance for this type of natural language processing work. The vessel optimization system operates across 50+ vessels and consistently delivers the projected fuel savings."""

        return base_response
    
    def get_skills_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        skills = self.aniket_data['technical_skills']
        
        response = f"""Aniket possesses a comprehensive technical foundation. He is proficient in {', '.join(skills['programming'])} for programming and development, which covers the essential requirements for data science applications.

In cloud computing, he has experience with {', '.join(skills['cloud_platforms'])}, enabling him to deploy and scale solutions effectively. His artificial intelligence and machine learning expertise encompasses {', '.join(skills['ai_ml'])}, and importantly, he has applied these technologies in real-world projects rather than purely academic contexts.

What distinguishes him is his ability to translate technical capabilities into measurable business value. His vessel optimization project generated over one million dollars in annual savings, and his cultural ambiguity detection models achieve 90% accuracy in production environments."""

        if context["wants_examples"]:
            response += f"""\n\nFor example, he developed cultural ambiguity detection models using advanced natural language processing techniques and achieved 90% accuracy. The vessel fuel optimization system he created utilizes predictive modeling and currently operates across 50+ vessels. His experience encompasses the complete pipeline: data processing, model development, deployment, and monitoring."""

        return response
    
    def get_education_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        edu = self.aniket_data['education']
        
        response = f"""Aniket's educational background is highly impressive. He is currently pursuing his {edu['current']['degree']} at {edu['current']['university']} while maintaining a perfect {edu['current']['gpa']} GPA and simultaneously serving as a {self.aniket_data['personal_info']['current_role']}.

His academic portfolio also includes a {edu['previous']['degree']} from {edu['previous']['university']}. This business foundation is evident in his approach to technical problems, where he focuses on creating solutions with clear business impact rather than purely theoretical applications.

His ability to maintain perfect academic performance while conducting meaningful research demonstrates exceptional time management skills and his capacity to deliver high-quality work under demanding circumstances."""

        if context["wants_details"]:
            response += f"""\n\nHis current program emphasizes advanced machine learning, computer vision, natural language processing, and statistical analysis. The management background provides him with business strategy perspective that is uncommon among technical candidates, creating a valuable and rare combination of skills."""

        return response
    
    def get_experience_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        response = f"""Aniket currently serves as a {self.aniket_data['experience']['current_role']} while completing his Master's degree, which represents a significant professional achievement. The quality and impact of his work are particularly noteworthy.

He developed a cultural ambiguity detection system that analyzes advertisements for cultural sensitivity. The models he created achieve {self.aniket_data['experience']['key_projects'][0]['result']}, which represents excellent performance for this type of natural language processing application.

His vessel fuel optimization project demonstrates substantial business impact. He created predictive algorithms that generate {self.aniket_data['experience']['key_projects'][1]['result']} through a {self.aniket_data['experience']['key_projects'][1]['impact']} across 50+ vessels. This represents quantifiable value creation that directly impacts organizational performance.

Additionally, he serves as {self.aniket_data['leadership'][0]} and maintains active participation in {self.aniket_data['leadership'][1]}. This demonstrates his commitment to balancing technical expertise, leadership responsibilities, and personal development."""

        return response
    
    def get_projects_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        projects = self.aniket_data['experience']['key_projects']
        
        response = f"""Aniket has been developing projects that demonstrate both technical proficiency and business acumen.

His cultural ambiguity detection project addresses the important challenge of analyzing advertisements for potential cultural sensitivities. The approach utilizes advanced natural language processing and machine learning techniques, achieving {projects[0]['result']}. This type of capability is increasingly valuable for organizations with global reach.

The vessel fuel optimization project demonstrates clear business impact. He developed predictive modeling algorithms that optimize fuel consumption for maritime fleets. The system currently operates across 50+ vessels, delivering {projects[1]['impact']} and translating to {projects[1]['result']} in annual savings.

Both projects represent practical solutions to real business challenges with measurable outcomes, reflecting the type of strategic thinking valuable in data science applications."""

        if context["wants_details"]:
            response += f"""\n\nFrom a technical implementation perspective, he has developed complete end-to-end pipelines encompassing data processing, custom machine learning algorithm development, production deployment, and ongoing monitoring. The cultural detection work required sophisticated natural language processing preprocessing, while the vessel optimization demanded real-time predictive capabilities."""

        return response
    
    def get_personal_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return f"""Beyond his technical qualifications, Aniket demonstrates well-rounded personal development. He is a member of the {self.aniket_data['leadership'][1]}, which reflects his commitment to discipline and collaborative teamwork. Rowing requires significant coordination and dedication, qualities that translate effectively to professional environments.

He also serves as {self.aniket_data['leadership'][0]}, demonstrating his commitment to community building and mentoring others in the field. This indicates leadership potential and a collaborative approach to professional development.

His interests reflect a genuine passion for learning and addressing complex challenges. He stays current with developments in artificial intelligence and machine learning, and demonstrates enthusiasm for applying academic concepts to practical business problems.

The combination of athletic discipline, community leadership, and intellectual curiosity suggests an individual capable of performing under pressure, collaborating effectively, and maintaining continuous professional growth."""
    
    def get_contact_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return f"""Aniket is {self.aniket_data['career_goals'].lower()}, and therefore welcomes discussions regarding potential opportunities.

The most effective approach would be to connect through his professional networks, particularly LinkedIn or through his university contacts. He has demonstrated responsiveness to inquiries from potential employers.

When reaching out, it would be beneficial to specify the role or opportunity under consideration and how his background aligns with your requirements. He is particularly interested in positions where he can apply his machine learning and optimization expertise to address genuine business challenges.

He can provide a comprehensive portfolio of his work, references from his research activities, and is prepared to conduct technical demonstrations if that would support your evaluation process."""
    
    def get_availability_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return f"""Aniket is currently completing his {self.aniket_data['personal_info']['current_status'].lower()} while serving as a {self.aniket_data['personal_info']['current_role'].lower()}, and he is {self.aniket_data['career_goals'].lower()}.

He is available for interviews and discussions immediately. Regarding start dates, he demonstrates flexibility and can accommodate arrangements that work for both parties. His research experience has involved managing multiple concurrent commitments, providing him with the skills to navigate transition periods effectively.

It is important to note that he is actively pursuing his next career step rather than casually exploring opportunities. When he identifies the appropriate fit, he is prepared to make the necessary arrangements from a timing perspective.

Given his active job search status, I would recommend initiating conversations promptly if there is potential interest."""
    
    def get_salary_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return f"""Aniket approaches compensation discussions with a professional and reasonable perspective. He prioritizes finding the appropriate role where he can apply his skills and continue professional development over maximizing initial compensation.

However, he brings substantial value to any organization. His track record includes {self.aniket_data['experience']['key_projects'][1]['result']} in documented business impact, combined with advanced technical skills in high-demand areas.

He is open to discussing competitive compensation packages appropriate for data science roles at his experience level. He values opportunities for professional development and is interested in comprehensive packages that extend beyond base salary considerations.

Given his accomplishments in both academic excellence and practical business results, he represents both immediate capability and strong long-term potential. Most organizations would find the investment in his capabilities to be highly worthwhile."""
    
    def get_location_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return f"""Aniket is currently based in Indianapolis due to his studies at Indiana University Indianapolis, but he demonstrates considerable flexibility regarding location arrangements.

He is open to remote work arrangements, hybrid configurations, or relocation for appropriate opportunities. His research experience has involved substantial remote collaboration, making him comfortable with distributed team environments.

His international background from his time at {self.aniket_data['education']['previous']['university']} has prepared him for working with diverse teams and adapting to various work environments and cultural contexts.

His primary focus is identifying a role where he can make meaningful contributions rather than being constrained by geographic limitations. He is willing to discuss arrangements that align with organizational needs and role requirements."""
    
    def get_culture_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return f"""Aniket appears well-suited for most data-driven organizations. His perfect {self.aniket_data['education']['current']['gpa']} GPA while conducting research demonstrates a high-performance mindset, while his leadership role as {self.aniket_data['leadership'][0]} shows his ability to work collaboratively.

His involvement with {self.aniket_data['leadership'][1]} demonstrates his understanding of teamwork and discipline. His international background from {self.aniket_data['education']['previous']['university']} has prepared him for working effectively with diverse teams.

He would likely thrive in a culture that values both innovation and measurable impact. He has demonstrated capability in working independently on complex problems while also mentoring others and building community. Organizations that encourage collaboration and continuous learning would be particularly appealing.

Given his track record of delivering measurable business results while maintaining academic excellence, he would be most effective in environments that appreciate both technical depth and practical problem-solving capabilities."""
    
    def get_future_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return f"""Aniket has developed a clear vision for his career progression. In the short term, he seeks to transition from academic research into industry applications where he can apply his machine learning and artificial intelligence expertise to address genuine business challenges.

Looking ahead, he aspires to become a technical leader in the data science field. Based on his track record with projects such as the vessel optimization that delivered {self.aniket_data['experience']['key_projects'][1]['result']}, he demonstrates the appropriate mindset, viewing AI and ML as tools for creating measurable business value rather than purely academic exercises.

Long-term, he is interested in leading strategic data science initiatives and potentially developing expertise in specialized areas such as cultural AI or optimization systems. His management background provides him with business perspective that would be valuable as he progresses into leadership roles.

His motivation centers on bridging the gap between cutting-edge technical work and practical business impact. This combination of academic rigor with real-world results suggests he will continue advancing boundaries while consistently delivering value."""
    
    def get_general_response(self, is_casual: bool = False) -> str:
        return f"""Aniket Shirsat is currently pursuing his {self.aniket_data['personal_info']['current_status'].lower()} with a perfect {self.aniket_data['education']['current']['gpa']} GPA while serving as a {self.aniket_data['personal_info']['current_role'].lower()}.

His distinguishing characteristic is the measurable business impact he has already generated. His accomplishments include achieving {self.aniket_data['achievements'][1]}, delivering {self.aniket_data['achievements'][2]}, and maintaining {self.aniket_data['achievements'][4]}.

From a technical perspective, he is proficient in {', '.join(self.aniket_data['technical_skills']['programming'])}, experienced with {', '.join(self.aniket_data['technical_skills']['cloud_platforms'])}, and has hands-on experience with machine learning, computer vision, and natural language processing.

He brings leadership experience as {self.aniket_data['leadership'][0]} and maintains active involvement with {self.aniket_data['leadership'][1]}. This combination of academic excellence, technical expertise, and leadership capabilities makes him well-suited for data science and machine learning roles.

Currently, he is {self.aniket_data['career_goals'].lower()} where he can apply his combination of technical expertise and business understanding to drive meaningful organizational impact."""

def main():
    """Full-featured chatbot with NO suggested questions interface"""
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
    
    # Initialize - FULL VERSION
    if "chatbot" not in st.session_state:
        st.session_state.chatbot = SmartHybridChatbot()
    
    if "session_id" not in st.session_state:
        st.session_state.session_id = f"full_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
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
    
    # Chat input logic with enhanced name handling
    if st.session_state.asking_for_name:
        placeholder = "Enter your name..."
    elif st.session_state.asking_for_name_confirmation:
        placeholder = "Please let me know how you'd like to be addressed..."
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
                response = f"Perfect, {st.session_state.user_display_name}! Could you please share your email address?"
            
            elif any(word in confirmation_lower for word in ["no", "nope", "actually", "call me", "prefer"]):
                # They want to be called something different
                # Try to extract their preferred name from their response
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
                response = f"Perfect, {st.session_state.user_display_name}! Could you please share your email address?"
            
            else:
                # They probably just said their preferred name directly
                # Try to extract a name from their response
                corrected_name = extract_name_from_input(prompt)
                if corrected_name:
                    st.session_state.user_display_name = corrected_name.split()[0]  # Take first word
                else:
                    # Use their response as-is (cleaned up)
                    st.session_state.user_display_name = prompt.strip().title()
                
                response = f"Perfect, {st.session_state.user_display_name}! Could you please share your email address?"
            
            st.session_state.asking_for_name_confirmation = False
            st.session_state.asking_for_email = True
            st.session_state.messages.append({"role": "assistant", "content": response})
        
        elif st.session_state.asking_for_email:
            extracted_email = extract_email_from_input(prompt)
            
            if extracted_email and is_valid_email(extracted_email):
                st.session_state.user_email = extracted_email
                st.session_state.asking_for_email = False
                st.session_state.user_info_collected = True
                
                save_user_info(st.session_state.user_name, st.session_state.user_email, st.session_state.session_id)
                
                response = f"Perfect! Thank you, {st.session_state.user_display_name}. I'm ready to answer questions about Aniket's professional background. What would you like to know?"
                st.session_state.messages.append({"role": "assistant", "content": response})
            
            elif is_valid_email(prompt.strip()):
                st.session_state.user_email = prompt.strip()
                st.session_state.asking_for_email = False
                st.session_state.user_info_collected = True
                
                save_user_info(st.session_state.user_name, st.session_state.user_email, st.session_state.session_id)
                
                response = f"Perfect! Thank you, {st.session_state.user_display_name}. I'm ready to answer questions about Aniket's professional background. What would you like to know?"
                st.session_state.messages.append({"role": "assistant", "content": response})
            
            else:
                response = "That doesn't look like a valid email address. Please enter your email (e.g., john@company.com)."
                st.session_state.messages.append({"role": "assistant", "content": response})
        
        else:
            # Normal chat - FULL RESPONSE SYSTEM
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
    main(),
        r'(?:this\s+is|its)\s+(.+)',
        r'(.+?)\s+here

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
    """Intelligent hybrid chatbot with full response capabilities"""
    
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
        
        # Question intent patterns - RESTORED FULL VERSION
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
        """Analyze user intent from input with enhanced natural language understanding - COMPREHENSIVE VERSION"""
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
        """Generate intelligent response based on intent analysis - FULL VERSION"""
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
    
    # RESTORED ALL DETAILED RESPONSE METHODS
    
    def get_greeting_response(self, is_casual: bool = False) -> str:
        return """Hello! I'm Aniket's AI assistant, here to help you learn about his professional background and qualifications.

Aniket is currently pursuing his Master's in Applied Data Science at Indiana University Indianapolis with a perfect 4.0 GPA while working as a Research Assistant.

What would you like to know about him? I can share details about his skills, experience, projects, or why he'd be an excellent addition to your team."""
    
    def get_thanks_response(self, is_casual: bool = False) -> str:
        return """You're welcome! I'm glad I could help you learn more about Aniket.

If you have any other questions about his background, skills, projects, or qualifications, please feel free to ask. Is there anything specific about his experience or technical expertise you'd like to explore further?"""
    
    def get_goodbye_response(self, is_casual: bool = False) -> str:
        return """Thank you for your interest in Aniket Shirsat.

I hope the information has been helpful in understanding his qualifications and potential value to your organization. If you'd like to connect with Aniket directly, please reach out through his professional channels. He's actively pursuing new opportunities and would be pleased to discuss how his skills and experience align with your needs.

Have a great day!"""
    
    def get_hiring_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        base_response = f"""I would strongly recommend considering Aniket for your organization. He demonstrates an exceptional combination of academic excellence and measurable business impact.

He maintains a perfect {self.aniket_data['education']['current']['gpa']} GPA in his {self.aniket_data['education']['current']['degree']} while serving as a {self.aniket_data['personal_info']['current_role']}. This demonstrates his ability to manage multiple demanding responsibilities effectively.

His business impact is particularly noteworthy. His vessel fuel optimization project delivered {self.aniket_data['experience']['key_projects'][1]['result']} with a {self.aniket_data['experience']['key_projects'][1]['impact']}. Additionally, his cultural ambiguity detection work achieved {self.aniket_data['experience']['key_projects'][0]['result']}.

From a technical perspective, he is proficient in {', '.join(self.aniket_data['technical_skills']['programming'])}, experienced with {', '.join(self.aniket_data['technical_skills']['cloud_platforms'])}, and has hands-on expertise in {', '.join(self.aniket_data['technical_skills']['ai_ml'])}.

Furthermore, he brings leadership experience as {self.aniket_data['leadership'][0]} and maintains active involvement with {self.aniket_data['leadership'][1]}. This combination ensures you would be hiring someone capable of delivering results, leading teams, and applying academic rigor to practical business challenges."""

        if context["wants_details"]:
            base_response += f"""\n\nTo provide specific metrics, the cultural ambiguity detection models he developed are performing at {self.aniket_data['experience']['key_projects'][0]['result']}, which represents excellent performance for this type of natural language processing work. The vessel optimization system operates across 50+ vessels and consistently delivers the projected fuel savings."""

        return base_response
    
    def get_skills_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        skills = self.aniket_data['technical_skills']
        
        response = f"""Aniket possesses a comprehensive technical foundation. He is proficient in {', '.join(skills['programming'])} for programming and development, which covers the essential requirements for data science applications.

In cloud computing, he has experience with {', '.join(skills['cloud_platforms'])}, enabling him to deploy and scale solutions effectively. His artificial intelligence and machine learning expertise encompasses {', '.join(skills['ai_ml'])}, and importantly, he has applied these technologies in real-world projects rather than purely academic contexts.

What distinguishes him is his ability to translate technical capabilities into measurable business value. His vessel optimization project generated over one million dollars in annual savings, and his cultural ambiguity detection models achieve 90% accuracy in production environments."""

        if context["wants_examples"]:
            response += f"""\n\nFor example, he developed cultural ambiguity detection models using advanced natural language processing techniques and achieved 90% accuracy. The vessel fuel optimization system he created utilizes predictive modeling and currently operates across 50+ vessels. His experience encompasses the complete pipeline: data processing, model development, deployment, and monitoring."""

        return response
    
    def get_education_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        edu = self.aniket_data['education']
        
        response = f"""Aniket's educational background is highly impressive. He is currently pursuing his {edu['current']['degree']} at {edu['current']['university']} while maintaining a perfect {edu['current']['gpa']} GPA and simultaneously serving as a {self.aniket_data['personal_info']['current_role']}.

His academic portfolio also includes a {edu['previous']['degree']} from {edu['previous']['university']}. This business foundation is evident in his approach to technical problems, where he focuses on creating solutions with clear business impact rather than purely theoretical applications.

His ability to maintain perfect academic performance while conducting meaningful research demonstrates exceptional time management skills and his capacity to deliver high-quality work under demanding circumstances."""

        if context["wants_details"]:
            response += f"""\n\nHis current program emphasizes advanced machine learning, computer vision, natural language processing, and statistical analysis. The management background provides him with business strategy perspective that is uncommon among technical candidates, creating a valuable and rare combination of skills."""

        return response
    
    def get_experience_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        response = f"""Aniket currently serves as a {self.aniket_data['experience']['current_role']} while completing his Master's degree, which represents a significant professional achievement. The quality and impact of his work are particularly noteworthy.

He developed a cultural ambiguity detection system that analyzes advertisements for cultural sensitivity. The models he created achieve {self.aniket_data['experience']['key_projects'][0]['result']}, which represents excellent performance for this type of natural language processing application.

His vessel fuel optimization project demonstrates substantial business impact. He created predictive algorithms that generate {self.aniket_data['experience']['key_projects'][1]['result']} through a {self.aniket_data['experience']['key_projects'][1]['impact']} across 50+ vessels. This represents quantifiable value creation that directly impacts organizational performance.

Additionally, he serves as {self.aniket_data['leadership'][0]} and maintains active participation in {self.aniket_data['leadership'][1]}. This demonstrates his commitment to balancing technical expertise, leadership responsibilities, and personal development."""

        return response
    
    def get_projects_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        projects = self.aniket_data['experience']['key_projects']
        
        response = f"""Aniket has been developing projects that demonstrate both technical proficiency and business acumen.

His cultural ambiguity detection project addresses the important challenge of analyzing advertisements for potential cultural sensitivities. The approach utilizes advanced natural language processing and machine learning techniques, achieving {projects[0]['result']}. This type of capability is increasingly valuable for organizations with global reach.

The vessel fuel optimization project demonstrates clear business impact. He developed predictive modeling algorithms that optimize fuel consumption for maritime fleets. The system currently operates across 50+ vessels, delivering {projects[1]['impact']} and translating to {projects[1]['result']} in annual savings.

Both projects represent practical solutions to real business challenges with measurable outcomes, reflecting the type of strategic thinking valuable in data science applications."""

        if context["wants_details"]:
            response += f"""\n\nFrom a technical implementation perspective, he has developed complete end-to-end pipelines encompassing data processing, custom machine learning algorithm development, production deployment, and ongoing monitoring. The cultural detection work required sophisticated natural language processing preprocessing, while the vessel optimization demanded real-time predictive capabilities."""

        return response
    
    def get_personal_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return f"""Beyond his technical qualifications, Aniket demonstrates well-rounded personal development. He is a member of the {self.aniket_data['leadership'][1]}, which reflects his commitment to discipline and collaborative teamwork. Rowing requires significant coordination and dedication, qualities that translate effectively to professional environments.

He also serves as {self.aniket_data['leadership'][0]}, demonstrating his commitment to community building and mentoring others in the field. This indicates leadership potential and a collaborative approach to professional development.

His interests reflect a genuine passion for learning and addressing complex challenges. He stays current with developments in artificial intelligence and machine learning, and demonstrates enthusiasm for applying academic concepts to practical business problems.

The combination of athletic discipline, community leadership, and intellectual curiosity suggests an individual capable of performing under pressure, collaborating effectively, and maintaining continuous professional growth."""
    
    def get_contact_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return f"""Aniket is {self.aniket_data['career_goals'].lower()}, and therefore welcomes discussions regarding potential opportunities.

The most effective approach would be to connect through his professional networks, particularly LinkedIn or through his university contacts. He has demonstrated responsiveness to inquiries from potential employers.

When reaching out, it would be beneficial to specify the role or opportunity under consideration and how his background aligns with your requirements. He is particularly interested in positions where he can apply his machine learning and optimization expertise to address genuine business challenges.

He can provide a comprehensive portfolio of his work, references from his research activities, and is prepared to conduct technical demonstrations if that would support your evaluation process."""
    
    def get_availability_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return f"""Aniket is currently completing his {self.aniket_data['personal_info']['current_status'].lower()} while serving as a {self.aniket_data['personal_info']['current_role'].lower()}, and he is {self.aniket_data['career_goals'].lower()}.

He is available for interviews and discussions immediately. Regarding start dates, he demonstrates flexibility and can accommodate arrangements that work for both parties. His research experience has involved managing multiple concurrent commitments, providing him with the skills to navigate transition periods effectively.

It is important to note that he is actively pursuing his next career step rather than casually exploring opportunities. When he identifies the appropriate fit, he is prepared to make the necessary arrangements from a timing perspective.

Given his active job search status, I would recommend initiating conversations promptly if there is potential interest."""
    
    def get_salary_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return f"""Aniket approaches compensation discussions with a professional and reasonable perspective. He prioritizes finding the appropriate role where he can apply his skills and continue professional development over maximizing initial compensation.

However, he brings substantial value to any organization. His track record includes {self.aniket_data['experience']['key_projects'][1]['result']} in documented business impact, combined with advanced technical skills in high-demand areas.

He is open to discussing competitive compensation packages appropriate for data science roles at his experience level. He values opportunities for professional development and is interested in comprehensive packages that extend beyond base salary considerations.

Given his accomplishments in both academic excellence and practical business results, he represents both immediate capability and strong long-term potential. Most organizations would find the investment in his capabilities to be highly worthwhile."""
    
    def get_location_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return f"""Aniket is currently based in Indianapolis due to his studies at Indiana University Indianapolis, but he demonstrates considerable flexibility regarding location arrangements.

He is open to remote work arrangements, hybrid configurations, or relocation for appropriate opportunities. His research experience has involved substantial remote collaboration, making him comfortable with distributed team environments.

His international background from his time at {self.aniket_data['education']['previous']['university']} has prepared him for working with diverse teams and adapting to various work environments and cultural contexts.

His primary focus is identifying a role where he can make meaningful contributions rather than being constrained by geographic limitations. He is willing to discuss arrangements that align with organizational needs and role requirements."""
    
    def get_culture_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return f"""Aniket appears well-suited for most data-driven organizations. His perfect {self.aniket_data['education']['current']['gpa']} GPA while conducting research demonstrates a high-performance mindset, while his leadership role as {self.aniket_data['leadership'][0]} shows his ability to work collaboratively.

His involvement with {self.aniket_data['leadership'][1]} demonstrates his understanding of teamwork and discipline. His international background from {self.aniket_data['education']['previous']['university']} has prepared him for working effectively with diverse teams.

He would likely thrive in a culture that values both innovation and measurable impact. He has demonstrated capability in working independently on complex problems while also mentoring others and building community. Organizations that encourage collaboration and continuous learning would be particularly appealing.

Given his track record of delivering measurable business results while maintaining academic excellence, he would be most effective in environments that appreciate both technical depth and practical problem-solving capabilities."""
    
    def get_future_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return f"""Aniket has developed a clear vision for his career progression. In the short term, he seeks to transition from academic research into industry applications where he can apply his machine learning and artificial intelligence expertise to address genuine business challenges.

Looking ahead, he aspires to become a technical leader in the data science field. Based on his track record with projects such as the vessel optimization that delivered {self.aniket_data['experience']['key_projects'][1]['result']}, he demonstrates the appropriate mindset, viewing AI and ML as tools for creating measurable business value rather than purely academic exercises.

Long-term, he is interested in leading strategic data science initiatives and potentially developing expertise in specialized areas such as cultural AI or optimization systems. His management background provides him with business perspective that would be valuable as he progresses into leadership roles.

His motivation centers on bridging the gap between cutting-edge technical work and practical business impact. This combination of academic rigor with real-world results suggests he will continue advancing boundaries while consistently delivering value."""
    
    def get_general_response(self, is_casual: bool = False) -> str:
        return f"""Aniket Shirsat is currently pursuing his {self.aniket_data['personal_info']['current_status'].lower()} with a perfect {self.aniket_data['education']['current']['gpa']} GPA while serving as a {self.aniket_data['personal_info']['current_role'].lower()}.

His distinguishing characteristic is the measurable business impact he has already generated. His accomplishments include achieving {self.aniket_data['achievements'][1]}, delivering {self.aniket_data['achievements'][2]}, and maintaining {self.aniket_data['achievements'][4]}.

From a technical perspective, he is proficient in {', '.join(self.aniket_data['technical_skills']['programming'])}, experienced with {', '.join(self.aniket_data['technical_skills']['cloud_platforms'])}, and has hands-on experience with machine learning, computer vision, and natural language processing.

He brings leadership experience as {self.aniket_data['leadership'][0]} and maintains active involvement with {self.aniket_data['leadership'][1]}. This combination of academic excellence, technical expertise, and leadership capabilities makes him well-suited for data science and machine learning roles.

Currently, he is {self.aniket_data['career_goals'].lower()} where he can apply his combination of technical expertise and business understanding to drive meaningful organizational impact."""

def main():
    """Full-featured chatbot with NO suggested questions interface"""
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
    
    # Initialize - FULL VERSION
    if "chatbot" not in st.session_state:
        st.session_state.chatbot = SmartHybridChatbot()
    
    if "session_id" not in st.session_state:
        st.session_state.session_id = f"full_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
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
            # Normal chat - FULL RESPONSE SYSTEM
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
    main(),
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
            valid_name_words = [word for word in name_words if word not in non_names and len(word) >= 2]
            
            if valid_name_words:
                # Capitalize each word properly
                return ' '.join(word.capitalize() for word in valid_name_words)
    
    # If no pattern matches, check if it's just a name without intro words
    words = input_clean.split()
    non_names = {
        'hello', 'hi', 'hey', 'good', 'morning', 'afternoon', 'evening',
        'my', 'name', 'is', 'am', 'im', 'this', 'its', 'here', 'there',
        'yes', 'no', 'ok', 'okay', 'sure', 'thanks', 'thank', 'you',
        'please', 'can', 'could', 'would', 'will', 'the', 'a', 'an'
    }
    
    # Filter out non-name words and keep valid name parts
    valid_words = [word for word in words if word not in non_names and len(word) >= 2]
    
    if valid_words:
        return ' '.join(word.capitalize() for word in valid_words)
    
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
    """Intelligent hybrid chatbot with full response capabilities"""
    
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
        
        # Question intent patterns - RESTORED FULL VERSION
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
        """Analyze user intent from input with enhanced natural language understanding - COMPREHENSIVE VERSION"""
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
        """Generate intelligent response based on intent analysis - FULL VERSION"""
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
    
    # RESTORED ALL DETAILED RESPONSE METHODS
    
    def get_greeting_response(self, is_casual: bool = False) -> str:
        return """Hello! I'm Aniket's AI assistant, here to help you learn about his professional background and qualifications.

Aniket is currently pursuing his Master's in Applied Data Science at Indiana University Indianapolis with a perfect 4.0 GPA while working as a Research Assistant.

What would you like to know about him? I can share details about his skills, experience, projects, or why he'd be an excellent addition to your team."""
    
    def get_thanks_response(self, is_casual: bool = False) -> str:
        return """You're welcome! I'm glad I could help you learn more about Aniket.

If you have any other questions about his background, skills, projects, or qualifications, please feel free to ask. Is there anything specific about his experience or technical expertise you'd like to explore further?"""
    
    def get_goodbye_response(self, is_casual: bool = False) -> str:
        return """Thank you for your interest in Aniket Shirsat.

I hope the information has been helpful in understanding his qualifications and potential value to your organization. If you'd like to connect with Aniket directly, please reach out through his professional channels. He's actively pursuing new opportunities and would be pleased to discuss how his skills and experience align with your needs.

Have a great day!"""
    
    def get_hiring_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        base_response = f"""I would strongly recommend considering Aniket for your organization. He demonstrates an exceptional combination of academic excellence and measurable business impact.

He maintains a perfect {self.aniket_data['education']['current']['gpa']} GPA in his {self.aniket_data['education']['current']['degree']} while serving as a {self.aniket_data['personal_info']['current_role']}. This demonstrates his ability to manage multiple demanding responsibilities effectively.

His business impact is particularly noteworthy. His vessel fuel optimization project delivered {self.aniket_data['experience']['key_projects'][1]['result']} with a {self.aniket_data['experience']['key_projects'][1]['impact']}. Additionally, his cultural ambiguity detection work achieved {self.aniket_data['experience']['key_projects'][0]['result']}.

From a technical perspective, he is proficient in {', '.join(self.aniket_data['technical_skills']['programming'])}, experienced with {', '.join(self.aniket_data['technical_skills']['cloud_platforms'])}, and has hands-on expertise in {', '.join(self.aniket_data['technical_skills']['ai_ml'])}.

Furthermore, he brings leadership experience as {self.aniket_data['leadership'][0]} and maintains active involvement with {self.aniket_data['leadership'][1]}. This combination ensures you would be hiring someone capable of delivering results, leading teams, and applying academic rigor to practical business challenges."""

        if context["wants_details"]:
            base_response += f"""\n\nTo provide specific metrics, the cultural ambiguity detection models he developed are performing at {self.aniket_data['experience']['key_projects'][0]['result']}, which represents excellent performance for this type of natural language processing work. The vessel optimization system operates across 50+ vessels and consistently delivers the projected fuel savings."""

        return base_response
    
    def get_skills_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        skills = self.aniket_data['technical_skills']
        
        response = f"""Aniket possesses a comprehensive technical foundation. He is proficient in {', '.join(skills['programming'])} for programming and development, which covers the essential requirements for data science applications.

In cloud computing, he has experience with {', '.join(skills['cloud_platforms'])}, enabling him to deploy and scale solutions effectively. His artificial intelligence and machine learning expertise encompasses {', '.join(skills['ai_ml'])}, and importantly, he has applied these technologies in real-world projects rather than purely academic contexts.

What distinguishes him is his ability to translate technical capabilities into measurable business value. His vessel optimization project generated over one million dollars in annual savings, and his cultural ambiguity detection models achieve 90% accuracy in production environments."""

        if context["wants_examples"]:
            response += f"""\n\nFor example, he developed cultural ambiguity detection models using advanced natural language processing techniques and achieved 90% accuracy. The vessel fuel optimization system he created utilizes predictive modeling and currently operates across 50+ vessels. His experience encompasses the complete pipeline: data processing, model development, deployment, and monitoring."""

        return response
    
    def get_education_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        edu = self.aniket_data['education']
        
        response = f"""Aniket's educational background is highly impressive. He is currently pursuing his {edu['current']['degree']} at {edu['current']['university']} while maintaining a perfect {edu['current']['gpa']} GPA and simultaneously serving as a {self.aniket_data['personal_info']['current_role']}.

His academic portfolio also includes a {edu['previous']['degree']} from {edu['previous']['university']}. This business foundation is evident in his approach to technical problems, where he focuses on creating solutions with clear business impact rather than purely theoretical applications.

His ability to maintain perfect academic performance while conducting meaningful research demonstrates exceptional time management skills and his capacity to deliver high-quality work under demanding circumstances."""

        if context["wants_details"]:
            response += f"""\n\nHis current program emphasizes advanced machine learning, computer vision, natural language processing, and statistical analysis. The management background provides him with business strategy perspective that is uncommon among technical candidates, creating a valuable and rare combination of skills."""

        return response
    
    def get_experience_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        response = f"""Aniket currently serves as a {self.aniket_data['experience']['current_role']} while completing his Master's degree, which represents a significant professional achievement. The quality and impact of his work are particularly noteworthy.

He developed a cultural ambiguity detection system that analyzes advertisements for cultural sensitivity. The models he created achieve {self.aniket_data['experience']['key_projects'][0]['result']}, which represents excellent performance for this type of natural language processing application.

His vessel fuel optimization project demonstrates substantial business impact. He created predictive algorithms that generate {self.aniket_data['experience']['key_projects'][1]['result']} through a {self.aniket_data['experience']['key_projects'][1]['impact']} across 50+ vessels. This represents quantifiable value creation that directly impacts organizational performance.

Additionally, he serves as {self.aniket_data['leadership'][0]} and maintains active participation in {self.aniket_data['leadership'][1]}. This demonstrates his commitment to balancing technical expertise, leadership responsibilities, and personal development."""

        return response
    
    def get_projects_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        projects = self.aniket_data['experience']['key_projects']
        
        response = f"""Aniket has been developing projects that demonstrate both technical proficiency and business acumen.

His cultural ambiguity detection project addresses the important challenge of analyzing advertisements for potential cultural sensitivities. The approach utilizes advanced natural language processing and machine learning techniques, achieving {projects[0]['result']}. This type of capability is increasingly valuable for organizations with global reach.

The vessel fuel optimization project demonstrates clear business impact. He developed predictive modeling algorithms that optimize fuel consumption for maritime fleets. The system currently operates across 50+ vessels, delivering {projects[1]['impact']} and translating to {projects[1]['result']} in annual savings.

Both projects represent practical solutions to real business challenges with measurable outcomes, reflecting the type of strategic thinking valuable in data science applications."""

        if context["wants_details"]:
            response += f"""\n\nFrom a technical implementation perspective, he has developed complete end-to-end pipelines encompassing data processing, custom machine learning algorithm development, production deployment, and ongoing monitoring. The cultural detection work required sophisticated natural language processing preprocessing, while the vessel optimization demanded real-time predictive capabilities."""

        return response
    
    def get_personal_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return f"""Beyond his technical qualifications, Aniket demonstrates well-rounded personal development. He is a member of the {self.aniket_data['leadership'][1]}, which reflects his commitment to discipline and collaborative teamwork. Rowing requires significant coordination and dedication, qualities that translate effectively to professional environments.

He also serves as {self.aniket_data['leadership'][0]}, demonstrating his commitment to community building and mentoring others in the field. This indicates leadership potential and a collaborative approach to professional development.

His interests reflect a genuine passion for learning and addressing complex challenges. He stays current with developments in artificial intelligence and machine learning, and demonstrates enthusiasm for applying academic concepts to practical business problems.

The combination of athletic discipline, community leadership, and intellectual curiosity suggests an individual capable of performing under pressure, collaborating effectively, and maintaining continuous professional growth."""
    
    def get_contact_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return f"""Aniket is {self.aniket_data['career_goals'].lower()}, and therefore welcomes discussions regarding potential opportunities.

The most effective approach would be to connect through his professional networks, particularly LinkedIn or through his university contacts. He has demonstrated responsiveness to inquiries from potential employers.

When reaching out, it would be beneficial to specify the role or opportunity under consideration and how his background aligns with your requirements. He is particularly interested in positions where he can apply his machine learning and optimization expertise to address genuine business challenges.

He can provide a comprehensive portfolio of his work, references from his research activities, and is prepared to conduct technical demonstrations if that would support your evaluation process."""
    
    def get_availability_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return f"""Aniket is currently completing his {self.aniket_data['personal_info']['current_status'].lower()} while serving as a {self.aniket_data['personal_info']['current_role'].lower()}, and he is {self.aniket_data['career_goals'].lower()}.

He is available for interviews and discussions immediately. Regarding start dates, he demonstrates flexibility and can accommodate arrangements that work for both parties. His research experience has involved managing multiple concurrent commitments, providing him with the skills to navigate transition periods effectively.

It is important to note that he is actively pursuing his next career step rather than casually exploring opportunities. When he identifies the appropriate fit, he is prepared to make the necessary arrangements from a timing perspective.

Given his active job search status, I would recommend initiating conversations promptly if there is potential interest."""
    
    def get_salary_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return f"""Aniket approaches compensation discussions with a professional and reasonable perspective. He prioritizes finding the appropriate role where he can apply his skills and continue professional development over maximizing initial compensation.

However, he brings substantial value to any organization. His track record includes {self.aniket_data['experience']['key_projects'][1]['result']} in documented business impact, combined with advanced technical skills in high-demand areas.

He is open to discussing competitive compensation packages appropriate for data science roles at his experience level. He values opportunities for professional development and is interested in comprehensive packages that extend beyond base salary considerations.

Given his accomplishments in both academic excellence and practical business results, he represents both immediate capability and strong long-term potential. Most organizations would find the investment in his capabilities to be highly worthwhile."""
    
    def get_location_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return f"""Aniket is currently based in Indianapolis due to his studies at Indiana University Indianapolis, but he demonstrates considerable flexibility regarding location arrangements.

He is open to remote work arrangements, hybrid configurations, or relocation for appropriate opportunities. His research experience has involved substantial remote collaboration, making him comfortable with distributed team environments.

His international background from his time at {self.aniket_data['education']['previous']['university']} has prepared him for working with diverse teams and adapting to various work environments and cultural contexts.

His primary focus is identifying a role where he can make meaningful contributions rather than being constrained by geographic limitations. He is willing to discuss arrangements that align with organizational needs and role requirements."""
    
    def get_culture_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return f"""Aniket appears well-suited for most data-driven organizations. His perfect {self.aniket_data['education']['current']['gpa']} GPA while conducting research demonstrates a high-performance mindset, while his leadership role as {self.aniket_data['leadership'][0]} shows his ability to work collaboratively.

His involvement with {self.aniket_data['leadership'][1]} demonstrates his understanding of teamwork and discipline. His international background from {self.aniket_data['education']['previous']['university']} has prepared him for working effectively with diverse teams.

He would likely thrive in a culture that values both innovation and measurable impact. He has demonstrated capability in working independently on complex problems while also mentoring others and building community. Organizations that encourage collaboration and continuous learning would be particularly appealing.

Given his track record of delivering measurable business results while maintaining academic excellence, he would be most effective in environments that appreciate both technical depth and practical problem-solving capabilities."""
    
    def get_future_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return f"""Aniket has developed a clear vision for his career progression. In the short term, he seeks to transition from academic research into industry applications where he can apply his machine learning and artificial intelligence expertise to address genuine business challenges.

Looking ahead, he aspires to become a technical leader in the data science field. Based on his track record with projects such as the vessel optimization that delivered {self.aniket_data['experience']['key_projects'][1]['result']}, he demonstrates the appropriate mindset, viewing AI and ML as tools for creating measurable business value rather than purely academic exercises.

Long-term, he is interested in leading strategic data science initiatives and potentially developing expertise in specialized areas such as cultural AI or optimization systems. His management background provides him with business perspective that would be valuable as he progresses into leadership roles.

His motivation centers on bridging the gap between cutting-edge technical work and practical business impact. This combination of academic rigor with real-world results suggests he will continue advancing boundaries while consistently delivering value."""
    
    def get_general_response(self, is_casual: bool = False) -> str:
        return f"""Aniket Shirsat is currently pursuing his {self.aniket_data['personal_info']['current_status'].lower()} with a perfect {self.aniket_data['education']['current']['gpa']} GPA while serving as a {self.aniket_data['personal_info']['current_role'].lower()}.

His distinguishing characteristic is the measurable business impact he has already generated. His accomplishments include achieving {self.aniket_data['achievements'][1]}, delivering {self.aniket_data['achievements'][2]}, and maintaining {self.aniket_data['achievements'][4]}.

From a technical perspective, he is proficient in {', '.join(self.aniket_data['technical_skills']['programming'])}, experienced with {', '.join(self.aniket_data['technical_skills']['cloud_platforms'])}, and has hands-on experience with machine learning, computer vision, and natural language processing.

He brings leadership experience as {self.aniket_data['leadership'][0]} and maintains active involvement with {self.aniket_data['leadership'][1]}. This combination of academic excellence, technical expertise, and leadership capabilities makes him well-suited for data science and machine learning roles.

Currently, he is {self.aniket_data['career_goals'].lower()} where he can apply his combination of technical expertise and business understanding to drive meaningful organizational impact."""

def main():
    """Full-featured chatbot with NO suggested questions interface"""
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
    
    # Initialize - FULL VERSION
    if "chatbot" not in st.session_state:
        st.session_state.chatbot = SmartHybridChatbot()
    
    if "session_id" not in st.session_state:
        st.session_state.session_id = f"full_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
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
            # Normal chat - FULL RESPONSE SYSTEM
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
