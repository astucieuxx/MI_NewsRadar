import streamlit as st
import pandas as pd
import datetime
from pathlib import Path
import glob
import json
import subprocess
import sys
import time
import re
import html
import os

# Page config - ensure sidebar is always visible
st.set_page_config(
    page_title="News Radar Dashboard",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Force sidebar to always be visible using Streamlit's built-in method
if 'sidebar_state' not in st.session_state:
    st.session_state.sidebar_state = 'expanded'


# Custom CSS for Zendesk look and feel
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .stApp {
        background: #ffffff;
    }
    
    .main > div {
        background: #ffffff;
    }
    
    .main-container {
        display: none;
    }
    
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1a1a1a;
        margin-bottom: 0.5rem;
        letter-spacing: -0.02em;
    }
    
    .sub-header {
        font-size: 1rem;
        color: #666666;
        margin-bottom: 0.5rem;
        font-weight: 400;
    }
    
    .info-text {
        font-size: 0.875rem;
        color: #9ca3af;
        margin-bottom: 1.5rem;
        font-weight: 400;
        font-style: italic;
    }
    
    .engagement-high {
        background: #D1F46E;
        color: #1a1a1a;
        padding: 0.35rem 0.85rem;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
    }
    
    .engagement-medium {
        background: #1a5d3f;
        color: white;
        padding: 0.35rem 0.85rem;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
    }
    
    .engagement-low {
        background: #9ca3af;
        color: white;
        padding: 0.35rem 0.85rem;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
    }
    
    .news-card {
        background: #ffffff;
        padding: 1.5rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        border: 1px solid #e5e7eb;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        position: relative;
    }
    
    .news-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
        background: #D1F46E;
        border-radius: 8px 0 0 8px;
    }
    
    .news-title {
        font-size: 1.25rem;
        font-weight: 600;
        color: #1a1a1a;
        margin-bottom: 0.75rem;
        line-height: 1.4;
    }
    
    .news-hook {
        font-size: 1rem;
        font-weight: 500;
        color: #1a1a1a;
        font-style: italic;
        margin: 0.75rem 0;
        padding: 0.75rem 1rem;
        background-color: #f9fafb;
        border-radius: 6px;
        border-left: 3px solid #D1F46E;
    }
    
    .news-summary {
        color: #4b5563;
        line-height: 1.6;
        margin: 1rem 0;
        font-size: 0.95rem;
    }
    
    .news-meta {
        font-size: 0.875rem;
        color: #6b7280;
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid #e5e7eb;
        display: flex;
        flex-wrap: wrap;
        gap: 1rem;
        align-items: center;
    }
    
    .news-meta a {
        color: #1a1a1a;
        text-decoration: none;
        font-weight: 600;
        padding: 0.5rem 1rem;
        background: #D1F46E;
        border-radius: 6px;
        border: 1px solid #D1F46E;
        transition: all 0.2s;
    }
    
    .news-meta a:hover {
        background: #b8d85a;
    }
    
    .slack-preview {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(0, 168, 112, 0.3);
        border-radius: 12px;
        padding: 1.25rem;
        margin-top: 0.5rem;
        margin-bottom: 0.75rem;
        font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
        font-size: 0.875rem;
        color: #e5e7eb;
        white-space: pre-wrap;
        word-wrap: break-word;
        line-height: 1.7;
        max-height: 300px;
        overflow-y: auto;
        backdrop-filter: blur(5px);
        display: none;
    }
    
    .slack-preview.show {
        display: block;
    }
    
    .slack-preview-label {
        color: #D1F46E;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.5rem;
    }
    
    .toggle-preview-button {
        background: rgba(0, 168, 112, 0.2);
        color: #D1F46E;
        border: 1px solid rgba(0, 168, 112, 0.3);
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.875rem;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        margin-right: 0.5rem;
        transition: all 0.2s;
    }
    
    .toggle-preview-button:hover {
        background: rgba(0, 168, 112, 0.3);
        border-color: #D1F46E;
    }
    
    .slack-button {
        background: #D1F46E;
        color: white;
        border: none;
        padding: 0.625rem 1.25rem;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.875rem;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        box-shadow: 0 2px 8px rgba(0, 168, 112, 0.3);
        transition: all 0.2s;
    }
    
    .slack-button:hover {
        background: #1a5d3f;
        box-shadow: 0 4px 12px rgba(0, 168, 112, 0.4);
        transform: translateY(-1px);
    }
    
    .slack-button:active {
        transform: translateY(0);
    }
    
    .copy-success {
        color: #D1F46E;
        font-size: 0.875rem;
        margin-left: 0.5rem;
        font-weight: 500;
    }
    
    .stat-box {
        background: #ffffff;
        color: #1a1a1a;
        padding: 1rem 1.25rem;
        border-radius: 8px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        border: 1px solid #e5e7eb;
    }
    
    .stat-number {
        font-size: 2rem;
        font-weight: 700;
        margin: 0.25rem 0;
        letter-spacing: -0.02em;
        line-height: 1.2;
        color: #1a1a1a;
    }
    
    .stat-label {
        font-size: 0.75rem;
        color: #6b7280;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 0.25rem;
    }
    
    .stat-box-high {
        border-left: 4px solid #D1F46E;
    }
    
    .stat-box-medium {
        border-left: 4px solid #1a5d3f;
    }
    
    .stat-box-low {
        border-left: 4px solid #9ca3af;
    }
    
    .category-badge {
        display: inline-block;
        padding: 0.35rem 0.85rem;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .category-ccaas {
        background: #9ca3af;
        color: white;
    }
    
    .category-es {
        background: #9ca3af;
        color: white;
    }
    
    /* Sidebar styling - always visible and compact */
    section[data-testid="stSidebar"],
    [data-testid="stSidebar"] {
        background: #ffffff !important;
        border-right: 1px solid #e5e7eb !important;
        visibility: visible !important;
        display: block !important;
        transform: translateX(0) !important;
        min-width: 21rem !important;
        max-height: 100vh !important;
        overflow-y: auto !important;
    }
    
    /* Sidebar content container - prevent overflow */
    [data-testid="stSidebar"] > div:first-child {
        padding: 1rem 1.5rem !important;
        max-height: calc(100vh - 2rem) !important;
        overflow-y: visible !important;
        display: flex !important;
        flex-direction: column !important;
    }
    
    /* Force sidebar to stay open */
    section[data-testid="stSidebar"][aria-expanded="false"],
    [data-testid="stSidebar"][aria-expanded="false"] {
        visibility: visible !important;
        display: block !important;
        transform: translateX(0) !important;
    }
    
    /* Hide sidebar toggle button */
    button[data-testid="baseButton-header"],
    button[kind="header"],
    [data-testid="collapsedControl"] {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* Make sidebar content more compact */
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #1a1a1a;
        font-size: 0.875rem !important;
        margin-top: 0.25rem !important;
        margin-bottom: 0.25rem !important;
        font-weight: 600 !important;
    }
    
    [data-testid="stSidebar"] p {
        color: #4b5563;
        font-size: 0.75rem !important;
        margin: 0.15rem 0 !important;
        line-height: 1.4 !important;
    }
    
    [data-testid="stSidebar"] .stMarkdown {
        margin-bottom: 0.25rem !important;
    }
    
    [data-testid="stSidebar"] .stButton {
        margin-bottom: 0.5rem !important;
    }
    
    [data-testid="stSidebar"] .stSelectbox,
    [data-testid="stSidebar"] .stCheckbox {
        margin-bottom: 0.1rem !important;
    }
    
    [data-testid="stSidebar"] .stSelectbox > label {
        font-size: 0.75rem !important;
        margin-bottom: 0.25rem !important;
    }
    
    [data-testid="stSidebar"] .stCheckbox > label {
        padding-top: 0.1rem !important;
        padding-bottom: 0.1rem !important;
        margin-bottom: 0 !important;
        font-size: 0.875rem !important;
    }
    
    [data-testid="stSidebar"] .stCheckbox > div {
        margin-bottom: 0.1rem !important;
    }
    
    [data-testid="stSidebar"] hr {
        margin: 0.5rem 0 !important;
    }
    
    /* Compact info/warning boxes in sidebar */
    [data-testid="stSidebar"] .stAlert {
        padding: 0.5rem 0.75rem !important;
        margin-bottom: 0.5rem !important;
        font-size: 0.75rem !important;
        border-radius: 6px !important;
    }
    
    [data-testid="stSidebar"] .stAlert > div {
        padding: 0 !important;
    }
    
    [data-testid="stSidebar"] .stAlert p {
        margin: 0 !important;
        font-size: 0.75rem !important;
        line-height: 1.4 !important;
    }
    
    /* Change checkbox color to Zendesk green */
    [data-testid="stSidebar"] .stCheckbox input[type="checkbox"]:checked {
        background-color: #D1F46E !important;
        border-color: #D1F46E !important;
        accent-color: #D1F46E !important;
    }
    
    [data-testid="stSidebar"] .stCheckbox input[type="checkbox"]:focus {
        border-color: #D1F46E !important;
        box-shadow: 0 0 0 2px rgba(209, 244, 110, 0.3) !important;
        outline-color: #D1F46E !important;
    }
    
    [data-testid="stSidebar"] .stCheckbox input[type="checkbox"]:hover {
        border-color: #D1F46E !important;
    }
    
    /* Alternative selector for Streamlit checkboxes */
    [data-testid="stSidebar"] input[type="checkbox"]:checked {
        background-color: #D1F46E !important;
        border-color: #D1F46E !important;
        accent-color: #D1F46E !important;
    }
    
    [data-testid="stSidebar"] input[type="checkbox"] {
        accent-color: #D1F46E !important;
    }
    
    [data-testid="stSidebar"] .css-1d391kg {
        background: #ffffff;
    }
    
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #1a1a1a;
    }
    
    [data-testid="stSidebar"] p {
        color: #4b5563;
    }
    
    /* Make selectbox more compact in sidebar */
    [data-testid="stSidebar"] .stSelectbox > div > div {
        padding: 0.4rem 0.75rem !important;
        font-size: 0.875rem !important;
        min-height: 2rem !important;
    }
    
    /* Reduce spacing in sidebar elements */
    [data-testid="stSidebar"] > div > div {
        margin-bottom: 0.5rem !important;
    }
    
    /* Compact spacing for all sidebar children */
    [data-testid="stSidebar"] * {
        box-sizing: border-box !important;
    }
    
    /* Ensure no extra padding in sidebar */
    [data-testid="stSidebar"] [class*="block-container"],
    [data-testid="stSidebar"] [class*="element-container"] {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        border-bottom: 2px solid #4b5563 !important;
        background: transparent;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 0.75rem 1.5rem;
        font-weight: 500;
        color: #6b7280;
        background: transparent;
        border-bottom: none !important;
    }
    
    .stTabs [aria-selected="true"] {
        color: #1a1a1a !important;
        background: #D1F46E !important;
        border-bottom: 2px solid #4b5563 !important;
    }
    
    /* Override any default Streamlit tab border colors */
    .stTabs [data-baseweb="tab-list"] [data-baseweb="tab"] {
        border-bottom: none !important;
    }
    
    .stTabs [data-baseweb="tab-list"] [data-baseweb="tab"][aria-selected="true"] {
        border-bottom: 2px solid #4b5563 !important;
    }
    
    /* Remove any red borders from tabs */
    .stTabs * {
        border-color: #4b5563 !important;
    }
    
    .stTabs [aria-selected="true"] * {
        border-bottom-color: #4b5563 !important;
    }
    
    /* Target pseudo-elements and children that might have red */
    .stTabs [data-baseweb="tab"][aria-selected="true"]::after,
    .stTabs [data-baseweb="tab"][aria-selected="true"]::before {
        border-color: #4b5563 !important;
        background: #4b5563 !important;
    }
    
    /* Remove any red from tab indicators */
    .stTabs [data-baseweb="tab-list"]::after,
    .stTabs [data-baseweb="tab-list"]::before {
        border-color: #4b5563 !important;
        background: #4b5563 !important;
    }
    
    /* Force remove red from any element inside tabs - very aggressive */
    .stTabs [style*="red"],
    .stTabs [style*="rgb(255"],
    .stTabs [style*="#ff"],
    .stTabs [style*="#FF"],
    .stTabs [style*="rgb(239, 68, 68)"] {
        border-color: #4b5563 !important;
        background: transparent !important;
    }
    
    /* Override Streamlit's default tab indicator color */
    .stTabs [data-baseweb="tab-list"] [data-baseweb="tab"][aria-selected="true"] > div,
    .stTabs [data-baseweb="tab-list"] [data-baseweb="tab"][aria-selected="true"] > span {
        border-bottom-color: #4b5563 !important;
    }
    
    /* Hide Streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Button styling - Zendesk green */
    .stButton > button {
        background: #D1F46E !important;
        color: #1a1a1a !important;
        border-radius: 6px !important;
        border: none !important;
        font-weight: 600 !important;
        transition: all 0.2s !important;
    }
    
    .stButton > button:hover {
        background: #b8d85a !important;
        box-shadow: 0 2px 8px rgba(209, 244, 110, 0.4) !important;
    }
    
    /* Sidebar button specifically */
    [data-testid="stSidebar"] .stButton > button {
        background: #D1F46E !important;
        color: #1a1a1a !important;
        border-radius: 6px !important;
        border: none !important;
        font-weight: 600 !important;
        width: 100% !important;
    }
    
    [data-testid="stSidebar"] .stButton > button:hover {
        background: #b8d85a !important;
        box-shadow: 0 2px 8px rgba(209, 244, 110, 0.4) !important;
    }
    
    /* Selectbox styling */
    .stSelectbox label {
        color: #374151;
        font-weight: 500;
    }
    
    .stSelectbox > div > div {
        background: #ffffff;
        color: #1a1a1a;
        border: 1px solid #e5e7eb;
        border-radius: 6px;
    }
    
    /* Checkbox styling */
    .stCheckbox label {
        color: #374151;
        font-weight: 500;
    }
    
    /* Text input styling */
    .stTextInput > div > div > input {
        background: #ffffff;
        color: #1a1a1a;
        border: 1px solid #e5e7eb;
        border-radius: 6px;
    }
    
    /* Markdown text colors */
    .stMarkdown {
        color: #4b5563;
    }
    
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #1a1a1a;
    }
    
    /* Info boxes */
    .stInfo {
        background: #f9fafb;
        border: 1px solid #D1F46E;
        border-radius: 6px;
        color: #1a1a1a;
    }
    
    .stWarning {
        background: #f9fafb;
        border: 1px solid #9ca3af;
        border-radius: 6px;
        color: #4b5563;
    }
    
    .stError {
        background: #f9fafb;
        border: 1px solid #9ca3af;
        border-radius: 6px;
        color: #4b5563;
    }
    
    /* Main content area */
    section[data-testid="stMain"] {
        background: #ffffff;
    }
    
    /* Block container */
    .block-container {
        background: #ffffff;
    }
    
    /* Streamlit expander styling - make it look integrated with cards */
    /* Target expanders that come right after news cards */
    .news-card {
        margin-bottom: 0 !important;
        border-radius: 8px 8px 0 0 !important;
    }
    
    /* Style expander to appear as part of the card */
    [data-testid="stExpander"] {
        background: #ffffff !important;
        border: 1px solid #e5e7eb !important;
        border-top: 1px solid #e5e7eb !important;
        border-radius: 0 0 8px 8px !important;
        margin-top: 0 !important;
        margin-bottom: 1rem !important;
        margin-left: 0 !important;
        margin-right: 0 !important;
    }
    
    /* Expander header - always grey, whether open or closed */
    [data-testid="stExpander"] > div:first-child {
        background: #9ca3af !important;
        background-color: #9ca3af !important;
        border: none !important;
        border-radius: 0 !important;
        color: white !important;
        font-weight: 600 !important;
        padding: 0.75rem 1.5rem !important;
        margin: 0 !important;
    }
    
    /* When expander is closed (not expanded) */
    [data-testid="stExpander"]:not([aria-expanded="true"]) > div:first-child,
    [data-testid="stExpander"][aria-expanded="false"] > div:first-child {
        background: #9ca3af !important;
        background-color: #9ca3af !important;
        color: white !important;
    }
    
    /* When expander is open (expanded) */
    [data-testid="stExpander"][aria-expanded="true"] > div:first-child {
        background: #9ca3af !important;
        background-color: #9ca3af !important;
        color: white !important;
    }
    
    /* Target Streamlit's expander button directly - all states */
    [data-testid="stExpander"] button {
        background: #9ca3af !important;
        background-color: #9ca3af !important;
        color: white !important;
        border: none !important;
    }
    
    [data-testid="stExpander"] button:hover {
        background: #6b7280 !important;
        background-color: #6b7280 !important;
    }
    
    [data-testid="stExpander"] button * {
        color: white !important;
    }
    
    /* Also target any nested divs - all states */
    [data-testid="stExpander"] > div:first-child > div,
    [data-testid="stExpander"] > div:first-child > button,
    [data-testid="stExpander"] > div:first-child > button > div {
        background: #9ca3af !important;
        background-color: #9ca3af !important;
        color: white !important;
    }
    
    /* Force grey background on the button container regardless of state */
    [data-testid="stExpander"] > div:first-child > button,
    [data-testid="stExpander"] > div:first-child > div > button {
        background: #9ca3af !important;
        background-color: #9ca3af !important;
    }
    
    /* Force all text inside expander header to be dark grey - very aggressive */
    [data-testid="stExpander"] > div:first-child *,
    [data-testid="stExpander"] > div:first-child p,
    [data-testid="stExpander"] > div:first-child span,
    [data-testid="stExpander"] > div:first-child div,
    [data-testid="stExpander"] > div:first-child > div,
    [data-testid="stExpander"] > div:first-child > div > p,
    [data-testid="stExpander"] > div:first-child > div > span,
    [data-testid="stExpander"] > div:first-child > div > div,
    [data-testid="stExpander"] button,
    [data-testid="stExpander"] button *,
    [data-testid="stExpander"] button p,
    [data-testid="stExpander"] button span,
    [data-testid="stExpander"] button div {
        color: #4b5563 !important;
    }
    
    /* Target Streamlit's specific expander button structure */
    [data-testid="stExpander"] > div:first-child button,
    [data-testid="stExpander"] > div:first-child button p,
    [data-testid="stExpander"] > div:first-child button span,
    [data-testid="stExpander"] > div:first-child button div,
    [data-testid="stExpander"] > div:first-child > button,
    [data-testid="stExpander"] > div:first-child > button * {
        color: #4b5563 !important;
    }
    
    /* Override any white color specifically */
    [data-testid="stExpander"] [style*="color: white"],
    [data-testid="stExpander"] [style*="color: #fff"],
    [data-testid="stExpander"] [style*="color: #ffffff"],
    [data-testid="stExpander"] [style*="color:rgb(255"] {
        color: #4b5563 !important;
    }
    
    [data-testid="stExpander"] > div:first-child:hover {
        background: #6b7280 !important;
    }
    
    [data-testid="stExpander"] > div:last-child {
        background: #ffffff !important;
        border: none !important;
        border-radius: 0 0 8px 8px !important;
        padding: 1rem 1.5rem !important;
        margin: 0 !important;
    }
    
    /* Style the text area inside expander */
    [data-testid="stExpander"] textarea {
        background: #f9fafb !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 6px !important;
        color: #1a1a1a !important;
        font-family: 'Monaco', 'Menlo', 'Courier New', monospace !important;
        font-size: 0.875rem !important;
    }
    
    [data-testid="stExpander"] label {
        color: #6b7280 !important;
        font-size: 0.875rem !important;
        font-weight: 500 !important;
    }
