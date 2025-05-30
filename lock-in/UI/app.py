from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import os
from dotenv import load_dotenv
import logging
import uuid
from functools import wraps
import json
from datetime import datetime, timedelta
from preference_questions import PREFERENCE_QUESTIONS, get_default_preferences
import sqlitecloud

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Database configuration
# Using SQLite Cloud
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'  # Keep for compatibility with Flask-SQLAlchemy
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# SQLite Cloud connection
SQLITE_CLOUD_URL = "sqlitecloud://cbqkimyjnk.g3.sqlite.cloud:8860/chinook.sqlite?apikey=NC5QKK2m7shqgXow0sb2MMhNyh8uwQVHcJMAh7H0DQI" 
app.config['SQLITE_CLOUD_ADMIN_KEY'] = 'admin_apikey'

# Initialize database with SQLAlchemy for model definitions
db = SQLAlchemy(app)

# Helper function to get SQLite Cloud connection
def get_cloud_connection():
    return sqlitecloud.connect(SQLITE_CLOUD_URL)

# Define User model (still used for type hints and structure)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    latest_schedule = db.Column(db.Text, nullable=True)  # New column to store latest final_schedule.json
    schedule_timestamp = db.Column(db.DateTime, nullable=True)  # New column to store timestamp when schedule was updated
    preferences = db.Column(db.Text, nullable=True)  # Store user preferences as JSON
    preferences_completed = db.Column(db.Boolean, default=False)  # Flag to track if preferences have been completed
    parsed_json = db.Column(db.Text, nullable=True)  # Store the complete parsed JSON after all missing info is filled
    parsed_json_timestamp = db.Column(db.DateTime, nullable=True)  # When the parsed JSON was last updated
    google_calendar = db.Column(db.Text, nullable=True)  # Store Google Calendar data
    google_calendar_timestamp = db.Column(db.DateTime, nullable=True)  # When the Google Calendar was imported
    custom_prompt = db.Column(db.Text, nullable=True)  # Store personalized prompt versions for schedule generation
    
    def __repr__(self):
        return f'<User {self.email}>'

