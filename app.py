import os
import random
import json
import math
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- App Configuration ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'a-super-secret-key-that-is-hard-to-guess'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///life_simulator.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- Database and Login Manager Initialization ---
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- Gemini API Configuration ---
GEMINI_API_KEYS = os.getenv("GEMINI_API_KEYS", "").split(',')
api_key_index = 0

if not all(GEMINI_API_KEYS) or GEMINI_API_KEYS == ['']:
    print("WARNING: Gemini API keys not found or are empty in .env file. The application may not function correctly.")

# --- Game Constants ---
ALL_PERKS = [
    "Genius Intellect",
    "Artistic Talent",
    "Athletic Prowess",
    "Charismatic Leader",
    "Financial Mogul",
    "Kind Heart",
    "Resilient Body",
    "Lucky Charm",
    "Inventive Mind",
    "Musical Prodigy",
    "Master Negotiator",
    "Photographic Memory",
    "Night Owl Focus",
    "Early Riser Energy",
    "Perpetual Optimism",
    "Skeptical Mind",
    "Silver Tongue",
    "Stone Cold Poker Face",
    "Pack Rat Tendencies",
    "Minimalist Lifestyle",
    "Master Chef Skills",
    "Gardening Green Thumb",
    "DIY Handyman",
    "Tech Savvy",
    "Analog Lover",
    "Boundless Curiosity",
    "Commitment Phobe",
    "Eternal Student",
    "Natural Therapist",
    "Cold-Blooded Calm",
    "Hot-Temper Burst",
    "Chronic Procrastination",
    "Deadline Crusher",
    "Serial Hobbyist",
    "Collector's Eye",
    "Travel Junkie",
    "Homebody Comfort",
    "Social Butterfly",
    "Introvert Recharge",
    "Photographer's Eye",
    "Slow and Steady",
    "Speed Demon",
    "Perceptive Observer",
    "Absent-Minded Professor",
    "Wallflower Charm",
    "Spotlight Seeker",
    "Coincidence Magnet",
    "Conspiracy Theorist",
    "Lucky Penny Finder",
    "Jinxed Luck",
    "Silver Lining Finder",
    "Perfectionist Tendencies",
    "Happy-Go-Lucky",
    "Blunt Honesty",
    "White Lie Expert",
    "Master of Small Talk",
    "Deep Conversationalist",
    "Emotionally Intuitive",
    "Emotionally Reserved",
    "Night Vision",
    "Daydream Weaver",
    "Memory Like a Sieve",
    "Eidetic Recall",
    "Street Smart",
    "Book Smart",
    "Natural Leader",
    "Reluctant Follower",
    "Team Player",
    "Lone Wolf",
    "Adaptive Chameleon",
    "Stubborn as Ox",
    "Flexible Thinker",
    "Risk Averse",
    "Gambler's Instinct",
    "Safety First",
    "Adrenaline Seeker",
    "Cautious Investor",
    "Impulsive Buyer",
    "Savvy Saver",
    "Generous Soul",
    "Miserly Ways",
    "Prankster Spirit",
    "Serious Stoic",
    "Optimized Routine",
    "Chaotic Energy",
    "Organizational Guru",
    "Creative Mess",
    "Multitasking Pro",
    "Monotasking Master",
    "Hyperfocused",
    "Easily Distracted",
    "Translator Tongue",
    "Monolingual Comfort",
    "Sense of Direction",
    "Perpetual Lost",
    "Negotiation Tactician",
    "Concession Giver",
    "Fashion Forward",
    "Fashionably Late",
    "DIY Medical Kit",
    "Health Nut",
    "Fast Healer",
    "Fragile Constitution",
    "Logical Analyzer",
    "Spiritual Seeker",
    "Animal Whisperer",
    "Allergic to Pets",
    "Green Thumb Failure",
    "Crafty Maker",
    "Tech-Phobic",
    "Quick Wit",
    "Dry Humor"
]


# --- Database Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    characters = db.relationship('Character', backref='player', lazy=True)
    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)

