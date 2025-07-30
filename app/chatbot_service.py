import os
import requests
import re
import random
from flask import session
from database import get_user_memory, update_user_memory, extract_user_info, get_conversation_history, add_to_conversation_history

def get_chatbot_response(user_message, conversation_history=None, username=None):
    """
    Get response from AI model via API with permanent memory
    
    Args:
        user_message (str): The user's message to the chatbot
        conversation_history (list, optional): Previous conversation messages
        username (str, optional): The username of the current user
        
    Returns:
        str: The AI's response with memory updates and 1-4 keywords in bold
    """
    # Use default username if not provided
    if not username and 'username' in session:
        username = session['username']
    elif not username:
        username = "guest"
    
    # Print debug information
    print(f"\033[96m[DEBUG]\033[0m Processing message for user: {username}")
    print(f"\033[96m[DEBUG]\033[0m Message content: {user_message}")
    
    # Extract user information from message
    memory_updates = []
    if username != "guest":
        user_info = extract_user_info(user_message)
        print(f"\033[96m[DEBUG]\033[0m Extracted user info: {user_info}")
        
        if user_info:  # Only process if we found information
            for memory_type, value in user_info:
                update_result = update_user_memory(username, memory_type, value)
                if update_result:
                    memory_updates.append(update_result)
    
    # Get user memory
    user_memory = get_user_memory(username) if username != "guest" else {}
    
    # Get conversation history from database if not provided
    if not conversation_history and username != "guest":
        conversation_history = get_conversation_history(username)
    elif not conversation_history:
        conversation_history = []
    
    # Prepare system message with context and user memory
    system_message = "You are a helpful assistant for the PixelMind text encryption system. "
    
    # Add user memory to system message if available
    if username != "guest" and user_memory:
        system_message += "Here is what you know about the user:\n"
        if user_memory.get("name"):
            system_message += f"- Name: {user_memory['name']}\n"
        if user_memory.get("place"):
            system_message += f"- Location: {user_memory['place']}\n"
        if user_memory.get("friends"):
            system_message += f"- Friends: {', '.join(user_memory['friends'])}\n"
        if user_memory.get("priorities"):
            system_message += f"- Priorities: {', '.join(user_memory['priorities'])}\n"
        if user_memory.get("preferences"):
            system_message += "- Preferences:\n"
            for pref, sentiment in user_memory["preferences"].items():
                system_message += f"  - {pref}: {sentiment}\n"
        if user_memory.get("other_info"):
            system_message += "- Other Information:\n"
            for key, value in user_memory["other_info"].items():
                system_message += f"  - {key}: {value}\n"
    
    system_message += "\nWhen responding, make 1-4 important keywords in your response bold by surrounding them with ** (e.g., **keyword**). Choose only the most important words to emphasize. Keep your answers concise and helpful."
    
    # Debug print system message
    print(f"\033[96m[DEBUG]\033[0m System message: {system_message}")
    
    # Prepare messages with history
    messages = [{"role": "system", "content": system_message}]
    
    if conversation_history:
        # Add previous exchanges to maintain context
        for message in conversation_history[-100:]:
            messages.append(message)
    
    # Add current user message
    messages.append({"role": "user", "content": user_message})
    
    # Make API call
    try:
        api_key = os.environ.get('CHATBOT_API_KEY', '')
        api_url = os.environ.get('API_URL', '')
        
        if not api_key:
            print("\033[91m[ERROR]\033[0m CHATBOT_API_KEY environment variable is not set or empty")
            return "I'm sorry, the chatbot is not properly configured. Please contact the administrator."
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "llama-3.3-70b-versatile",  # Or any other model you want to use
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 500  # Increased to allow for longer responses
        }
        
        print(f"\033[96m[DEBUG]\033[0m Making API request to: {api_url}")
        
        response = requests.post(api_url, headers=headers, json=data)
        
        # Print response status for debugging
        print(f"\033[96m[DEBUG]\033[0m Response status: {response.status_code}")
        
        # If there's an error, try to get more details
        if response.status_code != 200:
            print(f"\033[91m[ERROR]\033[0m Error response body: {response.text}")
            response.raise_for_status()
        
        result = response.json()
        bot_response = result["choices"][0]["message"]["content"]
        
        # Store conversation in database if username is provided
        if username != "guest":
            # Add user message to history
            add_to_conversation_history(username, {"role": "user", "content": user_message})
            
            # Add bot response to history
            add_to_conversation_history(username, {"role": "assistant", "content": bot_response})
        
        if memory_updates:
            memory_update_text = "**Memory Updated:**<br>"
            bot_response = f"<div class='memory-update'>{memory_update_text}</div>\n\n{bot_response}"
            
            print(f"\033[92m[SUCCESS]\033[0m Memory updated: {memory_updates}")
        
        # Modified function to limit bold keywords to 1-4 words
        def limit_bold_keywords(text):
            # First, collect all existing bold sections
            existing_bold = re.findall(r'\*\*(.*?)\*\*', text)
            
            # If we already have 1-4 bold words, return the text as is
            if 1 <= len(existing_bold) <= 4:
                return text
            
            # If we have more than 4 bold words, keep only the first 4
            if len(existing_bold) > 4:
                # Remove all bold formatting
                text_without_bold = re.sub(r'\*\*', '', text)
                
                # Add bold formatting back to the first 4 words only
                for word in existing_bold[:4]:
                    text_without_bold = text_without_bold.replace(word, f"**{word}**", 1)
                
                return text_without_bold
            
            # If we have no bold words, add 1-4 bold words
            # Remove any existing bold formatting first
            text_without_bold = re.sub(r'\*\*', '', text)
            
            # Find candidate words for bolding (4+ chars, not common words)
            common_words = ['that', 'this', 'with', 'from', 'have', 'your', 'which', 'there', 
                            'their', 'about', 'would', 'could', 'should', 'these', 'those', 
                            'then', 'than', 'when', 'what', 'where', 'will', 'been', 'were', 
                            'they', 'them', 'some', 'such', 'please', 'thanks', 'thank', 'hello']
            
            # Find words with 4+ chars
            candidate_words = [word for word in re.findall(r'\b[A-Za-z][A-Za-z]{3,}\b', text_without_bold) 
                               if word.lower() not in common_words]
            
            # Select 1-4 words to bold
            num_words_to_bold = min(4, max(1, len(candidate_words)))
            
            # Prioritize words that might be important based on context
            priority_words = [word for word in candidate_words if word.lower() in ['encryption', 'security', 'password', 'pixelmind', 'protect', 'encrypt', 'decrypt', 'message', 'key', 'privacy']]
            
            # If we have priority words, use them first
            words_to_bold = priority_words[:num_words_to_bold] if priority_words else []
            
            # If we still need more words, randomly select from remaining candidates
            if len(words_to_bold) < num_words_to_bold and candidate_words:
                remaining_words = [word for word in candidate_words if word not in words_to_bold]
                random.shuffle(remaining_words)
                words_to_bold.extend(remaining_words[:num_words_to_bold - len(words_to_bold)])
            
            # Apply bold formatting to selected words
            result_text = text_without_bold
            for word in words_to_bold:
                # Bold only the first occurrence of each word
                pattern = r'\b' + re.escape(word) + r'\b'
                result_text = re.sub(pattern, f'**{word}**', result_text, count=1)
            
            return result_text
        
        # Apply limited bold formatting to keywords
        bot_response = limit_bold_keywords(bot_response)
        
        return bot_response
    except requests.exceptions.RequestException as e:
        print(f"\033[91m[ERROR]\033[0m Request error calling API: {e}")
        return "I'm sorry, I **encountered** a network issue while connecting to the AI service. Please try again later."
    except KeyError as e:
        print(f"\033[91m[ERROR]\033[0m Response parsing error: {e}")
        print(f"\033[91m[ERROR]\033[0m Response content: {response.text if 'response' in locals() else 'No response'}")
        return "I'm sorry, I received an **unexpected** response format from the AI service. Please try again later."
    except Exception as e:
        print(f"\033[91m[ERROR]\033[0m Unexpected error calling API: {e}")
        return "I'm sorry, I **encountered** an issue while processing your request. Please try again later."