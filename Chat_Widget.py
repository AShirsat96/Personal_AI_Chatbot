import os
import streamlit as st
from typing import List, Dict, Optional
from datetime import datetime
import json
import re

# Environment setup
from dotenv import load_dotenv
load_dotenv()

def is_valid_email(email):
    """Simple email validation"""
    email = email.strip()
    if len(email) < 5 or email.count('@') != 1 or '.' not in email:
        return False
    parts = email.split('@')
    if len(parts) != 2:
        return False
    local, domain = parts
    return len(local) >= 1 and len(domain) >= 3 and '.' in domain

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
        """Analyze user intent from input"""
        input_lower = user_input.lower()
        
        # Check for conversation patterns first
        if any(pattern in input_lower for pattern in self.conversation_patterns["greetings"]):
            return "greeting"
        elif any(pattern in input_lower for pattern in self.conversation_patterns["thanks"]):
            return "thanks"
        elif any(pattern in input_lower for pattern in self.conversation_patterns["goodbye"]):
            return "goodbye"
        
        # Check for question intents
        intent_scores = {}
        for intent, patterns in self.intent_patterns.items():
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
    
    def generate_response(self, user_input: str) -> str:
        """Generate intelligent response based on intent analysis"""
        intent = self.analyze_intent(user_input)
        context = self.extract_context(user_input)
        
        # Generate base response
        if intent == "greeting":
            return self.get_greeting_response()
        elif intent == "thanks":
            return self.get_thanks_response()
        elif intent == "goodbye":
            return self.get_goodbye_response()
        elif intent == "hiring":
            return self.get_hiring_response(context)
        elif intent == "skills":
            return self.get_skills_response(context)
        elif intent == "education":
            return self.get_education_response(context)
        elif intent == "experience":
            return self.get_experience_response(context)
        elif intent == "projects":
            return self.get_projects_response(context)
        elif intent == "personal":
            return self.get_personal_response(context)
        elif intent == "contact":
            return self.get_contact_response(context)
        elif intent == "availability":
            return self.get_availability_response(context)
        elif intent == "salary":
            return self.get_salary_response(context)
        elif intent == "location":
            return self.get_location_response(context)
        elif intent == "company_culture":
            return self.get_culture_response(context)
        elif intent == "future":
            return self.get_future_response(context)
        else:
            return self.get_general_response()
    
    def get_greeting_response(self) -> str:
        return """Hello! Great to meet you! 👋 

I'm here to help you learn about Aniket Shirsat's professional background and qualifications. 

Aniket is currently pursuing his Master's in Applied Data Science at Indiana University Indianapolis with a perfect 4.0 GPA while working as a Research Assistant.

What would you like to know about him? I can share details about his skills, experience, projects, or why he'd be an excellent addition to your team!"""
    
    def get_thanks_response(self) -> str:
        return """You're very welcome! 😊

I'm glad I could help you learn more about Aniket. If you have any other questions about his background, skills, projects, or qualifications, feel free to ask!

Is there anything specific about his experience or technical expertise you'd like to explore further?"""
    
    def get_goodbye_response(self) -> str:
        return """Thank you for your interest in Aniket Shirsat! 👋

I hope the information was helpful in understanding his qualifications and potential value to your team. 

If you'd like to connect with Aniket directly, please reach out through his professional channels. He's actively seeking opportunities and would love to discuss how his skills can contribute to your organization.

Have a great day!"""
    
    def get_hiring_response(self, context: Dict[str, bool]) -> str:
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
    
    def get_skills_response(self, context: Dict[str, bool]) -> str:
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
    
    def get_education_response(self, context: Dict[str, bool]) -> str:
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
    
    def get_experience_response(self, context: Dict[str, bool]) -> str:
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
    
    def get_projects_response(self, context: Dict[str, bool]) -> str:
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
    
    def get_personal_response(self, context: Dict[str, bool]) -> str:
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
    
    def get_contact_response(self, context: Dict[str, bool]) -> str:
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
    
    def get_availability_response(self, context: Dict[str, bool]) -> str:
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
    
    def get_salary_response(self, context: Dict[str, bool]) -> str:
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
    
    def get_location_response(self, context: Dict[str, bool]) -> str:
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
    
    def get_culture_response(self, context: Dict[str, bool]) -> str:
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
    
    def get_future_response(self, context: Dict[str, bool]) -> str:
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
    
    def get_general_response(self) -> str:
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

# Simple storage functions
def save_user_info(name: str, email: str, session_id: str) -> bool:
    """Save user info to session state"""
    try:
        if "user_data" not in st.session_state:
            st.session_state.user_data = []
        
        user_entry = {
            'timestamp': datetime.now().isoformat(),
            'name': name,
            'email': email,
            'session_id': session_id
        }
        st.session_state.user_data.append(user_entry)
        return True
    except:
        return False

