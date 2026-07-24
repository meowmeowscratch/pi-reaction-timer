"""
Pi Reaction Timer
=================
A reaction-time game: an LED lights up after a random delay, and
you press a button as fast as possible. Your time (in milliseconds)
gets posted to meow meow scratch with a persistent top-10 leaderboard.

Wiring:
  LED   -> 220-ohm resistor -> GPIO24 (pin 18), cathode to GND (pin 20)
  Button -> GPIO25 (pin 22) and GND (pin 20)

Setup:
  pip install -r requirements.txt
  export MEOW_API_KEY="your-key"
  export PLAYER_NAME="your-name"
  python reaction_timer.py
"""

# os: lets us read environment variables (like your API key) from the system
import os
# sys: lets us exit the program with an error code if something is wrong
import sys
# time: provides time.sleep() for pauses and time.perf_counter() for
#   precise timing. perf_counter is a high-resolution monotonic clock --
#   it only counts forward and is not affected by system clock changes.
import time
# random: generates the random delay before the LED turns on, so you
#   cannot predict exactly when it will light up
import random
# datetime, timezone: lets us get the current time in UTC and format it
#   as a standard ISO 8601 string that APIs understand
from datetime import datetime, timezone
# RPi.GPIO: the library that lets Python talk to the Raspberry Pi's
#   physical GPIO pins -- controlling the LED and reading the button
import RPi.GPIO as GPIO
# meow_sdk: the official library for the meow meow scratch API.
#   Meow is the main client class; MeowError is raised when API calls fail.
from meow_sdk import Meow, MeowError, AuthError

# --- Configuration -----------------------------------------------------------

# Read the API key from an environment variable. We keep it out of the code
# so you don't accidentally share your secret key if you share this file.
API_KEY = os.environ.get("MEOW_API_KEY")
if not API_KEY:
    print("Set MEOW_API_KEY environment variable")
    sys.exit(1)

# Each player needs a name so the leaderboard can track who got which score.
# Using an environment variable means multiple people can take turns on the
# same Pi just by changing this value.
PLAYER_NAME = os.environ.get("PLAYER_NAME")
if not PLAYER_NAME:
    print("Set PLAYER_NAME environment variable (e.g. export PLAYER_NAME=\"alice\")")
    sys.exit(1)

# These must match exactly what you set up on meow meow scratch:
APP = "pi-reaction-timer"
ENDPOINT_REACTION = "reaction"      # stores this player's latest stats
ENDPOINT_LEADERBOARD = "leaderboard"  # stores the top-10 all-time scores

# GPIO pin assignments (BCM numbering)
LED_PIN = 24      # GPIO24 (physical pin 18) -- output to the LED
BUTTON_PIN = 25   # GPIO25 (physical pin 22) -- input from the push button

# Game timing constants
MIN_DELAY = 2.0   # minimum seconds before LED turns on
MAX_DELAY = 6.0   # maximum seconds before LED turns on
TIMEOUT = 10.0    # seconds to wait for a button press before giving up

# --- GPIO setup --------------------------------------------------------------

# BCM mode means we refer to pins by their Broadcom chip number (GPIO24),
# not physical board position (pin 18). BCM is the standard convention.
GPIO.setmode(GPIO.BCM)

# Set LED pin as output. initial=GPIO.LOW starts with the LED off.
GPIO.setup(LED_PIN, GPIO.OUT, initial=GPIO.LOW)

# Set button pin as input with the internal pull-up resistor enabled.
# The pull-up gently connects the pin to 3.3V, so it reads HIGH when
# nothing is pressing the button. When you press the button, it connects
# the pin to GND, pulling it LOW. Without the pull-up, the pin would
# float and give random readings.
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# --- Helper functions --------------------------------------------------------


def led_on():
    """Turn the LED on by setting the GPIO pin HIGH (3.3V)."""
    GPIO.output(LED_PIN, GPIO.HIGH)


def led_off():
    """Turn the LED off by setting the GPIO pin LOW (0V)."""
    GPIO.output(LED_PIN, GPIO.LOW)


def is_button_pressed():
    """Check if the button is currently being pressed.

    Because of the pull-up resistor, the pin reads HIGH normally.
    Pressing the button connects it to GND, so it reads LOW.
    LOW == pressed, HIGH == not pressed.
    """
    return GPIO.input(BUTTON_PIN) == GPIO.LOW


def wait_for_press(timeout):
    """Wait for a button press, polling every 1ms.

    Returns the elapsed time in seconds, or None if the timeout expires.

    We poll every 1ms (0.001s). This adds at most 1ms of error to the
    measurement -- negligible compared to human reaction times (150-400ms).
    Using perf_counter ensures we measure real elapsed time, not just
    loop iterations.
    """
    start = time.perf_counter()
    while True:
        if is_button_pressed():
            return time.perf_counter() - start
        if time.perf_counter() - start >= timeout:
            return None
        time.sleep(0.001)  # 1ms polling interval


# --- API helper functions ----------------------------------------------------


def post_result(api, player, time_ms, best_ms, games_played):
    """Post this player's latest stats to the reaction endpoint."""
    now = datetime.now(timezone.utc).isoformat()
    data = {
        "player": player,
        "last_ms": time_ms,
        "best_ms": best_ms,
        "games_played": games_played,
        "updated_at": now,
    }
    try:
        # set_payload overwrites the stored data at this endpoint.
        # Anyone checking it always sees the player's CURRENT stats.
        api.set_payload(APP, ENDPOINT_REACTION, data)
    except AuthError as e:
        # Without a working key nothing can be saved, so there's no point
        # letting the game continue pretending scores are being recorded.
        print(f"  API key rejected: {e}")
        if e.hint:
            print(f"  Hint: {e.hint}")
        sys.exit(1)
    except MeowError as e:
        print(f"  Could not post result: {e}")
        # .hint is a plain-English fix from the API, when it has one.
        if e.hint:
            print(f"  Hint: {e.hint}")


