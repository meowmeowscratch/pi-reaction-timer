# Pi Reaction Timer

Test your reflexes and compete with friends! This project turns your Raspberry Pi into a reaction-time game -- an LED lights up after a random delay, you slam the button as fast as you can, and your time gets posted to the internet with a live top-10 leaderboard.

---

## What you'll learn

- **GPIO output (controlling an LED)** -- How to use the Raspberry Pi's GPIO pins to turn an LED on and off from Python code.
- **GPIO input with pull-up resistors** -- How to read a button press through a GPIO pin, and why we need an internal "pull-up resistor" to get clean, reliable readings.
- **Precise timing with `perf_counter`** -- Why `time.perf_counter()` is better than `time.time()` for measuring short intervals, and how it gives you sub-millisecond accuracy.
- **Random delays and false-start detection** -- How to use randomness to make a fair game, and how to catch players who press too early.
- **Online leaderboards** -- How to read and write data to an API so scores persist across sessions and multiple players can compete.

---

## What you'll need

### Hardware

- **Raspberry Pi** (any model with GPIO pins -- Pi 3, Pi 4, Pi 5, Pi Zero, etc.)
- **1 LED** (any color) -- a small light that turns on when electricity flows through it. It has two legs: the longer one is positive (anode) and the shorter one is negative (cathode).
- **1 resistor (220 ohms)** -- a tiny component that limits the current flowing through the LED so it doesn't burn out. 220 ohms is a safe value for most LEDs. Look for one with red-red-brown color bands.
- **1 push button (momentary)** -- a small button that only stays "on" while you're pressing it. The common 4-pin tactile buttons that come in most Pi kits work perfectly.
- **1 breadboard** -- a plastic board with holes for plugging in components. It lets you build circuits without soldering.
- **4 jumper wires** (male-to-female or male-to-male depending on your breadboard) -- simple wires for connecting everything together.

### Software

- **Python 3** -- the programming language that runs our script. It comes pre-installed on Raspberry Pi OS.
- **A meow meow scratch account** -- this is the free service where your scores and leaderboard get posted so you can check them from any device. Sign up at [meowmeowscratch.com](https://meowmeowscratch.com).

---

## Wiring diagram

```
    Raspberry Pi              Breadboard
    +-----------+
    |           |             LED (longer leg = +, shorter leg = -)
    | GPIO24 o--+--- wire --- [ 220Ω resistor ]---[ LED + ]
    | (pin 18)  |                                  [ LED - ]--- wire --- GND bus
    |           |
    | GPIO25 o--+--- wire --- [ button leg 1 ]
    | (pin 22)  |             [ button leg 2 ]--- wire --- GND bus
    |           |
    | GND    o--+--- wire --- GND bus on breadboard
    | (pin 20)  |
    +-----------+

    LED circuit:   GPIO24 → resistor → LED anode(+) → LED cathode(-) → GND
    Button circuit: GPIO25 → button → GND
```

### Pin reference table

| Component       | Component pin | Raspberry Pi pin   | What it does                                    |
|-----------------|---------------|--------------------|-------------------------------------------------|
| LED (anode +)   | Longer leg    | GPIO24 (pin 18)    | Pi sends power here to turn the LED on          |
| LED (cathode -) | Shorter leg   | GND (pin 20)       | Ground -- completes the LED circuit              |
| Button          | Leg 1         | GPIO25 (pin 22)    | Pi reads this pin to detect button presses      |
| Button          | Leg 2         | GND (pin 20)       | Ground -- when pressed, pulls GPIO25 to GND     |

> **Why the resistor?** LEDs are greedy -- they'll draw as much current as they can and burn themselves out. The 220-ohm resistor limits the current to a safe level (about 10-15 milliamps) so the LED glows without damage.

> **How does the button work?** The button has two legs that are normally disconnected. When you press it, they connect. We wire one leg to GPIO25 and the other to GND. With the internal pull-up resistor enabled, GPIO25 normally reads HIGH (3.3V). When you press the button, it connects to GND and reads LOW. So LOW = pressed, HIGH = not pressed.

---

## Step-by-step setup

### 1. Wire up the circuit

Follow the wiring diagram above. Plug the LED, resistor, and button into your breadboard, then connect them to the Pi with jumper wires. Double-check that:
- The LED's longer leg (positive) is on the resistor side, and the shorter leg (negative) goes to ground.
- The button has one leg on GPIO25 and one on the GND rail.

### 2. Install the required Python libraries

Open a terminal on your Pi and navigate to this project folder. Then run:

```bash
pip install -r requirements.txt
```

**What is pip?** `pip` is Python's package installer. It downloads and installs libraries (other people's code) that our script depends on. The `requirements.txt` file lists everything needed. In this case it installs:

