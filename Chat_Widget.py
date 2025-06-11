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
        
        # First check for specific question patterns - be more specific about greetings
        if any(word in input_lower for word in ["hello", "hi", "hey"]) and len(input_lower.split()) <= 3 and not any(word in input_lower for word in ["skill", "project", "hire", "experience"]):
            return "greeting"
        elif any(pattern in input_lower for pattern in ["thank", "thanks", "appreciate", "grateful"]) and not any(word in input_lower for word in ["skill", "project", "hire", "experience"]):
            return "thanks"
        elif any(pattern in input_lower for pattern in ["bye", "goodbye", "see you", "farewell", "take care"]):
            return "goodbye"
        
        # Enhanced question patterns - check these BEFORE greeting patterns
        if any(word in input_lower for word in ["hire", "why", "recommend", "choose", "recruit", "employ", "candidate", "should we", "good choice", "worth it", "benefit"]):
            return "hiring"
        elif any(word in input_lower for word in ["skill", "technical", "programming", "tech", "abilities", "competencies", "expertise", "tools", "technologies", "what can he do", "good at", "proficient"]):
            return "skills"
        elif any(word in input_lower for word in ["education", "school", "degree", "gpa", "university", "academic", "study", "college", "educational background", "qualifications"]):
            return "education"
        elif any(word in input_lower for word in ["experience", "work", "job", "employment", "career", "professional", "background", "history", "worked at", "previous"]):
            return "experience"
        elif any(word in input_lower for word in ["project", "research", "built", "created", "developed", "worked on", "achievement", "accomplishment", "portfolio", "examples"]):
            return "projects"
        elif any(word in input_lower for word in ["hobby", "hobbies", "interest", "interests", "personal", "outside work", "free time", "activities", "personality"]):
            return "personal"
        elif any(word in input_lower for word in ["contact", "reach", "connect", "email", "phone", "linkedin", "get in touch", "how to reach"]):
            return "contact"
        elif any(word in input_lower for word in ["available", "start", "when", "timeline", "notice", "free", "availability", "ready to work"]):
            return "availability"
        elif any(word in input_lower for word in ["salary", "compensation", "pay", "money", "cost", "rate", "price", "how much", "budget"]):
            return "salary"
        elif any(word in input_lower for word in ["location", "where", "based", "remote", "relocate", "move", "lives", "located"]):
            return "location"
        elif any(word in input_lower for word in ["culture", "team", "environment", "fit", "values", "work style", "team player", "collaborative"]):
            return "company_culture"
        elif any(word in input_lower for word in ["future", "goals", "plans", "career path", "ambition", "vision", "aspirations", "long term", "growth"]):
            return "future"
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
        base_response = f"""You should definitely consider Aniket! He's got this rare combination that's hard to find - top academic performance with real business results.

He's maintaining a perfect {self.aniket_data['education']['current']['gpa']} GPA in his {self.aniket_data['education']['current']['degree']} while working as a {self.aniket_data['personal_info']['current_role']}. That alone shows he can handle multiple demanding responsibilities.

But what really sets him apart is the business impact. His vessel fuel optimization project saved {self.aniket_data['experience']['key_projects'][1]['result']} with a {self.aniket_data['experience']['key_projects'][1]['impact']}. And his cultural ambiguity detection work achieved {self.aniket_data['experience']['key_projects'][0]['result']}.

He's technically solid too - knows {', '.join(self.aniket_data['technical_skills']['programming'])}, works with {', '.join(self.aniket_data['technical_skills']['cloud_platforms'])}, and has hands-on experience with {', '.join(self.aniket_data['technical_skills']['ai_ml'])}.

Plus he's got leadership experience as {self.aniket_data['leadership'][0]} and stays active with {self.aniket_data['leadership'][1]}. So you're getting someone who can deliver results, lead teams, and bring that academic rigor to real-world problems."""

        if context["wants_details"]:
            base_response += f"""\n\nIf you want specifics - the cultural ambiguity detection models he built are performing at {self.aniket_data['experience']['key_projects'][0]['result']}, which is pretty impressive for this type of work. The vessel optimization system is running across 50+ vessels and consistently delivering those fuel savings."""

        return base_response
    
    def get_skills_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        skills = self.aniket_data['technical_skills']
        
        response = f"""Aniket's got a really solid technical foundation. He's proficient in {', '.join(skills['programming'])} for programming, which covers most of what you'd need for data science work.

On the cloud side, he's worked with {', '.join(skills['cloud_platforms'])}, so he can deploy and scale solutions properly. His AI and ML experience includes {', '.join(skills['ai_ml'])}, and he's actually applied these in real projects, not just academic exercises.

What makes him different is that he's not just technically competent - he understands how to translate technical work into business value. His vessel optimization project saved over a million dollars annually, and his cultural ambiguity detection models are achieving 90% accuracy in production."""

        if context["wants_examples"]:
            response += f"""\n\nFor example, he built those cultural ambiguity detection models using advanced NLP techniques and achieved 90% accuracy. The vessel fuel optimization system he developed uses predictive modeling and is currently running across 50+ vessels. He's also done the full pipeline work - data processing, model development, deployment, and monitoring."""

        return response
    
    def get_education_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        edu = self.aniket_data['education']
        
        response = f"""Aniket's educational background is pretty impressive. He's currently working on his {edu['current']['degree']} at {edu['current']['university']} and maintaining a perfect {edu['current']['gpa']} GPA while also working as a {self.aniket_data['personal_info']['current_role']}.

What I think is interesting is that he also has a {edu['previous']['degree']} from {edu['previous']['university']}. That business background really shows in how he approaches technical problems - he's not just building models for the sake of it, he's thinking about real business impact.

The fact that he's keeping up perfect grades while doing actual research work tells you a lot about his ability to manage priorities and deliver quality work under pressure."""

        if context["wants_details"]:
            response += f"""\n\nHis current program focuses on advanced machine learning, computer vision, NLP, and statistical analysis. The management background gives him that business strategy perspective you don't usually see in technical candidates. It's a combination that's pretty rare."""

        return response
    
    def get_experience_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        response = f"""Aniket's been working as a {self.aniket_data['experience']['current_role']} while completing his Master's, which is no small feat. But what's really impressive is the kind of work he's been doing.

He built this cultural ambiguity detection system that analyzes advertisements for cultural sensitivity. The models he developed are hitting {self.aniket_data['experience']['key_projects'][0]['result']}, which is really solid performance for this type of NLP work.

Then there's his vessel fuel optimization project - this one's got real business impact. He created predictive algorithms that are saving {self.aniket_data['experience']['key_projects'][1]['result']} through a {self.aniket_data['experience']['key_projects'][1]['impact']} across 50+ vessels. That's the kind of work where you can directly see the value.

Outside of his research, he's also leading as {self.aniket_data['leadership'][0]} and stays involved with {self.aniket_data['leadership'][1]}. So he's got that balance of technical depth, leadership experience, and staying active."""

        return response
    
    def get_projects_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        projects = self.aniket_data['experience']['key_projects']
        
        response = f"""Aniket's been working on some really interesting projects that show both technical skill and business thinking.

His cultural ambiguity detection project is fascinating - he's analyzing advertisements to identify potential cultural sensitivities. The approach uses advanced NLP and machine learning techniques, and he's achieved {projects[0]['result']}. This kind of work is becoming really important for companies going global.

The vessel fuel optimization project is where you can see the business impact clearly. He built predictive modeling algorithms that help optimize fuel consumption for maritime fleets. The system is currently running across 50+ vessels and delivering {projects[1]['impact']}, which translates to {projects[1]['result']} in savings annually.

What I like about both projects is that they're not just academic exercises - they're solving real problems with measurable outcomes. That's the kind of thinking you want in a data scientist."""

        if context["wants_details"]:
            response += f"""\n\nFrom a technical standpoint, he's built complete end-to-end pipelines - data processing, custom ML algorithm development, deployment to production, and ongoing monitoring. The cultural detection work required sophisticated NLP preprocessing and the vessel optimization needed real-time predictive capabilities."""

        return response
    
    def get_personal_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return f"""Beyond all the technical stuff, Aniket's got a pretty well-rounded personality. He's a member of the {self.aniket_data['leadership'][1]}, which tells you he's disciplined and knows how to work as part of a team. Rowing is one of those sports that really requires coordination and commitment.

He's also {self.aniket_data['leadership'][0]}, so he's actively building the data science community and helping other students. That shows he's not just focused on his own success - he's thinking about lifting others up too.

From what I can tell, he's genuinely passionate about learning and tackling complex problems. He stays current with the latest developments in AI and ML, and he seems to really enjoy the challenge of applying academic concepts to real-world business problems.

The combination of athletic commitment, community leadership, and intellectual curiosity usually means you're dealing with someone who can handle pressure, work well with others, and keep growing professionally."""

        return response
    
    def get_contact_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return f"""Aniket is {self.aniket_data['career_goals'].lower()}, so he's definitely open to conversations about opportunities.

The best way to reach him would be through his professional channels - I'd recommend connecting via LinkedIn or reaching out through his university contacts. He's been pretty responsive to potential employers from what I understand.

When you do reach out, it would be helpful to mention the specific role or opportunity you're thinking about, and how his background might align with what you're looking for. He's particularly interested in positions where he can apply his ML and optimization skills to real business challenges.

He can provide a detailed portfolio of his work, references from his research, and he's usually happy to do a technical demonstration if that would be useful for your evaluation process."""

        return response
    
    def get_availability_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return f"""Aniket's in an interesting position right now. He's finishing up his {self.aniket_data['personal_info']['current_status'].lower()} while working as a {self.aniket_data['personal_info']['current_role'].lower()}, and he's {self.aniket_data['career_goals'].lower()}.

He's definitely available for interviews and discussions right away. As for start dates, he's pretty flexible and can work around what makes sense for both sides. His research work has given him experience managing multiple commitments, so he's comfortable navigating the transition period.

The key thing is that he's seriously looking for his next step and isn't just casually browsing opportunities. When he finds the right fit, he's prepared to make it work from a timing perspective.

I'd say if you're interested, it's worth having that conversation sooner rather than later since he's actively in the market."""

        return response
    
    def get_salary_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return f"""From what I understand, Aniket's approach to compensation is pretty reasonable. He's more focused on finding the right role where he can apply his skills and continue growing than on maximizing the initial salary.

That said, he's bringing some serious value to the table. His track record includes {self.aniket_data['experience']['key_projects'][1]['result']} in measurable business impact, plus advanced technical skills in areas that are really in demand right now.

He's open to discussing competitive packages that are appropriate for data science roles at his experience level. He values opportunities for professional development and is interested in comprehensive packages beyond just base salary.

Given what he's already accomplished - perfect academic performance plus real business results - he represents both immediate capability and strong long-term potential. I think most companies would find the investment worthwhile."""

        return response
    
    def get_location_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return f"""Aniket's currently based in Indianapolis since he's at Indiana University Indianapolis, but he's pretty flexible about location arrangements.

He's open to remote work, hybrid setups, or relocating for the right opportunity. His research experience has involved quite a bit of remote collaboration, so he's comfortable with distributed teams.

Having that international background from his time at {self.aniket_data['education']['previous']['university']} means he's used to working with diverse teams and adapting to different work environments.

I think his priority is really finding a role where he can make meaningful contributions rather than being tied to a specific location. He's willing to discuss whatever arrangement works best for the company and the role."""

        return response
    
    def get_culture_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return f"""Aniket seems like someone who'd fit well in most data-driven organizations. His perfect {self.aniket_data['education']['current']['gpa']} GPA while doing research shows he's got that high-performance mindset, but he's also shown he can work collaboratively through his leadership role as {self.aniket_data['leadership'][0]}.

The fact that he's involved with {self.aniket_data['leadership'][1]} tells you he understands teamwork and discipline. Plus his international background from {self.aniket_data['education']['previous']['university']} means he's comfortable working with diverse teams.

What I think would appeal to him is a culture that values both innovation and measurable impact. He's shown he can work independently on complex problems, but he also likes mentoring others and building community. So probably somewhere that encourages collaboration and continuous learning.

Given his track record of delivering real business results while maintaining academic excellence, I think he'd thrive in environments that appreciate both technical depth and practical problem-solving."""

        return response
    
    def get_future_response(self, context: Dict[str, bool], is_casual: bool = False, is_formal: bool = False) -> str:
        return f"""Aniket's got a pretty clear vision for where he wants to go. Short-term, he's looking to transition from academic research into industry applications where he can apply his ML and AI skills to solve real business challenges.

Looking further ahead, he wants to become a technical leader in the data science space. Based on his track record with projects like the vessel optimization that saved {self.aniket_data['experience']['key_projects'][1]['result']}, I think he's got the right mindset - he sees AI and ML as tools for creating tangible business value, not just academic exercises.

Long-term, he's interested in leading strategic data science initiatives and maybe building expertise in specialized areas like cultural AI or optimization systems. His management background gives him that business perspective that could be really valuable as he moves into leadership roles.

What drives him seems to be the opportunity to bridge the gap between cutting-edge technical work and practical business impact. That combination of academic rigor with real-world results suggests he'll keep pushing boundaries while delivering consistent value."""

        return response
    
    def get_general_response(self, is_casual: bool = False) -> str:
        return f"""Let me tell you about Aniket Shirsat. He's currently working on his {self.aniket_data['personal_info']['current_status'].lower()} with a perfect {self.aniket_data['education']['current']['gpa']} GPA while also working as a {self.aniket_data['personal_info']['current_role'].lower()}.

What makes him stand out is the real business impact he's already creating. His work includes achieving {self.aniket_data['achievements'][1]}, delivering {self.aniket_data['achievements'][2]}, and maintaining {self.aniket_data['achievements'][4]}.

He's technically solid with {', '.join(self.aniket_data['technical_skills']['programming'])}, {', '.join(self.aniket_data['technical_skills']['cloud_platforms'])}, and hands-on experience with machine learning, computer vision, and NLP.

Right now he's {self.aniket_data['career_goals'].lower()} where he can apply his combination of technical expertise and business understanding.

What would you like to know more about? I can tell you why companies should consider hiring him, dive deeper into his technical skills, talk about his specific projects, or cover his educational background."""

        return response

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
            "Tell me about his projects"
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
