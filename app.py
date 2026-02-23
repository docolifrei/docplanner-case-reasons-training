import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- 1. INITIALIZE SESSION STATE (Must be at the very top) ---
if 'role' not in st.session_state: st.session_state.role = None
if 'user' not in st.session_state: st.session_state.user = None
if 'country' not in st.session_state: st.session_state.country = None
if 'score' not in st.session_state: st.session_state.score = 0
if 'current_question' not in st.session_state: st.session_state.current_question = 0
if 'quiz_complete' not in st.session_state: st.session_state.quiz_complete = False
if 'question_solved' not in st.session_state: st.session_state.question_solved = False


# --- 2. PREMIUM UI & FONT CONFIGURATION ---
def apply_premium_ui():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Figtree:wght@300&display=swap');
        html, body, [class*="css"], .stText, .stMarkdown {
            font-family: 'Figtree', sans-serif !important;
            font-weight: 300 !important;
        }
        h1, h2, h3 { font-weight: 300 !important; }
        .glass-card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(15px);
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 25px;
            margin-bottom: 20px;
        }
        </style>
    """, unsafe_allow_html=True)


st.set_page_config(page_title="Case Reasons Training", layout="wide")
apply_premium_ui()

# --- 3. DATA & CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)


@st.cache_data
def load_data():
    df = pd.read_csv('[CC][GLOBAL] New Case Reasons Restructure - New Case Taxonomy for Efficiency.csv')
    df['Case Reason 1 (mandatory)'] = df['Case Reason 1 (mandatory)'].ffill()
    df['Case Reason 2 (mandatory)'] = df['Case Reason 2 (mandatory)'].ffill()
    return df


df = load_data()

if 'shuffled_data' not in st.session_state:
    st.session_state.shuffled_data = df.dropna(subset=['Definition / Notes']).sample(frac=1).reset_index(drop=True)


# --- 4. CORE FUNCTIONS ---
def save_score(name, score):
    # Manager's Reward Logic: 100=3 logos, 70=2 logos, 40=1 logo
    asterisk_count = 3 if score >= 100 else (2 if score >= 70 else (1 if score >= 40 else 0))
    try:
        existing_data = conn.read(ttl=0)
        new_entry = pd.DataFrame([[name, score, asterisk_count]], columns=['Name', 'Score', 'Asterisks'])
        updated_data = pd.concat([existing_data, new_entry], ignore_index=True)
        conn.update(data=updated_data)
        st.success(f"SSync Complete! You earned {asterisk_count} Docplanner Logos.")
    except Exception as e:
        st.error(f"GCP Sync Error: {e}")


def reset_quiz():
    st.session_state.score = 0
    st.session_state.current_question = 0
    st.session_state.quiz_complete = False
    st.session_state.question_solved = False
    st.session_state.shuffled_data = df.dropna(subset=['Definition / Notes']).sample(frac=1).reset_index(drop=True)


# --- 5. SIDEBAR NAVIGATION ---
st.sidebar.title("💎 DP Portal")
if st.session_state.role == "admin":
    menu = ["Admin Dashboard", "Explanation", "Leaderboard"]
else:
    menu = ["Login", "Practice", "Explanation", "Leaderboard"]

page = st.sidebar.radio("Navigation", menu)

# --- 6. PAGE LOGIC ---
if page == "Login":
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.title("🛡️ Docplanner Training Access")
    col1, col2 = st.columns(2)
    with col1:
        u_name = st.text_input("Agent Name")
    with col2:
        u_country = st.selectbox("Market", ["Global", "Spain", "Poland", "Italy", "Brazil", "Mexico"])

    u_role = st.radio("Access Level", ["Agent", "Admin Manager"], horizontal=True)
    u_pass = st.text_input("Security Key", type="password") if u_role == "Admin Manager" else ""

    if st.button("Initialize"):
        if u_role == "Admin Manager" and u_pass == "DP2026!":
            st.session_state.role, st.session_state.user, st.session_state.country = "admin", u_name, u_country
            st.rerun()
        elif u_role == "Agent" and u_name:
            st.session_state.role, st.session_state.user, st.session_state.country = "user", u_name, u_country
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

elif page == "Admin Dashboard":
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.header("⚙️ GCP Sync Status")
    c1, c2 = st.columns(2)
    c1.metric("Sheets API", "Connected", "Active")
    c2.metric("Project ID", st.secrets["connections"]["gsheets"]["project_id"])
    st.write(
        f"**Admin:** {st.session_state.user} | **Cloud Identity:** {st.secrets['connections']['gsheets']['client_email']}")
    st.markdown('</div>', unsafe_allow_html=True)

    st.write("### Global Training Audit")
    admin_data = conn.read(ttl=0)
    st.dataframe(admin_data, use_container_width=True)

elif page == "Practice":
    if not st.session_state.user:
        st.warning("Please Login first.")
    elif st.session_state.quiz_complete:
        st.balloons()
        st.success(f"Well done {st.session_state.user}! Score: {st.session_state.score}")
        if st.button("Restart"): reset_quiz()
    else:
        row = st.session_state.shuffled_data.iloc[st.session_state.current_question]
        st.info(f"**Scenario {st.session_state.current_question + 1}:** {row['Definition / Notes']}")

        # Taxonomy Dropdowns
        r1 = st.selectbox("Reason 1", ["-- Choose --"] + sorted(df['Case Reason 1 (mandatory)'].unique().tolist()))
        r2 = st.selectbox("Reason 2", ["-- Choose --"] + sorted(df[df['Case Reason 1 (mandatory)'] == r1][
                                                                    'Case Reason 2 (mandatory)'].unique().tolist())) if r1 != "-- Choose --" else "-- Choose --"

        if not st.session_state.question_solved:
            if st.button("Submit"):
                if r1 == row['Case Reason 1 (mandatory)'] and r2 == row['Case Reason 2 (mandatory)']:
                    st.session_state.score += 10
                    st.session_state.question_solved = True
                    st.rerun()
                else:
                    st.session_state.score -= 5
                    st.error("Incorrect. -5 points.")
        else:
            st.success("Correct!")
            if st.button("Next Scenario"):
                if st.session_state.current_question + 1 < 10:
                    st.session_state.current_question += 1
                    st.session_state.question_solved = False
                else:
                    save_score(st.session_state.user, st.session_state.score)
                    st.session_state.quiz_complete = True
                st.rerun()

elif page == "Leaderboard":
    st.title("🏆 Wall of Fame")
    data = conn.read(ttl="1m").sort_values("Score", ascending=False)
    for _, row in data.head(10).iterrows():
        st.markdown(f'<div class="glass-card"><b>{row["Name"]}</b> - {row["Score"]} pts</div>', unsafe_allow_html=True)
        cols = st.columns(12)
        for i in range(int(row["Asterisks"])):
            with cols[i]: st.image("dp_logo.png", width=30)