class Character(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(50), nullable=False)
    is_alive = db.Column(db.Boolean, default=True, nullable=False)
    age = db.Column(db.Integer, default=0)
    score = db.Column(db.Integer, default=0)
    events = db.relationship('LifeEvent', backref='character', lazy=True, cascade="all, delete-orphan")
    attributes = db.relationship('Attribute', backref='character', lazy=True, cascade="all, delete-orphan")
    perks = db.relationship('Perk', backref='character', lazy=True, cascade="all, delete-orphan")
    choices = db.relationship('Choice', backref='character', lazy=True, cascade="all, delete-orphan")
    achievements = db.relationship('Achievement', backref='character', lazy=True, cascade="all, delete-orphan")

class LifeEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    character_id = db.Column(db.Integer, db.ForeignKey('character.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    summary = db.Column(db.Text, nullable=False)

class Attribute(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    character_id = db.Column(db.Integer, db.ForeignKey('character.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    health = db.Column(db.Integer, default=100)
    wealth = db.Column(db.BigInteger, default=500) # Changed to BigInteger
    happiness = db.Column(db.Integer, default=75)
    karma = db.Column(db.Integer, default=0)
    iq = db.Column(db.Integer, default=100)

class Perk(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    character_id = db.Column(db.Integer, db.ForeignKey('character.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)

class Choice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    character_id = db.Column(db.Integer, db.ForeignKey('character.id'), nullable=False)
    description = db.Column(db.String(255), nullable=False)

class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    character_id = db.Column(db.Integer, db.ForeignKey('character.id'), nullable=False)
    description = db.Column(db.String(255), nullable=False)

@login_manager.user_loader
def load_user(user_id): return User.query.get(int(user_id))

def call_gemini_api(prompt_data):
    global api_key_index
    if not all(GEMINI_API_KEYS) or GEMINI_API_KEYS == ['']: return None
    try:
        api_key = GEMINI_API_KEYS[api_key_index % len(GEMINI_API_KEYS)]
        api_key_index += 1
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt_text = json.dumps(prompt_data)
        generation_config = genai.types.GenerationConfig(response_mime_type="application/json")
        response = model.generate_content(prompt_text, generation_config=generation_config)
        return json.loads(response.text)
    except (Exception, json.JSONDecodeError) as e:
        print(f"An error occurred with the Gemini API or parsing its response: {e}")
        return None

def get_full_history(character):
    return [{"year": e.year, "summary": e.summary} for e in character.events]

def generate_initial_life_story(character):
    prompt1_data = {
        "task": "generate_initial_narrative",
        "instruction": "You are a life simulator AI. Create a narrative for the first 5 years of a character's life. The character is an infant and toddler during this period. Events MUST be appropriate for this age range (e.g., learning to walk, first words, playing with toys). Perks should manifest in subtle, nascent ways (e.g., a 'Genius' baby might be fascinated by patterns, not solving calculus).",
        "character_details": { "name": character.name, "gender": character.gender, "perks": [p.name for p in character.perks] },
        "response_schema": { "1": "Summary for year 1.", "2": "...", "3": "...", "4": "...", "5": "..." }
    }
    narrative_json = call_gemini_api(prompt1_data)
    if not narrative_json: return False, "Failed to generate life story."
    try:
        full_summary = "\n".join(narrative_json.values())
        for year, summary in narrative_json.items():
            db.session.add(LifeEvent(character_id=character.id, year=int(year), summary=summary))
        character.age = 5
        db.session.commit()
    except (TypeError, KeyError, AttributeError) as e: return False, f"Received an invalid narrative format from the AI: {e}"
    
    prompt2_data = {
        "task": "evaluate_attributes_and_score",
        "narrative": full_summary,
        "response_schema": {
            "health": "Integer 0-100", "wealth": "Integer, can be very large (e.g., 500, 10000, 1000000)",
            "happiness": "Integer 0-100", "karma": "Integer -100 to 100",
            "iq": "Integer 0-300", "life_score": "An integer score from 0-200 for this 5-year period."
        }
    }
    attributes_json = call_gemini_api(prompt2_data)
    if not attributes_json: return False, "Failed to evaluate attributes."
    try:
        character.score += int(attributes_json.get('life_score', 0))
        new_attributes = Attribute(
            character_id=character.id, year=character.age,
            health=int(attributes_json.get('health', 100)),
            wealth=int(attributes_json.get('wealth', 500)),
            happiness=int(attributes_json.get('happiness', 75)),
            karma=int(attributes_json.get('karma', 0)),
            iq=int(attributes_json.get('iq', 100))
        )
        db.session.add(new_attributes)
        db.session.commit()
    except (TypeError, KeyError, ValueError): return False, "Received an invalid attribute format from the AI."
    
    if not generate_turn_results(character, new_attributes, get_full_history(character)):
        return False, "Failed to generate initial choices and achievements."
    return True, "Success"

def generate_turn_results(character, latest_attributes, full_history):
    prompt3_data = {
        "task": "generate_turn_results",
        "instruction": "You are a life simulator AI. All generated choices and achievements MUST be realistic and appropriate for the character's specific age.",
        "character_details": { "name": character.name, "age": character.age, "attributes": { "health": latest_attributes.health, "wealth": latest_attributes.wealth, "happiness": latest_attributes.happiness, "karma": latest_attributes.karma, "iq": latest_attributes.iq } },
        "life_history": full_history,
        "response_schema": { "choices": ["List of 10 string choices"], "achievements": ["List of string achievements"] }
    }
    results_json = call_gemini_api(prompt3_data)
    if not results_json: return False
    try:
        Choice.query.filter_by(character_id=character.id).delete()
        for choice_desc in results_json.get("choices", []):
            db.session.add(Choice(character_id=character.id, description=choice_desc))
        Achievement.query.filter_by(character_id=character.id).delete()
        for achievement_desc in results_json.get("achievements", []):
            db.session.add(Achievement(character_id=character.id, description=achievement_desc))
        db.session.commit()
        return True
    except (TypeError, KeyError): return False

@app.route('/')
def index(): return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('dashboard'))
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and user.check_password(request.form.get('password')):
            login_user(user); return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated: return redirect(url_for('dashboard'))
    if request.method == 'POST':
        if User.query.filter_by(username=request.form.get('username')).first():
            flash('Username already exists.', 'warning'); return redirect(url_for('signup'))
        new_user = User(username=request.form.get('username'))
        new_user.set_password(request.form.get('password'))
        db.session.add(new_user); db.session.commit()
        flash('Account created! Please log in.', 'success'); return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout(): logout_user(); return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    active_characters = Character.query.filter_by(user_id=current_user.id, is_alive=True).order_by(Character.id.desc()).all()
    completed_characters = Character.query.filter_by(user_id=current_user.id, is_alive=False).order_by(Character.id.desc()).all()
    return render_template('dashboard.html', active_characters=active_characters, completed_characters=completed_characters)

@app.route('/leaderboard')
@login_required
def leaderboard():
    dead_characters = Character.query.filter_by(is_alive=False).order_by(Character.score.desc()).all()
    leaderboard_data = []
    for char in dead_characters:
        player = User.query.get(char.user_id)
        leaderboard_data.append({
            'player_name': player.username if player else "Unknown",
            'character_name': char.name, 'age': char.age, 'score': char.score
        })
    return render_template('leaderboard.html', leaderboard=leaderboard_data)

@app.route('/create-character', methods=['GET', 'POST'])
@login_required
def create_character():
    if request.method == 'POST':
        new_char = Character(user_id=current_user.id, name=request.form.get('name'), gender=request.form.get('gender'))
        db.session.add(new_char); db.session.flush()
        for perk_name in request.form.getlist('perks'):
            db.session.add(Perk(character_id=new_char.id, name=perk_name))
        db.session.commit()
        success, message = generate_initial_life_story(new_char)
        if success:
            flash(f'Your new life as {new_char.name} has begun!', 'success')
            return redirect(url_for('life_view', character_id=new_char.id))
        else:
            flash(message, 'danger'); db.session.delete(new_char); db.session.commit()
            return redirect(url_for('create_character'))
    return render_template('create_character.html', perks=random.sample(ALL_PERKS, 6))

@app.route('/life/<int:character_id>')
@login_required
def life_view(character_id):
    character = Character.query.get_or_404(character_id)
    if character.user_id != current_user.id: return redirect(url_for('dashboard'))
    latest_attributes = Attribute.query.filter_by(character_id=character.id).order_by(Attribute.year.desc()).first()
    choices = Choice.query.filter_by(character_id=character.id).all()
    achievements = Achievement.query.filter_by(character_id=character.id).all()
    return render_template('life_view.html', character=character, attributes=latest_attributes, choices=[c.description for c in choices], achievements=achievements)

@app.route('/life/<int:character_id>/end', methods=['POST'])
@login_required
def end_life(character_id):
    character = Character.query.get_or_404(character_id)
    if character.user_id != current_user.id or not character.is_alive:
        return redirect(url_for('dashboard'))
    
    character.is_alive = False
    db.session.add(LifeEvent(character_id=character.id, year=character.age, summary=f"{character.name} decided to end their story peacefully at the age of {character.age}."))
    db.session.commit()
    flash(f"{character.name}'s story has concluded by your choice.", "info")
    return redirect(url_for('life_view', character_id=character.id))

@app.route('/life/<int:character_id>/advance', methods=['POST'])
@login_required
def advance_year(character_id):
    character = Character.query.get_or_404(character_id)
    if character.user_id != current_user.id or not character.is_alive: return redirect(url_for('dashboard'))
    latest_attributes = Attribute.query.filter_by(character_id=character.id).order_by(Attribute.year.desc()).first()
    prompt1_data = {
        "task": "advance_year_narrative",
        "instruction": "You are a life simulator AI. The narrative summary MUST be realistic for the character's specific age. A 6-year-old starts school, a 90-year-old retires.",
        "character_details": { "name": character.name, "age": character.age, "attributes": { "health": latest_attributes.health, "wealth": latest_attributes.wealth, "happiness": latest_attributes.happiness, "karma": latest_attributes.karma, "iq": latest_attributes.iq } },
        "life_history": get_full_history(character),
        "player_choices": request.form.getlist('choices'),
        "response_schema": { "summary": "A 5-8 sentence summary for the next year.", "is_deceased": "A boolean (true/false) indicating if the character died this year." }
    }
    narrative_json = call_gemini_api(prompt1_data)
    if not narrative_json:
        flash("The story could not continue. Please try again.", "danger"); return redirect(url_for('life_view', character_id=character_id))
    try:
        next_year_summary = narrative_json['summary']
        is_deceased = narrative_json['is_deceased']
        character.age += 1
        db.session.add(LifeEvent(character_id=character.id, year=character.age, summary=next_year_summary))
        db.session.commit()
        if is_deceased:
            character.is_alive = False; latest_attributes.health = 0; db.session.commit()
            flash(f"{character.name} has passed away at the age of {character.age}.", "info")
            return redirect(url_for('life_view', character_id=character_id))
    except KeyError:
        flash("Received an invalid story format from the AI.", "danger"); return redirect(url_for('life_view', character_id=character_id))
    
    prompt2_data = {
        "task": "evaluate_attributes_and_score", "narrative": next_year_summary,
        "previous_attributes": { "health": latest_attributes.health, "wealth": latest_attributes.wealth, "happiness": latest_attributes.happiness, "karma": latest_attributes.karma, "iq": latest_attributes.iq },
        "response_schema": {
            "health": "Integer 0-100", "wealth": "Integer, can be very large",
            "happiness": "Integer 0-100", "karma": "Integer -100 to 100",
            "iq": "Integer 0-300", "life_score": "Integer 0-200"
        }
    }
    attributes_json = call_gemini_api(prompt2_data)
    new_attributes = latest_attributes
    if attributes_json:
        try:
            character.score += int(attributes_json.get('life_score', 0))
            new_attributes = Attribute(
                character_id=character.id, year=character.age,
                health=int(attributes_json.get('health', latest_attributes.health)),
                wealth=int(attributes_json.get('wealth', latest_attributes.wealth)),
                happiness=int(attributes_json.get('happiness', latest_attributes.happiness)),
                karma=int(attributes_json.get('karma', latest_attributes.karma)),
                iq=int(attributes_json.get('iq', latest_attributes.iq))
            )
            db.session.add(new_attributes); db.session.commit()
            if new_attributes.health <= 0:
                character.is_alive = False
                db.session.add(LifeEvent(character_id=character.id, year=character.age, summary=f"{character.name}'s journey has come to an end due to poor health."))
                db.session.commit()
                flash(f"{character.name} has passed away at the age of {character.age}.", "info")
                return redirect(url_for('life_view', character_id=character.id))
        except (TypeError, KeyError, ValueError): pass
    generate_turn_results(character, new_attributes, get_full_history(character))
    return redirect(url_for('life_view', character_id=character.id))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
