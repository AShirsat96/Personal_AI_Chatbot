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
        img = img.resize((50, 50), Image.Resampling.LANCZOS)
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
            resume_context = "\n\nRESUME INFORMATION: You have access to Aniket's detailed resume content. Use this information to provide specific details about his work experience, education, skills, projects, and achievements. When answering questions about his background, prioritize information from the resume as it contains the most current and detailed information."
        
        return f"""You are Aniket's AI assistant, providing information about Aniket Shirsat's qualifications and experience. Respond naturally and conversationally, as if you're representing him professionally.
        
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
            expertise_context = "Aniket brings solid experience in data science and machine learning. He's currently working toward his Master's in Applied Data Science at Indiana University with a perfect 4.0 GPA while serving as a Research Assistant. His background includes practical work developing ML models for cultural ambiguity detection that achieved 90% accuracy, plus vessel fuel optimization models that generated $1M in annual savings. He combines academic excellence with real-world application experience."
        elif any(keyword in query_lower for keyword in ['skills', 'technical', 'programming']):
            expertise_context = "His technical toolkit covers the essentials: Python, R, and SQL for programming, plus experience across AWS, Azure, and GCP cloud platforms. He specializes in machine learning, computer vision, and natural language processing, with hands-on experience building advanced analytics solutions. What stands out is his ability to translate technical skills into measurable business results."
        elif any(keyword in query_lower for keyword in ['projects', 'research', 'work']):
            expertise_context = "Some notable work includes developing cultural ambiguity detection systems for advertisements with 90% accuracy, creating vessel fuel optimization models that reduced consumption by 5% across 50+ vessels (saving $1M annually), and building dataset pipelines for annotated advertisement images. His research spans computer vision and NLP applications, often with practical business applications."
        elif any(keyword in query_lower for keyword in ['collaboration', 'contact', 'connect', 'hire', 'opportunity']):
            expertise_context = "Aniket is actively seeking full-time opportunities in data science and machine learning roles. His combination of strong academic performance, research experience, and proven ability to deliver quantifiable business results makes him well-suited for analyst, engineer, or research positions. He's particularly interested in roles where he can apply ML to solve real-world problems."
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

def main():
    """Main Streamlit application - Aniket Shirsat's Portfolio Assistant"""
    st.set_page_config(
        page_title="Ask Aniket",
        page_icon="👨‍💼",
        layout="centered",
        initial_sidebar_state="collapsed"
    )
    
    # Custom CSS for chat widget-style interface
    st.markdown("""
    <style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 500px;
    }
    
    .chat-widget {
        background: white;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        overflow: hidden;
        max-width: 450px;
        margin: 0 auto;
        border: 1px solid #e0e0e0;
    }
    
    .chat-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px 20px;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .chat-avatar {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        border: 2px solid rgba(255,255,255,0.3);
        object-fit: cover;
    }
    
    .chat-info h3 {
        margin: 0;
        font-size: 18px;
        font-weight: 600;
    }
    
    .chat-info p {
        margin: 0;
        font-size: 13px;
        opacity: 0.9;
    }
    
    .chat-messages {
        height: 400px;
        overflow-y: auto;
        padding: 20px;
        background: #f8f9fa;
    }
    
    .message {
        margin-bottom: 15px;
        display: flex;
        align-items: flex-start;
        gap: 10px;
    }
    
    .message.user {
        flex-direction: row-reverse;
    }
    
    .message-avatar {
        width: 35px;
        height: 35px;
        border-radius: 50%;
        object-fit: cover;
        flex-shrink: 0;
    }
    
    .message-content {
        background: white;
        padding: 12px 16px;
        border-radius: 18px;
        max-width: 280px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        font-size: 14px;
        line-height: 1.4;
    }
    
    .message.user .message-content {
        background: #667eea;
        color: white;
    }
    
    .message-time {
        font-size: 11px;
        color: #888;
        margin-top: 4px;
        text-align: right;
    }
    
    .powered-by {
        text-align: center;
        font-size: 11px;
        color: #888;
        padding: 10px;
        background: #f5f5f5;
        border-top: 1px solid #eee;
    }
    
    .stApp > footer {
        visibility: hidden;
    }
    
    .stChatInput > div > div > div {
        border-radius: 20px !important;
        border: 1px solid #ddd !important;
    }
    
    .stChatInput input {
        font-size: 14px !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Load API Key from environment variable
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if not openai_api_key:
        st.error("❌ API Configuration Missing - Please set OPENAI_API_KEY in environment")
        return
    
    # Initialize chatbot
    if "chatbot" not in st.session_state:
        st.session_state.chatbot = AniketChatbotAI(openai_api_key)
    
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
                "content": "Hello! I'm Aniket's AI assistant. I'm here to help answer any questions about Aniket's professional background, qualifications, and experience.",
                "timestamp": datetime.now()
            },
            {
                "role": "assistant", 
                "content": "Before we begin, may I please have your name?",
                "timestamp": datetime.now()
            }
        ]
        st.session_state.asking_for_name = True
    
    # Get avatar for display
    avatar_src = st.session_state.get("avatar_base64", "https://via.placeholder.com/40x40/667eea/ffffff?text=A")
    
    # Custom CSS for modern chat interface with proper message display
    st.markdown("""
    <style>
    /* Main container styling */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 800px;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    
    /* Hide Streamlit branding */
    .stApp > footer {
        visibility: hidden;
    }
    
    /* Chat messages container */
    .chat-container {
        background: white;
        padding: 0;
        margin-top: 0;
        width: 100%;
    }
    
    /* Streamlit chat message styling */
    .stChatMessage {
        padding: 1rem !important;
        max-width: 100% !important;
        width: 100% !important;
    }
    
    .stChatMessage > div {
        max-width: 100% !important;
        width: 100% !important;
    }
    
    /* Chat input styling */
    .stChatInput > div > div > div {
        border-radius: 25px !important;
        border: 2px solid #667eea !important;
        background: white !important;
    }
    
    .stChatInput input {
        font-size: 16px !important;
        padding: 12px 20px !important;
    }
    
    /* Ensure messages don't get cut off */
    .stChatMessage [data-testid="chatAvatarIcon-assistant"],
    .stChatMessage [data-testid="chatAvatarIcon-user"] {
        flex-shrink: 0;
    }
    
    .stChatMessage .stMarkdown {
        max-width: 100% !important;
        width: 100% !important;
        word-wrap: break-word;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Chat container - start directly with messages
    with st.container():
        
        # Display messages using Streamlit's native chat components
        for message in st.session_state.messages:
            if message["role"] == "assistant":
                # Use custom avatar if available, otherwise use emoji
                if "avatar_base64" in st.session_state and st.session_state.avatar_base64:
                    # Create custom message with avatar image
                    col1, col2 = st.columns([0.1, 0.9])
                    with col1:
                        st.markdown(f'<img src="{st.session_state.avatar_base64}" style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover;">', unsafe_allow_html=True)
                    with col2:
                        st.markdown(f"""
                        <div style="background: #f0f0f0; padding: 12px 16px; border-radius: 18px; margin-left: 10px;">
                            {message["content"]}
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    with st.chat_message("assistant", avatar="👨‍💼"):
                        st.write(message["content"])
            else:
                with st.chat_message("user"):
                    st.write(message["content"])
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Chat input
    if st.session_state.asking_for_name:
        placeholder_text = "Please enter your name..."
    elif st.session_state.asking_for_email:
        placeholder_text = "Please enter your email address..."
    else:
        placeholder_text = "e.g. What experience does Aniket have?"
    
    if prompt := st.chat_input(placeholder_text):
        # Add user message
        user_message = {
            "role": "user", 
            "content": prompt,
            "timestamp": datetime.now()
        }
        st.session_state.messages.append(user_message)
        
        # Handle user info collection flow
        if st.session_state.asking_for_name:
            # Validate name input
            if prompt.strip():
                st.session_state.user_name = prompt.strip()
                st.session_state.asking_for_name = False
                st.session_state.asking_for_email = True
                
                # Assistant asks for email
                email_request = f"Thank you, {st.session_state.user_name}! Could you please share your email address as well?"
                assistant_message = {
                    "role": "assistant", 
                    "content": email_request,
                    "timestamp": datetime.now()
                }
                st.session_state.messages.append(assistant_message)
            else:
                # Ask for name again if empty
                name_retry = "I didn't catch that. Could you please tell me your name?"
                assistant_message = {
                    "role": "assistant", 
                    "content": name_retry,
                    "timestamp": datetime.now()
                }
                st.session_state.messages.append(assistant_message)
        
        elif st.session_state.asking_for_email:
            # Simple email validation
            email_input = prompt.strip()
            
            if is_valid_email(email_input):
                st.session_state.user_email = email_input
                st.session_state.asking_for_email = False
                st.session_state.user_info_collected = True
                
                # Save user information
                try:
                    timestamp = datetime.now().isoformat()
                    user_data = {
                        'timestamp': [timestamp],
                        'name': [st.session_state.user_name],
                        'email': [st.session_state.user_email],
                        'session_id': [st.session_state.session_id]
                    }
                    
                    df = pd.DataFrame(user_data)
                    
                    # Save to CSV (append mode)
                    if os.path.exists(USER_DATA_FILE):
                        df.to_csv(USER_DATA_FILE, mode='a', header=False, index=False)
                    else:
                        df.to_csv(USER_DATA_FILE, mode='w', header=True, index=False)
                    
                    # Welcome message
                    welcome_msg = f"Perfect! Thank you, {st.session_state.user_name}. I'm ready to answer any questions about Aniket's professional background, qualifications, and experience. What would you like to know?"
                    
                    assistant_message = {
                        "role": "assistant", 
                        "content": welcome_msg,
                        "timestamp": datetime.now()
                    }
                    st.session_state.messages.append(assistant_message)
                    
                except Exception as e:
                    error_msg = "Thanks for the information! I'm ready to help with questions about Aniket's background."
                    assistant_message = {
                        "role": "assistant", 
                        "content": error_msg,
                        "timestamp": datetime.now()
                    }
                    st.session_state.messages.append(assistant_message)
                    
            else:
                # Ask for valid email
                email_retry = "That doesn't look like a valid email address. Could you please enter a valid email (e.g., john@company.com)?"
                assistant_message = {
                    "role": "assistant", 
                    "content": email_retry,
                    "timestamp": datetime.now()
                }
                st.session_state.messages.append(assistant_message)
        
        else:
            # Normal chat after info collection
            with st.spinner("Processing..."):
                response = st.session_state.chatbot.generate_expert_response(prompt)
            
            assistant_message = {
                "role": "assistant", 
                "content": response,
                "timestamp": datetime.now()
            }
            st.session_state.messages.append(assistant_message)
        
        # Rerun to show new messages
        st.rerun()
    
    # Admin panel in sidebar (hidden by default, accessible when needed)
    with st.sidebar:
        st.header("⚙️ Admin Panel")
        st.markdown("*For administrators only*")
        
        # Resume Upload Section
        st.markdown("### 📄 Resume Management")
        
        # Show current resume status
        if hasattr(st.session_state.chatbot.knowledge_base, 'resume_content') and st.session_state.chatbot.knowledge_base.resume_content:
            resume_info = st.session_state.chatbot.knowledge_base.resume_content
            st.success(f"✅ Resume: {resume_info.filename}")
            
            # Resume info
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Words", resume_info.metadata['word_count'])
            with col2:
                st.metric("Size", f"{resume_info.metadata['file_size'] / 1024:.1f} KB")
            
            if st.button("🗑️ Remove Resume"):
                if st.session_state.chatbot.knowledge_base.delete_saved_resume():
                    st.success("Resume removed!")
                    st.rerun()
        else:
            st.info("📝 No resume loaded")
        
        # Upload new resume
        resume_file = st.file_uploader(
            "Upload Resume",
            type=['pdf', 'docx', 'txt'],
            help="Upload Aniket's resume for enhanced responses"
        )
        
        if resume_file and st.button("📝 Process Resume"):
            process_resume_file(resume_file)
        
        # Avatar Upload Section
        st.markdown("### 🖼️ Avatar Management")
        
        if "avatar_base64" in st.session_state:
            st.success("✅ Avatar loaded")
            # Show current avatar preview
            st.image(st.session_state.avatar_base64, width=60)
            if st.button("🗑️ Remove Avatar"):
                if delete_saved_avatar():
                    if "avatar_base64" in st.session_state:
                        del st.session_state.avatar_base64
                    st.success("Avatar removed!")
                    st.rerun()
        else:
            st.info("📷 No avatar loaded")
        
        avatar_file = st.file_uploader(
            "Upload Avatar",
            type=['png', 'jpg', 'jpeg'],
            help="Upload professional avatar image"
        )
        
        if avatar_file:
            new_avatar = get_image_base64(avatar_file)
            if new_avatar:
                st.session_state.avatar_base64 = new_avatar
                save_avatar(new_avatar)
                st.success("✅ Avatar uploaded!")
                st.rerun()
        
        # Website scraping
        st.markdown("### 🌐 Website Data")
        website_url = st.text_input("Website URL", value="https://aniketdshirsat.com/")
        max_pages = st.slider("Pages to analyze", 1, 20, 10)
        
        if st.button("🔄 Update Knowledge Base"):
            scrape_website(website_url, max_pages)
        
        # User data analytics
        st.markdown("### 👥 User Analytics")
        user_data = load_user_data()
        
        if not user_data.empty:
            st.metric("Total Visitors", len(user_data))
            st.metric("Unique Visitors", user_data['email'].nunique())
            
            # Show recent visitors
            if len(user_data) > 0:
                recent_visitors = user_data.tail(5)[['name', 'email']]
                st.markdown("**Recent Visitors:**")
                for _, row in recent_visitors.iterrows():
                    st.text(f"• {row['name']} ({row['email']})")
            
            # Download data
            csv_data = export_user_data()
            if csv_data:
                st.download_button(
                    "📥 Download Visitor Data",
                    csv_data,
                    f"aniket_visitors_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv",
                    help="Download complete visitor data as CSV"
                )
        else:
            st.info("No visitor data yet")
        
        # System info
        st.markdown("### ⚡ System Status")
        knowledge_chunks = len(st.session_state.chatbot.knowledge_base.content_chunks) if hasattr(st.session_state.chatbot.knowledge_base, 'content_chunks') else 0
        st.metric("Knowledge Chunks", knowledge_chunks)
        st.metric("Session ID", st.session_state.session_id[-8:])  # Show last 8 chars

def process_resume_file(uploaded_file):
    """Process uploaded resume file"""
    with st.spinner("Processing resume..."):
        processor = ResumeProcessor()
        resume_content = processor.process_resume(uploaded_file)
        
        if resume_content:
            if "chatbot" in st.session_state:
                st.session_state.chatbot.knowledge_base.add_resume_content(resume_content)
            st.success(f"Resume processed: {resume_content.metadata['word_count']} words")
        else:
            st.error("Failed to process resume")

def scrape_website(url: str, max_pages: int):
    """Update knowledge base with website content"""
    with st.spinner("Updating knowledge base..."):
        scraper = SimpleWebsiteScraper()
        content = scraper.scrape_website(url, max_pages)
        
        if content and "chatbot" in st.session_state:
            st.session_state.chatbot.knowledge_base.add_website_content(content)
            st.success(f"Updated with {len(content)} pages")
        else:
            st.error("Could not retrieve content")

if __name__ == "__main__":
    main()
