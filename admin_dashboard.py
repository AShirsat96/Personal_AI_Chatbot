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
        text = ' '.join(text.split())
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
            
            time.sleep(1)
        
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

def get_image_base64(image_file):
    """Convert uploaded image to base64 string"""
    try:
        img = Image.open(image_file)
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
            csv_string = df.to_csv(index=False)
            return csv_string
        return None
    except Exception as e:
        st.error(f"Error exporting user data: {str(e)}")
        return None

class AniketChatbotAI:
    """Professional assistant for Aniket Shirsat's portfolio"""
    
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.knowledge_base = SimpleKnowledgeBase()

def main():
    """Admin Dashboard - Complete management interface"""
    st.set_page_config(
        page_title="Aniket Shirsat - Admin Dashboard",
        page_icon="⚙️",
        layout="wide"
    )
    
    # Password protection for admin panel
    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False
    
    if not st.session_state.admin_authenticated:
        st.title("🔐 Admin Panel - Authentication Required")
        
        admin_password = st.text_input("Enter Admin Password:", type="password")
        
        if st.button("Login"):
            correct_password = os.getenv("ADMIN_PASSWORD", "admin123")
            
            if admin_password == correct_password:
                st.session_state.admin_authenticated = True
                st.success("Authentication successful! Redirecting...")
                st.rerun()
            else:
                st.error("Incorrect password. Please try again.")
        
        st.info("This is the admin panel for managing Aniket's portfolio assistant. Access is restricted to authorized users only.")
        return
    
    # Custom CSS for admin dashboard
    st.markdown("""
    <style>
    .admin-header {
        text-align: center; 
        padding: 25px; 
        background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%); 
        color: white; 
        border-radius: 15px; 
        margin-bottom: 30px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .metric-card {
        background: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #2c3e50;
        margin: 10px 0;
        text-align: center;
    }
    .status-section {
        background: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        margin: 15px 0;
    }
    .danger-zone {
        background: #fff5f5;
        border: 2px solid #feb2b2;
        padding: 20px;
        border-radius: 10px;
        margin: 20px 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Admin header
    st.markdown("""
    <div class="admin-header">
        <h1>⚙️ Aniket Shirsat Portfolio - Admin Dashboard</h1>
        <p style="margin: 0; opacity: 0.9;">Complete Management & Analytics Interface</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Logout button in sidebar
    with st.sidebar:
        if st.button("🚪 Logout", type="secondary"):
            st.session_state.admin_authenticated = False
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 🎯 Quick Actions")
        
    # Main admin interface
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Analytics Dashboard", 
        "📄 Resume Management", 
        "🖼️ Avatar Management", 
        "🌐 Website Scraping", 
        "⚙️ System Settings"
    ])
    
    # Tab 1: Analytics Dashboard
    with tab1:
        st.header("📊 User Analytics & Insights")
        
        user_data = load_user_data()
        
        if not user_data.empty:
            # Main metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <h3>{len(user_data)}</h3>
                    <p>Total Visitors</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                unique_visitors = user_data['email'].nunique()
                st.markdown(f"""
                <div class="metric-card">
                    <h3>{unique_visitors}</h3>
                    <p>Unique Visitors</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                user_data['timestamp'] = pd.to_datetime(user_data['timestamp'])
                recent_visitors = user_data[user_data['timestamp'] > (datetime.now() - pd.Timedelta(days=7))]
                st.markdown(f"""
                <div class="metric-card">
                    <h3>{len(recent_visitors)}</h3>
                    <p>Recent (7 days)</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                return_visitors = user_data['email'].value_counts().sum() - unique_visitors
                st.markdown(f"""
                <div class="metric-card">
                    <h3>{return_visitors}</h3>
                    <p>Return Visits</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Detailed analytics
            st.subheader("📈 Detailed Analytics")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📅 Visitor Timeline")
                user_data['date'] = user_data['timestamp'].dt.date
                daily_visitors = user_data.groupby('date').size().reset_index(name='visitors')
                st.line_chart(daily_visitors.set_index('date'))
            
            with col2:
                st.subheader("🔄 Visitor Type Distribution")
                visitor_types = pd.DataFrame({
                    'Type': ['New Visitors', 'Return Visitors'],
                    'Count': [unique_visitors, return_visitors]
                })
                st.bar_chart(visitor_types.set_index('Type'))
            
            # Recent visitors table
            st.subheader("👥 Recent Visitors")
            display_data = user_data.copy()
            display_data['timestamp'] = display_data['timestamp'].dt.strftime('%Y-%m-%d %H:%M')
            display_data = display_data.sort_values('timestamp', ascending=False).head(10)
            st.dataframe(display_data[['timestamp', 'name', 'email']], use_container_width=True)
            
            # Export functionality
            st.subheader("📥 Data Export")
            csv_data = export_user_data()
            if csv_data:
                st.download_button(
                    label="📥 Download Complete Visitor Data (CSV)",
                    data=csv_data,
                    file_name=f"aniket_portfolio_analytics_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    help="Download complete visitor analytics data"
                )
            
        else:
            st.info("📊 No visitor data available yet. The analytics will populate as users interact with the chatbot.")
            
    # Tab 2: Resume Management
    with tab2:
        st.header("📄 Resume Management")
        
        # Current resume status
        if "chatbot" not in st.session_state:
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if openai_api_key:
                st.session_state.chatbot = AniketChatbotAI(openai_api_key)
        
        resume_loaded = False
        if "chatbot" in st.session_state:
            resume_loaded = (hasattr(st.session_state.chatbot.knowledge_base, 'resume_content') and 
                           st.session_state.chatbot.knowledge_base.resume_content is not None)
        
        if resume_loaded:
            st.success("✅ Resume Currently Loaded")
            resume_info = st.session_state.chatbot.knowledge_base.resume_content
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Filename", resume_info.filename)
            with col2:
                st.metric("Word Count", resume_info.metadata['word_count'])
            with col3:
                st.metric("File Size", f"{resume_info.metadata['file_size'] / 1024:.1f} KB")
            with col4:
                upload_date = datetime.fromisoformat(resume_info.metadata['processed_at']).strftime("%m/%d/%Y")
                st.metric("Upload Date", upload_date)
            
            # Preview content
            st.subheader("📄 Content Preview")
            preview_text = resume_info.content[:1000] + "..." if len(resume_info.content) > 1000 else resume_info.content
            st.text_area("Resume Content (First 1000 characters)", preview_text, height=200, disabled=True)
            
            # Management actions
            st.subheader("🔧 Management Actions")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Remove Current Resume", type="secondary"):
                    if st.session_state.chatbot.knowledge_base.delete_saved_resume():
                        st.success("Resume removed successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to remove resume")
            
            with col2:
                st.markdown("**Test Resume Search:**")
                test_query = st.text_input("Search query:", "education background")
                if st.button("🔍 Test Search"):
                    results = st.session_state.chatbot.knowledge_base.search(test_query, n_results=3)
                    for i, result in enumerate(results):
                        st.write(f"**Result {i+1} (Score: {result['score']:.2f}):**")
                        st.write(result['content'][:200] + "...")
                        st.write("---")
        
        else:
            st.warning("⚠️ No resume currently loaded")
        
        st.markdown("---")
        
        # Upload new resume
        st.subheader("📤 Upload New Resume")
        resume_file = st.file_uploader(
            "Choose Resume File",
            type=['pdf', 'docx', 'txt'],
            help="Supported formats: PDF, DOCX, TXT"
        )
        
        if resume_file:
            if st.button("📝 Process & Save Resume", type="primary"):
                process_resume_file(resume_file)
    
    # Tab 3: Avatar Management
    with tab3:
        st.header("🖼️ Avatar Management")
        
        saved_avatar = load_saved_avatar()
        
        if saved_avatar:
            st.success("✅ Custom Avatar Currently Active")
            
            col1, col2 = st.columns([1, 3])
            with col1:
                st.markdown(f'<img src="{saved_avatar}" style="width: 100px; height: 100px; border-radius: 50%; object-fit: cover; border: 3px solid #2c3e50;">', unsafe_allow_html=True)
            
            with col2:
                st.markdown("**Current Avatar Details:**")
                st.write("- Format: Base64 PNG")
                st.write("- Size: 100x100 pixels")
                st.write("- Status: Active and saved permanently")
                
                if st.button("🗑️ Remove Current Avatar", type="secondary"):
                    if delete_saved_avatar():
                        st.success("Avatar removed successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to remove avatar")
        
        else:
            st.info("ℹ️ No custom avatar currently set. Using default avatar.")
        
        st.markdown("---")
        
        # Upload new avatar
        st.subheader("📤 Upload New Avatar")
        avatar_file = st.file_uploader(
            "Choose Avatar Image",
            type=['png', 'jpg', 'jpeg'],
            help="Recommended: Square image, at least 100x100 pixels"
        )
        
        if avatar_file:
            st.subheader("🔍 Preview")
            preview_avatar = get_image_base64(avatar_file)
            if preview_avatar:
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.markdown(f'<img src="{preview_avatar}" style="width: 100px; height: 100px; border-radius: 50%; object-fit: cover; border: 3px solid #2c3e50;">', unsafe_allow_html=True)
                with col2:
                    st.write("**Preview of uploaded avatar**")
                    if st.button("💾 Save This Avatar", type="primary"):
                        if save_avatar(preview_avatar):
                            st.success("✅ Avatar saved successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to save avatar")
    
    # Tab 4: Website Scraping
    with tab4:
        st.header("🌐 Website Content Management")
        
        st.subheader("🔧 Scraping Configuration")
        
        col1, col2 = st.columns(2)
        with col1:
            website_url = st.text_input(
                "Portfolio Website URL",
                value="https://aniketdshirsat.com/",
                help="URL of Aniket's portfolio website"
            )
        
        with col2:
            max_pages = st.slider(
                "Maximum Pages to Analyze",
                min_value=1,
                max_value=50,
                value=10,
                help="Number of pages to scrape from the website"
            )
        
        # Current knowledge base status
        st.subheader("📊 Knowledge Base Status")
        
        if "chatbot" in st.session_state:
            kb = st.session_state.chatbot.knowledge_base
            
            total_chunks = len(kb.content_chunks)
            resume_chunks = len([m for m in kb.metadata if m.get('source_type') == 'resume'])
            website_chunks = total_chunks - resume_chunks
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Content Chunks", total_chunks)
            with col2:
                st.metric("Resume Chunks", resume_chunks)
            with col3:
                st.metric("Website Chunks", website_chunks)
            
            if kb.metadata:
                st.subheader("📋 Content Sources")
                sources_df = pd.DataFrame(kb.metadata)
                if not sources_df.empty:
                    source_summary = sources_df.groupby('source_type').agg({
                        'chunk_id': 'count',
                        'word_count': 'sum'
                    }).rename(columns={'chunk_id': 'chunks', 'word_count': 'total_words'})
                    st.dataframe(source_summary, use_container_width=True)
        
        # Scraping actions
        st.subheader("🚀 Update Knowledge Base")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Update Website Content", type="primary"):
                scrape_website(website_url, max_pages)
        
        with col2:
            if st.button("🧪 Test Single Page", type="secondary"):
                with st.spinner("Testing single page scrape..."):
                    scraper = SimpleWebsiteScraper()
                    content = scraper.scrape_page(website_url)
                    if content:
                        st.success(f"✅ Successfully scraped: {content.title}")
                        st.write(f"Content length: {len(content.content)} characters")
                        st.write(f"Word count: {content.metadata['word_count']}")
                    else:
                        st.error("❌ Failed to scrape the page")
        
        # Advanced settings
        with st.expander("⚙️ Advanced Scraping Settings"):
            st.info("Coming soon: Custom selectors, content filters, and scheduling options")
    
    # Tab 5: System Settings
    with tab5:
        st.header("⚙️ System Settings & Configuration")
        
        # API Configuration
        st.subheader("🔑 API Configuration")
        
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key:
            masked_key = openai_api_key[:7] + "..." + openai_api_key[-4:]
            st.success(f"✅ OpenAI API Key configured: {masked_key}")
        else:
            st.error("❌ OpenAI API Key not found in environment variables")
            st.code("Create a .env file with: OPENAI_API_KEY=your-key-here")
        
        # File system status
        st.subheader("📁 File System Status")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Data Directory:**")
            if os.path.exists(DATA_DIR):
                st.success(f"✅ {DATA_DIR} exists")
                
                files = os.listdir(DATA_DIR)
                if files:
                    st.write("**Files:**")
                    for file in files:
                        file_path = os.path.join(DATA_DIR, file)
                        file_size = os.path.getsize(file_path) / 1024
                        st.write(f"- {file} ({file_size:.1f} KB)")
                else:
                    st.info("Directory is empty")
            else:
                st.error(f"❌ {DATA_DIR} not found")
        
        with col2:
            st.write("**Individual Files:**")
            
            files_status = [
                ("Resume Data", RESUME_FILE),
                ("Avatar Data", AVATAR_FILE),
                ("User Data", USER_DATA_FILE)
            ]
            
            for name, path in files_status:
                if os.path.exists(path):
                    size = os.path.getsize(path) / 1024
                    st.success(f"✅ {name}: {size:.1f} KB")
                else:
                    st.warning(f"⚠️ {name}: Not found")
        
        # Chat widget deployment info
        st.subheader("🚀 Deployment Information")
        
        st.info("""
        **Chat Widget Deployment:**
        - Deploy `chat_widget.py` to a public Streamlit app
        - Embed using iframe in your website
        - Clean interface without admin features
        
        **Admin Dashboard:**
        - Deploy `admin_dashboard.py` separately 
        - Password protected for security
        - Complete management functionality
        """)
        
        # Danger zone
        st.markdown("""
        <div class="danger-zone">
            <h3>⚠️ Danger Zone</h3>
            <p>These actions cannot be undone. Use with caution.</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear All User Data", type="secondary"):
                if st.checkbox("I confirm I want to delete all user data"):
                    try:
                        if os.path.exists(USER_DATA_FILE):
                            os.remove(USER_DATA_FILE)
                        st.success("All user data cleared successfully!")
                    except Exception as e:
                        st.error(f"Error clearing user data: {str(e)}")
        
        with col2:
            if st.button("💥 Reset All Data", type="secondary"):
                if st.checkbox("I confirm I want to reset everything"):
                    try:
                        for file in [RESUME_FILE, AVATAR_FILE, USER_DATA_FILE]:
                            if os.path.exists(file):
                                os.remove(file)
                        st.success("All data reset successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error resetting data: {str(e)}")

def process_resume_file(uploaded_file):
    """Process uploaded resume file"""
    with st.spinner("Processing resume..."):
        processor = ResumeProcessor()
        resume_content = processor.process_resume(uploaded_file)
        
        if resume_content:
            if "chatbot" in st.session_state:
                st.session_state.chatbot.knowledge_base.add_resume_content(resume_content)
            
            st.subheader("📋 Resume Processing Results")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Filename", resume_content.filename)
            with col2:
                st.metric("Word Count", resume_content.metadata['word_count'])
            with col3:
                st.metric("File Size", f"{resume_content.metadata['file_size'] / 1024:.1f} KB")
            
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
            if "chatbot" in st.session_state:
                st.session_state.chatbot.knowledge_base.add_website_content(content)
            
            st.subheader("📊 Website Analysis Results")
            df = pd.DataFrame([
                {
                    "Page URL": c.url,
                    "Title": c.title[:50] + "..." if len(c.title) > 50 else c.title,
                    "Content Length": c.metadata.get("word_count", 0),
                    "Scraped At": c.timestamp.strftime("%Y-%m-%d %H:%M")
                }
                for c in content
            ])
            st.dataframe(df, use_container_width=True)
            
            total_words = sum(c.metadata.get("word_count", 0) for c in content)
            st.info(f"📈 Successfully processed {len(content)} pages with {total_words:,} total words")
        else:
            st.error("Could not retrieve content. Please verify the URL and try again.")

if __name__ == "__main__":
    main()