</style>
<script>
    // Function to change expander background to grey and text to white - works for both open and closed states
    function changeExpanderStyle() {
        // Find all expander headers - try multiple selectors
        const expanders1 = document.querySelectorAll('[data-testid="stExpander"] > div:first-child');
        const expanders2 = document.querySelectorAll('[data-testid="stExpander"] button');
        const expanders3 = document.querySelectorAll('.streamlit-expanderHeader');
        
        const allExpanders = [...expanders1, ...expanders2, ...expanders3];
        
        allExpanders.forEach(expander => {
            // Force background to grey - try multiple properties (works for both open and closed)
            expander.style.setProperty('background', '#9ca3af', 'important');
            expander.style.setProperty('background-color', '#9ca3af', 'important');
            expander.style.backgroundColor = '#9ca3af';
            expander.style.background = '#9ca3af';
            
            // Force text color to white
            expander.style.setProperty('color', 'white', 'important');
            expander.style.color = 'white';
            
            // Find all text elements inside and make them white
            const allElements = expander.querySelectorAll('*');
            allElements.forEach(el => {
                el.style.setProperty('color', 'white', 'important');
                el.style.color = 'white';
            });
            
            // Also check for buttons and their children - make button background grey too
            const buttons = expander.querySelectorAll('button');
            buttons.forEach(button => {
                button.style.setProperty('color', 'white', 'important');
                button.style.setProperty('background', '#9ca3af', 'important');
                button.style.setProperty('background-color', '#9ca3af', 'important');
                button.style.color = 'white';
                button.style.background = '#9ca3af';
                button.style.backgroundColor = '#9ca3af';
                const buttonChildren = button.querySelectorAll('*');
                buttonChildren.forEach(child => {
                    child.style.setProperty('color', 'white', 'important');
                    child.style.color = 'white';
                });
            });
        });
        
        // Also target the parent container - force grey even when closed
        const expanderContainers = document.querySelectorAll('[data-testid="stExpander"]');
        expanderContainers.forEach(container => {
            const firstChild = container.querySelector('div:first-child');
            if (firstChild) {
                // Force grey background regardless of expanded state
                firstChild.style.setProperty('background', '#9ca3af', 'important');
                firstChild.style.setProperty('background-color', '#9ca3af', 'important');
                firstChild.style.setProperty('color', 'white', 'important');
                firstChild.style.backgroundColor = '#9ca3af';
                firstChild.style.background = '#9ca3af';
                firstChild.style.color = 'white';
            }
        });
    }
    
    // Run immediately
    changeExpanderStyle();
    
    // Run after DOM is fully loaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', changeExpanderStyle);
    } else {
        changeExpanderStyle();
    }
    
    // Run after Streamlit renders (using MutationObserver)
    const observer = new MutationObserver(function(mutations) {
        changeExpanderStyle();
    });
    
    // Start observing
    observer.observe(document.body, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ['style', 'class']
    });
    
    // Also run on window load
    window.addEventListener('load', changeExpanderStyle);
    
    // Run periodically to catch any late-rendered elements - more frequent
    setInterval(changeExpanderStyle, 100);
    
    // Also try a more aggressive approach - find anything that looks like an expander
    function forceExpanderGrey() {
        // Find all elements that might be expander headers
        const allPossibleElements = document.querySelectorAll('div, button, span');
        allPossibleElements.forEach(el => {
            const text = el.textContent || el.innerText || '';
            if (text.includes('Create a Slack Post') || text.includes('📋')) {
                // Found it! Force grey background
                el.style.setProperty('background', '#9ca3af', 'important');
                el.style.setProperty('background-color', '#9ca3af', 'important');
                el.style.backgroundColor = '#9ca3af';
                el.style.background = '#9ca3af';
                el.style.setProperty('color', 'white', 'important');
                el.style.color = 'white';
                
                // Also check parent and siblings
                if (el.parentElement) {
                    el.parentElement.style.setProperty('background', '#9ca3af', 'important');
                    el.parentElement.style.backgroundColor = '#9ca3af';
                }
                
                // Check all children
                const children = el.querySelectorAll('*');
                children.forEach(child => {
                    child.style.setProperty('color', 'white', 'important');
                    child.style.color = 'white';
                });
            }
        });
    }
    
    // Run the aggressive function too
    forceExpanderGrey();
    setInterval(forceExpanderGrey, 100);
