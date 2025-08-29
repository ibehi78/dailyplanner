# daily_planner_complete.py with background notifications, unified summarizer, and local storage

import streamlit as st
from datetime import date, datetime, timedelta, time as dtime
import json
import re
import base64

try:
    from plyer import notification as plyer_notify
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False

st.set_page_config(page_title="Daily Planner", layout="wide", page_icon="🗓️")

# ------------------ CSS Themes ------------------
DARK_CSS = """
<style>
.stApp { background: #0b0f14; color: #eaeaea; }
.card { background:#0e1419; padding:12px; border-radius:12px; box-shadow:0 6px 20px rgba(0,0,0,0.6); }
.small { color:#a8b0b8; font-size:0.9rem; }
hr { border-color: rgba(255,255,255,0.06); }
.glow { text-shadow: 0 0 6px rgba(255,255,255,0.35); color:#FFD700; }
.due { color:#FF6B6B; font-weight:bold; }
.summary-box { background: #1a2634; padding: 15px; border-radius: 8px; margin: 10px 0; }
.hidden { display: none; }
</style>
"""
LIGHT_CSS = """
<style>
.stApp { background:#ffffff; color:#111827; }
.card { background:#f8fafc; padding:12px; border-radius:12px; box-shadow:0 6px 20px rgba(0,0,0,0.06); }
.small { color:#6b7280; font-size:0.9rem; }
hr { border-color: rgba(0,0,0,0.06); }
.glow { text-shadow: 0 0 6px rgba(17,24,39,0.25); color:#B45309; }
.due { color:#DC2626; font-weight:bold; }
.summary-box { background: #e6f3ff; padding: 15px; border-radius: 8px; margin: 10px 0; }
.hidden { display: none; }
</style>
"""

