import streamlit as st
import pandas as pd
import numpy as np
import datetime as dt
import matplotlib.pyplot as plt
import os

def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def load_fonts():
    st.markdown("""
    <style>
    @font-face {
        font-family: 'SohneBuch';
        src: url('fonts/Söhne-Buch.otf') format('opentype');
    }
    @font-face {
        font-family: 'SohneHalbfett';
        src: url('fonts/Söhne-Halbfett.otf') format('opentype');
    }
    @font-face {
        font-family: 'SohneKraeftig';
        src: url('fonts/Söhne-Kräftig.otf') format('opentype');
    }
    @font-face {
        font-family: 'SohneLeicht';
        src: url('fonts/Söhne-Leicht.otf') format('opentype');
    }

    /* Default body text */
    html, body, [class*="css"] {
        font-family: 'SohneBuch', sans-serif;
        font-weight: normal;
    }

    /* Headings */
    h1, h2, h3 {
        font-family: 'SohneHalbfett', sans-serif;
        font-weight: normal;
    }

    /* Subtitles, captions */
    h4, h5, h6, .stMarkdown small, .stCaption {
        font-family: 'SohneLeicht', sans-serif;
        font-weight: normal;
    }

    /* Metrics and buttons */
    .stMetric label, .stMetric, .stButton button {
        font-family: 'SohneKraeftig', sans-serif;
        font-weight: normal;
    }
    </style>
    """, unsafe_allow_html=True)

# Call this early in your app
load_fonts()

# Call this early
load_fonts()

def display_profile_name(raw_profile: str) -> str:
    # Only rename the healthy quadrant; others keep their names
    return "Sustainable" if raw_profile == "Healthy Fire" else raw_profile

def status_icon(net_fire: float) -> str:
    if net_fire > 1.5: return "🟢"
    if net_fire < -1.5: return "🔴"
    return "🟡"

def quick_tip(row) -> str:
    # Very simple rule-set; you can refine later
    nf = row["NetFire"]
    if nf > 1.5:
        return "Your fire is strong. Maintain it: protect sleep windows and one screen-free recovery block today."
    if nf < -1.5:
        return "Dial down drain: pick one task to drop/defer and schedule 30 min for active recovery (walk, stretch)."
    # Flickering zone → look at weakest item today
    items = {"Sleep/Recovery (Q1)": row["Q1"], "Motivation (Q2)": row["Q2"],
             "Support (Q3)": row["Q3"], "Exhaustion (Q4)": row["Q4"],
             "Overload (Q5)": row["Q5"], "Switching off (Q6)": row["Q6"]}
    weakest = min(items, key=items.get)
    tips = {
        "Sleep/Recovery (Q1)": "Aim for a calm wind-down: 20–30 min without screens before bed.",
        "Motivation (Q2)": "Reconnect with purpose: note 1 thing today that feels meaningful.",
        "Support (Q3)": "Ask for a micro-help: a 10-minute check-in or quick feedback.",
        "Exhaustion (Q4)": "Insert a 10-minute micro-break between blocks of work.",
        "Overload (Q5)": "Say no to one non-essential task today.",
        "Switching off (Q6)": "Do a phone-free walk after work to create a boundary.",
    }
    return tips[weakest]


st.set_page_config(
    page_title="Healthy Fire Dashboard",
    page_icon="assets/icon.png",
    layout="centered"
)

st.title("🔥 Healthy Fire MVP")
st.caption("Ambition is like fire - you want it to burn bright, not out. Check in to keep tabs on your Fuel vs. Drain over time.")


# ---------- Config ----------
CSV_PATH = "healthy_fire_data.csv"

QUESTIONS = [
    ("Q1", "I felt physically and mentally refreshed after sleep or rest."),
    ("Q2", "I felt motivated and energised by my work and activities."),
    ("Q3", "I felt supported by people around me."),
    ("Q4", "I felt emotionally exhausted or drained."),
    ("Q5", "My workload or responsibilities felt unmanageable or unmotivating."),
    ("Q6", "I found it hard to switch off and recover after work.")
]

# Visible daily-intensity scale
SCALE = [
    (1, "1 – Not at all"),
    (2, "2 – A little"),
    (3, "3 – Somewhat"),
    (4, "4 – Quite a lot"),
    (5, "5 – Extremely"),
]

