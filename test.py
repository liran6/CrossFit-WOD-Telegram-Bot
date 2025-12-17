import pytest
import json
import os
from unittest.mock import patch, MagicMock
# Import all relevant functions from the main script
from main import (
    analyze_and_structure_wod,
    format_telegram_message,
    fetch_latest_wod,
    main
)

# --- Mock Data ---

# Mock raw data simulating a complex WOD (including mixed case and potential errors)
MOCK_RAW_TEXT_COMPLEX = """
W.O.D. - Morning Session ☀️
Skill:
10 Minutes to warm up Handstand Walk. Focus on position.

Strength:
Deadlift
E03:00MOMx5 Sets:
5 Deadlifts @ 70%

Metcon:
14:00 Min AMRAP:
400m Run (or 800m Bike)
15 Wallball Shottz #20/14
30 KB Swings #53/35

Cool Down:
3 Minutes Pgeon Pose per side.
"""

# Expected structured output from the LLM for the complex WOD (dynamic titles)
MOCK_GEMINI_OUTPUT_COMPLEX = [
    {"Title": "Skill:", "Content": "10 Minutes to warm up Handstand Walk. Focus on position."},
    {"Title": "Strength:", "Content": "Deadlift\nE03:00MOMx5 Sets:\n5 Deadlifts @ 70%"},
    {"Title": "Metcon:", "Content": "14:00 Min AMRAP:\n400m Run (or 800m Bike)\n15 Wallball Shottz #20/14\n30 KB Swings #53/35"},
    {"Title": "Cool Down:", "Content": "3 Minutes Pgeon Pose per side."}
]

# --- Unit Tests (Isolated Logic) ---

@patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"})
@patch('daily_wod_sender.client.models.generate_content')
def test_analyze_and_structure_wod_dynamic_titles(mock_gemini_call):
    """
    Test the LLM agent parsing function using the dynamic title structure.
    We mock the Gemini API call to return a known list of objects.
    """
    # Configure the mock to return the complex expected JSON (as a list)
    mock_response = MagicMock()
    mock_response.text = json.dumps(MOCK_GEMINI_OUTPUT_COMPLEX)
    mock_gemini_call.return_value = mock_response

    # Execute the function
    result = analyze_and_structure_wod(MOCK_RAW_TEXT_COMPLEX)

    # Assert the result matches the expected structured data (a list of dicts)
    assert isinstance(result, list)
    assert len(result) == 4
    assert result[2]['Title'] == 'Metcon:'
    assert 'Wallball Shottz' in result[2]['Content'] # Check for typo tolerance in content
    mock_gemini_call.assert_called_once()


def test_format_telegram_message_dynamic():
    """
    Test the message formatting function, ensuring correct Markdown, emojis,
    and proper handling of dynamic titles (Skill, Cool Down).
    """
    formatted_message = format_telegram_message(MOCK_GEMINI_OUTPUT_COMPLEX)

    # Check for core formatting and content presence
    assert "💥 **W.O.D. The Daily Workout has Arrived!** 💥" in formatted_message

    # Check that dynamic titles are present and correctly formatted with relevant emojis
    assert "🎯 **Skill:**" in formatted_message # Uses '🎯' from the EMOJIS map
    assert "🏋️ **Strength:**" in formatted_message # Uses '🏋️' from the EMOJIS map
    assert "🧘 **Cool Down:**" in formatted_message # Uses '🧘' from the EMOJIS map

    # Check for content indentation (4 spaces after newline)
    assert "Focus on position.\n    \n    Deadlift\n" not in formatted_message
    assert "Focus on position.\n    \n\n🏋️ **Strength:**" not in formatted_message # Check for proper spacing

    # Verify content itself is present and indented
    assert "    10 Minutes to warm up Handstand Walk." in formatted_message


# --- Integration Test (End-to-End Simulation) ---

@patch.dict(os.environ, {
    "GEMINI_API_KEY": "dummy_key",  # Must be present, but we mock the call
    "TELEGRAM_BOT_TOKEN": "dummy_token",
    "TELEGRAM_CHAT_ID": "12345"
})
@patch('daily_wod_sender.send_telegram_message') # Mock the Telegram function
@patch('daily_wod_sender.analyze_and_structure_wod') # Mock the LLM analysis
@patch('daily_wod_sender.fetch_latest_wod') # Mock the web scraping
def test_main_simulation(mock_fetch, mock_analyze, mock_send_telegram):
    """
    Simulates a full run of the main script, mocking all external calls
    (web scraping, LLM analysis, and Telegram sending).
    """
    # 1. Configure Mocks: Define what each external call should return
    mock_fetch.return_value = MOCK_RAW_TEXT_COMPLEX
    mock_analyze.return_value = MOCK_GEMINI_OUTPUT_COMPLEX

    # 2. Execute the main function
    main()

    # 3. Assertions (verify the flow)
    mock_fetch.assert_called_once()
    mock_analyze.assert_called_once_with(MOCK_RAW_TEXT_COMPLEX)

    # Verify the Telegram sender was called exactly once with a string argument
    mock_send_telegram.assert_called_once()

    # Optional: Verify the message content sent to Telegram starts correctly
    sent_message = mock_send_telegram.call_args[0][0]
    assert "💥 **W.O.D. The Daily Workout has Arrived!** 💥" in sent_message
    assert "🏋️ **Strength:**" in sent_message


@patch('daily_wod_sender.send_telegram_message')
@patch.dict(os.environ, {
    "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"), # Use the REAL key from environment
    "TELEGRAM_BOT_TOKEN": "dummy_token",
    "TELEGRAM_CHAT_ID": "12345"
})
def test_full_live_fetch_and_analysis(mock_send_telegram, capsys):
    """
    FINAL INTEGRATION CHECK: Performs a live fetch and live LLM analysis
    using the actual website and the REAL Gemini API key.
    Telegram sending is still mocked.
    """
    # The 'main' function will now execute fetch_latest_wod (LIVE)
    # and analyze_and_structure_wod (LIVE)

    # NOTE: This test requires a valid GEMINI_API_KEY to be set in your environment
    if not os.getenv("GEMINI_API_KEY"):
        pytest.skip("Skipping live integration test: GEMINI_API_KEY environment variable is not set.")
        return

    # Execute the main function
    main()

    # Assertions
    # 1. Verify Telegram sending was skipped (mocked)
    mock_send_telegram.assert_called_once()

    # 2. Capture the script output (stdout)
    captured = capsys.readouterr()

    # The final formatted message is printed just before 'Sending to Telegram...'
    # We look for successful signs in the output.
    assert "Fetching WOD from:" in captured.out
    assert "Analyzing WOD content using Gemini..." in captured.out

    # The code prints the final message before calling the mocked send function.
    # We check the logs for the formatted message content:
    assert "Daily Workout has Arrived!" in captured.out
    assert "**Strength:**" in captured.out
    assert "**Metcon:**" in captured.out

    print("\n--- Final Generated Message (Printed for Inspection) ---")
    # Due to the complexity of parsing the output stream,
    # we rely on the main function logging its progress.
    # If the test passed, it means fetch, analysis, and formatting completed successfully.
    # Check your terminal output for the final formatted message.