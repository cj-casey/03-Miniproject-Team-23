# conductor.py
# To be run on a student's computer (not the Pico)
# Requires the 'requests' library: pip install requests

import requests
import time

# --- Configuration ---
# Students should populate this list with the IP address(es of their Picos
PICO_IPS = [
    "192.168.1.101",
]

# --- Music Definition ---
# Notes mapped to frequencies (in Hz)
C4 = 262
D4 = 294
E4 = 330
F4 = 349
G4 = 392
A4 = 440
B4 = 494
C5 = 523

# A simple melody: "Twinkle, Twinkle, Little Star"
# Format: (note_frequency, duration_in_ms)
SONG = [
    (C4, 400),
    (C4, 400),
    (G4, 400),
    (G4, 400),
    (A4, 400),
    (A4, 400),
    (G4, 800),
    (F4, 400),
    (F4, 400),
    (E4, 400),
    (E4, 400),
    (D4, 400),
    (D4, 400),
    (C4, 800),
]

# what modes from CLI interface are able to work
VALID_MODES = [
    "l",
    "r",
    "L",
    "R",
    "Record & Play",
    "Live Play"
    ]
# whats the max range
VALID_RANGE = 1000

# --- Conductor Logic ---


def play_note_on_all_picos(freq, ms):
    """Sends a /tone POST request to every Pico in the list."""
    print(f"Playing note: {freq}Hz for {ms}ms on all devices.")

    payload = {"freq": freq, "ms": ms, "duty": 0.5}

    for ip in PICO_IPS:
        url = f"http://{ip}/tone"
        try:
            # We use a short timeout because we don't need to wait for a response
            # This makes the orchestra play more in sync.
            requests.post(url, json=payload, timeout=0.1)
        except requests.exceptions.Timeout:
            # This is expected, we can ignore it
            pass
        except requests.exceptions.RequestException as e:
            print(f"Error contacting {ip}: {e}")
            
# -- additional api calls
def play_note_on_specific_picos(freq, ms, listed_ips):
    """Sends a /tone POST request to every Pico in the list."""
    print(f"Playing note: {freq}Hz for {ms}ms on all devices.")

    payload = {"freq": freq, "ms": ms, "duty": 0.5}

    for ip in listed_ips:
        url = f"http://{ip}/tone"
        try:
            # We use a short timeout because we don't need to wait for a response
            # This makes the orchestra play more in sync.
            requests.post(url, json=payload, timeout=0.1)
        except requests.exceptions.Timeout:
            # This is expected, we can ignore it
            pass
        except requests.exceptions.RequestException as e:
            print(f"Error contacting {ip}: {e}")

def play_melody_on_all_picos(song, note_gap):
    # POST /melody API Call
    # takes a song, list of note structs, and a note_gap
    #plays melody on all connected PICOS
    for note, duration in song:
            play_note_on_all_picos(note, duration)
            # Wait for the note's duration plus a small gap before playing the next one
            time.sleep(note_gap / 1000)
            
def play_melody_on_specifc_picos(song, note_gap, listed_ips):
    # POST /melody API Call
    # takes a song, list of note structs, and a note_gap
    #plays melody on all connected PICOS
    for note, duration in song:
            play_note_on_specific_picos(note, duration, listed_ips)
            # Wait for the note's duration plus a small gap before playing the next one
            time.sleep(note_gap / 1000)
            
def get_pico_health(ip):
    # GET /health API Call
    # returns struct with fields "status", "device_id","api"
    print(f"Obtaining health of PICO with ip:{ip}")
    url = f"http://{ip}/health"
    try:
        resp = requests.get(url, timeout=0.5)
        device_health = resp.json()
    except requests.exceptions.Timeout as e:
        print(f"Timeout reaching {ip}:{e}")
        return
    except requests.exceptions.RequestException as e:
        print(f"Error contacting {ip}: {e}")
        return
    print(f'Status: {device_health["status"]}, Device ID: {device_health["device_id"]}, API: {device_health["api"]}')
    return device_health
        
