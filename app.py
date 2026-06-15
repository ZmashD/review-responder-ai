import os
import json
import streamlit as st
from responder_engine import generate_review_response
from database_manager import init_db, log_review_transaction
from notifier_engine import send_escalation_email
from ingestion_simulator import fetch_next_simulated_review
from analytics_engine import (
    get_overall_kpis, 
    get_sentiment_distribution, 
    get_escalation_reasons, 
    get_brand_performance
)

# Configure the browser tab title and layout
st.set_page_config(page_title="AI Review Responder", layout="wide")

# Global Configuration Constants
CONFIG_DIR = "config"
MOCK_DATA_PATH = os.path.join(CONFIG_DIR, "mock_reviews.json")

# Initialize the relational SQLite database on startup
init_db()


# ==========================================
# 1. CACHED FILE I/O OPERATIONS
# ==========================================

@st.cache_data
def load_mock_reviews(file_path: str) -> list:
    """Loads and caches test scenarios to minimize disk access."""
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.sidebar.error(f"Error reading mock file: {e}")
    return []


@st.cache_data
def get_available_profiles(config_dir: str) -> list:
    """Scans and caches valid JSON brand profiles from the target directory."""
    if os.path.exists(config_dir):
        # Explicitly filter out any testing data pools from the dropdown selection list
        return [
            f for f in os.listdir(config_dir) 
            if f.endswith(".json") and f not in ["mock_reviews.json", "mock_reviews_pool.json"]
        ]
    return []


# ==========================================
# 2. INTERFACE BUILDERS
# ==========================================

def build_sidebar_sandbox() -> str:
    """Renders the testing environment sidebar controls and returns selected text."""
    st.sidebar.header("🧪 Test Environment Sandbox")
    mock_data = load_mock_reviews(MOCK_DATA_PATH)
    
    if not mock_data:
        if not os.path.exists(MOCK_DATA_PATH):
            st.sidebar.warning("mock_reviews.json not found inside config/")
        return ""
        
    options = ["-- Select a Mock Review Type --"] + [item["expected_type"] for item in mock_data]
    selection = st.sidebar.selectbox("Load Test Scenario Dataset:", options, key="sandbox_dropdown")
    
    if selection != "-- Select a Mock Review Type --":
        matched_item = next(item for item in mock_data if item["expected_type"] == selection)
        st.sidebar.success(f"Loaded: {selection}")
        return matched_item["review_text"]
        
    return ""


# ==========================================
# 3. MAIN APPLICATION RUNTIME
# ==========================================

# Initialize execution session state variables
if "current_analysis" not in st.session_state:
    st.session_state.current_analysis = None
if "last_processed_review" not in st.session_state:
    st.session_state.last_processed_review = ""
if "last_used_profile" not in st.session_state:
    st.session_state.last_used_profile = ""

# Create Tabs
tab1, tab2 = st.tabs(["📊 Review Responder", "📈 Executive Analytics"])