</script>
""", unsafe_allow_html=True)


def load_news_data(date_str=None):
    """Load news data from CSV files for a given date."""
    if date_str is None:
        date_str = datetime.date.today().isoformat()
    
    base_path = Path(".")
    ccaas_file = base_path / f"ccaas_news_{date_str}.csv"
    es_file = base_path / f"es_news_{date_str}.csv"
    
    ccaas_df = None
    es_df = None
    
    if ccaas_file.exists():
        try:
            ccaas_df = pd.read_csv(ccaas_file)
            ccaas_df['category'] = 'CCaaS'
        except Exception as e:
            st.warning(f"Error loading CCaaS data: {e}")
    
    if es_file.exists():
        try:
            es_df = pd.read_csv(es_file)
            es_df['category'] = 'ES'
        except Exception as e:
            st.warning(f"Error loading ES data: {e}")
    
    return ccaas_df, es_df


def get_available_dates():
    """Get list of available dates from CSV files."""
    base_path = Path(".")
    ccaas_files = glob.glob(str(base_path / "ccaas_news_*.csv"))
    es_files = glob.glob(str(base_path / "es_news_*.csv"))
    
    dates = set()
    for file in ccaas_files + es_files:
        try:
            # Extract date from filename: ccaas_news_YYYY-MM-DD.csv
            date_str = file.split("_")[-1].replace(".csv", "")
            datetime.datetime.strptime(date_str, "%Y-%m-%d")
            dates.add(date_str)
        except:
            continue
    
    return sorted(dates, reverse=True)


def get_total_news_count():
    """Get total count of all news articles collected historically (deduplicated by URL)."""
    base_path = Path(".")
    ccaas_files = glob.glob(str(base_path / "ccaas_news_*.csv"))
    es_files = glob.glob(str(base_path / "es_news_*.csv"))
    
    all_urls = set()
    
    for file in ccaas_files + es_files:
        try:
            df = pd.read_csv(file)
            if 'url' in df.columns:
                all_urls.update(df['url'].dropna().astype(str))
        except Exception as e:
            # Skip files that can't be read
            continue
    
    return len(all_urls)


def safe_str(value, default=''):
    """Safely convert a value to string, handling NaN, None, and float types."""
    if pd.isna(value) or value is None:
        return default
    if isinstance(value, float):
        return default
    return str(value).strip() if str(value).strip() else default


# ============================
# AI IN CS ECOSYSTEM DETECTION
# ============================

# AI CS Ecosystem vendors by layer (from Q4 2025 Ecosystem Map)
AI_CS_ECOSYSTEM_VENDORS = {
    # CS Platforms (Helpdesks/CRMs)
    'CS Platforms': ['Zendesk', 'Salesforce', 'Microsoft', 'HubSpot', 'Freshworks', 
                     'ServiceNow', 'Intercom', 'Gorgias'],
    # CC Platforms
    'CCaaS': ['Genesys', 'NICE', 'Five9', 'RingCentral', '8x8', '8x8'],
    'CPaaS': ['Twilio', 'Vonage', 'Infobip'],
    # AI Agents (Autonomous)
    'AI Agents': ['Sierra', 'Ada', 'Crescendo', 'Decagon', 'Forethought', 'PolyAI', 'ASAPP'],
    # Conversational AI Agent Builders
    'Conversational AI': ['Kore.ai', 'Yellow.ai', 'Cognigy', 'Capacity', 'Replicant', 'Parloa'],
    # Agent Assist & Workforce Intel
    'Agent Assist': ['Cresta', 'Uniphore', 'Observe.AI', 'Gong', 'Assembled', 'Calabrio'],
    # Knowledge Management Platforms
    'Knowledge Management': ['Guru', 'Document360', 'eGain', 'Confluence', 'KMS Lighthouse', 'Shelf', 'Notion'],
    # AI Infrastructure Providers
    'AI Infrastructure': ['OpenAI', 'Gemini', 'LLaMA', 'AWS', 'Microsoft Azure', 'Google Cloud', 
                          'Google Cloud Platform', 'Databricks', 'Snowflake']
}

# Strategic movement keywords
STRATEGIC_MOVEMENT_KEYWORDS = [
    'acquisition', 'acquired', 'merger', 'partnership', 'partners with', 'partnered',
    'announces', 'launches', 'releases', 'unveils', 'introduces', 'rolls out',
    'investment', 'funding', 'raises', 'strategic', 'alliance', 'strategic partnership',
    'integration', 'collaboration', 'joint venture', 'teams up', 'joins forces'
]

# AI-related keywords
AI_KEYWORDS = [
    'ai', 'artificial intelligence', 'machine learning', 'llm', 'gpt', 'chatgpt',
    'agentic', 'copilot', 'autonomous', 'generative ai', 'genai', 'neural',
    'deep learning', 'natural language', 'nlp', 'conversational ai', 'voice ai',
    'ai agent', 'ai chatbot', 'ai assistant', 'ai-powered', 'ai-driven'
]


def is_ai_cs_strategic_news(article):
    """
    Detecta si un artículo es relevante para AI en Customer Service:
    1. Menciona vendors del ecosistema AI CS
    2. Incluye keywords de movimientos estratégicos
    3. Está relacionado con AI
    """
    title = safe_str(article.get('title', ''), '')
    summary = safe_str(article.get('summary', ''), '')
    hook = safe_str(article.get('hook', ''), '')
    
    # Combine all text for analysis
    text = f"{title} {summary} {hook}".lower()
    
    # Check for ecosystem vendors (case-insensitive)
    all_vendors = [v for vendors in AI_CS_ECOSYSTEM_VENDORS.values() for v in vendors]
    mentions_vendor = any(vendor.lower() in text for vendor in all_vendors)
    
    # Check for strategic movement keywords
    has_strategic_keyword = any(keyword.lower() in text for keyword in STRATEGIC_MOVEMENT_KEYWORDS)
    
    # Check for AI keywords
    is_ai_related = any(keyword.lower() in text for keyword in AI_KEYWORDS)
    
    # Must be: (vendor OR strategic) AND AI-related
    return (mentions_vendor or has_strategic_keyword) and is_ai_related


def filter_ai_cs_news(df):
    """
    Filtra artículos relevantes para AI in CS:
    - Debe pasar la detección por keywords/vendors
    - Y tener engagement HIGH o MEDIUM (movimientos estratégicos)
    """
    if df.empty:
        return df
    
    # Si el CSV tiene la columna is_ai_cs_relevant, usarla primero
    if 'is_ai_cs_relevant' in df.columns:
        # Normalize is_ai_cs_relevant: handle string "True"/"False", boolean, or NaN
        def normalize_is_ai_cs_relevant(value):
            if pd.isna(value):
                return False
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes")
            return bool(value)
        
        # Usar la columna si existe, pero también aplicar detección como fallback
        ai_filtered = df[df.apply(lambda row: 
            normalize_is_ai_cs_relevant(row.get('is_ai_cs_relevant', False)) or is_ai_cs_strategic_news(row.to_dict()), 
            axis=1)]
    else:
        # Fallback: detección por keywords/vendors
        # Convert Series to dict for is_ai_cs_strategic_news function
        ai_filtered = df[df.apply(lambda row: is_ai_cs_strategic_news(row.to_dict()), axis=1)]
    
    # Solo HIGH y MEDIUM (movimientos estratégicos)
    return ai_filtered[ai_filtered['engagement'].isin(['HIGH', 'MEDIUM'])]


def engagement_badge(engagement):
    """Return HTML badge for engagement level."""
    engagement = str(engagement).upper()
    if engagement == "HIGH":
        return '<span class="engagement-high">HIGH</span>'
    elif engagement == "MEDIUM":
        return '<span class="engagement-medium">MEDIUM</span>'
    else:
        return '<span class="engagement-low">LOW</span>'


def render_news_card(article, card_id):
    """Render a single news article card with Slack post button."""
    engagement_html = engagement_badge(article.get('engagement', 'LOW'))
    
    title = safe_str(article.get('title', 'No title'), 'No title')
    hook = safe_str(article.get('hook', ''), '')
    summary = safe_str(article.get('summary', ''), '')
    url = safe_str(article.get('url', '#'), '#')
    source = safe_str(article.get('source', 'Unknown'), 'Unknown')
    published = article.get('published', '')
    category = safe_str(article.get('category', ''), '')
    
    # If summary is empty, provide a helpful message
    if not summary or summary.strip() == '':
        summary = f"Click 'Read Article →' to view the full article from {source}."
    
    # Format published date
    pub_display = ''
    if published and pd.notna(published) and published != '':
        try:
            if 'T' in str(published):
                dt = datetime.datetime.fromisoformat(str(published).replace('Z', '+00:00'))
                pub_display = dt.strftime('%b %d, %Y at %I:%M %p')
            else:
                pub_display = str(published)
        except:
            pub_display = str(published)
    
    # Category badge
    category_class = "category-ccaas" if category == "CCaaS" else "category-es"
    
    # Generate Slack post
    slack_post = generate_slack_post(article)
    
    # Escape HTML in title and summary for display
    title_escaped = title.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    summary_escaped = summary.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    hook_escaped = hook.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;') if hook else ''
    
    # Render card with HTML
    card_html = f"""
    <div class="news-card" id="card-{card_id}">
        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 1rem; flex-wrap: wrap; gap: 1rem;">
            <div style="flex: 1; min-width: 300px;">
                <div class="news-title">{title_escaped}</div>
            </div>
            <div style="display: flex; gap: 0.75rem; align-items: center; flex-wrap: wrap;">
                <span class="category-badge {category_class}">{category}</span>
                <div>{engagement_html}</div>
            </div>
        </div>
        {f'<div class="news-hook">"{hook_escaped}"</div>' if hook else ''}
        <div class="news-summary">{summary_escaped}</div>
        <div class="news-meta">
            <span><strong>{source}</strong></span>
            {f'<span>{pub_display}</span>' if pub_display else ''}
            <a href="{url}" target="_blank">Read Article →</a>
        </div>
    </div>
    """
    
    # Use a container to group the card and expander together
    with st.container():
        st.markdown(card_html, unsafe_allow_html=True)
        
        # Use Streamlit expander for Slack post preview - styled to look inside card
        with st.expander("📋 Create a Slack Post", expanded=False):
            st.text_area(
                "Slack Post (select all and copy):",
                value=slack_post,
                height=100,
                key=f"slack-text-{card_id}",
                label_visibility="visible"
            )


def generate_slack_post(article):
    """Generate a simple, professional Slack post for leadership team."""
    title = safe_str(article.get('title', 'No title'), 'No title')
    summary = safe_str(article.get('summary', ''), '')
    url = safe_str(article.get('url', ''), '')
    hook = safe_str(article.get('hook', ''), '')
    
    # Strip HTML tags and decode HTML entities
    def clean_text(text):
        if not text:
            return ''
        # Remove HTML tags using a simple regex
        text = re.sub(r'<[^>]+>', '', text)
        # Decode HTML entities
        text = html.unescape(text)
        return text.strip()
    
    title = clean_text(title)
    summary = clean_text(summary)
    hook = clean_text(hook)
    
    # Key Insight: Use hook if available, otherwise use title
    if hook and hook.strip():
        key_insight = hook.strip()
    else:
        key_insight = title
    
    # Contextual Summary: Use first sentence of summary, or first 150 chars
    if summary and summary.strip():
        # Get first sentence or truncate to 150 chars
        first_sentence = summary.split('.')[0].strip()
        if len(first_sentence) > 150:
            first_sentence = first_sentence[:150].rsplit(' ', 1)[0] + '...'
        contextual_summary = first_sentence + '.' if not first_sentence.endswith('.') else first_sentence
    else:
        contextual_summary = "Summary not available."
    
    # Build simple Slack post format
    slack_post = f"""{key_insight}

