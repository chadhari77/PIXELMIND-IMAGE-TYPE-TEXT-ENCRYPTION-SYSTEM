from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify
import os
import shutil
from werkzeug.utils import secure_filename
import fitz
from dotenv import load_dotenv
from authlib.integrations.flask_client import OAuth
import secrets

# Import other modules
import image_operations 
import pdf_operations 
import zip_operations 
import database 
import chatbot_service 

# Get the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def create_app():
    # Load environment variables from .env file
    load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

    app = Flask(__name__, 
                template_folder=os.path.join(PROJECT_ROOT, 'templates'),
                static_folder=os.path.join(PROJECT_ROOT, 'static'))
    app.secret_key = os.environ.get('SECRET_KEY')  

    # Configure OAuth with Authlib
    oauth = OAuth(app)
    
    # Google OAuth configuration using Authlib
    oauth.register(
        name='google',
        client_id=os.environ.get('GOOGLE_CLIENT_ID'),
        client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )

    # Updated upload and directory paths
    UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, 'uploads')
    ALLOWED_EXTENSIONS_TEXT = {'txt', 'md', 'py', 'c', 'cpp', 'java', 'js', 'html', 'css', 'php', 'swift', 'kotlin', 'go', 'rs', 'sh', 'bat'}
    ALLOWED_EXTENSIONS_IMAGE = {'png', 'jpg', 'jpeg'}
    ALLOWED_EXTENSIONS_PDF = {'pdf'}

    # Create necessary directories
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(os.path.join(PROJECT_ROOT, 'static', 'enimg'), exist_ok=True)
    os.makedirs(os.path.join(PROJECT_ROOT, 'uploads'), exist_ok=True)

    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

    def allowed_file(filename, file_type):
        if file_type == 'text':
            return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS_TEXT
        elif file_type == 'image':
            return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS_IMAGE
        elif file_type == 'pdf':
            return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS_PDF
        return False

    @app.route('/')
    def index():
        if 'username' in session:
            return render_template('dashboard.html', username=session['username'])
        return render_template('login.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            
            # MongoDB authentication
            success, user = database.validate_user(username, password)
            
            if success:
                session['username'] = username
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password', 'error')
        
        return render_template('login.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            confirm_password = request.form['confirm_password']
            
            # Validate form data
            if not username or not email or not password:
                flash('All fields are required', 'error')
                return redirect(url_for('register'))
            
            if password != confirm_password:
                flash('Passwords do not match', 'error')
                return redirect(url_for('register'))
            
            # Register user
            success, message = database.create_user(username, password, email)
            
            if success:
                flash('Registration successful! You can now login.', 'success')
                return redirect(url_for('login'))
            else:
                flash(message, 'error')
                return redirect(url_for('register'))
        
        return render_template('register.html')

    # Google OAuth routes - updated for Authlib with account selection
    @app.route('/login/google')
    def google_login():
        # Generate a random state token to prevent CSRF attacks
        session['oauth_state'] = secrets.token_hex(16)
        redirect_uri = url_for('google_authorized', _external=True)
        
        # Add prompt=select_account to force account selection
        return oauth.google.authorize_redirect(
            redirect_uri, 
            state=session['oauth_state'],
            prompt='select_account'  # Force Google to show account selector
        )

    @app.route('/login/google/authorized')
    def google_authorized():
        # Verify state token
        if request.args.get('state') != session.pop('oauth_state', None):
            flash('Invalid state token. Please try again.', 'error')
            return redirect(url_for('login'))
        
        # Get token
        token = oauth.google.authorize_access_token()
        if not token:
            flash('Access denied', 'error')
            return redirect(url_for('login'))
        
        # Get user info - FIX: Use the complete URL
        resp = oauth.google.get('https://www.googleapis.com/oauth2/v2/userinfo')
        user_info = resp.json()
        google_email = user_info['email']
        google_username = user_info.get('name', '').replace(' ', '_').lower()
        
        # Check if user exists in database
        db = database.get_db()
        user = db.users.find_one({"email": google_email})
        
        if user:
            # User exists, log them in
            session['username'] = user['username']
            flash('Logged in with Google successfully!', 'success')
        else:
            # User doesn't exist, create new account
            # Generate unique username if needed
            base_username = google_username if google_username else google_email.split('@')[0]
            unique_username = base_username
            counter = 1
            
            # Make sure username is unique
            while db.users.find_one({"username": unique_username}):
                unique_username = f"{base_username}{counter}"
                counter += 1
            
            # Generate a random password for Google accounts
            google_password = secrets.token_urlsafe(16)
            
            # Create new user
            success, message = database.create_google_user(unique_username, google_password, google_email)
            
            if success:
                session['username'] = unique_username
                flash('Account created and logged in with Google!', 'success')
            else:
                flash(f'Failed to create account: {message}', 'error')
                return redirect(url_for('login'))
        
        return redirect(url_for('dashboard'))

    @app.route('/dashboard')
    def dashboard():
        if 'username' not in session:
            return redirect(url_for('login'))
        return render_template('dashboard.html', username=session['username'])

    @app.route('/encrypt', methods=['GET', 'POST'])
    def encrypt():
        if 'username' not in session:
            return redirect(url_for('login'))
        
        if request.method == 'POST':
            if 'files' not in request.files:
                flash('No file part', 'error')
                return redirect(request.url)
            
            files = request.files.getlist('files')
            
            if not files:
                flash('No selected files', 'error')
                return redirect(request.url)
            
            image_paths = []
            for file in files:
                if file and allowed_file(file.filename, 'text'):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    
                    # Process the file (encrypt)
                    encrypted_image = image_operations.encrypt_file(filepath)
                    
                    # Ensure the static/enimg directory exists
                    static_enimg_dir = os.path.join(PROJECT_ROOT, 'static', 'enimg')
                    os.makedirs(static_enimg_dir, exist_ok=True)
                    
                    # Move the image to the static folder with proper path handling
                    filename = os.path.basename(encrypted_image)
                    static_image_path = os.path.join(static_enimg_dir, filename)
                    
                    if not os.path.exists(static_image_path):
                        shutil.copy(encrypted_image, static_image_path)
                    
                    image_paths.append(static_image_path)
                    
                    # Log activity
                    if 'username' in session:
                        database.log_user_activity(
                            username=session['username'],
                            action_type='encrypt',
                            filename=filename
                        )
            
            # Create PDF from images
            pdf_output_path = os.path.join(PROJECT_ROOT, 'static', 'encrypted_images.pdf')
            pdf_operations.create_pdf_from_images(image_paths, pdf_output_path)
            
            return render_template('encrypt_success.html', filename='encrypted_images.pdf')
        
        return render_template('encrypt.html')

    @app.route('/decrypt', methods=['GET', 'POST'])
    def decrypt():
        if 'username' not in session:
            return redirect(url_for('login'))
        
        if request.method == 'POST':
            if 'file' not in request.files:
                flash('No file part', 'error')
                return redirect(request.url)
            
            file = request.files['file']
            
            if file.filename == '':
                flash('No selected file', 'error')
                return redirect(request.url)
            
            if file and allowed_file(file.filename, 'pdf'):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                # Extract images from PDF using PyMuPDF
                pdf_document = fitz.open(filepath)
                decrypted_files = []
                processed_images = set()  # Track processed images to avoid duplicates
                
                for page_number in range(len(pdf_document)):
                    page = pdf_document.load_page(page_number)
                    image_list = page.get_images(full=True)
                    
                    for image_index, img in enumerate(image_list):
                        xref = img[0]
                        if xref in processed_images:
                            continue  # Skip already processed images
                        
                        base_image = pdf_document.extract_image(xref)
                        image_bytes = base_image["image"]
                        
                        # Generate a unique name for the decrypted file
                        unique_name = f'decrypted_{page_number}_{image_index}.txt'
                        decrypted_file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
                        
                        # Save the image to a temporary file
                        image_path = os.path.join(app.config['UPLOAD_FOLDER'], f'image_{page_number}_{image_index}.png')
                        with open(image_path, 'wb') as img_file:
                            img_file.write(image_bytes)
                        
                        # Process the image (decrypt)
                        decrypted_file = image_operations.decrypt_file(image_path)
                        shutil.move(decrypted_file, decrypted_file_path)
                        decrypted_files.append(decrypted_file_path)
                        
                        processed_images.add(xref)  # Mark this image as processed
                
                # Create a zip file with decrypted files
                zip_filename = 'decrypted_files.zip'
                zip_path = os.path.join(app.config['UPLOAD_FOLDER'], zip_filename)
                zip_operations.create_zip_from_files(decrypted_files, zip_path)
                
                # Log activity
                if 'username' in session:
                    database.log_user_activity(
                        username=session['username'],
                        action_type='decrypt',
                        filename=filename
                    )
                
                return render_template('decrypt_success.html', filename='decrypted_files.zip')
        
        return render_template('decrypt.html')

    @app.route('/download_pdf')
    def download_pdf():
        pdf_path = os.path.join(PROJECT_ROOT, 'static', 'encrypted_images.pdf')
        return send_file(pdf_path, as_attachment=True, download_name='encrypted_images.pdf')

    @app.route('/download_zip')
    def download_zip():
        zip_path = os.path.join(app.config['UPLOAD_FOLDER'], 'decrypted_files.zip')
        return send_file(zip_path, as_attachment=True, download_name='decrypted_files.zip')

    @app.route('/logout')
    def logout():
        # Clear Flask session
        session.pop('username', None)
        session.pop('google_token', None)
        
        # Redirect to home page
        return redirect(url_for('index'))

    @app.route('/activity')
    def activity_log():
        if 'username' not in session:
            return redirect(url_for('login'))
        
        username = session['username']
        
        # Get all activities for the user
        activities = database.get_user_activities(username)
        
        # Format timestamps for display
        for activity in activities:
            # Convert timestamp to string format
            if 'timestamp' in activity and activity['timestamp']:
                activity['timestamp_str'] = activity['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        
        return render_template('activity_log.html', username=username, activities=activities)

    # Chatbot API route
    @app.route('/api/chatbot', methods=['POST'])
    def chatbot_api():
        if request.method == 'POST':
            data = request.json
            user_message = data.get('message', '')
            
            # Get username from session if available
            username = session.get('username', 'guest')
            
            # Get response from chatbot service with permanent memory
            bot_response = chatbot_service.get_chatbot_response(user_message, username=username)
            
            return jsonify({"response": bot_response})

    # Serve chat.css
    @app.route('/static/css/chat.css')
    def serve_chat_css():
        return send_file(os.path.join(PROJECT_ROOT, 'static', 'css', 'chat.css'))

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