with tab1:
    # 1A. Construct the sandbox environment sidebar
    selected_review_text = build_sidebar_sandbox()

    # 1B. Display the main workspace headers
    st.title("📊 AI Review Responder Workspace")
    st.caption("Select an active brand profile and process instant brand-compliant drafts.")
    st.divider()

    st.subheader("🏢 Active Brand Environment")
    available_profiles = get_available_profiles(CONFIG_DIR)

    if not available_profiles:
        st.error("❌ No configuration profiles found in the config directory.")
        st.stop()

    selected_profile = st.selectbox(
        "Choose which location or brand guidelines to enforce:",
        options=available_profiles,
        index=0
    )
    st.divider()

    # Initialize a session state variable for the input field if it doesn't exist yet
    if "review_input_value" not in st.session_state:
        st.session_state.review_input_value = ""

    # Master Automation Toggle Controls
    st.subheader("🤖 Automation Stream Settings")
    auto_ingest = st.toggle("Enable Real-Time Background Ingestion Loop", value=False)

    # Local execution fragment to handle background scheduling safely
    @st.fragment(run_every=30.0 if auto_ingest else None)
    def render_review_workspace_container(sidebar_text: str):
        # 1A. Sync check: If a sidebar scenario is loaded, force update the workspace state
        if sidebar_text and st.session_state.get("last_processed_review") != sidebar_text:
            st.session_state.review_input_value = sidebar_text

        # Check if autopilot ingestion mode is active
        if auto_ingest:
            mock_data = fetch_next_simulated_review()
            if mock_data:
                st.session_state.review_input_value = mock_data["review_text"]
                st.toast(f"📥 Automated Stream Ingested Review: {mock_data['review_id']}")

        # Layout manual adjustment columns inside the fragment card bounds
        col_sim1, col_sim2 = st.columns([3, 1])

        with col_sim1:
            if st.button("📥 Fetch Mock Review from Ingestion Stream", use_container_width=True):
                mock_data = fetch_next_simulated_review()
                if mock_data:
                    st.session_state.review_input_value = mock_data["review_text"]
                    st.rerun()

        with col_sim2:
            if st.button("🗑️ Clear Workspace", use_container_width=True):
                st.session_state.review_input_value = ""
                st.sidebar.selectbox("Load Test Scenario Dataset:", ["-- Select a Mock Review Type --"], index=0)
                st.rerun()

        # Bind the workspace text area directly to the localized session state container
        return st.text_area(
            "Customer Review Text Workspace:", 
            value=st.session_state.review_input_value,
            height=150
        )

    # Invoke the fragment runner to render the input box onto the page canvas, passing the sidebar state
    customer_review = render_review_workspace_container(selected_review_text)

    # 1D. Resilient processing execution trigger block
    if st.button("Generate Smart Response", type="primary"):
        # 1C. Guardrail against processing empty string configurations
        if not customer_review or not customer_review.strip():
            st.warning("⚠️ Action Blocked: Customer text area cannot be empty or solely whitespace characters.")
        else:
            with st.spinner(f"🤖 AI Engine applying guidelines from '{selected_profile}'..."):
                try:
                    analysis = generate_review_response(customer_review, profile_filename=selected_profile)
                    
                    # Extra structural safety check against empty downstream responses from the engine
                    if not analysis or not getattr(analysis, 'draft_response', '').strip():
                        st.error("⚠️ AI Exception: The response engine parsed successfully but generated an unreadable empty string asset.")
                    else:
                        st.session_state.current_analysis = analysis
                        st.session_state.last_processed_review = customer_review
                        st.session_state.last_used_profile = selected_profile
                        st.success("✅ Analysis Complete!")
                        
                        # 1C. Real-Time Instant Ingestion Escalation Dispatch Check
                        if analysis.escalation_required is True:
                            try:
                                email_sent = send_escalation_email(
                                    review_text=customer_review,
                                    reason=analysis.escalation_reason,
                                    brand_profile=selected_profile
                                )
                                
                                if email_sent:
                                    st.warning("⚠️ High-Risk Emergency Review Detected: An immediate escalation alert has been dispatched to corporate leadership.")
                                else:
                                    st.error("❌ SendGrid Operational Error: The mail server accepted the socket payload but dropped execution delivery.")
                            except Exception as mail_err:
                                st.error(f"❌ Network Alert Broadcast Exception: Response was generated successfully, but the background emergency notification loop dropped. Detail: {mail_err}")
                                
                except KeyError as ke:
                    st.error(f"❌ Configuration Schema Error: Target metadata file '{selected_profile}' appears malformed. Missing key: {ke}")
                except Exception as e:
                    # Capture high-level backend platform drops gracefully without throwing hard trace errors
                    st.error(f"❌ Core API Runtime Connectivity Failure: Model call dropped or rate limit constraints were exceeded. Trace: {e}")

    # 1E. Render downstream validation modules if the state sync matches
    if (st.session_state.current_analysis and 
        st.session_state.last_processed_review == customer_review and
        st.session_state.last_used_profile == selected_profile):
        
        analysis = st.session_state.current_analysis
        
        # Render operational status widgets
        if analysis.escalation_required:
            st.error(f"🚨 [ESCALATE TO MANAGER] Triggers Met: {analysis.escalation_reason}")
        else:
            st.info("🟢 Safe for Standard Auto-Reply (No Escalation Triggers Met)")
            
        st.divider()
        st.subheader("📝 Drafted Brand Response:")
        
        final_draft = st.text_area(
            "You can edit this draft manually before final approval:",
            value=analysis.draft_response,
            height=250
        )
        
        # Execution validation trigger button
        if st.button("Approve & Log Response", type="secondary"):
            # Ensure variations are cleaned out before assessing execution parameters
            if not final_draft or not final_draft.strip():
                st.warning("⚠️ Action Blocked: You cannot submit an entirely empty response draft to the transaction database.")
            else:
                success = log_review_transaction(
                    brand_profile=selected_profile,
                    review_text=customer_review,
                    sentiment=analysis.sentiment,
                    escalation_required=analysis.escalation_required,
                    escalation_reason=analysis.escalation_reason,
                    draft_response=analysis.draft_response,
                    final_response=final_draft
                )
                
                if success:
                    st.balloons()
                    st.success(f"💾 Entry successfully committed to database storage! Profile: {selected_profile}")
                else:
                    st.error("❌ Database Transaction Error: Failed to lock or write transaction entry ledger logs to the SQLite workspace.")

with tab2:
    st.header("Executive Analytics Dashboard")
    
    # KPI Row
    kpis = get_overall_kpis()
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Reviews", kpis['total'])
    col2.metric("Escalation Rate", f"{kpis['escalation_rate']}%")
    col3.metric("Manager Edit Rate", f"{kpis['edit_rate']}%")
    
    st.divider()
    
    # Charts Row
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Sentiment Distribution")
        sentiment_df = get_sentiment_distribution()
        if not sentiment_df.empty:
            st.bar_chart(sentiment_df.set_index("sentiment"))
        else:
            st.info("No data yet.")
            
    with c2:
        st.subheader("Escalation Triggers")
        esc_df = get_escalation_reasons()
        if not esc_df.empty:
            st.bar_chart(esc_df.set_index("escalation_reason"))
        else:
            st.info("No escalations recorded.")

        st.subheader("Brand Performance")
        brand_df = get_brand_performance()
        st.dataframe(brand_df, use_container_width=True)