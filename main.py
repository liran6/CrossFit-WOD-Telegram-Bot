import os
import json
import logging
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google import genai
# import google.generativeai as genai
from google.genai import types
from telegram import Bot
from telegram.error import TelegramError
import time
import datetime
import re
#############################################################################################################
# Telegram Bot API token and Channel ID
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')  # Replace with your channel name or chat ID
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

MAX_RETRIES = 5
INITIAL_SLEEP_SEC = 5

def resolve_wod_url(predicted_url):
    """
    Determines the correct URL for today's WOD.
    1. Tries the predicted URL based on date.
    2. Fallback: Scrapes the main page for the latest link.
    """
    # 1. Generate predicted URL (e.g., wednesday-171225)
    # now = datetime.now()
    # day_name = now.strftime('%A').lower()
    # date_str = now.strftime('%d%m%y')
    # predicted_url = f"{base_url.rstrip('/')}/{day_name}-{date_str}/"

    print(f"DEBUG: Checking predicted URL: {predicted_url}")

    try:
        # We use a 5-second timeout and allow redirects
        response = requests.head(predicted_url, allow_redirects=True, timeout=5)
        if response.status_code == 200:
            print("DEBUG: Success! Predicted URL is valid.")
            return predicted_url
    except Exception:
        pass

    # 2. Fallback: Scrape main page hierarchy
    print("DEBUG: Predicted URL invalid or not found. Scraping main page hierarchy...")
    parse_url =urlparse(predicted_url)
    base_url = f"{parse_url.scheme}://{parse_url.netloc}/"
    try:
        main_page = requests.get(base_url, timeout=10)
        main_page.raise_for_status()
        soup = BeautifulSoup(main_page.text, 'html.parser')

        # Locate the first post link as per your inspection image
        first_post = soup.find('article', class_='gh-card post')
        if first_post:
            link_tag = first_post.find('a', class_='gh-card-link')
            if link_tag and link_tag.get('href'):
                found_url = link_tag['href']

                # Convert relative URL to absolute if necessary
                if found_url.startswith('/'):
                    found_url = f"{base_url.rstrip('/')}{found_url}"

                print(f"DEBUG: Fallback successful. Found URL: {found_url}")
                return found_url
    except Exception as e:
        print(f"DEBUG: Fallback failed: {e}")

    return None

# def fetch_wod_description(url):
#     """Fetch the WOD description from the given URL and format the text."""
#     try:
#         logging.info(f"Attempting to fetch WOD description from {url}")
#         response = requests.get(url)
#         response.raise_for_status()  # Raise an error for bad responses
#     except requests.RequestException as e:
#         logging.error(f"HTTP request failed: {e}")
#         return "Error fetching WOD description."

#     soup = BeautifulSoup(response.text, 'html.parser')

#     # Find the section tag containing the WOD
#     section = soup.find('section', class_='gh-content gh-canvas is-body')
#     if not section:
#         logging.error("WOD section not found in the HTML.")
#         return "WOD section not found."

#     # Replace <br> tags with new lines
#     logging.info("Replacing <br> tags with new lines.")
#     for br in section.find_all('br'):
#         br.replace_with('\n')

#     # Get the text content
#     wod_text = section.get_text(separator='\n').strip()
#     logging.info(f"Fetched WOD text: {wod_text[:100]}...")  # Log a snippet of the text

#     # Initialize the formatted text with the header
#     formatted_text = "CrossFit WOD:\n\n"

#     # Define the sections
#     sections = ["Strength","Strerngth","Skill", "skill", "Weightlifting", "Metcon", "Endurance", "CrossFit Strength"]
#     logging.info("Formatting the WOD text into sections.")

#     # Format the text by sections
#     for section in sections:
#         if section in wod_text:
#             logging.info(f"Processing section: {section}")
#             # Find the start of this section
#             start = wod_text.find(section)
#             # Find where the next section begins, to capture only the current section's text
#             end = min([wod_text.find(sec, start + 1) for sec in sections if wod_text.find(sec, start + 1) != -1],
#                       default=len(wod_text))
#             # Extract and clean the section's text
#             part = wod_text[start:end].replace(section + ":", "").strip()
#             formatted_text += f"{section}:\n{part}\n\n"
#         else:
#             logging.warning(f"Section '{section}' not found in the WOD text.")

