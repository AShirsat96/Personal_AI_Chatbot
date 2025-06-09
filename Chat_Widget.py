import os
import streamlit as st
from typing import List, Dict, Optional
from datetime import datetime
import pickle

# OpenAI for chat
import openai
from openai import OpenAI

# Environment setup
from dotenv import load_dotenv
load_dotenv()

# Create data directory for persistent storage
DATA_DIR = "chatbot_data"
RESUME_FILE = os.path.join(DATA_DIR, "resume_content.pkl")
AVATAR_FILE = os.path.join(DATA_DIR, "avatar.pkl")
USER_DATA_FILE = os.path.join(DATA_DIR, "user_interactions.csv")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

def load_saved_resume():
    """Load saved resume content from persistent storage"""
    try:
        if os.path.exists(RESUME_FILE):
            with open(RESUME_FILE, 'rb') as f:
                return pickle.load(f)
    except Exception:
        return None
    return None

def load_saved_avatar():
    """Load saved avatar from persistent storage"""
    try:
        if os.path.exists(AVATAR_FILE):
            with open(AVATAR_FILE, 'rb') as f:
                return pickle.load(f)
    except Exception:
        return None
    return None

def is_valid_email(email):
    """Simple email validation"""
    email = email.strip()
    if len(email) < 5:
        return False
    if email.count('@') != 1:
        return False
    if '.' not in email:
        return False
    
    parts = email.split('@')
    if len(parts) != 2:
        return False
    
    local, domain = parts
    if len(local) < 1 or len(domain) < 3:
        return False
    if '.' not in domain:
        return False
    
    return True

def save_user_info(name, email, timestamp=None):
    """Save user information to CSV file"""
    try:
        import pandas as pd
        
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        user_data = {
            'timestamp': [timestamp],
            'name': [name],
            'email': [email],
            'session_id': [st.session_state.get('session_id', 'unknown')]
        }
        
        df = pd.DataFrame(user_data)
        
        if os.path.exists(USER_DATA_FILE):
            df.to_csv(USER_DATA_FILE, mode='a', header=False, index=False)
        else:
            df.to_csv(USER_DATA_FILE, mode='w', header=True, index=False)
        
        return True
    except Exception:
        return False