def get_sensor_data(ip):
    # GET /sensor API Call
    # returns struct with fields "raw", "norm", "lux_est"
    # for future chromatic sensor, expect sensor_data to be a vector structured as:
    # [red level, green level, blue level, luminance]
    
    print(f"Obtaining data of PICO sensor with ip:{ip}")
    url = f"http://{ip}/sensor"
    try:
        resp = requests.get(url,timeout=0.5)
        sensor_data = resp.json()   
    except requests.exceptions.Timeout as e:
        print(f"Timeout reaching {ip}:{e}")
        return
    except requests.exceptions.RequestException as e:
        print(f"Error contacting {ip}: {e}")
        return
    print(f'Raw: {sensor_data["raw"]}, Norm: {sensor_data["norm"]}, Estimated Lux: {sensor_data["lux_est"]}')        
    return sensor_data

def get_device_mode(ip):
    # GET /mode API Call
    # returns mode, either "Live Play" or "Record & Play"
    
    print(f"Obtaining mode of PICO sensor with ip:{ip}")
    url = f"http://{ip}/get_mode"
    try:
        resp = requests.get(url,timeout=0.5)
        mode = resp.json()
    except requests.exceptions.Timeout as e:
        print(f"Timeout reaching {ip}:{e}")
        return
    except requests.exceptions.RequestException as e:
        print(f"Error contacting {ip}: {e}")
        return
    print(f"Mode: {mode}")
    return mode

def post_device_mode(ip, mode):
    #POST /mode API Call
    # sends mode to be to PICO, valid modes are:
    # Live Play: can pass "l", "L", "Live Play"
    # Record & Play: can pass "r","R", "Record & Play"
    payload = {"mode": mode}
    if mode in VALID_MODES:
        url = f"http://{ip}/post_mode"
        try:
            requests.post(url, json=payload, timeout=0.5)
        except requests.exceptions.Timeout as e:
            print(f"Timeout reaching {ip}:{e}")
            return
        except requests.exceptions.RequestException as e:
            print(f"Error contacting {ip}: {e}")
            return
    else:
        print(f"Error: Invalid mode entered. Valid modes are: {VALID_MODES}")
        
def get_sensor_range(ip):
    # GET /get_range
    print(f"Obtaining data of PICO sensor with ip:{ip}")
    url = f"http://{ip}/get_range"
    try:
        resp = requests.get(url,timeout=0.5)
        range_value = resp.json()
    except requests.exceptions.Timeout as e:
        print(f"Timeout reaching {ip}:{e}")
        return
    except requests.exceptions.RequestException as e:
        print(f"Error contacting {ip}: {e}")
        return
    print(f"Range: 0-{range}")
    return range_value

def post_device_range(ip, range_value):
    #POST /post_range API Call
    # sends value for range for PICO
    # anytime it detects light above or below +/- range, thats when we'll use it, so might need tweaking
    
    payload = {"range": range_value}
    if 0 <= range_value <= VALID_RANGE: 
        url = f"http://{ip}/post_range"
        try:
            requests.post(url, json=payload, timeout=0.5)
        except requests.exceptions.Timeout as e:
            print("Timeout reaching {ip}:{e}")
            return
        except requests.exceptions.RequestException as e:
            print(f"Error contacting {ip}: {e}")
            return
    else:
        print(f"Error: Invalid range entered. They must be in 0-X.")
        
def get_events(ip, sampling_rate):
    print(f"Streaming events from {ip} every {sampling_rate}ms. CTRL+C to stop.")
    try:
        while True:
            get_sensor_data(ip)
            time.sleep(sampling_rate / 1000)
    except KeyboardInterrupt:
        print("\nStopped event streaming.")

    
def get_melody(ip, sampling_rate):
    # GET /melody
    # assuming the device is playing anything, this will give a live update of the current notes
    # future expansion with library to handle playing the sounds in the conductor
    # reads at timesteps according to sampling rate
    #similar to get events but it hopefully will play sounds
    """Continuously simulate melody streaming from a Pico at a given interval (ms)."""
    print(f"Streaming melody from {ip} every {sampling_rate}ms. CTRL+C to stop.")
    try:
        while True:
            for note, duration in SONG:
                print(f"{ip} playing {note}Hz for {duration}ms")
                time.sleep(sampling_rate / 1000)
    except KeyboardInterrupt:
        print("\nStopped melody streaming.")

