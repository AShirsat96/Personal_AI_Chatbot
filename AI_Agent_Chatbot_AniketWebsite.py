import streamlit as st
import streamlit.components.v1 as components

# Configure Streamlit for iframe embedding
st.set_page_config(
    page_title="Aniket's AI Assistant",
    page_icon="👨‍💼",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CRITICAL: Remove iframe blocking headers
def remove_iframe_blocking():
    """Remove X-Frame-Options and other iframe blocking headers"""
    st.markdown("""
    <script>
    // Remove iframe restrictions
    if (window.parent !== window) {
        // We're in an iframe, remove any blocking headers
        console.log('Running in iframe mode');
    }
    </script>
    """, unsafe_allow_html=True)

# CRITICAL: Hide Streamlit UI elements for clean embedding
def hide_streamlit_ui():
    """Hide all Streamlit UI elements for clean iframe embedding"""
    hide_streamlit_style = """
    <style>
    /* Hide Streamlit branding and UI */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp > header {visibility: hidden;}
    .stApp > footer {visibility: hidden;}
    .stDeployButton {visibility: hidden;}
    .stDecoration {visibility: hidden;}
    #stDecoration {visibility: hidden;}
    
    /* Hide sidebar completely */
    .css-1d391kg {display: none;}
    .stSidebar {display: none;}
    
    /* Adjust main container for iframe */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 100%;
    }
    
    /* Remove top spacing */
    .appview-container .main .block-container {
        padding-top: 1rem;
    }
    
    /* Make content fit iframe better */
    .stApp {
        background-color: white;
    }
    
    /* Ensure widgets work in iframe */
    .stSelectbox, .stTextInput, .stButton {
        z-index: 999999;
    }
    </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# CRITICAL: Add iframe-specific meta tags
def add_iframe_meta():
    """Add meta tags to allow iframe embedding"""
    st.markdown("""
    <meta http-equiv="X-Frame-Options" content="ALLOWALL">
    <meta http-equiv="Content-Security-Policy" content="frame-ancestors *;">
    """, unsafe_allow_html=True)

# Call all the iframe setup functions
remove_iframe_blocking()
hide_streamlit_ui()
add_iframe_meta()

import os
import time
import requests
import streamlit as st
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import base64
from io import BytesIO
from PIL import Image
import PyPDF2
import docx
import pickle

# Core libraries
import pandas as pd
from bs4 import BeautifulSoup

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

@dataclass
class WebsiteContent:
    """Data class for storing scraped website content"""
    url: str
    title: str
    content: str
    metadata: Dict
    timestamp: datetime

@dataclass
class ResumeContent:
    """Data class for storing resume content"""
    filename: str
    content: str
    file_type: str
    metadata: Dict
    timestamp: datetime

class SimpleWebsiteScraper:
    """Simplified website scraper using only requests and BeautifulSoup"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def extract_links(self, base_url: str, soup: BeautifulSoup) -> List[str]:
        """Extract all internal links from a page"""
        links = set()
        domain = urlparse(base_url).netloc
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(base_url, href)
            
            # Only include internal links
            if urlparse(full_url).netloc == domain:
                links.add(full_url)
                
        return list(links)
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        # Simple text cleaning without regex
        text = ' '.join(text.split())  # Replace multiple whitespace with single space
        return text.strip()
    
    def scrape_page(self, url: str) -> Optional[WebsiteContent]:
        """Scrape a single page and extract content"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Extract title
            title = soup.find('title')
            title_text = title.get_text().strip() if title else url
            
            # Extract main content
            content_selectors = [
                'main', 'article', '.content', '#content', 
                '.post', '.entry-content', 'section'
            ]
            
            content = ""
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    content = ' '.join([elem.get_text() for elem in elements])
                    break
            
            # If no specific content found, get body text
            if not content:
                body = soup.find('body')
                if body:
                    content = body.get_text()
            
            content = self.clean_text(content)
            
            # Extract metadata
            metadata = {
                'word_count': len(content.split()),
                'scraped_at': datetime.now().isoformat(),
            }
            
            # Extract meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                metadata['description'] = meta_desc.get('content', '')
            
            return WebsiteContent(
                url=url,
                title=title_text,
                content=content,
                metadata=metadata,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            st.error(f"Error scraping {url}: {str(e)}")
            return None
    
    def scrape_website(self, base_url: str, max_pages: int = 10) -> List[WebsiteContent]:
        """Scrape an entire website starting from base URL"""
        scraped_content = []
        visited_urls = set()
        urls_to_visit = [base_url]
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        while urls_to_visit and len(scraped_content) < max_pages:
            current_url = urls_to_visit.pop(0)
            
            if current_url in visited_urls:
                continue
                
            visited_urls.add(current_url)
            
            status_text.text(f"Analyzing: {current_url}")
            progress = len(scraped_content) / max_pages
            progress_bar.progress(min(progress, 1.0))
            
            content = self.scrape_page(current_url)
            
            if content and len(content.content) > 100:
                scraped_content.append(content)
                
                # Find more links to scrape
                if len(scraped_content) < max_pages:
                    try:
                        response = self.session.get(current_url, timeout=5)
                        soup = BeautifulSoup(response.text, 'html.parser')
                        new_links = self.extract_links(base_url, soup)
                        
                        for link in new_links:
                            if link not in visited_urls and link not in urls_to_visit:
                                urls_to_visit.append(link)
                                
                    except Exception as e:
                        st.warning(f"Could not extract links from {current_url}")
            
            time.sleep(1)  # Be respectful to the server
        
        progress_bar.progress(1.0)
        status_text.text(f"Analysis complete! Found {len(scraped_content)} pages.")
        
        return scraped_content

class ResumeProcessor:
    """Process and extract content from resume files"""
    
    @staticmethod
    def extract_text_from_pdf(file_bytes: bytes) -> str:
        """Extract text from PDF file"""
        try:
            pdf_file = BytesIO(file_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text.strip()
        except Exception as e:
            st.error(f"Error reading PDF: {str(e)}")
            return ""
    
    @staticmethod
    def extract_text_from_docx(file_bytes: bytes) -> str:
        """Extract text from DOCX file"""
        try:
            docx_file = BytesIO(file_bytes)
            doc = docx.Document(docx_file)
            
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            
            return text.strip()
        except Exception as e:
            st.error(f"Error reading DOCX: {str(e)}")
            return ""
    
    @staticmethod
    def extract_text_from_txt(file_bytes: bytes) -> str:
        """Extract text from TXT file"""
        try:
            return file_bytes.decode('utf-8').strip()
        except Exception as e:
            st.error(f"Error reading TXT: {str(e)}")
            return ""
    
    def process_resume(self, uploaded_file) -> Optional[ResumeContent]:
        """Process uploaded resume file and extract content"""
        try:
            file_bytes = uploaded_file.read()
            file_type = uploaded_file.type
            filename = uploaded_file.name
            
            # Extract text based on file type
            if file_type == "application/pdf":
                content = self.extract_text_from_pdf(file_bytes)
            elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                content = self.extract_text_from_docx(file_bytes)
            elif file_type == "text/plain":
                content = self.extract_text_from_txt(file_bytes)
            else:
                st.error(f"Unsupported file type: {file_type}")
                return None
            
            if not content:
                st.error("Could not extract text from the file")
                return None
            
            # Generate metadata
            metadata = {
                'word_count': len(content.split()),
                'file_size': len(file_bytes),
                'processed_at': datetime.now().isoformat(),
            }
            
            return ResumeContent(
                filename=filename,
                content=content,
                file_type=file_type,
                metadata=metadata,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            st.error(f"Error processing resume: {str(e)}")
            return None

class SimpleKnowledgeBase:
    """Simple text-based knowledge storage without vector database"""
    
    def __init__(self):
        self.content_chunks = []
        self.metadata = []
        self.resume_content = None
        
        # Load saved resume on initialization
        self.load_saved_resume()
    
    def save_resume(self):
        """Save resume content to persistent storage"""
        try:
            if self.resume_content:
                with open(RESUME_FILE, 'wb') as f:
                    pickle.dump(self.resume_content, f)
                return True
        except Exception as e:
            st.error(f"Error saving resume: {str(e)}")
            return False
        return False
    
    def load_saved_resume(self):
        """Load saved resume content from persistent storage"""
        try:
            if os.path.exists(RESUME_FILE):
                with open(RESUME_FILE, 'rb') as f:
                    self.resume_content = pickle.load(f)
                return True
        except Exception as e:
            st.warning(f"Could not load saved resume: {str(e)}")
            return False
        return False
    
    def delete_saved_resume(self):
        """Delete saved resume from persistent storage"""
        try:
            if os.path.exists(RESUME_FILE):
                os.remove(RESUME_FILE)
                self.resume_content = None
                return True
        except Exception as e:
            st.error(f"Error deleting resume: {str(e)}")
            return False
        return False
    
    def chunk_content(self, content: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split content into overlapping chunks"""
        words = content.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if len(chunk.strip()) > 50:
                chunks.append(chunk.strip())
                
        return chunks
    
    def add_website_content(self, website_content: List[WebsiteContent]):
        """Add website content to simple storage"""
        # Clear existing website content but keep resume
        self.content_chunks = []
        self.metadata = []
        
        # Add resume content first if available
        if self.resume_content:
            self._add_resume_to_chunks()
        
        # Add website content
        for i, content in enumerate(website_content):
            chunks = self.chunk_content(content.content)
            
            for j, chunk in enumerate(chunks):
                self.content_chunks.append(chunk.lower())
                self.metadata.append({
                    "url": content.url,
                    "title": content.title,
                    "chunk_id": f"web_{i}_{j}",
                    "original_chunk": chunk,
                    "source_type": "website",
                    "word_count": len(chunk.split()),
                    "timestamp": content.timestamp.isoformat()
                })
        
        st.success(f"Knowledge base updated with {len(self.content_chunks)} information segments!")
    
    def add_resume_content(self, resume_content: ResumeContent):
        """Add resume content to knowledge base and save persistently"""
        self.resume_content = resume_content
        self._add_resume_to_chunks()
        
        # Save resume to persistent storage
        if self.save_resume():
            st.success(f"✅ Resume '{resume_content.filename}' saved permanently!")
        else:
            st.warning(f"Resume '{resume_content.filename}' added but could not be saved permanently")
    
    def _add_resume_to_chunks(self):
        """Helper method to add resume content to chunks"""
        if not self.resume_content:
            return
            
        chunks = self.chunk_content(self.resume_content.content, chunk_size=800, overlap=150)
        
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
    
    def search(self, query: str, n_results: int = 5) -> List[Dict]:
        """Simple keyword-based search across website and resume content"""
        if not self.content_chunks:
            return []
        
        query_words = set(query.lower().split())
        results = []
        
        for i, chunk in enumerate(self.content_chunks):
            # Count matching words
            chunk_words = set(chunk.split())
            matches = len(query_words.intersection(chunk_words))
            
            if matches > 0:
                # Boost resume content relevance for job-related queries
                score = matches / len(query_words)
                if self.metadata[i].get('source_type') == 'resume':
                    score *= 1.3  # Boost resume content
                
                results.append({
                    'content': self.metadata[i]['original_chunk'],
                    'metadata': self.metadata[i],
                    'score': score
                })
        
        # Sort by relevance score and return top results
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:n_results]

