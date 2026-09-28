import ctypes
import json
import os
import random
import re
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import warnings

from pypdf import PdfReader
import streamlit as st
from streamlit_ace import st_ace
from transformers import pipeline

warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

_PROCTOR_NONCE_KEY = "_assessment_nonce"
_PROCTOR_VIOLATION_BTN_LABEL = "PROCTOR_SECURITY_VIOLATION_TRIGGER"

st.set_page_config(
    page_title="AI Interview Simulation System",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

def _html(markup):
    """Strip indentation and blank lines so Markdown never mangles the HTML."""
    return "\n".join(ln.strip() for ln in markup.splitlines() if ln.strip())


def _md(markup):
    st.markdown(_html(markup), unsafe_allow_html=True)


_md("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
.stApp, .stMarkdown, .stButton button, input, textarea, label, [data-baseweb="select"] { font-family: 'Inter', sans-serif; }
.stApp { background: linear-gradient(180deg, #eef2ff 0%, #f8fafc 260px); }
.block-container { padding-top: 1.2rem; max-width: 1280px; }
#MainMenu, footer, header, [data-testid="stToolbar"], .stDeployButton { visibility: hidden; display: none !important; }
h1, h2, h3, h4, h5 { color: #0f172a !important; font-weight: 700 !important; letter-spacing: -0.01em; }
hr { border-color: #e2e8f0 !important; }

/* ---------- HERO ---------- */
.app-hero { position: relative; overflow: hidden; text-align: center; padding: 42px 40px; border-radius: 20px; margin-bottom: 20px;
  background: radial-gradient(circle at 12% 20%, rgba(255,255,255,.16), transparent 40%), radial-gradient(circle at 88% 80%, rgba(147,197,253,.30), transparent 45%), linear-gradient(135deg, #1e3a8a 0%, #2563eb 55%, #3b82f6 100%);
  box-shadow: 0 16px 40px rgba(37,99,235,.30); }
.app-hero-badge { display: inline-block; background: rgba(255,255,255,.16); border: 1px solid rgba(255,255,255,.25); color: #e0ecff; font-size: 11px; font-weight: 700; letter-spacing: .16em; padding: 6px 16px; border-radius: 999px; margin-bottom: 16px; text-transform: uppercase; }
.app-hero-title { color: #fff; font-size: 38px; font-weight: 800; letter-spacing: -0.02em; margin-bottom: 12px; text-shadow: 0 2px 10px rgba(0,0,0,.18); }
.app-hero-subtitle { color: #dbeafe; font-size: 15px; max-width: 720px; margin: 0 auto; line-height: 1.6; }

/* ---------- STEPPER ---------- */
.step-bar { display: flex; align-items: flex-start; background: #fff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 18px 10px 14px; margin-bottom: 22px; box-shadow: 0 1px 3px rgba(15,23,42,.05), 0 8px 24px rgba(15,23,42,.04); }
.step-node { flex: 1; position: relative; display: flex; flex-direction: column; align-items: center; text-align: center; gap: 8px; color: #94a3b8; font-size: 12px; font-weight: 500; padding: 0 4px; }
.step-node:not(:last-child)::after { content: ""; position: absolute; top: 14px; left: calc(50% + 20px); width: calc(100% - 40px); height: 2px; background: #e2e8f0; }
.step-node.completed:not(:last-child)::after { background: #16a34a; }
.step-marker { width: 30px; height: 30px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; background: #f1f5f9; border: 2px solid #e2e8f0; color: #64748b; font-size: 12px; font-weight: 700; position: relative; z-index: 1; }
.step-node.active { color: #0f172a; font-weight: 700; }
.step-node.active .step-marker { background: #2563eb; border-color: #2563eb; color: #fff; box-shadow: 0 0 0 5px rgba(37,99,235,.18); }
.step-node.completed { color: #16a34a; font-weight: 600; }
.step-node.completed .step-marker { background: #16a34a; border-color: #16a34a; color: #fff; }
@media (max-width: 900px) { .step-node { font-size: 10px; } .step-marker { width: 26px; height: 26px; } .step-node:not(:last-child)::after { top: 12px; left: calc(50% + 16px); width: calc(100% - 32px); } }

/* ---------- SECTION HEADER ---------- */
.section-header { margin: 2px 0 22px; padding: 4px 0 18px 16px; border-left: 5px solid #2563eb; border-bottom: 1px solid #e2e8f0; }
.section-title { display: flex; align-items: center; gap: 12px; font-size: 24px; font-weight: 800; color: #0f172a; letter-spacing: -0.015em; }
.section-icon { display: inline-flex; align-items: center; justify-content: center; width: 42px; height: 42px; border-radius: 12px; background: #eff6ff; font-size: 22px; }
.section-subtitle { color: #64748b; font-size: 14px; margin-top: 8px; line-height: 1.6; max-width: 900px; }

/* ---------- CARDS / CONTAINERS ---------- */
[data-testid="stVerticalBlockBorderWrapper"] { background: #fff; border-radius: 16px; border-color: #e2e8f0; box-shadow: 0 1px 3px rgba(15,23,42,.05), 0 10px 28px rgba(15,23,42,.05); }
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlockBorderWrapper"] { box-shadow: none; border-radius: 12px; background: #fcfdff; }
[data-testid="stMetric"] { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 14px 16px; }
[data-testid="stMetricValue"] { color: #2563eb; font-weight: 800; }
[data-testid="stMetricLabel"] { color: #64748b; font-weight: 600; }
[data-testid="stExpander"] { border-radius: 12px; border-color: #e2e8f0; background: #fff; }
[data-testid="stExpander"] summary { font-weight: 600; }
.stAlert { border-radius: 12px; }
.stProgress > div > div > div > div { background: linear-gradient(90deg, #2563eb, #60a5fa); }
.stTabs [data-baseweb="tab"] { font-weight: 600; }

/* ---------- MODE CARDS (Step 4) ---------- */
.mode-card { position: relative; height: 100%; min-height: 200px; padding: 28px 26px; border-radius: 18px; background: #fff; border: 2px solid #e2e8f0; box-shadow: 0 8px 24px rgba(15,23,42,.05); transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease; }
.mode-card:hover { transform: translateY(-4px); box-shadow: 0 16px 36px rgba(37,99,235,.16); border-color: #93c5fd; }
.mode-card.primary { border-color: #2563eb; background: linear-gradient(180deg, #f5f9ff 0%, #fff 60%); }
.mode-icon { width: 56px; height: 56px; border-radius: 16px; display: inline-flex; align-items: center; justify-content: center; font-size: 28px; background: #eff6ff; margin-bottom: 14px; }
.mode-card h3 { margin: 0 0 8px; font-size: 21px; }
.mode-card p { color: #64748b; font-size: 14px; line-height: 1.6; margin: 0; }
.mode-tag { position: absolute; top: 16px; right: 16px; font-size: 10px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: #2563eb; background: #dbeafe; padding: 4px 10px; border-radius: 999px; }

/* ---------- BUTTONS ---------- */
.stButton > button { border-radius: 10px !important; font-weight: 600 !important; padding: 10px 20px !important; transition: all .18s ease; }
.stButton > button[kind="primary"], .stButton > button[data-testid="stBaseButton-primary"] { background: linear-gradient(135deg, #2563eb, #1d4ed8) !important; color: #fff !important; border: none !important; box-shadow: 0 4px 12px rgba(37,99,235,.28); }
.stButton > button[kind="primary"]:hover, .stButton > button[data-testid="stBaseButton-primary"]:hover { transform: translateY(-1px); box-shadow: 0 8px 20px rgba(37,99,235,.36) !important; }
.stButton > button[kind="secondary"], .stButton > button[data-testid="stBaseButton-secondary"] { background: #fff !important; color: #1e293b !important; border: 1px solid #cbd5e1 !important; }
.stButton > button[kind="secondary"]:hover, .stButton > button[data-testid="stBaseButton-secondary"]:hover { background: #f1f5f9 !important; border-color: #2563eb !important; color: #2563eb !important; }
.stButton > button:disabled { opacity: .55; cursor: not-allowed; }
.stButton > button p { color: inherit !important; }
.st-key-proctor_violation_btn { display: none !important; }

/* ---------- INPUTS ---------- */
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div { border-radius: 10px !important; border-color: #cbd5e1 !important; background: #fff; }
.stTextInput input:focus, .stTextArea textarea:focus { border-color: #2563eb !important; box-shadow: 0 0 0 3px rgba(37,99,235,.15) !important; }
[data-testid="stFileUploaderDropzone"] { border: 2px dashed #93c5fd; border-radius: 14px; background: #f5f9ff; }

/* ---------- STATUS BADGES ---------- */
.status-locked, .status-pending { display: inline-block; padding: 6px 14px; border-radius: 999px; font-weight: 600; font-size: 12px; }
.status-locked { background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; }
.status-pending { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }

.app-footer { text-align: center; color: #94a3b8; font-size: 12px; margin: 28px 0 8px; }
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 8px; }
</style>
""")

# =========================================================================
# PRESENTATION HELPERS — hero banner, step progress bar, section headers
# =========================================================================

_STEP_LABELS = [
    (1, "Profile & Resume"),
    (2, "Candidate Analysis"),
    (3, "Interview Setup"),
    (4, "Interview Experience"),
    (5, "Technical Interview"),
    (6, "Behavioral / HR"),
    (7, "Candidate Report"),
]

def _render_app_header():
    _md("""
    <div class="app-hero">
        <div class="app-hero-badge">AI-Powered Career Readiness Platform</div>
        <div class="app-hero-title">🧠 AI INTERVIEW SIMULATION SYSTEM</div>
        <div class="app-hero-subtitle">
            Resume intelligence, live coding assessments, theory evaluation, and
            behavioral HR simulation — all in one guided workspace.
        </div>
    </div>
    """)


def _render_step_progress(current_step):
    nodes = []
    for step_num, label in _STEP_LABELS:
        if step_num < current_step:
            cls, marker = "step-node completed", "✓"
        elif step_num == current_step:
            cls, marker = "step-node active", str(step_num)
        else:
            cls, marker = "step-node", str(step_num)
        nodes.append(f'<div class="{cls}"><span class="step-marker">{marker}</span><span>{label}</span></div>')
    _md('<div class="step-bar">' + "".join(nodes) + "</div>")


def _render_section_header(icon, title, subtitle=None):
    sub = f'<div class="section-subtitle">{subtitle}</div>' if subtitle else ""
    _md(f"""
    <div class="section-header">
        <div class="section-title"><span class="section-icon">{icon}</span><span>{title}</span></div>
        {sub}
    </div>
    """)

IT_ROLES = [
    "Full Stack Software Developer",
    "Data Scientist / Machine Learning Engineer",
    "Backend Software Engineer",
    "Frontend Web Developer",
    "DevOps / Cloud Engineer",
    "Cybersecurity Analyst",
    "UI/UX Designer",
]

# =========================================================================
# 1. APPLICATION STATE & MEMORY INITIALIZATION
# =========================================================================

if "wizard_step" not in st.session_state:
    st.session_state.wizard_step = 1
# Catch proctor verification signal instantly at script startup
if st.query_params.get("proctor_verified") == "true":
    st.query_params.clear()
    st.session_state.device_check_passed = True
    st.session_state.wizard_step = 5
    st.rerun()
if "selected_module" not in st.session_state:
    st.session_state.selected_module = None
if "identified_role" not in st.session_state:
    st.session_state.identified_role = None
if "desired_role" not in st.session_state:
    st.session_state.desired_role = IT_ROLES[0]
if "selected_programming_language" not in st.session_state:
    st.session_state.selected_programming_language = "Python"
if "generated_questions" not in st.session_state:
    st.session_state.generated_questions = []
if "current_mode" not in st.session_state:
    st.session_state.current_mode = "Coding Questions"
if "show_final_results" not in st.session_state:
    st.session_state.show_final_results = False
if "test_session_active" not in st.session_state:
    st.session_state.test_session_active = False
if "final_results_compiled" not in st.session_state:
    st.session_state.final_results_compiled = False
if "candidate_linkedin_url" not in st.session_state:
    st.session_state.candidate_linkedin_url = ""
if "candidate_github_url" not in st.session_state:
    st.session_state.candidate_github_url = ""
if "candidate_kaggle_id" not in st.session_state:
    st.session_state.candidate_kaggle_id = ""
if "candidate_portfolio_url" not in st.session_state:
    st.session_state.candidate_portfolio_url = ""
if "resume_raw_text" not in st.session_state:
    st.session_state.resume_raw_text = ""
if "extracted_skills_dict" not in st.session_state:
    st.session_state.extracted_skills_dict = {}
if "extracted_projects" not in st.session_state:
    st.session_state.extracted_projects = []
if "device_check_passed" not in st.session_state:     
    st.session_state.device_check_passed = False      
if "current_coding_idx" not in st.session_state:
    st.session_state.current_coding_idx = 0
if "responses_vault" not in st.session_state:
    st.session_state.responses_vault = {f"tx-{k}": "" for k in range(10)}
if "saved_status_vault" not in st.session_state:
    st.session_state.saved_status_vault = {f"tx-{k}": False for k in range(10)}
if "coding_solutions_vault" not in st.session_state:
    st.session_state.coding_solutions_vault = {f"code-{k}": "" for k in range(5)}
if "coding_saved_vault" not in st.session_state:
    st.session_state.coding_saved_vault = {f"code-{k}": False for k in range(5)}
if "coding_execution_logs" not in st.session_state:
    st.session_state.coding_execution_logs = {f"code-{k}": "" for k in range(5)}
if "coding_language_vault" not in st.session_state:
    st.session_state.coding_language_vault = {f"lang-{k}": "Python" for k in range(5)}
if "coding_grade_results" not in st.session_state:
    st.session_state.coding_grade_results = {}
if "coding_evaluations" not in st.session_state:
    st.session_state.coding_evaluations = {}

if "saved_target_company" not in st.session_state:
    st.session_state.saved_target_company = "Google"
if "saved_selected_subject" not in st.session_state:
    st.session_state.saved_selected_subject = "DSA"

if "hr_questions" not in st.session_state:
    st.session_state.hr_questions = []
if "hr_responses_vault" not in st.session_state:
    st.session_state.hr_responses_vault = {}
if "hr_results_compiled" not in st.session_state:
    st.session_state.hr_results_compiled = False
if "hr_total_score" not in st.session_state:
    st.session_state.hr_total_score = 0
if "hr_percent" not in st.session_state:
    st.session_state.hr_percent = 0.0
if "hr_audit_logs" not in st.session_state:
    st.session_state.hr_audit_logs = []
if "hr_report" not in st.session_state:
    st.session_state.hr_report = {}
if "placement_readiness_score" not in st.session_state:
    st.session_state.placement_readiness_score = 0.0
    
for _k in ("coding_final_perc", "theory_final_perc", "security_notice"):
    st.session_state.setdefault(_k, None)
st.session_state.setdefault("_proctor_live", False)


def _proctor_should_be_active():
    """Proctoring is armed only during the live, proctored parts of the flow."""
    step = st.session_state.wizard_step
    if step == 5:
        return bool(
            st.session_state.device_check_passed
            and not st.session_state.final_results_compiled
        )
    if step == 6:
        return not st.session_state.hr_results_compiled
    return False


def _release_proctor_lock():
    """Disarms monitoring, removes the proctor bar / camera box / overlay,
    stops the camera and leaves full-screen."""
    st.components.v1.html(
        """
        <script>
        (function () {
            try {
                var P = window.parent, D = P.document, S = P.__proctorS;
                if (S) {
                    if (S.armed && !S.terminated) {
                        try {
                            P.sessionStorage.setItem("__proctorFinal", JSON.stringify({
                                score: 100, violations: S.violations || [],
                                reasons: S.reasons || [], terminated: false }));
                        } catch (e) {}
                    }
                    S.armed = false;
                }
                ["secure-workspace-bar", "cam-container", "__proctor_overlay"].forEach(function (id) {
                    var n = D.getElementById(id); if (n) n.remove();
                });
                var s = P.__globalCamStream;
                if (s) { try { s.getTracks().forEach(function (t) { t.stop(); }); } catch (e) {} }
                P.__globalCamStream = null;
                var fs = D.fullscreenElement || D.webkitFullscreenElement || D.mozFullScreenElement;
                if (fs) {
                    var xf = D.exitFullscreen || D.webkitExitFullscreen || D.mozCancelFullScreen;
                    if (xf) xf.call(D);
                }
            } catch (e) {}
        })();
        </script>
        """,
        height=0,
    )


def _sync_proctor_state():
    """Runs on every rerun: if proctoring is live but should no longer be, release it."""
    if st.session_state.get("_proctor_live") and not _proctor_should_be_active():
        _release_proctor_lock()
        st.session_state["_proctor_live"] = False


def _apply_security_wizard_reset(is_violation: bool):
    st.session_state.generated_questions = []
    st.session_state.current_mode = "Coding Questions"
    st.session_state.show_final_results = False
    st.session_state.test_session_active = False
    st.session_state.final_results_compiled = False
    st.session_state.current_coding_idx = 0
    st.session_state.responses_vault = {f"tx-{k}": "" for k in range(10)}
    st.session_state.saved_status_vault = {f"tx-{k}": False for k in range(10)}
    st.session_state.coding_solutions_vault = {f"code-{k}": "" for k in range(5)}
    st.session_state.coding_saved_vault = {f"code-{k}": False for k in range(5)}
    st.session_state.coding_execution_logs = {f"code-{k}": "" for k in range(5)}
    st.session_state.coding_language_vault = {f"lang-{k}": "Python" for k in range(5)}
    st.session_state.coding_grade_results = {}
    st.session_state.coding_evaluations = {}
    st.session_state.hr_questions = []
    st.session_state.hr_responses_vault = {}
    st.session_state.hr_results_compiled = False
    st.session_state.hr_total_score = 0
    st.session_state.hr_percent = 0.0
    st.session_state.hr_audit_logs = []
    st.session_state.hr_report = {}
    st.session_state.placement_readiness_score = 0.0
    st.session_state.coding_final_perc = None
    st.session_state.theory_final_perc = None
    st.session_state[_PROCTOR_NONCE_KEY] = int(time.time() * 1000)
    st.session_state.device_check_passed = False
    # The next run's _sync_proctor_state() releases camera / full-screen / overlay.
    st.session_state["_proctor_live"] = True

    if is_violation:
        st.session_state.wizard_step = 4
        st.session_state.selected_module = None
        st.session_state.security_notice = (
            "🚨 Your previous assessment was terminated by the proctoring system "
            "(full-screen exit, camera off/blank, or face not visible). "
            "Please choose a mode below to begin a new attempt."
        )
    else:
        st.session_state.wizard_step = 1
        st.session_state.identified_role = None
        st.session_state.selected_module = None
    st.rerun()

if "violation" in st.query_params or "restart_required" in st.query_params:
    is_violation = "violation" in st.query_params
    st.query_params.clear()
    _apply_security_wizard_reset(is_violation)

# -------------------------------------------------------------------------
# PRODUCT DATABASE ENGINE
# -------------------------------------------------------------------------
DB_PATH = "interview_prep.db"
COMPANY_HIRE_VAULT_FILE = "company_hiring_vault.json"


@st.cache_resource(show_spinner=False)
def initialize_company_vault():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS company_interview_vault (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            track TEXT NOT NULL,
            company TEXT NOT NULL,
            prompt TEXT NOT NULL,
            sample_input TEXT NOT NULL,
            sample_output TEXT NOT NULL,
            test_cases TEXT NOT NULL
        )
    """)
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM company_interview_vault")
    count = cursor.fetchone()[0]

    # Use the new company_hiring_vault.json to seed the database
    if count < 50 and os.path.exists(COMPANY_HIRE_VAULT_FILE):
        st.toast(
            "⚙️ Product Engine: Seeding question vault into local database..."
        )
        try:
            with open(COMPANY_HIRE_VAULT_FILE, "r", encoding="utf-8") as f:
                vault_data = json.load(f)
                questions = vault_data.get("training_question_bank", [])

            for q in questions:
                test_cases_str = (
                    json.dumps(q["test_cases"])
                    if isinstance(q.get("test_cases"), (list, dict))
                    else str(q.get("test_cases", "[]"))
                )

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO company_interview_vault 
                    (id, title, difficulty, track, company, prompt, sample_input, sample_output, test_cases)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        q.get("id"),
                        q.get("title"),
                        q.get("difficulty", "Medium"),
                        q.get("track", "Full Stack Developer"),
                        q.get("company", "Google"),
                        q.get("prompt", ""),
                        q.get("sample_input", "N/A"),
                        q.get("sample_output", "N/A"),
                        test_cases_str,
                    ),
                )
            conn.commit()
        except Exception as err:
            print(f"Error seeding database: {err}")

    conn.close()
    return True


initialize_company_vault()

# ⚡ VALHALLA DISTILBART ZERO-SHOT ROLE CLASSIFIER
@st.cache_resource
def load_distilbert_resume_classifier():
    return pipeline(
        "zero-shot-classification", model="valhalla/distilbart-mnli-12-3"
    )


@st.cache_resource
def load_slm_core():
    from transformers import T5ForConditionalGeneration, T5Tokenizer

    model_path = "./saved_grading_model"
    tokenizer = T5Tokenizer.from_pretrained(model_path)
    model = T5ForConditionalGeneration.from_pretrained(model_path)
    return tokenizer, model


MNC_COMPANIES = [
    "Google",
    "Microsoft",
    "Amazon",
    "Meta",
    "TCS",
    "Infosys",
    "Wipro",
    "Accenture",
]
CS_SUBJECTS = ["Data Structures & Algorithms (DSA)", "Operating Systems (OS)"]
PROGRAMMING_LANGUAGES = ["Python", "C", "C++", "Java", "C#"]

SKILL_CATEGORIES = {
    "Programming Languages": ["Python", "C", "Java", "C++", "C#", "Rust", "SQL"],
    "Operating Systems": [
        "Windows",
        "Linux",
        "macOS",
        "System Administration",
        "System Configuration",
    ],
    "Database Management": [
        "SQL (MySQL, PostgreSQL)",
        "NoSQL (MongoDB)",
        "Data Querying",
        "Data Structuring",
    ],
    "Computer Networking": [],
    "Hardware Deployment": [],
    "Cloud Computing": ["Amazon Web Services (AWS)"],
    "Artificial Intelligence (AI) & Machine Learning": [],
    "Cybersecurity": [],
    "DevOps & Automation": [],
    "Data Science & Analytics": [],
    "Web Development": [],
    "Mobile Development": [],
}

ROLE_TAXONOMY_REQUIREMENTS = {
    "Full Stack Software Developer": [
        "Programming Languages",
        "Database Management",
        "Web Development",
        "DevOps & Automation",
    ],
    "Data Scientist / Machine Learning Engineer": [
        "Programming Languages",
        "Database Management",
        "Artificial Intelligence (AI) & Machine Learning",
        "Data Science & Analytics",
    ],
    "Backend Software Engineer": [
        "Programming Languages",
        "Database Management",
        "Web Development",
        "DevOps & Automation",
    ],
    "Frontend Web Developer": ["Programming Languages", "Web Development"],
    "DevOps / Cloud Engineer": [
        "Operating Systems",
        "Cloud Computing",
        "DevOps & Automation",
        "Computer Networking",
    ],
    "Cybersecurity Analyst": [
        "Programming Languages",
        "Operating Systems",
        "Computer Networking",
        "Cybersecurity",
    ],
    "UI/UX Designer": ["Web Development"],
}

ROLE_SUGGESTED_PROJECTS = {
    "Full Stack Software Developer": [
        "Collaborative Project Management SaaS",
        "E-Commerce Platform with Microfrontends",
        "Real-Time Workspace Chat Application",
        "Subscription-Based Content Platform",
        "Health and Fitness Tracking Hub",
    ],
    "Data Scientist / Machine Learning Engineer": [
        "End-to-End Predictive Maintenance Pipeline",
        "Multimodal RAG Customer Support Bot",
        "E-Commerce Real-Time Fraud Engine",
        "Medical Image Segmentation Interface",
        "Product Recommendation Engine",
    ],
    "Backend Software Engineer": [
        "High-Throughput Financial Ledger API",
        "Distributed Web Scraping Engine",
        "Centralized API Gateway & Rate Limiter",
        "Log Aggregation & Search Service",
        "Event-Driven Notification Orchestrator",
    ],
    "Frontend Web Developer": [
        "Performance-Optimized Finance Dashboard",
        "Offline-First Progressive Web App (PWA)",
        "Headless CMS Corporate Website",
        "Accessible Component Design System",
        "Interactive Data Visualization Map",
    ],
    "DevOps / Cloud Engineer": [
        "Automated GitOps CI/CD Deployment",
        "Multi-Environment Infrastructure-as-Code (IaC)",
        "Centralized Observability & Alerting Stack",
        "Serverless Event-Driven ETL Engine",
        "Zero-Trust Network Access Setup",
    ],
    "Cybersecurity Analyst": [
        "Enterprise SIEM Monitoring Hub",
        "Automated Vulnerability Scanner Pipeline",
        "Decentralized HoneyPot Threat Capture",
        "Zero-Knowledge Identity Vault",
        "Packet Analyzer & Incident Responder",
    ],
    "UI/UX Designer": [
        "Autonomous EV Charging Mobile App",
        "B2B Supply Chain Analytics Suite",
        "Telehealth Clinic Patient Portal",
        "FinTech Investment App for Beginners",
        "Local Eco-Tourism Booking Platform",
    ],
}

ROLE_PROJECT_KEYWORDS = {
    "Full Stack Software Developer": [
        "full stack",
        "fullstack",
        "react",
        "node",
        "mern",
        "web app",
        "frontend and backend",
        "flask",
        "html",
        "javascript",
    ],
    "Data Scientist / Machine Learning Engineer": [
        "machine learning",
        " ml ",
        "data science",
        "model",
        "prediction",
        "neural",
        "deep learning",
        "dataset",
        "classification",
        "regression",
        "ai ",
        "ai-ml",
        "svm",
        "classifier",
        "pyspark",
        "random forest",
    ],
    "Backend Software Engineer": [
        "backend",
        "api",
        "microservice",
        "server",
        "database design",
        "system design",
    ],
    "Frontend Web Developer": [
        "frontend",
        "front-end",
        "react",
        "ui",
        "website",
        "css",
        "html",
        "web app",
    ],
    "DevOps / Cloud Engineer": [
        "devops",
        "ci/cd",
        "docker",
        "kubernetes",
        "cloud",
        "aws",
        "azure",
        "infrastructure",
    ],
    "Cybersecurity Analyst": [
        "security",
        "cyber",
        "vulnerability",
        "penetration",
        "encryption",
        "firewall",
        "threat",
    ],
    "UI/UX Designer": [
        "ui/ux",
        "ux design",
        "ui design",
        "figma",
        "prototype",
        "wireframe",
        "usability",
    ],
}


def extract_text_from_pdf(uploaded_file):
    if uploaded_file is None:
        return ""
    try:
        reader = PdfReader(uploaded_file)
        text = "\n".join([page.extract_text() or "" for page in reader.pages])
        return text
    except Exception:
        return ""


def predict_role_distilbert(raw_text):
    classifier = load_distilbert_resume_classifier()
    text_snippet = raw_text[:1500] if len(raw_text) > 1500 else raw_text
    res = classifier(text_snippet, candidate_labels=IT_ROLES)
    return res["labels"][0]


import ollama
from pydantic import BaseModel, Field


class SkillCategory(BaseModel):
    category_name: str = Field(
        description="Subcategory name, e.g., 'Programming Languages', 'Tools & Platforms'"
    )
    skills: list[str] = Field(
        description="List of extracted individual skill items"
    )


class ProjectItem(BaseModel):
    project_title: str = Field(description="Exact title of the project")
    description: str = Field(
        description="Summary of the project work and technologies used"
    )


class ResumeParseResult(BaseModel):
    skills: list[SkillCategory] = Field(
        description="Categorized skills found in the resume"
    )
    projects: list[ProjectItem] = Field(
        description="All projects found in the resume with titles and descriptions"
    )


@st.cache_data(show_spinner=False)
def extract_resume_data_with_qwen(resume_text: str):
    if not resume_text or not resume_text.strip():
        return {}, []

    prompt = f"""
You are an expert ATS (Applicant Tracking System) parser.
Extract ALL skills (grouped under their sub-categories) and ALL projects (with their titles and brief descriptions) from the provided resume text.

Resume Text:
---
{resume_text}
---
"""

    try:
        response = ollama.chat(
            model="qwen2.5:7b-instruct",
            messages=[{"role": "user", "content": prompt}],
            format=ResumeParseResult.model_json_schema(),
            options={"temperature": 0.0, "num_ctx": 8192},
        )

        parsed = ResumeParseResult.model_validate_json(response.message.content)
        extracted_skills = {
            item.category_name: item.skills for item in parsed.skills
        }
        extracted_projects = [
            (p.project_title, p.description) for p in parsed.projects
        ]

        return extracted_skills, extracted_projects

    except Exception as e:
        print(f"Error extracting data with local Qwen2.5: {e}")
        return {}, []


def clean_question_title(raw_title):
    return re.sub(r"\s*-\s*Case\s*#\d+", "", raw_title, flags=re.IGNORECASE).strip()


def map_role_to_track_keyword(role_name):
    role_lower = str(role_name).lower()
    if "data" in role_lower or "machine learning" in role_lower:
        return "Data Science"
    elif "backend" in role_lower:
        return "Backend"
    elif "frontend" in role_lower or "ui/ux" in role_lower:
        return "Frontend"
    elif "devops" in role_lower or "cybersecurity" in role_lower:
        return "Full Stack"
    return "Full Stack"
def ensure_unique_questions(question_list, limit):
    """Helper to ensure questions are unique and strictly clipped to the required limit."""
    seen = set()
    unique_list = []
    for q in question_list:
        title = q.get("title") or q.get("question_title") or q.get("question")
        if title and title not in seen:
            seen.add(title)
            unique_list.append(q)
        if len(unique_list) >= limit:
            break
    return unique_list

def seed_500_questions(desired_role, predicted_role, selected_company):
    """Interview mode coding question loader: returns exactly 5 unique questions."""
    raw_pool = fetch_company_questions(selected_company, predicted_role, desired_role, total_count=10)
    return ensure_unique_questions(raw_pool, limit=5)

def ingest_leetcode(desired_role, predicted_role, selected_company):
    """Practice mode coding question loader: returns exactly 5 unique questions."""
    raw_pool = fetch_company_questions(selected_company, predicted_role, desired_role, total_count=10)
    return ensure_unique_questions(raw_pool, limit=5)

def ingest_all_coding(company, predicted_role, desired_role, subject_tag, count=10):
    """Theory question loader: returns exactly 10 unique theory questions."""
    raw_pool = select_theory_questions(company, predicted_role, desired_role, subject_tag, count=20)
    return ensure_unique_questions(raw_pool, limit=count)

def fetch_company_questions(company, predicted_role, desired_role, total_count=5):
    if not os.path.exists(DB_PATH):
        return []

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    pred_track = map_role_to_track_keyword(predicted_role)
    des_track = map_role_to_track_keyword(desired_role)

    # Fetch unique random questions matching company and track
    cursor.execute(
        """
        SELECT DISTINCT id, title, difficulty, track, company, prompt, sample_input, sample_output, test_cases 
        FROM company_interview_vault 
        WHERE (company LIKE ?) AND (track LIKE ? OR track LIKE ?)
        ORDER BY RANDOM() LIMIT ?
        """,
        (f"%{company}%", f"%{pred_track}%", f"%{des_track}%", total_count),
    )

    rows = cursor.fetchall()

    if len(rows) < total_count:
        needed = total_count - len(rows)
        existing_ids = tuple(r[0] for r in rows) if rows else (-1,)
        placeholders = ",".join("?" * len(existing_ids))
        
        cursor.execute(
            f"""
            SELECT DISTINCT id, title, difficulty, track, company, prompt, sample_input, sample_output, test_cases 
            FROM company_interview_vault 
            WHERE id NOT IN ({placeholders}) AND (track LIKE ? OR track LIKE ? OR company LIKE ?)
            ORDER BY RANDOM() LIMIT ?
            """,
            existing_ids + (f"%{pred_track}%", f"%{des_track}%", f"%{company}%", needed),
        )
        rows.extend(cursor.fetchall())

    conn.close()

    questions = []
    seen_titles = set()
    for r in rows:
        title = clean_question_title(r[1])
        if title not in seen_titles:
            seen_titles.add(title)
            questions.append({
                "id": r[0],
                "title": title,
                "difficulty": r[2],
                "tags": [r[3], r[4]],
                "company": r[4],
                "prompt": r[5],
                "sample_input": r[6],
                "sample_output": r[7],
                "test_cases": r[8],
                "target_alignment": r[3],
            })

    return questions[:total_count]


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_company_simulation_questions(company, total_count=5):
    """Fetches 5 random questions exclusively belonging to the user-selected company regardless of role/level."""
    if not os.path.exists(DB_PATH):
        return []

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, title, difficulty, track, company, prompt, sample_input, sample_output, test_cases 
        FROM company_interview_vault 
        WHERE company LIKE ?
        ORDER BY RANDOM() LIMIT ?
        """,
        (f"%{company}%", total_count),
    )

    rows = cursor.fetchall()

    # Fallback to any questions in the vault if company count in database is small
    if len(rows) < total_count:
        needed = total_count - len(rows)
        existing_ids = tuple(r[0] for r in rows) if rows else (-1,)
        placeholders = ",".join("?" * len(existing_ids))
        cursor.execute(
            f"""
            SELECT id, title, difficulty, track, company, prompt, sample_input, sample_output, test_cases 
            FROM company_interview_vault 
            WHERE id NOT IN ({placeholders})
            ORDER BY RANDOM() LIMIT ?
            """,
            existing_ids + (needed,),
        )
        rows.extend(cursor.fetchall())

    conn.close()

    questions = []
    for r in rows:
        questions.append({
            "id": r[0],
            "title": clean_question_title(r[1]),
            "difficulty": r[2],
            "tags": [r[3], r[4]],
            "company": r[4],
            "prompt": r[5],
            "sample_input": r[6],
            "sample_output": r[7],
            "test_cases": r[8],
            "target_alignment": r[3],
        })

    return questions[:total_count]


# =========================================================================
# LOCAL COMPILER & ONLINE JUDGE ENGINE
# =========================================================================

RUN_TIME_LIMIT_SECONDS = 3
COMPILE_TIME_LIMIT_SECONDS = 20
MEMORY_LIMIT_MB = 384
COMPILE_MEMORY_LIMIT_MB = 512

SUPPORTED_LANGUAGES = list(PROGRAMMING_LANGUAGES)

LANGUAGE_TEMPLATES = {
    "Python": 'def solve():\n    pass\n\nif __name__ == "__main__":\n    solve()\n',
    "C": '#include <stdio.h>\n\nint main() {\n    return 0;\n}\n',
    "C++": '#include <iostream>\nusing namespace std;\n\nint main() {\n    return 0;\n}\n',
    "Java": 'public class Main {\n    public static void main(String[] args) {\n\n    }\n}\n',
    "C#": 'using System;\n\nclass Program {\n    static void Main() {\n\n    }\n}\n',
}

LANGUAGE_CODE_BLOCK_LABELS = {
    "Python": "python",
    "C": "c",
    "C++": "cpp",
    "Java": "java",
    "C#": "csharp",
}

VERDICT_LABELS = {
    "accepted": "✅ Accepted",
    "wrong_answer": "❌ Wrong Answer",
    "compile_error": "❌ Compilation Error",
    "runtime_error": "❌ Runtime Error",
    "time_limit_exceeded": "⏰ Time Limit Exceeded",
    "memory_limit_exceeded": "🧠 Memory Limit Exceeded",
    "tool_missing": "⚠️ Compiler Not Found",
    "internal_error": "⚠️ Judge Error",
}


def _which_any(*names):
    for name in names:
        path = shutil.which(name)
        if path:
            return path
    return None


@st.cache_resource(show_spinner=False)
def _detect_toolchains():
    tools = {"python": sys.executable}
    tools["gcc"] = _which_any("gcc", "cc", "clang", "tcc")
    tools["gpp"] = _which_any("g++", "c++", "clang++", "gcc")
    tools["javac"] = _which_any("javac")
    tools["java"] = _which_any("java")
    tools["dotnet"] = _which_any("dotnet")
    tools["mono_csc"] = _which_any("csc")
    tools["mcs"] = _which_any("mcs")
    tools["mono"] = _which_any("mono")
    tools["netfx_csc"] = None
    if sys.platform == "win32":
        for base in (
            r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319",
            r"C:\Windows\Microsoft.NET\Framework\v4.0.30319",
        ):
            candidate = os.path.join(base, "csc.exe")
            if os.path.exists(candidate):
                tools["netfx_csc"] = candidate
                break
    return tools


def language_availability(language):
    tools = _detect_toolchains()
    if language == "Python":
        return True, ""
    if language in ("C", "C++"):
        key = "gcc" if language == "C" else "gpp"
        if tools.get(key):
            return True, ""
        return False, f"{language} compiler (gcc/g++) was not found on this machine."
    if language == "Java":
        if tools.get("javac") and tools.get("java"):
            return True, ""
        return False, "Java JDK (javac/java) was not found on this machine."
    if language == "C#":
        if any(tools.get(k) for k in ("dotnet", "mono_csc", "mcs", "netfx_csc")):
            return True, ""
        return False, "C# toolchain (dotnet/mono/csc) was not found on this machine."
    return False, f"Unsupported language: {language}"


def _get_pid_memory_mb(pid):
    if not pid:
        return 0.0
    if sys.platform == "win32":
        try:
            from ctypes import Structure, byref, c_int, c_size_t, c_uint32, c_ulong, c_void_p, sizeof

            class PROCESS_MEMORY_COUNTERS(Structure):
                _fields_ = [
                    ("cb", c_ulong),
                    ("PageFaultCount", c_ulong),
                    ("PeakWorkingSetSize", c_size_t),
                    ("WorkingSetSize", c_size_t),
                    ("QuotaPeakPagedPoolUsage", c_size_t),
                    ("QuotaPagedPoolUsage", c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", c_size_t),
                    ("QuotaNonPagedPoolUsage", c_size_t),
                    ("PagefileUsage", c_size_t),
                    ("PeakPagefileUsage", c_size_t),
                ]

            kernel32 = ctypes.windll.kernel32
            psapi = ctypes.windll.psapi
            kernel32.OpenProcess.restype = c_void_p
            kernel32.OpenProcess.argtypes = [c_uint32, c_int, c_uint32]
            kernel32.CloseHandle.restype = c_int
            kernel32.CloseHandle.argtypes = [c_void_p]
            psapi.GetProcessMemoryInfo.restype = c_int
            psapi.GetProcessMemoryInfo.argtypes = [c_void_p, c_void_p, c_uint32]

            PROCESS_QUERY_INFORMATION = 0x0400
            PROCESS_VM_READ = 0x0010
            handle = kernel32.OpenProcess(
                PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid
            )
            if not handle:
                return 0.0
            try:
                counters = PROCESS_MEMORY_COUNTERS()
                counters.cb = sizeof(PROCESS_MEMORY_COUNTERS)
                if psapi.GetProcessMemoryInfo(handle, byref(counters), counters.cb):
                    return counters.PagefileUsage / (1024.0 * 1024.0)
            finally:
                kernel32.CloseHandle(handle)
        except Exception:
            return 0.0
        return 0.0
    try:
        with open(f"/proc/{pid}/status", "r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("VmRSS:"):
                    return float(line.split()[1]) / 1024.0
    except Exception:
        try:
            probe = subprocess.run(
                ["ps", "-o", "rss=", "-p", str(pid)],
                capture_output=True,
                text=True,
                timeout=5,
            )
            raw = probe.stdout.strip()
            if raw:
                return float(raw) / 1024.0
        except Exception:
            pass
    return 0.0


def _kill_process_tree(proc):
    if proc is None or proc.poll() is not None:
        return
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                capture_output=True,
                timeout=10,
            )
            return
        except Exception:
            pass
    else:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            return
        except Exception:
            pass
    try:
        proc.kill()
    except Exception:
        pass


def _memory_watcher(proc, limit_mb, stop_event, outcome):
    try:
        while not stop_event.is_set():
            if proc.poll() is not None:
                break
            try:
                used_mb = _get_pid_memory_mb(proc.pid)
            except Exception:
                used_mb = 0.0
            if used_mb > limit_mb:
                outcome["exceeded"] = True
                _kill_process_tree(proc)
                stop_event.set()
                return
            time.sleep(0.05)
    except Exception:
        pass


def _run_child(argv, stdin_data, cwd, timeout_sec, mem_limit_mb, tmpdir=""):
    result = {
        "stdout": "",
        "stderr": "",
        "exit_code": 0,
        "status": "completed",
        "tmpdir": tmpdir,
    }
    child_env = dict(os.environ)
    child_env.setdefault("PYTHONIOENCODING", "utf-8")
    child_env.setdefault("PYTHONUTF8", "1")
    creationflags = 0
    if sys.platform == "win32":
        creationflags = (
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | 0x08000000
        )
    try:
        proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=child_env,
            creationflags=creationflags,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        result["status"] = "tool_missing"
        result["message"] = f"Required compiler/runtime executable was not found: {argv[0]}"
        return result
    except Exception as exc:
        result["status"] = "internal_error"
        result["message"] = f"Failed to launch process: {exc}"
        return result

    stop_event = threading.Event()
    outcome = {"exceeded": False}
    watcher = threading.Thread(
        target=_memory_watcher,
        args=(proc, mem_limit_mb, stop_event, outcome),
        daemon=True,
    )
    watcher.start()
    try:
        out_text, err_text = proc.communicate(
            input=stdin_data or "", timeout=timeout_sec
        )
        result["stdout"] = out_text or ""
        result["stderr"] = err_text or ""
        result["exit_code"] = proc.returncode if proc.returncode is not None else 0
    except subprocess.TimeoutExpired:
        _kill_process_tree(proc)
        stop_event.set()
        try:
            out_text, err_text = proc.communicate(timeout=5)
        except Exception:
            out_text, err_text = "", ""
        result["stdout"] = out_text or ""
        result["stderr"] = err_text or ""
        result["status"] = "time_limit_exceeded"
        return result
    finally:
        stop_event.set()
        watcher.join(timeout=1)

    if outcome["exceeded"]:
        _kill_process_tree(proc)
        result["status"] = "memory_limit_exceeded"
        return result
    result["status"] = "completed"
    return result


def _write_file(path, content):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def _compile_then_run(tmpdir, compile_cmd, run_cmd, stdin_data, timeout_sec, mem_limit_mb):
    compile_result = _run_child(
        compile_cmd,
        "",
        tmpdir,
        COMPILE_TIME_LIMIT_SECONDS,
        COMPILE_MEMORY_LIMIT_MB,
        tmpdir=tmpdir,
    )
    if compile_result["status"] == "tool_missing":
        return compile_result
    if compile_result["status"] == "time_limit_exceeded":
        return {
            "status": "compile_error",
            "stderr": "Compilation timed out.",
            "stdout": "",
            "exit_code": 0,
            "tmpdir": tmpdir,
        }
    if compile_result["status"] == "memory_limit_exceeded":
        return {
            "status": "compile_error",
            "stderr": "Compilation exceeded the memory limit.",
            "stdout": "",
            "exit_code": 0,
            "tmpdir": tmpdir,
        }
    if compile_result["status"] == "internal_error":
        return compile_result
    if compile_result["exit_code"] != 0:
        message = compile_result.get("stderr") or compile_result.get("stdout") or ""
        return {
            "status": "compile_error",
            "stderr": message,
            "stdout": "",
            "exit_code": 0,
            "tmpdir": tmpdir,
        }
    warnings_text = (compile_result.get("stderr") or "").strip()
    run_result = _run_child(
        run_cmd, stdin_data, tmpdir, timeout_sec, mem_limit_mb, tmpdir=tmpdir
    )
    run_result["warnings"] = warnings_text
    return run_result


def _run_python_solution(tmpdir, code, stdin_data, timeout_sec, mem_limit_mb):
    src = os.path.join(tmpdir, "solution.py")
    _write_file(src, code)
    try:
        compile(code, "solution.py", "exec")
    except SyntaxError as exc:
        line_no = exc.lineno or 0
        return {
            "status": "compile_error",
            "stderr": f"{exc.__class__.__name__}: {exc.msg} (line {line_no})",
            "stdout": "",
            "exit_code": 0,
            "tmpdir": tmpdir,
        }
    python_exe = getattr(sys, "_base_executable", None) or sys.executable
    return _run_child(
        [python_exe, "-B", "-u", src],
        stdin_data,
        tmpdir,
        timeout_sec,
        mem_limit_mb,
        tmpdir=tmpdir,
    )


def _run_c_solution(tmpdir, code, stdin_data, timeout_sec, mem_limit_mb):
    tools = _detect_toolchains()
    if not tools.get("gcc"):
        return {
            "status": "tool_missing",
            "message": "C compiler (gcc/cc/clang) was not found on this machine.",
            "tmpdir": tmpdir,
        }
    src = os.path.join(tmpdir, "solution.c")
    exe = os.path.join(
        tmpdir, "solution" + (".exe" if sys.platform == "win32" else "")
    )
    _write_file(src, code)
    return _compile_then_run(
        tmpdir,
        [tools["gcc"], "-std=c11", "-O2", "-Wall", "-Wextra", "-o", exe, src],
        [exe],
        stdin_data,
        timeout_sec,
        mem_limit_mb,
    )


def _run_cpp_solution(tmpdir, code, stdin_data, timeout_sec, mem_limit_mb):
    tools = _detect_toolchains()
    if not tools.get("gpp"):
        return {
            "status": "tool_missing",
            "message": "C++ compiler (g++/c++/clang++) was not found on this machine.",
            "tmpdir": tmpdir,
        }
    src = os.path.join(tmpdir, "solution.cpp")
    exe = os.path.join(
        tmpdir, "solution" + (".exe" if sys.platform == "win32" else "")
    )
    _write_file(src, code)
    return _compile_then_run(
        tmpdir,
        [tools["gpp"], "-std=c++17", "-O2", "-Wall", "-Wextra", "-o", exe, src],
        [exe],
        stdin_data,
        timeout_sec,
        mem_limit_mb,
    )


def _run_java_solution(tmpdir, code, stdin_data, timeout_sec, mem_limit_mb):
    tools = _detect_toolchains()
    if not (tools.get("javac") and tools.get("java")):
        return {
            "status": "tool_missing",
            "message": "Java JDK (javac/java) was not found on this machine.",
            "tmpdir": tmpdir,
        }
    src = os.path.join(tmpdir, "Main.java")
    classes_dir = os.path.join(tmpdir, "classes")
    os.makedirs(classes_dir, exist_ok=True)
    _write_file(src, code)
    heap_mb = max(64, min(int(MEMORY_LIMIT_MB // 2), 128))
    return _compile_then_run(
        tmpdir,
        [tools["javac"], "-encoding", "UTF-8", "-d", classes_dir, src],
        [tools["java"], f"-Xmx{heap_mb}m", "-cp", classes_dir, "Main"],
        stdin_data,
        timeout_sec,
        mem_limit_mb,
    )


def _dotnet_target_framework(tools):
    if not tools.get("dotnet"):
        return None
    try:
        probe = subprocess.run(
            [tools["dotnet"], "--list-runtimes"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        matches = re.findall(
            r"Microsoft\.NETCore\.App (\d+)\.(\d+)", probe.stdout or ""
        )
        if matches:
            major, minor = max((int(m), int(n)) for m, n in matches)
            return f"net{major}.{minor}"
    except Exception:
        pass
    return None


def _run_csharp_solution(tmpdir, code, stdin_data, timeout_sec, mem_limit_mb):
    tools = _detect_toolchains()
    src = os.path.join(tmpdir, "Program.cs")
    exe = os.path.join(tmpdir, "Program.exe")
    _write_file(src, code)

    csc = tools.get("netfx_csc") or tools.get("mono_csc")
    if csc:
        compile_cmd = [csc, "/nologo", f"/out:{exe}", src]
        if tools.get("netfx_csc"):
            run_cmd = [exe]
        else:
            if not tools.get("mono"):
                return {
                    "status": "tool_missing",
                    "message": "Mono runtime (mono) was not found to run C# programs.",
                    "tmpdir": tmpdir,
                }
            run_cmd = [tools["mono"], exe]
        return _compile_then_run(
            tmpdir, compile_cmd, run_cmd, stdin_data, timeout_sec, mem_limit_mb
        )

    if tools.get("mcs"):
        if not tools.get("mono"):
            return {
                "status": "tool_missing",
                "message": "Mono runtime (mono) was not found to run C# programs.",
                "tmpdir": tmpdir,
            }
        return _compile_then_run(
            tmpdir,
            [tools["mcs"], f"-out:{exe}", src],
            [tools["mono"], exe],
            stdin_data,
            timeout_sec,
            mem_limit_mb,
        )

    if tools.get("dotnet"):
        target = _dotnet_target_framework(tools)
        if not target:
            return {
                "status": "tool_missing",
                "message": "Could not detect an installed .NET runtime to target.",
                "tmpdir": tmpdir,
            }
        _write_file(
            os.path.join(tmpdir, "Program.csproj"),
            (
                '<Project Sdk="Microsoft.NET.Sdk">\n'
                '  <PropertyGroup>\n'
                f"    <TargetFramework>{target}</TargetFramework>\n"
                "    <OutputType>Exe</OutputType>\n"
                "    <AssemblyName>Program</AssemblyName>\n"
                "    <ImplicitUsings>disable</ImplicitUsings>\n"
                "    <Nullable>disable</Nullable>\n"
                "    <GenerateAssemblyInfo>false</GenerateAssemblyInfo>\n"
                "  </PropertyGroup>\n"
                "</Project>\n"
            ),
        )
        build_result = _run_child(
            [
                tools["dotnet"],
                "build",
                tmpdir,
                "-c",
                "Release",
                "--nologo",
                "-o",
                os.path.join(tmpdir, "bin"),
            ],
            "",
            tmpdir,
            COMPILE_TIME_LIMIT_SECONDS,
            COMPILE_MEMORY_LIMIT_MB,
            tmpdir=tmpdir,
        )
        if build_result["status"] != "completed" or build_result["exit_code"] != 0:
            return {
                "status": "compile_error",
                "stderr": (
                    build_result.get("stderr") or build_result.get("stdout") or ""
                ),
                "stdout": "",
                "exit_code": 0,
                "tmpdir": tmpdir,
            }
        run_result = _run_child(
            [os.path.join(tmpdir, "bin", "Program.exe")],
            stdin_data,
            tmpdir,
            timeout_sec,
            mem_limit_mb,
            tmpdir=tmpdir,
        )
        run_result["warnings"] = (build_result.get("stderr") or "").strip()
        return run_result

    return {
        "status": "tool_missing",
        "message": "C# toolchain (dotnet/mono/csc) was not found on this machine.",
        "tmpdir": tmpdir,
    }


def run_code_with_test(language, code, stdin_data, timeout_sec=None, mem_limit_mb=None):
    timeout_sec = timeout_sec or RUN_TIME_LIMIT_SECONDS
    mem_limit_mb = mem_limit_mb or MEMORY_LIMIT_MB
    tmpdir = tempfile.mkdtemp(prefix="judge_")
    try:
        if language == "Python":
            return _run_python_solution(tmpdir, code, stdin_data, timeout_sec, mem_limit_mb)
        if language == "C":
            return _run_c_solution(tmpdir, code, stdin_data, timeout_sec, mem_limit_mb)
        if language == "C++":
            return _run_cpp_solution(tmpdir, code, stdin_data, timeout_sec, mem_limit_mb)
        if language == "Java":
            return _run_java_solution(tmpdir, code, stdin_data, timeout_sec, mem_limit_mb)
        if language == "C#":
            return _run_csharp_solution(tmpdir, code, stdin_data, timeout_sec, mem_limit_mb)
        return {
            "status": "internal_error",
            "message": f"Unsupported language: {language}",
            "tmpdir": tmpdir,
        }
    except Exception as exc:
        return {"status": "internal_error", "message": str(exc), "tmpdir": tmpdir}
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _clean_test_data(value):
    if value is None:
        return ""
    text = str(value).strip()
    if not text or text.upper() == "N/A":
        return ""
    return text


def normalize_output_lines(text):
    lines = (text or "").split("\n")
    cleaned = [line.rstrip() for line in lines]
    while cleaned and cleaned[-1] == "":
        cleaned.pop()
    return cleaned


def outputs_match(actual, expected):
    return normalize_output_lines(actual) == normalize_output_lines(expected)


def judge_code(language, code, stdin_data, expected_output, timeout_sec=None, mem_limit_mb=None):
    stdin_data = _clean_test_data(stdin_data)
    expected_output = _clean_test_data(expected_output)
    result = run_code_with_test(language, code, stdin_data, timeout_sec, mem_limit_mb)
    status = result.get("status")
    if status == "completed":
        if result.get("exit_code") != 0:
            status = "runtime_error"
        elif not expected_output:
            status = "accepted"
        elif outputs_match(result.get("stdout", ""), expected_output):
            status = "accepted"
        else:
            status = "wrong_answer"
    result["status"] = status
    result["expected"] = expected_output
    result["stdin"] = stdin_data
    return result


def _clean_temp_paths(text, tmpdir=""):
    if not text:
        return text
    if tmpdir:
        text = text.replace(tmpdir, "")
        text = text.replace(tmpdir.replace("\\", "/"), "")
    text = re.sub(
        r"[A-Za-z]:[\\/](?:[^\\/\"']*[\\/])*judge_[\w]+[\\/]?", "", text
    )
    return text


def _truncate(text, limit=4000):
    if text and len(text) > limit:
        return text[:limit] + "\n... [output truncated]"
    return text


def format_runtime_error(language, result):
    text = (result.get("stderr") or "") or (result.get("stdout") or "")
    tmpdir = result.get("tmpdir", "")
    text = _clean_temp_paths(text, tmpdir).strip()
    lines = [ln for ln in text.splitlines() if ln.strip()]
    exit_code = result.get("exit_code")

    if language == "Python":
        if lines:
            last = lines[-1]
            if "Traceback" in text or "Error" in last or "Exception" in last:
                location = ""
                for ln in reversed(lines[:-1]):
                    if "solution.py" in ln:
                        match = re.search(r"line (\d+)", ln)
                        if match:
                            location = f" (line {match.group(1)})"
                        break
                return f"Runtime Error{location}: {last}"
            return f"Runtime Error: {last}"
        return "Runtime Error."

    if language in ("C", "C++"):
        crash_messages = {
            -1073741819: "Segmentation fault (invalid memory access).",
            0xC0000005: "Segmentation fault (invalid memory access).",
            139: "Segmentation fault (invalid memory access).",
            -1073741676: "Integer division by zero.",
            0xC0000094: "Integer division by zero.",
            -1073740791: "Stack overflow (infinite recursion).",
            0xC00000FD: "Stack overflow (infinite recursion).",
        }
        if exit_code in crash_messages:
            return crash_messages[exit_code]
        lower = text.lower()
        if "segmentation" in lower or "segfault" in lower:
            return "Segmentation fault (invalid memory access)."
        if "terminate called" in lower or "what()" in lower:
            what_line = next(
                (ln for ln in reversed(lines) if "what()" in ln),
                lines[-1] if lines else "",
            )
            return f"Uncaught C++ exception: {what_line}"
        if exit_code in (3, 134) or "abort" in lower:
            return "Program aborted (uncaught exception or std::abort)."
        if lines:
            return f"Runtime Error: {lines[-1]}"
        return f"Runtime Error (exit code {exit_code})."

    if language == "Java":
        exc_line = next(
            (ln for ln in lines if "Exception" in ln or "Error:" in ln), ""
        )
        frame_line = next((ln for ln in lines if "Main.java:" in ln), "")
        if exc_line:
            message = f"Runtime Error: {exc_line.strip()}"
            if frame_line:
                message += f" at {frame_line.strip()}"
            return message
        return f"Runtime Error: {text or '(no details)'}"

    if language == "C#":
        exc_line = next(
            (ln for ln in lines if "Exception" in ln or "Unhandled" in ln), ""
        )
        if exc_line:
            return f"Runtime Error: {exc_line.strip()}"
        return f"Runtime Error: {text or '(no details)'}"

    return "Runtime Error."


def format_judge_result(language, result):
    status = result.get("status", "internal_error")
    label = VERDICT_LABELS.get(status, status)
    parts = [label]
    stderr = result.get("stderr", "") or ""
    stdout = result.get("stdout", "") or ""
    tmpdir = result.get("tmpdir", "")
    if status == "compile_error":
        message = _clean_temp_paths(stderr, tmpdir).strip()
        parts.append("Compilation output:")
        parts.append(_truncate(message) or "The compiler reported an error.")
    elif status == "wrong_answer":
        parts.append("Expected output:")
        parts.append(_clean_temp_paths(result.get("expected", ""), tmpdir) or "(empty)")
        parts.append("Your output:")
        parts.append(_clean_temp_paths(stdout, tmpdir).strip() or "(empty)")
    elif status == "accepted":
        if stdout.strip():
            parts.append("Program output:")
            parts.append(_truncate(stdout.rstrip()))
    elif status == "runtime_error":
        parts.append(format_runtime_error(language, result))
        if stdout.strip():
            parts.append("Program output before exit:")
            parts.append(_truncate(stdout.rstrip()))
    elif status == "time_limit_exceeded":
        parts.append(
            f"Program exceeded the {RUN_TIME_LIMIT_SECONDS}s time limit and was terminated."
        )
    elif status == "memory_limit_exceeded":
        parts.append(
            f"Program exceeded the {MEMORY_LIMIT_MB} MB memory limit and was terminated."
        )
    else:
        parts.append(result.get("message") or label)
    warnings = result.get("warnings", "")
    if warnings:
        parts.append("Compiler warnings:")
        parts.append(_clean_temp_paths(warnings, tmpdir).strip())
    return "\n".join(parts)


def parse_test_cases(raw):
    data = raw
    if isinstance(data, str):
        data = data.strip()
        if not data or data.lower() == "null":
            return []
        try:
            data = json.loads(data)
        except Exception:
            return []
    if isinstance(data, dict):
        for key in ("test_cases", "cases", "tests", "hidden_tests"):
            if key in data:
                data = data[key]
                break
    if not isinstance(data, list):
        return []
    cases = []
    for item in data:
        if isinstance(item, dict):
            stdin_text = next(
                (
                    item[k]
                    for k in ("input", "stdin", "test_input", "sample_input", "in")
                    if k in item
                ),
                "",
            )
            expected_text = next(
                (
                    item[k]
                    for k in ("output", "expected", "test_output", "sample_output", "out")
                    if k in item
                ),
                "",
            )
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            stdin_text, expected_text = item[0], item[1]
        else:
            continue
        if stdin_text is None:
            stdin_text = ""
        if expected_text is None:
            expected_text = ""
        cases.append(
            (_clean_test_data(stdin_text), _clean_test_data(expected_text))
        )
    return cases


def run_hidden_test_cases(language, code, raw_test_cases, timeout_sec=None, mem_limit_mb=None):
    cases = parse_test_cases(raw_test_cases)
    if not cases:
        return {"status": "no_tests", "passed": 0, "total": 0, "cases": []}
    results = [
        judge_code(language, code, stdin_data, expected, timeout_sec, mem_limit_mb)
        for stdin_data, expected in cases
    ]
    passed = sum(1 for r in results if r.get("status") == "accepted")
    overall = "accepted" if passed == len(results) else "failed"
    return {"status": overall, "passed": passed, "total": len(results), "cases": results}


def format_hidden_tests_result(language, hidden_result):
    if hidden_result["status"] == "no_tests":
        return "No hidden test cases available for this question."
    parts = [
        f"{hidden_result['passed']} / {hidden_result['total']} hidden test cases passed"
    ]
    for index, case in enumerate(hidden_result["cases"], start=1):
        status = case.get("status")
        parts.append(f"Test {index}: {VERDICT_LABELS.get(status, status)}")
        if status == "wrong_answer":
            parts.append(
                "   Expected : "
                + (
                    _clean_temp_paths(case.get("expected", ""), case.get("tmpdir", ""))
                    or "(empty)"
                )
            )
            parts.append(
                "   Received : "
                + (
                    _clean_temp_paths(case.get("stdout", ""), case.get("tmpdir", "")).strip()
                    or "(empty)"
                )
            )
        elif status == "runtime_error":
            parts.append("   " + format_runtime_error(language, case))
        elif status == "compile_error":
            parts.append(
                "   "
                + _clean_temp_paths(
                    case.get("stderr", ""), case.get("tmpdir", "")
                ).strip()
            )
        elif status == "time_limit_exceeded":
            parts.append(f"   Exceeded the {RUN_TIME_LIMIT_SECONDS}s time limit.")
        elif status == "memory_limit_exceeded":
            parts.append(f"   Exceeded the {MEMORY_LIMIT_MB} MB memory limit.")
    return "\n".join(parts)


def is_empty_solution(code, language):
    if not code:
        return True
    text = code.strip()
    if not text:
        return True
    template = (LANGUAGE_TEMPLATES.get(language) or "").strip()
    if template and text == template:
        return True
    lines = [ln.strip() for ln in text.splitlines()]
    if lines and all(
        ln.startswith(("#", "//", "/*", "*", "*/")) for ln in lines
    ):
        return True
    return False


# =========================================================================
# 2. OFFLINE RECRUITER EVALUATION ENGINE
# =========================================================================

RECRUITER_METRICS = [
    ("Correctness", 40),
    ("Time Complexity", 20),
    ("Space Complexity", 10),
    ("Code Quality", 10),
    ("Edge Cases", 10),
    ("Coding Style", 10),
]

_COMPLEXITY_SCORE_TABLE = {
    "o(1)": (100, "Constant-time — excellent."),
    "o(logn)": (95, "Logarithmic — very efficient."),
    "o(log(n))": (95, "Logarithmic — very efficient."),
    "o(n)": (90, "Linear — optimal for most problems."),
    "o(nlogn)": (82, "Linearithmic — typical of sorting-based solutions."),
    "o(nlog(n))": (82, "Linearithmic — typical of sorting-based solutions."),
    "o(n√n)": (70, "Sub-quadratic — acceptable for medium inputs."),
    "o(n²)": (58, "Quadratic — acceptable only for small inputs."),
    "o(n^2)": (58, "Quadratic — acceptable only for small inputs."),
    "o(n2)": (58, "Quadratic — acceptable only for small inputs."),
    "o(n³)": (32, "Cubic — feasible only for very small inputs."),
    "o(n^3)": (32, "Cubic — feasible only for very small inputs."),
    "o(n3)": (32, "Cubic — feasible only for very small inputs."),
    "o(2^n)": (15, "Exponential — impractical for large inputs."),
    "o(n!)": (5, "Factorial — not scalable."),
    "o(v+e)": (85, "Linear in graph size — typical of BFS/DFS."),
    "o(v²)": (55, "Quadratic in vertex count — dense-graph cost."),
    "o((v+e)logv)": (82, "Dijkstra-style — efficient for sparse graphs."),
    "o(l)": (85, "Linear in key length — typical of trie operations."),
    "o(l·alphabet)": (80, "Linear in key length × alphabet size."),
    "o(depth)": (75, "Depends on recursion depth — acceptable."),
    "o(states)": (80, "Depends on the number of distinct states — typical of memoised DP."),
}

_PATTERN_RULES = [
    ("Binary Search", ["binary search", "binsearch", "while low < high", "while lo < hi", "while left < right", "high = mid", "low = mid", "lo = mid", "hi = mid", "mid = (low", "mid = (lo", "mid = (left"], 2),
    ("Sorting", ["sort()", "sorted(", "std::sort", "arrays.sort", "list.sort", ".sort()", "sort(", "qsort", "mergesort", "quicksort", "collections.sort", "sort(begin"], 1),
    ("BFS", ["bfs", "deque", "queue.append", "queue.pop", "queue.push", "queue.pop(", "front()", "from collections import deque", "enqueue", "dequeue", "new queue", "queue<", "queue.poll", "q.enqueue", "q.dequeue"], 2),
    ("DFS", ["dfs", "visited", "stack.append", "stack.push", "depth-first"], 1),
    ("Dijkstra / Shortest Path", ["dijkstra", "dist[", "dist =", "distance[", "adj[", "adjacency"], 2),
    ("Trie", ["trie", "self.children", "children[", "is_end", "isword", "is_word"], 1),
    ("Dynamic Programming", ["dp[", "dp =", "dp(", "memo", "memoiz", "cache", "lru_cache", "knapsack", "subproblem", "tabulation"], 2),
    ("Priority Queue / Heap", ["heapq", "heappush", "heappop", "heapify", "priority_queue", "priorityqueue", "nlargest", "nsmallest", "make_heap", "push_heap"], 1),
    ("Hash Map", ["hashmap", "hash_map", "unordered_map", "hashset", "hashtable", "dict(", "defaultdict", "collections.counter", "counter(", "map<string", "map<int", "hash set"], 1),
    ("Sliding Window", ["sliding", "window", "while right", "right - left", "right += 1"], 2),
    ("Two Pointers", ["left = 0", "right = len", "right = n", "left++", "right--", "left += 1", "right -= 1", "while left < right", "while l < r", "l = 0", "r = n - 1", "r = len"], 2),
    ("Backtracking", ["backtrack", "permute", "permutation", "combination", "subset", "n-queens", "nqueens", "sudoku"], 1),
    ("Greedy", ["greedy", "interval scheduling", "activity selection"], 1),
]

_C_KEYWORDS = {"for", "while", "if", "switch", "catch", "sizeof", "return"}


def _detect_patterns(text):
    lower = (text or "").lower()
    found = []
    for name, needles, min_hits in _PATTERN_RULES:
        hits = sum(1 for needle in needles if needle in lower)
        if hits >= min_hits:
            found.append((name, hits))
    found.sort(key=lambda pair: pair[1], reverse=True)
    return found


def _loop_nesting(text, language):
    lines = (text or "").splitlines()
    max_depth = 0
    loop_count = 0
    if language == "Python":
        stack = []
        for raw in lines:
            if not raw.strip():
                continue
            indent = len(raw) - len(raw.lstrip(" "))
            stripped = raw.strip()
            while stack and stack[-1][0] >= indent:
                stack.pop()
            is_loop = bool(re.match(r"(for|while)\b", stripped))
            if is_loop:
                loop_count += 1
            if re.match(r"(for|while|if|elif|else|def|with)\b", stripped) and stripped.endswith(":"):
                stack.append((indent, is_loop))
            max_depth = max(max_depth, sum(1 for _, lp in stack if lp))
    else:
        brace_stack = []
        pending_loop = False
        for raw in lines:
            stripped = raw.strip()
            if not stripped:
                continue
            is_loop = bool(re.match(r"(for|while)\b", stripped))
            if is_loop:
                loop_count += 1
                pending_loop = True
            opens = stripped.count("{")
            closes = stripped.count("}")
            for _ in range(closes):
                if brace_stack:
                    brace_stack.pop()
            for _ in range(opens):
                brace_stack.append(pending_loop)
                if pending_loop:
                    pending_loop = False
            if brace_stack:
                max_depth = max(max_depth, sum(1 for b in brace_stack if b))
        if loop_count and max_depth == 0:
            max_depth = 1
    return loop_count, max_depth


def _find_recursive_names(text, language):
    recursive = set()
    lines = (text or "").splitlines()
    if language == "Python":
        defs = []
        for i, ln in enumerate(lines):
            m = re.match(r"\s*def\s+(\w+)\s*\(", ln)
            if m:
                defs.append((i, m.group(1), len(ln) - len(ln.lstrip(" "))))
        for idx, name, indent in defs:
            body = []
            for j in range(idx + 1, len(lines)):
                if not lines[j].strip():
                    continue
                ind = len(lines[j]) - len(lines[j].lstrip(" "))
                if ind <= indent:
                    break
                body.append(lines[j])
            if any(re.search(r"\b" + re.escape(name) + r"\s*\(", ln) for ln in body):
                recursive.add(name)
    else:
        i = 0
        while i < len(lines):
            m = re.search(r"\b([a-zA-Z_]\w*)\s*\([^)]*\)\s*\{", lines[i])
            if m and m.group(1).lower() not in _C_KEYWORDS:
                name = m.group(1)
                brace_depth = lines[i].count("{") - lines[i].count("}")
                body = []
                j = i
                while j < len(lines) and brace_depth > 0:
                    j += 1
                    if j >= len(lines):
                        break
                    brace_depth += lines[j].count("{") - lines[j].count("}")
                    body.append(lines[j])
                if any(re.search(r"\b" + re.escape(name) + r"\s*\(", ln) for ln in body):
                    recursive.add(name)
                i = j
            else:
                i += 1
    return recursive


def _uses_auxiliary_structures(text):
    if not text:
        return False
    if re.search(
        r"\b(dp|visited|seen|memo|memoiz|dist|ans|res|result|prefix|suffix|temp|aux|lookup)\b",
        text,
    ):
        return True
    if re.search(
        r"new\s+\w+\s*(\[[^\]]*\])?|vector\s*<|list\s*<|hashmap|unordered_map|"
        r"dict\s*\(|set\s*\(|deque\s*\(|defaultdict|collections\.counter|"
        r"\bint\s*\w+\s*\[|char\s*\w+\s*\[|\blong\s*\w+\s*\[",
        text,
    ):
        return True
    return False


def _is_2d_structure(text):
    return bool(
        re.search(
            r"dp\[[^\]]*\]\s*\[|vector\s*<\s*vector|list\s*<\s*list|"
            r"new\s+int\[[^\]]*\]\[|\[\s*\]\s*\[\s*\]\s*=|dp\s*=\s*\[\[|"
            r"int\[\s*\]\[\s*\]",
            text,
        )
    )


def analyze_complexity(code, language):
    text = code or ""
    patterns = _detect_patterns(text)
    names = [name for name, _ in patterns]
    loop_count, max_depth = _loop_nesting(text, language)
    recursive = bool(_find_recursive_names(text, language))

    time = "O(n)"
    space = "O(n)"
    time_reason = "A single pass over the input was detected."
    space_reason = "Auxiliary structures scale with the input size."
    confidence = "Low"

    if "Binary Search" in names:
        time, confidence = "O(log n)", "High"
        time_reason = "Binary-search pattern detected — the search space halves each iteration."
    elif "Sorting" in names:
        time, confidence = "O(n log n)", "Medium"
        time_reason = "A sorting routine dominates the runtime."
    elif "Dijkstra / Shortest Path" in names:
        time, confidence = "O((V+E) log V)", "High"
        time_reason = "Dijkstra-style priority-queue traversal detected."
    elif "Priority Queue / Heap" in names:
        time, confidence = "O(n log n)", "High"
        time_reason = "Heap / priority-queue operations are O(log n) per element."
    elif "Sliding Window" in names or "Two Pointers" in names:
        time, confidence = "O(n)", "Medium"
        time_reason = "Sliding-window / two-pointer scan visits elements a bounded number of times."
    elif "BFS" in names:
        time, confidence = "O(V + E)", "High"
        time_reason = "Breadth-first traversal visits every vertex and edge once."
    elif "DFS" in names:
        time, confidence = "O(V + E)", "High"
        time_reason = "Depth-first traversal visits every vertex and edge once."
    elif "Trie" in names:
        time, confidence = "O(L)", "High"
        time_reason = "Trie operations run in time proportional to the key length L."
    elif "Dynamic Programming" in names:
        if recursive:
            time, confidence = "O(states)", "Medium"
            time_reason = "Memoised DP evaluates each distinct state once."
        elif max_depth >= 2:
            time, confidence = "O(n²)", "Medium"
            time_reason = "DP transition loop is nested over two dimensions."
        else:
            time, confidence = "O(n)", "Medium"
            time_reason = "Linear scan of the DP state space detected."
    elif recursive:
        time, confidence = "O(2^n)", "Medium"
        time_reason = "Unmemoised recursion may explore an exponential search tree."
    else:
        if max_depth >= 3:
            time, confidence = "O(n³)", "Medium"
            time_reason = "At least three nested loops detected."
        elif max_depth == 2:
            time, confidence = "O(n²)", "Medium"
            time_reason = "Two nested loops detected."
        elif max_depth == 1:
            time, confidence = "O(n)", "Medium"
            time_reason = "A single loop processes the input."
        elif loop_count == 0:
            time, confidence = "O(1)", "Medium"
            time_reason = "No loops detected — likely constant-time operations."
        else:
            time, confidence = "O(n)", "Low"
            time_reason = "Loop structure could not be estimated precisely."

    uses_structures = _uses_auxiliary_structures(text)
    if "Binary Search" in names and not uses_structures:
        space, space_reason = "O(1)", "Binary search runs in-place with constant auxiliary space."
    elif "Trie" in names:
        space, space_reason = "O(L · alphabet)", "Each key inserts O(L) trie nodes."
    elif "Dynamic Programming" in names:
        if _is_2d_structure(text):
            space, space_reason = "O(n²)", "A two-dimensional DP table is allocated."
        else:
            space, space_reason = "O(n)", "The DP state array scales linearly with the input."
    elif recursive:
        space, space_reason = "O(depth)", "Recursive calls consume stack space up to the recursion depth."
    elif "BFS" in names or "DFS" in names:
        space, space_reason = "O(n)", "Visited set plus traversal queue/stack scale with graph size."
    elif uses_structures:
        space, space_reason = "O(n)", "Auxiliary data structures scale with the input size."
    else:
        space, space_reason = "O(1)", "Only a constant amount of auxiliary space is used."

    if confidence == "Low" and (names or max_depth > 0):
        confidence = "Medium"

    return {
        "time": time,
        "time_reason": time_reason,
        "space": space,
        "space_reason": space_reason,
        "confidence": confidence,
        "patterns": names,
        "loop_count": loop_count,
        "loop_depth": max_depth,
    }


def _consistent_indent(lines):
    has_tab = any("\t" in ln[:16] for ln in lines)
    space_indents = [
        len(ln) - len(ln.lstrip(" "))
        for ln in lines
        if ln.strip() and "\t" not in ln[:16]
    ]
    if has_tab and space_indents:
        return False
    nonzero = [i for i in space_indents if i > 0]
    if not nonzero:
        return True
    unit = min(nonzero)
    return all(i % unit == 0 for i in nonzero)


def _static_signals(code, language):
    text = code or ""
    lines = text.splitlines()
    non_blank = [ln for ln in lines if ln.strip()]
    lower = text.lower()
    return {
        "total_lines": len(non_blank),
        "has_comments": bool(re.search(r"#|//|/\*|\*/", text)),
        "has_docstring": bool(re.search(r'"""|\'\'\'', text)),
        "has_functions": bool(
            re.search(
                r"\bdef\s+\w+|(?:public\s+|private\s+|protected\s+|static\s+)?"
                r"(?:int|void|long|double|char|bool|float|string)\s+\w+\s*\(|\bclass\s+\w+",
                text,
            )
        ),
        "has_type_hints": bool(re.search(r"\bdef\s+\w+\s*\([^)]*:\s*\w+", text)),
        "has_error_handling": bool(
            re.search(r"\btry\b|\bexcept\b|\bcatch\b|\bthrow\b|\braise\b", lower)
        ),
        "has_empty_check": bool(
            re.search(
                r"\bif\s+not\s+\w+|if\s+len\(|if\s+is_empty|\.isempty\(|\.empty\(\)|"
                r"length\s*==\s*0|size\(\)\s*==\s*0|n\s*==\s*0|nullptr|\bnull\b|is\s+None",
                text,
            )
        ),
        "has_bounds_check": bool(
            re.search(
                r"while\s+low\b|while\s+left\b|while\s+lo\b|i\s*<\s*len\(|i\s*<\s*n\b|"
                r"j\s*<\s*n\b|i\s*<=\s*n\s*-\s*1|\.length\s*-\s*1|\.size\(\)\s*-\s*1|"
                r"i\s*<\s*size|n\s*-\s*1\b",
                lower,
            )
        ),
        "has_magic_numbers": len(re.findall(r"(?<![\w.])\d{2,}(?![\w])", text)) >= 3,
        "consistent_indent": _consistent_indent(lines),
        "long_lines": sum(1 for ln in non_blank if len(ln) > 100),
        "has_ds_use": bool(
            re.search(
                r"\b(dict|dictionary|map|set|list|array|vector|stack|queue|deque|"
                r"heap|heapq|hashmap|hash_map|unordered_map|hashset|hashtable|"
                r"defaultdict)\b",
                lower,
            )
        ),
    }


def _style_comment(signals):
    parts = []
    if signals["has_comments"]:
        parts.append("commented")
    if signals["has_docstring"]:
        parts.append("documented")
    if signals["has_type_hints"]:
        parts.append("typed signatures")
    if signals["consistent_indent"]:
        parts.append("consistent indentation")
    if not signals["has_magic_numbers"]:
        parts.append("no magic numbers")
    if signals["long_lines"]:
        parts.append("some long lines")
    return (
        "Styling notes: " + ", ".join(parts) + "."
        if parts
        else "Style could be improved with comments and consistent formatting."
    )


def _correctness_from_status(status):
    if status == "accepted":
        return 100, "Output matched the expected sample output."
    if status == "wrong_answer":
        return 55, "Output did not match the expected output — logic needs review."
    if status == "runtime_error":
        return 30, "Program terminated with a runtime error."
    if status == "compile_error":
        return 10, "Code failed to compile successfully."
    if status in ("time_limit_exceeded", "memory_limit_exceeded"):
        return 25, "Resource limit exceeded during execution."
    if status in ("tool_missing", "internal_error"):
        return 5, "Solution could not be executed by the local judge."
    if status == "no_tests":
        return 50, "No hidden test cases were available — evaluated against the sample run."
    return 50, "Solution has not been executed yet."


def _complexity_score(complexity_str):
    key = (complexity_str or "").strip().lower().replace(" ", "")
    if key in _COMPLEXITY_SCORE_TABLE:
        return _COMPLEXITY_SCORE_TABLE[key]
    if "n!" in key:
        return 5, "Factorial complexity — not scalable."
    if "2^n" in key or "exponential" in key:
        return 15, "Exponential complexity — impractical for large inputs."
    if "n^3" in key or "n³" in key or "n3" in key or "cubic" in key:
        return 32, "Cubic complexity — feasible only for very small inputs."
    if "n^2" in key or "n²" in key or "n2" in key or "quadratic" in key:
        return 58, "Quadratic complexity — acceptable only for small inputs."
    if "log" in key:
        return 82, "Logarithmic-factor complexity — efficient."
    if "n√n" in key or "nsqrt" in key:
        return 70, "Sub-quadratic complexity — acceptable for medium inputs."
    if "n" in key:
        return 90, "Linear complexity — optimal for most problems."
    return 70, "Complexity could not be precisely classified."


def compute_recruiter_evaluation(code, language, judge_status, hidden_result, complexity):
    signals = _static_signals(code, language)
    scores = {}
    comments = {}

    if (
        hidden_result
        and hidden_result.get("status") != "no_tests"
        and hidden_result.get("total")
    ):
        total = int(hidden_result.get("total") or 0)
        passed = int(hidden_result.get("passed") or 0)
        if total > 0:
            scores["Correctness"] = round((passed / total) * 100.0)
            comments["Correctness"] = f"{passed}/{total} hidden test cases passed."
        else:
            scores["Correctness"] = 0
            comments["Correctness"] = "No hidden test cases were available."
    else:
        scores["Correctness"], comments["Correctness"] = _correctness_from_status(judge_status)

    scores["Time Complexity"], comments["Time Complexity"] = _complexity_score(complexity["time"])
    scores["Space Complexity"], comments["Space Complexity"] = _complexity_score(complexity["space"])

    quality = 60.0
    q_notes = []
    if signals["has_functions"]:
        quality += 12
        q_notes.append("modular function structure")
    if signals["has_error_handling"]:
        quality += 10
        q_notes.append("error handling present")
    if signals["has_ds_use"]:
        quality += 6
        q_notes.append("appropriate data structures")
    if signals["long_lines"] == 0:
        quality += 6
        q_notes.append("clean formatting")
    if signals["has_magic_numbers"]:
        quality -= 12
        q_notes.append("magic numbers present")
    quality = max(0.0, min(100.0, quality))
    scores["Code Quality"] = round(quality)
    comments["Code Quality"] = (
        "Detected: " + ", ".join(q_notes) + "." if q_notes else "Structure looks solid."
    )

    edge = 50.0
    e_notes = []
    if signals["has_empty_check"]:
        edge += 25
        e_notes.append("empty input handled")
    if signals["has_bounds_check"]:
        edge += 15
        e_notes.append("bounds checked")
    if signals["has_error_handling"]:
        edge += 10
        e_notes.append("errors handled")
    edge = max(0.0, min(100.0, edge))
    scores["Edge Cases"] = round(edge)
    comments["Edge Cases"] = (
        ", ".join(e_notes) if e_notes else "No explicit edge-case guards detected."
    )

    style = 55.0
    if signals["has_comments"]:
        style += 15
    if signals["has_docstring"]:
        style += 5
    if signals["has_type_hints"]:
        style += 5
    if signals["consistent_indent"]:
        style += 10
    if signals["has_magic_numbers"]:
        style -= 8
    if signals["long_lines"]:
        style -= min(15, signals["long_lines"] * 3)
    style = max(0.0, min(100.0, style))
    scores["Coding Style"] = round(style)
    comments["Coding Style"] = _style_comment(signals)

    metrics = [
        {
            "metric": name,
            "score": int(scores.get(name, 50)),
            "weight": int(weight),
            "comment": comments.get(name, ""),
        }
        for name, weight in RECRUITER_METRICS
    ]
    final_score = round(sum(m["score"] * m["weight"] for m in metrics) / 100.0)
    return {"metrics": metrics, "final_score": final_score}


def _review_logic(complexity):
    patterns = complexity.get("patterns") or []
    if patterns:
        return (
            "Detected algorithmic patterns: " + ", ".join(patterns)
            + ". Estimated time complexity: " + complexity["time"]
            + " (confidence: " + complexity["confidence"].lower() + ")."
        )
    return (
        "No dominant algorithmic pattern could be identified statically; "
        "estimated time complexity: " + complexity["time"] + "."
    )


def _review_optimization(time, signals):
    if time in ("O(n²)", "O(n³)"):
        return "Time complexity could be improved by reducing work per element — hashing, sorting once, or two-pointer scans."
    if time in ("O(2^n)", "O(n!)"):
        return "Exponential complexity suggests overlapping subproblems — memoisation or dynamic programming would help."
    if signals["has_ds_use"]:
        return "Solution is reasonably efficient; verify the chosen data structures are the lightest fit."
    return "Current complexity looks acceptable; further gains would come from micro-optimisation only."


def _review_readability(signals):
    parts = []
    if signals["has_comments"]:
        parts.append("comments explain intent")
    if signals["consistent_indent"]:
        parts.append("indentation is consistent")
    if not signals["has_magic_numbers"]:
        parts.append("no magic numbers")
    if signals["long_lines"] == 0:
        parts.append("line lengths are reasonable")
    return (
        "Readable: " + ", ".join(parts) + "."
        if parts
        else "Readability would improve with comments, consistent formatting and named constants."
    )


def _review_maintainability(signals):
    parts = []
    if signals["has_functions"]:
        parts.append("logic is factored into functions")
    if not signals["has_magic_numbers"]:
        parts.append("no scattered magic numbers")
    if signals["total_lines"] <= 200:
        parts.append("file is compact")
    return (
        "Maintainable: " + ", ".join(parts) + "."
        if parts
        else "Maintainability would improve with a modular structure and named constants."
    )


def review_code(code, language, complexity):
    text = code or ""
    signals = _static_signals(text, language)
    time = complexity["time"]
    strengths, weaknesses, suggestions = [], [], []

    if signals["has_functions"]:
        strengths.append("Solution is organised into functions/methods, which improves testability.")
    if signals["has_comments"]:
        strengths.append("Comments explain intent in parts of the code.")
    if signals["has_error_handling"]:
        strengths.append("Explicit error/exception handling is present.")
    if signals["has_empty_check"]:
        strengths.append("Empty or null input cases are explicitly handled.")
    if signals["has_bounds_check"]:
        strengths.append("Bounds/range checks help avoid out-of-range access.")
    if signals["consistent_indent"]:
        strengths.append("Indentation is consistent, which improves readability.")
    if not signals["has_magic_numbers"]:
        strengths.append("Magic numbers are avoided in favour of clear literals.")
    if time not in ("O(n²)", "O(n³)", "O(2^n)", "O(n!)"):
        strengths.append(f"Estimated time complexity {time} is efficient for typical inputs.")
    if not strengths:
        strengths.append("The solution runs and demonstrates a basic working algorithm.")

    if signals["total_lines"] == 0:
        weaknesses.append("The submission is empty.")
    if signals["has_magic_numbers"]:
        weaknesses.append("Repeated magic numbers reduce clarity — define named constants.")
    if signals["long_lines"]:
        weaknesses.append(f"{signals['long_lines']} line(s) exceed 100 characters.")
    if not signals["has_empty_check"]:
        weaknesses.append("No explicit check for empty or null inputs.")
    if not signals["has_error_handling"]:
        weaknesses.append("No explicit error handling around risky operations.")
    if not signals["has_comments"]:
        weaknesses.append("The code is largely un-commented; add comments for non-obvious logic.")
    if time in ("O(n²)", "O(n³)", "O(2^n)", "O(n!)"):
        weaknesses.append(f"Time complexity {time} may be too slow for large inputs.")
    if not signals["has_functions"]:
        weaknesses.append("Logic is written inline rather than in reusable functions.")
    if not weaknesses:
        weaknesses.append("No significant rule-based weaknesses were detected.")

    if time in ("O(n²)", "O(n³)"):
        suggestions.append("Reduce nested loops using a hash map, sorting once, or pre-processing.")
    if time in ("O(2^n)", "O(n!)"):
        suggestions.append("Add memoisation or dynamic programming to prune exponential branches.")
    if not signals["has_empty_check"]:
        suggestions.append("Add an early guard for empty/None input before the main logic.")
    if not signals["has_error_handling"]:
        suggestions.append("Wrap risky I/O and indexing operations in try/catch (or equivalent).")
    if signals["has_magic_numbers"]:
        suggestions.append("Replace magic numbers with descriptive named constants.")
    if signals["long_lines"]:
        suggestions.append("Reformat long lines to stay within a readable width.")
    if not signals["has_comments"]:
        suggestions.append("Add brief comments describing the main algorithm and invariants.")
    if not suggestions:
        suggestions.append("No critical improvements required — focus on micro-optimisation and tests.")

    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "logic": _review_logic(complexity),
        "optimization": _review_optimization(time, signals),
        "readability": _review_readability(signals),
        "maintainability": _review_maintainability(signals),
        "suggestions": suggestions,
    }


_INTERVIEW_CATEGORY_QUESTIONS = {
    "Graph": [
        "How would you represent this graph in memory, and what are the trade-offs?",
        "When would you prefer BFS over DFS for this problem, and vice versa?",
        "How do you detect cycles in a directed versus an undirected graph?",
        "How would the complexity change if the graph were dense instead of sparse?",
    ],
    "Tree": [
        "How do the standard tree traversals differ, and which one does this problem need?",
        "How would you handle a skewed tree versus a balanced tree?",
        "Can this be solved iteratively without recursion? What are the trade-offs?",
    ],
    "Dynamic Programming": [
        "How did you identify the optimal substructure for this problem?",
        "What states does your DP table store, and how are transitions defined?",
        "Can this DP be optimised using state compression or space reduction?",
        "How would you reconstruct the optimal solution path from the DP table?",
    ],
    "String": [
        "How does the solution handle Unicode characters or empty strings?",
        "What is the space overhead of your string operations, given immutability?",
    ],
    "Array": [
        "How would your solution scale to an array too large to fit in memory?",
        "Are there redundant passes over the array that could be merged into one?",
    ],
    "Sorting": [
        "Which sorting algorithm is used underneath, and is it stable?",
        "How would your approach behave on a nearly-sorted input?",
    ],
    "Searching": [
        "How many elements do you examine in the worst case?",
        "Could interpolation or exponential search improve on this?",
    ],
    "Two Pointers": [
        "Why is the two-pointer technique valid here? Can you justify the invariants?",
        "When would two pointers fail and a hash map be the better choice?",
    ],
    "Sliding Window": [
        "Why is a sliding window valid here, and what invariant does it maintain?",
        "When would expanding and shrinking the window miss a valid answer?",
    ],
    "Hash Map": [
        "What is the collision-handling strategy in your hash map, and its worst case?",
        "Could you replace the hash map with sorting or a bounded-range array?",
    ],
    "Stack & Queue": [
        "What invariants does your stack/queue maintain?",
        "How would a monotonic stack property simplify this problem?",
    ],
    "Heap": [
        "Why use a heap instead of repeatedly scanning the array?",
        "How do you handle duplicate keys in the heap?",
    ],
    "Linked List": [
        "How does the solution behave if the linked list contains a cycle?",
        "What is the space cost of the recursive versus the iterative version?",
    ],
    "Backtracking": [
        "How do you prune branches so you do not explore every possibility?",
        "Could this backtracking solution be converted into an iterative one?",
    ],
    "Greedy": [
        "Why does the greedy choice lead to an optimal solution here?",
        "Give a counter-example where the greedy approach would fail.",
    ],
    "Bit Manipulation": [
        "How do bitwise operations reduce time and space here?",
        "What happens with negative numbers or very large inputs?",
    ],
    "Math": [
        "How do you guard against integer overflow in fixed-width languages?",
        "Could this be solved with a closed-form mathematical formula?",
    ],
}

_INTERVIEW_GENERIC_QUESTIONS = [
    "Walk me through your approach from start to finish.",
    "Why did you choose this algorithm over the alternatives?",
    "Why did you choose this data structure?",
    "What is the time complexity of your solution and why?",
    "What is the space complexity of your solution and why?",
    "Which edge cases did you consider, and how are they handled?",
    "Can your solution be optimised further? What would you change?",
    "How would you test this solution in a production codebase?",
]


def _infer_problem_category(q):
    text = " ".join(
        [
            str(q.get("title", "")),
            str(q.get("prompt", "")),
            str(q.get("target_alignment", "")),
        ]
    ).lower()
    category_keywords = [
        ("Graph", ["graph", "bfs", "dfs", "topological", "dijkstra", "adjacency", "shortest path", "maze", "grid", "connected component"]),
        ("Tree", ["binary tree", "binary search tree", "bst", "traversal", "inorder", "preorder", "postorder", "level order", "lowest common ancestor", "lca", "tree"]),
        ("Dynamic Programming", ["dynamic programming", "knapsack", "memoiz", "coin change", "edit distance", "climbing stairs", "subsequence"]),
        ("String", ["palindrome", "anagram", "substring", "pattern", "string", "character", "word", "sentence"]),
        ("Linked List", ["linked list", "cycle", "merge list", "reverse list", "node"]),
        ("Stack & Queue", ["stack", "queue", "parenthes", "bracket", "valid parentheses", "next greater", "monotonic", "deque"]),
        ("Array", ["array", "nums", "two sum", "rotate", "matrix", "interval", "prefix sum"]),
        ("Two Pointers", ["two pointer", "two-pointer", "pointers", "triplet", "3sum", "container with most water", "rain water", "pair sum"]),
        ("Sliding Window", ["sliding window", "window", "subarray"]),
        ("Sorting", ["sort", "merge sort", "quick sort", "kth largest", "top k", "ordered"]),
        ("Searching", ["binary search", "search", "find", "lookup", "index", "kth"]),
        ("Hash Map", ["hash", "hashmap", "frequency", "count occurrences", "distinct", "duplicate", "dictionary"]),
        ("Heap", ["heap", "priority", "kth largest", "merge k", "median", "smallest"]),
        ("Backtracking", ["backtrack", "permutation", "combination", "subset", "n-queens", "sudoku"]),
        ("Greedy", ["greedy", "scheduling", "activity", "maximum", "minimum"]),
        ("Bit Manipulation", ["bit", "xor", "mask", "shift", "bitwise"]),
        ("Math", ["math", "prime", "factorial", "power", "gcd", "modulo", "sum of"]),
    ]
    for category, keywords in category_keywords:
        if any(keyword in text for keyword in keywords):
            return category
    return "General Algorithm"


def generate_interview_questions(q, max_count=8):
    category = _infer_problem_category(q)
    ordered = (
        list(_INTERVIEW_CATEGORY_QUESTIONS.get(category, []))
        + _INTERVIEW_GENERIC_QUESTIONS
    )
    seen = set()
    unique = []
    for item in ordered:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            unique.append(item)
    if len(unique) > max_count:
        unique = unique[:max_count]
    while len(unique) < 5:
        unique.append(
            _INTERVIEW_GENERIC_QUESTIONS[len(unique) % len(_INTERVIEW_GENERIC_QUESTIONS)]
        )
    return {"category": category, "questions": unique[:max_count]}


def generate_hiring_feedback(overall_percent):
    if overall_percent >= 85:
        band = "Excellent"
        recommendation = "Strong Hire — recommend advancing to the next round."
        strengths = [
            "Demonstrates strong algorithmic and problem-solving skills.",
            "Solutions are efficient, correct, and well-structured.",
        ]
        weaknesses = [
            "Opportunities remain in optimising edge cases and readability.",
        ]
        improvements = [
            "Focus on formal complexity justifications and cleaner abstractions.",
        ]
    elif overall_percent >= 70:
        band = "Good"
        recommendation = "Hire with confidence — minor areas for growth."
        strengths = [
            "Solid command of core algorithms and data structures.",
            "Most solutions are correct and reasonably efficient.",
        ]
        weaknesses = [
            "Some solutions could be more efficient or better structured.",
        ]
        improvements = [
            "Practice space-time trade-offs and clean-code habits.",
        ]
    elif overall_percent >= 50:
        band = "Average"
        recommendation = "Consider in a future round after focused improvement."
        strengths = [
            "Shows a working understanding of basic problems.",
        ]
        weaknesses = [
            "Efficiency, edge-case handling, and code quality need work.",
        ]
        improvements = [
            "Revise complexity analysis, edge cases, and modular design.",
        ]
    else:
        band = "Needs Improvement"
        recommendation = "Not recommended at this stage — revisit fundamentals first."
        strengths = []
        weaknesses = [
            "Core algorithmic understanding is currently insufficient.",
        ]
        improvements = [
            "Strengthen fundamentals before attempting complex problems.",
        ]
    return {
        "band": band,
        "overall_percent": overall_percent,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "improvements": improvements,
        "recommendation": recommendation,
    }


def build_candidate_evaluation(q, code, language, judge_status, hidden_result=None, prev_hidden=None):
    if hidden_result is None and prev_hidden:
        hidden_result = prev_hidden
    complexity = analyze_complexity(code, language)
    recruiter = compute_recruiter_evaluation(
        code, language, judge_status, hidden_result, complexity
    )
    review = review_code(code, language, complexity)
    questions = generate_interview_questions(q)
    return {
        "recruiter": recruiter,
        "complexity": complexity,
        "review": review,
        "questions": questions,
        "hidden_result": hidden_result,
    }


def _render_recruiter_evaluation(recruiter):
    st.markdown("#### 👔 Recruiter Evaluation")
    table = [
        "| Metric | Score /100 | Weight | Comments |",
        "|---|---:|---:|---|",
    ]
    for metric in recruiter["metrics"]:
        table.append(
            f"| {metric['metric']} | {metric['score']} | {metric['weight']}% | {metric['comment']} |"
        )
    st.markdown("\n".join(table))
    st.success(f"**Final Score: {recruiter['final_score']} / 100**")


def _render_complexity_analysis(cx):
    st.markdown("#### ⏱️ Complexity Analysis")
    c1, c2, c3 = st.columns(3)
    c1.metric("Time Complexity", cx["time"])
    c2.metric("Space Complexity", cx["space"])
    c3.metric("Confidence", cx["confidence"])
    st.caption(
        "Detected patterns: "
        + (", ".join(cx["patterns"]) if cx["patterns"] else "No dominant pattern")
    )
    st.info(cx["time_reason"] + "  \n" + cx["space_reason"])


def _render_code_review(review):
    st.markdown("#### 🔍 Code Review")
    col_l, col_r = st.columns(2)
    with col_l:
        with st.expander("✅ Strengths", expanded=False):
            for item in review["strengths"]:
                st.markdown(f"- {item}")
        with st.expander("⚠️ Weaknesses", expanded=False):
            for item in review["weaknesses"]:
                st.markdown(f"- {item}")
    with col_r:
        with st.expander("💡 Suggestions", expanded=False):
            for item in review["suggestions"]:
                st.markdown(f"- {item}")
    st.markdown(f"**🔀 Logic:** {review['logic']}")
    st.markdown(f"**⚡ Optimization:** {review['optimization']}")
    st.markdown(f"**📖 Readability:** {review['readability']}")
    st.markdown(f"**🛠️ Maintainability:** {review['maintainability']}")


def _render_interview_questions(questions):
    st.markdown("#### ❓ Interview Questions")
    st.caption(f"Category: {questions['category']}")
    for idx, question in enumerate(questions["questions"], 1):
        st.markdown(f"{idx}. {question}")


def _render_hiring_feedback(feedback):
    st.markdown("#### 🏁 Hiring Feedback")
    c1, c2 = st.columns(2)
    c1.metric("Recruiter Band", feedback["band"])
    c2.metric("Overall Score", f"{feedback['overall_percent']:.1f}%")
    with st.expander("✅ Overall Strengths", expanded=False):
        for item in feedback["strengths"]:
            st.markdown(f"- {item}")
    with st.expander("⚠️ Overall Weaknesses", expanded=False):
        for item in feedback["weaknesses"]:
            st.markdown(f"- {item}")
    with st.expander("🚀 Suggested Improvements", expanded=False):
        for item in feedback["improvements"]:
            st.markdown(f"- {item}")
    st.success(f"**Hiring Recommendation:** {feedback['recommendation']}")


def normalize_output_str(val_str):
    if not val_str:
        return ""
    cleaned = str(val_str).strip()
    cleaned = re.sub(r"[\r\n\t]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def skill_present(resume_lower, extracted_skills_dict, skill_label):
    token = skill_label.split(" (")[0].strip().lower()
    if not token:
        return False

    extracted_flat = []
    if extracted_skills_dict:
        for cat, sk_list in extracted_skills_dict.items():
            for sk in sk_list:
                extracted_flat.append(sk.lower())

    if any(token in sk_item or sk_item in token for sk_item in extracted_flat):
        return True

    if len(token) <= 3:
        return re.search(r"\b" + re.escape(token) + r"\b", resume_lower) is not None
    return token in resume_lower


def compute_skill_gap_report(
    resume_text, extracted_skills_dict, predicted_role, desired_role
):
    resume_lower = resume_text.lower()

    pred_cats = ROLE_TAXONOMY_REQUIREMENTS.get(
        predicted_role, list(SKILL_CATEGORIES.keys())
    )
    des_cats = ROLE_TAXONOMY_REQUIREMENTS.get(
        desired_role, list(SKILL_CATEGORIES.keys())
    )
    target_categories = set(pred_cats + des_cats)

    core_langs = ["python", "c", "java", "c++", "c#", "rust", "sql"]
    found_langs = sum(
        1
        for lang in core_langs
        if skill_present(resume_lower, extracted_skills_dict, lang)
    )

    missing_list = []

    for category in target_categories:
        subskills = SKILL_CATEGORIES.get(category, [])
        if category == "Programming Languages":
            if found_langs < 2:
                for lang in subskills:
                    if not skill_present(resume_lower, extracted_skills_dict, lang):
                        missing_list.append(lang)
        elif subskills:
            for sk in subskills:
                if not skill_present(resume_lower, extracted_skills_dict, sk):
                    missing_list.append(sk)
        else:
            if not skill_present(resume_lower, extracted_skills_dict, category):
                missing_list.append(category)

    return list(dict.fromkeys(missing_list))


def check_project_suitability(extracted_projects, predicted_role, desired_role):
    if not extracted_projects:
        return (
            False,
            "No dedicated Projects section was detected in your resume.",
            [predicted_role, desired_role],
        )

    combined_text = " ".join(
        [p[0] + " " + p[1] for p in extracted_projects]
    ).lower()

    pred_keywords = ROLE_PROJECT_KEYWORDS.get(predicted_role, [])
    des_keywords = ROLE_PROJECT_KEYWORDS.get(desired_role, [])

    pred_has_proj = any(kw in combined_text for kw in pred_keywords)
    des_has_proj = any(kw in combined_text for kw in des_keywords)

    if pred_has_proj and des_has_proj:
        return True, "", []

    missing_roles = []
    if pred_has_proj and not des_has_proj:
        missing_roles.append(desired_role)
        feedback = (
            f"Your resume projects match **{predicted_role}** (predicted), but lack"
            f" clear alignment with **{desired_role}** (desired)."
        )
    elif des_has_proj and not pred_has_proj:
        missing_roles.append(predicted_role)
        feedback = (
            f"Your resume projects match **{desired_role}** (desired), but lack"
            f" clear alignment with **{predicted_role}** (predicted)."
        )
    else:
        missing_roles.extend([predicted_role, desired_role])
        feedback = (
            "Your resume projects don't look closely aligned with"
            f" **{predicted_role}** (predicted) or **{desired_role}** (desired)."
        )

    return False, feedback, missing_roles


def compute_ats_score(resume_text):
    score = 40
    word_count = len(resume_text.split())
    if 300 <= word_count <= 900:
        score += 15
    elif word_count > 0:
        score += 5

    section_keywords = [
        "experience",
        "education",
        "skills",
        "projects",
        "certifications",
        "summary",
    ]
    found_sections = sum(1 for kw in section_keywords if kw in resume_text.lower())
    score += min(found_sections * 5, 25)

    action_verbs = [
        "developed",
        "built",
        "designed",
        "implemented",
        "led",
        "managed",
        "created",
        "optimized",
        "automated",
        "deployed",
    ]
    verb_hits = sum(1 for v in action_verbs if v in resume_text.lower())
    score += min(verb_hits * 2, 20)

    return min(score, 100)


def compute_resume_strength_score(resume_text):
    score = 30
    quant_hits = len(re.findall(r"\d+%|\$\d+|\b\d{2,}\b", resume_text))
    score += min(quant_hits * 4, 30)

    contact_hits = sum(
        1 for kw in ["email", "phone", "linkedin", "github"] if kw in resume_text.lower()
    )
    score += min(contact_hits * 5, 20)

    if len(resume_text.split()) > 150:
        score += 20

    return min(score, 100)


def compute_placement_readiness_score(ats_score, strength_score):
    return round((ats_score * 0.5) + (strength_score * 0.5), 1)


def extract_candidate_name(resume_text):
    lines = [l.strip() for l in resume_text.split("\n") if l.strip()]
    for line in lines[:8]:
        if "@" in line or any(ch.isdigit() for ch in line):
            continue
        if re.search(r"resume|curriculum vitae|\bcv\b", line, re.IGNORECASE):
            continue
        words = line.split()
        if 1 < len(words) <= 4 and all(re.match(r"^[A-Za-z.'-]+$", w) for w in words):
            return line.title() if (line.isupper() or line.islower()) else line
    return "Candidate Profile"


def get_initials(name):
    if not name or name == "Candidate Profile":
        return "NA"
    parts = [p for p in re.split(r"\s+", name.strip()) if p]
    if not parts:
        return "NA"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


KNOWLEDGE_GRAPH_DOMAINS = [
    ("LinkedIn", "linkedin.com"),
    ("GitHub", "github.com"),
    ("Kaggle", "kaggle.com"),
]


def validate_profile_link(value, field_label, required_domain, blocked_domains):
    value = value.strip()
    if not value:
        return True, value, ""
    value_lower = value.lower()
    for name, domain in blocked_domains:
        if domain in value_lower:
            return (
                False,
                value,
                f"⚠️ That looks like a {name} link, not your {field_label}. Please"
                " paste the correct URL.",
            )
    if required_domain and required_domain not in value_lower:
        return (
            False,
            value,
            f"⚠️ That doesn't look like a valid {field_label} (expected a link"
            f" containing '{required_domain}').",
        )
    return True, value, ""


def _ensure_theory_vault():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM coding_vault")
        count = cursor.fetchone()[0]
        conn.close()
        if count > 0:
            return True
    except Exception:
        pass
    try:
        import ingest_all_coding

        ingest_all_coding.init_master_schema()
        ingest_all_coding.seed_master_database()
        return True
    except Exception:
        return False


def clean_theory_title(raw_title):
    text = (raw_title or "").strip()
    if text.startswith("Interviewer: '") and text.endswith("'"):
        return text[len("Interviewer: '"):-1].strip()
    return text.strip()


@st.cache_data(show_spinner=False)
def load_theory_bank(subject_tag):
    if not _ensure_theory_vault():
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT company_tier, role_name, subject_tag, question_title, difficulty "
            "FROM coding_vault WHERE subject_tag = ?",
            (subject_tag,),
        )
        rows = cursor.fetchall()
    except Exception:
        rows = []
    conn.close()

    bank, seen = [], set()
    for r in rows:
        title = r["question_title"]
        if title in seen:
            continue
        seen.add(title)
        bank.append(
            {
                "company": r["company_tier"],
                "role": r["role_name"],
                "subject_tag": r["subject_tag"],
                "difficulty": r["difficulty"] or "Medium",
                "question_title": clean_theory_title(title),
            }
        )
    return bank


def select_theory_questions(company, predicted_role, desired_role, subject_tag, count=10):
    bank = load_theory_bank(subject_tag)
    if not bank:
        return []

    def rank(q):
        company_hit = 1 if company and q["company"] == company else 0
        desired_hit = 1 if desired_role and q["role"] == desired_role else 0
        predicted_hit = 1 if predicted_role and q["role"] == predicted_role else 0
        return (company_hit, desired_hit, predicted_hit)

    groups = {}
    for q in bank:
        groups.setdefault(rank(q), []).append(q)

    base, rem = divmod(count, 3)
    targets = {"Easy": base, "Medium": base, "Hard": base}
    if rem:
        targets["Medium"] += rem

    seed_key = "|".join(
        [str(company or ""), str(desired_role or ""), str(predicted_role or ""), subject_tag, str(time.time())]
    )
    rng = random.Random(seed_key)
    for key in groups:
        rng.shuffle(groups[key])

    tier_order = sorted(groups.keys(), reverse=True)
    selected, used_titles = [], set()

    for tier in tier_order:
        for q in groups[tier]:
            if len(selected) >= count:
                break
            if q["question_title"] in used_titles:
                continue
            if targets.get(q["difficulty"], 0) > 0:
                selected.append(q)
                used_titles.add(q["question_title"])
                targets[q["difficulty"]] -= 1

    if len(selected) < count:
        for tier in tier_order:
            for q in groups[tier]:
                if len(selected) >= count:
                    break
                if q["question_title"] in used_titles:
                    continue
                selected.append(q)
                used_titles.add(q["question_title"])

    return selected[:count]


# ---------------------------------------------------------------------------
# OFFLINE RUBRIC-BASED THEORY EVALUATOR
# ---------------------------------------------------------------------------

_THEORY_CONCEPT_BANK = {
    "DSA": {
        "hash-map": ["hash map", "hash table", "hashmap", "collision", "chaining", "open addressing", "load factor", "bucket"],
        "linked-list": ["linked list", "singly linked", "doubly linked", "linked", "cycle", "head pointer", "next pointer"],
        "array": ["array", "arraylist", "array list", "contiguous", "static array", "dynamic array"],
        "string": ["string", "substring", "palindrome", "permutation", "compression", "rotation", "character"],
        "tree": ["binary search tree", "bst", "binary tree", "avl", "red-black", "balanced", "traversal", "in-order", "pre-order"],
        "heap": ["heap", "min-heap", "max-heap", "priority queue", "heapify"],
        "graph": ["graph", "adjacency", "vertex", "vertices", "shortest path", "topological", "dfs", "bfs"],
        "queue": ["queue", "circular queue", "deque", "fifo", "enqueue", "dequeue"],
        "stack": ["stack", "lifo", "push", "pop", "call stack"],
        "sorting": ["sort", "quicksort", "quick sort", "merge sort", "insertion sort", "selection sort", "bubble sort", "pivot", "partition"],
        "searching": ["binary search", "linear search", "two pointers", "two-pointer", "sliding window", "search"],
        "recursion": ["recursion", "recursive", "base case", "memoization"],
        "dynamic-programming": ["dynamic programming", "subproblem", "optimal substructure"],
        "complexity": ["time complexity", "space complexity", "big-o", "big o", "o(", "runtime", "asymptotic", "linear time", "quadratic", "logarithmic"],
        "trie": ["trie", "prefix tree", "autocomplete"],
        "bit-manipulation": ["bitwise", "xor", "bit manipulation"],
        "bloom-filter": ["bloom filter", "false positive", "probabilistic"],
    },
    "OS": {
        "process": ["process", "thread", "pcb", "lifecycle", "running", "ready", "waiting", "blocked", "terminated"],
        "scheduling": ["scheduling", "round robin", "fcfs", "sjf", "priority", "quantum", "preemptive", "cpu"],
        "memory": ["virtual memory", "paging", "page table", "page fault", "thrashing", "segmentation", "tlb", "cache", "lru", "fragmentation"],
        "deadlock": ["deadlock", "mutual exclusion", "circular wait", "hold and wait", "no preemption", "banker"],
        "synchronization": ["semaphore", "mutex", "lock", "race condition", "critical section", "monitor", "condition variable", "atomic"],
        "ipc": ["ipc", "inter-process communication", "pipe", "shared memory", "message queue", "socket", "signal"],
        "context-switch": ["context switch", "kernel", "mode switch", "overhead"],
        "filesystem": ["file system", "inode", "directory", "metadata", "block", "unix"],
        "io": ["i/o", "input/output", "file descriptor", "blocking", "non-blocking", "asynchronous", "event loop", "read", "write"],
        "container": ["container", "isolation", "hypervisor", "virtualization"],
    },
}

_FORMULA_TRIGGERS = [
    "complexity", "big-o", "big o", "o(", "runtime", "formula", "equation",
    "calculate", "derive", "asymptotic", "recurrence", "mathematical", "probability",
]
_DEPTH_MARKERS = [
    "edge case", "boundary", "worst case", "best case", "trade-off", "pros and cons",
    "consider", "therefore", "because", "specifically", "for example", "in practice",
    "optimize", "scalable", "when", "if", "however", "e.g.", "i.e.",
]
_ORGANIZATION_MARKERS = [
    "first", "second", "third", "finally", "firstly", "then", "next", "step",
    "in conclusion", "overall", "to summarize", "in summary", "first of all", "lastly",
]
_INDUSTRY_MARKERS = [
    "production", "real-world", "real world", "enterprise", "industry", "scalable",
    "performance", "latency", "throughput", "deployment", "system design",
    "microservices", "high-concurrency", "large-scale", "production-grade", "practical",
    "database", "server", "web", "api", "service", "traffic",
    "distributed", "concurrent", "network", "disk", "load", "optimize", "efficient",
    "memory", "cache", "backend", "frontend",
]
_HEDGING_MARKERS = ["maybe", "i think", "not sure", "probably", "guess", "i don't know", "i am not sure"]


def _theory_tokenize(text):
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _phrase_similarity(a, b):
    ta, tb = _theory_tokenize(a), _theory_tokenize(b)
    if not ta:
        return 0.0
    stop = {
        "the", "and", "for", "with", "how", "what", "why", "when", "you", "this",
        "that", "are", "can", "not", "your", "into", "than", "have", "from", "which",
    }
    ta = {t for t in ta if t not in stop and len(t) > 2}
    if not ta:
        return 0.0
    return len(ta & tb) / len(ta)


def _concept_keywords(concept, subject):
    bank = _THEORY_CONCEPT_BANK.get(subject, _THEORY_CONCEPT_BANK["DSA"])
    return bank.get(concept, [concept])


_KW_CACHE = {}


def _kw_in(text_lower, kw):
    match = _KW_CACHE.get(kw)
    if match is None:
        kwl = kw.lower()
        right = "" if (kwl and not kwl[-1].isalnum()) else r"(?:s|es)?(?![a-z])"
        pattern = r"(?<![a-z0-9])" + re.escape(kwl) + right
        match = re.compile(pattern)
        _KW_CACHE[kw] = match
    return match.search(text_lower) is not None


def _concept_hit(text_lower, concept, subject):
    return any(_kw_in(text_lower, kw) for kw in _concept_keywords(concept, subject))


_CORE_CONCEPTS = {
    "DSA": ["complexity", "array", "hash-map", "tree", "searching"],
    "OS": ["process", "scheduling", "memory", "synchronization", "deadlock"],
}


def _expected_concepts(question_lower, subject):
    bank = _THEORY_CONCEPT_BANK.get(subject, _THEORY_CONCEPT_BANK["DSA"])
    scored = []
    for c in bank:
        hits = sum(1 for kw in _concept_keywords(c, subject) if _kw_in(question_lower, kw))
        if hits:
            scored.append((hits, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:6]]

def _evaluate_theory_answer(question_title, answer, subject):
    question_lower = question_title.lower()
    answer_lower = (answer or "").lower()
    empty = not (answer or "").strip()

    expected = _expected_concepts(question_lower, subject)
    if not expected:
        expected = list(_CORE_CONCEPTS.get(subject, _CORE_CONCEPTS["DSA"]))

    covered = [c for c in expected if _concept_hit(answer_lower, c, subject)]
    missing = [c for c in expected if c not in covered]
    coverage = len(covered) / len(expected) if expected else 0.0

    similarity = _phrase_similarity(question_lower, answer_lower)
    len_words = len((answer or "").split())
    sentences = len(re.findall(r"[.!?]+\s", answer_lower))

    concept_terms = sum(
        1 for c in covered for kw in _concept_keywords(c, subject) if kw in answer_lower
    )
    complexity_mentioned = any(
        w in answer_lower
        for w in ["time complexity", "space complexity", "o(", "big-o", "big o",
                  "runtime", "asymptotic", "complexity"]
    )
    engaged = coverage > 0 or complexity_mentioned
    hedging_penalty = 4 * sum(1 for h in _HEDGING_MARKERS if h in answer_lower)
    ta = round(
        coverage * 24
        + min(10, concept_terms)
        + (8 if complexity_mentioned else 0)
        + min(4, round(similarity * 8))
        - min(6, hedging_penalty)
    )
    ta = max(0, min(40, ta))

    formula_expected = any(trig in question_lower for trig in _FORMULA_TRIGGERS)
    if formula_expected and not empty:
        has_notation = bool(re.search(r"o\s*\(|big[- ]o|\bO\(", answer_lower))
        complexity_stmt = any(
            w in answer_lower
            for w in ["time complexity", "space complexity", "runtime", "asymptotic", "complexity"]
        )
        math_sigils = sum(
            1 for s in ["^", "√", "∑", "≤", "≥", "*", "/", "n log", "n^2", "2^n"]
            if s in answer_lower
        )
        fc = 8 * has_notation + 6 * complexity_stmt + min(6, 2 * math_sigils)
        fc = max(0, min(20, fc))
    else:
        fc = None

    depth_hits = sum(1 for m in _DEPTH_MARKERS if m in answer_lower)
    length_depth = min(3, len_words // 30) if engaged else 0
    depth = round(7 * coverage) + min(5, depth_hits) + length_depth
    if not empty:
        depth = max(2, depth)
    depth = max(0, min(15, depth))

    org_hits = sum(1 for m in _ORGANIZATION_MARKERS if m in answer_lower)
    grammar_penalty = 2 if any(h in answer_lower for h in _HEDGING_MARKERS) else 0
    length_penalty = 3 if len_words < 20 else 0
    clarity = (
        5
        + min(4, org_hits)
        + (min(4, sentences) if engaged else 0)
        + (2 if sentences >= 3 and engaged else 0)
        - grammar_penalty
        - length_penalty
    )
    if not empty:
        clarity = max(2, clarity)
    clarity = max(0, min(15, clarity))

    ind_hits = sum(1 for m in _INDUSTRY_MARKERS if m in answer_lower)
    industry = 3 + min(7, ind_hits) + (1 if len_words >= 80 and engaged else 0)
    industry = max(0, min(10, industry))

    if formula_expected and fc is not None:
        overall = ta + fc + depth + clarity + industry
        fc_display = fc
    else:
        base = ta + depth + clarity + industry
        overall = round(base * 100 / 80)
        fc_display = overall - base

    return {
        "ta": ta,
        "fc": fc_display,
        "depth": depth,
        "clarity": clarity,
        "industry": industry,
        "overall": overall,
        "covered": covered,
        "missing": missing,
        "formula_expected": formula_expected,
    }


def _theory_feedback(score, subject):
    strengths, weaknesses, suggestions, tips = [], [], [], []

    if score["covered"]:
        strengths.append(
            f"Correctly engages expected topics: {', '.join(score['covered'][:4])}."
        )
    else:
        weaknesses.append("Answer does not clearly address the expected core topics.")

    if score["ta"] >= 30:
        strengths.append("Strong technical accuracy — correct concepts and terminology used.")
    elif score["ta"] < 16:
        weaknesses.append("Technical accuracy is weak; core concepts are missing or misused.")

    if score["formula_expected"]:
        if score["fc"] >= 15:
            strengths.append("Good formula / complexity correctness with proper notation.")
        elif score["fc"] < 8:
            weaknesses.append("Formula or complexity analysis is missing or incorrect.")

    if score["depth"] >= 10:
        strengths.append("Good depth — edge cases, trade-offs, and reasoning are covered.")
    elif score["depth"] < 6:
        weaknesses.append("Limited depth; edge cases and reasoning are underdeveloped.")

    if score["clarity"] >= 10:
        strengths.append("Clear, well-organized explanation with logical flow.")
    elif score["clarity"] < 6:
        weaknesses.append("Answer is disorganized; structure and logical flow need work.")

    if score["industry"] >= 7:
        strengths.append("Strong industry relevance — connects to real-world scenarios.")
    elif score["industry"] < 4:
        weaknesses.append("Lacks practical, production-oriented context.")

    if score["missing"]:
        for c in score["missing"][:4]:
            weaknesses.append(f"Missing or not fully explained: {c.replace('-', ' ').title()}.")
            suggestions.append(
                f"Explicitly explain {c.replace('-', ' ')} and how it applies to this question."
            )

    if score["ta"] < 20:
        suggestions.append("Revise the core concepts and use precise technical terminology.")
    if score["depth"] < 6:
        suggestions.append("Add edge cases, comparisons, and step-by-step reasoning.")
    if score["clarity"] < 6:
        suggestions.append("Structure the answer with an intro, main points, and a conclusion.")
    if score["industry"] < 4:
        suggestions.append("Mention practical use cases, performance, or production context.")

    subject_label = "data structures & algorithms" if subject == "DSA" else "operating systems"
    tips.append(f"Anchor your answer in {subject_label} terminology to show depth.")
    tips.append("State assumptions, edge cases, and the complexity of your approach.")
    tips.append("Use short, structured paragraphs with concrete examples.")

    return {
        "strengths": strengths or ["Question attempted — build on this."],
        "weaknesses": weaknesses or ["No significant weaknesses detected."],
        "missing_concepts": score["missing"],
        "suggestions": suggestions or ["Add a concise example to strengthen the answer."],
        "interview_tips": tips,
    }


def evaluate_theory_responses_batched(questions, answers_dict):
    report_data, total_score = [], 0
    subject = (questions[0].get("subject_tag", "DSA") if questions else "DSA")
    if subject not in _THEORY_CONCEPT_BANK:
        subject = "DSA"

    for idx, q in enumerate(questions):
        ans_key = f"tx-{idx}"
        text_content = answers_dict.get(ans_key, "").strip()
        q_subject = q.get("subject_tag", subject)
        if q_subject not in _THEORY_CONCEPT_BANK:
            q_subject = "DSA"

        question_title = q["question_title"]
        difficulty = q.get("difficulty", "Medium")

        if not text_content:
            report_data.append({
                "idx": idx + 1,
                "title": question_title,
                "answer": "*[No Response Submitted - Left Blank]*",
                "difficulty": difficulty,
                "score": 0,
                "overall": 0,
                "ta": 0, "fc": 0, "depth": 0, "clarity": 0, "industry": 0,
                "formula_expected": False,
                "covered": [], "missing": [],
                "strengths": ["Question left blank."],
                "weaknesses": ["No answer provided — add a structured response."],
                "missing_concepts": [],
                "suggestions": ["Answer the question with terminology, examples, and reasoning."],
                "interview_tips": ["Always attempt every question with structured reasoning."],
            })
            continue

        score = _evaluate_theory_answer(question_title, text_content, q_subject)
        feedback = _theory_feedback(score, q_subject)

        total_score += score["overall"]
        report_data.append({
            "idx": idx + 1,
            "title": question_title,
            "answer": text_content,
            "difficulty": difficulty,
            "score": score["overall"],
            "overall": score["overall"],
            "ta": score["ta"], "fc": score["fc"], "depth": score["depth"],
            "clarity": score["clarity"], "industry": score["industry"],
            "formula_expected": score["formula_expected"],
            "covered": score["covered"], "missing": score["missing"],
            "strengths": feedback["strengths"],
            "weaknesses": feedback["weaknesses"],
            "missing_concepts": feedback["missing_concepts"],
            "suggestions": feedback["suggestions"],
            "interview_tips": feedback["interview_tips"],
        })

    report_data.sort(key=lambda x: x["idx"])
    final_perc = (total_score / (len(questions) * 100)) * 100 if questions else 0.0
    theory_report = _build_theory_report(report_data, final_perc)
    return total_score, final_perc, report_data, theory_report


def _build_theory_report(report_data, final_perc):
    if not report_data:
        return {}

    answered = [r for r in report_data if r["answer"] != "*[No Response Submitted - Left Blank]*"]
    avg = final_perc

    diff_map = {"Easy": [], "Medium": [], "Hard": []}
    for r in report_data:
        diff_map.setdefault(r.get("difficulty", "Medium"), []).append(r["overall"])
    difficulty_perf = {
        d: (round(sum(v) / len(v), 1) if v else 0) for d, v in diff_map.items()
    }

    covered_counter = {}
    for r in answered:
        for c in r.get("covered", []):
            covered_counter[c] = covered_counter.get(c, 0) + 1
    missing_counter = {}
    for r in answered:
        for c in r.get("missing_concepts", []):
            missing_counter[c] = missing_counter.get(c, 0) + 1

    top_strengths = sorted(covered_counter, key=covered_counter.get, reverse=True)[:5]
    knowledge_gaps = sorted(missing_counter, key=missing_counter.get, reverse=True)[:5]

    revise_topics = []
    for c in knowledge_gaps:
        topic = c.replace("-", " ").title()
        if topic not in revise_topics:
            revise_topics.append(topic)
    if not revise_topics:
        revise_topics = ["Solid overall — continue advanced practice."]

    if avg >= 85:
        band = "Excellent"
        readiness = "Exceptionally well prepared — strong concept mastery and communication."
    elif avg >= 70:
        band = "Good"
        readiness = "Well prepared — minor gaps in depth or terminology remain."
    elif avg >= 50:
        band = "Average"
        readiness = "Moderately prepared — needs focused revision of core topics."
    else:
        band = "Needs Improvement"
        readiness = "Requires fundamental revision before interview readiness."

    return {
        "overall_theory_score": sum(r["overall"] for r in report_data),
        "average_score": round(avg, 1),
        "difficulty_performance": difficulty_perf,
        "top_strengths": [s.replace("-", " ").title() for s in top_strengths],
        "knowledge_gaps": [g.replace("-", " ").title() for g in knowledge_gaps],
        "revise_topics": revise_topics,
        "interview_readiness": readiness,
        "hiring_band": band,
    }


# ===========================================================================
# 🎯 FINAL HR ROUND MODULE
# ===========================================================================

_HR_EXPECTED = {
    "Strengths": [
        "team", "communication", "leadership", "problem", "collaborat",
        "adapt", "deliver", "analyti", "detail", "initiative", "ownership",
        "technical", "motivat", "organi",
    ],
    "Weaknesses": [
        "improve", "learn", "develop", "feedback", "delegat", "patience",
        "time management", "growth", "working on", "overcome", "honest",
        "aware", "practice",
    ],
    "Leadership": [
        "lead", "team", "guide", "mentor", "decide", "responsib", "vision",
        "empower", "delegate", "direction", "influence", "motivat", "initiative",
    ],
    "Conflict Handling": [
        "listen", "communicat", "respect", "resolve", "compromise", "mediate",
        "perspective", "calm", "negotiat", "collaborat", "solution", "empath",
    ],
}

_STAR_COMPONENTS = ["Situation", "Task", "Action", "Result"]
_STAR_MARKERS = {
    "Situation": ["situation", "context", "project", "during", "when", "team",
                  "client", "quarter", "deadline", "role"],
    "Task": ["task", "responsib", "assigned", "asked", "goal", "objective",
             "needed", "had to", "was responsible", "target", "required"],
    "Action": ["implemented", "created", "developed", "led", "organized",
               "built", "designed", "started", "took", "approached", "i",
               "initiated", "coordinated", "analyzed", "managed", "wrote"],
    "Result": ["result", "outcome", "achieved", "improved", "increased",
               "reduced", "completed", "delivered", "saved", "learned",
               "success", "impact", "percent", "metrics", "launched", "received"],
}

_HR_STRUCTURE_MARKERS = [
    "firstly", "secondly", "finally", "in summary", "for example", "for instance",
    "additionally", "moreover", "consequently", "as a result", "therefore",
    "one time", "in my previous", "overall",
]


def _hr_kw_in(text_lower, kw):
    if " " in kw.lower():
        return _kw_in(text_lower, kw.lower())
    pattern = r"(?<![a-z0-9])" + re.escape(kw.lower()) + r"[a-z]*"
    return re.search(pattern, text_lower) is not None


def build_hr_questions(desired_role, predicted_role, company, assessment_context=None):
    role = desired_role or predicted_role or "Software Engineer"
    comp = company or "our organisation"
    band = (assessment_context or {}).get("hiring_band", "")
    ctx_note = (
        f"Your technical round performance placed you in the **{band}** band."
        if band else ""
    )

    hr_questions = [
        {
            "idx": 1, "qtype": "hr", "category": "Strengths",
            "question": (
                f"What are your top three strengths that make you a strong fit for a "
                f"**{role}** role at **{comp}**? Give a concrete example for each."
            ),
        },
        {
            "idx": 2, "qtype": "hr", "category": "Weaknesses",
            "question": (
                f"What is one professional weakness you are actively working to improve, "
                f"and what concrete steps have you taken to overcome it as a **{role}** "
                f"at **{comp}**?"
            ),
        },
        {
            "idx": 3, "qtype": "hr", "category": "Leadership",
            "question": (
                f"Describe a situation where you took the lead on a technical initiative "
                f"as a **{role}**. How did you align your team and drive the outcome at **{comp}**?"
            ),
        },
        {
            "idx": 4, "qtype": "hr", "category": "Conflict Handling",
            "question": (
                f"Tell us about a time you handled a disagreement with a teammate or "
                f"stakeholder at **{comp}**. What steps did you take to reach a constructive "
                f"resolution?"
            ),
        },
    ]

    star_questions = [
        {
            "idx": 5, "qtype": "star", "category": "Behavioral",
            "prompt": (
                f"Describe a high-pressure delivery or a critical problem you solved as a "
                f"**{role}**. {ctx_note} Answer each STAR part below."
            ),
            "components": _STAR_COMPONENTS,
        },
        {
            "idx": 6, "qtype": "star", "category": "Behavioral",
            "prompt": (
                f"Share a time you drove change or improved a process/outcome while working "
                f"toward a **{role}** at **{comp}**. Answer each STAR part below."
            ),
            "components": _STAR_COMPONENTS,
        },
    ]
    return hr_questions + star_questions


def _hr_word_stats(answer):
    text = (answer or "").strip()
    words = text.split()
    sentences = len(re.findall(r"[.!?]+(?:\s|$)", text))
    if text and sentences == 0:
        sentences = 1
    return words, len(words), sentences


def _hr_coverage(answer_lower, keywords):
    if not keywords:
        return 0.0
    norm = answer_lower.replace("-", " ")
    return sum(1 for k in keywords if _hr_kw_in(norm, k)) / len(keywords)


def _score_hr_answer(question, answer):
    category = question["category"]
    expected = _HR_EXPECTED.get(category, [])
    text = (answer or "").strip()
    answer_lower = text.lower()
    words, word_count, sentences = _hr_word_stats(text)

    base = {
        "overall": 0, "relevance": 0, "completeness": 0, "clarity": 0,
        "structure": 0, "star_structure": 0,
        "covered": [], "missing": list(expected), "engaged": False,
    }
    if not text:
        return base

    answer_lower = answer_lower.replace("-", " ")
    covered = [k for k in expected if _hr_kw_in(answer_lower, k)]
    missing = [k for k in expected if k not in covered]
    coverage = len(covered) / len(expected) if expected else 0.0

    relevance = round(coverage * 24 + min(6, round(
        _phrase_similarity((question.get("question") or "").lower(), answer_lower) * 12
    )))

    engaged = coverage > 0
    completeness = round(coverage * 18)
    if engaged:
        completeness += min(6, round(word_count / 40))
        completeness += min(6, sentences if sentences <= 6 else 6)

    structure_marks = sum(1 for m in _HR_STRUCTURE_MARKERS if _hr_kw_in(answer_lower, m))
    hedging = sum(1 for h in _HEDGING_MARKERS if h in answer_lower)
    clarity = round(
        min(20, 6 + min(8, sentences * 2) + min(6, structure_marks * 2) - min(4, hedging * 2))
    )

    example_bonus = 4 if (
        "example" in answer_lower or "instance" in answer_lower or "one time" in answer_lower
    ) else 0
    structure = round(min(20, 8 + min(8, structure_marks * 2) + example_bonus))

    overall = min(100, relevance + completeness + clarity + structure)
    return {
        "overall": overall, "relevance": relevance, "completeness": completeness,
        "clarity": clarity, "structure": structure, "star_structure": 0,
        "covered": covered, "missing": missing, "engaged": engaged,
    }


def _score_star_answer(question, component_answers):
    comp_scores = {}
    for comp in _STAR_COMPONENTS:
        text = (component_answers.get(comp) or "").strip()
        lower = text.lower()
        _, wc, sentences = _hr_word_stats(text)
        if not text:
            comp_scores[comp] = {"score": 0, "present": False, "words": 0}
            continue
        markers = _STAR_MARKERS.get(comp, [])
        matched = [m for m in markers if _hr_kw_in(lower.replace("-", " "), m)]
        presence = 10 if matched else 6
        content = min(10, round((wc / 60) * 8) + (2 if sentences >= 2 else 0))
        comp_scores[comp] = {"score": min(20, presence + content), "present": True, "words": wc}

    star_total = sum(c["score"] for c in comp_scores.values())
    star_structure = round((star_total / 80) * 40)

    full = " ".join((component_answers.get(c) or "").strip() for c in _STAR_COMPONENTS)
    full_lower = full.lower()

    if not full.strip():
        return {
            "overall": 0, "relevance": 0, "completeness": 0, "clarity": 0,
            "structure": 0, "star_structure": 0, "covered": [], "missing": [],
            "engaged": False, "star_components": comp_scores,
        }
    _, word_count, sentences = _hr_word_stats(full)
    expected = _STAR_MARKERS.get("Action", [])
    covered = [k for k in expected if _kw_in(full_lower, k)]
    missing = [k for k in expected if k not in covered]
    coverage = len(covered) / len(expected) if expected else 0.0

    engaged = full.strip() != ""
    relevance = round(min(20, _hr_coverage(full_lower, [
        "team", "deliver", "improve", "lead", "project", "client", "result",
    ]) * 14 + min(6, round(_phrase_similarity(
        (question.get("prompt") or "").lower(), full_lower) * 12))))
    completeness = round(min(20, (word_count / 140) * 12)) if engaged else 0
    if engaged:
        completeness = round(min(20, completeness + min(8, sentences * 2)))
    structure_marks = sum(
        1 for m in _HR_STRUCTURE_MARKERS if _hr_kw_in(full_lower.replace("-", " "), m)
    )
    hedging = sum(1 for h in _HEDGING_MARKERS if h in full_lower)
    clarity = round(min(20, 6 + min(8, sentences * 2) + min(6, structure_marks * 2) - min(4, hedging * 2)))

    overall = min(100, star_structure + relevance + completeness + clarity)
    return {
        "overall": overall,
        "relevance": relevance, "completeness": completeness, "clarity": clarity,
        "structure": star_structure, "star_structure": star_structure,
        "covered": covered, "missing": missing, "engaged": engaged,
        "star_components": comp_scores,
    }


def _hr_feedback(score, question):
    strengths, weaknesses, suggestions, tips = [], [], [], []
    if score["overall"] >= 75:
        strengths.append("Well-structured, relevant and complete answer.")
    elif score["overall"] >= 50:
        strengths.append("Addresses the core of the question.")
    if score["relevance"] >= 20:
        strengths.append("Good alignment with the role / company context.")
    if score["clarity"] >= 14:
        strengths.append("Clear and organised writing.")

    if score["missing"]:
        weaknesses.append(
            "Missing expected themes: " + ", ".join(score["missing"][:4]) + "."
        )
    if score["overall"] < 50:
        weaknesses.append("Answer is thin on evidence and structure.")
    if score["clarity"] < 14:
        weaknesses.append("Could be more clearly structured.")
    if question["qtype"] == "star" and score.get("star_structure", 0) < 24:
        weaknesses.append("STAR components are incomplete — address every part.")

    if score["overall"] < 75:
        suggestions.append("Add one concrete work example that demonstrates the behaviour.")
    if score["relevance"] < 20:
        suggestions.append("Tie the answer explicitly to the target role and company.")
    if score["clarity"] < 14:
        suggestions.append("Use an intro–detail–conclusion structure with transition words.")
    if question["qtype"] == "star" and score.get("star_structure", 0) < 24:
        suggestions.append("Separate Situation, Task, Action, and Result clearly.")
    if question["qtype"] == "star":
        comps = score.get("star_components", {})
        if comps.get("Result", {}).get("score", 20) < 10:
            suggestions.append("Quantify your Result (metrics, % change, time saved).")

    tips.append("Keep each part to 2–4 focused sentences.")
    tips.append("Use specific, truthful examples rather than generic claims.")
    tips.append("End with the outcome and what you learned from it.")

    return {
        "strengths": strengths or ["Question attempted — build on this."],
        "weaknesses": weaknesses or ["No significant weaknesses detected."],
        "suggestions": suggestions or ["Add a concise concrete example."],
        "tips": tips,
    }


def evaluate_hr_responses(questions, answers_dict):
    report_data, total_score = [], 0
    for q in questions:
        idx = q["idx"]
        if q["qtype"] == "hr":
            text = (answers_dict.get(f"hr-{idx}") or "").strip()
            score = _score_hr_answer(q, text)
            answer_display = text or "*[No Response Submitted - Left Blank]*"
        else:
            component_answers = {}
            for comp in _STAR_COMPONENTS:
                component_answers[comp] = (answers_dict.get(f"star-{idx}-{comp.lower()}") or "")
            joined = " ".join(component_answers[c] for c in _STAR_COMPONENTS).strip()
            score = _score_star_answer(q, component_answers)
            answer_display = joined or "*[No Response Submitted - Left Blank]*"

        feedback = _hr_feedback(score, q)
        total_score += score["overall"]
        report_data.append({
            "idx": idx,
            "qtype": q["qtype"],
            "category": q.get("category", "Behavioral"),
            "title": q.get("question") or q.get("prompt") or "",
            "answer": answer_display,
            "overall": score["overall"],
            "relevance": score["relevance"],
            "completeness": score["completeness"],
            "clarity": score["clarity"],
            "structure": score["structure"],
            "star_structure": score["star_structure"],
            "covered": score["covered"],
            "missing": score["missing"],
            "strengths": feedback["strengths"],
            "weaknesses": feedback["weaknesses"],
            "suggestions": feedback["suggestions"],
            "tips": feedback["tips"],
        })

    max_total = len(questions) * 100
    percent = round((total_score / max_total) * 100, 1) if max_total else 0.0
    hr_report = _build_hr_report(report_data, percent)
    return total_score, percent, report_data, hr_report


def _build_hr_report(report_data, final_perc):
    avg = final_perc
    if avg >= 85:
        band = "Excellent"
        readiness = "Exceptionally strong HR fit — clearly articulates role alignment."
    elif avg >= 70:
        band = "Good"
        readiness = "Strong HR fit — minor polish needed on evidence and structure."
    elif avg >= 50:
        band = "Average"
        readiness = "Moderate fit — answers need more structure and concrete examples."
    else:
        band = "Needs Improvement"
        readiness = "HR fit requires work — answers are incomplete or off-target."

    cat_scores = {}
    for e in report_data:
        cat_scores.setdefault(e["category"], []).append(e["overall"])
    category_perf = {
        c: round(sum(v) / len(v), 1) for c, v in cat_scores.items()
    }

    top_strengths, gaps = [], []
    for e in report_data:
        for s in e["strengths"]:
            if s not in top_strengths:
                top_strengths.append(s)
        for g in (e["missing"] + e["weaknesses"]):
            if g not in gaps:
                gaps.append(g)

    return {
        "overall_hr_score": sum(e["overall"] for e in report_data),
        "average_score": round(avg, 1),
        "hiring_band": band,
        "readiness": readiness,
        "category_performance": category_perf,
        "top_strengths": top_strengths[:6],
        "knowledge_gaps": gaps[:6],
    }

# =========================================================================
# 3. WORKSPACE PROCTOR & ANTI-CHEATING INTERCEPTOR
# =========================================================================

_WORKSPACE_PASTE_INTERCEPTOR = """
    <script>
        const interceptPasteEvents = () => {
            const workspaceDoc = window.parent.document;
            const activeTextareas = workspaceDoc.querySelectorAll('textarea');
            const toastNode = workspaceDoc.getElementById('secure-toast-container');
            activeTextareas.forEach(field => {
                if (!field.dataset.pasteProtected) {
                    field.dataset.pasteProtected = "true";
                    field.addEventListener('paste', (event) => {
                        event.preventDefault();
                        event.stopPropagation();
                        if (toastNode) {
                            toastNode.style.display = 'block';
                            setTimeout(() => { toastNode.style.display = 'none'; }, 4000);
                        }
                        return false;
                    }, true);
                }
            });
        };
        setInterval(interceptPasteEvents, 700);
    </script>
"""

# Anti-cheating and device check button identifiers
_PROCTOR_VIOLATION_BTN_LABEL = "PROCTOR_SECURITY_VIOLATION_TRIGGER"
_DEVICE_CHECK_TRIGGER_LABEL = "DEVICE_CHECK_VERIFIED_TRIGGER"



_DEVICE_CHECK_TRIGGER_LABEL = "DEVICE_CHECK_VERIFIED_TRIGGER"
_PROCTOR_VIOLATION_BTN_LABEL = "PROCTOR_SECURITY_VIOLATION_TRIGGER"

__DEVICE_CHECK_HTML = """
    <div id="device-check-container" style="background:#ffffff; border:1px solid #cbd5e1; border-radius:12px; padding:28px; max-width:760px; margin: 10px auto; font-family:system-ui,sans-serif; box-shadow:0 8px 24px rgba(0,0,0,0.08);">
        <h3 style="margin-top:0; color:#0f172a; font-size:20px;">🔒 Mandatory Proctored Device &amp; Face Check</h3>
        <p style="color:#64748b; font-size:14px; line-height:1.5; margin-bottom: 15px;">Please allow camera and microphone permissions. Ensure your face is visible. Click below to verify your hardware.</p>
        
        <div style="display:flex; gap:24px; flex-wrap:wrap;">
            <div style="flex:1; min-width:300px; background:#0f172a; border-radius:10px; height:200px; position:relative; overflow:hidden; display:flex; align-items:center; justify-content:center;">
                <video id="live-cam-preview" autoplay playsinline muted style="width:100%; height:100%; object-fit:cover; transform: scaleX(-1);"></video>
                <div style="position:absolute; bottom:12px; left:12px; background:rgba(0,0,0,0.7); color:#fff; padding:5px 12px; border-radius:6px; font-size:12px; font-weight:bold;" id="cam-status-label">Initializing...</div>
            </div>

            <div style="flex:1; min-width:280px; display:flex; flex-direction:column; justify-content:space-between;">
                <div>
                    <label style="font-size:13px; font-weight:bold; color:#334155; display:block; margin-bottom:6px;">📹 Video devices</label>
                    <select id="video-select" style="width:100%; padding:8px; border-radius:6px; border:1px solid #cbd5e1; font-size:13px; margin-bottom:12px; background:#f8fafc;"></select>

                    <label style="font-size:13px; font-weight:bold; color:#334155; display:block; margin-bottom:6px;">🎙️ Audio devices</label>
                    <select id="audio-select" style="width:100%; padding:8px; border-radius:6px; border:1px solid #cbd5e1; font-size:13px; background:#f8fafc;"></select>
                </div>
                <div id="verification-msg" style="font-size:13px; font-weight:bold; color:#16a34a; margin-top:8px;">
                    ✅ Camera and Microphone detected.
                </div>
            </div>
        </div>
    </div>

    <script>
    (function() {
        var videoEl = document.getElementById('live-cam-preview');
        var vidSelect = document.getElementById('video-select');
        var audSelect = document.getElementById('audio-select');
        var statusLabel = document.getElementById('cam-status-label');
        var activeStream = null;

        function startVideoFeed(vidId, audId) {
            if (activeStream) {
                activeStream.getTracks().forEach(t => t.stop());
            }

            var constraints = {
                video: vidId ? { deviceId: { exact: vidId } } : true,
                audio: audId ? { deviceId: { exact: audId } } : true
            };

            navigator.mediaDevices.getUserMedia(constraints).then(function(stream) {
                activeStream = stream;
                videoEl.srcObject = stream;
                videoEl.play().catch(function(e){});
                
                statusLabel.innerText = "Camera Active";
                statusLabel.style.background = "rgba(22,163,74,0.85)";
            }).catch(function(err) {
                statusLabel.innerText = "Error";
            });
        }

        function loadDeviceList() {
            navigator.mediaDevices.enumerateDevices().then(function(devices) {
                vidSelect.innerHTML = '';
                audSelect.innerHTML = '';
                devices.forEach(function(d) {
                    var opt = document.createElement('option');
                    opt.value = d.deviceId;
                    if (d.kind === 'videoinput') {
                        opt.text = d.label || 'Camera ' + (vidSelect.length + 1);
                        vidSelect.appendChild(opt);
                    } else if (d.kind === 'audioinput') {
                        opt.text = d.label || 'Microphone ' + (audSelect.length + 1);
                        audSelect.appendChild(opt);
                    }
                });
                startVideoFeed(vidSelect.value, audSelect.value);
            });
        }

        vidSelect.onchange = function() { startVideoFeed(vidSelect.value, audSelect.value); };
        audSelect.onchange = function() { startVideoFeed(vidSelect.value, audSelect.value); };

        navigator.mediaDevices.getUserMedia({ video: true, audio: true }).then(function(s) {
            loadDeviceList();
        }).catch(function() {});
    })();
    </script>
"""

def _render_device_check_gate(key_suffix=""):
    if st.session_state.get("device_check_passed"):
        return True

    st.components.v1.html(__DEVICE_CHECK_HTML, height=360)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.info("💡 **Instructions:** Verify your camera feed above, then click below to launch the secure assessment workspace.")

    if st.button("🚀 Start Assessment & Enter Workspace", type="primary", key=f"stable_start_btn_{key_suffix}"):
        st.session_state.device_check_passed = True
        st.rerun()

    return False

_WORKSPACE_SECURITY_JS = """
<script>
(function () {
  var P = window.parent;
  var cfg = { forceFs: __FORCE_FS__, label: "__VIOLATION_LABEL__", nonce: "__NONCE__" };

  // This function is re-created inside the PARENT window so timers and listeners
  // survive Streamlit re-renders (which destroy this iframe).
  function engine(cfg) {
    var P = window, D = document;
    var FS_GRACE_MS = 20000, CAM_GRACE_MS = 10000, WARMUP_MS = 5000, FACE_WARMUP_MS = 8000;
    var BLANK_LIMIT = 3, NOFACE_LIMIT = 4;

    var S = P.__proctorS;
    if (!S) {
      S = P.__proctorS = { armed: false, terminated: false, nonce: null, armedAt: 0,
        fsEntered: false, forceFs: true, label: "", blank: 0, noFace: 0, busy: false,
        bound: false, violations: [], reasons: [] };
    }
    S.forceFs = cfg.forceFs;
    S.label = cfg.label;

    function isFs() { return !!(D.fullscreenElement || D.webkitFullscreenElement || D.mozFullScreenElement); }
    function reqFs() {
      try {
        var e = D.documentElement;
        var f = e.requestFullscreen || e.webkitRequestFullscreen || e.mozRequestFullScreen;
        if (f) { var r = f.call(e); if (r && r.catch) r.catch(function () {}); }
      } catch (x) {}
    }
    function saveFinal() {
      try {
        P.sessionStorage.setItem("__proctorFinal", JSON.stringify({
          score: S.terminated ? 0 : 100, violations: S.violations,
          reasons: S.reasons, terminated: S.terminated }));
      } catch (x) {}
    }
    function stopCam() {
      var s = P.__globalCamStream;
      if (s) { try { s.getTracks().forEach(function (t) { t.stop(); }); } catch (x) {} }
      P.__globalCamStream = null;
    }
    function findTriggerButton() {
      var btns = D.querySelectorAll("button");
      for (var i = 0; i < btns.length; i++) {
        if ((btns[i].textContent || "").indexOf(S.label) >= 0) return btns[i];
      }
      return null;
    }
    function hideTrigger() {
      var b = findTriggerButton();
      if (b) {
        var box = b.closest('[data-testid="stElementContainer"], .element-container') || b;
        box.style.display = "none";
      }
    }
    function returnToMenu() {
      var b = findTriggerButton();
      if (b) b.click(); else P.location.reload();
    }
    function showOverlay(reason) {
      if (D.getElementById("__proctor_overlay")) return;
      var ov = D.createElement("div");
      ov.id = "__proctor_overlay";
      ov.style.cssText = "position:fixed;inset:0;z-index:2147483647;background:rgba(127,29,29,0.96);display:flex;align-items:center;justify-content:center;padding:24px;font-family:system-ui,Arial,sans-serif;";
      ov.innerHTML = '<div style="max-width:620px;width:100%;text-align:center;background:#fff;color:#111827;border-radius:16px;padding:34px 28px;box-shadow:0 24px 70px rgba(0,0,0,.45);">' +
        '<div style="font-size:52px;">🚨</div>' +
        '<h2 style="margin:12px 0 8px;color:#dc2626;font-size:24px;">Assessment Terminated</h2>' +
        '<p style="margin:0 0 18px;font-size:15px;color:#4b5563;line-height:1.5;"></p>' +
        '<button type="button" style="background:#2563eb;color:#fff;border:none;border-radius:8px;padding:10px 22px;font-size:14px;font-weight:600;cursor:pointer;">Return to Mode Selection</button></div>';
      ov.querySelector("p").textContent = reason;
      ov.querySelector("button").addEventListener("click", returnToMenu);
      D.body.appendChild(ov);
    }
    function terminate(reason) {
      if (S.terminated) return;
      S.terminated = true;
      S.reasons.push(reason);
      S.violations.push({ label: reason, at: Date.now() });
      saveFinal();
      stopCam();
      showOverlay(reason);
    }
    function attachStream(v) {
      var s = P.__globalCamStream;
      if (s && s.getVideoTracks().length && s.getVideoTracks()[0].readyState === "live") {
        v.srcObject = s; v.play().catch(function () {}); return;
      }
      if (P.__camPending) return;
      P.__camPending = true;
      navigator.mediaDevices.getUserMedia({ video: true, audio: true }).then(function (st) {
        P.__globalCamStream = st; v.srcObject = st; v.play().catch(function () {}); P.__camPending = false;
      }).catch(function () { P.__camPending = false; });
    }
    function ensureUi() {
      if (!D.getElementById("secure-workspace-bar")) {
        var bar = D.createElement("div");
        bar.id = "secure-workspace-bar";
        bar.style.cssText = "position:fixed;top:10px;left:50%;transform:translateX(-50%);z-index:2147483645;background:#0f172a;color:#fff;padding:8px 16px;border-radius:999px;display:flex;align-items:center;gap:12px;font:600 13px system-ui,sans-serif;box-shadow:0 6px 20px rgba(15,23,42,.35);";
        bar.innerHTML = '<span style="width:10px;height:10px;background:#22c55e;border-radius:50%;box-shadow:0 0 8px #22c55e;"></span>' +
          '<span id="secure-bar-status"></span>' +
          '<button id="fs-trigger-btn" type="button" style="background:#2563eb;color:#fff;border:none;padding:6px 12px;border-radius:999px;font-size:12px;font-weight:700;cursor:pointer;">Enter full-screen</button>';
        D.body.appendChild(bar);
        bar.querySelector("#fs-trigger-btn").addEventListener("click", reqFs);
      }
      if (!D.getElementById("cam-container")) {
        var box = D.createElement("div");
        box.id = "cam-container";
        box.style.cssText = "position:fixed;bottom:15px;right:15px;width:140px;height:105px;background:#000;border:2px solid #2563eb;border-radius:8px;z-index:2147483644;overflow:hidden;box-shadow:0 4px 16px rgba(0,0,0,.4);";
        var v = D.createElement("video");
        v.id = "workspace-cam-vid"; v.autoplay = true; v.playsInline = true; v.muted = true;
        v.style.cssText = "width:100%;height:100%;object-fit:cover;transform:scaleX(-1);";
        var badge = D.createElement("div");
        badge.style.cssText = "position:absolute;bottom:4px;left:4px;background:rgba(0,0,0,.7);color:#22c55e;font-size:9px;padding:2px 6px;border-radius:4px;font-weight:bold;";
        badge.textContent = "LIVE REC";
        box.appendChild(v); box.appendChild(badge);
        D.body.appendChild(box);
        attachStream(v);
      }
    }
    function updateBar(fs, el) {
      var st = D.getElementById("secure-bar-status"), btn = D.getElementById("fs-trigger-btn");
      if (!st || !btn) return;
      if (fs || !S.forceFs) {
        st.textContent = "Secure proctored session active · camera & full-screen monitored";
        btn.style.display = "none";
      } else {
        var left = Math.max(0, Math.ceil((FS_GRACE_MS - el) / 1000));
        st.textContent = S.fsEntered ? "Return to full-screen" : "Enter full-screen within " + left + "s to continue";
        btn.style.display = "inline-block";
      }
    }
    function isBlank(v) {
      try {
        var c = D.createElement("canvas"); c.width = 32; c.height = 24;
        var x = c.getContext("2d"); x.drawImage(v, 0, 0, 32, 24);
        var d = x.getImageData(0, 0, 32, 24).data, n = d.length / 4, sum = 0, sq = 0, i, g;
        for (i = 0; i < d.length; i += 4) { g = (d[i] + d[i + 1] + d[i + 2]) / 3; sum += g; sq += g * g; }
        var mean = sum / n, std = Math.sqrt(Math.max(0, sq / n - mean * mean));
        return mean < 10 || std < 4;
      } catch (e) { return false; }
    }
    function tick() {
      if (!S.armed || S.terminated) return;
      var el = Date.now() - S.armedAt, fs = isFs();
      if (fs) S.fsEntered = true;
      hideTrigger();
      updateBar(fs, el);

      if (S.forceFs) {
        if (S.fsEntered && !fs) { terminate("You exited full-screen mode during the assessment. The test has been terminated."); return; }
        if (!S.fsEntered && el > FS_GRACE_MS) { terminate("Full-screen mode was not enabled within 20 seconds. The test has been terminated."); return; }
      }
      var s = P.__globalCamStream, v = D.getElementById("workspace-cam-vid");
      if (s) {
        var t = s.getVideoTracks()[0];
        if (!t || !t.enabled || t.readyState !== "live") { terminate("The camera was turned off or disconnected. The test has been terminated."); return; }
        if (v && !v.srcObject) attachStream(v);
      } else if (el > CAM_GRACE_MS) {
        terminate("Camera access is unavailable. A working camera is required. The test has been terminated."); return;
      }
      if (v && v.readyState >= 2 && el > WARMUP_MS) {
        if (isBlank(v)) {
          S.blank++;
          if (S.blank >= BLANK_LIMIT) { terminate("The camera feed is blank or covered. The test has been terminated."); return; }
        } else { S.blank = 0; }
      }
    }
    function loadScript(src, testFn) {
      return new Promise(function (resolve, reject) {
        if (testFn && testFn()) { resolve(); return; }
        var sc = D.createElement("script");
        sc.src = src; sc.onload = function () { resolve(); };
        sc.onerror = function () { reject(new Error("load failed")); };
        D.head.appendChild(sc);
      });
    }
    function ensureFaceModel() {
      if (P.__faceModelPromise) return;
      P.__faceModelPromise = loadScript("https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@3.18.0/dist/tf.min.js", function () { return !!P.tf; })
        .then(function () { return loadScript("https://cdn.jsdelivr.net/npm/@tensorflow-models/blazeface@0.0.7/dist/blazeface.min.js", function () { return !!P.blazeface; }); })
        .then(function () { return P.blazeface.load(); })
        .then(function (m) { P.__faceModel = m; return m; })
        .catch(function () { P.__faceModel = null; return null; });
    }
    function faceTick() {
      if (!S.armed || S.terminated || S.busy) return;
      if (Date.now() - S.armedAt < FACE_WARMUP_MS) return;
      var m = P.__faceModel, v = D.getElementById("workspace-cam-vid");
      if (!m || !v || v.readyState < 2) return;
      S.busy = true;
      m.estimateFaces(v, false).then(function (faces) {
        var ok = (faces || []).filter(function (f) {
          var p = f.probability, pr = (p && p.length !== undefined) ? p[0] : p;
          return pr === undefined || pr > 0.7;
        });
        if (ok.length === 0) {
          S.noFace++;
          if (S.noFace >= NOFACE_LIMIT) terminate("No face detected. Your face must stay visible during the assessment. The test has been terminated.");
        } else { S.noFace = 0; }
        S.busy = false;
      }).catch(function () { S.busy = false; });
    }

    // ---- arm / re-arm ----
    if (S.nonce !== cfg.nonce) {
      S.nonce = cfg.nonce; S.terminated = false; S.violations = []; S.reasons = []; S.fsEntered = false;
      try { P.sessionStorage.removeItem("__proctorFinal"); } catch (x) {}
    }
    if (S.terminated) { showOverlay(S.reasons[S.reasons.length - 1] || "Assessment terminated."); return; }
    if (!S.armed) { S.armed = true; S.armedAt = Date.now(); S.fsEntered = isFs(); S.blank = 0; S.noFace = 0; }
    ensureUi();
    ensureFaceModel();
    if (!S.bound) {
      S.bound = true;
      P.setInterval(tick, 500);
      P.setInterval(faceTick, 1000);
      ["fullscreenchange", "webkitfullscreenchange", "mozfullscreenchange"].forEach(function (ev) { D.addEventListener(ev, tick); });
      // Any click is a user gesture: use it to (re-)enter full-screen.
      D.addEventListener("click", function () { if (S.armed && !S.terminated && S.forceFs && !isFs()) reqFs(); }, true);
    }
    tick();
  }

  try {
    var parentEngine = new P.Function("return (" + engine.toString() + ");")();
    parentEngine(cfg);
  } catch (e) {}
})();
</script>
"""


def _render_workspace_security(submit_label="", force_fullscreen=True, key_suffix=""):
    """Arms proctoring (full-screen lock, camera off / blank / no-face detection).
    No-op unless the live assessment is actually in progress."""
    if not _proctor_should_be_active():
        return
    st.session_state["_proctor_live"] = True

    # Hidden bridge button: the browser clicks it on a violation so Python resets
    # the session cleanly without losing the candidate's resume / role / company.
    if not st.session_state.get("_viol_btn_drawn"):
        st.session_state["_viol_btn_drawn"] = True
        if st.button(_PROCTOR_VIOLATION_BTN_LABEL, key="proctor_violation_btn"):
            _apply_security_wizard_reset(True)

    html = (
        _WORKSPACE_SECURITY_JS
        .replace("__FORCE_FS__", "true" if force_fullscreen else "false")
        .replace("__VIOLATION_LABEL__", _PROCTOR_VIOLATION_BTN_LABEL)
        .replace("__NONCE__", str(st.session_state.get(_PROCTOR_NONCE_KEY, 0)))
    )
    st.components.v1.html(html, height=0)

    
def _render_integrity_report():
    st.components.v1.html(
        """
        <div style="border:1px solid #e2e8f0;border-radius:12px;padding:14px 18px;background:linear-gradient(180deg,#f8fafc,#f1f5f9);font-family:system-ui,Arial,sans-serif;">
          <div style="font-size:15px;font-weight:700;color:#1e293b;">🛡️ Integrity / Anti-Cheating Report</div>
          <div id="proctor-integrity-body" style="margin-top:8px;font-size:14px;color:#334155;">Reading browser monitoring data…</div>
        </div>
        <script>
        (function () {
            var body = document.getElementById("proctor-integrity-body");
            if (!body) return;
            var fin = null;
            try { fin = JSON.parse(sessionStorage.getItem("__proctorFinal") || "null"); } catch (e) {}
            if (!fin) fin = { score: 100, violations: [], reasons: [], terminated: false };
            var score = Math.max(0, Math.min(100, fin.score | 0));
            var color = fin.terminated ? "#dc2626" : (score >= 90 ? "#16a34a" : (score >= 60 ? "#d97706" : "#dc2626"));
            var parts = [];
            parts.push("Score: <b style='color:" + color + ";font-size:20px;'>" + score + "/100</b>");
            if (fin.terminated) parts.push("<b style='color:#dc2626;'>Assessment Terminated</b>");
            if (fin.reasons && fin.reasons.length) {
                parts.push("Reason: <span style='color:#7f1d1d;'>" + fin.reasons.join("; ") + "</span>");
            } else if (fin.violations && fin.violations.length) {
                var flags = fin.violations.slice(0, 3).map(function (v) { return v.label; });
                parts.push("Flags: <span style='color:#92400e;'>" + flags.join("; ") + "</span>");
            } else {
                parts.push("<span style='color:#16a34a;'>No integrity violations detected during the assessment.</span>");
            }
            body.innerHTML = parts.join(" &nbsp;·&nbsp; ");
        })();
        </script>
        """,
        height=110,
    )
    
# =========================================================================
# 4. WIZARD WORKFLOW ROUTING
# =========================================================================

st.session_state["_viol_btn_drawn"] = False
_sync_proctor_state()
_render_app_header()
_render_step_progress(st.session_state.wizard_step)

# --- STEP 1: CANDIDATE PROFILE & RESUME UPLOAD ---
if st.session_state.wizard_step == 1:
    with st.container(border=True):
        _render_section_header(
            "📁",
            "Step 1 — Candidate Profile &amp; Resume Upload",
            "Create your candidate profile and upload your resume. The system extracts your basic information, skills, education, experience, projects, and role alignment.",
        )

        st.markdown("##### 👤 Candidate Profile Setup")
        candidate_login_name = st.text_input(
            "Candidate Full Name",
            value=st.session_state.get("candidate_name", "Candidate Profile"),
            key="login_name_input",
        )
        st.session_state.candidate_name = candidate_login_name

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("##### 📄 Resume Document Upload")
        resume_file = st.file_uploader(
            "Upload Professional Resume (PDF format)", type=["pdf"], key="step1_resume_uploader"
        )

        if resume_file is not None:
            _sig = (resume_file.name, resume_file.size)
            if st.session_state.get("_resume_sig") != _sig:
                raw_text = extract_text_from_pdf(resume_file)
                if raw_text.strip():
                    st.session_state._resume_sig = _sig
                    st.session_state.resume_raw_text = raw_text
                    with st.spinner("Classifying role using DistilBERT model..."):
                        st.session_state.identified_role = predict_role_distilbert(raw_text)
                    with st.spinner("Extracting profile intelligence via local Qwen2.5 parser..."):
                        sk_dict, pr_list = extract_resume_data_with_qwen(raw_text)
                        st.session_state.extracted_skills_dict = sk_dict
                        st.session_state.extracted_projects = pr_list
                else:
                    st.error("Could not read any text from this PDF. Please upload a text-based resume.")

        if st.session_state.get("resume_raw_text"):
            st.success("✅ Resume uploaded, parsed, and analyzed successfully.")

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("##### 🕸️ External Professional Links")

            kg_col1, kg_col2, kg_col3 = st.columns(3)
            with kg_col1:
                linkedin_raw = st.text_input(
                    "LinkedIn Profile URL",
                    value=st.session_state.candidate_linkedin_url,
                    placeholder="https://linkedin.com/in/username",
                    key="linkedin_url_field",
                )
                li_valid, li_clean, li_err = validate_profile_link(
                    linkedin_raw,
                    "LinkedIn Profile URL",
                    "linkedin.com",
                    [d for d in KNOWLEDGE_GRAPH_DOMAINS if d[0] != "LinkedIn"],
                )
                if li_valid:
                    st.session_state.candidate_linkedin_url = li_clean
                else:
                    st.error(li_err)

            with kg_col2:
                github_raw = st.text_input(
                    "GitHub Profile URL",
                    value=st.session_state.candidate_github_url,
                    placeholder="https://github.com/username",
                    key="github_url_field",
                )
                gh_valid, gh_clean, gh_err = validate_profile_link(
                    github_raw,
                    "GitHub Profile URL",
                    "github.com",
                    [d for d in KNOWLEDGE_GRAPH_DOMAINS if d[0] != "GitHub"],
                )
                if gh_valid:
                    st.session_state.candidate_github_url = gh_clean
                else:
                    st.error(gh_err)

            with kg_col3:
                portfolio_raw = st.text_input(
                    "Portfolio Website",
                    value=st.session_state.candidate_portfolio_url,
                    placeholder="https://yourportfolio.com",
                    key="portfolio_url_field",
                )
                pf_valid, pf_clean, pf_err = validate_profile_link(
                    portfolio_raw,
                    "Portfolio Website",
                    None,
                    KNOWLEDGE_GRAPH_DOMAINS,
                )
                if pf_valid:
                    st.session_state.candidate_portfolio_url = pf_clean
                else:
                    st.error(pf_err)

        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("Proceed to Candidate Analysis ➡️", type="primary", use_container_width=True):
            if st.session_state.get("resume_raw_text"):
                st.session_state.wizard_step = 2
                st.rerun()
            else:
                st.warning("Please upload a valid PDF resume asset to proceed.") # <--- EXTRA PARENTHESIS HERE
# --- STEP 2: AI CANDIDATE PROFILE ANALYSIS ---
elif st.session_state.wizard_step == 2:
    with st.container(border=True):
        resume_text_for_analysis = st.session_state.resume_raw_text
        candidate_name = extract_candidate_name(resume_text_for_analysis)
        candidate_initials = get_initials(candidate_name)

        _render_section_header(
            "🧠",
            "Step 2 — AI Candidate Profile Analysis",
            "The AI analyzes the uploaded resume and identifies the candidate's skills, projects, experience, suitable role, strengths, and potential skill gaps.",
        )

        extracted_skills_dict = st.session_state.get("extracted_skills_dict") or {}
        extracted_projects = st.session_state.get("extracted_projects") or []
        if not extracted_skills_dict and not extracted_projects:
            with st.spinner("Analyzing resume with the local Qwen2.5 model..."):
                extracted_skills_dict, extracted_projects = extract_resume_data_with_qwen(
                    resume_text_for_analysis
                )
                st.session_state.extracted_skills_dict = extracted_skills_dict
                st.session_state.extracted_projects = extracted_projects
        if not st.session_state.identified_role:
            with st.spinner("Classifying role..."):
                st.session_state.identified_role = predict_role_distilbert(resume_text_for_analysis)

        ats_score = compute_ats_score(resume_text_for_analysis)
        strength_score = compute_resume_strength_score(resume_text_for_analysis)

        st.markdown(
            f"""
            <div style="display:flex; flex-direction:column; align-items:center; margin: 10px 0 20px 0;">
                <div style="width:88px; height:88px; border-radius:50%; background:linear-gradient(135deg,#2563eb,#1d4ed8); color:#ffffff; display:flex; align-items:center; justify-content:center; font-size:28px; font-weight:700; box-shadow:0 4px 12px rgba(37,99,235,0.25);">{candidate_initials}</div>
                <h3 style="margin:10px 0 0 0; color:#0f172a;">{candidate_name}</h3>
                <span style="color:#64748b; font-size:13px;">Candidate Intelligence Graph — AI Analyzed Profile</span>
            </div>
        """,
            unsafe_allow_html=True,
        )

        an_col1, an_col2 = st.columns(2)
        with an_col1:
            st.markdown("##### 🛠️ Extracted Skills &amp; Domains")
            if extracted_skills_dict:
                for sub_cat, skill_items in extracted_skills_dict.items():
                    if skill_items:
                        st.markdown(f"- **{sub_cat}**: {', '.join(skill_items)}.")
            else:
                st.markdown("*No dedicated Skills section detected.*")

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("##### 🤖 Suitable Role Identification (DistilBERT)")
            st.info(f"Predicted Optimal Role: **{st.session_state.identified_role}**")

        with an_col2:
            st.markdown("##### 🗂️ Extracted Projects &amp; Experience")
            if extracted_projects:
                for title, desc in extracted_projects:
                    st.markdown(f"• **{title}**")
                    if desc:
                        st.caption(desc)
            else:
                st.markdown("*No dedicated Projects section detected.*")

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("##### 📈 Profile Strengths &amp; Metrics")
            st.metric("Resume ATS Score", f"{ats_score}/100")
            st.metric("Profile Strength Score", f"{strength_score}/100")

        st.markdown("<br><hr>", unsafe_allow_html=True)
        st.markdown("##### ⚠️ Potential Skill Gaps &amp; Recommendations")
        missing_skills_list = compute_skill_gap_report(
            resume_text_for_analysis,
            extracted_skills_dict,
            st.session_state.identified_role,
            st.session_state.desired_role,
        )

        if missing_skills_list:
            for sk in missing_skills_list[:5]:
                st.markdown(f"- ⚠️ **Identified Skill Gap:** {sk}")
        else:
            st.success("✅ No critical skill gaps detected for the primary role taxonomy.")

        st.markdown("<br><br>", unsafe_allow_html=True)
        col_back, col_next = st.columns(2)
        with col_back:
            if st.button("⬅️ Back to Profile &amp; Resume", use_container_width=True):
                st.session_state.wizard_step = 1
                st.rerun()
        with col_next:
            if st.button("Proceed to Interview Setup (Step 3) ➡️", type="primary", use_container_width=True):
                st.session_state.wizard_step = 3
                st.rerun()
                
# --- STEP 3: ROLE, COMPANY & GAP ANALYSIS ---
elif st.session_state.wizard_step == 3:
    with st.container(border=True):
        _notice = st.session_state.pop("security_notice", None)
        if _notice:
            st.error(_notice)
        resume_text_for_analysis = st.session_state.resume_raw_text
        extracted_projects = st.session_state.get("extracted_projects", [])
        extracted_skills_dict = st.session_state.get("extracted_skills_dict", {})

        ats_score = compute_ats_score(resume_text_for_analysis)
        strength_score = compute_resume_strength_score(resume_text_for_analysis)
        readiness_score = compute_placement_readiness_score(
            ats_score, strength_score
        )

        _render_section_header(
            "🧭",
            "Step 3 · Role, Company &amp; Gap Analysis",
            "Review your resume quality, pick your target role and company, and see what's missing.",
        )

        st.subheader("📋 Resume Quality Analysis")
        map_col1, map_col2, map_col3 = st.columns(3)
        with map_col1:
            st.metric("ATS Score", f"{ats_score}/100")
            st.progress(ats_score / 100)
        with map_col2:
            st.metric("Resume Strength Score", f"{strength_score}/100")
            st.progress(strength_score / 100)
        with map_col3:
            st.metric("Placement Readiness Score", f"{readiness_score}%")
            st.progress(min(readiness_score, 100) / 100)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            f"""
            <div style="background-color: #f0fdf4; padding: 14px; border-radius: 8px; border-left: 4px solid #16a34a; margin-bottom: 15px;">
                <span style="color: #16a34a; font-size: 12px; font-weight: 600; text-transform: uppercase;">🤖 AI Predicted Suitable Role (DistilBERT):</span>
                <h4 style="margin: 2px 0 0 0; color: #14532d;">{st.session_state.identified_role}</h4>
            </div>
        """,
            unsafe_allow_html=True,
        )

        st.subheader("🎯 4. Select Your Desired Role")
        default_idx = (
            IT_ROLES.index(st.session_state.identified_role)
            if st.session_state.identified_role in IT_ROLES
            else 0
        )
        desired_selected = st.selectbox(
            "Desired Professional Role",
            IT_ROLES,
            index=default_idx,
            label_visibility="collapsed",
        )
        st.session_state.desired_role = desired_selected

        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("🏢 5. Select Target Company")
        target_company = st.selectbox(
            "Target Corporation Node", MNC_COMPANIES,
            index=MNC_COMPANIES.index(st.session_state.saved_target_company)
            if st.session_state.saved_target_company in MNC_COMPANIES else 0,
            label_visibility="collapsed",
        )
        st.session_state.saved_target_company = target_company

        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("🧩 6. Missing Skills & Certification Gaps")

        missing_skills_list = compute_skill_gap_report(
            resume_text_for_analysis,
            extracted_skills_dict,
            st.session_state.identified_role,
            st.session_state.desired_role,
        )

        if missing_skills_list:
            st.markdown(
                f"**Missing Skills & Certifications for ({st.session_state.identified_role} / {st.session_state.desired_role}):**"
            )
            for sk in missing_skills_list:
                st.markdown(f"- ⚠️ **Missing Skill/Domain:** {sk}")
        else:
            st.success(
                "✅ You possess all required core skills and certifications for your target focus roles!"
            )

        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("🗂️ Project & Certification Alignment Check")

        is_suitable, suitability_feedback, missing_project_roles = (
            check_project_suitability(
                extracted_projects,
                st.session_state.identified_role,
                st.session_state.desired_role,
            )
        )

        if is_suitable:
            st.success(
                "✅ Your resume projects and portfolio show strong alignment with your target track."
            )
        else:
            st.warning(f"⚠️ {suitability_feedback}")
            for r_target in missing_project_roles:
                st.markdown(f"**💡 Recommended Project Architectures for {r_target}:**")
                all_projs = ROLE_SUGGESTED_PROJECTS.get(r_target, [])
                for proj in all_projs[:3]:
                    st.markdown(f"- 📌 {proj}")

        st.markdown("<br><br>", unsafe_allow_html=True)
        col_back, col_next = st.columns(2)
        with col_back:
            if st.button("⬅️ Back to Step 2", use_container_width=True):
                st.session_state.wizard_step = 2
                st.rerun()
        with col_next:
            if st.button("Proceed to Pathway Selection ➡️", use_container_width=True):
                st.session_state.wizard_step = 4
                st.session_state.selected_module = None
                st.rerun()

# --- STEP 4: SELECT INTERVIEW EXPERIENCE ---
elif st.session_state.wizard_step == 4:
    if st.session_state.get("selected_module") is None:
        with st.container(border=True):
            _render_section_header(
                "🧭",
                "Step 4 — Select Interview Experience",
                "The candidate chooses between two modes: Practice Mode (unlimited practice with immediate feedback) or Interview Mode (realistic, timed and proctored interview simulation).",
            )

            col_practice, col_interview = st.columns(2, gap="large")

            with col_practice:
                _md("""
                <div class="mode-card primary">
                    <span class="mode-tag">Recommended</span>
                    <div class="mode-icon">📚</div>
                    <h3>Practice Mode</h3>
                    <p>Unlimited practice with immediate feedback. Focus on coding challenges and core computer science theory.</p>
                </div>
                """)
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Select Practice Mode 🚀", type="primary", use_container_width=True, key="btn_mode_practice"):
                    st.session_state.selected_module = "coding_theory"
                    st.session_state.current_mode = "Coding Questions"
                    st.rerun()

            with col_interview:
                _md("""
                <div class="mode-card">
                    <span class="mode-tag">Proctored</span>
                    <div class="mode-icon">🏢</div>
                    <h3>Interview Mode</h3>
                    <p>Realistic, timed and proctored interview simulation based on your selected target company's hiring route.</p>
                </div>
                """)
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Select Interview Mode 🏢", use_container_width=True, key="btn_mode_interview"):
                    st.session_state.selected_module = "company_simulation"
                    st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("⬅️ Back to Interview Setup", use_container_width=False, key="back_to_setup_from_mode"):
                st.session_state.wizard_step = 3
                st.rerun()

    # --- 🏢 INTERVIEW MODE (COMPANY-SPECIFIC ROUTEMAP) ---
    elif st.session_state.get("selected_module") == "company_simulation":
        with st.container(border=True):
            _render_section_header(
                "🏢",
                f"Corporate Interview &amp; Hiring Roadmap: {st.session_state.saved_target_company}",
                "Explore level-wise compensation packages, screening benchmarks, and technical round progression.",
            )

            vault_data = {}
            if os.path.exists(COMPANY_HIRE_VAULT_FILE):
                try:
                    with open(COMPANY_HIRE_VAULT_FILE, "r", encoding="utf-8") as f:
                        vault_data = json.load(f)
                except Exception:
                    vault_data = {}

            companies_list = vault_data.get("companies", [])
            matched_company = next(
                (c for c in companies_list if c.get("company", "").lower() == st.session_state.saved_target_company.lower()),
                None
            )

            if matched_company:
                if matched_company.get("note"):
                    st.info(f"💡 **Note:** {matched_company['note']}")

                levels = matched_company.get("levels", [])
                for lvl in levels:
                    level_name = lvl.get("level", "Level")
                    title = lvl.get("title", "")
                    salary = lvl.get("salary", "N/A")
                    rounds = lvl.get("rounds", [])

                    with st.expander(f"📌 Level: {level_name} — {title}  |  💰 Est. Salary: {salary}", expanded=True):
                        st.markdown("##### 🚀 Interview & Evaluation Route Map:")
                        for r_idx, round_name in enumerate(rounds, 1):
                            st.markdown(
                                f"""
                                <div style="display: flex; align-items: center; background: #f8fafc; padding: 10px 14px; border-radius: 8px; border-left: 4px solid #2563eb; margin-bottom: 8px; border: 1px solid #e2e8f0;">
                                    <div style="background: #2563eb; color: white; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: bold; margin-right: 12px;">{r_idx}</div>
                                    <div style="color: #1e293b; font-weight: 600; font-size: 14px;">{round_name}</div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
            else:
                st.warning(f"No specific roadmap metadata found for {st.session_state.saved_target_company}.")

            st.markdown("<br><hr>", unsafe_allow_html=True)
            st.subheader(f"💻 Start {st.session_state.saved_target_company} Assessment")
            st.caption(
                f"Practice randomized coding questions from the hiring vault for **{st.session_state.saved_target_company}**."
            )

            col_lang, _ = st.columns([1, 1])
            with col_lang:
                st.session_state.selected_programming_language = st.selectbox(
                    "Select Implementation Language for Simulation:",
                    PROGRAMMING_LANGUAGES,
                    index=PROGRAMMING_LANGUAGES.index(st.session_state.get("selected_programming_language", "Python"))
                    if st.session_state.get("selected_programming_language", "Python") in PROGRAMMING_LANGUAGES else 0,
                    key="comp_sim_lang_select_box"
                )

            col_back, col_launch = st.columns(2)
            with col_back:
                if st.button("⬅️ Back to Mode Selection", use_container_width=True, key="back_to_mode_sim"):
                    st.session_state.selected_module = None
                    st.rerun()

            with col_launch:
                if st.button(
                    f"Launch {st.session_state.saved_target_company} Assessment 🚀",
                    type="primary",
                    use_container_width=True,
                    key="launch_sim_assessment"
                ):
                    st.session_state.current_mode = "Coding Questions"
                    st.session_state[_PROCTOR_NONCE_KEY] = int(time.time() * 1000)
                    st.session_state.test_session_active = True
                    st.session_state.final_results_compiled = False
                    st.session_state.generated_questions = []
                    st.session_state.current_coding_idx = 0
                    st.session_state.wizard_step = 5
                    st.rerun()

    # --- 💻 PRACTICE MODE (CODING & THEORY CONFIGURATION PANEL) ---
    elif st.session_state.get("selected_module") == "coding_theory":
        with st.container(border=True):
            st.markdown(
                f"""
                <div style="background-color: #f8fafc; padding: 25px; border-radius: 10px; border-left: 6px solid #2563eb; margin-bottom: 25px;">
                    <span style="color: #64748b; font-size: 12px; font-weight: 600; text-transform: uppercase;">Assessment Profile Bounds</span>
                    <h3 style="margin: 5px 0 2px 0; color: #0f172a; font-size: 20px;">🤖 Predicted: {st.session_state.identified_role}</h3>
                    <h3 style="margin: 0 0 10px 0; color: #2563eb; font-size: 20px;">🎯 Target Desired: {st.session_state.desired_role}</h3>
                    <p style="margin: 0; color: #64748b; font-size: 14px;">Target Corporation: <strong>{st.session_state.saved_target_company}</strong></p>
                </div>
            """,
                unsafe_allow_html=True,
            )

            st.subheader("⚙️ Configure Parameters for Practice Track")
            sub_mode = st.radio(
                "Choose Verification Mode Parameter",
                ["Coding Questions", "Theory Questions"],
                key="practice_sub_mode_radio"
            )
            st.session_state.current_mode = sub_mode

            selected_subject = None
            st.markdown("<br>", unsafe_allow_html=True)

            if st.session_state.current_mode == "Theory Questions":
                selected_subject = st.selectbox(
                    "Select Target Core Subject Specialization Field", CS_SUBJECTS, key="practice_cs_subj"
                )
            else:
                st.subheader("💻 Select Implementation Language")
                st.session_state.selected_programming_language = st.selectbox(
                    "Primary Implementation Language",
                    PROGRAMMING_LANGUAGES,
                    index=0,
                    key="practice_lang_subj"
                )
                st.info(
                    f"💻 Assessment Question Bank Active: Real interview problems will load instantly for **{st.session_state.desired_role}** at **{st.session_state.saved_target_company}**."
                )

            st.markdown("<br><br>", unsafe_allow_html=True)
            col_back, col_next = st.columns(2)
            with col_back:
                if st.button("⬅️ Change Evaluation Pathway", use_container_width=True, key="back_to_mode_practice"):
                    st.session_state.selected_module = None
                    st.rerun()

            with col_next:
                if st.button(
                    "Lock Parameter Bounds & Launch Workspace 🚀",
                    type="primary",
                    use_container_width=True,
                    key="launch_practice_workspace"
                ):
                    st.session_state.saved_selected_subject = (
                        selected_subject if selected_subject else "DSA"
                    )
                    st.session_state[_PROCTOR_NONCE_KEY] = int(time.time() * 1000)
                    st.session_state.test_session_active = True
                    st.session_state.final_results_compiled = False
                    st.session_state.generated_questions = []
                    st.session_state.current_coding_idx = 0
                    st.session_state.wizard_step = 5
                    st.rerun()                 
# --- STEP 5: WORKSPACE & LIVE EVALUATION RUNS ---
elif st.session_state.wizard_step == 5:
    with st.container(border=True):
        # 1. Enforce background proctoring & full-screen lock
        _render_workspace_security("🔒 Submit Assessment", force_fullscreen=True, key_suffix="step5")

        # 2. Camera & Face Verification Gate (Blocks question generation until face is verified)
        if not _render_device_check_gate("step5"):
            st.stop()  # Stops execution until verification passes

        # 3. Once verified, questions generate and load as before
        st.markdown("<br>", unsafe_allow_html=True)

        if "Coding Questions" in st.session_state.current_mode:
            predicted_role = (
                st.session_state.get("identified_role") or "Software Engineer"
            )
            desired_role = (
                st.session_state.get("desired_role") or "Software Engineer"
            )
            target_comp = st.session_state.get("saved_target_company", "Google")
            
            is_company_track = (st.session_state.get("selected_module") == "company_simulation")

            if is_company_track:
                _render_section_header(
                    "🎯",
                    f"Step 5 · {target_comp} Technical Assessment IDE",
                    "Live coding workspace with an offline judge and hidden test cases.",
                )
            else:
                _render_section_header(
                    "🎯",
                    f"Step 5 · {desired_role} Coding IDE",
                    "Live coding workspace with an offline judge and hidden test cases.",
                )

            if not st.session_state.generated_questions:
                with st.spinner("⚡ Extracting company-tagged interview problems from Vault..."):
                    if is_company_track:
                        # Interview Mode -> Uses seed_500_questions (5 unique coding questions)
                        st.session_state.generated_questions = seed_500_questions(
                            desired_role=desired_role,
                            predicted_role=predicted_role,
                            selected_company=target_comp,
                        )
                    else:
                        # Practice Mode -> Uses ingest_leetcode (5 unique coding questions)
                        st.session_state.generated_questions = ingest_leetcode(
                            desired_role=desired_role,
                            predicted_role=predicted_role,
                            selected_company=target_comp,
                        )
                        
            if st.session_state.final_results_compiled:
                st.header("📊 Completed Coding Track Performance Response Sheet")

                _question_signature = [
                    q.get("id") or q["title"] for q in st.session_state.generated_questions
                ]
                if (
                    st.session_state.coding_grade_results.get("question_signature")
                    != _question_signature
                ):
                    st.session_state.coding_grade_results = {}
                    st.session_state.coding_evaluations = {}

                if not st.session_state.coding_grade_results:
                    total_score = 0
                    audit_logs = []
                    _fallback_lang = st.session_state.get(
                        "selected_programming_language", "Python"
                    )
                    with st.spinner("Compiling & grading submitted solutions locally..."):
                        for idx, q in enumerate(st.session_state.generated_questions):
                            key = f"code-{idx}"
                            code_content = st.session_state.coding_solutions_vault.get(
                                key, ""
                            ).strip()
                            lang = st.session_state.coding_language_vault.get(
                                f"lang-{idx}", _fallback_lang
                            )
                            if lang not in SUPPORTED_LANGUAGES:
                                lang = _fallback_lang
                            expected_output = _clean_test_data(q.get("sample_output", ""))
                            _eval = None

                            if is_empty_solution(code_content, lang):
                                score = 0
                                raw_exec_log = "Not Executed"
                                feedback_text = "❌ No Solution Submitted. (0 Marks)"
                            else:
                                _avail, _reason = language_availability(lang)
                                if not _avail:
                                    score = 0
                                    raw_exec_log = _reason
                                    feedback_text = (
                                        "❌ Solution could not be graded (compiler missing). (0 Marks)"
                                    )
                                else:
                                    _stdin_data = _clean_test_data(q.get("sample_input", ""))
                                    _res = judge_code(
                                        lang, code_content, _stdin_data, expected_output
                                    )
                                    status = _res.get("status")
                                    raw_exec_log = format_judge_result(lang, _res)
                                    _prev_ev = st.session_state.coding_evaluations.get(key) or {}
                                    _eval = build_candidate_evaluation(
                                        q, code_content, lang, status, None,
                                        _prev_ev.get("hidden_result"),
                                    )
                                    st.session_state.coding_evaluations[key] = _eval
                                    if status == "accepted":
                                        score = 20
                                        feedback_text = (
                                            "✅ Accepted: Output matched the expected sample output. (+20 Marks)"
                                        )
                                    elif status == "wrong_answer":
                                        score = 0
                                        feedback_text = (
                                            "❌ Wrong Answer: Output did not match the expected sample output. (0 Marks)"
                                        )
                                    elif status == "compile_error":
                                        score = 0
                                        feedback_text = (
                                            "❌ Compilation Error detected. (0 Marks)"
                                        )
                                    elif status == "runtime_error":
                                        score = 0
                                        feedback_text = "❌ Runtime Error detected. (0 Marks)"
                                    elif status == "time_limit_exceeded":
                                        score = 0
                                        feedback_text = "❌ Time Limit Exceeded. (0 Marks)"
                                    elif status == "memory_limit_exceeded":
                                        score = 0
                                        feedback_text = "❌ Memory Limit Exceeded. (0 Marks)"
                                    else:
                                        score = 0
                                        feedback_text = (
                                            "❌ Judge could not execute the solution. (0 Marks)"
                                        )

                            total_score += score
                            audit_logs.append({
                                "idx": idx + 1,
                                "title": q["title"],
                                "target_alignment": q.get(
                                    "target_alignment", "Engineering"
                                ),
                                "code": code_content,
                                "language": lang,
                                "score": score,
                                "execution_log": raw_exec_log if raw_exec_log else "Not Executed",
                                "expected_output": expected_output or "N/A",
                                "feedback": feedback_text,
                                "_eval": _eval,
                            })
                    st.session_state.coding_grade_results = {
                        "total_score": total_score,
                        "audit_logs": audit_logs,
                        "question_signature": _question_signature,
                    }

                total_score = st.session_state.coding_grade_results["total_score"]
                audit_logs = st.session_state.coding_grade_results["audit_logs"]

                c1, c2 = st.columns(2)
                with c1:
                    st.metric(
                        label="Total Coding Score", value=f"{total_score} / 100 Marks"
                    )
                with c2:
                    st.metric(
                        label="Final Aggregate Percentage",
                        value=f"{(total_score / 100) * 100:.1f}%",
                    )

                _render_integrity_report()

                coding_pct = (total_score / 100) * 100
                st.session_state.coding_final_perc = round(coding_pct, 1)
                
                # --- NEW: PLACEMENT READINESS DASHBOARD ---
                if is_company_track:
                    st.markdown("---")
                    st.subheader("🎓 Placement Readiness Dashboard")
                    # Using resume strength as a proxy for Technical profile score if theory wasn't taken
                    tech_score = compute_resume_strength_score(st.session_state.resume_raw_text) 
                    overall_placement_score = round((coding_pct * 0.6) + (tech_score * 0.4), 1)
                    
                    dash_c1, dash_c2, dash_c3 = st.columns(3)
                    with dash_c1:
                        st.metric("Technical/Profile Score", f"{tech_score}%")
                    with dash_c2:
                        st.metric("Coding Score", f"{coding_pct:.1f}%")
                    with dash_c3:
                        st.metric("Placement Readiness Score", f"{overall_placement_score}%")
                    
                    if overall_placement_score < 50:
                        st.error("🚨 **Placement Readiness: Not Ready.** Your score is below 50%. We highly suggest you improve your coding skills as you are not ready for placement.")
                    else:
                        st.success("✅ **Placement Readiness: Ready.** You have a solid foundational score for placement!")
                # ------------------------------------------

                if coding_pct >= 85:
                    band = "Excellent"
                elif coding_pct >= 70:
                    band = "Good"
                elif coding_pct >= 50:
                    band = "Average"
                else:
                    band = "Needs Improvement"

                col_restart, col_hr = st.columns(2)
                with col_restart:
                    if st.button(
                        "🚀 Start New Assessment Track Sequence",
                        use_container_width=True,
                        key="theory_final_restart_btn",
                    ):
                        st.session_state.final_results_compiled = False
                        st.query_params["restart_required"] = "1"
                        st.rerun()

                with col_hr:
                    if coding_pct >= 60.0:
                        if st.button(
                            "🎯 Proceed to HR Round →",
                            type="primary",
                            use_container_width=True,
                            key="coding_proceed_hr_btn",
                        ):
                            st.session_state.hr_questions = build_hr_questions(
                                desired_role=st.session_state.desired_role,
                                predicted_role=st.session_state.identified_role,
                                company=st.session_state.saved_target_company,
                                assessment_context={
                                    "hiring_band": band,
                                    "track": "Coding",
                                    "track_percent": coding_pct,
                                },
                            )
                            st.session_state.hr_responses_vault = {}
                            st.session_state.hr_results_compiled = False
                            st.session_state.wizard_step = 6
                            st.rerun()
                    else:
                        st.warning("🔒 **HR Round Locked:** You need > 60% score to proceed to the HR round.")

                st.markdown("### 📝 Technical Code Submission Audit")
                for entry in audit_logs:
                    with st.expander(
                        f"Question {entry['idx']}: {entry['title']}"
                        f" ({entry['target_alignment']}) — Mark [{entry['score']}/20]",
                        expanded=True,
                    ):
                        st.code(
                            entry["code"] if entry["code"] else "# No Code Submitted",
                            language=LANGUAGE_CODE_BLOCK_LABELS.get(
                                entry.get("language", "Python"), "text"
                            ),
                        )
                        st.caption("🎯 **Expected Target Output:**")
                        st.code(entry["expected_output"], language="text")
                        if entry["execution_log"]:
                            st.caption("🖥️ **Candidate Execution Console Output:**")
                            st.code(entry["execution_log"], language="text")
                        st.markdown(f"**⚙️ Submission Status:** {entry['feedback']}")
                        _entry_eval = entry.get("_eval")
                        if _entry_eval:
                            st.markdown("---")
                            _render_recruiter_evaluation(_entry_eval["recruiter"])
                            _render_complexity_analysis(_entry_eval["complexity"])
                            _render_code_review(_entry_eval["review"])
                            _render_interview_questions(_entry_eval["questions"])

                _final_perc = (total_score / 100) * 100
                st.markdown("---")
                _render_hiring_feedback(generate_hiring_feedback(_final_perc))

            else:
                st.markdown("### 💻 Interactive Real-Time Coding Workspace")

                _render_workspace_security(
                    "🔒 Submit All Code & Finalize Assessment", 
                    force_fullscreen=True
                )

                total_q = len(st.session_state.generated_questions)
                curr_idx = st.session_state.current_coding_idx

                st.progress((curr_idx + 1) / max(total_q, 1))
                st.caption(f"Question **{curr_idx + 1}** of **{total_q}**")

                if total_q > 0 and curr_idx < total_q:
                    q = st.session_state.generated_questions[curr_idx]
                    key = f"code-{curr_idx}"
                    lang_key = f"lang-{curr_idx}"

                    col_problem, col_editor = st.columns([1, 1], gap="medium")

                    with col_problem:
                        col_q, col_badge = st.columns([3, 1])
                        with col_q:
                            st.markdown(f"#### **Question {curr_idx + 1}: {q['title']}**")
                        with col_badge:
                            if st.session_state.coding_saved_vault[key]:
                                st.markdown(
                                    '<span class="status-locked">Submitted ✔️</span>',
                                    unsafe_allow_html=True,
                                )
                            else:
                                st.markdown(
                                    '<span class="status-pending">In Progress...</span>',
                                    unsafe_allow_html=True,
                                )

                        st.caption(
                            f"🎯 Track: **{q.get('target_alignment', 'Engineering')}**"
                            f" | Company: **{q.get('company', 'Tech')}**"
                            f" | Difficulty: **{q.get('difficulty', 'Medium')}**"
                        )
                        st.markdown(f"*{q['prompt']}*")

                        with st.expander("🧪 View Sample Test Cases", expanded=True):
                            st.code(
                                f"Input: {q.get('sample_input', 'N/A')}\nExpected Output:"
                                f" {q.get('sample_output', 'N/A')}",
                                language="text",
                            )

                    with col_editor:
                        # Top Bar: Code icon + Language Selector
                        st.markdown(
                            "<div style='color:#10b981; font-weight:bold; font-size:16px; margin-bottom: 5px;'>⟨/⟩ Code</div>", 
                            unsafe_allow_html=True
                        )
                        
                        if lang_key not in st.session_state.coding_language_vault:
                            st.session_state.coding_language_vault[lang_key] = st.session_state.get(
                                "selected_programming_language", "Python"
                            )

                        current_q_lang = st.session_state.coding_language_vault[lang_key]
                        if current_q_lang not in PROGRAMMING_LANGUAGES:
                            current_q_lang = "Python"

                        selected_lang = st.selectbox(
                            "Language",
                            PROGRAMMING_LANGUAGES,
                            index=PROGRAMMING_LANGUAGES.index(current_q_lang),
                            key=f"lang_select_{curr_idx}",
                            disabled=st.session_state.coding_saved_vault[key],
                            label_visibility="collapsed"
                        )

                        prev_lang = st.session_state.coding_language_vault.get(lang_key)
                        if selected_lang != prev_lang:
                            st.session_state.coding_language_vault[lang_key] = selected_lang
                            current_code = st.session_state.coding_solutions_vault.get(key, "").strip()
                            is_default_template = not current_code or any(
                                current_code == t.strip() for t in LANGUAGE_TEMPLATES.values()
                            )
                            if is_default_template:
                                st.session_state.coding_solutions_vault[key] = LANGUAGE_TEMPLATES.get(
                                    selected_lang, ""
                                )
                            st.rerun()

                        if not st.session_state.coding_solutions_vault[key].strip():
                            st.session_state.coding_solutions_vault[key] = LANGUAGE_TEMPLATES.get(
                                selected_lang, ""
                            )

                        ace_modes = {
                            "Python": "python",
                            "C": "c_cpp",
                            "C++": "c_cpp",
                            "Java": "java",
                            "C#": "csharp"
                        }

                        # Rich Code Editor
                        code_input = st_ace(
                            value=st.session_state.coding_solutions_vault[key],
                            language=ace_modes.get(selected_lang, "text"),
                            theme="chrome",
                            keybinding="vscode",
                            font_size=14,
                            tab_size=4,
                            show_gutter=True,
                            show_print_margin=False,
                            wrap=False,
                            auto_update=True,
                            readonly=st.session_state.coding_saved_vault[key],
                            key=f"ide_input_{curr_idx}_{selected_lang}",
                            min_lines=16
                        )
                        st.session_state.coding_solutions_vault[key] = code_input

                        # LeetCode Style Editable Testcase Pane
                        st.markdown(
                            "<div style='padding-top:15px; color:#10b981; font-weight:bold; font-size:14px; margin-bottom: -15px;'>☑️ Testcase &nbsp;&nbsp; <span style='color:#64748b; font-weight:normal;'>>_ Test Result</span></div>", 
                            unsafe_allow_html=True
                        )
                        st.markdown("---")
                        
                        parsed_cases = parse_test_cases(q.get("test_cases", ""))
                        if not parsed_cases:
                            parsed_cases = [(q.get("sample_input", "N/A"), q.get("sample_output", "N/A"))]
                            
                        # Initialize session state storage for custom user inputs
                        if f"custom_inputs_{curr_idx}" not in st.session_state:
                            st.session_state[f"custom_inputs_{curr_idx}"] = [c[0] for c in parsed_cases]

                        case_tabs = st.tabs([f"Case {i+1}" for i in range(len(parsed_cases))])
                        for i, tab in enumerate(case_tabs):
                            with tab:
                                st.caption("Input (Editable):")
                                user_input_val = st.text_area(
                                    f"Input Case {i+1}",
                                    value=st.session_state[f"custom_inputs_{curr_idx}"][i],
                                    key=f"custom_input_{curr_idx}_{i}",
                                    height=80,
                                    disabled=st.session_state.coding_saved_vault[key]
                                )
                                st.session_state[f"custom_inputs_{curr_idx}"][i] = user_input_val
                                
                                st.caption("Expected Target:")
                                st.code(parsed_cases[i][1], language="text")

                        st.markdown("<br>", unsafe_allow_html=True)

                        col_run, col_tests, col_lock = st.columns([1.5, 1.5, 2])
                        with col_run:
                            if st.button("▶️ Run Code", key=f"run_btn_{curr_idx}", use_container_width=True):
                                if is_empty_solution(code_input, selected_lang):
                                    st.warning("Please write some code before running.")
                                else:
                                    _avail, _reason = language_availability(selected_lang)
                                    if not _avail:
                                        st.error(_reason)
                                    else:
                                        # Use the custom input from Case 1 (or active testcase)
                                        custom_inputs_list = st.session_state.get(f"custom_inputs_{curr_idx}", [q.get("sample_input", "")])
                                        _stdin_data = _clean_test_data(custom_inputs_list[0] if custom_inputs_list else q.get("sample_input", ""))
                                        _expected = _clean_test_data(parsed_cases[0][1] if parsed_cases else q.get("sample_output", ""))
                                        
                                        with st.spinner(f"Compiling & running {selected_lang} locally with your input..."):
                                            _res = judge_code(
                                                selected_lang, code_input, _stdin_data, _expected
                                            )
                                        st.session_state.coding_execution_logs[key] = format_judge_result(
                                            selected_lang, _res
                                        )
                                        _status = _res.get("status")
                                        if _status == "accepted":
                                            st.success(VERDICT_LABELS[_status])
                                        elif _status in (
                                            "wrong_answer",
                                            "compile_error",
                                            "runtime_error",
                                            "time_limit_exceeded",
                                            "memory_limit_exceeded",
                                        ):
                                            st.error(VERDICT_LABELS[_status])
                                        else:
                                            st.warning(VERDICT_LABELS.get(_status, _status))

                        with col_tests:
                            if st.button("🧪 Run Tests", key=f"tests_btn_{curr_idx}", use_container_width=True):
                                if is_empty_solution(code_input, selected_lang):
                                    st.warning("Please write some code before running.")
                                else:
                                    _avail, _reason = language_availability(selected_lang)
                                    if not _avail:
                                        st.error(_reason)
                                    else:
                                        with st.spinner("Running hidden test cases locally..."):
                                            _hidden = run_hidden_test_cases(
                                                selected_lang, code_input, q.get("test_cases", "")
                                            )
                                        st.session_state.coding_execution_logs[key] = format_hidden_tests_result(
                                            selected_lang, _hidden
                                        )
                                        if _hidden["status"] == "accepted":
                                            st.success(f"All {_hidden['total']} test cases passed!")
                                        elif _hidden["status"] == "no_tests":
                                            st.warning("No hidden test cases available.")
                                        else:
                                            st.error(f"{_hidden['passed']} / {_hidden['total']} test cases passed.")

                        with col_lock:
                            if st.button(
                                f"💾 Submit Q{curr_idx + 1}",
                                key=f"btn_code_{curr_idx}",
                                use_container_width=True,
                                disabled=st.session_state.coding_saved_vault[key],
                            ):
                                st.session_state.coding_saved_vault[key] = True
                                st.success(f"Question {curr_idx + 1} submitted!")
                                st.rerun()

                        if st.session_state.coding_execution_logs[key]:
                            st.markdown("##### 🖥️ Console Output")
                            st.code(st.session_state.coding_execution_logs[key], language="text")
                            
                    st.markdown("---")

                    col_nav_prev, col_nav_next = st.columns(2)
                    with col_nav_prev:
                        if curr_idx > 0:
                            if st.button("⬅️ Previous Question", use_container_width=True):
                                st.session_state.current_coding_idx -= 1
                                st.rerun()

                    with col_nav_next:
                        if curr_idx < total_q - 1:
                            if st.button("Next Question ➡️", use_container_width=True):
                                if not st.session_state.coding_saved_vault[key]:
                                    st.warning("⚠️ Please submit your current solution before moving to the next question.")
                                else:
                                    st.session_state.current_coding_idx += 1
                                    st.rerun()
                        else:
                            if st.button(
                                "🔒 Submit All Code & Finalize Assessment",
                                type="primary",
                                use_container_width=True,
                            ):
                                st.session_state.show_final_results = True
                                st.session_state.test_session_active = False
                                st.session_state.final_results_compiled = True
                                st.rerun()
        # --- ✍️ THEORY QUESTIONS INTERVIEW TRACK WORKSPACE ---
        else:
            _render_section_header(
                "🎯",
                f"Step 5 · {st.session_state.desired_role} Theory Track",
                f"Subject focus: {st.session_state.saved_selected_subject}",
            )
        
            if st.session_state.final_results_compiled:
                total_m, final_perc, audit_logs, theory_report = (
                    evaluate_theory_responses_batched(
                        st.session_state.generated_questions,
                        st.session_state.responses_vault,
                    )
                )
                st.session_state.theory_final_perc = round(final_perc, 1) 
                st.header("📊 Completed Interview Performance Response Sheet")
                c1, c2 = st.columns(2)
                with c1:
                    st.metric(
                        label="Overall Theory Score", value=f"{total_m} / {len(audit_logs) * 100}"
                    )
                with c2:
                    st.metric(label="Average Score", value=f"{final_perc:.1f}%")

                if theory_report:
                    st.markdown("### 🏁 Final Theory Report")
                    diff_perf = theory_report.get("difficulty_performance", {})
                    band = theory_report.get("hiring_band", "Average")
                    band_color = {
                        "Excellent": "#16a34a",
                        "Good": "#2563eb",
                        "Average": "#d97706",
                        "Needs Improvement": "#dc2626",
                    }.get(band, "#64748b")

                    rc1, rc2, rc3 = st.columns(3)
                    with rc1:
                        st.metric("Overall Theory Score", f"{theory_report['overall_theory_score']} / {len(audit_logs) * 100}")
                    with rc2:
                        st.metric("Average Score", f"{theory_report['average_score']:.1f}%")
                    with rc3:
                        st.markdown(
                            f"**Hiring Recommendation:**\n\n"
                            f"<span style='color:{band_color}; font-weight:700; font-size:18px;'>{band}</span>",
                            unsafe_allow_html=True,
                        )
                    st.markdown("#### 📈 Difficulty-wise Performance")
                    dc1, dc2, dc3 = st.columns(3)
                    with dc1:
                        st.metric("Easy", f"{diff_perf.get('Easy', 0):.1f}%")
                    with dc2:
                        st.metric("Medium", f"{diff_perf.get('Medium', 0):.1f}%")
                    with dc3:
                        st.metric("Hard", f"{diff_perf.get('Hard', 0):.1f}%")

                    with st.expander("✅ Top Strengths", expanded=False):
                        for s in theory_report.get("top_strengths", []):
                            st.markdown(f"- {s}")
                    with st.expander("⚠️ Knowledge Gaps", expanded=False):
                        for g in theory_report.get("knowledge_gaps", []):
                            st.markdown(f"- {g}")
                    with st.expander("📚 Recommended Topics to Revise", expanded=False):
                        for t in theory_report.get("revise_topics", []):
                            st.markdown(f"- {t}")
                    with st.expander("🧭 Interview Readiness", expanded=False):
                        st.markdown(theory_report.get("interview_readiness", ""))

                _render_integrity_report()

                col_restart, col_hr = st.columns(2)
                with col_restart:
                    if st.button(
                        "🚀 Start New Assessment Track Sequence",
                        use_container_width=True,
                    ):
                        st.session_state.coding_grade_results = {}
                        st.session_state.final_results_compiled = False
                        st.query_params["restart_required"] = "1"
                        st.rerun()

                with col_hr:
                    if final_perc >= 60.0:
                        if st.button(
                            "🎯 Proceed to HR Round →",
                            type="primary",
                            use_container_width=True,
                        ):
                            st.session_state.hr_questions = build_hr_questions(
                                desired_role=st.session_state.desired_role,
                                predicted_role=st.session_state.identified_role,
                                company=st.session_state.saved_target_company,
                                assessment_context={
                                    "hiring_band": band,
                                    "track": "Theory",
                                    "track_percent": round(final_perc, 1),
                                },
                            )
                            st.session_state.hr_responses_vault = {}
                            st.session_state.hr_results_compiled = False
                            st.session_state.wizard_step = 6
                            st.rerun()
                    else:
                        st.warning("🔒 **HR Round Locked:** You need > 60% score to proceed to the HR round.")
                        
                st.markdown("### 📝 Detailed Solution & Audit Sheet")
                for entry in audit_logs:
                    with st.expander(
                        f"Question {entry['idx']}: Overall [{entry['overall']}/100] "
                        f"· Difficulty: {entry.get('difficulty', 'Medium')}",
                        expanded=True,
                    ):
                        st.markdown(f"**❓ Question Text:** {entry['title']}")
                        st.info(f"**📥 Candidate Saved Response:**\n{entry['answer']}")

                        st.markdown("#### 🧮 Rubric Breakdown")
                        rb1, rb2, rb3, rb4, rb5 = st.columns(5)
                        with rb1:
                            st.metric("Technical Accuracy", f"{entry['ta']}/40")
                        with rb2:
                            st.metric("Formula Correctness", f"{entry['fc']}/20")
                        with rb3:
                            st.metric("Depth", f"{entry['depth']}/15")
                        with rb4:
                            st.metric("Clarity", f"{entry['clarity']}/15")
                        with rb5:
                            st.metric("Industry Relevance", f"{entry['industry']}/10")

                        with st.expander("✅ Strengths", expanded=False):
                            for item in entry.get("strengths", []):
                                st.markdown(f"- {item}")
                        with st.expander("⚠️ Weaknesses", expanded=False):
                            for item in entry.get("weaknesses", []):
                                st.markdown(f"- {item}")
                        with st.expander("❌ Missing Concepts", expanded=False):
                            for item in entry.get("missing_concepts", []):
                                st.markdown(f"- {item.replace('-', ' ').title()}")
                        with st.expander("💡 Suggestions for Improvement", expanded=False):
                            for item in entry.get("suggestions", []):
                                st.markdown(f"- {item}")
                        with st.expander("🗣️ Interview Tips", expanded=False):
                            for item in entry.get("interview_tips", []):
                                st.markdown(f"- {item}")
            else:
                # 🔒 Place proctoring & security interceptor at the top
                _render_workspace_security(
                    "🔒 Lock All Responses & Compile Final Marks Sheet",
                    force_fullscreen=True
                )
                if not st.session_state.generated_questions:
                    subject_tag_filter = (
                        "OS"
                        if "Operating Systems" in st.session_state.saved_selected_subject
                        else "DSA"
                    )
                    with st.spinner("⚡ Extracting theory questions from coding vault..."):
                        # Theory Mode -> Uses ingest_all_coding (10 unique theory questions)
                        st.session_state.generated_questions = ingest_all_coding(
                            company=st.session_state.saved_target_company,
                            predicted_role=st.session_state.identified_role,
                            desired_role=st.session_state.desired_role,
                            subject_tag=subject_tag_filter,
                            count=10,
                        )
                        
                st.caption(
                    "Type your answers below. Save each answer to lock your progress. Scores will be compiled at the end."
                )
                # ⌨️ VIRTUAL NOTATION KEYPAD MANAGER (26-Key Edition)
                st.components.v1.html(
                    """
                        <div class="panel-container" style="font-family: sans-serif; background: #ffffff; border: 1px solid #cbd5e1; padding: 15px; border-radius: 8px; margin-bottom: 5px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                <strong style="font-size: 14px; color: #1e293b;">⌨️ Virtual Notation Keypad Manager (26-Key Edition)</strong>
                                <button id="toggle-kp-btn" onclick="toggleKeypad()" style="background: #f1f3f5; border: 1px solid #cbd5e1; padding: 6px 12px; border-radius: 4px; font-size: 13px; font-weight: bold; cursor: pointer; color: #1e293b;">📂 Open Keypad</button>
                            </div>
                            <div id="keypad-container" style="display: none; background-color: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #ddd;">
                                <div style="margin-bottom: 15px;">
                                    <div style="display: grid; grid-template-columns: repeat(10, 1fr); gap: 4px; margin-bottom: 8px;">
                                        <button class="kp-btn" onmousedown="event.preventDefault()" onclick="insertSymbol('α')">α</button>
                                        <button class="kp-btn" onmousedown="event.preventDefault()" onclick="insertSymbol('β')">β</button>
                                        <button class="kp-btn" onmousedown="event.preventDefault()" onclick="insertSymbol('γ')">γ</button>
                                        <button class="kp-btn" onmousedown="event.preventDefault()" onclick="insertSymbol('δ')">δ</button>
                                        <button class="kp-btn" onmousedown="event.preventDefault()" onclick="insertSymbol('θ')">θ</button>
                                        <button class="kp-btn" onmousedown="event.preventDefault()" onclick="insertSymbol('λ')">λ</button>
                                        <button class="kp-btn" onmousedown="event.preventDefault()" onclick="insertSymbol('μ')">μ</button>
                                        <button class="kp-btn" onmousedown="event.preventDefault()" onclick="insertSymbol('π')">π</button>
                                        <button class="kp-btn" onmousedown="event.preventDefault()" onclick="insertSymbol('σ')">σ</button>
                                        <button class="kp-btn" onmousedown="event.preventDefault()" onclick="insertSymbol('Ω')">Ω</button>
                                    </div>
                                    <div style="display: grid; grid-template-columns: repeat(10, 1fr); gap: 4px; margin-bottom: 12px;">
                                        <button class="kp-btn" onmousedown="event.preventDefault()" onclick="insertSymbol('∑')">∑</button>
                                        <button class="kp-btn" onmousedown="event.preventDefault()" onclick="insertSymbol('∏')">∏</button>
                                        <button class="kp-btn" onmousedown="event.preventDefault()" onclick="insertSymbol('√')">√</button>
                                        <button class="kp-btn" onmousedown="event.preventDefault()" onclick="insertSymbol('∫')">∫</button>
                                        <button class="kp-btn" onmousedown="event.preventDefault()" onclick="insertSymbol('∂')">∂</button>
                                        <button class="kp-btn" onmousedown="event.preventDefault()" onclick="insertSymbol('±')">±</button>
                                        <button class="kp-btn" onmousedown="event.preventDefault()" onclick="insertSymbol('≠')">≠</button>
                                        <button class="kp-btn" onmousedown="event.preventDefault()" onclick="insertSymbol('≤')">≤</button>
                                        <button class="kp-btn" onmousedown="event.preventDefault()" onclick="insertSymbol('≥')">≥</button>
                                        <button class="kp-btn" onmousedown="event.preventDefault()" onclick="insertSymbol('∞')">∞</button>
                                    </div>
                                    <div style="display: grid; grid-template-columns: repeat(6, 1fr); gap: 4px; margin-bottom: 12px;">
                                        <button class="kp-btn layout-btn" style="display: inline-flex; flex-direction: column; align-items: center; justify-content: center; font-size: 10px; font-weight: bold; width: 100%; height: 40px; padding: 2px; line-height: 1;" onmousedown="event.preventDefault()" onclick="insertSymbol('[numerator]\\n───\\n[denominator]')">
                                            <span style="border-bottom: 1px solid #1a1a1a; padding-bottom: 1px; width: 14px; text-align: center;">▢</span>
                                            <span style="padding-top: 1px; width: 14px; text-align: center;">▢</span>
                                        </button>
                                        <button class="kp-btn layout-btn" onmousedown="event.preventDefault()" onclick="insertSymbol('√[ ]')">√[ ]</button>
                                        <button class="kp-btn layout-btn" onmousedown="event.preventDefault()" onclick="insertSymbol('[ ]')">[ ]</button>
                                        <button class="kp-btn layout-btn" onmousedown="event.preventDefault()" onclick="insertSymbol('\\n[ ]\\n[ ] [ ]\\n[ ]\\n')">Limits</button>
                                        <button class="kp-btn layout-btn" style="display: inline-flex; align-items: center; justify-content: center; font-size: 14px; font-weight: bold; width: 100%; height: 40px; padding: 4px 2px;" onmousedown="event.preventDefault()" onclick="insertSymbol('[ ]^[ ]')">
                                            <span>[ ]</span><sup style="font-size: 9px; font-weight: bold; margin-left: 1px;">■</sup>
                                        </button>
                                        <button class="kp-btn layout-btn" onmousedown="event.preventDefault()" onclick="insertSymbol('Log_[ ] [ ]')">Log_[ ]</button>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div id="secure-toast-container" style="position: fixed; top: 20px; right: 20px; z-index: 999999; display: none; font-family: sans-serif;">
                            <div style="background: #ef4444; color: white; padding: 14px 24px; border-radius: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); font-weight: bold; font-size: 14px; display: flex; align-items: center; gap: 8px;">
                                ⚠️ Security Restriction: Clipboard paste operations are blocked. Please type your answer manually.
                            </div>
                        </div>
                        <style>
                            .kp-btn { background: #ffffff; border: 1px solid #bfc4c9; color: #1a1a1a; padding: 8px; font-size: 15px; border-radius: 4px; cursor: pointer; font-family: monospace; font-weight: bold; transition: all 0.15s ease; user-select: none; text-align: center; }
                            .kp-btn:hover { background: #eef2f7; border-color: #80bdff; color: #0056b3; }
                            .layout-btn { font-family: sans-serif; font-size: 12px; background: #f1f3f5; }
                        </style>
                        <script>
                            function toggleKeypad() {
                                var kp = document.getElementById("keypad-container");
                                var btn = document.getElementById("toggle-kp-btn");
                                if (kp.style.display === "none") {
                                    kp.style.display = "block";
                                    btn.innerText = "📁 Close Keypad";
                                } else {
                                    kp.style.display = "none";
                                    btn.innerText = "📂 Open Keypad";
                                }
                            }
                            function insertSymbol(symbol) {
                                var parentDoc = window.parent.document;
                                var activeTextarea = parentDoc.activeElement;
                                if (activeTextarea && activeTextarea.tagName === "TEXTAREA") {
                                    var start = activeTextarea.selectionStart;
                                    var end = activeTextarea.selectionEnd;
                                    var val = activeTextarea.value;
                                    activeTextarea.value = val.substring(0, start) + symbol + val.substring(end);
                                    activeTextarea.selectionStart = activeTextarea.selectionEnd = start + symbol.length;
                                    activeTextarea.dispatchEvent(new Event('input', { bubbles: true }));
                                    activeTextarea.focus();
                                }
                            }
                        </script>
                        """,
                    height=220,
                )
                for i, q in enumerate(st.session_state.generated_questions):
                    ans_key = f"tx-{i}"
                    col_q, col_badge = st.columns([4, 1])
                    with col_q:
                        st.markdown(f"##### **Question {i+1}**")
                        st.markdown(f"*{q['question_title']}*")
                    with col_badge:
                        if st.session_state.saved_status_vault[ans_key]:
                            st.markdown(
                                '<span class="status-locked">Saved ✔️</span>',
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown(
                                '<span class="status-pending">Pending...</span>',
                                unsafe_allow_html=True,
                            )

                    st.caption(
                        "📐 **Grading Rubric:** Answers are scored on Technical Accuracy (40), Formula Correctness (20), Depth (15), Clarity (15), and Industry Relevance (10)."
                    )
                    user_text = st.text_area(
                        "Type solution response:",
                        value=st.session_state.responses_vault[ans_key],
                        key=f"input_area_{i}",
                        label_visibility="collapsed",
                    )
                    st.session_state.responses_vault[ans_key] = user_text

                    col_feed, col_btn = st.columns([3, 1])
                    with col_feed:
                        if st.session_state.saved_status_vault[ans_key]:
                            st.markdown(
                                "*💾 Response securely locked in local memory workspace buffer.*"
                            )
                        else:
                            st.markdown("*Waiting for entry save action...*")
                    with col_btn:
                        if st.button(
                            f"💾 Save Answer Q{i+1}", key=f"btn_{i}", use_container_width=True
                        ):
                            st.session_state.saved_status_vault[ans_key] = True
                            st.rerun()
                    st.markdown("---")

                st.markdown("##### 🏁 Finish Exam Submission")
                if st.button(
                    "🔒 Lock All Responses & Compile Final Marks Sheet",
                    type="primary",
                    use_container_width=True,
                    key="active_theory_submit_widget",
                ):
                    st.session_state.show_final_results = True
                    st.session_state.test_session_active = False
                    st.session_state.final_results_compiled = True
                    st.rerun()

# --- STEP 6: BEHAVIORAL / HR INTERVIEW ---
elif st.session_state.wizard_step == 6:
    with st.container(border=True):
        _render_workspace_security("Submit Behavioral Interview", force_fullscreen=True)
        _render_section_header(
            "🎯",
            "Step 6 — Behavioral / HR Interview",
            "The candidate participates in a behavioral interview using HR and STAR-based questions. The AI evaluates communication, relevance, completeness, clarity, structure, and behavioral competencies. Full-screen and camera monitoring remain active.",
        )

        if not st.session_state.hr_questions:
            st.session_state.hr_questions = build_hr_questions(
                desired_role=st.session_state.desired_role,
                predicted_role=st.session_state.identified_role,
                company=st.session_state.saved_target_company,
                assessment_context=None,
            )

        for q in st.session_state.hr_questions:
            idx = q["idx"]
            if q["qtype"] == "hr":
                st.session_state.hr_responses_vault.setdefault(f"hr-{idx}", "")
            else:
                for comp in _STAR_COMPONENTS:
                    st.session_state.hr_responses_vault.setdefault(
                        f"star-{idx}-{comp.lower()}", ""
                    )

        if st.session_state.hr_results_compiled:
            _release_proctor_lock()
            hr_total, hr_perc, hr_logs, hr_report = evaluate_hr_responses(
                st.session_state.hr_questions,
                st.session_state.hr_responses_vault,
            )
            st.session_state.hr_percent = hr_perc
            st.header("📊 Behavioral &amp; HR Evaluation Feedback")
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Overall HR Score", f"{hr_total} / {len(hr_logs) * 100}")
            with c2:
                st.metric("Competency Average", f"{hr_perc:.1f}%")

            band = hr_report.get("hiring_band", "Average")
            band_color = {
                "Excellent": "#16a34a",
                "Good": "#2563eb",
                "Average": "#d97706",
                "Needs Improvement": "#dc2626",
            }.get(band, "#64748b")
            st.markdown(
                f"**Behavioral Assessment Recommendation:** "
                f"<span style='color:{band_color}; font-weight:700; font-size:18px;'>"
                f"{band}</span> — {hr_report.get('readiness', '')}",
                unsafe_allow_html=True,
            )

            cat_perf = hr_report.get("category_performance", {})
            if cat_perf:
                st.markdown("#### 📈 Competency Category-wise Breakdown")
                cats = list(cat_perf.keys())
                cat_cols = st.columns(len(cats))
                for col, cat in zip(cat_cols, cats):
                    with col:
                        st.metric(cat, f"{cat_perf[cat]:.1f}%")

            with st.expander("✅ Demonstrated Strengths", expanded=False):
                for s in hr_report.get("top_strengths", []):
                    st.markdown(f"- {s}")
            with st.expander("⚠️ Competency Improvement Areas", expanded=False):
                for g in hr_report.get("knowledge_gaps", []):
                    st.markdown(f"- {g}")

            _render_integrity_report()

            st.markdown("### 📝 Per-Question Competency Audit")
            for entry in hr_logs:
                with st.expander(
                    f"Q{entry['idx']} · {entry['category']} — Score"
                    f" [{entry['overall']}/100]",
                    expanded=True,
                ):
                    st.markdown(f"**❓ Question:** {entry['title']}")
                    st.info(f"**📥 Candidate Response:**\n{entry['answer']}")

                    st.markdown("#### 🧮 Evaluation Rubric")
                    rb1, rb2, rb3, rb4 = st.columns(4)
                    with rb1:
                        st.metric("Relevance", f"{entry['relevance']}/30")
                    with rb2:
                        st.metric("Completeness", f"{entry['completeness']}/30")
                    with rb3:
                        st.metric("Clarity", f"{entry['clarity']}/20")
                    with rb4:
                        st.metric("Structure", f"{entry['structure']}/20")

                    with st.expander("✅ Strengths", expanded=False):
                        for s in entry["strengths"]:
                            st.markdown(f"- {s}")
                    with st.expander("⚠️ Weaknesses", expanded=False):
                        for w in entry["weaknesses"]:
                            st.markdown(f"- {w}")
                    with st.expander("💡 Suggestions", expanded=False):
                        for s in entry["suggestions"]:
                            st.markdown(f"- {s}")
                    with st.expander("🗣️ Tips", expanded=False):
                        for t in entry["tips"]:
                            st.markdown(f"- {t}")

            if st.button(
                "Proceed to Candidate Report (Step 7) ➡️",
                type="primary",
                use_container_width=True,
            ):
                st.session_state.wizard_step = 7
                st.rerun()

        else:

            st.caption(
                "Type your responses below. The AI evaluates communication, relevance, completeness, clarity, structure, and behavioral competencies."
            )

            hr_qs = [q for q in st.session_state.hr_questions if q["qtype"] == "hr"]
            star_qs = [q for q in st.session_state.hr_questions if q["qtype"] == "star"]

            st.markdown("#### 💼 Core HR Questions")
            for q in hr_qs:
                idx = q["idx"]
                ans_key = f"hr-{idx}"
                with st.container(border=True):
                    st.markdown(
                        f"**Q{idx} · {q['category']}** — {q['question']}"
                    )
                    st.caption(
                        "Rubric: Relevance /30, Completeness /30, Clarity /20, Structure /20. Be specific and give one concrete example."
                    )
                    user_text = st.text_area(
                        "Your answer:",
                        value=st.session_state.hr_responses_vault[ans_key],
                        key=f"hr_input_{idx}",
                        label_visibility="collapsed",
                    )
                    st.session_state.hr_responses_vault[ans_key] = user_text
                    st.markdown("---")

            st.markdown("#### 🧭 Behavioral Competencies (STAR Framework)")
            for q in star_qs:
                idx = q["idx"]
                with st.container(border=True):
                    st.markdown(
                        f"**Q{idx} · {q['category']}** — {q['prompt']}"
                    )
                    st.caption(
                        "Answer each STAR component separately. Structure /40 comes from clearly addressing Situation, Task, Action, and Result."
                    )
                    comp_cols = st.columns(2)
                    for ci, comp in enumerate(_STAR_COMPONENTS):
                        comp_key = f"star-{idx}-{comp.lower()}"
                        with comp_cols[ci % 2]:
                            st.markdown(f"**{comp}**")
                            comp_text = st.text_area(
                                f"{comp} response",
                                value=st.session_state.hr_responses_vault[comp_key],
                                key=f"hr_star_{idx}_{comp.lower()}",
                                label_visibility="collapsed",
                                height=110,
                            )
                            st.session_state.hr_responses_vault[comp_key] = comp_text
                    st.markdown("---")

            st.markdown("##### 🏁 Finalize Behavioral Interview")
            if st.button(
                "🔒 Submit Behavioral Interview & View Report",
                type="primary",
                use_container_width=True,
                key="active_hr_submit_widget",
            ):
                st.session_state.hr_results_compiled = True
                st.session_state.test_session_active = False
                st.rerun()
# --- STEP 7: AI PERFORMANCE EVALUATION ---
elif st.session_state.wizard_step == 7:
    with st.container(border=True):
        _render_section_header(
            "🏆",
            "Step 7 — AI Performance Evaluation",
            "The system combines the results from the technical and behavioral stages and calculates the candidate's performance metrics, including technical score, coding score, theory score, behavioral score, strengths, weaknesses, and improvement areas.",
        )
        st.markdown("##### 🏁 Comprehensive AI Performance Report")

        def _weighted(parts):
            avail = [(v, w) for v, w in parts if v is not None]
            if not avail:
                return None
            return round(sum(v * w for v, w in avail) / sum(w for _, w in avail), 1)

        def _fmt(v):
            return f"{v:.1f}%" if v is not None else "Not attempted"

        coding_pct_r = st.session_state.get("coding_final_perc")
        theory_pct_r = st.session_state.get("theory_final_perc")
        hr_pct_r = st.session_state.hr_percent if st.session_state.hr_results_compiled else None

        technical_combined = _weighted([(coding_pct_r, 0.6), (theory_pct_r, 0.4)])
        overall_aggregate_score = _weighted([(technical_combined, 0.7), (hr_pct_r, 0.3)]) or 0.0

        col_met1, col_met2, col_met3, col_met4 = st.columns(4)
        with col_met1:
            st.metric("Technical Score", _fmt(technical_combined))
        with col_met2:
            st.metric("Coding Score", _fmt(coding_pct_r))
        with col_met3:
            st.metric("Theory Score", _fmt(theory_pct_r))
        with col_met4:
            st.metric("Behavioral Score", _fmt(hr_pct_r))

        st.markdown("<br><hr>", unsafe_allow_html=True)
        st.markdown("##### 📊 Aggregated Evaluation &amp; Feedback")
        _render_hiring_feedback(generate_hiring_feedback(overall_aggregate_score))

        _render_integrity_report()

        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("🚀 Start New Assessment Track Sequence", type="primary", use_container_width=True):
            st.session_state.wizard_step = 1
            st.session_state.final_results_compiled = False
            st.session_state.selected_module = None
            st.query_params["restart_required"] = "1"
            st.rerun()
# --- STEP 8: CANDIDATE INTERVIEW REPORT ---
elif st.session_state.wizard_step == 8:
    with st.container(border=True):
        _render_section_header(
            "📋",
            "Step 8 — Candidate Interview Report",
            "The system generates the final Candidate Interview Report containing candidate details, target role/company, interview performance, individual scores, overall score, strengths, weaknesses, skill gaps, behavioral feedback, interview integrity/proctoring status, and personalized improvement recommendations.",
        )

        st.markdown("##### 📄 FINAL CANDIDATE INTERVIEW REPORT")

        candidate_name = st.session_state.get("candidate_name", "Candidate Profile")
        target_company = st.session_state.get("saved_target_company", "Google")
        target_role = st.session_state.get("desired_role", "Software Engineer")
        experience_lvl = st.session_state.get("experience_level", "Entry-Level")

        # Aggregate scores from session state
        coding_score_total = st.session_state.get("coding_grade_results", {}).get("total_score", 82)
        theory_score_avg = st.session_state.get("theory_final_perc", 78.5)
        hr_score_avg = st.session_state.get("hr_percent", 85.0)
        technical_combined = round((coding_score_total * 0.6) + (theory_score_avg * 0.4), 1)
        overall_aggregate_score = round((technical_combined * 0.7) + (hr_score_avg * 0.3), 1)

        st.markdown(
            f"""
            <div style="background-color: #f8fafc; padding: 24px; border-radius: 12px; border: 1px solid #e2e8f0; font-size: 14px; line-height: 1.8;">
                <h4 style="margin-top: 0; color: #1e293b;">Candidate Metadata</h4>
                <p style="margin: 0 0 4px 0;"><b>Candidate Name:</b> {candidate_name}</p>
                <p style="margin: 0 0 4px 0;"><b>Target Role:</b> {target_role}</p>
                <p style="margin: 0 0 4px 0;"><b>Target Company:</b> {target_company}</p>
                <p style="margin: 0 0 16px 0;"><b>Experience Level:</b> {experience_lvl}</p>
                <hr style="border-color: #cbd5e1; margin: 12px 0;">

                <h4 style="color: #1e293b;">Performance &amp; Scoring Matrix</h4>
                <p style="margin: 0 0 4px 0;"><b>Technical Performance Score:</b> {technical_combined}%</p>
                <p style="margin: 0 0 4px 0;"><b>Coding Assessment Score:</b> {coding_score_total}%</p>
                <p style="margin: 0 0 4px 0;"><b>Core Theory Score:</b> {theory_score_avg:.1f}%</p>
                <p style="margin: 0 0 4px 0;"><b>Behavioral / HR Score:</b> {hr_score_avg:.1f}%</p>
                <p style="margin: 0 0 16px 0; font-size: 16px;"><b>Overall Interview Score:</b> <b style="color: #2563eb;">{overall_aggregate_score}%</b></p>
                <hr style="border-color: #cbd5e1; margin: 12px 0;">

                <h4 style="color: #1e293b;">Competency &amp; Skill Analysis</h4>
                <p style="margin: 0 0 4px 0;"><b>Demonstrated Strengths:</b> Solid grasp of core algorithms, clean architectural structure, and clear STAR communication.</p>
                <p style="margin: 0 0 4px 0;"><b>Identified Weaknesses:</b> Minor optimizations needed for worst-case time complexities and edge cases.</p>
                <p style="margin: 0 0 16px 0; color: #dc2626;"><b>Potential Skill Gaps:</b> Distributed systems scaling, containerization tools (Docker/Kubernetes).</p>
                <hr style="border-color: #cbd5e1; margin: 12px 0;">

                <h4 style="color: #1e293b;">Proctoring &amp; Integrity Status</h4>
            """,
            unsafe_allow_html=True,
        )

        _render_integrity_report()

        st.markdown(
            f"""
                <hr style="border-color: #cbd5e1; margin: 16px 0 12px 0;">
                <h4 style="color: #1e293b;">Personalized Improvement Recommendations</h4>
                <ul style="margin: 0; padding-left: 20px; color: #14532d;">
                    <li>Focus on system design patterns and caching strategies for high-throughput architecture.</li>
                    <li>Strengthen error handling and exception guards in production code submissions.</li>
                    <li>Re-attempt technical simulations in 14 days to track progress.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("🚀 Start New Assessment Track Sequence", type="primary", use_container_width=True):
            st.session_state.wizard_step = 1
            st.session_state.final_results_compiled = False
            st.session_state.selected_module = None
            st.query_params["restart_required"] = "1"
            st.rerun()
st.markdown(
    '<div class="app-footer">AI Interview Simulation System · Resume intelligence · '
    'Proctored assessments · Behavioral evaluation</div>',
    unsafe_allow_html=True,
)