# CLI command handlers
def handle_play_note_specific(args):
    if len(args) != 3:
        print("Usage: play_note <device1,device2,...> <freq> <duration>")
        return
    device_list_str, freq_str, duration_str = args
    device_names = device_list_str.split(",")
    try:
        freq = int(freq_str)
        duration = int(duration_str)
    except ValueError:
        print("freq and duration must be integers")
        return
    listed_ips = []
    for name in device_names:
        ip = device_map.get(name)
        if not ip:
            print(f"Unknown device {name}, skipping")
        else:
            listed_ips.append(ip)
    if not listed_ips:
        print("No valid devices to play note on")
        return
    play_note_on_specific_picos(freq, duration, listed_ips)


def handle_play_melody_specific(args):
    """
    Usage: play_melody_specific <note_gap> <device1> [device2 ...]
    """
    # TO-DO add functionality to let user play songs from CLI
    
    if len(args) != 2:
        print("Usage: play_melody <device1,device2,...> <note_gap>")
        return
    device_list_str, note_gap_str = args
    device_names = device_list_str.split(",")
    try:
        note_gap = int(note_gap_str)
    except ValueError:
        print("note_gap must be an integer")
        return
    listed_ips = []
    for name in device_names:
        ip = device_map.get(name)
        if not ip:
            print(f"Unknown device {name}, skipping")
        else:
            listed_ips.append(ip)
    if not listed_ips:
        print("No valid devices to play melody on")
        return
    play_melody_on_specifc_picos(SONG, note_gap, listed_ips)
    
def handle_play_note_all(args):
    # play_note_all <freq> <duration>
    if len(args) != 2:
        print("Usage: play_note_all <freq> <duration>")
        return
    freq = int(args[0])
    duration = int(args[1])
    play_note_on_all_picos(freq, duration)

def handle_play_melody_all(args):
    # TO-DO add functionality to let user play songs from CLI
    
    if len(args) != 1:
        print("Usage: play_melody_all <note_gap>")
        return
    try:
        note_gap = int(args[0])
    except ValueError:
        print("note_gap must be an integer")
        return
    play_melody_on_all_picos(SONG, note_gap)
    
def handle_get_health(args):
    if len(args) != 1:
        print("Usage: get_health <device>")
        return
    ip = device_map.get(args[0])
    if not ip:
        print(f"Unknown device {args[0]}")
        return
    get_pico_health(ip)

def handle_get_mode(args):
    if len(args) != 1:
        print("Usage: get_mode <device>")
        return
    ip = device_map.get(args[0])
    if not ip:
        print(f"Unknown device {args[0]}")
        return
    get_device_mode(ip)

def handle_get_range(args):
    if len(args) != 1:
        print("Usage: get_range <device>")
        return
    ip = device_map.get(args[0])
    if not ip:
        print(f"Unknown device {args[0]}")
        return
    url = f"http://{ip}/get_range"
    try:
        resp = requests.get(url, timeout=0.1)
        range_val = resp.json()
        print(f"{args[0]} range: {range_val}")
    except requests.exceptions.RequestException as e:
        print(f"Error contacting {ip}: {e}")


def handle_get_sensor_data(args):
    if len(args) != 1:
        print("Usage: get_sensor_data <device>")
        return
    ip = device_map.get(args[0])
    if not ip:
        print(f"Unknown device {args[0]}")
        return
    get_sensor_data(ip)


def handle_get_events(args):
    if len(args) != 2:
        print("Usage: get_events <device> <sampling_rate>")
        return
    device_name = args[0]
    ip = device_map.get(device_name)
    if not ip:
        print(f"Unknown device {device_name}")
        return
    try:
        sampling_rate = int(args[1])
    except ValueError:
        print("sampling_rate must be an integer")
        return

    stream_events(ip, sampling_rate)