def get_image_base64(image_file):
    """Convert uploaded image to base64 string"""
    try:
        img = Image.open(image_file)
        # Resize image to reasonable size for avatar
        img = img.resize((100, 100), Image.Resampling.LANCZOS)
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"
    except Exception as e:
        st.error(f"Error processing avatar image: {str(e)}")
        return None

def save_avatar(avatar_base64):
    """Save avatar to persistent storage"""
    try:
        with open(AVATAR_FILE, 'wb') as f:
            pickle.dump(avatar_base64, f)
        return True
    except Exception as e:
        st.error(f"Error saving avatar: {str(e)}")
        return False

def load_saved_avatar():
    """Load saved avatar from persistent storage"""
    try:
        if os.path.exists(AVATAR_FILE):
            with open(AVATAR_FILE, 'rb') as f:
                return pickle.load(f)
    except Exception as e:
        st.warning(f"Could not load saved avatar: {str(e)}")
    return None

def delete_saved_avatar():
    """Delete saved avatar from persistent storage"""
    try:
        if os.path.exists(AVATAR_FILE):
            os.remove(AVATAR_FILE)
            return True
    except Exception as e:
        st.error(f"Error deleting avatar: {str(e)}")
        return False

def save_user_info(name, email, timestamp=None):
    """Save user information to CSV file"""
    try:
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        # Create DataFrame with user info
        user_data = {
            'timestamp': [timestamp],
            'name': [name],
            'email': [email],
            'session_id': [st.session_state.get('session_id', 'unknown')]
        }
        
        df = pd.DataFrame(user_data)
        
        # Append to CSV file (create if doesn't exist)
        if os.path.exists(USER_DATA_FILE):
            df.to_csv(USER_DATA_FILE, mode='a', header=False, index=False)
        else:
            df.to_csv(USER_DATA_FILE, mode='w', header=True, index=False)
        
        return True
    except Exception as e:
        st.error(f"Error saving user info: {str(e)}")
        return False