class SimpleKnowledgeBase:
    """Simple text-based knowledge storage"""
    
    def __init__(self):
        self.content_chunks = []
        self.metadata = []
        self.resume_content = None
        self._load_saved_resume()
    
    def _load_saved_resume(self):
        """Load saved resume content"""
        self.resume_content = load_saved_resume()
        if self.resume_content:
            self._add_resume_to_chunks()
    
    def _add_resume_to_chunks(self):
        """Add resume content to chunks"""
        if not self.resume_content:
            return
            
        chunks = self._chunk_content(self.resume_content.content, chunk_size=800, overlap=150)
        
        for j, chunk in enumerate(chunks):
            self.content_chunks.append(chunk.lower())
            self.metadata.append({
                "filename": self.resume_content.filename,
                "title": f"Resume - {self.resume_content.filename}",
                "chunk_id": f"resume_{j}",
                "original_chunk": chunk,
                "source_type": "resume",
                "word_count": len(chunk.split()),
                "timestamp": self.resume_content.timestamp.isoformat()
            })
    
    def _chunk_content(self, content: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split content into overlapping chunks"""
        words = content.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if len(chunk.strip()) > 50:
                chunks.append(chunk.strip())
                
        return chunks
    
    def search(self, query: str, n_results: int = 5) -> List[Dict]:
        """Simple keyword-based search"""
        if not self.content_chunks:
            return []
        
        query_words = set(query.lower().split())
        results = []
        
        for i, chunk in enumerate(self.content_chunks):
            chunk_words = set(chunk.split())
            matches = len(query_words.intersection(chunk_words))
            
            if matches > 0:
                score = matches / len(query_words)
                if self.metadata[i].get('source_type') == 'resume':
                    score *= 1.3
                
                results.append({
                    'content': self.metadata[i]['original_chunk'],
                    'metadata': self.metadata[i],
                    'score': score
                })
        
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:n_results]

class AniketChatbotAI:
    """Professional assistant for Aniket Shirsat's portfolio"""
    
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.knowledge_base = SimpleKnowledgeBase()
        
        self.aniket_profile = {
            "name": "Aniket Shirsat",
            "current_role": "Master's student in Applied Data Science at Indiana University Indianapolis",
            "gpa": "4.0",
            "previous_education": "Master's in Management from Singapore Management University",
            "current_position": "Research Assistant at Indiana University",
            "business": "Research Assistant at Indiana University",
            "specializations": [
                "Machine Learning", "Data Analysis", "Computer Vision", 
                "Natural Language Processing", "AI-powered Solutions",
                "Vessel Fuel Optimization", "Cultural Ambiguity Detection"
            ],
            "technical_skills": [
                "Python", "R", "SQL", "AWS", "Azure", "GCP",
                "Machine Learning Frameworks", "Advanced Analytics"
            ],
            "achievements": [
                "90% accuracy in cultural ambiguity detection models",
                "5% fuel reduction across 50+ vessels",
                "$1 million annual savings through ML optimization",
                "Perfect 4.0 GPA in Master's program"
            ],
            "leadership": [
                "Head of Outreach and Project Committee Lead - Data Science and Machine Learning Club",
                "Member of Indiana University Jaguars Rowing Club"
            ]
        }
    
    def get_expert_system_prompt(self, has_resume: bool = False) -> str:
        """Generate specialized system prompt"""
        resume_context = ""
        if has_resume:
            resume_context = """
        
        RESUME INFORMATION:
        You have access to Aniket's detailed resume content. Use this information to provide specific details about his work experience, education, skills, projects, and achievements."""
        
        return f"""You are a knowledgeable professional assistant providing information about Aniket Shirsat's qualifications and experience. Respond naturally and conversationally.
        
        ABOUT ANIKET SHIRSAT:
        • Currently: {self.aniket_profile['current_role']} (GPA: {self.aniket_profile['gpa']})
        • Previous: {self.aniket_profile['previous_education']}
        • Position: {self.aniket_profile['current_position']}
        
        EXPERTISE AREAS:
        • Specializations: {', '.join(self.aniket_profile['specializations'])}
        • Technical Skills: {', '.join(self.aniket_profile['technical_skills'])}
        
        KEY ACHIEVEMENTS:
        • {chr(10).join([f'• {achievement}' for achievement in self.aniket_profile['achievements']])}
        
        LEADERSHIP:
        • {chr(10).join([f'• {role}' for role in self.aniket_profile['leadership']])}
        {resume_context}
        
        RESPONSE STYLE:
        1. Write naturally and conversationally
        2. Provide specific, quantifiable achievements when relevant
        3. Focus on practical skills and real-world impact
        4. Mention availability for opportunities when appropriate
        5. Be informative but not overly promotional
        6. Use varied sentence structure and natural language flow
        7. Include relevant context without being verbose
        
        Always provide helpful, accurate information while maintaining a professional yet personable tone."""
    
    def generate_expert_response(self, user_query: str) -> str:
        """Generate response with context"""
        relevant_chunks = self.knowledge_base.search(user_query, n_results=5)
        
        context = ""
        if relevant_chunks:
            context = "\n\n".join([
                f"From {chunk['metadata'].get('title', 'Unknown Source')} ({chunk['metadata'].get('source_type', 'unknown')}):\n{chunk['content']}"
                for chunk in relevant_chunks
            ])
        
        query_lower = user_query.lower()
        
        if any(keyword in query_lower for keyword in ['experience', 'background', 'about']):
            expertise_context = """
            Aniket brings solid experience in data science and machine learning. He's currently working toward his Master's in Applied Data Science at Indiana University with a perfect 4.0 GPA while serving as a Research Assistant. His background includes practical work developing ML models for cultural ambiguity detection that achieved 90% accuracy, plus vessel fuel optimization models that generated $1M in annual savings.
            """
        elif any(keyword in query_lower for keyword in ['skills', 'technical', 'programming']):
            expertise_context = """
            His technical toolkit covers Python, R, and SQL for programming, plus experience across AWS, Azure, and GCP cloud platforms. He specializes in machine learning, computer vision, and natural language processing, with hands-on experience building advanced analytics solutions.
            """
        elif any(keyword in query_lower for keyword in ['projects', 'research', 'work']):
            expertise_context = """
            Notable work includes developing cultural ambiguity detection systems for advertisements with 90% accuracy, creating vessel fuel optimization models that reduced consumption by 5% across 50+ vessels (saving $1M annually), and building dataset pipelines for annotated advertisement images.
            """
        elif any(keyword in query_lower for keyword in ['collaboration', 'contact', 'connect', 'hire', 'opportunity']):
            expertise_context = """
            Aniket is actively seeking full-time opportunities in data science and machine learning roles. His combination of strong academic performance, research experience, and proven ability to deliver quantifiable business results makes him well-suited for analyst, engineer, or research positions.
            """
        else:
            expertise_context = ""
        
        full_context = f"{context}\n\n{expertise_context}".strip()
        
        has_resume = self.knowledge_base.resume_content is not None
        system_prompt = self.get_expert_system_prompt(has_resume)
        
        user_prompt = f"""Background information:
        {full_context}
        
        Question: {user_query}
        
        Please provide a helpful, natural response that showcases Aniket's qualifications and experience."""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=600,
                temperature=0.8
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"""I'd be happy to share information about Aniket Shirsat. He's currently pursuing his Master's in Applied Data Science at Indiana University Indianapolis with a perfect 4.0 GPA while working as a Research Assistant.
            
            His expertise spans machine learning, computer vision, and NLP, with proven results including 90% accuracy in cultural ambiguity detection and $1M in annual savings through vessel fuel optimization models.
            
            For more detailed information or direct contact, please reach out through his professional channels. (Technical note: {str(e)})"""

def main():
    """Chat Widget - Clean interface for embedding"""
    st.set_page_config(
        page_title="Chat with Aniket's AI Assistant",
        page_icon="💬",
        layout="centered"
    )
    
    # Hide Streamlit UI elements for clean embedding
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
        
        /* Modern chat container */
        .chat-container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
            overflow: hidden;
            max-width: 400px;
            margin: 20px auto;
            border: 1px solid #e1e8ed;
        }
        
        /* Chat header with avatar and title */
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
        
        .chat-title {
            flex: 1;
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
        
        /* Message styling */
        .message-container {
            padding: 15px 20px;
            max-height: 400px;
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
            max-width: 280px;
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
            max-width: 280px;
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
        
        /* Hide default streamlit chat elements */
        .stChatMessage {display: none;}
        .stChatInput {border-radius: 20px;}
        
        /* Scrollbar styling */
        .message-container::-webkit-scrollbar {
            width: 4px;
        }
        .message-container::-webkit-scrollbar-track {
            background: #f1f1f1;
        }
        .message-container::-webkit-scrollbar-thumb {
            background: #888;
            border-radius: 2px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Load API Key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if not openai_api_key:
        st.error("⚠️ API configuration required. Please contact the administrator.")
        st.stop()
    
    # Initialize chatbot
    if "chatbot" not in st.session_state:
        st.session_state.chatbot = AniketChatbotAI(openai_api_key)
    
    # Generate session ID
    if "session_id" not in st.session_state:
        st.session_state.session_id = f"widget_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(datetime.now()) % 10000}"
    
    # Load saved avatar
    if "avatar_base64" not in st.session_state:
        saved_avatar = load_saved_avatar()
        if saved_avatar:
            st.session_state.avatar_base64 = saved_avatar
    
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
    
    # Chat header with avatar and title
    if "avatar_base64" in st.session_state and st.session_state.avatar_base64:
        avatar_src = st.session_state.avatar_base64
    else:
        # Default avatar placeholder
        avatar_src = "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNTAiIGhlaWdodD0iNTAiIHZpZXdCb3g9IjAgMCA1MCA1MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iMjUiIGN5PSIyNSIgcj0iMjUiIGZpbGw9IiM2NjdlZWEiLz4KPHN2ZyB4PSIxMiIgeT0iMTIiIHdpZHRoPSIyNiIgaGVpZ2h0PSIyNiIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPgo8cGF0aCBkPSJNMTIgMTJDMTQuNzYxNCAxMiAxNyA5Ljc2MTQyIDE3IDdDMTcgNC4yMzg1OCAxNC43NjE0IDIgMTIgMkM5LjIzODU4IDIgNyA0LjIzODU4IDcgN0M3IDkuNzYxNDIgOS4yMzg1OCAxMiAxMiAxMlpNMTIgMTRDOC42ODYyOSAxNCA2IDE2LjIzODYgNiAxOUg2QzYgMjEuNzYxNCA4LjIzODU4IDI0IDExIDI0SDEzQzE1Ljc2MTQgMjQgMTggMjEuNzYxNCAxOCAxOUg2QzYgMTYuMjM4NiA5LjMxMzcxIDE0IDEyIDE0WiIgZmlsbD0id2hpdGUiLz4KPC9zdmc+Cjwvc3ZnPgo="
    
    st.markdown(f"""
    <div class="chat-header">
        <img src="{avatar_src}" class="chat-avatar" alt="Aniket's Avatar">
        <div class="chat-title">
            <h3>Aniket's AI Assistant</h3>
            <p class="chat-subtitle">Ask about qualifications, experience, and skills</p>
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
    
    # Display messages with custom styling
    for message in st.session_state.messages:
        if message["role"] == "assistant":
            if "avatar_base64" in st.session_state and st.session_state.avatar_base64:
                message_html = f"""
                <div class="assistant-message">
                    <img src="{st.session_state.avatar_base64}" class="assistant-avatar" alt="Assistant">
                    <div class="message-bubble">{message["content"]}</div>
                </div>
                """
            else:
                message_html = f"""
                <div class="assistant-message">
                    <div style="width: 35px; height: 35px; background: #667eea; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 18px; flex-shrink: 0;">👨‍💼</div>
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
    st.markdown('</div>', unsafe_allow_html=True)  # Close chat-container
    
    # Chat input
    if st.session_state.asking_for_name:
        placeholder = "Enter your name..."
    elif st.session_state.asking_for_email:
        placeholder = "Enter your email address..."
    else:
        placeholder = "Ask about Aniket's background, skills, or experience..."
    
    if prompt := st.chat_input(placeholder):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Handle user info collection
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
                save_user_info(st.session_state.user_name, st.session_state.user_email)
                
                response = f"""Perfect! Thank you, {st.session_state.user_name}. I'm ready to answer questions about Aniket's professional background.

**You can ask about:** Education • Technical Skills • Work Experience • Projects • Achievements

What would you like to know?"""
                
                st.session_state.messages.append({"role": "assistant", "content": response})
            else:
                response = "That doesn't look like a valid email. Please enter a valid email address (e.g., john@company.com)."
                st.session_state.messages.append({"role": "assistant", "content": response})
        
        else:
            # Normal chat
            with st.spinner("Thinking..."):
                response = st.session_state.chatbot.generate_expert_response(prompt)
            
            st.session_state.messages.append({"role": "assistant", "content": response})
        
        # Auto-refresh to show the new messages
        st.rerun()
    
    # Subtle footer
    st.markdown("""
    <div style="text-align: center; color: #aaa; font-size: 11px; margin-top: 20px; padding: 10px;">
        Aniket Shirsat - Portfolio Assistant
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