{contextual_summary}

Read more >> <{url}|LINK>"""
    
    return slack_post


def sort_by_engagement(df):
    """Sort dataframe by engagement level (HIGH > MEDIUM > LOW)."""
    if df is None or df.empty:
        return df
    
    engagement_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
    df['engagement_order'] = df['engagement'].map(engagement_order).fillna(2)
    df = df.sort_values('engagement_order').drop('engagement_order', axis=1)
    return df


def main():
    # Sidebar for date selection - MUST be first
    with st.sidebar:
        # Compact header with total count
        total_count = get_total_news_count()
        st.markdown(f"""
        <div style='padding: 0.75rem 0; border-bottom: 1px solid #e5e7eb; margin-bottom: 1rem;'>
            <div style='font-size: 0.75rem; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.25rem;'>Total News Collected</div>
            <div style='font-size: 1.75rem; font-weight: 700; color: #1a1a1a;'>{total_count:,}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Compact date selection
        st.markdown("""
        <div style='font-size: 0.75rem; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.5rem; margin-top: 0.5rem;'>Date Selection</div>
        """, unsafe_allow_html=True)
        available_dates = get_available_dates()
        
        # Default to today's date if available, otherwise most recent
        today_str = datetime.date.today().isoformat()
        default_index = 0
        if available_dates and today_str in available_dates:
            default_index = available_dates.index(today_str)
        
        if available_dates:
            selected_date = st.selectbox(
                "Choose a date:",
                options=available_dates,
                index=default_index,
                format_func=lambda x: datetime.datetime.strptime(x, "%Y-%m-%d").strftime("%b %d, %Y"),
                label_visibility="collapsed"
            )
        else:
            selected_date = datetime.date.today().isoformat()
            st.warning("No CSV files found.")
        
        # Compact priority filters
        st.markdown("""
        <div style='font-size: 0.75rem; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.5rem; margin-top: 0.75rem;'>Priority Filters</div>
        """, unsafe_allow_html=True)
        show_high = st.checkbox("HIGH Priority", value=True)
        show_medium = st.checkbox("MEDIUM Priority", value=True)
        show_low = st.checkbox("LOW Priority", value=True)
        
        # Compact data updates info
        st.markdown("""
        <div style='margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #e5e7eb;'>
            <div style='font-size: 0.75rem; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.5rem;'>Data Updates</div>
            <div style='font-size: 0.75rem; color: #4b5563; line-height: 1.5;'>
                Need to update? Contact <strong>Benjamin Miranda</strong> (Market Intelligence Lead)
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Compact attribution at bottom
        st.markdown("""
        <div style='margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #e5e7eb; font-size: 0.75rem; color: #6b7280;'>
            <strong style='color: #1a1a1a;'>Benjamin Miranda</strong><br>
            Market Intelligence Lead
        </div>
        """, unsafe_allow_html=True)
    
    # Header without container box - after sidebar (only once)
    st.markdown('<div class="main-header">News Radar</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Your morning briefing for CCaaS & Employee Service news</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-text">Compilation of relevant news from the last 24 hours</div>', unsafe_allow_html=True)
    
    # Load data
    ccaas_df, es_df = load_news_data(selected_date)
    
    # Combine dataframes
    all_news = []
    if ccaas_df is not None and not ccaas_df.empty:
        all_news.append(ccaas_df)
    if es_df is not None and not es_df.empty:
        all_news.append(es_df)
    
    if not all_news:
        st.error(f"❌ No news data found for {datetime.datetime.strptime(selected_date, '%Y-%m-%d').strftime('%B %d, %Y')}")
        st.info("💡 Make sure you've run the news pipelines to generate CSV files.")
        return
    
    combined_df = pd.concat(all_news, ignore_index=True)
    
    # Apply engagement filters
    engagement_filter = []
    if show_high:
        engagement_filter.append('HIGH')
    if show_medium:
        engagement_filter.append('MEDIUM')
    if show_low:
        engagement_filter.append('LOW')
    
    if engagement_filter:
        combined_df = combined_df[combined_df['engagement'].isin(engagement_filter)]
    
    # Sort by engagement
    combined_df = sort_by_engagement(combined_df)
    
    # Statistics with Zendesk colors
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total = len(combined_df)
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-label">Total Articles</div>
            <div class="stat-number">{total}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        high_count = len(combined_df[combined_df['engagement'] == 'HIGH'])
        st.markdown(f"""
        <div class="stat-box stat-box-high">
            <div class="stat-label">HIGH Priority</div>
            <div class="stat-number">{high_count}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        medium_count = len(combined_df[combined_df['engagement'] == 'MEDIUM'])
        st.markdown(f"""
        <div class="stat-box stat-box-medium">
            <div class="stat-label">MEDIUM Priority</div>
            <div class="stat-number">{medium_count}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        low_count = len(combined_df[combined_df['engagement'] == 'LOW'])
        st.markdown(f"""
        <div class="stat-box stat-box-low">
            <div class="stat-label">LOW Priority</div>
            <div class="stat-number">{low_count}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Category tabs with Zendesk styling
    tab1, tab2, tab3, tab4 = st.tabs(["All News", "CCaaS", "Employee Service", "CX AI"])
    
    with tab1:
        if combined_df.empty:
            st.info("No articles match the selected filters. Try adjusting your priority filters in the sidebar.")
        else:
            st.markdown(f"### {len(combined_df)} articles")
            st.markdown("---")
            for idx, row in combined_df.iterrows():
                render_news_card(row.to_dict(), f"all-{idx}")
    
    with tab2:
        ccaas_filtered = combined_df[combined_df['category'] == 'CCaaS'] if 'category' in combined_df.columns else pd.DataFrame()
        if ccaas_filtered.empty:
            st.info("No CCaaS articles found for this date.")
        else:
            st.markdown(f"### {len(ccaas_filtered)} articles")
            st.markdown("---")
            for idx, row in ccaas_filtered.iterrows():
                render_news_card(row.to_dict(), f"ccaas-{idx}")
    
    with tab3:
        es_filtered = combined_df[combined_df['category'] == 'ES'] if 'category' in combined_df.columns else pd.DataFrame()
        if es_filtered.empty:
            st.info("No Employee Service articles found for this date.")
        else:
            st.markdown(f"### {len(es_filtered)} articles")
            st.markdown("---")
            for idx, row in es_filtered.iterrows():
                render_news_card(row.to_dict(), f"es-{idx}")
    
    with tab4:
        ai_cs_filtered = filter_ai_cs_news(combined_df)
        if ai_cs_filtered.empty:
            st.info("No CX AI strategic news found for this date. This tab shows HIGH and MEDIUM priority news about AI movements in the Customer Service ecosystem (acquisitions, partnerships, features, etc.).")
        else:
            st.markdown(f"### {len(ai_cs_filtered)} articles")
            st.markdown("<div style='font-size: 0.875rem; color: #6b7280; margin-bottom: 1rem;'>Strategic AI movements in Customer Service ecosystem (HIGH & MEDIUM priority only)</div>", unsafe_allow_html=True)
            st.markdown("---")
            for idx, row in ai_cs_filtered.iterrows():
                render_news_card(row.to_dict(), f"ai-cs-{idx}")


if __name__ == "__main__":
    main()