#     logging.info("Finished formatting the WOD text.")
#     return formatted_text.strip()

def fetch_latest_wod(url: str) -> str or None: # pyright: ignore[reportInvalidTypeForm]
    """
    Fetches the textual content of the daily workout from the website.
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the page: {e}")
        return None

    # Use BeautifulSoup to extract the general textual content of the post
    soup = BeautifulSoup(response.content, 'html.parser')

    # Attempt to find the main content block of the latest post (common for Ghost blogs)
    post_content = soup.find('section', class_='gh-content gh-canvas is-body')
    if post_content:
        # Return the raw text of the content, separated by newlines to preserve some structure
        return post_content.get_text('\n', strip=True)

    print("No suitable WOD content found on the page.")
    return None

# def format_message(wod_text):
    """Format the WOD description into a Telegram-ready message with improved formatting."""
    logging.info("Formatting the WOD text for Telegram with improved formatting.")

    # Define emojis for each section
    section_emojis = {
        "Strength": "💪",
        "Metcon": "🏋️",
        "Skill": "🏋️",
        "Weightlifting": "🏋️‍♂️",
        "Endurance": "🏃‍♂️",
        "Part": "📊"
    }

    # Split the text into lines
    lines = wod_text.split('\n')

    # Process each line
    formatted_lines = []
    for line in lines:
        line = line.strip()
        if line.startswith('*'):
            line = line + '*'
        if line.endswith(':'):
            # Add emoji to section headers and make them bold
            for section, emoji in section_emojis.items():
                if section in line:
                    line = f"{emoji} *{line}*"
                    break
            else:
                line = f"*{line}*"
        elif line.startswith(('Part', 'AMRAP', 'EMOM')):
            # Make Part headers and workout instructions italic
            line = f"_{line}_"
        elif line and not line[0].isdigit():
            # Add bullet points to non-numeric lines
            line = f"• {line}"

        formatted_lines.append(line)

    # Join the lines back together
    formatted_text = '\n'.join(formatted_lines)

    # Remove excessive newlines and add section separators
    formatted_text = re.sub(r'\n\s*\n+', '\n\n', formatted_text).strip()
    formatted_text = formatted_text.replace('CrossFit WOD:', '*CrossFit WOD:*\n---')
    formatted_text = formatted_text.replace('Weightlifting:', '---\n🏋️‍♂️ *Weightlifting:*')

    return f"🏋️‍♂️ *Workout of the Day*\n\n{formatted_text}\n\n---\n💪 _Stay strong and crush it!_"

# def analyze_and_structure_wod(raw_wod_text: str) -> list or None: # pyright: ignore[reportInvalidTypeForm]
#     """
#     Analyzes the raw text using the Gemini API and returns structured JSON data
#     as a list of objects, preserving the original section titles.
#     """
#     if not GEMINI_API_KEY:
#         print("GEMINI_API_KEY is missing. Cannot analyze content.")
#         return None

#     try:
#         client = genai.Client(api_key=GEMINI_API_KEY)

#         # Define the prompt to instruct the LLM on the extraction task
#         prompt = f"""
#         You are an assistant for analyzing a Daily Workout (WOD) from a blog.

#         The raw text of the workout is:
#         ---
#         {raw_wod_text}
#         ---

#         Please extract the workout sections. Do not assume fixed categories.
#         For each section found (e.g., Strength, Metcon, Endurance, Skill, Warmup, etc.),
#         you must extract its exact title and its content.

#         Return the data in JSON format ONLY, structured as a list of objects:
#         [
#           {{"Title": "Original Section Name 1", "Content": "Section content 1"}},
#           {{"Title": "Original Section Name 2", "Content": "Section content 2"}},
#           ...
#         ]

#         - Ensure the 'Title' field uses the exact wording found in the raw text (e.g., 'Strength:', 'Skill', 'W.O.D').
#         - The 'Content' field must contain the complete description of that workout section.
#         """

#         # Generate content with JSON output configuration
#         response = client.models.generate_content(
#             model='gemini-2.5-flash',
#             contents=prompt,
#             config=types.GenerateContentConfig(
#                 response_mime_type="application/json",
#             ),
#         )