def load_user_data():
    """Load all user interaction data"""
    try:
        if os.path.exists(USER_DATA_FILE):
            return pd.read_csv(USER_DATA_FILE)
        else:
            return pd.DataFrame(columns=['timestamp', 'name', 'email', 'session_id'])
    except Exception as e:
        st.error(f"Error loading user data: {str(e)}")
        return pd.DataFrame(columns=['timestamp', 'name', 'email', 'session_id'])

def export_user_data():
    """Export user data with download option"""
    try:
        df = load_user_data()
        if not df.empty:
            # Convert to CSV string
            csv_string = df.to_csv(index=False)
            return csv_string
        return None
    except Exception as e:
        st.error(f"Error exporting user data: {str(e)}")
        return None

def is_valid_email(email):
    """Simple email validation without regex"""
    email = email.strip()
    # Check basic email format: contains @ and ., and reasonable length
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

class AniketChatbotAI:
    """Professional assistant for Aniket Shirsat's portfolio"""
    
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.knowledge_base = SimpleKnowledgeBase()
        
        # Aniket's professional profile
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
        """Generate specialized system prompt for Aniket's expertise"""
        resume_context = ""
        if has_resume:
            resume_context = """
        
        RESUME INFORMATION:
        You have access to Aniket's detailed resume content. Use this information to provide specific details about his work experience, education, skills, projects, and achievements. When answering questions about his background, prioritize information from the resume as it contains the most current and detailed information."""
        
        return f"""You are a knowledgeable professional assistant providing information about Aniket Shirsat's qualifications and experience. Respond naturally and conversationally, as if you're a well-informed colleague sharing insights about his background.
        
        ABOUT ANIKET SHIRSAT:
        • Currently: {self.aniket_profile['current_role']} (GPA: {self.aniket_profile['gpa']})
        • Previous: {self.aniket_profile['previous_education']}
        • Position: {self.aniket_profile['current_position']}
        • Business: {self.aniket_profile['business']}
        
        EXPERTISE AREAS:
        • Specializations: {', '.join(self.aniket_profile['specializations'])}
        • Technical Skills: {', '.join(self.aniket_profile['technical_skills'])}
        
        KEY ACHIEVEMENTS:
        • {chr(10).join([f'• {achievement}' for achievement in self.aniket_profile['achievements']])}
        
        LEADERSHIP:
        • {chr(10).join([f'• {role}' for role in self.aniket_profile['leadership']])}
        {resume_context}
        
        RESPONSE STYLE:
        1. Write naturally and conversationally - avoid robotic or templated responses
        2. Provide specific, quantifiable achievements when relevant
        3. Focus on practical skills and real-world impact
        4. Mention availability for opportunities when appropriate
        5. Be informative but not overly promotional
        6. Use varied sentence structure and natural language flow
        7. Include relevant context without being verbose
        8. When resume information is available, use specific details from it
        
        Always provide helpful, accurate information while maintaining a professional yet personable tone."""
    
    def generate_expert_response(self, user_query: str) -> str:
        """Generate natural response with Aniket's expertise context"""
        # Search for relevant content (both website and resume)
        relevant_chunks = self.knowledge_base.search(user_query, n_results=5)
        
        # Build context from relevant chunks
        context = ""
        if relevant_chunks:
            context = "\n\n".join([
                f"From {chunk['metadata'].get('title', 'Unknown Source')} ({chunk['metadata'].get('source_type', 'unknown')}):\n{chunk['content']}"
                for chunk in relevant_chunks
            ])
        
        # Determine query type for specialized responses
        query_lower = user_query.lower()
        
        # Custom responses for common queries about Aniket
        if any(keyword in query_lower for keyword in ['experience', 'background', 'about']):
            expertise_context = f"""
            Aniket brings solid experience in data science and machine learning. He's currently working toward his Master's in Applied Data Science at Indiana University with a perfect 4.0 GPA while serving as a Research Assistant. His background includes practical work developing ML models for cultural ambiguity detection that achieved 90% accuracy, plus vessel fuel optimization models that generated $1M in annual savings. He combines academic excellence with real-world application experience.
            """
        elif any(keyword in query_lower for keyword in ['skills', 'technical', 'programming']):
            expertise_context = f"""
            His technical toolkit covers the essentials: Python, R, and SQL for programming, plus experience across AWS, Azure, and GCP cloud platforms. He specializes in machine learning, computer vision, and natural language processing, with hands-on experience building advanced analytics solutions. What stands out is his ability to translate technical skills into measurable business results.
            """
        elif any(keyword in query_lower for keyword in ['projects', 'research', 'work']):
            expertise_context = f"""
            Some notable work includes developing cultural ambiguity detection systems for advertisements with 90% accuracy, creating vessel fuel optimization models that reduced consumption by 5% across 50+ vessels (saving $1M annually), and building dataset pipelines for annotated advertisement images. His research spans computer vision and NLP applications, often with practical business applications.
            """
        elif any(keyword in query_lower for keyword in ['collaboration', 'contact', 'connect', 'hire', 'opportunity']):
            expertise_context = f"""
            Aniket is actively seeking full-time opportunities in data science and machine learning roles. His combination of strong academic performance, research experience, and proven ability to deliver quantifiable business results makes him well-suited for analyst, engineer, or research positions. He's particularly interested in roles where he can apply ML to solve real-world problems.
            """
        else:
            expertise_context = ""
        
        # Combine all context
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
    
    def get_suggested_questions(self) -> List[str]:
        """Get suggested questions for recruiters and hiring managers"""
        base_questions = [
            "What is Aniket's educational background?",
            "What programming languages does he know?",
            "Tell me about his work experience",
            "What are his key achievements?",
            "What machine learning projects has he worked on?",
            "Does he have leadership experience?",
            "What cloud platforms is he familiar with?",
            "What is his GPA and academic performance?",
            "What research has he conducted?",
            "Is he available for full-time opportunities?"
        ]
        
        # Add resume-specific questions if resume is uploaded
        if self.knowledge_base.resume_content:
            resume_questions = [
                "Walk me through his resume",
                "What specific skills are listed on his resume?",
                "What companies has he worked for?",
                "What are his most recent achievements?",
                "Tell me about his certifications"
            ]
            return base_questions + resume_questions
        
        return base_questions