def fetch_leaderboard(api):
    """Fetch the existing leaderboard from meow meow scratch.

    Returns the list of scores, or an empty list if the endpoint
    has no data yet or the request fails.
    """
    try:
        data = api.get(APP, ENDPOINT_LEADERBOARD)
        # The leaderboard is stored as {"scores": [...]}.
        # If it's a fresh endpoint with no data, we get an empty dict
        # or a dict without "scores", so default to an empty list.
        return data.get("scores", [])
    except MeowError:
        # First run or network issue -- start with an empty leaderboard
        return []


def update_leaderboard(api, scores, player, time_ms):
    """Add a score to the leaderboard if it qualifies for the top 10.

    The leaderboard stores the 10 fastest reaction times ever recorded.
    Lower times are better (faster reaction = smaller number).
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    entry = {"player": player, "time_ms": time_ms, "date": now}

    # Add the new score to the list
    scores.append(entry)

    # Sort by time_ms so the fastest (smallest number) comes first
    scores.sort(key=lambda s: s["time_ms"])

    # Keep only the top 10
    scores = scores[:10]

    try:
        api.set_payload(APP, ENDPOINT_LEADERBOARD, {"scores": scores})
    except MeowError as e:
        print(f"  Could not update leaderboard: {e}")
        # .hint is a plain-English fix from the API, when it has one.
        if e.hint:
            print(f"  Hint: {e.hint}")

    return scores


# --- Game round --------------------------------------------------------------


def play_round():
    """Play one round of the reaction game.

    Returns the reaction time in milliseconds, or None if the player
    pressed too early (false start) or did not press in time (timeout).
    """
    print("\n--- Get ready... ---")
    led_off()

    # Wait a random amount of time between MIN_DELAY and MAX_DELAY seconds.
    # The random delay prevents the player from guessing when the LED will
    # light up and pressing early based on timing alone.
    delay = random.uniform(MIN_DELAY, MAX_DELAY)

    # During the wait, check every 10ms if the player pressed the button
    # before the LED turned on. That's a false start!
    wait_start = time.perf_counter()
    while time.perf_counter() - wait_start < delay:
        if is_button_pressed():
            print("  FALSE START! You pressed before the light came on.")
            print("  Wait for the LED to light up, then press.")
            # Brief pause so the message is readable before the next round
            time.sleep(2)
            return None
        time.sleep(0.01)  # 10ms polling -- fast enough to catch cheaters

    # --- GO! ---
    led_on()
    print("  >>> GO! Press the button! <<<")

    # Start the precision timer and wait for a press
    elapsed = wait_for_press(TIMEOUT)
    led_off()

    if elapsed is None:
        print(f"  Too slow! You didn't press within {TIMEOUT:.0f} seconds.")
        return None

    # Convert seconds to milliseconds for a more intuitive display.
    # Humans think in milliseconds for reaction times (e.g. "230 ms"),
    # not fractions of a second (e.g. "0.23 s").
    time_ms = round(elapsed * 1000)
    print(f"  Your reaction time: {time_ms} ms")

    return time_ms


# --- Main loop ---------------------------------------------------------------


def main():
    # Create the API client we'll use to send data to meow meow scratch
    api = Meow(api_key=API_KEY)

    print(f"=== Reaction Timer ===")
    print(f"Player: {PLAYER_NAME}")
    print(f"Press Ctrl+C to quit\n")

    # Fetch any existing leaderboard so scores survive across restarts.
    # If this is the first run, we start with an empty list.
    print("Loading leaderboard...")
    scores = fetch_leaderboard(api)
    if scores:
        print(f"  Loaded {len(scores)} score(s) from previous sessions")
    else:
        print("  No existing scores -- starting fresh")

    # Track session stats
    games_played = 0
    best_ms = None

    try:
        while True:
            time_ms = play_round()

            if time_ms is not None:
                games_played += 1

                # Update best time
                if best_ms is None or time_ms < best_ms:
                    best_ms = time_ms
                    print(f"  New personal best!")

                print(f"  Games: {games_played}  Best: {best_ms} ms")

                # Post this player's stats to the API
                post_result(api, PLAYER_NAME, time_ms, best_ms, games_played)

                # Check if this score makes the top 10
                # If the leaderboard has fewer than 10 entries, any score qualifies.
                # Otherwise, the score must beat the slowest time on the board.
                qualifies = (
                    len(scores) < 10
                    or time_ms < scores[-1]["time_ms"]
                )
                if qualifies:
                    scores = update_leaderboard(
                        api, scores, PLAYER_NAME, time_ms
                    )
                    rank = next(
                        i + 1 for i, s in enumerate(scores)
                        if s["time_ms"] == time_ms and s["player"] == PLAYER_NAME
                    )
                    print(f"  Leaderboard rank: #{rank} of {len(scores)}")

            # Pause between rounds so the player can read the results
            print("\nNext round in 3 seconds...")
            time.sleep(3)

    except KeyboardInterrupt:
        print("\n\nThanks for playing!")
        if games_played > 0:
            print(f"You played {games_played} round(s). Best time: {best_ms} ms")
    finally:
        # Always clean up GPIO on exit. This resets all pins to their
        # default state so they don't interfere with other programs.
        led_off()
        GPIO.cleanup()


if __name__ == "__main__":
    main()
