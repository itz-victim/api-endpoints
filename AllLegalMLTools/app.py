import streamlit as st

# Set page configuration
st.set_page_config(page_title="Legal Tools", page_icon="⚖️", layout="wide")

# Custom CSS to style the specific buttons
st.markdown("""
    <style>
    .button-container {
        display: flex;
        justify-content: space-around;
        margin-top: 50px;
    }
    .custom-button {
        width: 280px;
        height: 280px;
        font-size: 24px;
    }
    
        .st-emotion-cache-1ghhuty,
.st-emotion-cache-bho8sy {
    display: flex;
    width: 2rem;
    height: 2rem;
    flex-shrink: 0;
    border-radius: 0.5rem;
    align-items: center;
    justify-content: center;
    color: #ffffff;
}

.st-emotion-cache-1ghhuty {
    background-color: #ff6cca; /* Adjusted color */
}
.st-emotion-cache-4zpzjl {
    display: flex;
    width: 2rem;
    height: 2rem;
    flex-shrink: 0;
    border-radius: 0.5rem;
    -webkit-box-align: center;
    align-items: center;
    -webkit-box-pack: center;
    justify-content: center;
    background-color: rgb(255 126 108);
    color: rgb(14, 17, 23);
}
.st-emotion-cache-jmw8un {
    display: flex;
    width: 2rem;
    height: 2rem;
    flex-shrink: 0;
    border-radius: 0.5rem;
    -webkit-box-align: center;
    align-items: center;
    -webkit-box-pack: center;
    justify-content: center;
    background-color: rgb(69 166 255);
    color: rgb(14, 17, 23);
}
.st-emotion-cache-bho8sy {
    background-color: #abff45; /* Adjusted color */
}
div.stDownloadButton > button:first-child,
div.stButton > button:first-child {
    background-color: #82bc9a; /* Solid background color */
    color: #ffffff;
    border: none;
    border-radius: 12px; /* Smaller border radius */
    padding: 8px 16px; /* Smaller padding */
    font-size: 14px; /* Smaller font size */
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
    transition: background-color 0.3s ease, box-shadow 0.3s ease, transform 0.3s ease;
}
.st-emotion-cache-go9sty {
    display: flex;
    -webkit-box-align: center;
    align-items: center;
    padding-top: 0px;
    padding-bottom: 0px;
}

.st-b5 {
    transition-timing-function: cubic-bezier(0.18, 0.89, 0.32, 1.28);
}
.st-cx {
    background-color: rgb(240 255 239);
}
div.stDownloadButton > button:hover,
div.stButton > button:hover {
    background-color: #abd6ab; /* Adjusted color on hover */
    color: #ffffff;
    box-shadow: 0 8px 15px rgba(0, 0, 0, 0.3);
    transform: scale(1.05);
}

/* Adjusted style for st-emotion-cache-1j6rxz7 */
.st-emotion-cache-1j6rxz7 {
    display: flex;
    gap: 0.5rem;
    align-items: center; /* Adjusted alignment */
    justify-content: center;
}
.st-emotion-cache-1ld26xq {
    font-size: 14px;
    width: 1.375rem;
    height: 1.375rem;
    border-width: 3px;
    padding: 0px;
    margin: 0px;
    border-color: rgb(94 255 94) rgba(255, 255, 255, 0.2) rgba(255, 255, 255, 0.2);
    -webkit-box-flex: 0;
    flex-grow: 0;
    flex-shrink: 0;
}
.st-emotion-cache-1yhgwcx {
    display: flex;
    -webkit-box-align: center;
    align-items: center;
    padding: 1rem;
    background-color: rgb(197, 230, 202);
    border-radius: 0.9rem;
    color: rgb(62, 80, 80);
    border-color: rgb(58 176 58) rgba(255, 255, 255, 0.2) rgba(255, 255, 255, 0.2);
}
.st-emotion-cache-5mifvs {
    display: inline-flex;
    -webkit-box-align: center;
    align-items: center;
    -webkit-box-pack: center;
    justify-content: center;
    font-weight: 400;
    padding: 0.25rem 0.75rem;
    border-radius: 0.5rem;
    min-height: 2.5rem;
    margin: 0px;
    line-height: 1.6;
    color: inherit;
    width: auto;
    user-select: none;
    background-color: rgb(139 210 139);
    border: 1px solid rgba(62, 80, 80, 0.2);
}
    </style>
    """, unsafe_allow_html=True)

# Initialize session state
if "page" not in st.session_state:
    st.session_state.page = "home"

def home():
    st.title("Legal Tools ⚖️")
    st.write("Welcome to the Legal Tools application. Please select a tool below:")

    # Button container
    st.markdown('<div class="button-container">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.markdown('<button class="custom-button">:frame_with_picture: Case Summarizer.img</button>', unsafe_allow_html=True):
            if st.button("Case Summarizer", key="summarizer"):
                st.session_state.page = "summarizer"
    with col2:
        if st.markdown('<button class="custom-button">:frame_with_picture: Case Search.img</button>', unsafe_allow_html=True):
            if st.button("Case Search", key="search"):
                st.session_state.page = "search"
    with col3:
        if st.markdown('<button class="custom-button">:frame_with_picture: Law Chatbot.img</button>', unsafe_allow_html=True):
            if st.button("Law Chatbot", key="chatbot"):
                st.session_state.page = "chatbot"
    st.markdown('</div>', unsafe_allow_html=True)

def run_script(script_name):
    exec(open(script_name).read(), globals())

def main():
    if st.session_state.page == "summarizer":
        run_script('case_summariser.py')
    elif st.session_state.page == "search":
        run_script('case_search.py')
    elif st.session_state.page == "chatbot":
        run_script('criminal_case_chatbot.py')
    else:
        home()

if __name__ == "__main__":
    main()