- **RPi.GPIO** -- a library that lets Python talk to the Raspberry Pi's physical GPIO pins. Without it, Python would have no way to control the LED or read the button.
- **meow-sdk** -- the official Python library for the meow meow scratch API. It handles posting your scores to the internet.

### 3. Set up your API key

You need to tell the script your meow meow scratch credentials. In the terminal, run:

```bash
export MEOW_API_KEY="your-key-here"
```

Replace `your-key-here` with the actual API key from your meow meow scratch account.

**What does `export` do?** It creates an "environment variable" -- a piece of information stored in your terminal session that programs can read. This keeps your secret API key out of the code itself (so you don't accidentally share it).

> **Tip:** This environment variable goes away when you close the terminal. To make it permanent, add the `export` line to the end of your `~/.bashrc` file.

### 4. Set your player name

The leaderboard needs to know who you are! Pick a name and set it:

```bash
export PLAYER_NAME="alice"
```

Replace `alice` with whatever name you want on the leaderboard. If multiple people share the same Pi, each person just sets their own name before playing.

### 5. Set up your meow meow scratch app and endpoints

Before running the script, you need to create a place for the data to live on meow meow scratch:

1. **Log in** to your account at [meowmeowscratch.com](https://meowmeowscratch.com).
2. **Create an app** called `pi-reaction-timer` (the name must match exactly).
3. **Add a static endpoint** called `reaction` -- this stores the current player's latest stats.
4. **Add a second static endpoint** called `leaderboard` -- this stores the top-10 scores.
5. **Copy your API key** from the dashboard (if you haven't already).

### 6. Run it

```bash
python reaction_timer.py
```

You should see:

```
=== Reaction Timer ===
Player: alice
Press Ctrl+C to quit

Loading leaderboard...
  No existing scores -- starting fresh

--- Get ready... ---
  >>> GO! Press the button! <<<
  Your reaction time: 234 ms
  Games: 1  Best: 234 ms
  Leaderboard rank: #1 of 1

Next round in 3 seconds...
```

Press **Ctrl+C** at any time to stop.

---

## How to play

1. **Get ready.** The terminal says "Get ready..." and the LED is off.
2. **Wait.** After a random delay (2 to 6 seconds), the LED turns on and the terminal says "GO!"
3. **Press!** Hit the button as fast as you can.
4. **See your time.** The LED turns off and your reaction time is displayed in milliseconds.
5. **Check the leaderboard.** If your time is fast enough, it goes into the top 10!
6. **Repeat.** After 3 seconds, the next round starts automatically.
7. **Don't cheat!** If you press the button before the LED turns on, that's a false start and the round doesn't count.

---

## How the code works

Here is a plain-English walkthrough of what the script does.

### GPIO setup

```python
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
```

- `GPIO.BCM` means we refer to pins by their Broadcom chip numbers (like GPIO24) instead of physical board positions (like pin 18).
- The LED pin is set as an **output** (we send power TO the LED). `initial=GPIO.LOW` starts with it off.
- The button pin is set as an **input** (we read FROM the button). `PUD_UP` enables the internal pull-up resistor so the pin reads HIGH when the button is not pressed, and LOW when it is.

### Why `perf_counter` instead of `time.time`?

```python
start = time.perf_counter()
# ... player presses button ...
elapsed = time.perf_counter() - start
```

`time.perf_counter()` is a **monotonic clock** -- it only counts forward and is never adjusted by the operating system. `time.time()` can jump backwards or forwards if the system clock gets updated (for example, by an NTP sync). For measuring reaction times where every millisecond matters, `perf_counter` gives you reliable, precise measurements.

### False start detection

```python
while time.perf_counter() - wait_start < delay:
    if is_button_pressed():
        print("FALSE START!")
        return None
    time.sleep(0.01)  # check every 10ms
```

During the random wait before the LED turns on, the script checks the button every 10 milliseconds. If you press early, it catches you. The 10ms polling is fast enough that no human press could slip through undetected.

### Measuring reaction time

```python
led_on()
elapsed = wait_for_press(TIMEOUT)
led_off()
time_ms = round(elapsed * 1000)
```

The moment the LED turns on, a precision timer starts. The script polls the button every 1ms. When you press it, the elapsed time is calculated and converted to milliseconds. The 1ms polling adds at most 1ms of measurement error -- negligible when human reaction times are 150-400ms.

### The leaderboard

```python
scores = fetch_leaderboard(api)  # load existing scores on startup
# ... after each round ...
scores.append(new_entry)
scores.sort(key=lambda s: s["time_ms"])  # fastest first
scores = scores[:10]  # keep only top 10
api.set_payload(APP, ENDPOINT_LEADERBOARD, {"scores": scores})
```

The leaderboard is fetched from meow meow scratch when the script starts, so scores survive across restarts. After each round, if the new score qualifies (either the board has fewer than 10 entries, or the score beats the slowest one), it gets inserted, the list is re-sorted, and the top 10 are saved back.

### Cleanup

```python
finally:
    led_off()
    GPIO.cleanup()
```

When you press Ctrl+C, the `finally` block runs no matter what. It turns off the LED and resets all GPIO pins to their default state, preventing them from being stuck in unexpected states.

---

## Troubleshooting

### Button press not detected

- **Check the wiring.** Make sure one button leg goes to GPIO25 (physical pin 22) and the other to GND (physical pin 20).
- **Test the button.** Some 4-pin tactile buttons have two pairs of always-connected legs. Try rotating the button 90 degrees on the breadboard.
- **Loose connections.** Push the jumper wires firmly into the breadboard holes and the Pi's GPIO header.

### LED does not light up

- **Check the LED direction.** The longer leg (anode, positive) must be on the side connected to the resistor/GPIO24. The shorter leg (cathode, negative) must go to GND. LEDs only work in one direction.
- **Check the resistor.** Make sure the resistor is actually in the circuit between GPIO24 and the LED. Without it, the LED might not light up at all, or could burn out.
- **Test with a different LED.** It might be dead. LEDs are cheap and sometimes arrive broken.

### Every round is a false start

- **The button might be stuck.** Check that the button springs back up after pressing. A stuck button reads as always pressed.
- **Wiring issue.** If GPIO25 is accidentally shorted to GND (not through the button), it will always read as pressed. Check that the wires are only connected through the button.
- **Debounce.** Some cheap buttons can "bounce" (send rapid on-off signals). This script's polling should handle normal bounce, but a very noisy button might cause issues. Try a different button.

### Reaction times seem too high or inconsistent

- **Close other programs.** CPU-intensive programs running in the background can cause tiny delays. For the most accurate timing, close other applications.
- **Don't use SSH for serious competition.** If you're running the script over SSH, network lag adds to your apparent reaction time. Run it directly on the Pi with a monitor and keyboard for the fairest results.

### "No access to /dev/mem" or "Cannot determine SOC peripheral base address"

- This script must run on a real Raspberry Pi -- it cannot run on a regular laptop or desktop computer because those machines don't have GPIO pins.
- On the Pi, you may need to run with `sudo`: `sudo python reaction_timer.py`

### "Set MEOW_API_KEY environment variable" or "Set PLAYER_NAME environment variable"

- You forgot to set one or both environment variables before running the script. Run these first (in the same terminal window):

```bash
export MEOW_API_KEY="your-key"
export PLAYER_NAME="alice"
```

### Scores don't appear on meow meow scratch

- Double-check that your app is named exactly `pi-reaction-timer` and your endpoints are named exactly `reaction` and `leaderboard` on the meow meow scratch dashboard.
- Make sure your API key is correct and has not expired.
- Check your Pi's internet connection: `ping google.com`

---

## API setup

Before running the script, set up two static endpoints on meow meow scratch:

1. **Log in** to your account at [meowmeowscratch.com](https://meowmeowscratch.com).
2. **Create an app** called `pi-reaction-timer` (the name must match exactly).
3. **Add a static endpoint** called `reaction`.
4. **Add a static endpoint** called `leaderboard`.
5. **Copy your API key** from the dashboard.

### `reaction` endpoint payload

Once the script is running, the `reaction` endpoint will contain:

```json
{
  "player": "alice",
  "last_ms": 234,
  "best_ms": 198,
  "games_played": 5,
  "updated_at": "2026-02-26T14:23:07+00:00"
}
```

| Field          | Description                                          |
|----------------|------------------------------------------------------|
| `player`       | The player's name (from the `PLAYER_NAME` variable)  |
| `last_ms`      | Reaction time from the most recent round (ms)        |
| `best_ms`      | Best reaction time this session (ms)                 |
| `games_played` | Number of completed rounds this session              |
| `updated_at`   | When the last round was played (UTC timestamp)       |

### `leaderboard` endpoint payload

The `leaderboard` endpoint stores the top 10 fastest reaction times ever recorded:

```json
{
  "scores": [
    {"player": "alice", "time_ms": 198, "date": "2026-02-26 14:20"},
    {"player": "bob", "time_ms": 215, "date": "2026-02-26 14:35"},
    {"player": "alice", "time_ms": 234, "date": "2026-02-26 14:23"}
  ]
}
```

| Field     | Description                                       |
|-----------|---------------------------------------------------|
| `player`  | Who achieved this time                            |
| `time_ms` | The reaction time in milliseconds                 |
| `date`    | When the score was recorded (UTC, human-readable) |

Scores are sorted fastest-first. The same player can appear multiple times. Only the top 10 are kept.
