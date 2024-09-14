from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import re
import wikipedia
import requests
import sqlite3
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Initialize an empty list to store chat history
chat_history = []

# Add your Google Custom Search Engine ID and API key
CSE_ID = "553d562247e854a5d"
API_KEY = "AIzaSyC0OXEZYoQTlD-RipouZLzRq4neAn0QxQ4"

# Define sources for different roles
role_sources = {
    'doctor': [
        "https://pubmed.ncbi.nlm.nih.gov",
        "https://www.uptodate.com",
        "https://www.medscape.com"
    ],
    'business expert': [
        "https://hbr.org",
        "https://www.investopedia.com",
        "https://www.forbes.com"
    ],
    'counselor': [
        "https://www.counseling.org",
        "https://www.psychologytoday.com",
        "https://www.mindtools.com"
    ],
    'lawyer': [
        "https://www.americanbar.org",
        "https://www.findlaw.com",
        "https://www.justia.com"
    ],
    'engineer': [
        "https://ieeexplore.ieee.org",
        "https://www.engineering.com",
        "https://www.asme.org"
    ],
    'teacher': [
        "https://www.edutopia.org",
        "https://www.teachthought.com",
        "https://www.educationworld.com"
    ]
}

# Database setup
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    if 'username' in session:
        return render_template('index.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Hash the password
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        # Store user in the database
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Query the user
        user = User.query.filter_by(username=username).first()

        # Check if the user exists and the password is correct
        if user and check_password_hash(user.password, password):
            # Store the username in the session
            session['username'] = username
            # Redirect to the index page after successful login
            return redirect(url_for('index'))
        else:
            return jsonify(message="Invalid username or password.")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/get-response', methods=['POST'])
def get_response():
    user_input = request.json.get('message')

    # Handle basic greetings
    if "hi" in user_input.lower() or "hello" in user_input.lower():
        bot_response = f"Hi there, {session['username']}! How can I help you today?"
    elif "how are you" in user_input.lower():
        bot_response = "I'm just a bot, but I'm doing great! How about you?"
    elif "bye" in user_input.lower():
        bot_response = "Goodbye! Have a nice day!"
    else:
        # Check if the input contains a math operation
        if is_math_operation(user_input):
            try:
                # Evaluate the math expression
                result = eval_math_expression(user_input)
                bot_response = f"The result is: {result}"
            except Exception as e:
                bot_response = f"Sorry, I couldn't compute that. Error: {str(e)}"
        else:
            # Determine the role based on the input
            role = identify_role(user_input)
            if role:
                bot_response = generate_role_based_response(role, user_input)
            else:
                # If no role is identified, perform a general search
                bot_response = fetch_information(user_input)
                if not bot_response:
                    bot_response = "I didn't quite understand that. Could you rephrase?"

    # Store the conversation in history
    chat_history.append({'user': user_input, 'bot': bot_response})
    
    return jsonify(response=bot_response)

@app.route('/get-history', methods=['GET'])
def get_history():
    return jsonify(history=chat_history)

def is_math_operation(user_input):
    # Regular expression to detect basic math operations
    return re.search(r'\b\d+(\s*[-+*/]\s*\d+)+\b', user_input)

def eval_math_expression(expression):
    # Evaluates the math expression safely
    return eval(expression)

def identify_role(user_input):
    role_keywords = {
        'doctor': ['health', 'sick', 'ill', 'doctor', 'medicine', 'disease', 'symptoms'],
        'business expert': ['business', 'market', 'strategy', 'sales', 'profit', 'management'],
        'counselor': ['stress', 'relationship', 'mental health', 'anxiety', 'depression'],
        'lawyer': ['law', 'legal', 'contract', 'court', 'agreement', 'rights'],
        'engineer': ['engineering', 'technology', 'design', 'mechanics', 'electronics'],
        'teacher': ['education', 'teaching', 'learning', 'student', 'school', 'lesson']
    }

    tokens = user_input.lower().split()
    for role, keywords in role_keywords.items():
        for keyword in keywords:
            if keyword in tokens:
                return role

    return None

def generate_role_based_response(role, user_input):
    if role:
        # Fetch information based on the role
        information = fetch_information(user_input, role)
        return f"As a {role}, here's what I found: {information}"
    else:
        return "I'm here to help! Can you tell me more about your situation?"

def fetch_information(query, role=None):
    if role and role in role_sources:
        # Perform a search on specific websites related to the role
        search_query = f"{query} site:{' OR site:'.join(role_sources[role])}"
    else:
        # General search query
        search_query = query

    # Attempt to fetch from Wikipedia first
    try:
        summary = wikipedia.summary(query, sentences=5)
        return summary
    except Exception as e:
        pass

    # If Wikipedia fails, use Google Custom Search API
    try:
        url = f"https://www.googleapis.com/customsearch/v1?q={search_query}&cx={CSE_ID}&key={API_KEY}"
        response = requests.get(url)
        search_results = response.json()
        if 'items' in search_results:
            first_result = search_results['items'][0]
            return first_result['snippet']
        else:
            return None
    except Exception as e:
        return f"An error occurred: {str(e)}"

# Configure the SQLAlchemy part of the app instance
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Create the SQLAlchemy db instance
db = SQLAlchemy(app)

# Define the User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

# Initialize the database
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