# Create database tables using SQLite Cloud instead of SQLAlchemy
with app.app_context():
    try:
        conn = get_cloud_connection()
        cursor = conn.cursor()
        
        # Create user table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            latest_schedule TEXT,
            schedule_timestamp TEXT,
            preferences TEXT,
            preferences_completed INTEGER DEFAULT 0,
            parsed_json TEXT,
            parsed_json_timestamp TEXT,
            google_calendar TEXT,
            google_calendar_timestamp TEXT,
            custom_prompt TEXT
        )
        ''')
        conn.commit()
        conn.close()
        logger.info("Database tables have been initialized")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")

CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:5002", "http://127.0.0.1:5002"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Service URLs
EEP1_URL = os.getenv('EEP1_URL', 'http://localhost:5000')

# Add state management
current_schedule = None

logger.debug(f"Using EEP1_URL: {EEP1_URL}")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.before_request
def require_login():
    # List of allowed endpoint prefixes that don't require login
    allowed = ['login', 'register', 'static']
    # If no endpoint is set, return (could be 404)
    if not request.endpoint:
        return

    # If user is not in session and the endpoint does not start with any allowed prefix, redirect to login
    if 'user' not in session and not any(request.endpoint.startswith(ep) for ep in allowed):
        return redirect(url_for('login'))
    
    # If preferences not completed, redirect to preferences page
    # except for these endpoints that don't require completed preferences
    exempt_endpoints = ['preferences', 'save_preferences', 'logout', 'static']
    if 'user' in session and request.endpoint and not any(request.endpoint.startswith(ep) for ep in exempt_endpoints):
        try:
            # Check preferences completion status in SQLite Cloud
            conn = get_cloud_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT preferences_completed FROM user WHERE email = ?", (session['user'],))
            user_row = cursor.fetchone()
            conn.close()
            
            # If preferences not completed, redirect to preferences page
            if user_row and not user_row[0]:
                return redirect(url_for('preferences'))
        except Exception as e:
            logger.error(f"Error checking preferences status: {str(e)}")

@app.route('/')
@login_required
def index():
    # Connect to SQLite Cloud
    conn = get_cloud_connection()
    cursor = conn.cursor()
    
    # Query user by email
    cursor.execute("SELECT preferences_completed, latest_schedule, schedule_timestamp FROM user WHERE email = ?", (session['user'],))
    user_row = cursor.fetchone()
    conn.close()
    
    if not user_row:
        logger.error(f"User not found in database: {session['user']}")
        return redirect(url_for('logout'))
    
    # Redirect to preferences if not completed
    if not user_row[0]:  # preferences_completed
        return redirect(url_for('preferences'))
        
    # Check if user has a recent schedule
    has_recent_schedule = False
    if user_row[1] and user_row[2]:  # latest_schedule and schedule_timestamp
        try:
            schedule_timestamp = datetime.fromisoformat(user_row[2])
            if datetime.utcnow() - schedule_timestamp < timedelta(days=7):
                has_recent_schedule = True
        except (ValueError, TypeError) as e:
            logger.error(f"Error parsing schedule timestamp: {str(e)}")
    
    if has_recent_schedule:
        return render_template('schedule-only.html')
    else:
        return render_template('index.html')

@app.route('/schedule-only')
@login_required
def schedule_only():
    # Connect to SQLite Cloud
    conn = get_cloud_connection()
    cursor = conn.cursor()
    
    # Query user by email
    cursor.execute("SELECT latest_schedule, schedule_timestamp FROM user WHERE email = ?", (session['user'],))
    user_row = cursor.fetchone()
    conn.close()
    
    # Check if user has a recent schedule
    has_recent_schedule = False
    if user_row and user_row[0] and user_row[1]:  # latest_schedule and schedule_timestamp exist
        try:
            schedule_timestamp = datetime.fromisoformat(user_row[1])
            if datetime.utcnow() - schedule_timestamp < timedelta(days=7):
                has_recent_schedule = True
        except (ValueError, TypeError) as e:
            logger.error(f"Error parsing schedule timestamp: {str(e)}")
    
    if not has_recent_schedule:
        return redirect(url_for('index'))
    return render_template('schedule-only.html')

@app.route('/parse-schedule', methods=['POST'])
@login_required
def parse_schedule():
    global current_schedule
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'No text provided'}), 400

        logger.info(f"Sending parse request to EEP1 with text: {data['text'][:100]}...")
        
        # Send to EEP1 for parsing
        response = requests.post(f'{EEP1_URL}/parse-schedule', json=data, timeout=30)
        response.raise_for_status()
        response_data = response.json()
        
        logger.info(f"Received response from EEP1: {response_data}")
        
        # Debug: Log questions from EEP1
        if 'questions' in response_data:
            logger.info(f"Questions from EEP1: {json.dumps(response_data['questions'])}")
        else:
            logger.info("No questions in EEP1 response")
        
        # Store the schedule
        if 'schedule' in response_data:
            current_schedule = response_data['schedule']
            logger.info(f"Updated current schedule with new data")
            logger.debug(f"Current schedule: {current_schedule}")

            # Store the schedule in EEP1
            store_response = requests.post(f'{EEP1_URL}/store-schedule', json={'schedule': current_schedule}, timeout=30)
            if store_response.ok:
                logger.info("Successfully stored schedule in EEP1")
            else:
                logger.warning(f"Failed to store schedule in EEP1: {store_response.text}")

            # Update user's latest_schedule in the database
            try:
                # Connect to SQLite Cloud
                conn = get_cloud_connection()
                cursor = conn.cursor()
                
                # Update the user record
                current_time = datetime.utcnow().isoformat()
                schedule_json = json.dumps(response_data['schedule'])
                
                # If the schedule is complete, also save it as parsed_json
                if response_data.get('status') == 'complete':
                    cursor.execute(
                        "UPDATE user SET latest_schedule = ?, schedule_timestamp = ?, parsed_json = ?, parsed_json_timestamp = ? WHERE email = ?",
                        (schedule_json, current_time, schedule_json, current_time, session['user'])
                    )
                    logger.info(f"Saved complete parsed JSON to user record for {session['user']}")
                else:
                    cursor.execute(
                        "UPDATE user SET latest_schedule = ?, schedule_timestamp = ? WHERE email = ?",
                        (schedule_json, current_time, session['user'])
                    )
                
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"Error updating user record: {str(e)}")
        else:
            logger.warning("No schedule in response data")
            
        return jsonify(response_data)

    except requests.exceptions.Timeout:
        logger.error("Request to EEP1 timed out")
        return jsonify({'error': 'Request timed out'}), 504
    except requests.exceptions.RequestException as e:
        logger.error(f"Request to EEP1 failed: {str(e)}")
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/get-schedule', methods=['GET'])
@login_required
def get_schedule():
    try:
        if current_schedule:
            return jsonify({'schedule': current_schedule})
        user = User.query.filter_by(email=session['user']).first()
        if user and user.latest_schedule:
            schedule = json.loads(user.latest_schedule)
            return jsonify({'schedule': schedule})
        response = requests.get(f'{EEP1_URL}/get-schedule', timeout=30)
        response.raise_for_status()
        return jsonify(response.json())

    except requests.exceptions.Timeout:
        return jsonify({'error': 'Request timed out'}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/answer-question', methods=['POST'])
@login_required
def answer_question():
    """Answer a question about missing information in the schedule"""
    global current_schedule
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        logger.info(f"Processing answer for {data.get('type', 'unknown')} question")

        # First, try to get the current schedule from EEP1
        try:
            schedule_response = requests.get(f'{EEP1_URL}/get-schedule', timeout=10)
            if schedule_response.ok:
                current_schedule = schedule_response.json().get('schedule')
                logger.info("Retrieved current schedule from EEP1")
            else:
                logger.warning("Could not retrieve schedule from EEP1, using local schedule")
        except Exception as e:
            logger.warning(f"Error getting schedule from EEP1: {str(e)}")

        # Use the schedule from the request if provided, otherwise use current_schedule
        schedule = data.get('schedule', current_schedule)
        if not schedule:
            logger.error("No schedule available")
            return jsonify({"error": "No schedule available"}), 400

        # Construct request data for EEP1
        request_data = {
            'item_id': data['item_id'],
            'type': data['type'],
            'answer': data['answer'],
            'field': data.get('field'),
            'target': data.get('target'),
            'target_type': data.get('target_type'),
            'schedule': schedule
        }

        # Remove None values
        request_data = {k: v for k, v in request_data.items() if v is not None}

        logger.debug(f"Sending request to EEP1: {request_data}")

        # Send request to EEP1
        response = requests.post(
            f'{EEP1_URL}/answer-question',
            json=request_data,
            timeout=10
        )

        # Log response for debugging
        logger.debug(f"EEP1 response status: {response.status_code}")
        logger.debug(f"EEP1 response content: {response.text}")

        if not response.ok:
            error_msg = "Error from EEP1"
            try:
                error_data = response.json()
                error_msg = error_data.get('error', error_msg)
            except:
                error_msg = response.text or error_msg
            logger.error(f"EEP1 error: {error_msg}")
            return jsonify({"error": error_msg}), response.status_code

        response_data = response.json()
        
        # Log the full EEP1 response for debugging
        logger.info(f"Received response from EEP1 with keys: {list(response_data.keys())}")
        
        # Update current schedule if provided in response
        if 'schedule' in response_data:
            current_schedule = response_data['schedule']
            logger.debug(f"Updated current_schedule with response data")

            # If the answer was for a course code for a meeting, propagate it to related tasks
            if data.get('type') == 'course_code' and data.get('target_type') == 'meeting':
                meeting_description = data.get('target')
                course_code = data.get('answer')
                
                # Apply the course code to any preparation task related to this meeting
                if meeting_description and course_code:
                    for task in current_schedule.get('tasks', []):
                        if task.get('related_event') == meeting_description and not task.get('course_code'):
                            task['course_code'] = course_code
                            logger.info(f"Propagated course code {course_code} to task {task.get('description')}")
            
            # Store the updated schedule in EEP1
            try:
                store_response = requests.post(f'{EEP1_URL}/store-schedule', json={'schedule': current_schedule}, timeout=10)
                if store_response.ok:
                    logger.info("Successfully stored updated schedule in EEP1")
                else:
                    logger.warning(f"Failed to store updated schedule in EEP1: {store_response.text}")
            except Exception as e:
                logger.warning(f"Error storing schedule in EEP1: {str(e)}")

            # Update user's latest_schedule in the database
            try:
                # Connect to SQLite Cloud
                conn = get_cloud_connection()
                cursor = conn.cursor()
                
                # Update the latest schedule
                current_time = datetime.utcnow().isoformat()
                schedule_json = json.dumps(response_data['schedule'])
                
                cursor.execute(
                    "UPDATE user SET latest_schedule = ?, schedule_timestamp = ? WHERE email = ?",
                    (schedule_json, current_time, session['user'])
                )
                
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"Error updating user record: {str(e)}")

        # Pass the ready_for_optimization flag from EEP1 to the frontend
        ready_for_optimization = response_data.get('ready_for_optimization', False)
        logger.info(f"IMPORTANT - ready_for_optimization flag from EEP1: {ready_for_optimization}")

        # Check if all questions have been answered
        has_more_questions = response_data.get('has_more_questions', True)
        logger.info(f"IMPORTANT - has_more_questions flag from EEP1: {has_more_questions}")

        # Construct response to frontend
        frontend_response = {
            "success": True,
            "schedule": response_data.get('schedule'),
            "message": "Answer submitted successfully",
            "ready_for_optimization": ready_for_optimization,
            "has_more_questions": has_more_questions,
            "questions": response_data.get('questions')
        }
        
        # If no more questions, save the complete parsed JSON to the user's record
        if ready_for_optimization and not has_more_questions and 'schedule' in response_data:
            try:
                conn = get_cloud_connection()
                cursor = conn.cursor()
                
                cursor.execute(
                    "UPDATE user SET parsed_json = ?, parsed_json_timestamp = ? WHERE email = ?",
                    (json.dumps(response_data['schedule']), datetime.utcnow().isoformat(), session['user'])
                )
                
                conn.commit()
                conn.close()
                logger.info(f"Saved parsed JSON to user record for {session['user']}")
            except Exception as e:
                logger.error(f"Error saving parsed JSON: {str(e)}")
        
        logger.info(f"Sending response to frontend with ready_for_optimization={ready_for_optimization}")
        return jsonify(frontend_response)

    except requests.Timeout:
        logger.error("Timeout while connecting to EEP1")
        return jsonify({"error": "Timeout while connecting to EEP1"}), 504
    except requests.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        return jsonify({"error": f"Request failed: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

def check_missing_info(schedule: dict) -> list:
    questions = []
    
    # Log the schedule structure for debugging
    logger.info(f"Schedule structure - meetings: {len(schedule.get('meetings', []))}, tasks: {len(schedule.get('tasks', []))}")
    for task in schedule.get('tasks', []):
        logger.info(f"Task structure: {json.dumps(task)}")
    
    # Create mappings to track relationships and avoid redundant questions
    meeting_ids_with_missing_course = set()  # Track meeting IDs missing course codes
    meeting_descriptions = {}  # Map meeting IDs to descriptions
    related_tasks = {}  # Map meeting descriptions to their related task IDs
    
    # First pass: collect all meetings and their properties
    for meeting in schedule.get("meetings", []):
        meeting_id = meeting.get("id")
        description = meeting.get("description")
        if meeting_id and description:
            meeting_descriptions[meeting_id] = description
        
        # Track meetings missing course codes
        if not meeting.get("course_code") and meeting.get("type") in ["exam", "presentation"]:
            if meeting_id:
                meeting_ids_with_missing_course.add(meeting_id)
    
    # Second pass: identify related tasks
    for task in schedule.get("tasks", []):
        related_event = task.get("related_event")
        task_id = task.get("id")
        if related_event and task_id:
            if related_event not in related_tasks:
                related_tasks[related_event] = []
            related_tasks[related_event].append(task_id)
    
    # Now generate questions for meetings
    for meeting in schedule.get("meetings", []):
        if not meeting.get("time"):
            questions.append({
                "type": "time",
                "question": f"What time is the {meeting.get('description')}?",
                "field": "time",
                "target": meeting.get("description"),
                "target_type": "meeting",
                "target_id": meeting.get("id")
            })
        if not meeting.get("duration_minutes"):
            questions.append({
                "type": "duration",
                "question": f"How long is the {meeting.get('description')}?",
                "field": "duration_minutes",
                "target": meeting.get("description"),
                "target_type": "meeting",
                "target_id": meeting.get("id")
            })
        if not meeting.get("course_code") and meeting.get("type") in ["exam", "presentation"]:
            questions.append({
                "type": "course_code",
                "question": f"What is the course code for the {meeting.get('description')}?",
                "field": "course_code",
                "target": meeting.get("description"),
                "target_type": "meeting",
                "target_id": meeting.get("id")
            })
    
    # Check tasks - only ask for course_code when not related to a meeting we're already asking about
    for task in schedule.get("tasks", []):
        # Only process tasks that don't have a course code and are preparation tasks
        if not task.get("course_code") and task.get("category") == "preparation":
            related_event = task.get("related_event")
            
            # Skip if this task is related to a meeting we're already asking about
            should_skip = False
            for meeting in schedule.get("meetings", []):
                # If the meeting description matches the related_event and we're already asking about it
                if meeting.get("description") == related_event and meeting.get("id") in meeting_ids_with_missing_course:
                    should_skip = True
                    break
            
            # Only add the question if we shouldn't skip it
            if not should_skip:
                logger.info(f"Adding course code question for task: {task.get('description')}")
            else:
                logger.info(f"Skipping course code question for task: {task.get('description')} - related to meeting being queried")
                
            if not should_skip:
                questions.append({
                    "type": "course_code",
                    "question": f"What is the course code for the {task.get('description')}?",
                    "field": "course_code",
                    "target": task.get("description"),
                    "target_type": "task",
                    "target_id": task.get("id")
                })
    
    return questions

@app.route('/generate-optimized-schedule', methods=['POST'])
@login_required
def generate_optimized_schedule():
    """Generate an optimized schedule using EEP1 service, which will call IEP2."""
    global current_schedule
    try:
        data = request.get_json()
        logger.info("Generating optimized schedule")
        
        # Check if this is a regeneration request
        is_regeneration = data.get('regenerate', False)
        
        # Get user data from SQLite Cloud
        conn = get_cloud_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT parsed_json, preferences, google_calendar FROM user WHERE email = ?", 
            (session['user'],)
        )
        user_row = cursor.fetchone()
        conn.close()
        
        if not user_row:
            logger.error(f"User not found in database: {session['user']}")
            return jsonify({"error": "User not found"}), 404
        
        # Determine which schedule data to use
        schedule = None
        
        # If regeneration is requested and parsed_json exists, use that
        if is_regeneration and user_row[0]:  # parsed_json
            try:
                schedule = json.loads(user_row[0])
                logger.info("Using stored parsed JSON for schedule regeneration")
            except json.JSONDecodeError:
                logger.error(f"Error parsing stored JSON for user {session['user']}")
        
        # Otherwise use schedule from request or current_schedule
        if not schedule:
            schedule = data.get('schedule', current_schedule)
            logger.info("Using current schedule or schedule from request")
        
        if not schedule:
            logger.error("No schedule available for optimization")
            return jsonify({"error": "No schedule available"}), 400
        
        # Always load and include user preferences
        user_preferences = None
        if user_row[1]:  # preferences
            try:
                user_preferences = json.loads(user_row[1])
                logger.info(f"Including user preferences in optimization request")
            except json.JSONDecodeError:
                logger.error(f"Error parsing user preferences JSON for user {session['user']}")
        
        # Always load and include Google Calendar if available
        google_calendar = None
        if user_row[2]:  # google_calendar
            try:
                google_calendar = json.loads(user_row[2])
                logger.info(f"Including Google Calendar data in optimization request")
            except json.JSONDecodeError:
                logger.error(f"Error parsing Google Calendar JSON for user {session['user']}")
        
        # Call EEP1 to generate optimized schedule (it will call IEP2 internally)
        logger.info("Calling EEP1 to generate optimized schedule")
        
        # Always include all available data in the request
        request_data = {
            'schedule': schedule
        }
        
        # Add preferences if available
        if user_preferences:
            request_data['preferences'] = user_preferences
            
        # Add Google Calendar if available
        if google_calendar:
            request_data['google_calendar'] = google_calendar
        
        response = requests.post(
            f'{EEP1_URL}/generate-optimized-schedule',
            json=request_data,
            timeout=350  # Longer timeout for schedule generation
        )
        
        if not response.ok:
            error_msg = "Error from EEP1"
            try:
                error_data = response.json()
                error_msg = error_data.get('error', error_msg)
            except:
                error_msg = response.text or error_msg
            logger.error(f"EEP1 error: {error_msg}")
            return jsonify({"error": error_msg}), response.status_code
        
        response_data = response.json()
        
        # Update current schedule with optimized schedule
        current_schedule = response_data
        logger.info("Updated current schedule with optimized schedule")
        
        # Update user's record with the new schedule
        try:
            # Connect to SQLite Cloud
            conn = get_cloud_connection()
            cursor = conn.cursor()
            
            # Update the latest_schedule
            current_time = datetime.utcnow().isoformat()
            schedule_json = json.dumps(response_data)
            
            cursor.execute(
                "UPDATE user SET latest_schedule = ?, schedule_timestamp = ? WHERE email = ?",
                (schedule_json, current_time, session['user'])
            )
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error updating user record: {str(e)}")

        return jsonify(response_data)
        
    except requests.Timeout:
        logger.error("Timeout while connecting to EEP1")
        return jsonify({"error": "Timeout while connecting to EEP1"}), 504
    except requests.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        return jsonify({"error": f"Request failed: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "GET":
        # If user is already logged in, redirect to index
        if 'user' in session:
            return redirect(url_for('index'))
        return render_template('login.html', error=None, success=None)
    else:
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            # Connect to SQLite Cloud
            conn = get_cloud_connection()
            cursor = conn.cursor()
            
            # Query user by email
            cursor.execute("SELECT id, email, password, first_name, last_name, latest_schedule, schedule_timestamp, preferences_completed FROM user WHERE email = ?", (email,))
            user_row = cursor.fetchone()
            conn.close()
            
            if not user_row:
                logger.info(f"Login attempt with non-existent email: {email}")
                flash('Email address not found.')
                return render_template('login.html', error='Email address not found.', success=None)
            
            # Check if the password matches
            if not check_password_hash(user_row[2], password):
                logger.info(f"Failed login attempt for user: {email}")
                flash('Incorrect password.')
                return render_template('login.html', error='Incorrect password.', success=None)
                
            # Success! Set up the session
            session['user'] = email
            session['first_name'] = user_row[3]  # first_name
            logger.info(f"User logged in successfully: {email}")
            
            # Check if user has a schedule and it's less than 7 days old
            has_recent_schedule = False
            if user_row[5] and user_row[6]:  # latest_schedule and schedule_timestamp
                try:
                    schedule_timestamp = datetime.fromisoformat(user_row[6])
                    if datetime.utcnow() - schedule_timestamp < timedelta(days=7):
                        has_recent_schedule = True
                except (ValueError, TypeError) as e:
                    logger.error(f"Error parsing schedule timestamp: {str(e)}")
            
            if has_recent_schedule:
                return redirect(url_for('schedule_only'))
            return redirect(url_for('index'))
            
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            flash('An error occurred during login.')
            return render_template('login.html', error='Login failed. Please try again.', success=None)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "GET":
        # If user is already logged in, redirect to index
        if 'user' in session:
            return redirect(url_for('index'))
        return render_template('login.html', error=None)
    else:
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        
        # Validate required fields
        if not all([email, password, confirm_password, first_name, last_name]):
            flash('All fields are required.')
            return render_template('login.html', error='All fields are required.')
        
        if password != confirm_password:
            flash('Passwords do not match.')
            return render_template('login.html', error='Passwords do not match.')
        
        try:
            # Connect to SQLite Cloud
            conn = get_cloud_connection()
            cursor = conn.cursor()
            
            # Check if email already exists
            cursor.execute("SELECT email FROM user WHERE email = ?", (email,))
            existing_user = cursor.fetchone()
            
            if existing_user:
                conn.close()
                flash('Email already exists.')
                return render_template('login.html', error='Email address already exists.')
                
            # Create new user with hashed password
            hashed_password = generate_password_hash(password)
            
            # Insert the new user
            cursor.execute(
                "INSERT INTO user (email, password, first_name, last_name, preferences_completed) VALUES (?, ?, ?, ?, ?)",
                (email, hashed_password, first_name, last_name, 0)
            )
            conn.commit()
            conn.close()
            
            # Automatically log in the user after registration
            session['user'] = email
            session['first_name'] = first_name
            logger.info(f"User registered and logged in successfully: {email}")
            # Redirect to preferences page instead of index
            return redirect(url_for('preferences'))
        except Exception as e:
            logger.error(f"Error registering user: {str(e)}")
            flash('An error occurred during registration.')
            return render_template('login.html', error='Registration failed. Please try again.')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/reset-schedule', methods=['POST'])
@login_required
def reset_schedule():
    try:
        # Connect to SQLite Cloud
        conn = get_cloud_connection()
        cursor = conn.cursor()
        
        # Reset the schedule data in the database
        cursor.execute(
            "UPDATE user SET latest_schedule = NULL, parsed_json = NULL, " +
            "parsed_json_timestamp = NULL, schedule_timestamp = NULL " +
            "WHERE email = ?", 
            (session['user'],)
        )
        
        conn.commit()
        conn.close()
        logger.info(f"Reset schedule data for user: {session['user']}")
            
        # Reset the global current_schedule
        global current_schedule
        current_schedule = None

        # Call EEP1 to reset the stored schedule from storage
        response = requests.post(f'{EEP1_URL}/reset-stored-schedule', timeout=10)
        if response.ok:
            logger.info("Successfully reset stored schedule in EEP1.")
        else:
            logger.warning(f"Failed to reset stored schedule in EEP1: {response.text}")

        return jsonify({
            "status": "success", 
            "message": "Schedule reset successful. Google Calendar data and preferences are still available."
        })
    except Exception as e:
        logger.error(f"Error in reset schedule: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# New routes for preferences handling
@app.route('/preferences', methods=['GET', 'POST'])
@login_required
def preferences():
    """Display and process user preferences form"""
    # Get the user email from session
    user_email = session.get('user')
    
    # Connect to SQLite Cloud
    conn = get_cloud_connection()
    cursor = conn.cursor()
    
    # Query user by email
    cursor.execute("SELECT preferences, preferences_completed FROM user WHERE email = ?", (user_email,))
    user_row = cursor.fetchone()
    
    if not user_row:
        logger.error(f"User not found in database: {user_email}")
        return redirect(url_for('logout'))
    
    # Handle form submission (POST request)
    if request.method == 'POST':
        preferences = {}
        # Process each question from our defined questions list
        for question in PREFERENCE_QUESTIONS:
            if question['type'] == 'complex':
                # Handle complex questions with subfields
                preferences[question['id']] = {}
                for subfield in question['subfields']:
                    field_name = f"{question['id']}_{subfield['id']}"
                    value = request.form.get(field_name)
                    if value:
                        preferences[question['id']][subfield['id']] = value
            else:
                # Handle simple questions
                value = request.form.get(question['id'])
                if value:
                    preferences[question['id']] = value
        
        # Update user record
        try:
            # Update preferences in database
            preferences_json = json.dumps(preferences)
            cursor.execute(
                "UPDATE user SET preferences = ?, preferences_completed = ? WHERE email = ?",
                (preferences_json, 1, user_email)
            )
            conn.commit()
            logger.info(f"Preferences saved for user: {user_email}")
            
            # Close connection
            conn.close()
            
            # Redirect to the schedule page
            return redirect(url_for('index'))
        except Exception as e:
            conn.close()
            logger.error(f"Error saving preferences: {str(e)}")
            return render_template(
                'preferences.html', 
                questions=PREFERENCE_QUESTIONS,
                user_preferences=preferences,
                error="Failed to save preferences. Please try again."
            )
    
    # Display form (GET request)
    user_preferences = None
    if user_row[0]:  # If preferences exist
        try:
            user_preferences = json.loads(user_row[0])
        except json.JSONDecodeError:
            logger.error(f"Error parsing user preferences JSON for user {user_email}")
    
    # Close connection
    conn.close()
    
    return render_template(
        'preferences.html', 
        questions=PREFERENCE_QUESTIONS,
        user_preferences=user_preferences
    )

# Google Calendar Integration Routes
@app.route('/google-calendar/authorize', methods=['GET'])
@login_required
def google_calendar_authorize():
    """Start the Google Calendar authorization flow."""
    try:
        # Set the redirect URI to the callback route
        redirect_uri = f"{request.url_root.rstrip('/')}/google-calendar/callback"
        
        # Call EEP1 to get the authorization URL
        response = requests.get(
            f"{EEP1_URL}/google-calendar/authorize", 
            params={'redirect_uri': redirect_uri},
            timeout=10
        )
        
        if response.status_code != 200:
            logger.error(f"Error getting authorization URL from EEP1: {response.text}")
            return jsonify({"error": "Failed to initialize Google Calendar authorization"}), 500
        
        # Get the authorization URL from the response
        data = response.json()
        auth_url = data.get('url')
        
        if not auth_url:
            logger.error("No authorization URL returned from EEP1")
            return jsonify({"error": "Failed to get authorization URL"}), 500
        
        # Store the state in the session
        session['google_auth_state'] = data.get('state')
        
        # Redirect the user to the authorization URL
        return redirect(auth_url)
    except Exception as e:
        logger.error(f"Error initiating Google Calendar authorization: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/google-calendar/export-to-google', methods=['POST'])
@login_required
def export_to_google_calendar():
    """Export the user's schedule to Google Calendar."""
    try:
        user = User.query.filter_by(email=session['user']).first()
        
        # Check if we have a schedule to export
        if not user.latest_schedule:
            return jsonify({"error": "No schedule available to export to Google Calendar"}), 400
        
        # Check if we have Google credentials
        credentials_data = None
        if 'google_credentials' in session:
            credentials_data = session['google_credentials']
        
        # If no credentials, the UI will redirect to authorization
        if not credentials_data:
            # Set the export flow flag so we know to resume the export after authorization
            session['is_export_flow'] = True
            return jsonify({"error": "Google Calendar authorization required", "needs_auth": True}), 401
        
        # Load the latest schedule
        try:
            schedule = json.loads(user.latest_schedule)
        except json.JSONDecodeError:
            logger.error(f"Error parsing schedule JSON for user {user.email}")
            return jsonify({"error": "Invalid schedule data"}), 400
        
        # Load imported Google Calendar data if available
        imported_events = None
        if user.google_calendar:
            try:
                imported_events = json.loads(user.google_calendar)
            except json.JSONDecodeError:
                logger.error(f"Error parsing Google Calendar JSON for user {user.email}")
        
        # Call EEP1 to export the schedule
        export_data = {
            'credentials': credentials_data,
            'schedule': schedule,
            'skip_meals': False  # Optional: allow user to configure this
        }
        
        # Add imported events if available
        if imported_events:
            export_data['imported_events'] = imported_events
        
        response = requests.post(
            f"{EEP1_URL}/google-calendar/export-schedule",
            json=export_data,
            timeout=60  # Longer timeout for exporting many events
        )
        
        if response.status_code != 200:
            # Check if it's an authorization error
            if response.status_code == 401:
                # Clear credentials and redirect to authorization
                session.pop('google_credentials', None)
                # Set the export flow flag so we know to resume the export after authorization
                session['is_export_flow'] = True
                return jsonify({
                    "error": "Google Calendar authorization required", 
                    "needs_auth": True
                }), 401
            
            error_data = response.json()
            error_msg = error_data.get('error', 'Unknown error')
            logger.error(f"Error exporting schedule to Google Calendar: {error_msg}")
            return jsonify({"error": error_msg}), response.status_code
        
        # Return the response from EEP1
        return jsonify(response.json())
        
    except Exception as e:
        logger.error(f"Error in export_to_google_calendar: {str(e)}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

@app.route('/google-calendar/callback', methods=['GET'])
@login_required
def google_calendar_callback():
    """Handle the callback from Google OAuth."""
    try:
        # Get the authorization code from the request
        code = request.args.get('code')
        if not code:
            logger.error("No authorization code in callback")
            flash('Google Calendar authorization failed: No authorization code received.')
            return redirect(url_for('index'))
        
        # Prepare the callback data
        redirect_uri = f"{request.url_root.rstrip('/')}/google-calendar/callback"
        callback_data = {
            'code': code,
            'redirect_uri': redirect_uri
        }
        
        # Call EEP1 to exchange the code for tokens
        response = requests.post(
            f"{EEP1_URL}/google-calendar/callback",
            json=callback_data,
            timeout=10
        )
        
        if response.status_code != 200:
            logger.error(f"Error exchanging code for tokens: {response.text}")
            flash('Google Calendar authorization failed. Please try again.')
            return redirect(url_for('index'))
        
        # Get the credentials from the response
        data = response.json()
        credentials = data.get('credentials')
        
        if not credentials:
            logger.error("No credentials in response from EEP1")
            flash('Google Calendar authorization failed: No credentials received.')
            return redirect(url_for('index'))
        
        # Store the credentials in the session for later use
        session['google_credentials'] = credentials
        
        # Use the credentials to fetch the user's calendar
        fetch_response = requests.post(
            f"{EEP1_URL}/google-calendar/fetch",
            json={'credentials': credentials},
            timeout=30
        )
        
        if fetch_response.status_code != 200:
            logger.error(f"Error fetching calendar data: {fetch_response.text}")
            flash('Failed to fetch Google Calendar data.')
            return redirect(url_for('index'))
        
        # Get the calendar data from the response
        fetch_data = fetch_response.json()
        google_calendar = fetch_data.get('google_calendar')
        
        if not google_calendar:
            logger.error("No calendar data in response from EEP1")
            flash('No calendar data received from Google Calendar.')
            return redirect(url_for('index'))
        
        # Save the calendar data to the user's record
        user = User.query.filter_by(email=session['user']).first()
        user.google_calendar = json.dumps(google_calendar)
        user.google_calendar_timestamp = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Google Calendar data saved for user {user.email}")
        flash('Google Calendar imported successfully!')
        
        # If the request was for export (check a flag in the session), redirect to schedule page
        if session.get('is_export_flow'):
            session.pop('is_export_flow', None)
            return redirect(url_for('schedule_only'))
        
        # Otherwise redirect back to the index page
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error in Google Calendar callback: {str(e)}")
        flash(f'Error importing Google Calendar: {str(e)}')
        return redirect(url_for('index'))

# -------------------------------
# IEP4 Chat Integration
# -------------------------------
@app.route('/chat', methods=['POST'])
@login_required
def chat():
    """Process a chat message to modify schedule interactively."""
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'No message provided'}), 400
            
        user = User.query.filter_by(email=session['user']).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        # Check if we have a schedule
        if not user.latest_schedule:
            return jsonify({'error': 'No schedule found. Please generate a schedule first.'}), 400
        
        # Get the schedule as a Python dict
        schedule = json.loads(user.latest_schedule)
        
        # Get chat history from session or initialize empty list
        if 'chat_history' not in session:
            session['chat_history'] = []
            
        # Add user message to history
        session['chat_history'].append({
            'role': 'user',
            'content': data['message']
        })
        
        # Prepare data for EEP1
        eep1_data = {
            'message': data['message'],
            'user_id': user.id,
            'chat_history': session['chat_history']
        }
        
        # Send to EEP1 for processing
        response = requests.post(f'{EEP1_URL}/chat', json=eep1_data, timeout=300)
        response.raise_for_status()
        response_data = response.json()
        
        # Extract assistant response and updated schedule
        if 'response' in response_data:
            # Add assistant response to chat history
            session['chat_history'].append({
                'role': 'assistant',
                'content': response_data['response']
            })
            
            # Limit chat history to last 10 messages to prevent session bloat
            if len(session['chat_history']) > 10:
                session['chat_history'] = session['chat_history'][-10:]
                
            # Save chat history to session
            session.modified = True
            
        # Update user's schedule if present
        if 'schedule' in response_data:
            # Save the updated schedule
            user.latest_schedule = json.dumps(response_data['schedule'])
            user.schedule_timestamp = datetime.utcnow()
            db.session.commit()
            
        return jsonify(response_data)
        
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Request to EEP1 timed out'}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Request to EEP1 failed: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/finalize-chat', methods=['POST'])
@login_required
def finalize_chat():
    """Finalize chat and update the user's custom prompt."""
    try:
        user = User.query.filter_by(email=session['user']).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        # Get the chat history from session
        chat_history = session.get('chat_history', [])
        
        # If no chat history, return early
        if not chat_history:
            return jsonify({'message': 'No chat history to process'}), 200
            
        # Get the original prompt
        original_prompt = user.custom_prompt
        if not original_prompt:
            # Fetch the default prompt from EEP1
            prompt_response = requests.get(f'{EEP1_URL}/get-prompt', params={'user_id': user.id}, timeout=30)
            prompt_response.raise_for_status()
            original_prompt = prompt_response.json().get('prompt', '')
            
        # Prepare data for EEP1
        data = {
            'original_prompt': original_prompt,
            'chat_history': chat_history,
            'user_id': user.id
        }
        
        # Send to EEP1 for processing
        response = requests.post(f'{EEP1_URL}/update-prompt', json=data, timeout=300)
        response.raise_for_status()
        response_data = response.json()
        
        # Update the user's custom prompt
        if 'custom_prompt' in response_data:
            user.custom_prompt = response_data['custom_prompt']
            db.session.commit()
            logger.info(f"Updated custom prompt for user {user.email}")
            
            # Clear chat history after updating prompt
            session.pop('chat_history', None)
            session.modified = True
            
        return jsonify({'message': 'Chat finalized and prompt updated', 'success': True})
        
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Request to EEP1 timed out'}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Request to EEP1 failed: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500
        
@app.route('/get-chat-history', methods=['GET'])
@login_required
def get_chat_history():
    """Return the current chat history from session."""
    try:
        chat_history = session.get('chat_history', [])
        return jsonify({'chat_history': chat_history})
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True) 