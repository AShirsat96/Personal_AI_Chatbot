import os
import time
import requests
import streamlit as st
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
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

# GitHub Gist Database Class (enhanced)
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
        """Get default data structure"""
        return {
            "user_interactions": [],
            "conversations": [],
            "conversation_threads": [],
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
    
    def get_user_interactions(self) -> pd.DataFrame:
        """Get all user interactions"""
        try:
            data = self._load_gist_data()
            interactions = data.get("user_interactions", [])
            
            if interactions:
                return pd.DataFrame(interactions)
            else:
                return pd.DataFrame(columns=['timestamp', 'name', 'email', 'session_id'])
                
        except Exception as e:
            st.error(f"Error loading user interactions: {str(e)}")
            return pd.DataFrame(columns=['timestamp', 'name', 'email', 'session_id'])
    
    def get_conversations(self) -> pd.DataFrame:
        """Get all conversation data"""
        try:
            data = self._load_gist_data()
            conversations = data.get("conversations", [])
            
            if conversations:
                return pd.DataFrame(conversations)
            else:
                return pd.DataFrame(columns=[
                    'timestamp', 'session_id', 'user_name', 'user_email', 
                    'user_message', 'bot_response', 'detected_intent', 
                    'response_length', 'message_length'
                ])
                
        except Exception as e:
            st.error(f"Error loading conversations: {str(e)}")
            return pd.DataFrame(columns=[
                'timestamp', 'session_id', 'user_name', 'user_email', 
                'user_message', 'bot_response', 'detected_intent', 
                'response_length', 'message_length'
            ])
    
    def get_conversation_threads(self) -> pd.DataFrame:
        """Get all complete conversation threads"""
        try:
            data = self._load_gist_data()
            threads = data.get("conversation_threads", [])
            
            if threads:
                thread_summaries = []
                for thread in threads:
                    summary = {
                        'session_id': thread['session_id'],
                        'user_name': thread['user_name'],
                        'user_email': thread['user_email'],
                        'start_time': thread['start_time'],
                        'end_time': thread['end_time'],
                        'total_messages': thread['total_messages'],
                        'duration_minutes': self.calculate_conversation_duration(thread['start_time'], thread['end_time']),
                        'saved_at': thread['saved_at']
                    }
                    thread_summaries.append(summary)
                
                return pd.DataFrame(thread_summaries)
            else:
                return pd.DataFrame(columns=[
                    'session_id', 'user_name', 'user_email', 'start_time', 
                    'end_time', 'total_messages', 'duration_minutes', 'saved_at'
                ])
                
        except Exception as e:
            st.error(f"Error loading conversation threads: {str(e)}")
            return pd.DataFrame()
    
    def calculate_conversation_duration(self, start_time: str, end_time: str) -> float:
        """Calculate conversation duration in minutes"""
        try:
            start = pd.to_datetime(start_time)
            end = pd.to_datetime(end_time)
            duration = (end - start).total_seconds() / 60
            return round(duration, 1)
        except:
            return 0.0
    
    def get_complete_conversation(self, session_id: str) -> dict:
        """Get complete conversation thread by session ID"""
        try:
            data = self._load_gist_data()
            threads = data.get("conversation_threads", [])
            
            for thread in threads:
                if thread['session_id'] == session_id:
                    return thread
            
            return None
            
        except Exception as e:
            st.error(f"Error loading conversation: {str(e)}")
            return None
    
    def save_conversation_thread(self, session_id: str, user_name: str, user_email: str, conversation_messages: list) -> bool:
        """Save complete conversation thread"""
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
    
    def save_resume(self, filename: str, content: str, file_type: str, metadata: dict) -> bool:
        """Save resume content"""
        try:
            data = self._load_gist_data()
            
            resume_data = {
                "filename": filename,
                "content": content,
                "file_type": file_type,
                "metadata": metadata,
                "uploaded_at": datetime.now().isoformat()
            }
            
            data["resume_content"] = resume_data
            data["last_updated"] = datetime.now().isoformat()
            
            return self._save_gist_data(data)
            
        except Exception as e:
            st.error(f"Error saving resume: {str(e)}")
            return False
    
    def get_resume(self) -> Optional[Dict]:
        """Get current resume"""
        try:
            data = self._load_gist_data()
            return data.get("resume_content")
            
        except Exception as e:
            st.error(f"Error loading resume: {str(e)}")
            return None
    
    def delete_resume(self) -> bool:
        """Delete current resume"""
        try:
            data = self._load_gist_data()
            data["resume_content"] = None
            data["last_updated"] = datetime.now().isoformat()
            
            return self._save_gist_data(data)
            
        except Exception as e:
            st.error(f"Error deleting resume: {str(e)}")
            return False
    
    def save_avatar(self, avatar_base64: str) -> bool:
        """Save avatar data"""
        try:
            data = self._load_gist_data()
            
            avatar_data = {
                "avatar_base64": avatar_base64,
                "uploaded_at": datetime.now().isoformat()
            }
            
            data["avatar_data"] = avatar_data
            data["last_updated"] = datetime.now().isoformat()
            
            return self._save_gist_data(data)
            
        except Exception as e:
            st.error(f"Error saving avatar: {str(e)}")
            return False
    
    def get_avatar(self) -> Optional[str]:
        """Get current avatar"""
        try:
            data = self._load_gist_data()
            avatar_data = data.get("avatar_data")
            
            if avatar_data:
                return avatar_data.get("avatar_base64")
            return None
            
        except Exception as e:
            st.error(f"Error loading avatar: {str(e)}")
            return None
    
    def delete_avatar(self) -> bool:
        """Delete current avatar"""
        try:
            data = self._load_gist_data()
            data["avatar_data"] = None
            data["last_updated"] = datetime.now().isoformat()
            
            return self._save_gist_data(data)
            
        except Exception as e:
            st.error(f"Error deleting avatar: {str(e)}")
            return False
    
    def get_database_status(self) -> Dict:
        """Get database connection status"""
        status = {
            "database_type": "GitHub Gist" if self.use_gist else "Local Session",
            "connected": self.use_gist,
            "gist_configured": bool(self.github_token and self.gist_id)
        }
        
        if self.use_gist:
            try:
                response = requests.get(f"https://api.github.com/gists/{self.gist_id}", headers=self.headers)
                status["connection_test"] = response.status_code == 200
                status["last_updated"] = self._load_gist_data().get("last_updated", "Never")
            except:
                status["connection_test"] = False
        
        return status
    
    def export_all_data(self) -> Dict:
        """Export all data for backup"""
        data = self._load_gist_data()
        data["export_timestamp"] = datetime.now().isoformat()
        return data
    
    def clear_all_data(self) -> bool:
        """Clear all data (danger zone)"""
        try:
            default_data = self._get_default_data()
            return self._save_gist_data(default_data)
        except Exception as e:
            st.error(f"Error clearing data: {str(e)}")
            return False

# Initialize shared database
@st.cache_resource
def get_shared_db():
    """Get shared database instance"""
    return GitHubGistDatabase()

# Updated storage functions
def save_user_info_shared(name: str, email: str, session_id: str) -> bool:
    """Save user info to shared database"""
    db = get_shared_db()
    return db.save_user_interaction(name, email, session_id)

def load_user_data_shared() -> pd.DataFrame:
    """Load user data from shared database"""
    db = get_shared_db()
    return db.get_user_interactions()

def load_conversation_data_shared() -> pd.DataFrame:
    """Load conversation data from shared database"""
    db = get_shared_db()
    return db.get_conversations()

def load_conversation_threads_shared() -> pd.DataFrame:
    """Load conversation threads from shared database"""
    db = get_shared_db()
    return db.get_conversation_threads()

def get_complete_conversation_shared(session_id: str) -> dict:
    """Get complete conversation thread"""
    db = get_shared_db()
    return db.get_complete_conversation(session_id)

def save_conversation_thread_shared(session_id: str, user_name: str, user_email: str, messages: list) -> bool:
    """Save complete conversation thread"""
    db = get_shared_db()
    return db.save_conversation_thread(session_id, user_name, user_email, messages)

def analyze_intent_patterns(df: pd.DataFrame) -> Dict:
    """Analyze intent patterns from conversation data"""
    if df.empty:
        return {}
    
    intent_counts = df['detected_intent'].value_counts().to_dict()
    
    # Calculate response efficiency
    avg_response_length = df.groupby('detected_intent')['response_length'].mean().to_dict()
    
    # Find most common questions
    common_questions = df['user_message'].value_counts().head(10).to_dict()
    
    return {
        'intent_distribution': intent_counts,
        'avg_response_length': avg_response_length,
        'common_questions': common_questions,
        'total_conversations': len(df)
    }

def save_avatar_shared(avatar_base64: str) -> bool:
    """Save avatar to shared database"""
    db = get_shared_db()
    return db.save_avatar(avatar_base64)

def load_avatar_shared() -> Optional[str]:
    """Load avatar from shared database"""
    db = get_shared_db()
    return db.get_avatar()

def delete_avatar_shared() -> bool:
    """Delete avatar from shared database"""
    db = get_shared_db()
    return db.delete_avatar()

def save_resume_shared(filename: str, content: str, file_type: str, metadata: dict) -> bool:
    """Save resume to shared database"""
    db = get_shared_db()
    return db.save_resume(filename, content, file_type, metadata)

def load_resume_shared() -> Optional[Dict]:
    """Load resume from shared database"""
    db = get_shared_db()
    return db.get_resume()

def delete_resume_shared() -> bool:
    """Delete resume from shared database"""
    db = get_shared_db()
    return db.delete_resume()

def export_user_data_shared():
    """Export user data from shared database"""
    db = get_shared_db()
    df = db.get_user_interactions()
    if not df.empty:
        return df.to_csv(index=False)
    return None

def show_database_status():
    """Show database connection status"""
    db = get_shared_db()
    status = db.get_database_status()
    
    if status["connected"]:
        st.success(f"✅ Connected to {status['database_type']}")
        st.info(f"Last updated: {status.get('last_updated', 'Unknown')}")
    else:
        st.warning(f"⚠️ Using {status['database_type']} (limited functionality)")
        st.info("Configure GitHub Gist for full app synchronization")
    
    return status

# Original classes with minimal changes
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

class AniketChatbotAI:
    """Professional assistant for Aniket Shirsat's portfolio"""
    
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

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

def calculate_conversation_duration(start_time: str, end_time: str) -> float:
    """Calculate conversation duration in minutes"""
    try:
        start = pd.to_datetime(start_time)
        end = pd.to_datetime(end_time)
        duration = (end - start).total_seconds() / 60
        return round(duration, 1)
    except:
        return 0.0

def delete_conversation(session_id: str, timestamp) -> bool:
    """Delete a specific conversation from the database"""
    try:
        db = get_shared_db()
        data = db._load_gist_data()
        
        # Find and remove the conversation
        conversations = data.get("conversations", [])
        timestamp_str = timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)
        
        # Filter out the conversation to delete
        updated_conversations = [
            conv for conv in conversations 
            if not (conv.get('session_id') == session_id and conv.get('timestamp') == timestamp_str)
        ]
        
        if len(updated_conversations) < len(conversations):
            data["conversations"] = updated_conversations
            data["last_updated"] = datetime.now().isoformat()
            return db._save_gist_data(data)
        else:
            return False
            
    except Exception as e:
        st.error(f"Error deleting conversation: {str(e)}")
        return False

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
            
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            title = soup.find('title')
            title_text = title.get_text().strip() if title else url
            
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
            
            if not content:
                body = soup.find('body')
                if body:
                    content = body.get_text()
            
            content = self.clean_text(content)
            
            metadata = {
                'word_count': len(content.split()),
                'scraped_at': datetime.now().isoformat(),
            }
            
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