def handle_get_melody(args):
    if len(args) != 2:
        print("Usage: get_melody <device> <sampling_rate>")
        return
    device_name = args[0]
    ip = device_map.get(device_name)
    if not ip:
        print(f"Unknown device {device_name}")
        return
    try:
        sampling_rate = int(args[1])
    except ValueError:
        print("sampling_rate must be an integer")
        return

    stream_melody(ip, sampling_rate)

def handle_set_mode(args):
    if len(args) != 2:
        print("Usage: set_mode <device> <mode>")
        return
    ip = device_map.get(args[0])
    if not ip:
        print(f"Unknown device {args[0]}")
        return
    mode = args[1]
    post_device_mode(ip, mode)


def handle_set_range(args):
    if len(args) != 2:
        print("Usage: set_range <device> <range>")
        return
    ip = device_map.get(args[0])
    if not ip:
        print(f"Unknown device {args[0]}")
        return
    try:
        range_val = int(args[1])
    except ValueError:
        print("range must be an integer")
        return
    payload = {"range": range_val}
    url = f"http://{ip}/post_range"
    try:
        requests.post(url, json=payload, timeout=0.1)
        print(f"Set range of {args[0]} to {range_val}")
    except requests.exceptions.RequestException as e:
        print(f"Error contacting {ip}: {e}")

COMMAND_HANDLERS = {
    "play_note": handle_play_note_specific,
    "play_melody": handle_play_melody_specific,
    "play_note_all": handle_play_note_all,
    "play_melody_all": handle_play_melody_all,
    "get_health": handle_get_health,
    "get_mode": handle_get_mode,
    "get_range": handle_get_range,
    "get_sensor_data": handle_get_sensor_data,
    "get_events": handle_get_events,
    "get_melody": handle_get_melody,
    "set_mode": handle_set_mode,
    "set_range": handle_set_range
}

def main():
    print("--- Conductor App for Miniproject ---")
    print("Type 'help' for commands, 'exit' to quit or CTRL+C")

    # Build device mapping (device_1, device_2, etc.)
    global device_map
    device_map = {f"device_{i+1}": ip for i, ip in enumerate(PICO_IPS)}

    # Print detected devices
    print("Detected devices:")
    for name, ip in device_map.items():
        print(f"  {name}: {ip}")
    try:
        while True:
            cmd_input = input("> ").strip()
            if not cmd_input:
                continue
            if cmd_input.lower() in ["exit", "quit"]:
                print("Exiting CLI...")
                break

            # Split command into name + args
            parts = cmd_input.split()
            cmd_name, *args = parts

            # Handle 'help' separately
            if cmd_name.lower() == "help":
                print("""Commands:
play_note_all <freq> <duration>
play_melody_all <song> <note_gap>
play_note <targeted devices> <freq> <duration>
play_melody <targeted devices> <song> <note_gap>
get_health <device>
get_mode <device>
get_range <device>
get_sensor_data <device>
get_events <device> <sampling_rate>
get_melody <device> <sampling_rate>
set_mode <device> <mode>
set_range <device> <range>""")
                continue

            # Lookup handler
            handler = COMMAND_HANDLERS.get(cmd_name)
            if handler:
                try:
                    handler(args)
                except Exception as e:
                    print(f"Error executing command '{cmd_name}': {e}")
            else:
                print(f"Unknown command '{cmd_name}'. Type 'help' for a list of commands.")

    except KeyboardInterrupt:
        print("\nCLI stopped by user")


if __name__ == "__main__":
    main()

# original main loop    
"""
if __name__ == "__main__":
    print("--- Pico Light Orchestra Conductor ---")
    print(f"Found {len(PICO_IPS)} devices in the orchestra.")
    print("Press Ctrl+C to stop.")

    try:
        # Give a moment for everyone to get ready
        print("\nStarting in 3...")
        time.sleep(1)
        print("2...")
        time.sleep(1)
        print("1...")
        time.sleep(1)
        print("Go!\n")

        # Play the song
        for note, duration in SONG:
            play_note_on_all_picos(note, duration)
            # Wait for the note's duration plus a small gap before playing the next one
            time.sleep(duration / 1000 * 1.1)

        print("\nSong finished!")

    except KeyboardInterrupt:
        print("\nConductor stopped by user.")
        """