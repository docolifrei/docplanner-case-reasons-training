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
    df = pd.read_csv('data.csv')
    df['Case Reason 1 (mandatory)'] = df['Case Reason 1 (mandatory)'].ffill()
    df['Case Reason 2 (mandatory)'] = df['Case Reason 2 (mandatory)'].ffill()
    return df


df = load_data()

if 'shuffled_data' not in st.session_state:
    st.session_state.shuffled_data = df.dropna(subset=['Definition / Notes']).sample(frac=1).reset_index(drop=True)


# --- 4. CORE FUNCTIONS ---


def get_ai_email(definition):
    # This replaces the AI call with the actual data from your CSV
    if pd.isna(definition) or definition == "":
        return "No description available for this scenario."

    # We return the raw text from your 'Description' column
    return f"Customer Inquiry: {definition}"

def save_score(name, country, score):
    # Manager's Reward Logic: 100=3 logos, 70=2 logos, 40=1 logo
    asterisk_count = 3 if score >= 100 else (2 if score >= 70 else (1 if score >= 40 else 0))
    try:
        existing_data = conn.read(ttl=0)
        new_entry = pd.DataFrame([[name, country, score, asterisk_count]],
                                 columns=['Name', 'Country', 'Score', 'Asterisks'])
        updated_data = pd.concat([existing_data, new_entry], ignore_index=True)
        conn.update(data=updated_data)
        st.success(f"Sync Complete! You earned {asterisk_count} Docplanner Logos.")
    except Exception as e:
        st.error(f"GCP Sync Error: {e}")


def reset_quiz():
    st.session_state.score = 0
    st.session_state.current_question = 0
    st.session_state.quiz_complete = False
    st.session_state.question_solved = False
    st.session_state.shuffled_data = df.dropna(subset=['Definition / Notes']).sample(frac=1).reset_index(drop=True)


# --- 5. SIDEBAR NAVIGATION ---
# --- 5. AUTHENTICATION & NAVIGATION GATE ---
if st.session_state.role is None:
    # ONLY SHOW LOGIN PAGE - NO SIDEBAR HERE
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.title("🛡️ DocPlanner Training Access")

    col1, col2 = st.columns(2)
    with col1:
        u_name = st.text_input("Agent Name")
    with col2:
        u_country = st.selectbox("Country", ["Spain", "Poland", "Italy", "Brazil", "Mexico", "Global"])

    u_role = st.radio("Access Level", ["Agent", "Admin Manager"], horizontal=True)
    u_pass = st.text_input("Security Key", type="password") if u_role == "Admin Manager" else ""

    if st.button("Initialize"):
        if u_role == "Admin Manager" and u_pass == "DP2026!":
            st.session_state.role = "admin"
            st.session_state.user = u_name
            st.session_state.country = u_country
            st.rerun()
        elif u_role == "Agent" and u_name:
            st.session_state.role = "user"
            st.session_state.user = u_name
            st.session_state.country = u_country
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