def main():
    """Hybrid Chatbot - Clean interface for embedding"""
    st.set_page_config(
        page_title="Chat with Aniket's AI Assistant",
        page_icon="💬",
        layout="centered"
    )
    
    # Hide Streamlit UI elements
    st.markdown("""
    <style>
        .stApp > header {visibility: hidden;}
        .stApp > .main > div:nth-child(1) {padding-top: 0rem;}
        .stDeployButton {display: none;}
        .stDecoration {display: none;}
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        .stApp > .main {max-width: 100%; padding: 0;}
        .stApp {background: #f5f7fa;}
        
        .chat-container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
            overflow: hidden;
            max-width: 420px;
            margin: 20px auto;
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
        
        .user-info-prompt {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 15px;
            text-align: center;
            font-size: 14px;
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
    
    # Chat header
    avatar_src = "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNTAiIGhlaWdodD0iNTAiIHZpZXdCb3g9IjAgMCA1MCA1MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iMjUiIGN5PSIyNSIgcj0iMjUiIGZpbGw9IiM2NjdlZWEiLz4KPHN2ZyB4PSIxMiIgeT0iMTIiIHdpZHRoPSIyNiIgaGVpZ2h0PSIyNiIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPgo8cGF0aCBkPSJNMTIgMTJDMTQuNzYxNCAxMiAxNyA5Ljc2MTQyIDE3IDdDMTcgNC4yMzg1OCAxNC43NjE0IDIgMTIgMkM5LjIzODU4IDIgNyA0LjIzODU4IDcgN0M3IDkuNzYxNDIgOS4yMzg1OCAxMiAxMiAxMlpNMTIgMTRDOC42ODYyOSAxNCA2IDE2LjIzODYgNiAxOUg2QzYgMjEuNzYxNCA4LjIzODU4IDI0IDExIDI0SDEzQzE1Ljc2MTQgMjQgMTggMjEuNzYxNCAxOCAxOUg2QzYgMTYuMjM4NiA5LjMxMzcxIDE0IDEyIDE0WiIgZmlsbD0id2hpdGUiLz4KPC9zdmc+Cjwvc3ZnPgo="
    
    st.markdown(f"""
    <div class="chat-header">
        <img src="{avatar_src}" class="chat-avatar" alt="Aniket's Avatar">
        <div class="chat-title">
            <h3>Aniket's AI Assistant</h3>
            <p class="chat-subtitle">Intelligent responses powered by hybrid AI</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Messages container
    st.markdown('<div class="message-container">', unsafe_allow_html=True)
    
    # User info collection prompt
    if not st.session_state.user_info_collected:
        if st.session_state.asking_for_name:
            st.markdown("""
            <div class="user-info-prompt">
                👋 <strong>Welcome!</strong> Please share your name to get started
            </div>
            """, unsafe_allow_html=True)
        elif st.session_state.asking_for_email:
            st.markdown(f"""
            <div class="user-info-prompt">
                📧 <strong>Nice to meet you, {st.session_state.user_name}!</strong><br>
                Could you also share your email address?
            </div>
            """, unsafe_allow_html=True)
    
    # Display messages
    for message in st.session_state.messages:
        if message["role"] == "assistant":
            message_html = f"""
            <div class="assistant-message">
                <div style="width: 35px; height: 35px; background: #667eea; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 18px; flex-shrink: 0;">🤖</div>
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
                    response = st.session_state.chatbot.generate_response(suggestion)
                    st.session_state.messages.append({"role": "assistant", "content": response})
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
            if prompt.strip():
                st.session_state.user_name = prompt.strip()
                st.session_state.asking_for_name = False
                st.session_state.asking_for_email = True
                
                response = f"Thank you, {st.session_state.user_name}! Could you please share your email address?"
                st.session_state.messages.append({"role": "assistant", "content": response})
            else:
                response = "I didn't catch that. Could you please tell me your name?"
                st.session_state.messages.append({"role": "assistant", "content": response})
        
        elif st.session_state.asking_for_email:
            if is_valid_email(prompt.strip()):
                st.session_state.user_email = prompt.strip()
                st.session_state.asking_for_email = False
                st.session_state.user_info_collected = True
                
                # Save user info
                save_user_info(st.session_state.user_name, st.session_state.user_email, st.session_state.session_id)
                
                response = f"""Perfect! Thank you, {st.session_state.user_name}. I'm ready to answer questions about Aniket's professional background.

I'm powered by a hybrid AI system that provides intelligent, contextual responses about Aniket's qualifications, experience, and why he'd be an excellent addition to your team.

**Try asking:** "Why should I hire Aniket?" or "What are his technical skills?"

What would you like to know?"""
                
                st.session_state.messages.append({"role": "assistant", "content": response})
            else:
                response = "That doesn't look like a valid email. Please enter a valid email address (e.g., john@company.com)."
                st.session_state.messages.append({"role": "assistant", "content": response})
        
        else:
            # Normal chat using hybrid AI
            with st.spinner("🤖 Analyzing your question..."):
                response = st.session_state.chatbot.generate_response(prompt)
            
            st.session_state.messages.append({"role": "assistant", "content": response})
        
        st.rerun()
    
    # Footer with hybrid AI branding
    st.markdown("""
    <div style="text-align: center; color: #aaa; font-size: 11px; margin-top: 20px; padding: 10px;">
        🤖 Powered by Hybrid AI • Aniket Shirsat Portfolio Assistant
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