# Colors
FUEL_COLOR = "#2e7d32"   # green
DRAIN_COLOR = "#e53935"  # red
ZONE_OK = (0.5, None)       # top zone threshold (green-ish, keep default alpha)
ZONE_MID = (-0.5, 0.5)      # middle zone
ZONE_RISK = (None, -0.5)    # bottom zone (use light blue)
LIGHT_BLUE = "#bbdefb"


PROFILE_DESCRIPTIONS = {
    "Sustainable": "You have strong energy and recovery resources while demands feel manageable. This is the ideal, steady state to maintain.",
    "Fast Burner": "You’re highly driven but also under heavy demands. Feels great short term, but risks a sudden crash without recovery.",
    "Exhausted": "Energy and recovery are low while demands are high. This is the classic burnout path and needs urgent rest and relief.",
    "Detached": "Demands are low, but so are energy and motivation. Not in crisis, but risks disengagement or loss of meaning over time."
}

PROFILE_ICONS = {
    "Sustainable": "🔥",
    "Fast Burner": "🌶️🌶️🌶️",
    "Exhausted": "🫠",
    "Detached": "😶‍🌫️"
}


# ---------- Helpers ----------
def load_data(path: str) -> pd.DataFrame:
    if os.path.exists(path):
        try:
            return pd.read_csv(path, parse_dates=["date"])
        except Exception:
            return pd.DataFrame(columns=["date","Q1","Q2","Q3","Q4","Q5","Q6"])
    else:
        return pd.DataFrame(columns=["date","Q1","Q2","Q3","Q4","Q5","Q6"])

def save_row(path: str, row: dict):
    df = load_data(path)
    df = df[df["date"] != row["date"]]
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df = df.sort_values("date")
    df.to_csv(path, index=False)