else:
    # --- EVERYTHING ELSE ONLY RUNS AFTER LOGIN ---
    with st.sidebar:
        st.image("dp_logo.png", width=50)
        st.title("DP Portal")
        st.divider()

        # Define the menu based on role
        if st.session_state.role == "admin":
            menu_options = ["Admin Dashboard", "Practice", "Explanation", "Leaderboard"]
        else:
            menu_options = ["Practice", "Explanation", "Leaderboard"]

        # Create the navigation widget ONLY ONCE
        page = st.radio("Navigation", menu_options, key="main_navigation")

        st.divider()
        if st.button("Logout", key="sidebar_logout"):
            st.session_state.role = None
            st.rerun()

    # --- PAGE ROUTING ENGINE ---
    if page == "Admin Dashboard":
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.header("⚙️ Admin Controls")
        c1, c2 = st.columns(2)
        c1.metric("Status", "Online", "Stable")
        # c2.metric("Project ID", "case-reasons-training") # Simplified to avoid secret errors
        st.write(f"**Admin:** {st.session_state.user}")
        st.markdown('</div>', unsafe_allow_html=True)

        st.write("### Global Training Audit")

        # Use the SAME published CSV link we used for the Leaderboard
        csv_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQlvQW_QsBwRB3ZWmK7wibMhW7oeBqbpd8osTvPprhxXROfpc01x0JwcptMB4oOFHMcB0V-IHvvmnU2/pub?gid=0&single=true&output=csv"

        try:
            # Direct read bypasses the 'TransportError'
            admin_data = pd.read_csv(csv_url)
            st.dataframe(admin_data, use_container_width=True)
        except Exception as e:
            st.error("Could not load audit data. Please check the 'Publish to Web' link.")


    elif page == "Practice":

        # --- SIDEBAR SEARCH stays as it is ---

        with st.sidebar:
            st.divider()
            st.subheader("📖 Quick Reference")
            search_term = st.text_input("Search taxonomy keywords:")
            if search_term:
                filtered_df = df[df['Definition / Notes'].str.contains(search_term, case=False, na=False)]

            else:
                filtered_df = df.head(5)

            for _, row_sidebar in filtered_df.iterrows():
                with st.expander(
                        f"{row_sidebar['Case Reason 1 (mandatory)']} > {row_sidebar['Case Reason 2 (mandatory)']}"):
                    st.write(
                        f"**R3:** {row_sidebar['Case Reason 3 (optional)']}\n\n**Note:** {row_sidebar['Definition / Notes']}")

        # --- MAIN CONTENT LOGIC ---

        if not st.session_state.user:
            st.warning("Please Login first.")

        elif st.session_state.quiz_complete:
            st.balloons()
            st.success(f"Well done {st.session_state.user}! Score: {st.session_state.score}")
            if st.button("Restart"): reset_quiz()


        else:

            # THIS SECTION NOW PULLS DIRECTLY FROM YOUR DATA
            row = st.session_state.shuffled_data.iloc[st.session_state.current_question]
            current_email = get_ai_email(row['Definition / Notes'])
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader(f"Scenario {st.session_state.current_question + 1}")
            # This displays the text from your CSV instantly
            st.write(current_email)
            st.markdown('</div>', unsafe_allow_html=True)


            # --- TAXONOMY DROPDOWNS ---

            r1 = st.selectbox("Reason 1",

                              ["-- Choose --"] + sorted(df['Case Reason 1 (mandatory)'].unique().tolist()),

                              key=f"r1_q{st.session_state.current_question}")

            r2 = "-- Choose --"

            r3 = None

            if r1 != "-- Choose --":

                options_r2 = sorted(
                    df[df['Case Reason 1 (mandatory)'] == r1]['Case Reason 2 (mandatory)'].unique().tolist())

                r2 = st.selectbox("Reason 2", ["-- Choose --"] + options_r2,
                                  key=f"r2_q{st.session_state.current_question}")

                if r2 != "-- Choose --":

                    r3_options = df[(df['Case Reason 1 (mandatory)'] == r1) &

                                    (df['Case Reason 2 (mandatory)'] == r2)][
                        'Case Reason 3 (optional)'].dropna().unique().tolist()

                    if r3_options:
                        r3 = st.selectbox("Reason 3 (Optional)", ["-- Choose --"] + r3_options,
                                          key=f"r3_q{st.session_state.current_question}")

            # --- SUBMISSION LOGIC ---

            if not st.session_state.question_solved:

                if st.button("Submit Answer"):

                    check_r1 = (r1 == row['Case Reason 1 (mandatory)'])

                    check_r2 = (r2 == row['Case Reason 2 (mandatory)'])

                    correct_r3 = row['Case Reason 3 (optional)']

                    check_r3 = True if pd.isna(correct_r3) else (r3 == correct_r3)

                    if check_r1 and check_r2 and check_r3:

                        st.session_state.score += 10

                        st.session_state.question_solved = True

                        st.rerun()

                    else:

                        st.session_state.score -= 5

                        st.error("Incorrect path. Review the Sidebar Reference and try again!")

            else:

                st.success("Correct!")

                if st.button("Next Scenario"):

                    if st.session_state.current_question + 1 < 10:

                        st.session_state.current_question += 1

                        st.session_state.question_solved = False

                    else:

                        save_score(st.session_state.user, st.session_state.country, st.session_state.score)

                        st.session_state.quiz_complete = True

                    st.rerun()

    elif page == "Explanation":
        st.header("📖 Taxonomy Guide")
        st.write("Full taxonomy details for reference:")
        st.dataframe(df, use_container_width=True)



    elif page == "Leaderboard":

        st.header("🏆 Wall of Fame")
        csv_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQlvQW_QsBwRB3ZWmK7wibMhW7oeBqbpd8osTvPprhxXROfpc01x0JwcptMB4oOFHMcB0V-IHvvmnU2/pub?gid=0&single=true&output=csv"

        try:

            df_leader = pd.read_csv(csv_url)

            if not df_leader.empty:
                df_leader = df_leader.sort_values(by="Score", ascending=False)
                display_df = df_leader[['Name', 'Country', 'Score', 'Asterisks']]
                display_df.columns = ['Agent Name', 'Country', 'Points', 'Logos']

                st.table(display_df.head(15))
            else:
                st.info("The board is currently empty!")
        except Exception as e:
            st.error("Waiting for first score with Country data to be saved...")