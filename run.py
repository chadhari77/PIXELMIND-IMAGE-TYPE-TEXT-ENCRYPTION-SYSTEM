import os
import sys

# Get the absolute path of the project root
project_root = os.path.dirname(os.path.abspath(__file__))

# Add the project root and app directory to Python path
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'app'))

# Set the PYTHONPATH environment variable
os.environ['PYTHONPATH'] = project_root

# Now import the app
from app import create_app

if __name__ == "__main__":
    # Ensure .env is loaded from the project root
    from dotenv import load_dotenv
    load_dotenv(os.path.join(project_root, '.env'))
    
    # Create and run the Flask app
    app = create_app()
    app.run(debug=True)