def compute_scores(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["Fuel"]  = df[["Q1","Q2","Q3"]].mean(axis=1)
    df["Drain"] = df[["Q4","Q5","Q6"]].mean(axis=1)
    df["NetFire"] = df["Fuel"] - df["Drain"]

    # Store the new label directly in the data
    def quadrant(row):
        fuel, drain = row["Fuel"], row["Drain"]
        if fuel >= 3 and drain < 3:  return "Sustainable"     # was "Healthy Fire"
        if fuel >= 3 and drain >= 3: return "Fast Burner"
        if fuel < 3 and drain >= 3:  return "Exhausted"
        return "Detached"

    df["Profile"] = df.apply(quadrant, axis=1)
    return df

def status_from_balance(net_fire: float) -> str:
    if net_fire > 1.5: return "Healthy Fire"
    if net_fire < -1.5: return "Fire at Risk"
    return "Flickering Fire"


# ---------- Data ----------
df_raw = load_data(CSV_PATH)


# ---------- Check-in Form ----------
st.subheader("Check in on your fire")
today = st.date_input("Choose date", value=dt.date.today())

with st.form("checkin"):
    st.write("**How strongly do you feel each of these today?**")
    answers = {}

    # Radios return the selected tuple (value, label); None until selected
    def radio_item(question_key, question_text):
        choice = st.radio(
            label=question_text,
            options=SCALE,                 # [(1,"1 – Not at all"), ...]
            format_func=lambda x: x[1],    # show the label text
            index=None,                    # no default selection
            key=f"radio_{question_key}"
        )
        return None if choice is None else choice[0]  # return the numeric value or None

    st.markdown("### Fuel (protective factors)")
    for key, text in QUESTIONS[:3]:
        answers[key] = radio_item(key, text)

    st.markdown("### Drain (risk factors)")
    for key, text in QUESTIONS[3:]:
        answers[key] = radio_item(key, text)

    submitted = st.form_submit_button("Check my Fire")

    if submitted:
        missing = [k for k, v in answers.items() if v is None]
        if missing:
            st.error("Please answer all items before submitting.")
        else:
            row = {"date": pd.to_datetime(today)} | answers
            save_row(CSV_PATH, row)
            st.success("Saved today's check-in.")


# ---------- Load + Score ----------
df_scored = compute_scores(load_data(CSV_PATH))

if df_scored.empty:
    st.info("No data yet. Add a check-in above to see your dashboard.")
    st.stop()

# ---------- Selected date ----------
selected_date = st.selectbox(
    "View a specific day",
    options=list(df_scored["date"].dt.date.astype(str)),
    index=len(df_scored)-1
)
sel = df_scored[df_scored["date"].dt.date.astype(str) == selected_date].iloc[-1]

# ===== ORDER STARTS HERE =====
st.subheader(f"Your Healthy Fire — {selected_date}")

# Status (with icon) on its own line
st.markdown(f"**Status:** {status_icon(sel['NetFire'])} {status_from_balance(sel['NetFire'])}")

# Profile and emoji
profile_name = sel["Profile"]              # already stores "Sustainable", "Fast Burner", etc.
profile_emoji = PROFILE_ICONS.get(profile_name, "")
st.markdown(f"**Profile:** {profile_emoji} {profile_name}")


# --- Your fire over time ---
st.subheader("Your fire over time")
fig2, ax2 = plt.subplots(figsize=(6,3))

# Background zones (–4..–1.5 red, –1.5..1.5 yellow, 1.5..4 green)
ax2.axhspan(-4.0, -1.5, color="#ffcdd2", alpha=0.6)
ax2.axhspan(-1.5,  1.5, color="#fff59d", alpha=0.6)
ax2.axhspan( 1.5,  4.0, color="#a5d6a7", alpha=0.6)

# Data
dates  = df_scored["date"].tolist()
scores = df_scored["NetFire"].tolist()

# Colour-coded segments
for i in range(len(scores)-1):
    if scores[i] > 1.5 and scores[i+1] > 1.5:
        color = "#2e7d32"  # green
    elif scores[i] < -1.5 and scores[i+1] < -1.5:
        color = "#e53935"  # red
    else:
        color = "#fbc02d"  # yellow
    ax2.plot(dates[i:i+2], scores[i:i+2], marker="o", color=color, linewidth=2)

# Highlight today's/selected score
today_date  = sel["date"]
today_score = sel["NetFire"]
marker_color = "#2e7d32" if today_score > 1.5 else ("#e53935" if today_score < -1.5 else "#fbc02d")
ax2.scatter(today_date, today_score, s=120, color=marker_color, edgecolors="black", zorder=5)

# Axis formatting: fixed –4..4; pad so first point isn’t on the y-axis
import matplotlib.dates as mdates
min_d = min(dates)
max_d = max(dates)
pad   = pd.Timedelta(days=0.5)
ax2.set_xlim(min_d - pad, max_d + pad)

# Adaptive tick locator/formatter based on date span
n_days = (max_d - min_d).days + 1
if n_days <= 21:
    interval = 1          # every day
elif n_days <= 45:
    interval = 3          # every 3 days
elif n_days <= 120:
    interval = 7          # weekly
else:
    interval = 14         # every 2 weeks

ax2.xaxis.set_major_locator(mdates.DayLocator(interval=interval))
date_fmt = "%d.%m" if interval <= 3 else "%d %b"
ax2.xaxis.set_major_formatter(mdates.DateFormatter(date_fmt))
fig2.autofmt_xdate(rotation=45)

# Y-axis & labels
ax2.axhline(0, linestyle="--", linewidth=0.8, color="black")
ax2.set_ylim(-4, 4)
ax2.set_yticks(range(-4, 5, 1))
ax2.set_ylabel("Net Fire (Fuel − Drain)")
ax2.set_xlabel("Date")

st.pyplot(fig2, clear_figure=True)




# --- Scores block: Fuel - Drain = Net Fire ---
col1, col_minus, col2, col_equal, col3 = st.columns([3,1,3,1,3])

with col1:
    st.markdown("<div style='text-align:center; font-weight:bold;'>Fuel</div>", unsafe_allow_html=True)
    st.markdown(f"<h2 style='text-align: center; color:#2e7d32;'>{sel['Fuel']:.1f}</h2>", unsafe_allow_html=True)

with col_minus:
    st.markdown("<div style='text-align:center; font-size:24px; font-weight:bold;'>−</div>", unsafe_allow_html=True)

with col2:
    st.markdown("<div style='text-align:center; font-weight:bold;'>Drain</div>", unsafe_allow_html=True)
    st.markdown(f"<h2 style='text-align: center; color:#e53935;'>{sel['Drain']:.1f}</h2>", unsafe_allow_html=True)

with col_equal:
    st.markdown("<div style='text-align:center; font-size:24px; font-weight:bold;'>=</div>", unsafe_allow_html=True)

with col3:
    st.markdown("<div style='text-align:center; font-weight:bold;'>Net Fire</div>", unsafe_allow_html=True)
    st.markdown(f"<h2 style='text-align: center;'>{sel['NetFire']:.1f}</h2>", unsafe_allow_html=True)



# --- Fuel vs Drain (SECOND) ---
st.subheader("Fuel vs. Drain")
fig1, ax1 = plt.subplots(figsize=(4,3))
FUEL_COLOR = "#2e7d32"   # green
DRAIN_COLOR = "#e53935"  # red
ax1.bar(["Fuel","Drain"], [sel["Fuel"], sel["Drain"]], color=[FUEL_COLOR, DRAIN_COLOR])
ax1.set_ylim(0,5)
ax1.set_ylabel("Score (1–5)")
st.pyplot(fig1, clear_figure=True)



# --- Quadrant chart (last 5 days only) ---
st.subheader("Your fire profile")
fig3, ax3 = plt.subplots(figsize=(6,6))

# Use only the last 5 days of data
df_recent = df_scored.tail(5)

ax3.axhline(3, color="black", linewidth=1)
ax3.axvline(3, color="black", linewidth=1)
ax3.plot(df_recent["Drain"], df_recent["Fuel"], marker="o", color="#1e88e5")

# Add date labels
for i, row in df_recent.reset_index().iterrows():
    ax3.text(
        row["Drain"]+0.02, row["Fuel"]+0.02,
        row["date"].date().strftime("%m-%d"),
        fontsize=8
    )

# Highlight the latest point (big black marker on top)
latest = df_recent.iloc[-1]
ax3.scatter(latest["Drain"], latest["Fuel"], s=160, color="black", zorder=5)

ax3.set_xlim(1,5); ax3.set_ylim(1,5)
ax3.set_xlabel("Drain (1–5)"); ax3.set_ylabel("Fuel (1–5)")
ax3.set_title("Quadrant path")

# Labels
ax3.text(2, 4.6, f"Sustainable {PROFILE_ICONS['Sustainable']}", ha="center", fontsize=11, color=FUEL_COLOR, weight="bold")
ax3.text(4, 4.6, f"Fast Burner {PROFILE_ICONS['Fast Burner']}", ha="center", fontsize=11, color="#f39c12",  weight="bold")
ax3.text(4, 1.5, f"Exhausted {PROFILE_ICONS['Exhausted']}",    ha="center", fontsize=11, color=DRAIN_COLOR, weight="bold")
ax3.text(2, 1.5, f"Detached {PROFILE_ICONS['Detached']}",      ha="center", fontsize=11, color="#546e7a",  weight="bold")

st.pyplot(fig3, clear_figure=True)




# --- Profile descriptions under quadrant ---

# Today's profile (always visible)
current_profile = sel["Profile"]
if current_profile in PROFILE_DESCRIPTIONS:
    icon = PROFILE_ICONS.get(current_profile, "")
    st.markdown(f"**Your profile today: {current_profile} {icon}**")
    st.write(PROFILE_DESCRIPTIONS[current_profile])

# Full guide (collapsed by default)
with st.expander("Fire profile guide"):
    for profile, desc in PROFILE_DESCRIPTIONS.items():
        st.markdown(f"**{profile}** — {desc}")


# --- Quick tip (LAST) ---
st.subheader("Quick tip")
st.write(quick_tip(sel))


# --- Download + References ---
st.download_button(
    "Download my data (CSV)",
    data=df_scored.to_csv(index=False),
    file_name="healthy_fire_data_export.csv",
    mime="text/csv"
)

# Add spacing before references
st.markdown("<br><br><br>", unsafe_allow_html=True)

# Grey style block
st.markdown(
    """
    <div style="color: #6e6e6e; font-size: 0.9em;">
    <b>NOTES</b><br><br>
    <b>MVP logic</b><br>
    Fuel = mean(Q1–Q3), Drain = mean(Q4–Q6), Net fire = Fuel − Drain<br><br>

    <b>Key References</b><br>
    * Maslach, C., & Jackson, S. E. (1981). <i>Maslach Burnout Inventory (MBI).</i><br>
    * Kristensen, T. S. et al. (2005). <i>The Copenhagen Burnout Inventory.</i><br>
    * Schaufeli, W. B. et al. (2002). <i>Utrecht Work Engagement Scale (UWES).</i><br>
    * Sonnentag, S., & Fritz, C. (2007). <i>Recovery Experience Questionnaire.</i><br>
    * Kallus, K. W., & Kellmann, M. (2016). <i>Recovery-Stress Questionnaire (RESTQ).</i><br>
    * Bakker, A. B., & Demerouti, E. (2007). <i>Job Demands–Resources (JD-R) model.</i>
    </div>
    """,
    unsafe_allow_html=True
)
