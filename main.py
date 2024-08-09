import os
import logging
import requests
from bs4 import BeautifulSoup
import datetime
import re

# Telegram Bot API token and Channel ID
TELEGRAM_API_TOKEN = os.getenv('TELEGRAM_API_TOKEN')
TELEGRAM_CHANNEL_ID = '@crossfitworkout'  # Replace with your channel name or chat ID


def fetch_wod_description(url):
    """Fetch the WOD description from the given URL and format the text."""
    try:
        logging.info(f"Attempting to fetch WOD description from {url}")
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses
    except requests.RequestException as e:
        logging.error(f"HTTP request failed: {e}")
        return "Error fetching WOD description."

    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the section tag containing the WOD
    section = soup.find('section', class_='gh-content gh-canvas is-body')
    if not section:
        logging.error("WOD section not found in the HTML.")
        return "WOD section not found."

    # Replace <br> tags with new lines
    logging.info("Replacing <br> tags with new lines.")
    for br in section.find_all('br'):
        br.replace_with('\n')

    # Get the text content
    wod_text = section.get_text(separator='\n').strip()
    logging.info(f"Fetched WOD text: {wod_text[:100]}...")  # Log a snippet of the text

    # Initialize the formatted text with the header
    formatted_text = "CrossFit WOD:\n\n"

    # Define the sections
    sections = ["Strength", "Metcon", "Endurance"]
    logging.info("Formatting the WOD text into sections.")

    # Format the text by sections
    for section in sections:
        if section in wod_text:
            logging.info(f"Processing section: {section}")
            # Find the start of this section
            start = wod_text.find(section)
            # Find where the next section begins, to capture only the current section's text
            end = min([wod_text.find(sec, start + 1) for sec in sections if wod_text.find(sec, start + 1) != -1],
                      default=len(wod_text))
            # Extract and clean the section's text
            part = wod_text[start:end].replace(section + ":", "").strip()
            formatted_text += f"{section}:\n{part}\n\n"
        else:
            logging.warning(f"Section '{section}' not found in the WOD text.")

    logging.info("Finished formatting the WOD text.")
    return formatted_text.strip()


# def format_message(wod_text):
#     """Format the WOD description into a Telegram-ready message."""
#     logging.info("Formatting the WOD text for Telegram.")
#     formatted_text = re.sub(r'\n\s*\n+', '\n\n', wod_text).strip()
#     return f"🏋️‍♂️ *Workout of the Day*\n\n{formatted_text}\n\n💪 _Stay strong and crush it!_"
def format_message(wod_text):
    """Format the WOD description into a Telegram-ready message with improved formatting."""
    logging.info("Formatting the WOD text for Telegram with improved formatting.")

    # Define emojis for each section
    section_emojis = {
        "Strength": "💪",
        "Metcon": "🏋️",
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


def send_telegram_message(message):
    """Send a message to the Telegram channel."""
    url = f"https://api.telegram.org/bot{TELEGRAM_API_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHANNEL_ID,
        'text': message,
        'parse_mode': 'Markdown'  # To format the message with bold, italic, etc.
    }
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        logging.info("Message sent successfully.")
    except requests.RequestException as e:
        logging.error(f"Failed to send message to Telegram: {e}")


def main():
    # Get the current date
    today = datetime.datetime.now()

    # Format the date as "day-ddmmyy"
    formatted_date = today.strftime("%A-%d%m%y").lower()

    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    logging.info(f"Fetching WOD for date: {formatted_date}")
    url = 'https://wods.crossfitpanda.com/' + formatted_date + '/'  # Replace with your target URL
    logging.info(f"Fetching URL: {url}")

    wod_text = fetch_wod_description(url)
    message = format_message(wod_text)
    logging.info(f"Formatted message:\n{message}")

    # Send the message to the Telegram channel
    send_telegram_message(message)


if __name__ == "__main__":
    try:
        main()
        logging.info("Script executed successfully.")
    except Exception as e:
        logging.critical(f"Unexpected error: {e}", exc_info=True)
