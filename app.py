import streamlit as st
import asyncio
from langchain_google_genai import ChatGoogleGenerativeAI
from browser_use import Agent
from datetime import datetime, timedelta
from google.cloud import bigquery
from google.oauth2 import service_account
from streamlit_feedback import streamlit_feedback
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
json_key_path = 'service-account-key.json'
credentials = service_account.Credentials.from_service_account_file(json_key_path)
client = bigquery.Client(credentials=credentials, project=credentials.project_id)

st.set_page_config(page_title="Web Search Assistant", page_icon="🔍", layout="wide")

# Sidebar
with st.sidebar:
    st.header("Get free API Key")
    st.markdown("""
    1. Visit [Google AI Studio](https://aistudio.google.com/prompts/new_chat?_gl=1*15wmpsj*_ga*MTE4NzAxNDg4MS4xNzMwMzgzMjcy*_ga_P1DBVKWT6V*MTczNzY4OTYyNS44LjAuMTczNzY4OTYyNS42MC4wLjEyMDIxNjYxOTY.)
    2. Create/Sign in to your account
    3. Get your API key from settings
    """)

# Session state initialization
if 'feedback_key' not in st.session_state:
    st.session_state.feedback_key = 'feedback_widget'

def store_session_data(session_data_df, session_id, session_time):
    new_row = pd.DataFrame.from_dict({'session_id': [session_id], 'session_creation_time': [session_time]})
    
    # Append the new row to the DataFrame
    session_data_df = pd.concat([session_data_df, new_row], ignore_index=True)

def make_new_session(session_data_df):
    session_id = 'id_'+str(datetime.now())
    session_time = datetime.now()
    
    # Store session data in session_state
    st.session_state.session_id = 'id_'+str(datetime.now())
    st.session_state.session_time = session_time
    st.session_state.created_at = session_time
    st.session_state.welcome_shown = False
    st.session_state.share_button = False
    
    # Store session data in the BQ
    print(session_id, session_time)
    session_data_df['session_id']=[session_id]
    session_data_df['session_creation_time']=[session_time]
    print(session_data_df.shape)
    upload_to_bq(session_data_df, 'session_data')


@st.dialog("Welcome to Web Agent 🌐")
def welcome_message():
    st.balloons()
    st.write(f"""
**Your AI’s Gateway to the Browser in one click!**

✨ Features:

1. Seamless Integration: Effortlessly connect your AI agents to any browser for enhanced automation.
2. Full Control: Enable typing, clicking, scrolling, and more—just like a real user!
3. User-Friendly Setup: No complex configurations; start controlling the browser in seconds.
4. Versatile Applications: Perfect for data scraping, automated testing, or streamlining workflows.
5. Simply define the actions your agent needs to perform, and Web Agent takes care of the rest! 🚀

###### Collects feedback to improve — no personal data 🔒
###### Powered by Google Cloud 🌥️
""")

@st.dialog("Share Your Model Matrimony Experience 🕵️‍♂️")
def share_app():
    if 'copy_button_clicked' not in st.session_state:
        st.session_state.copy_button_clicked = False
        
    def copy_to_clipboard():
        st.session_state.copy_button_clicked = True
        st.write('<script>navigator.clipboard.writeText("google.com");</script>', unsafe_allow_html=True)
        
    app_url = 'https://model-matrimony.app'
    text = f'''Looking for the perfect open source LLM? 🤔
Check out Model Matrimony - it matches you with the ideal LLM for your needs!

Try this free tool and find your perfect model match now 🚀
Link to the app: {app_url}
    '''
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        url = 'https://www.linkedin.com/sharing/share-offsite/?url={app_url}'
        st.link_button('💼 LinkedIn', url)
    with col2:
        url = f'https://x.com/intent/post?original_referer=http%3A%2F%2Flocalhost%3A8502%2F&ref_src=twsrc%5Etfw%7Ctwcamp%5Ebuttonembed%7Ctwterm%5Eshare%7Ctwgr%5E&text={text}+%F0%9F%8E%88&url=%7B{app_url}%7D'
        st.link_button('𝕏 Twitter', url)
    with col3:
        placeholder = st.empty()
        if st.session_state.copy_button_clicked:
            placeholder.button("Copied!", disabled=True)
            st.toast('Link copied to clipboard! 📋')
        else:
            placeholder.button('📄 Copy Link', on_click=copy_to_clipboard)
    st.text_area("Sample Text", text, height=350)

async def perform_search(query, api_key):
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-pro",
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
        google_api_key=api_key
    )
    
    agent = Agent(
        task=query,
        llm=llm,
    )
    
    result = await agent.run()
    return result.extracted_content()

def upload_to_bq(df, table_name):
    destination_table = client.dataset("web_agent").table(f'{table_name}')
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
    load_job = client.load_table_from_dataframe(df, destination_table, job_config=job_config)
    load_job.result()

def _submit_feedback(user_response, emoji=None):
    session_id = st.session_state.get("session_id")
    feedback_value = 1 if user_response['score'] == '👍' else 0
    user_feedback = user_response['text']
    new_feedback = pd.DataFrame([[session_id, feedback_value, user_feedback]], columns=["session_id", "vote", "comment"])
    upload_to_bq(new_feedback, 'user_feedback')
    st.success("Your feedback has been submitted!")

def load_lottieurl(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

# lottie_hello = load_lottieurl('https://lottie.host/7068ee1c-5f48-429c-aca3-7aa89eb1de98/MpwlwRBTj0.json')

session_data_df = pd.DataFrame(columns=["session_id", "session_creation_time"])
if 'session_id' not in st.session_state:
    make_new_session(session_data_df)
else:
    # Check if session is older than 5 minutes
    session_age = datetime.now() - st.session_state.created_at
    if session_age > timedelta(minutes=10):
        make_new_session(session_data_df)

if 'copy_button_clicked' not in st.session_state:
    st.session_state.copy_button_clicked = False

# Main layout
col1, col2 = st.columns([3,1])
with col1:
    st.title("🌐 Web Agent")
with col2:
    api_key = st.text_input("Enter Google API Key", type="password")

# Show welcome message only once per session
if not st.session_state.welcome_shown:
    welcome_message()
    st.session_state.welcome_shown = True

if 'search_results' not in st.session_state:
    st.session_state.search_results = None

container = st.container()
with container:
    c1, c2 = st.columns([3,1])
    query = c1.text_input("What would you like to search for?", 
                         placeholder="Enter your search query...", 
                         label_visibility='hidden')
    search_button = c1.button("Execute 🚀")
    
    if search_button and query:
        if not api_key:
            st.error("Please enter your API key")
        else:
            with st.spinner("Agents are working ..."):
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    results = loop.run_until_complete(perform_search(query, api_key))
                    st.session_state.search_results = results[-1]
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
                finally:
                    loop.close()

    if st.session_state.search_results:
        c1.markdown(results[:-1])
        c1.markdown(st.session_state.search_results)

streamlit_feedback(
    feedback_type="thumbs",
    optional_text_label="Please provide extra information",
    on_submit=_submit_feedback,
    key=st.session_state.feedback_key,
)

st.markdown(
    """
    <style>
    .footer {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        text-align: center;
        padding: 10px 0;
        font-size: 14px;
        color: #f1f1f1;
    }
    </style>
    <div class="footer">
        Built with ❤️ using Streamlit | 
        <a href="https://www.linkedin.com/in/bhavishya-pandit/" target="_blank" style="color: #f1f1f1; text-decoration: none;">Bhavishya Pandit</a>
    </div>
    """,
    unsafe_allow_html=True,
)