#         # The model returns a JSON string; convert it to a Python list
#         return json.loads(response.text)

#     except Exception as e:
#         print(f"Error during analysis with Gemini: {e}")
#         return None

# # def analyze_and_structure_wod(raw_wod_text: str) -> list or None:
#     """
#     Analyzes the raw text using the Gemini API and returns structured JSON data
#     as a list of objects, with a robust retry mechanism for 503 (overload) errors.
#     """
#     GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

#     if not GEMINI_API_KEY:
#         print("GEMINI_API_KEY is missing. Cannot analyze content.")
#         return None

#     client = genai.Client(api_key=GEMINI_API_KEY)

#     # Define the prompt to instruct the LLM on the extraction task
#     # (Assuming your prompt definition is here)
#     prompt = f"""
#     You are an assistant for analyzing a Daily Workout (WOD) from a blog.
#     ... (rest of your prompt) ...
#     """

#     # Loop for retries (Exponential Backoff)
#     for attempt in range(MAX_RETRIES):
#         try:
#             # Attempt to execute the API call
#             response = client.models.generate_content(
#                 model='gemini-2.5-flash',
#                 contents=prompt,
#                 config=types.GenerateContentConfig(
#                     response_mime_type="application/json",
#                 ),
#             )

#             # If successful, return the result and exit the function
#             return json.loads(response.text)

#         except Exception as e:
#             error_message = str(e)

#             # Check for overload error (503 UNAVAILABLE)
#             if '503 UNAVAILABLE' in error_message or 'The model is overloaded' in error_message:

#                 if attempt < MAX_RETRIES - 1:
#                     # Calculate sleep time: initial * (2^attempt)
#                     sleep_time = INITIAL_SLEEP_SEC * (2 ** attempt)
#                     print(f"Gemini model overloaded (503). Attempt {attempt + 1}/{MAX_RETRIES}. Retrying in {sleep_time} seconds...")
#                     time.sleep(sleep_time)
#                 else:
#                     # Final attempt failed
#                     print(f"Gemini model overloaded. Maximum retries ({MAX_RETRIES}) exceeded.")
#                     print(f"Final error: {e}")
#                     return None
#             else:
#                 # Handle all other unrecoverable errors (e.g., 400 Bad Request/Invalid Key)
#                 print(f"Unrecoverable error during analysis with Gemini: {e}")
#                 return None

#     return None

