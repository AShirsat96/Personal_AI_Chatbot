import os
import streamlit as st
from datetime import datetime
import pandas as pd

# Environment setup
from dotenv import load_dotenv
load_dotenv()

def main():
    """Admin Dashboard - Debug Version"""
    st.set_page_config(
        page_title="Aniket Shirsat - Admin Dashboard",
        page_icon="⚙️",
        layout="wide"
    )
    
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
    .status-card {
        background: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border-left: 4px solid #2c3e50;
        margin: 10px 0;
    }
    .error-card {
        background: #fff5f5;
        border: 2px solid #feb2b2;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .success-card {
        background: #f0fff4;
        border: 2px solid #9ae6b4;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Admin header
    st.markdown("""
    <div class="admin-header">
        <h1>⚙️ Aniket Shirsat Portfolio - Admin Dashboard</h1>
        <p style="margin: 0; opacity: 0.9;">Management & Analytics Interface (Debug Mode)</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check environment variables
    st.header("🔍 System Status Check")
    
    openai_api_key = os.getenv("OPENAI_API_KEY")
    admin_password = os.getenv("ADMIN_PASSWORD")
    
    # API Key Status
    if openai_api_key:
        masked_key = openai_api_key[:7] + "..." + openai_api_key[-4:]
        st.markdown(f"""
        <div class="success-card">
            <h3>✅ OpenAI API Key</h3>
            <p>Status: <strong>Configured</strong></p>
            <p>Key: <code>{masked_key}</code></p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="error-card">
            <h3>❌ OpenAI API Key Missing</h3>
            <p>The OpenAI API key is not configured.</p>
            <p><strong>To fix:</strong></p>
            <ol>
                <li>Click "Manage app" (bottom right)</li>
                <li>Go to Settings → Secrets</li>
                <li>Add: <code>OPENAI_API_KEY = "your-key-here"</code></li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
    
    # Admin Password Status
    if admin_password:
        st.markdown("""
        <div class="success-card">
            <h3>✅ Admin Password</h3>
            <p>Status: <strong>Configured</strong></p>
            <p>Ready for authentication</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="status-card">
            <h3>⚠️ Admin Password</h3>
            <p>Using default password: <code>admin123</code></p>
            <p>Recommend setting custom password in secrets:</p>
            <p><code>ADMIN_PASSWORD = "your-secure-password"</code></p>
        </div>
        """, unsafe_allow_html=True)
    
    # Authentication Section
    st.header("🔐 Authentication")
    
    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False
    
    if not st.session_state.admin_authenticated:
        st.markdown("""
        <div class="status-card">
            <h3>🔑 Login Required</h3>
            <p>Enter the admin password to access the dashboard.</p>
        </div>
        """, unsafe_allow_html=True)
        
        admin_password_input = st.text_input("Enter Admin Password:", type="password")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔓 Login", type="primary"):
                correct_password = admin_password if admin_password else "admin123"
                
                if admin_password_input == correct_password:
                    st.session_state.admin_authenticated = True
                    st.success("✅ Authentication successful!")
                    st.rerun()
                else:
                    st.error("❌ Incorrect password. Please try again.")
        
        with col2:
            if st.button("🔍 Test Default Password"):
                st.info("Default password is: **admin123**")
        
        # Show configuration instructions
        st.markdown("""
        <div class="status-card">
            <h3>📋 Configuration Checklist</h3>
            <p>Make sure you have configured:</p>
            <ul>
                <li>✅ OPENAI_API_KEY in app secrets</li>
                <li>✅ ADMIN_PASSWORD in app secrets (optional, defaults to 'admin123')</li>
                <li>✅ Both chat widget and admin dashboard deployed separately</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
    else:
        # Show authenticated dashboard preview
        st.success("🎉 Successfully authenticated!")
        
        # Logout button
        if st.button("🚪 Logout"):
            st.session_state.admin_authenticated = False
            st.rerun()
        
        st.markdown("""
        <div class="success-card">
            <h3>🎛️ Admin Dashboard Features</h3>
            <p>Once fully configured, this dashboard provides:</p>
            <ul>
                <li>📊 <strong>Analytics Dashboard</strong> - Visitor tracking and metrics</li>
                <li>📄 <strong>Resume Management</strong> - Upload and manage resume content</li>
                <li>🖼️ <strong>Avatar Management</strong> - Custom avatar upload</li>
                <li>🌐 <strong>Website Scraping</strong> - Portfolio content management</li>
                <li>⚙️ <strong>System Settings</strong> - Configuration and maintenance</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        # Simple analytics preview
        st.header("📊 Analytics Preview")
        
        # Create sample data for demonstration
        sample_data = pd.DataFrame({
            'Date': pd.date_range('2024-01-01', periods=10, freq='D'),
            'Visitors': [5, 8, 12, 6, 15, 20, 18, 25, 22, 30]
        })
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Visitors", "165", "↗️ +12%")
        
        with col2:
            st.metric("Unique Visitors", "128", "↗️ +8%")
        
        with col3:
            st.metric("Return Visitors", "37", "↗️ +23%")
        
        st.line_chart(sample_data.set_index('Date'))
        
        st.info("💡 This is a preview. Real analytics will show actual visitor data once the chat widget starts collecting information.")
    
    # Footer with deployment info
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 14px; padding: 20px;">
        <p><strong>Deployment Information:</strong></p>
        <p>Admin Dashboard: personalaichatbot-lqmfb7ethymakrhablh2o.streamlit.app</p>
        <p>Chat Widget: (deploy separately for embedding)</p>
        <p>Status: Debug Mode - Configure secrets to enable full functionality</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