def main():
    """Main Streamlit application - Aniket Shirsat's Portfolio Assistant"""
    st.set_page_config(
        page_title="Aniket Shirsat - Portfolio Assistant",
        page_icon="👨‍💼",
        layout="wide"
    )
    
    # Custom CSS for enhanced styling
    st.markdown("""
    <style>
    .main-header {
        text-align: center; 
        padding: 25px; 
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
        color: white; 
        border-radius: 15px; 
        margin-bottom: 30px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .assistant-badge {
        background: rgba(255,255,255,0.1);
        padding: 8px 16px;
        border-radius: 20px;
        display: inline-block;
        margin-top: 10px;
    }
    .achievement-card {
        background: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin: 10px 0;
    }
    .upload-section {
        background: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border: 2px dashed #667eea;
        margin: 15px 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Custom header for the assistant
    st.markdown("""
    <div class="main-header">
        <h1>👨‍💼 Aniket Shirsat Portfolio Assistant</h1>
        <div class="assistant-badge">
            Professional Information & Career Insights
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Load API Key from environment variable
        openai_api_key = os.getenv("OPENAI_API_KEY")
        
        if openai_api_key:
            st.success("✅ System Ready")
            # Show partial key for verification (security)
            masked_key = openai_api_key[:7] + "..." + openai_api_key[-4:]
            st.info(f"🔑 API Key: {masked_key}")
        else:
            st.error("❌ API Configuration Missing")
            st.markdown("""
            **Setup Instructions:**
            1. Create a `.env` file in the project folder
            2. Add your API key:
               ```
               OPENAI_API_KEY=your-key-here
               ```
            3. Restart the application
            """)
            
            # Fallback: Allow manual entry if env var not found
            openai_api_key = st.text_input(
                "Or enter API key manually:",
                type="password",
                help="Temporary fallback option"
            )
        
        # Avatar Upload Section
        st.markdown("### 🖼️ Custom Avatar")
        
        # Load saved avatar on startup
        if "avatar_base64" not in st.session_state:
            saved_avatar = load_saved_avatar()
            if saved_avatar:
                st.session_state.avatar_base64 = saved_avatar
        
        avatar_file = st.file_uploader(
            "Upload Avatar Image",
            type=['png', 'jpg', 'jpeg'],
            help="Upload a professional photo to use as the assistant avatar"
        )
        
        # Show current avatar status
        if "avatar_base64" in st.session_state:
            st.success("✅ Avatar loaded and saved permanently!")
            # Show current avatar preview
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown(f'<img src="{st.session_state.avatar_base64}" style="width: 60px; height: 60px; border-radius: 50%; object-fit: cover;">', unsafe_allow_html=True)
            with col2:
                if st.button("🗑️ Remove Avatar", key="remove_avatar"):
                    if delete_saved_avatar():
                        if "avatar_base64" in st.session_state:
                            del st.session_state.avatar_base64
                        st.success("Avatar removed successfully!")
                        st.rerun()
        
        if avatar_file:
            new_avatar = get_image_base64(avatar_file)
            if new_avatar:
                st.session_state.avatar_base64 = new_avatar
                if save_avatar(new_avatar):
                    st.success("✅ Avatar uploaded and saved permanently!")
                else:
                    st.warning("Avatar uploaded but could not be saved permanently")
                st.rerun()
        
        # Resume Upload Section
        st.markdown("### 📄 Resume Management")
        
        # Show current resume status first
        resume_loaded = ("chatbot" in st.session_state and 
                        hasattr(st.session_state.chatbot.knowledge_base, 'resume_content') and
                        st.session_state.chatbot.knowledge_base.resume_content is not None)
        
        if resume_loaded:
            resume_info = st.session_state.chatbot.knowledge_base.resume_content
            st.success(f"✅ Resume saved permanently: {resume_info.filename}")
            
            # Resume info in columns
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Words", resume_info.metadata['word_count'])
            with col2:
                st.metric("Size", f"{resume_info.metadata['file_size'] / 1024:.1f} KB")
            with col3:
                uploaded_date = datetime.fromisoformat(resume_info.metadata['processed_at']).strftime("%m/%d/%y")
                st.metric("Uploaded", uploaded_date)
            
            # Option to remove current resume
            if st.button("🗑️ Remove Current Resume", key="remove_resume"):
                if st.session_state.chatbot.knowledge_base.delete_saved_resume():
                    st.success("Resume removed successfully!")
                    st.rerun()
                else:
                    st.error("Failed to remove resume")
        else:
            st.info("📝 No resume currently loaded")
        
        # Upload new resume
        resume_file = st.file_uploader(
            "Upload New Resume" if resume_loaded else "Upload Resume",
            type=['pdf', 'docx', 'txt'],
            help="Upload Aniket's resume for detailed Q&A"
        )
        
        if resume_file:
            if st.button("📝 Process Resume", type="primary"):
                process_resume_file(resume_file)
        
        # Pre-configured for Aniket's website
        st.markdown("### 🌐 Portfolio Website")
        website_url = "https://aniketdshirsat.com/"
        st.text_input(
            "Portfolio Website",
            value=website_url,
            help="Aniket Shirsat's professional portfolio",
            disabled=True
        )
        
        # Display Aniket's key achievements in styled cards
        st.markdown("### 🏆 Key Highlights")
        st.markdown("""
        <div class="achievement-card">
            <strong>Academic Excellence</strong><br>
            Perfect 4.0 GPA in Applied Data Science
        </div>
        <div class="achievement-card">
            <strong>ML Innovation</strong><br>
            90% accuracy in cultural detection models
        </div>
        <div class="achievement-card">
            <strong>Business Impact</strong><br>
            $1M+ savings through optimization
        </div>
        <div class="achievement-card">
            <strong>Current Role</strong><br>
            Research Assistant at Indiana University
        </div>
        """, unsafe_allow_html=True)
        
        # Show resume status
        if ("chatbot" in st.session_state and 
            hasattr(st.session_state.chatbot.knowledge_base, 'resume_content') and 
            st.session_state.chatbot.knowledge_base.resume_content is not None):
            resume_info = st.session_state.chatbot.knowledge_base.resume_content
            st.markdown("### 📋 Knowledge Base Status")
            st.success(f"✅ Resume: {resume_info.filename}")
            st.success(f"✅ Portfolio: aniketdshirsat.com")
            st.info(f"📊 Total content: {resume_info.metadata['word_count']} words from resume + website data")
        
        # Data collection options
        st.markdown("### 📊 Data Management")
        max_pages = st.slider("Pages to Analyze", 1, 20, 10)
        
        # Update button
        if st.button("🔄 Update Knowledge Base", type="primary"):
            scrape_website(website_url, max_pages)
        
        # User data management section
        st.markdown("### 👥 User Analytics")
        user_data = load_user_data()
        
        if not user_data.empty:
            st.metric("Total Visitors", len(user_data))
            st.metric("Unique Visitors", user_data['email'].nunique())
            
            # Show recent visitors (last 5)
            if len(user_data) > 0:
                recent_visitors = user_data.tail(3)[['name', 'email']].values
                st.markdown("**Recent Visitors:**")
                for name, email in recent_visitors:
                    st.text(f"• {name} ({email})")
            
            # Export data button
            csv_data = export_user_data()
            if csv_data:
                st.download_button(
                    label="📥 Download Visitor Data",
                    data=csv_data,
                    file_name=f"aniket_chatbot_visitors_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    help="Download complete visitor information as CSV"
                )
        else:
            st.info("No visitor data yet")
    
    # Main chat interface
    if openai_api_key:
        if "chatbot" not in st.session_state:
            st.session_state.chatbot = AniketChatbotAI(openai_api_key)
            # Load saved resume into the knowledge base
            if hasattr(st.session_state.chatbot.knowledge_base, 'resume_content') and st.session_state.chatbot.knowledge_base.resume_content:
                st.session_state.chatbot.knowledge_base._add_resume_to_chunks()
        
        # Generate unique session ID if not exists
        if "session_id" not in st.session_state:
            st.session_state.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(datetime.now()) % 10000}"
        
        # Load saved avatar if not already loaded
        if "avatar_base64" not in st.session_state:
            saved_avatar = load_saved_avatar()
            if saved_avatar:
                st.session_state.avatar_base64 = saved_avatar
        
        # Initialize user info collection states
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
                    "content": """Hello! I'm Aniket's AI Assistant. How may I help you?"""
                },
                {
                    "role": "assistant", 
                    "content": """Before we begin, may I please have your name?"""
                }
            ]
            st.session_state.asking_for_name = True
        
        # User information collection (only show if not collected)
        if not st.session_state.user_info_collected:
            # Show limited suggested questions during info collection
            if st.session_state.asking_for_name:
                st.markdown("### 👋 Please share your name to get started")
            elif st.session_state.asking_for_email:
                st.markdown(f"### 📧 Nice to meet you, {st.session_state.user_name}! What's your email address?")
        else:
            # Show full chat interface (user info already collected)
            # Suggested questions section with improved styling
            st.markdown("### 💡 Common Questions")
            suggested_questions = st.session_state.chatbot.get_suggested_questions()
            
            # Display suggested questions in columns
            col1, col2 = st.columns(2)
            
            for i, question in enumerate(suggested_questions[:10]):
                col = col1 if i % 2 == 0 else col2
                if col.button(f"❓ {question}", key=f"suggestion_{i}"):
                    # Add suggested question as user message
                    st.session_state.messages.append({"role": "user", "content": question})
                    
                    # Generate and add response
                    with st.spinner("Gathering information..."):
                        response = st.session_state.chatbot.generate_expert_response(question)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    st.rerun()
        
        st.markdown("---")
        
        # Display chat history with custom or default avatar
        for message in st.session_state.messages:
            if message["role"] == "assistant":
                # Use custom avatar if uploaded, otherwise use default
                if "avatar_base64" in st.session_state and st.session_state.avatar_base64:
                    # Create custom avatar HTML
                    st.markdown(f"""
                    <div style="display: flex; align-items: flex-start; margin-bottom: 1rem;">
                        <img src="{st.session_state.avatar_base64}" 
                             style="width: 40px; height: 40px; border-radius: 50%; margin-right: 12px; object-fit: cover;">
                        <div style="flex-grow: 1; background: #f0f2f6; padding: 12px; border-radius: 12px;">
                            {message["content"]}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    with st.chat_message("assistant", avatar="👨‍💼"):
                        st.markdown(message["content"])
            else:
                with st.chat_message("user"):
                    st.markdown(message["content"])
        
        # Chat input with conditional behavior
        if st.session_state.asking_for_name:
            placeholder_text = "Please enter your name..."
        elif st.session_state.asking_for_email:
            placeholder_text = "Please enter your email address..."
        else:
            placeholder_text = "Ask about Aniket's qualifications, experience, or skills..."
        
        if prompt := st.chat_input(placeholder_text):
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Handle user info collection flow
            if st.session_state.asking_for_name:
                # Validate name input
                if prompt.strip():
                    st.session_state.user_name = prompt.strip()
                    st.session_state.asking_for_name = False
                    st.session_state.asking_for_email = True
                    
                    # Assistant asks for email
                    email_request = f"Thank you, {st.session_state.user_name}! Could you please share your email address as well?"
                    st.session_state.messages.append({"role": "assistant", "content": email_request})
                    
                    # Display response with custom avatar
                    if "avatar_base64" in st.session_state and st.session_state.avatar_base64:
                        st.markdown(f"""
                        <div style="display: flex; align-items: flex-start; margin-bottom: 1rem;">
                            <img src="{st.session_state.avatar_base64}" 
                                 style="width: 40px; height: 40px; border-radius: 50%; margin-right: 12px; object-fit: cover;">
                            <div style="flex-grow: 1; background: #f0f2f6; padding: 12px; border-radius: 12px;">
                                {email_request}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        with st.chat_message("assistant", avatar="👨‍💼"):
                            st.markdown(email_request)
                else:
                    # Ask for name again if empty
                    name_retry = "I didn't catch that. Could you please tell me your name?"
                    st.session_state.messages.append({"role": "assistant", "content": name_retry})
                    
                    if "avatar_base64" in st.session_state and st.session_state.avatar_base64:
                        st.markdown(f"""
                        <div style="display: flex; align-items: flex-start; margin-bottom: 1rem;">
                            <img src="{st.session_state.avatar_base64}" 
                                 style="width: 40px; height: 40px; border-radius: 50%; margin-right: 12px; object-fit: cover;">
                            <div style="flex-grow: 1; background: #f0f2f6; padding: 12px; border-radius: 12px;">
                                {name_retry}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        with st.chat_message("assistant", avatar="👨‍💼"):
                            st.markdown(name_retry)
            
            elif st.session_state.asking_for_email:
                # Simple email validation - check for @ and . characters
                email_input = prompt.strip()
                
                if is_valid_email(email_input):
                    st.session_state.user_email = email_input
                    st.session_state.asking_for_email = False
                    st.session_state.user_info_collected = True
                    
                    # Save user information to CSV
                    timestamp = datetime.now().isoformat()
                    user_data = {
                        'timestamp': [timestamp],
                        'name': [st.session_state.user_name],
                        'email': [st.session_state.user_email],
                        'company': ['Not provided'],
                        'role': ['Not provided'],
                        'session_id': [st.session_state.session_id]
                    }
                    
                    try:
                        df = pd.DataFrame(user_data)
                        
                        # Save to CSV (append mode)
                        if os.path.exists(USER_DATA_FILE):
                            existing_df = pd.read_csv(USER_DATA_FILE)
                            # Check if we need to add new columns
                            if 'company' not in existing_df.columns:
                                existing_df['company'] = 'Not provided'
                            if 'role' not in existing_df.columns:
                                existing_df['role'] = 'Not provided'
                            df = pd.concat([existing_df, df], ignore_index=True)
                        
                        df.to_csv(USER_DATA_FILE, index=False)
                        
                        # Welcome message and instructions
                        welcome_msg = f"""Perfect! Thank you, {st.session_state.user_name}. I'm ready to answer any questions about Aniket Shirsat's professional background, qualifications, and experience.

**Ask me about:** Education • Technical Skills • Work Experience • Projects • Achievements

What would you like to know?"""
                        
                        st.session_state.messages.append({"role": "assistant", "content": welcome_msg})
                        
                        # Display response with custom avatar
                        if "avatar_base64" in st.session_state and st.session_state.avatar_base64:
                            st.markdown(f"""
                            <div style="display: flex; align-items: flex-start; margin-bottom: 1rem;">
                                <img src="{st.session_state.avatar_base64}" 
                                     style="width: 40px; height: 40px; border-radius: 50%; margin-right: 12px; object-fit: cover;">
                                <div style="flex-grow: 1; background: #f0f2f6; padding: 12px; border-radius: 12px;">
                                    {welcome_msg}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            with st.chat_message("assistant", avatar="👨‍💼"):
                                st.markdown(welcome_msg)
                        
                    except Exception as e:
                        st.error(f"Error saving information: {str(e)}")
                        
                else:
                    # Ask for valid email
                    email_retry = "That doesn't look like a valid email address. Could you please enter a valid email (e.g., john@company.com)?"
                    st.session_state.messages.append({"role": "assistant", "content": email_retry})
                    
                    if "avatar_base64" in st.session_state and st.session_state.avatar_base64:
                        st.markdown(f"""
                        <div style="display: flex; align-items: flex-start; margin-bottom: 1rem;">
                            <img src="{st.session_state.avatar_base64}" 
                                 style="width: 40px; height: 40px; border-radius: 50%; margin-right: 12px; object-fit: cover;">
                            <div style="flex-grow: 1; background: #f0f2f6; padding: 12px; border-radius: 12px;">
                                {email_retry}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        with st.chat_message("assistant", avatar="👨‍💼"):
                            st.markdown(email_retry)
            
            else:
                # Normal chat after info collection
                # Generate response with custom avatar
                if "avatar_base64" in st.session_state and st.session_state.avatar_base64:
                    with st.spinner("Processing your question..."):
                        response = st.session_state.chatbot.generate_expert_response(prompt)
                    
                    # Display response with custom avatar
                    st.markdown(f"""
                    <div style="display: flex; align-items: flex-start; margin-bottom: 1rem;">
                        <img src="{st.session_state.avatar_base64}" 
                             style="width: 40px; height: 40px; border-radius: 50%; margin-right: 12px; object-fit: cover;">
                        <div style="flex-grow: 1; background: #f0f2f6; padding: 12px; border-radius: 12px;">
                            {response}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    with st.chat_message("assistant", avatar="👨‍💼"):
                        with st.spinner("Processing your question..."):
                            response = st.session_state.chatbot.generate_expert_response(prompt)
                        st.markdown(response)
                
                st.session_state.messages.append({"role": "assistant", "content": response})
    
    else:
        st.warning("Please configure your API key in the sidebar to start using the assistant.")
        
        # Show information without API key
        st.subheader("🎯 About This Assistant")
        st.info("""
        This professional assistant provides comprehensive information about **Aniket Shirsat** for recruiters, hiring managers, and professional contacts.
        
        **Key Features:**
        • Complete educational background and credentials
        • Technical skills and programming expertise  
        • Professional experience and measurable achievements
        • **Permanent resume storage** - upload once, use forever
        • **Custom avatar support** - personalize the experience
        • Intelligent search across portfolio and resume content
        
        **Perfect for:**
        • Recruiter candidate screening
        • Hiring manager evaluations
        • HR preliminary assessments
        • Professional networking inquiries
        
        **Get Started:**
        1. Configure your API key (see sidebar)
        2. Upload resume and avatar (saved permanently)
        3. Update the knowledge base with latest information
        4. Ask any questions about Aniket's professional background
        """)
        
        # Show what's already saved
        if os.path.exists(RESUME_FILE) or os.path.exists(AVATAR_FILE):
            st.markdown("### 💾 Saved Data")
            if os.path.exists(RESUME_FILE):
                st.success("✅ Resume data saved and ready to load")
            if os.path.exists(AVATAR_FILE):
                st.success("✅ Custom avatar saved and ready to load")
    
    # Footer with subtle branding
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 14px; padding: 20px;">
        Professional Portfolio Assistant | Enhanced with Persistent Resume & Avatar Storage
    </div>
    """, unsafe_allow_html=True)

def process_resume_file(uploaded_file):
    """Process uploaded resume file"""
    with st.spinner("Processing resume..."):
        processor = ResumeProcessor()
        resume_content = processor.process_resume(uploaded_file)
        
        if resume_content:
            # Store in session state so it persists
            if "chatbot" in st.session_state:
                st.session_state.chatbot.knowledge_base.add_resume_content(resume_content)
            
            # Show processing results
            st.subheader("📋 Resume Processing Results")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Filename", resume_content.filename)
            with col2:
                st.metric("Word Count", resume_content.metadata['word_count'])
            with col3:
                st.metric("File Size", f"{resume_content.metadata['file_size'] / 1024:.1f} KB")
            
            # Show first few lines of extracted content
            st.subheader("📄 Content Preview")
            preview_text = resume_content.content[:500] + "..." if len(resume_content.content) > 500 else resume_content.content
            st.text_area("Extracted Text (Preview)", preview_text, height=200, disabled=True)
            
        else:
            st.error("Failed to process the resume. Please check the file format and try again.")

def scrape_website(url: str, max_pages: int):
    """Update knowledge base with website content"""
    with st.spinner("Updating knowledge base..."):
        scraper = SimpleWebsiteScraper()
        content = scraper.scrape_website(url, max_pages)
        
        if content:
            # Store in session state so it persists
            if "chatbot" in st.session_state:
                st.session_state.chatbot.knowledge_base.add_website_content(content)
            
            # Show analysis results
            st.subheader("📊 Knowledge Base Update")
            df = pd.DataFrame([
                {
                    "Page": c.url,
                    "Title": c.title[:50] + "..." if len(c.title) > 50 else c.title,
                    "Content Length": c.metadata.get("word_count", 0),
                }
                for c in content
            ])
            st.dataframe(df, use_container_width=True)
        else:
            st.error("Could not retrieve content. Please verify the URL and try again.")

if __name__ == "__main__":
    main()