def analyze_and_structure_wod(raw_wod_text: str) -> list or None:
    """
    Analyzes the raw workout text using the Gemini API.

    It extracts workout sections with their original titles and content,
    and implements an Exponential Backoff retry mechanism for 503 (overload) errors.

    :param raw_wod_text: The raw, scraped text of the WOD.
    :return: A list of dicts [{"Title": ..., "Content": ...}, ...], or None on final failure.
    """
    # Retrieve API Key from environment variables
    #GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY is missing. Cannot analyze content.")
        return None

    # Initialize Gemini Client
    client = genai.Client(api_key=GEMINI_API_KEY)

    # PROMPT: Instruct the LLM to extract dynamic sections and return a List of JSON Objects
    prompt = f"""
    You are an assistant for analyzing a Daily Workout (WOD) from a blog.

    The raw text of the workout is:
    ---
    {raw_wod_text}
    ---

    Please extract the workout sections. Do not assume fixed categories.
    For each section found (e.g., Strength, Metcon, Endurance, Skill, Warmup, etc.),
    you must extract its exact title and its content. Preserve the single line breaks
    within the content, as each line represents a separate exercise or instruction.

    Return the data in JSON format ONLY, structured as a list of objects:
    [
      {{"Title": "Original Section Name 1", "Content": "Section content 1"}},
      {{"Title": "Original Section Name 2", "Content": "Section content 2"}},
      ...
    ]

    - Ensure the 'Title' field uses the exact wording found in the raw text (e.g., 'Strength:', 'Skill').
    - The 'Content' field must contain the complete description of that workout section.
    """

    # Loop for Retries (Exponential Backoff)
    for attempt in range(MAX_RETRIES):
        try:
            # Attempt to execute the API call
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )

            # If successful, return the result and exit
            return json.loads(response.text)

        except Exception as e:
            error_message = str(e)

            # 1. Check for recoverable overload error (503 UNAVAILABLE)
            if '503 UNAVAILABLE' in error_message or 'The model is overloaded' in error_message:

                if attempt < MAX_RETRIES - 1:
                    # Calculate sleep time: initial * (2^attempt)
                    sleep_time = INITIAL_SLEEP_SEC * (2 ** attempt)
                    print(f"Gemini model overloaded (503). Attempt {attempt + 1}/{MAX_RETRIES}. Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                else:
                    # Final attempt failed
                    print(f"Gemini model overloaded. Maximum retries ({MAX_RETRIES}) exceeded.")
                    print(f"Final error: {e}")
                    return None

            # 2. Handle all other unrecoverable errors (e.g., 400 Bad Request / Invalid Key)
            else:
                print(f"Unrecoverable error during analysis with Gemini: {e}")
                return None

    return None # Should not be reached if logic is followed, but included for safety.

# def format_telegram_message(parsed_wod: list) -> str:

# def format_telegram_message(parsed_wod: list) -> str: #markdown version
#     """
#     Formats the workout data into a readable and visually appealing message
#     using Markdown and emojis, based on dynamic section titles.
#     (Updated to preserve all single line breaks within content for better readability).
#     """
#     EMOJIS = {
#         "strength": "🏋️",
#         "weightlifting": "🏋️‍♂️",
#         "metcon": "⏱️",
#         "endurance": "🏃‍♂️",
#         "wod": "🔥",
#         "skill": "🎯",
#         "warmup": "🤸",
#         "cooldown": "🧘",
#     }

#     # Attractive main header
#     message = "💥 **W.O.D. The Daily Workout has Arrived!** 💥\n"
#     message += "🗓️ Have a great and powerful training day!\n\n"
#     message += "---" * 10 + "\n\n"

#     for section in parsed_wod:
#         title = section.get("Title", "Untitled Section").strip()
#         content = section.get("Content", "").strip()

#         if content:
#             # 1. Determine emoji based on lowercased keywords
#             title_lower = title.lower().replace('.', '').replace(':', '')
#             emoji = "🔥" # Default emoji
#             for key, emo in EMOJIS.items():
#                 if key in title_lower:
#                     emoji = emo
#                     break

#             # 2. Cleaning and formatting content:
#             # We now rely on the LLM to provide the content with single newlines
#             # between items, as it saw them on the original web page.
#             # We only remove excess triple/quadruple newlines, keeping single/double.

#             # This ensures that every distinct line/exercise (separated by \n) stays on its own line.
#             clean_content = content.replace('\n\n\n', '\n\n')

#             # 3. Creating the section title: Section title is followed by TWO newlines (one empty line)
#             message += f"{emoji} **{title}:**\n\n"

#             # 4. Adding the content. The content itself contains the required single newlines.
#             # We add a trailing newline pair to ensure separation from the next section title.
#             message += f"{clean_content}\n\n"

#     message += "\n" + "---" * 10
#     message += "\n\n**Enjoy the workout!** 🐼"

#     return message

# # def send_telegram_message(message):
#     """Send a message to the Telegram channel."""
#     url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
#     payload = {
#         'chat_id': TELEGRAM_CHAT_ID,
#         'text': message,
#         'parse_mode': 'Markdown'  # To format the message with bold, italic, etc.
#     }
#     try:
#         response = requests.post(url, data=payload)
#         response.raise_for_status()
#         logging.info("Message sent successfully.")
#     except requests.RequestException as e:
#         logging.error(f"Failed to send message to Telegram: {e}")

def format_telegram_message(parsed_wod: list) -> str: #html version
    """
    Formats the workout data into a readable message using HTML tags.
    This replaces Markdown to avoid parsing errors (HTTP 400) caused by special characters.
    """
    todays_date_str = datetime.datetime.now().strftime("%A-%d/%m/%y")
    # Mapping keywords to relevant emojis for section titles
    EMOJIS = {
        "strength": "🏋️",
        "weightlifting": "🏋️‍♂️",
        "metcon": "⏱️",
        "endurance": "🏃‍♂️",
        "wod": "🔥",
        "skill": "🎯",
        "warmup": "🤸",
        "cooldown": "🧘",
    }

    # Header of the message using HTML <b> tags
    message = "💥 <b>W.O.D. The Daily Workout has Arrived!</b> 💥\n"
    message += "🗓️ Have a great and powerful training day!\n\n"
    message += f"📅 Date: {todays_date_str}\n\n"
    message += "----------------------------------------\n\n"

    for section in parsed_wod:
        title = section.get("Title", "Untitled Section").strip()
        content = section.get("Content", "").strip()

        if content:
            # 1. Determine the appropriate emoji for the title
            title_lower = title.lower().replace('.', '').replace(':', '')
            emoji = "🔥"  # Default emoji if no keyword matches
            for key, emo in EMOJIS.items():
                if key in title_lower:
                    emoji = emo
                    break

            # 2. Clean content to remove excessive empty lines
            # Preserves single and double newlines for exercise separation
            clean_content = content.replace('\n\n\n', '\n\n')

            # 3. Format the section: Emoji + Bold Title + 2 newlines
            message += f"{emoji} <b>{title}:</b>\n\n"

            # 4. Add the workout content + 2 newlines to separate from next section
            message += f"{clean_content}\n\n"

    # Footer and closing signature
    message += "----------------------------------------\n\n"
    message += "<b>Enjoy the workout!</b> 🐼"

    return message

def send_telegram_message(message: str): #Markdown version
    """
    Sends the formatted message to Telegram using the simple and reliable 'requests' library,
    which is confirmed to work with the user's setup.
    """
    # Use the variables as defined in the rest of the script (loaded from os.getenv)
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing. Cannot send message.")
        return

    # Telegram API endpoint for sending messages
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        'chat_id': TELEGRAM_CHAT_ID, # This can be the numerical ID or the @username
        'text': message,
        'parse_mode': 'HTML'     # Use HTML for formatting (bold, emojis, newlines)
    }

    print(f"DEBUG: Attempting to send message to Chat ID: {TELEGRAM_CHAT_ID}")

    try:
        # Send the POST request
        response = requests.post(url, data=payload)
        response.raise_for_status() # Raise an exception for HTTP error codes (4xx or 5xx)

        # Check Telegram's internal response for success/failure
        if response.json().get('ok'):
            print("WOD message sent successfully to Telegram!")
        else:
            # Handle non-HTTP errors reported by the Telegram API (e.g., invalid chat ID)
            print(f"Telegram reported success (HTTP 200) but failed to deliver: {response.json().get('description', 'Unknown API Error')}")

    except requests.RequestException as e:
        # Handle network or HTTP errors
        print(f"CRITICAL ERROR: Failed to send message via requests: {e}")
    except Exception as e:
        # Catch any other unexpected errors
        print(f"An unexpected error occurred during Telegram sending: {e}")