# ------------------ Local Storage Functions ------------------
def save_to_local_storage():
    """Save all data to browser's local storage"""
    import streamlit.components.v1 as components
    
    data = {
        "tasks": st.session_state.tasks,
        "activities": st.session_state.activities,
        "habits": st.session_state.habits,
        "notes": st.session_state.notes,
        "theme": st.session_state.theme,
        "settings": {
            "desktop_notify": st.session_state.desktop_notify,
            "auto_refresh": st.session_state.auto_refresh,
            "auto_refresh_secs": st.session_state.auto_refresh_secs,
            "bg_notify_enabled": st.session_state.bg_notify_enabled
        }
    }
    
    # Convert to JSON string, handling date objects
    def default_serializer(obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        elif isinstance(obj, dtime):
            return obj.strftime('%H:%M:%S')
        raise TypeError(f"Type {type(obj)} not serializable")
    
    data_str = json.dumps(data, default=default_serializer)
    
    # Save to local storage
    components.html(
        f"""
        <script>
        localStorage.setItem('daily_planner_data', `{data_str}`);
        console.log('Data saved to local storage');
        </script>
        """,
        height=0,
    )

def load_from_local_storage():
    """Load data from browser's local storage"""
    import streamlit.components.v1 as components
    
    # First, get data from local storage via JavaScript
    components.html(
        """
        <script>
        const data = localStorage.getItem('daily_planner_data');
        if (data) {
            // Store data in window for retrieval
            window.localStorageData = data;
            console.log('Data loaded from local storage');
        }
        </script>
        """,
        height=0,
    )
    
    # Now try to retrieve the data
    try:
        # Get data from query params using st.query_params
        query_params = st.query_params
        data_str = query_params.get('planner_data', None)
        if not data_str:
            # Try to get from window object via JavaScript
            components.html(
                """
                <script>
                if (window.localStorageData) {
                    const url = new URL(window.location);
                    url.searchParams.set('planner_data', window.localStorageData);
                    window.history.replaceState({}, '', url);
                    window.location.reload();
                }
                </script>
                """,
                height=0,
            )
            return None
            
        data = json.loads(data_str)
        
        # Convert string dates back to date objects
        def parse_dates(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key == "Date" and isinstance(value, str):
                        try:
                            obj[key] = datetime.fromisoformat(value).date()
                        except:
                            pass
                    elif key == "Time" and isinstance(value, str):
                        try:
                            obj[key] = datetime.strptime(value, '%H:%M:%S').time()
                        except:
                            pass
                    elif isinstance(value, (dict, list)):
                        parse_dates(value)
            elif isinstance(obj, list):
                for item in obj:
                    parse_dates(item)
            return obj
        
        data = parse_dates(data)
        return data
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

# ------------------ Session init ------------------
ss = st.session_state

# Try to load data from local storage first
saved_data = load_from_local_storage()

if saved_data:
    ss.tasks = saved_data.get("tasks", [])
    ss.activities = saved_data.get("activities", [])
    ss.habits = saved_data.get("habits", [])
    ss.notes = saved_data.get("notes", [])
    ss.theme = saved_data.get("theme", "Dark")
    
    settings = saved_data.get("settings", {})
    ss.desktop_notify = settings.get("desktop_notify", False)
    ss.auto_refresh = settings.get("auto_refresh", False)
    ss.auto_refresh_secs = settings.get("auto_refresh_secs", 30)
    ss.bg_notify_enabled = settings.get("bg_notify_enabled", False)
else:
    # Default values if no saved data
    ss.setdefault("tasks", [])
    ss.setdefault("activities", [])
    ss.setdefault("habits", [])
    ss.setdefault("notes", [])
    ss.setdefault("theme", "Dark")
    ss.setdefault("desktop_notify", False)
    ss.setdefault("auto_refresh", False)
    ss.setdefault("auto_refresh_secs", 30)
    ss.setdefault("bg_notify_enabled", False)

# These can remain as they're not critical to persist
ss.setdefault("selected_date", date.today())
ss.setdefault("calendar_month", date.today().replace(day=1))
ss.setdefault("editing_item", None)
ss.setdefault("editing_type", None)
ss.setdefault("search_date", None)
ss.setdefault("editing_id", None)
ss.setdefault("editing_item_type", None)
ss.setdefault("notified_items", set())
ss.setdefault("notify_trigger", 0)
ss.setdefault("summarizer_text", "")
ss.setdefault("summarizer_result", "")

# ------------------ Unified Text Summarization Function ------------------
def summarize_any_text(text: str, max_sentences: int = 3, max_length: int = 300) -> str:
    """Unified text summarizer that works for any type of content"""
    text = text.strip()
    if not text:
        return ""
    
    # If text is short enough, return as is
    if len(text) <= max_length:
        return text
    
    # Improved sentence splitting that handles various punctuation
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    # Remove empty sentences
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if len(sentences) <= max_sentences and len(text) <= max_length:
        return text
    
    # Look for important sentences (containing keywords)
    important_words = ['important', 'key', 'critical', 'essential', 'must', 'should', 
                      'conclusion', 'summary', 'therefore', 'thus', 'however', 'but',
                      'because', 'reason', 'result', 'findings', 'study', 'research',
                      'recommend', 'suggest', 'conclude']
    
    # Score sentences based on importance
    scored_sentences = []
    for i, sentence in enumerate(sentences):
        score = 0
        
        # Score based on keywords
        for word in important_words:
            if word in sentence.lower():
                score += 2
        
        # Score based on position (first sentences are often important)
        if i == 0:
            score += 3
        elif i < 3:
            score += 1
            
        # Score based on length (medium-length sentences are often good summaries)
        sentence_length = len(sentence.split())
        if 10 <= sentence_length <= 25:
            score += 1
            
        scored_sentences.append((sentence, score, i))
    
    # Sort by score (highest first)
    scored_sentences.sort(key=lambda x: x[1], reverse=True)
    
    # Select top sentences, but try to maintain some order
    selected_indices = set()
    selected_sentences = []
    
    # First, add high-scoring sentences
    for sentence, score, idx in scored_sentences[:max_sentences]:
        if score > 0:
            selected_indices.add(idx)
            selected_sentences.append((idx, sentence))
    
    # If we don't have enough sentences, add from the beginning
    if len(selected_sentences) < max_sentences:
        for i in range(min(max_sentences, len(sentences))):
            if i not in selected_indices:
                selected_sentences.append((i, sentences[i]))
                selected_indices.add(i)
    
    # Sort by original order
    selected_sentences.sort(key=lambda x: x[0])
    
    # Create the summary
    result = " ".join([s[1] for s in selected_sentences])
    
    # Trim if too long
    if len(result) > max_length:
        result = result[:max_length].rsplit(' ', 1)[0] + "..."
    
    return result

# ------------------ Helpers ------------------
def gen_id(prefix: str) -> str:
    return f"{prefix}-{int(datetime.now().timestamp()*1000)}"

def due_soon(item: dict) -> bool:
    try:
        reminder = int(item.get("ReminderMinutes", 0) or 0)
        dt = datetime.combine(item["Date"], item["Time"]) - timedelta(minutes=reminder)
        now = datetime.now()
        return now >= dt and item.get("Status", "Pending") == "Pending"
    except Exception:
        return False

def filter_items(items):
    d = ss.search_date
    if not d:
        return items
    return [x for x in items if "Date" in x and x["Date"] == d]

def edit_form(item_type, item):
    """Create an edit form for different item types"""
    edited_item = item.copy()
    
    if item_type == "task":
        edited_item["Title"] = st.text_input("Title", value=item.get("Title", ""), key="edit_title")
        edited_item["Date"] = st.date_input("Date", value=item.get("Date", date.today()), key="edit_date")
        edited_item["Time"] = st.time_input("Time", value=item.get("Time", dtime(9, 0)), key="edit_time")
        edited_item["Priority"] = st.selectbox(
            "Priority", ["Low", "Medium", "High"], 
            index=["Low", "Medium", "High"].index(item.get("Priority", "Medium")), 
            key="edit_priority"
        )
        edited_item["ReminderMinutes"] = st.number_input(
            "Remind minutes before", 
            min_value=0, max_value=1440, 
            value=item.get("ReminderMinutes", 0), 
            key="edit_reminder"
        )
        
    elif item_type == "activity":
        edited_item["Title"] = st.text_input("Title", value=item.get("Title", ""), key="edit_title")
        edited_item["Date"] = st.date_input("Date", value=item.get("Date", date.today()), key="edit_date")
        edited_item["Time"] = st.time_input("Time", value=item.get("Time", dtime(9, 0)), key="edit_time")
        edited_item["Duration"] = st.number_input(
            "Duration (minutes)", 
            min_value=1, max_value=1440, 
            value=item.get("Duration", 60), 
            key="edit_duration"
        )
        
    elif item_type == "habit":
        edited_item["Habit"] = st.text_input("Habit", value=item.get("Habit", ""), key="edit_habit")
        edited_item["Frequency"] = st.selectbox(
            "Frequency", 
            ["Daily", "Weekly", "Monthly"],
            index=["Daily", "Weekly", "Monthly"].index(item.get("Frequency", "Daily")), 
            key="edit_frequency"
        )
        
    elif item_type == "note":
        edited_item["Note"] = st.text_area("Note", value=item.get("Note", ""), key="edit_note")
        edited_item["Date"] = st.date_input("Date", value=item.get("Date", date.today()), key="edit_date")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Save Changes"):
            return edited_item
    with col2:
        if st.button("Cancel"):
            return None
            
    return None

# ------------------ Notifications ------------------
def notify(title: str, body: str, item_id=None):
    # Skip if already notified
    if item_id and item_id in ss.notified_items:
        return
        
    # Store notification to prevent duplicates
    if item_id:
        ss.notified_items.add(item_id)
    
    # Browser notification
    title_js = json.dumps(title)
    opts_js = json.dumps({"body": body, "icon": "https://cdn-icons-png.flaticon.com/512/3652/3652191.png"})
    st.markdown(f"""
<script>
(function(){{
  if (!("Notification" in window)) return;
  function send(){{ 
    try{{ 
      const notification = new Notification({title_js}, {opts_js});
      notification.onclick = function() {{
        window.focus();
        this.close();
      }};
    }}catch(e){{}} 
  }}
  if (Notification.permentission === "granted") {{ send(); }}
  else if (Notification.permission !== "denied") {{
    Notification.requestPermission().then(p => {{ if (p === "granted") send(); }});
  }}
}})();
</script>
""", unsafe_allow_html=True)
    
    # Desktop notification (if enabled)
    if ss.desktop_notify and PLYER_AVAILABLE:
        try:
            plyer_notify.notify(title=title, message=body, timeout=10, app_name="Daily Planner")
        except: 
            pass

# ------------------ Background Notification System ------------------
def setup_background_notifications():
    """Set up the background notification system"""
    if not ss.bg_notify_enabled:
        return
    
    # Create a background notification checker using data URL
    iframe_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Background Notifier</title>
        <script>
            let lastCheck = Date.now();
            const checkInterval = %s;
            
            function checkNotifications() {
                const now = Date.now();
                if (now - lastCheck >= checkInterval) {
                    lastCheck = now;
                    // Send message to parent to check for notifications
                    window.parent.postMessage({type: "checkNotifications"}, "*");
                }
            }
            
            // Check every 10 seconds
            setInterval(checkNotifications, 10000);
        </script>
    </head>
    <body>
        <!-- Background notification service -->
    </body>
    </html>
    """ % (ss.auto_refresh_secs * 1000)
    
    # Encode the HTML to base64 for data URL
    iframe_html_encoded = base64.b64encode(iframe_html.encode()).decode()
    
    st.markdown(f"""
    <iframe id="bgNotifier" style="display:nine;" src="data:text/html;base64,{iframe_html_encoded}"></iframe>
    
    <script>
        // Listen for messages from the background iframe
        window.addEventListener("message", function(event) {{
            if (event.data.type === "checkNotifications") {{
                // Create a hidden button to trigger notification check
                const btn = document.createElement("button");
                btn.id = "hiddenNotifyBtn";
                btn.style.display = "none";
                document.body.appendChild(btn);
                
                // Simulate a click to trigger Streamlit
                setTimeout(() => {{
                    btn.click();
                    btn.remove();
                }}, 100);
            }}
        }});
    </script>
    """, unsafe_allow_html=True)

# Create a hidden component to trigger notification checks
if "notify_trigger" not in st.session_state:
    st.session_state.notify_trigger = 0

# Create the actual button that will be clicked programmatically
if st.button("Check notifications", key="hidden_notify_check", help="Check for due notifications", type="primary"):
    st.session_state.notify_trigger += 1

# ------------------ Sidebar ------------------
with st.sidebar:
    st.title("Planner Controls")
    ss.theme = st.radio("Theme", ["Dark","Light"], index=0 if ss.theme=="Dark" else 1)
    st.markdown("---")
    page = st.radio("Page", ["Dashboard","Tasks","Activities","Habits","Notes","Summarizer","Calendar"], index=0)
   
    st.markdown("---")
    ss.auto_refresh = st.checkbox("Enable Auto-refresh", value=ss.auto_refresh)
    ss.auto_refresh_secs = st.number_input("Refresh every (sec)", min_value=5,max_value=600,value=int(ss.auto_refresh_secs))
    st.markdown("---")
    ss.desktop_notify = st.checkbox("Enable Desktop Notifications", value=ss.desktop_notify, disabled=not PLYER_AVAILABLE)
    ss.bg_notify_enabled = st.checkbox("Enable Background Notifications", value=ss.bg_notify_enabled, 
                                      help="Notifications will work even when tab is in background")
    
    # Data management section
    st.markdown("---")
    st.subheader("Data Management")
    
    if st.button("Force Save Data"):
        save_to_local_storage()
        st.success("Data saved to browser storage!")

# Apply theme
st.markdown(DARK_CSS if ss.theme=="Dark" else LIGHT_CSS, unsafe_allow_html=True)

# ------------------ Pages ------------------
if page == "Dashboard":
    st.title("📊 Dashboard")
    st.markdown(f"### Today's Summary - {date.today()}")
    
    # Today's tasks
    today_tasks = [t for t in ss.tasks if t["Date"] == date.today()]
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Tasks", len(today_tasks))
    with col2:
        st.metric("Completed", len([t for t in today_tasks if t.get("Status") == "Done"]))
    with col3:
        st.metric("Pending", len([t for t in today_tasks if t.get("Status") == "Pending"]))
    
    # Upcoming tasks
    st.markdown("### ⏰ Upcoming Tasks")
    upcoming_tasks = sorted([t for t in ss.tasks if t["Date"] >= date.today() and t.get("Status") == "Pending"], 
                           key=lambda x: (x["Date"], x["Time"]))[:5]
    if upcoming_tasks:
        for task in upcoming_tasks:
            due_class = " due" if due_soon(task) else ""
            st.markdown(f"<div class='card'><span class='glow{due_class}'>**{task['Title']}**</span><br>"
                       f"<span class='small'>📅 {task['Date']} ⏰ {task['Time'].strftime('%H:%M')} · {task['Priority']}</span></div>", 
                       unsafe_allow_html=True)
    else:
        st.info("No upcoming tasks.")
        
    # Recent notes
    st.markdown("### 📝 Recent Notes")
    recent_notes = sorted(ss.notes, key=lambda x: x.get("Date", date.today()), reverse=True)[:3]
    if recent_notes:
        for note in recent_notes:
            st.markdown(f"<div class='card'><strong>{note.get('Date', '')}</strong><br>"
                       f"{summarize_any_text(note.get('Note', ''))}</div>", 
                       unsafe_allow_html=True)
    else:
        st.info("No recent notes.")
        

elif page == "Tasks":
    st.title("✅ Tasks")
    
    # Check if we're in edit mode
    if ss.editing_id and ss.editing_item_type == "task":
        # Find the task being edited
        task_to_edit = next((t for t in ss.tasks if t["id"] == ss.editing_id), None)
        
        if task_to_edit:
            st.subheader("Edit Task")
            result = edit_form("task", task_to_edit)
            
            if result is not None:
                # Update the task
                index = next(i for i, t in enumerate(ss.tasks) if t["id"] == ss.editing_id)
                ss.tasks[index] = result
                ss.editing_id = None
                ss.editing_item_type = None
                save_to_local_storage()  # Save after editing
                st.success("Task updated!")
                st.experimental_rerun()
            elif result is None and ss.editing_id:
                # Cancel edit mode
                ss.editing_id = None
                ss.editing_item_type = None
                st.rerun()
        else:
            ss.editing_id = None
            ss.editing_item_type = None
    
    # Normal add task form
    with st.expander("➕ Add Task"):
        t_title = st.text_input("Title", key="t_title")
        t_date = st.date_input("Date", value=date.today(), key="t_date")
        t_time = st.time_input("Time", value=(datetime.now()+timedelta(minutes=1)).time().replace(second=0,microsecond=0), key="t_time")
        t_pri = st.selectbox("Priority", ["Low","Medium","High"], index=1, key="t_pri")
        t_rem = st.number_input("Remind minutes before", min_value=0, max_value=1440, value=0, key="t_rem")
        if st.button("Add Task", key="btn_add_task"):
            if t_title.strip():
                ss.tasks.append({"id":gen_id("task"),"Title":t_title.strip(),"Date":t_date,"Time":t_time,"Priority":t_pri,"Status":"Pending","ReminderMinutes":int(t_rem)})
                notify("Task Added", t_title.strip())
                save_to_local_storage()  # Save after adding
                st.success("Task added.")

    st.markdown("### Your tasks")
    tasks_to_show = filter_items(ss.tasks)
    if not tasks_to_show:
        st.info("No tasks.")
    else:
        for t in sorted(tasks_to_show, key=lambda x:(x["Date"],x["Time"])):
            due_class = " due" if due_soon(t) else ""
            cols = st.columns([0.5, 0.15, 0.15, 0.2])
            with cols[0]:
                st.markdown(f"<span class='glow{due_class}'>**{t['Title']}**</span><br><span class='small'>📅 {t['Date']} ⏰ {t['Time'].strftime('%H:%M')} · {t['Priority']} · {t['Status']}</span>", unsafe_allow_html=True)
            with cols[1]:
                if st.button("Edit", key=f"edit_{t['id']}"):
                    ss.editing_id = t["id"]
                    ss.editing_item_type = "task"
                    st.rerun()
            with cols[2]:
                if st.button("Done", key=f"done_{t['id']}"):
                    t["Status"]="Done"; notify("Task Completed", t["Title"]); 
                    save_to_local_storage()  # Save after completing
                    st.rerun()
            with cols[3]:
                if st.button("Delete", key=f"del_{t['id']}"):
                    ss.tasks=[x for x in ss.tasks if x["id"]!=t["id"]]; 
                    save_to_local_storage()  # Save after deleting
                    st.rerun()

elif page == "Activities":
    st.title("🎯 Activities")
    
    # Check if we're in edit mode
    if ss.editing_id and ss.editing_item_type == "activity":
        # Find the activity being edited
        activity_to_edit = next((a for a in ss.activities if a["id"] == ss.editing_id), None)
        
        if activity_to_edit:
            st.subheader("Edit Activity")
            result = edit_form("activity", activity_to_edit)
            
            if result is not None:
                # Update the activity
                index = next(i for i, a in enumerate(ss.activities) if a["id"] == ss.editing_id)
                ss.activities[index] = result
                ss.editing_id = None
                ss.editing_item_type = None
                save_to_local_storage()  # Save after editing
                st.success("Activity updated!")
                st.rerun()
            elif result is None and ss.editing_id:
                # Cancel edit mode
                ss.editing_id = None
                ss.editing_item_type = None
                st.rerun()
        else:
            ss.editing_id = None
            ss.editing_item_type = None
    
    # Add activity form
    with st.expander("➕ Add Activity"):
        a_title = st.text_input("Title", key="a_title")
        a_date = st.date_input("Date", value=date.today(), key="a_date")
        a_time = st.time_input("Time", value=dtime(9, 0), key="a_time")
        a_duration = st.number_input("Duration (minutes)", min_value=1, max_value=1440, value=60, key="a_duration")
        if st.button("Add Activity", key="btn_add_activity"):
            if a_title.strip():
                ss.activities.append({"id": gen_id("activity"), "Title": a_title.strip(), "Date": a_date, 
                                    "Time": a_time, "Duration": a_duration})
                save_to_local_storage()  # Save after adding
                st.success("Activity added.")
    
    st.markdown("### Your activities")
    activities_to_show = filter_items(ss.activities)
    if not activities_to_show:
        st.info("No activities.")
    else:
        for a in sorted(activities_to_show, key=lambda x:(x["Date"],x["Time"])):
            cols = st.columns([0.5, 0.15, 0.15, 0.2])
            with cols[0]:
                st.markdown(f"**{a['Title']}**<br><span class='small'>📅 {a['Date']} ⏰ {a['Time'].strftime('%H:%M')} · Duration: {a['Duration']} min</span>", unsafe_allow_html=True)
            with cols[1]:
                if st.button("Edit", key=f"edit_{a['id']}"):
                    ss.editing_id = a["id"]
                    ss.editing_item_type = "activity"
                    st.rerun()
            with cols[2]:
                if st.button("Complete", key=f"complete_{a['id']}"):
                    ss.activities = [x for x in ss.activities if x["id"] != a["id"]]
                    save_to_local_storage()  # Save after completing
                    st.rerun()
            with cols[3]:
                if st.button("Delete", key=f"del_{a['id']}"):
                    ss.activities = [x for x in ss.activities if x["id"] != a["id"]]
                    save_to_local_storage()  # Save after deleting
                    st.rerun()

elif page == "Habits":
    st.title("🔄 Habits")
    
    # Check if we're in edit mode
    if ss.editing_id and ss.editing_item_type == "habit":
        # Find the habit being edited
        habit_to_edit = next((h for h in ss.habits if h["id"] == ss.editing_id), None)
        
        if habit_to_edit:
            st.subheader("Edit Habit")
            result = edit_form("habit", habit_to_edit)
            
            if result is not None:
                # Update the habit
                index = next(i for i, h in enumerate(ss.habits) if h["id"] == ss.editing_id)
                ss.habits[index] = result
                ss.editing_id = None
                ss.editing_item_type = None
                save_to_local_storage()  # Save after editing
                st.success("Habit updated!")
                st.experimental_rerun()
            elif result is None and ss.editing_id:
                # Cancel edit mode
                ss.editing_id = None
                ss.editing_item_type = None
                st.experimental_rerun()
        else:
            ss.editing_id = None
            ss.editing_item_type = None
    
    # Add habit form
    with st.expander("➕ Add Habit"):
        h_habit = st.text_input("Habit", key="h_habit")
        h_freq = st.selectbox("Frequency", ["Daily", "Weekly", "Monthly"], key="h_freq")
        if st.button("Add Habit", key="btn_add_habit"):
            if h_habit.strip():
                ss.habits.append({"id": gen_id("habit"), "Habit": h_habit.strip(), "Frequency": h_freq})
                save_to_local_storage()  # Save after adding
                st.success("Habit added.")
    
    st.markdown("### Your habits")
    habits_to_show = filter_items(ss.habits)
    if not habits_to_show:
        st.info("No habits.")
    else:
        for h in habits_to_show:
            cols = st.columns([0.7, 0.15, 0.15])
            with cols[0]:
                st.markdown(f"**{h['Habit']}**<br><span class='small'>Frequency: {h['Frequency']}</span>", unsafe_allow_html=True)
            with cols[1]:
                if st.button("Edit", key=f"edit_{h['id']}"):
                    ss.editing_id = h["id"]
                    ss.editing_item_type = "habit"
                    st.rerun()
            with cols[2]:
                if st.button("Delete", key=f"del_{h['id']}"):
                    ss.habits = [x for x in ss.habits if x["id"] != h["id"]]
                    save_to_local_storage()  # Save after deleting
                    st.rerun()

elif page == "Notes":
    st.title("📝 Notes")
    
    # Check if we're in edit mode
    if ss.editing_id and ss.editing_item_type == "note":
        # Find the note being edited
        note_to_edit = next((n for n in ss.notes if n["id"] == ss.editing_id), None)
        
        if note_to_edit:
            st.subheader("Edit Note")
            result = edit_form("note", note_to_edit)
            
            if result is not None:
                # Update the note
                index = next(i for i, n in enumerate(ss.notes) if n["id"] == ss.editing_id)
                ss.notes[index] = result
                ss.editing_id = None
                ss.editing_item_type = None
                save_to_local_storage()  # Save after editing
                st.success("Note updated!")
                st.experimental_rerun()
            elif result is None and ss.editing_id:
                # Cancel edit mode
                ss.editing_id = None
                ss.editing_item_type = None
                st.experimental_rerun()
        else:
            ss.editing_id = None
            ss.editing_item_type = None
    
    # Add note form
    with st.expander("➕ Add Note"):
        n_note = st.text_area("Note", key="n_note", height=100)
        n_date = st.date_input("Date", value=date.today(), key="n_date")
        if st.button("Add Note", key="btn_add_note"):
            if n_note.strip():
                ss.notes.append({"id": gen_id("note"), "Note": n_note.strip(), "Date": n_date})
                save_to_local_storage()  # Save after adding
                st.success("Note added.")
    
    st.markdown("### Your notes")
    notes_to_show = sorted(filter_items(ss.notes), key=lambda x: x.get("Date", date.today()), reverse=True)
    if not notes_to_show:
        st.info("No notes.")
    else:
        for n in notes_to_show:
            cols = st.columns([0.7, 0.15, 0.15])
            with cols[0]:
                st.markdown(f"<div class='card'><strong>{n.get('Date', '')}</strong><br>{summarize_any_text(n.get('Note', ''))}</div>", unsafe_allow_html=True)
            with cols[1]:
                if st.button("Edit", key=f"edit_{n['id']}"):
                    ss.editing_id = n["id"]
                    ss.editing_item_type = "note"
                    st.experimental_rerun()
            with cols[2]:
                if st.button("Delete", key=f"del_{n['id']}"):
                    ss.notes = [x for x in ss.notes if x["id"] != n["id"]]
                    save_to_local_storage()  # Save after deleting
                    st.experimental_rerun()

elif page == "Summarizer":
    st.title("📝 Text Summarizer")
    st.markdown("Summarize any text, article, note, or document")
    
    # Text input with example
    example_text = """Artificial intelligence (AI) is intelligence demonstrated by machines, as opposed to the natural intelligence displayed by animals including humans. AI applications include advanced web search engines (e.g., Google), recommendation systems (used by YouTube, Amazon and Netflix), understanding human speech (such as Siri and Alexa), self-driving cars (e.g., Tesla), automated decision-making and competing at the highest level in strategic game systems (such as chess and Go). As machines become increasingly capable, tasks considered to require "intelligence" are often removed from the definition of AI, a phenomenon known as the AI effect. For instance, optical character recognition is frequently excluded from things considered to be AI, having become a routine technology."""
    
    ss.summarizer_text = st.text_area("Enter text to summarize:", value=ss.summarizer_text, height=200, 
                                     placeholder="Paste your text, article, note, or any content here...",
                                     help=f"Example: {example_text[:100]}...")
    
    # Customization options
    col1, col2 = st.columns(2)
    with col1:
        max_sentences = st.slider("Maximum sentences:", min_value=1, max_value=10, value=3)
    with col2:
        max_length = st.slider("Maximum length:", min_value=50, max_value=500, value=300)
    
    # Summarize button
    if st.button("Summarize Text", type="primary"):
        if ss.summarizer_text.strip():
            ss.summarizer_result = summarize_any_text(ss.summarizer_text, max_sentences, max_length)
        else:
            st.warning("Please enter some text to summarize.")
    
    # Display result
    if ss.summarizer_result:
        st.markdown("### Summary")
        st.markdown(f"<div class='summary-box'>{ss.summarizer_result}</div>", unsafe_allow_html=True)
        
        # Character count
        st.caption(f"Summary length: {len(ss.summarizer_result)} characters")
        
        # Copy to clipboard button
        st.markdown(f"""
        <script>
        function copyToClipboard() {{
            navigator.clipboard.writeText(`{ss.summarizer_result.replace('`', '\\`')}`);
            alert('Summary copied to clipboard!');
        }}
        </script>
        <button onclick="copyToClipboard()" style="margin-top: 10px; padding: 8px 16px; background-color: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer;">
            Copy Summary
        </button>
        """, unsafe_allow_html=True)

elif page == "Calendar":
    st.title("📅 Calendar")
    
    # Calendar navigation
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("⬅️ Previous"):
            ss.calendar_month = ss.calendar_month - timedelta(days=1)
            ss.calendar_month = ss.calendar_month.replace(day=1)
            st.rerun()
    with col2:
        st.markdown(f"### {ss.calendar_month.strftime('%B %Y')}")
    with col3:
        if st.button("Next ➡️"):
            if ss.calendar_month.month == 12:
                ss.calendar_month = ss.calendar_month.replace(year=ss.calendar_month.year+1, month=1)
            else:
                ss.calendar_month = ss.calendar_month.replace(month=ss.calendar_month.month+1)
            st.rerun()
    
    # Generate calendar
    first_day = ss.calendar_month.replace(day=1)
    start_idx = first_day.weekday()  # Monday is 0, Sunday is 6
    days_in_month = (first_day.replace(month=first_day.month % 12 + 1, day=1) - timedelta(days=1)).day
    
    # Calendar header
    weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    cols = st.columns(7)
    for i, col in enumerate(cols):
        col.markdown(f"**{weekdays[i]}**")
    
    # Calendar days
    day_counter = 1
    for i in range(6):  # Up to 6 weeks
        cols = st.columns(7)
        for j in range(7):
            with cols[j]:
                if (i == 0 and j < start_idx) or day_counter > days_in_month:
                    st.write("")
                else:
                    current_date = first_day.replace(day=day_counter)
                    day_tasks = [t for t in ss.tasks if t["Date"] == current_date]
                    day_activities = [a for a in ss.activities if a["Date"] == current_date]
                    
                    # Highlight today
                    is_today = current_date == date.today()
                    day_style = "border: 2px solid #FFD700; border-radius: 5px; padding: 5px;" if is_today else ""
                    
                    # Display day with task/activity count
                    st.markdown(f"<div style='{day_style}'>"
                               f"<strong>{day_counter}</strong><br>"
                               f"<small>📝 {len(day_tasks)} | 🎯 {len(day_activities)}</small>"
                               f"</div>", unsafe_allow_html=True)
                    
                    day_counter += 1
# ------------------ Setup Background Notifications ------------------
setup_background_notifications()

# ------------------ Check for Due Notifications ------------------
for item in ss.tasks+ss.activities:
    if due_soon(item):
        notify("⏰ Reminder", f"{item.get('Title','')} at {item['Time'].strftime('%H:%M')}", item.get("id"))
        item["Status"]="Notified"

# Auto-refresh
if ss.auto_refresh:
    st.markdown(f"<meta http-equiv='refresh' content='{ss.auto_refresh_secs}'>", unsafe_allow_html=True)
    st.markdown(f"<div class='small'>Auto-refreshing every {ss.auto_refresh_secs} seconds...</div>", unsafe_allow_html=True)