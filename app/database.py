from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import os
import sys
import re
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# MongoDB connection
def get_db():
    """
    Establish connection to MongoDB and return database object
    Prints connection status to console
    """
    try:
        # Get MongoDB connection string from environment variable
        mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017')
        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)  # 5 second timeout
        
        # Test the connection
        client.admin.command('ping')
        print("\033[92m[SUCCESS]\033[0m MongoDB connection established successfully!")
        
        db = client.pixelmind_db
        return db
    
    except Exception as e:
        print(f"\033[91m[ERROR]\033[0m MongoDB connection failed: {str(e)}")
        print("Make sure MongoDB is running and the connection string is correct.")
        sys.exit(1)  # Exit the application if database connection fails

def validate_password(password):
    """
    Validate password meets requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    Returns tuple (is_valid, message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not any(char.isupper() for char in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(char.islower() for char in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(char.isdigit() for char in password):
        return False, "Password must contain at least one numerical digit"
    
    return True, "Password meets requirements"

# User functions
def create_user(username, password, email):
    """Create a new user in the database"""
    db = get_db()
    
    # Check if user already exists
    if db.users.find_one({"username": username}):
        return False, "Username already exists"
    
    if db.users.find_one({"email": email}):
        return False, "Email already exists"
    
    # Validate password
    is_valid, message = validate_password(password)
    if not is_valid:
        return False, message
    
    # Create new user with hashed password
    user = {
        "username": username,
        "password": generate_password_hash(password),
        "email": email,
        "auth_type": "local"  # Regular local account
    }
    
    db.users.insert_one(user)
    print(f"\033[92m[SUCCESS]\033[0m User '{username}' created successfully")
    return True, "User created successfully"

def create_google_user(username, password, email):
    """Create a new user from Google OAuth"""
    db = get_db()
    
    # Check if user already exists by email
    existing_user = db.users.find_one({"email": email})
    if existing_user:
        if existing_user.get("auth_type") == "google":
            # User already exists with Google auth
            return True, "User already exists"
        else:
            # Update existing user to link Google account
            db.users.update_one(
                {"_id": existing_user["_id"]},
                {"$set": {"auth_type": "google"}}
            )
            return True, "Account linked to Google"
    
    # Create new user with Google auth
    user = {
        "username": username,
        "password": generate_password_hash(password),  # Store a random password
        "email": email,
        "auth_type": "google"  # Mark as Google authenticated
    }
    
    db.users.insert_one(user)
    print(f"\033[92m[SUCCESS]\033[0m Google user '{username}' created successfully")
    return True, "User created successfully"

def validate_user(username, password):
    """
    Validate user credentials
    username can be either username or email
    """
    # credential bypass - modular and can be easily removed
    if username == "guest" and password == "guest":
        print(f"\033[92m[SUCCESS]\033[0m Credential bypass login for '{username}'")
        # Create a minimal user object with just enough data
        guest_user = {
            "username": "guest",
            "email": "guest@example.com"
        }
        return True, guest_user
    
    # Regular authentication flow   
    db = get_db()
    
    # Check if username is an email (contains @ symbol)
    if '@' in username:
        user = db.users.find_one({"email": username})
    else:
        user = db.users.find_one({"username": username})
    
    if user and check_password_hash(user["password"], password):
        print(f"\033[92m[SUCCESS]\033[0m Login successful for user '{user['username']}'")
        return True, user
    
    print(f"\033[93m[WARNING]\033[0m Failed login attempt for username/email '{username}'")
    return False, None

# User memory functions
def get_user_memory(username):
    """Get user memory from database"""
    db = get_db()
    memory = db.user_memory.find_one({"username": username})
    
    if not memory:
        # Initialize empty memory if none exists
        memory = {
            "username": username,
            "name": "",
            "place": "",
            "friends": [],
            "priorities": [],
            "preferences": {},
            "other_info": {}
        }
        db.user_memory.insert_one(memory)
        print(f"\033[92m[INFO]\033[0m Created new memory for user '{username}'")
    
    return memory

def update_user_memory(username, memory_type, value):
    """Update a specific type of user memory"""
    db = get_db()
    
    # Debug print
    print(f"\033[96m[DEBUG]\033[0m Updating memory for {username}: {memory_type} = {value}")
    
    # Get current memory
    memory = get_user_memory(username)
    
    # Update the specific memory type
    if memory_type == "name":
        db.user_memory.update_one(
            {"username": username},
            {"$set": {"name": value}}
        )
        print(f"\033[92m[SUCCESS]\033[0m Updated name for {username} to '{value}'")
        return f"name: {value}"
    
    elif memory_type == "place":
        db.user_memory.update_one(
            {"username": username},
            {"$set": {"place": value}}
        )
        print(f"\033[92m[SUCCESS]\033[0m Updated place for {username} to '{value}'")
        return f"place: {value}"
    
    elif memory_type == "friends":
        # Add to friends list if not already present
        if value not in memory.get("friends", []):
            db.user_memory.update_one(
                {"username": username},
                {"$push": {"friends": value}}
            )
            print(f"\033[92m[SUCCESS]\033[0m Added friend '{value}' for {username}")
        return f"friend: {value}"
    
    elif memory_type == "priorities":
        # Add to priorities list if not already present
        if value not in memory.get("priorities", []):
            db.user_memory.update_one(
                {"username": username},
                {"$push": {"priorities": value}}
            )
            print(f"\033[92m[SUCCESS]\033[0m Added priority '{value}' for {username}")
        return f"priority: {value}"
    
    elif memory_type.startswith("preferences."):
        # Extract the preference key
        pref_key = memory_type.split(".", 1)[1]
        db.user_memory.update_one(
            {"username": username},
            {"$set": {f"preferences.{pref_key}": value}}
        )
        print(f"\033[92m[SUCCESS]\033[0m Updated preference {pref_key}='{value}' for {username}")
        return f"preference: {pref_key} = {value}"
    
    elif memory_type.startswith("other_info."):
        # Extract the info key
        info_key = memory_type.split(".", 1)[1]
        db.user_memory.update_one(
            {"username": username},
            {"$set": {f"other_info.{info_key}": value}}
        )
        print(f"\033[92m[SUCCESS]\033[0m Updated information {info_key}='{value}' for {username}")
        return f"information: {info_key} = {value}"
    
    return None

# Conversation history functions
def get_conversation_history(username):
    """Get conversation history for a user"""
    db = get_db()
    history = db.conversation_history.find_one({"username": username})
    
    if not history:
        # Initialize empty history if none exists
        history = {
            "username": username,
            "messages": []
        }
        db.conversation_history.insert_one(history)
    
    return history.get("messages", [])

def add_to_conversation_history(username, message):
    """Add a message to the conversation history"""
    db = get_db()
    
    # Add message to history
    db.conversation_history.update_one(
        {"username": username},
        {"$push": {"messages": message}},
        upsert=True  # Create the document if it doesn't exist
    )
    
    # Limit history to 100 messages
    db.conversation_history.update_one(
        {"username": username},
        {"$push": {"messages": {"$each": [], "$slice": -100}}}
    )

def extract_user_info(text):
    """
    Extract user information from text using regex patterns
    Returns a list of (memory_type, value) tuples
    """
    info = []
    
    # Debug print
    print(f"\033[96m[DEBUG]\033[0m Extracting user info from: {text}")
    
    # Convert to lowercase for case-insensitive matching
    text_lower = text.lower()
    
    # Name pattern: "my name is X" or "I am X" or "I'm X"
    name_patterns = [
        r"my name is (?:called\s+)?([A-Za-z]+(?:\s+[A-Za-z]+)*)",
        r"(?:i am|i'm) (?:called\s+)?([A-Za-z]+(?:\s+[A-Za-z]+)*)"
    ]
    
    for pattern in name_patterns:
        match = re.search(pattern, text_lower)
        if match:
            name_value = match.group(1)
            # Capitalize the first letter of each word
            name_value = ' '.join(word.capitalize() for word in name_value.split())
            info.append(("name", name_value))
            print(f"\033[96m[DEBUG]\033[0m Found name: {name_value}")
            break
    
    # Place pattern: "I live in X" or "I am from X" or "I'm from X" or "my place is X"
    place_patterns = [
        r"i live in ([A-Za-z]+(?:\s+[A-Za-z]+)*)",
        r"(?:i am|i'm) from ([A-Za-z]+(?:\s+[A-Za-z]+)*)",
        r"my place is ([A-Za-z]+(?:\s+[A-Za-z]+)*)"
    ]
    
    for pattern in place_patterns:
        match = re.search(pattern, text_lower)
        if match:
            place_value = match.group(1)
            # Capitalize the first letter of each word
            place_value = ' '.join(word.capitalize() for word in place_value.split())
            info.append(("place", place_value))
            print(f"\033[96m[DEBUG]\033[0m Found place: {place_value}")
            break
    
    # Friends pattern: "my friend X" or "my friends X, Y, and Z"
    # Fix: Change list of patterns to individual patterns with for loop
    friends_patterns = [
        r"my friend(?:s)? (?:is|are)? ([A-Za-z]+(?:\s+[A-Za-z]+)*(?:,\s+[A-Za-z]+(?:\s+[A-Za-z]+)*)*(?:,? and [A-Za-z]+(?:\s+[A-Za-z]+)*)?)",
        r"my friend(?:s)? name(?:s)? (?:is|are)? ([A-Za-z]+(?:\s+[A-Za-z]+)*(?:,\s+[A-Za-z]+(?:\s+[A-Za-z]+)*)*(?:,? and [A-Za-z]+(?:\s+[A-Za-z]+)*)?)"
    ]
    
    for pattern in friends_patterns:
        match = re.search(pattern, text_lower)
        if match:
            # Split the friends list
            friends_text = match.group(1)
            friends = re.split(r',\s*|\s+and\s+', friends_text)
            for friend in friends:
                if friend.strip():
                    friend_value = ' '.join(word.capitalize() for word in friend.strip().split())
                    info.append(("friends", friend_value))
                    print(f"\033[96m[DEBUG]\033[0m Found friend: {friend_value}")
            break
    
    # Priorities pattern: "my priority is X" or "my priorities are X, Y, and Z"
    priorities_pattern = r"my priorit(?:y|ies) (?:is|are) ([A-Za-z0-9]+(?:\s+[A-Za-z0-9]+)*(?:,\s+[A-Za-z0-9]+(?:\s+[A-Za-z0-9]+)*)*(?:,? and [A-Za-z0-9]+(?:\s+[A-Za-z0-9]+)*)?)"
    match = re.search(priorities_pattern, text_lower)
    if match:
        # Split the priorities list
        priorities_text = match.group(1)
        priorities = re.split(r',\s*|\s+and\s+', priorities_text)
        for priority in priorities:
            if priority.strip():
                info.append(("priorities", priority.strip()))
                print(f"\033[96m[DEBUG]\033[0m Found priority: {priority.strip()}")
    
    # Preferences pattern: "I like X" or "I prefer X" or "I love X" or "I hate X" or "I dislike X"
    preference_patterns = [
        (r"i (?:like|prefer|love) ([A-Za-z0-9]+(?:\s+[A-Za-z0-9]+)*)", "like"),
        (r"i (?:hate|dislike) ([A-Za-z0-9]+(?:\s+[A-Za-z0-9]+)*)", "dislike")
    ]
    
    for pattern, sentiment in preference_patterns:
        for match in re.finditer(pattern, text_lower):
            preference = match.group(1).strip()
            info.append((f"preferences.{preference}", sentiment))
            print(f"\033[96m[DEBUG]\033[0m Found preference: {preference} = {sentiment}")
    
    return info
# Add these functions to your database.py file

def log_user_activity(username, action_type, filename, timestamp=None):
    """
    Log user activity in the database
    action_type: 'encrypt' or 'decrypt'
    """
    import datetime
    
    db = get_db()
    
    # Use current time if timestamp not provided
    if timestamp is None:
        timestamp = datetime.datetime.now()
    
    activity = {
        "username": username,
        "action_type": action_type,
        "filename": filename,
        "timestamp": timestamp
    }
    
    db.activity_logs.insert_one(activity)
    print(f"\033[92m[SUCCESS]\033[0m Logged {action_type} activity for user '{username}'")
    return True

def get_user_activities(username=None, limit=50):
    """
    Retrieve user activities from database
    If username is None, get activities for all users
    """
    db = get_db()
    
    # Query based on username or get all activities
    if username:
        query = {"username": username}
    else:
        query = {}
    
    # Get activities sorted by timestamp (newest first)
    activities = list(db.activity_logs.find(
        query, 
        {"_id": 0}  # Exclude MongoDB _id field
    ).sort("timestamp", -1).limit(limit))
    
    return activities