def main():
    # Get the current date
    today = datetime.datetime.now()

    # Format the date as "day-ddmmyy"
    formatted_date = today.strftime("%A-%d%m%y").lower()
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    logging.info(f"Fetching WOD for date: {formatted_date}")
    url = f'https://wods.crossfitpanda.com/{formatted_date}/'  # Replace with your target URL
    logging.info(f"Fetching URL: {url}")

    url = resolve_wod_url(url)
    if not url:
        logging.error("Failed to resolve a valid WOD URL.")
        return
    wod_text = fetch_latest_wod(url)
    if not wod_text:
        return

    print("Analyzing WOD content using Gemini...")
    # print(f"DEBUG: GEMINI_API_KEY status: {'Key Loaded' if os.getenv('GEMINI_API_KEY') else 'Key Missing'}")
    # print(f"DEBUG: Key being used starts with: {GEMINI_API_KEY[:4]} and ends with: {GEMINI_API_KEY[-4:]}")
    message = analyze_and_structure_wod(wod_text)
    logging.info(f"Formatted message:\n{message}")
    if not message:
        return

    print("Formatting the message for sending...")
    telegram_message = format_telegram_message(message)
    # print('-----------------------------------------------------------\n')
    # print(message + '\n')
    # print('-----------------------------------------------------------\n')

    # Send the message to the Telegram channel
    print("Sending to Telegram...")
    send_telegram_message(telegram_message)
    print("Done.")


if __name__ == "__main__":
    try:
        main()
        logging.info("Script executed successfully.")
    except Exception as e:
        logging.critical(f"Unexpected error: {e}", exc_info=True)