def display_complete_conversation(conversation_thread: dict):
    """Display a complete conversation thread in chat format"""
    st.markdown(f"""
    ### 💬 Complete Conversation
    **User:** {conversation_thread['user_name']} ({conversation_thread['user_email']})  
    **Session:** {conversation_thread['session_id']}  
    **Duration:** {calculate_conversation_duration(conversation_thread['start_time'], conversation_thread['end_time'])} minutes  
    **Total Messages:** {conversation_thread['total_messages']}
    """)
    
    st.markdown("---")
    
    # Display conversation flow
    messages = conversation_thread['conversation_flow']
    
    for i, message in enumerate(messages):
        timestamp = pd.to_datetime(message['timestamp']).strftime('%H:%M:%S')
        
        if message['role'] == 'user':
            # User message
            st.markdown(f"""
            <div style="
                display: flex; 
                justify-content: flex-end; 
                margin: 10px 0;
            ">
                <div style="
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 12px 16px;
                    border-radius: 18px 18px 4px 18px;
                    max-width: 70%;
                    margin-left: 30%;
                ">
                    <div style="font-size: 12px; opacity: 0.8; margin-bottom: 4px;">
                        {conversation_thread['user_name']} • {timestamp}
                    </div>
                    {message['content']}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        else:
            # Bot message
            intent_badge = ""
            if 'intent' in message:
                intent_colors = {
                    'hiring': '#e74c3c', 'skills': '#3498db', 'projects': '#f39c12',
                    'education': '#2ecc71', 'personal': '#9b59b6', 'contact': '#e67e22',
                    'general': '#95a5a6'
                }
                color = intent_colors.get(message['intent'], '#95a5a6')
                intent_badge = f"""
                <span style="
                    background: {color}; 
                    color: white; 
                    padding: 2px 6px; 
                    border-radius: 8px; 
                    font-size: 10px;
                    margin-left: 8px;
                ">
                    {message['intent'].upper()}
                </span>
                """
            
            st.markdown(f"""
            <div style="
                display: flex; 
                align-items: flex-start; 
                margin: 10px 0;
            ">
                <div style="
                    width: 35px; 
                    height: 35px; 
                    background: #667eea; 
                    border-radius: 50%; 
                    display: flex; 
                    align-items: center; 
                    justify-content: center; 
                    color: white; 
                    font-size: 18px;
                    margin-right: 10px;
                ">🤖</div>
                <div style="
                    background: #f1f3f5;
                    padding: 12px 16px;
                    border-radius: 18px 18px 18px 4px;
                    max-width: 70%;
                ">
                    <div style="font-size: 12px; color: #666; margin-bottom: 4px;">
                        Aniket's AI Assistant • {timestamp} {intent_badge}
                    </div>
                    {message['content']}
                </div>
            </div>
            """, unsafe_allow_html=True)

def conversation_search_and_filter():
    """Simple conversation list with delete functionality - NO FILTERS"""
    st.subheader("💬 All Conversations")
    
    conversation_data = load_conversation_data_shared()
    
    if conversation_data.empty:
        st.info("No conversation data available.")
        return
    
    # Convert timestamp and handle any errors
    conversation_data['timestamp'] = pd.to_datetime(conversation_data['timestamp'], errors='coerce')
    conversation_data = conversation_data.dropna(subset=['timestamp'])
    
    if conversation_data.empty:
        st.warning("No valid conversation data found.")
        return
    
    # Simple search box only
    search_term = st.text_input("🔍 Search in conversations", placeholder="Enter keywords to search...", key="conversation_search")
    
    # Apply search filter if provided
    if search_term:
        search_mask = (
            conversation_data['user_message'].str.contains(search_term, case=False, na=False) |
            conversation_data['bot_response'].str.contains(search_term, case=False, na=False) |
            conversation_data['user_name'].str.contains(search_term, case=False, na=False)
        )
        filtered_data = conversation_data[search_mask]
        st.write(f"**Found {len(filtered_data)} conversations matching '{search_term}'**")
    else:
        filtered_data = conversation_data
        st.write(f"**Showing all {len(filtered_data)} conversations**")
    
    if not filtered_data.empty:
        # Export button
        col1, col2 = st.columns([3, 1])
        with col2:
            csv_data = filtered_data.to_csv(index=False)
            st.download_button(
                label="📥 Export All",
                data=csv_data,
                file_name=f"conversations_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                key="export_conversations"
            )
        
        # Sort by most recent first
        sorted_data = filtered_data.sort_values('timestamp', ascending=False)
        
        # Display conversations with delete option
        for idx, (_, conv) in enumerate(sorted_data.iterrows()):
            intent_colors = {
                'hiring': '#e74c3c', 'skills': '#3498db', 'projects': '#f39c12',
                'education': '#2ecc71', 'personal': '#9b59b6', 'contact': '#e67e22',
                'general': '#95a5a6'
            }
            intent_color = intent_colors.get(conv['detected_intent'], '#95a5a6')
            
            # Create unique key for each conversation
            conv_key = f"conv_{conv['session_id']}_{idx}"
            
            with st.expander(
                f"🕐 {conv['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} - {conv['user_name']} ({conv['detected_intent']})",
                expanded=False
            ):
                # Conversation content
                st.markdown(f"""
                <div style="border-left: 4px solid {intent_color}; padding: 15px; background: #f8f9fa; border-radius: 0 8px 8px 0;">
                    <div style="margin-bottom: 10px;">
                        <strong>👤 User:</strong> {conv['user_name']} ({conv['user_email']})
                    </div>
                    <div style="margin-bottom: 10px;">
                        <strong>📝 Question:</strong><br>
                        {conv['user_message']}
                    </div>
                    <div style="margin-bottom: 10px;">
                        <strong>🤖 Response:</strong><br>
                        {conv['bot_response']}
                    </div>
                    <div style="font-size: 12px; color: #666;">
                        <strong>Session:</strong> {conv['session_id']} | 
                        <strong>Intent:</strong> {conv['detected_intent']} | 
                        <strong>Response Length:</strong> {conv['response_length']} chars
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Delete button for this conversation
                col1, col2 = st.columns([4, 1])
                with col2:
                    if st.button(f"🗑️ Delete", key=f"delete_{conv_key}", type="secondary"):
                        if delete_conversation(conv['session_id'], conv['timestamp']):
                            st.success("Conversation deleted!")
                            st.rerun()
                        else:
                            st.error("Failed to delete conversation")
    else:
        st.info("No conversations found matching your search.")

def conversation_export_options():
    """Enhanced export options for conversation data"""
    st.subheader("📥 Advanced Export Options")
    
    conversation_data = load_conversation_data_shared()
    
    if conversation_data.empty:
        st.info("No conversation data to export.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📊 Standard Exports**")
        
        # Full conversation export
        conv_csv = conversation_data.to_csv(index=False)
        st.download_button(
            label="📥 Complete Conversations (CSV)",
            data=conv_csv,
            file_name=f"conversations_complete_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            key="export_complete_csv"
        )
        
        # JSON export for backup
        conv_json = conversation_data.to_json(orient='records', date_format='iso')
        st.download_button(
            label="📥 Complete Conversations (JSON)",
            data=conv_json,
            file_name=f"conversations_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json",
            key="export_complete_json"
        )
    
    with col2:
        st.markdown("**📈 Analytics Exports**")
        
        # Intent summary
        intent_summary = conversation_data.groupby('detected_intent').agg({
            'user_message': 'count',
            'response_length': 'mean',
            'message_length': 'mean'
        }).round(2)
        intent_summary.columns = ['Total_Questions', 'Avg_Response_Length', 'Avg_Question_Length']
        
        intent_csv = intent_summary.to_csv()
        st.download_button(
            label="📊 Intent Analytics (CSV)",
            data=intent_csv,
            file_name=f"intent_analytics_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            key="export_intent_analytics"
        )
        
        # User engagement summary
        user_summary = conversation_data.groupby('user_email').agg({
            'user_message': 'count',
            'session_id': 'nunique',
            'detected_intent': lambda x: len(x.unique()),
            'timestamp': ['min', 'max']
        }).round(2)
        
        user_csv = user_summary.to_csv()
        st.download_button(
            label="👥 User Engagement (CSV)",
            data=user_csv,
            file_name=f"user_engagement_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            key="export_user_engagement"
        )

def conversation_threads_tab():
    """Complete conversation threads management tab - NO FILTERS"""
    st.header("💬 Complete Conversation Threads")
    
    # Load conversation threads
    threads_df = load_conversation_threads_shared()
    
    if threads_df.empty:
        st.info("📝 No complete conversation threads saved yet.")
        st.markdown("""
        **How conversation threads work:**
        1. Each user session creates a conversation thread
        2. All messages in that session are saved together
        3. You can view the complete conversation flow
        4. Threads are automatically saved when sessions end
        """)
        return
    
    # Convert timestamps for display
    threads_df['start_time'] = pd.to_datetime(threads_df['start_time'])
    threads_df['end_time'] = pd.to_datetime(threads_df['end_time'])
    
    # Summary statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_threads = len(threads_df)
        st.metric("Total Conversations", total_threads)
    
    with col2:
        avg_messages = threads_df['total_messages'].mean()
        st.metric("Avg Messages/Conversation", f"{avg_messages:.1f}")
    
    with col3:
        avg_duration = threads_df['duration_minutes'].mean()
        st.metric("Avg Duration", f"{avg_duration:.1f}m")
    
    with col4:
        total_messages = threads_df['total_messages'].sum()
        st.metric("Total Messages", total_messages)
    
    st.write(f"**Showing all {len(threads_df)} conversations**")
    
    # Conversation list
    if not threads_df.empty:
        # Sort by most recent first
        filtered_df = threads_df.sort_values('start_time', ascending=False)
        
        for _, thread in filtered_df.iterrows():
            with st.expander(
                f"💬 {thread['user_name']} • {thread['start_time'].strftime('%Y-%m-%d %H:%M')} • "
                f"{thread['total_messages']} messages • {thread['duration_minutes']}m"
            ):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**User:** {thread['user_name']} ({thread['user_email']})")
                    st.write(f"**Session ID:** {thread['session_id']}")
                    st.write(f"**Duration:** {thread['duration_minutes']} minutes")
                
                with col2:
                    if st.button(f"👁️ View Full Conversation", key=f"view_{thread['session_id']}"):
                        st.session_state.selected_conversation = thread['session_id']
                
                # Show conversation preview (first and last message)
                conversation = get_complete_conversation_shared(thread['session_id'])
                if conversation and conversation['conversation_flow']:
                    messages = conversation['conversation_flow']
                    
                    st.markdown("**Conversation Preview:**")
                    
                    # First message
                    first_msg = messages[0]
                    if first_msg['role'] == 'user':
                        st.markdown(f"👤 **First:** {first_msg['content'][:100]}{'...' if len(first_msg['content']) > 100 else ''}")
                    
                    # Last message
                    if len(messages) > 1:
                        last_msg = messages[-1]
                        if last_msg['role'] == 'assistant':
                            st.markdown(f"🤖 **Last:** {last_msg['content'][:100]}{'...' if len(last_msg['content']) > 100 else ''}")
    
    # Display selected conversation
    if hasattr(st.session_state, 'selected_conversation'):
        st.markdown("---")
        conversation = get_complete_conversation_shared(st.session_state.selected_conversation)
        if conversation:
            display_complete_conversation(conversation)
            
            if st.button("❌ Close Conversation View", key="close_thread_conversation"):
                del st.session_state.selected_conversation
                st.rerun()

def export_conversation_threads():
    """Export complete conversation threads"""
    st.subheader("📥 Export Complete Conversations")
    
    db = get_shared_db()
    data = db._load_gist_data()
    threads = data.get("conversation_threads", [])
    
    if not threads:
        st.info("No conversation threads to export.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Export all threads as JSON
        threads_json = json.dumps(threads, indent=2, default=str)
        st.download_button(
            label="📥 Export All Conversations (JSON)",
            data=threads_json,
            file_name=f"complete_conversations_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json",
            help="Download all conversation threads with complete message history",
            key="export_threads_json"
        )
    
    with col2:
        # Export summary as CSV
        threads_df = load_conversation_threads_shared()
        if not threads_df.empty:
            summary_csv = threads_df.to_csv(index=False)
            st.download_button(
                label="📊 Export Summary (CSV)",
                data=summary_csv,
                file_name=f"conversation_summary_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                help="Download conversation summary statistics",
                key="export_threads_csv"
            )

def enhanced_analytics_tab_v2():
    """Enhanced analytics with simplified features - NO FILTERS"""
    st.header("📊 Enhanced Conversation Analytics")
    
    # Tabs within analytics - REMOVED LIVE MONITOR
    subtab1, subtab2, subtab3 = st.tabs([
        "📈 Analytics", 
        "🔍 Conversations", 
        "📥 Export Options"
    ])
    
    with subtab1:
        # Simple analytics without complex filtering
        conversation_data = load_conversation_data_shared()
        
        if conversation_data.empty:
            st.info("No conversation data available yet.")
            return
        
        # Convert timestamp
        conversation_data['timestamp'] = pd.to_datetime(conversation_data['timestamp'], errors='coerce')
        
        # Add derived columns for analysis
        conversation_data['hour'] = conversation_data['timestamp'].dt.hour
        conversation_data['day_of_week'] = conversation_data['timestamp'].dt.day_name()
        conversation_data['date'] = conversation_data['timestamp'].dt.date
        
        # Basic metrics
        st.subheader("📊 Basic Analytics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_sessions = conversation_data['session_id'].nunique()
            st.metric("Unique Sessions", total_sessions)
        
        with col2:
            avg_messages_per_session = conversation_data.groupby('session_id').size().mean()
            st.metric("Avg Messages/Session", f"{avg_messages_per_session:.1f}")
        
        with col3:
            avg_response_length = conversation_data['response_length'].mean()
            st.metric("Avg Response Length", f"{avg_response_length:.0f} chars")
        
        with col4:
            total_unique_users = conversation_data['user_email'].nunique()
            st.metric("Unique Users", total_unique_users)
        
        # Time-based analysis
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🕐 Activity by Hour")
            hourly_activity = conversation_data['hour'].value_counts().sort_index()
            st.bar_chart(hourly_activity)
        
        with col2:
            st.subheader("📅 Activity by Day")
            daily_activity = conversation_data['day_of_week'].value_counts()
            st.bar_chart(daily_activity)
        
        # Intent distribution
        st.subheader("🎯 Intent Distribution")
        intent_counts = conversation_data['detected_intent'].value_counts()
        st.bar_chart(intent_counts)
    
    with subtab2:
        conversation_search_and_filter()
    
    with subtab3:
        conversation_export_options()

def process_resume_file(uploaded_file):
    """Process uploaded resume file"""
    with st.spinner("Processing resume..."):
        processor = ResumeProcessor()
        resume_content = processor.process_resume(uploaded_file)
        
        if resume_content:
            # Save to shared database
            success = save_resume_shared(
                resume_content.filename,
                resume_content.content,
                resume_content.file_type,
                resume_content.metadata
            )
            
            if success:
                st.success("✅ Resume saved and synced to chat widget!")
            else:
                st.error("❌ Failed to save resume")
                return
            
            # Show processing results
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
            
            st.success("🎉 Resume is now active in the chat widget!")
            
        else:
            st.error("Failed to process the resume. Please check the file format and try again.")

def scrape_website(url: str, max_pages: int):
    """Update knowledge base with website content"""
    with st.spinner("Updating knowledge base..."):
        scraper = SimpleWebsiteScraper()
        content = scraper.scrape_website(url, max_pages)
        
        if content:
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
            
            # Note: Website content would need additional integration with the knowledge base
            # This is mainly for content analysis
            
        else:
            st.error("Could not retrieve content. Please verify the URL and try again.")

def main():
    """Admin Dashboard - Simplified interface focused on conversations"""
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
            correct_password = os.getenv("ADMIN_PASSWORD") or st.secrets.get("ADMIN_PASSWORD", "admin123")
            
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
        
        # Show database status in sidebar
        st.markdown("### 🔗 Database Status")
        show_database_status()
        
    # Main admin interface - REMOVED LIVE MONITORING TAB
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Analytics Dashboard", 
        "📄 Resume Management", 
        "🖼️ Avatar Management", 
        "🌐 Website Scraping", 
        "⚙️ System Settings",
        "💬 Complete Conversations"
    ])
    
    # Tab 1: Simplified Analytics Dashboard
    with tab1:
        enhanced_analytics_tab_v2()
            
    # Tab 2: Resume Management
    with tab2:
        st.header("📄 Resume Management")
        
        # Current resume status
        resume_data = load_resume_shared()
        
        if resume_data:
            st.success("✅ Resume Currently Loaded")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Filename", resume_data['filename'])
            with col2:
                st.metric("Word Count", resume_data['metadata']['word_count'])
            with col3:
                st.metric("File Size", f"{resume_data['metadata']['file_size'] / 1024:.1f} KB")
            with col4:
                upload_date = datetime.fromisoformat(resume_data['uploaded_at']).strftime("%m/%d/%Y")
                st.metric("Upload Date", upload_date)
            
            # Preview content
            st.subheader("📄 Content Preview")
            preview_text = resume_data['content'][:1000] + "..." if len(resume_data['content']) > 1000 else resume_data['content']
            st.text_area("Resume Content (First 1000 characters)", preview_text, height=200, disabled=True)
            
            # Management actions
            st.subheader("🔧 Management Actions")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Remove Current Resume", type="secondary"):
                    if delete_resume_shared():
                        st.success("Resume removed successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to remove resume")
            
            with col2:
                st.markdown("**Resume is now active in chat widget!**")
                st.info("✅ Chat widget will use this resume for answering questions")
        
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
        
        saved_avatar = load_avatar_shared()
        
        if saved_avatar:
            st.success("✅ Custom Avatar Currently Active")
            
            col1, col2 = st.columns([1, 3])
            with col1:
                st.markdown(f'<img src="{saved_avatar}" style="width: 100px; height: 100px; border-radius: 50%; object-fit: cover; border: 3px solid #2c3e50;">', unsafe_allow_html=True)
            
            with col2:
                st.markdown("**Current Avatar Details:**")
                st.write("- Format: Base64 PNG")
                st.write("- Size: 100x100 pixels")
                st.write("- Status: Active in both chat widget and admin")
                st.success("✅ Avatar is synced between both applications!")
                
                if st.button("🗑️ Remove Current Avatar", type="secondary"):
                    if delete_avatar_shared():
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
                        if save_avatar_shared(preview_avatar):
                            st.success("✅ Avatar saved and synced to chat widget!")
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
        
        # Database Connection Status
        st.subheader("🔗 Database Connection Status")
        status = show_database_status()
        
        if status["connected"]:
            st.success("🎉 Apps are successfully connected and syncing data!")
            
            # Test data sync
            st.subheader("🧪 Test Data Synchronization")
            if st.button("🔄 Test Sync"):
                # Test by reading current data
                avatar_test = load_avatar_shared()
                resume_test = load_resume_shared()
                user_test = load_user_data_shared()
                
                st.write("**Sync Test Results:**")
                st.write(f"✅ Avatar: {'Found' if avatar_test else 'Not found'}")
                st.write(f"✅ Resume: {'Found' if resume_test else 'Not found'}")
                st.write(f"✅ User data: {len(user_test)} records")
                st.success("All data is accessible from shared database!")
        
        else:
            st.error("❌ Apps are not connected! Data changes won't sync.")
            st.markdown("""
            **To connect your apps:**
            1. Create a GitHub Gist at [gist.github.com](https://gist.github.com)
            2. Create a GitHub token with 'gist' permissions
            3. Add both to secrets in BOTH apps:
            ```
            GITHUB_TOKEN = "your-token"
            GIST_ID = "your-gist-id"
            ```
            """)
        
        # API Configuration
        st.subheader("🔑 API Configuration")
        
        openai_api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
        if openai_api_key:
            masked_key = openai_api_key[:7] + "..." + openai_api_key[-4:]
            st.success(f"✅ OpenAI API Key configured: {masked_key}")
        else:
            st.error("❌ OpenAI API Key not found in environment variables")
        
        # App URLs
        st.subheader("🚀 Deployment Information")
        
        st.info("""
        **Your App URLs:**
        - **Chat Widget**: Use for embedding in your portfolio website
        - **Admin Dashboard**: Keep private for management
        
        **Embedding Code:**
        ```html
        <iframe 
            src="https://your-chat-widget-url.streamlit.app/" 
            width="420" 
            height="650" 
            frameborder="0"
            style="border-radius: 20px;">
        </iframe>
        ```
        """)
        
        # Data management
        st.subheader("📊 Data Management")
        
        # Export all data
        if st.button("📥 Export All Data"):
            db = get_shared_db()
            all_data = db.export_all_data()
            
            json_data = json.dumps(all_data, indent=2, default=str)
            st.download_button(
                label="📥 Download Complete Database Export",
                data=json_data,
                file_name=f"chatbot_database_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                help="Download complete database backup"
            )
        
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
                    db = get_shared_db()
                    # Clear only user interactions
                    data = db._load_gist_data()
                    data["user_interactions"] = []
                    if db._save_gist_data(data):
                        st.success("All user data cleared successfully!")
                    else:
                        st.error("Failed to clear user data")
        
        with col2:
            if st.button("💥 Reset All Data", type="secondary"):
                if st.checkbox("I confirm I want to reset everything"):
                    db = get_shared_db()
                    if db.clear_all_data():
                        st.success("All data reset successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to reset data")

    # Tab 6: Complete Conversations
    with tab6:
        conversation_threads_tab()
        st.markdown("---")
        export_conversation_threads()

if __name__ == "__main__":
    main()
