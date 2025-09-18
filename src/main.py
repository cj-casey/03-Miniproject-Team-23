# main.py - Enhanced Pico Light Orchestra Firmware
# With proper calibration and Record & Play functionality

import machine
import time
import network
import json
import asyncio
import gc
import ubinascii

# --- Pin Configuration ---
photo_sensor_pin = machine.ADC(26)  # ADC0 on GP26
buzzer_pin = machine.PWM(machine.Pin(16))

# Button pins for Record & Play control
button1_pin = machine.Pin(14, machine.Pin.IN, machine.Pin.PULL_UP)  # Start/Stop recording
button2_pin = machine.Pin(15, machine.Pin.IN, machine.Pin.PULL_UP)  # Playback

# --- Global State ---
device_id = ubinascii.hexlify(machine.unique_id()).decode()
current_mode = "Live Play"
sensor_range = 100
api_note_task = None
ip_address = "0.0.0.0"

# Calibration variables
ambient_light_floor = 30000  # Will be set during calibration
ambient_light_ceiling = 40000  # Will be set during calibration
calibrated = False

# Recording variables
recorded_melody = []
recording_start_time = 0
is_recording = False
is_playing_back = False
last_button1_state = 1
last_button2_state = 1

# Musical scale
NOTES = [262, 294, 330, 349, 392, 440, 494, 523, 587, 659, 698, 784]  # C4 to B4

# --- Calibration Functions ---

def calibrate_sensor(duration_ms=3000):
    """
    Calibrate the sensor by finding min/max values over a period.
    User should cover and uncover the sensor during calibration.
    """
    global ambient_light_floor, ambient_light_ceiling, calibrated
    
    print("=== CALIBRATION START ===")
    print("Move your hand over the sensor for 3 seconds...")
    print("Cover it completely and expose it to light")
    
    samples = []
    start_time = time.ticks_ms()
    
    # Blink LED/buzzer to indicate calibration
    for i in range(3):
        buzzer_pin.freq(1000)
        buzzer_pin.duty_u16(10000)
        time.sleep(0.1)
        buzzer_pin.duty_u16(0)
        time.sleep(0.2)
    
    # Collect samples
    while time.ticks_diff(time.ticks_ms(), start_time) < duration_ms:
        samples.append(photo_sensor_pin.read_u16())
        time.sleep(0.01)
    
    # Calculate floor (darkest) and ceiling (brightest)
    ambient_light_floor = min(samples)
    ambient_light_ceiling = max(samples)
    
    # Add some padding to avoid edge cases
    margin = (ambient_light_ceiling - ambient_light_floor) * 0.1
    ambient_light_floor = max(0, ambient_light_floor - margin)
    ambient_light_ceiling = min(65535, ambient_light_ceiling + margin)
    
    # Ensure minimum range
    if ambient_light_ceiling - ambient_light_floor < 1000:
        ambient_light_ceiling = ambient_light_floor + 1000
    
    calibrated = True
    
    # Success beep
    buzzer_pin.freq(523)
    buzzer_pin.duty_u16(20000)
    time.sleep(0.2)
    buzzer_pin.duty_u16(0)
    
    print(f"Calibration complete!")
    print(f"Floor (dark): {ambient_light_floor}")
    print(f"Ceiling (bright): {ambient_light_ceiling}")
    print(f"Range: {ambient_light_ceiling - ambient_light_floor}")
    
    return ambient_light_floor, ambient_light_ceiling

def read_sensor_calibrated():
    """
    Read sensor and return normalized value based on calibration.
    """
    raw_value = photo_sensor_pin.read_u16()
    
    if not calibrated:
        # Fallback to default range if not calibrated
        norm = (raw_value - 1000) / (50000 - 1000)
    else:
        # Use calibrated range
        norm = (raw_value - ambient_light_floor) / (ambient_light_ceiling - ambient_light_floor)
    
    # Clamp to 0.0 - 1.0
    norm = max(0.0, min(1.0, norm))
    
    return raw_value, norm

def light_to_note_index(norm_value, sensitivity=None):
    """
    Map normalized light (0-1) to note index with sensitivity adjustment.
    """
    if sensitivity is None:
        sensitivity = sensor_range / 100.0  # Convert range to 0-1 scale
    
    # Apply sensitivity curve (makes it easier to hit notes)
    adjusted = norm_value ** (2.0 - sensitivity)
    
    # Map to note index
    note_index = int(adjusted * (len(NOTES) - 1))
    return max(0, min(len(NOTES) - 1, note_index))

def stop_tone():
    """Stop any sound."""
    try:
        buzzer_pin.duty_u16(0)
    except:
        pass

# --- Recording Functions ---

def start_recording():
    """Start recording a melody."""
    global is_recording, recording_start_time, recorded_melody
    
    if current_mode != "Record & Play":
        return False
    
    recorded_melody = []
    recording_start_time = time.ticks_ms()
    is_recording = True
    
    # Indicate recording start with beeps
    for i in range(2):
        buzzer_pin.freq(800)
        buzzer_pin.duty_u16(20000)
        time.sleep(0.1)
        buzzer_pin.duty_u16(0)
        time.sleep(0.1)
    
    print("Recording started...")
    return True

def stop_recording():
    """Stop recording."""
    global is_recording
    
    if not is_recording:
        return False
    
    is_recording = False
    
    # Indicate recording stop
    buzzer_pin.freq(400)
    buzzer_pin.duty_u16(20000)
    time.sleep(0.2)
    buzzer_pin.duty_u16(0)
    
    print(f"Recording stopped. {len(recorded_melody)} events captured.")
    return True

async def playback_recording():
    """Play back the recorded melody."""
    global is_playing_back
    
    if not recorded_melody:
        print("No recording to play")
        return
    
    is_playing_back = True
    print(f"Playing back {len(recorded_melody)} events...")
    
    # Indicate playback start
    buzzer_pin.freq(600)
    buzzer_pin.duty_u16(20000)
    await asyncio.sleep_ms(100)
    buzzer_pin.duty_u16(0)
    await asyncio.sleep_ms(200)
    
    # Play back each recorded event
    last_time = 0
    for event in recorded_melody:
        # Wait for the correct timing
        time_diff = event["time"] - last_time
        if time_diff > 0:
            await asyncio.sleep_ms(time_diff)
        
        # Play the note
        if event["freq"] > 0:
            buzzer_pin.freq(event["freq"])
            buzzer_pin.duty_u16(event.get("duty", 32768))
        else:
            buzzer_pin.duty_u16(0)
        
        last_time = event["time"]
    
    # Stop at end
    buzzer_pin.duty_u16(0)
    is_playing_back = False
    print("Playback complete")

# --- Button Handlers ---

async def button_monitor():
    """Monitor button presses for Record & Play mode."""
    global last_button1_state, last_button2_state
    
    while True:
        if current_mode == "Record & Play":
            # Button 1: Start/Stop recording
            button1_state = button1_pin.value()
            if button1_state == 0 and last_button1_state == 1:  # Pressed
                if is_recording:
                    stop_recording()
                else:
                    start_recording()
            last_button1_state = button1_state
            
            # Button 2: Playback
            button2_state = button2_pin.value()
            if button2_state == 0 and last_button2_state == 1:  # Pressed
                if not is_recording and not is_playing_back:
                    asyncio.create_task(playback_recording())
            last_button2_state = button2_state
        
        await asyncio.sleep_ms(50)

# --- Web API Handlers ---

async def handle_request(reader, writer):
    """Handle HTTP requests with calibration endpoints."""
    global current_mode, sensor_range, api_note_task
    
    try:
        request_line = await reader.readline()
        
        # Skip headers
        while True:
            line = await reader.readline()
            if line == b"\r\n":
                break
        
        request = request_line.decode().strip()
        if not request:
            writer.close()
            await writer.wait_closed()
            return
            
        parts = request.split()
        if len(parts) < 2:
            writer.close()
            await writer.wait_closed()
            return
            
        method, path = parts[0], parts[1]
        print(f"{method} {path}")
        
        # Route endpoints
        if path == "/health":
            response = json.dumps({
                "status": "active",
                "device_id": device_id,
                "api": "v2.0",
                "calibrated": calibrated
            })
            writer.write(b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n")
            writer.write(response.encode())
            
        elif path == "/sensor":
            raw, norm = read_sensor_calibrated()
            response = json.dumps({
                "raw": raw,
                "norm": round(norm, 3),
                "floor": ambient_light_floor,
                "ceiling": ambient_light_ceiling,
                "calibrated": calibrated
            })
            writer.write(b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n")
            writer.write(response.encode())
            
        elif path == "/calibrate" and method == "POST":
            # Trigger calibration
            asyncio.create_task(async_calibrate())
            response = json.dumps({"status": "calibrating"})
            writer.write(b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n")
            writer.write(response.encode())
            
        elif path == "/get_mode":
            response = json.dumps({
                "mode": current_mode,
                "is_recording": is_recording,
                "is_playing": is_playing_back,
                "melody_length": len(recorded_melody)
            })
            writer.write(b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n")
            writer.write(response.encode())
            
        elif path == "/post_mode" and method == "POST":
            body = await reader.read(200)
            try:
                data = json.loads(body)
                mode = data.get("mode", "")
                
                if mode in ["l", "L", "Live Play"]:
                    current_mode = "Live Play"
                    stop_recording()
                elif mode in ["r", "R", "Record & Play"]:
                    current_mode = "Record & Play"
                
                response = json.dumps({"status": "ok", "mode": current_mode})
                writer.write(b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n")
                writer.write(response.encode())
            except:
                writer.write(b"HTTP/1.0 400 Bad Request\r\n\r\n")
        
        elif path == "/record/start" and method == "POST":
            success = start_recording()
            response = json.dumps({"status": "ok" if success else "error"})
            writer.write(b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n")
            writer.write(response.encode())
            
        elif path == "/record/stop" and method == "POST":
            success = stop_recording()
            response = json.dumps({
                "status": "ok" if success else "error",
                "events": len(recorded_melody)
            })
            writer.write(b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n")
            writer.write(response.encode())
            
        elif path == "/record/play" and method == "POST":
            if not is_recording and not is_playing_back:
                asyncio.create_task(playback_recording())
                response = json.dumps({"status": "playing"})
            else:
                response = json.dumps({"status": "busy"})
            writer.write(b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n")
            writer.write(response.encode())
            
        elif path == "/melody":
            response = json.dumps({
                "melody": recorded_melody[:100],  # Limit size
                "total_events": len(recorded_melody),
                "duration_ms": recorded_melody[-1]["time"] if recorded_melody else 0
            })
            writer.write(b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n")
            writer.write(response.encode())
            
        elif method == "POST" and path == "/tone":
            body = await reader.read(200)
            try:
                data = json.loads(body)
                freq = int(data.get("freq", 440))
                ms = int(data.get("ms", 100))
                duty = float(data.get("duty", 0.5))
                
                if api_note_task and not api_note_task.done():
                    api_note_task.cancel()
                
                api_note_task = asyncio.create_task(play_api_tone(freq, ms, duty))
                
                response = json.dumps({"status": "ok"})
                writer.write(b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n")
                writer.write(response.encode())
            except:
                writer.write(b"HTTP/1.0 400 Bad Request\r\n\r\n")
                
        elif path == "/":
            raw, norm = read_sensor_calibrated()
            
            # Build HTML with simpler string concatenation for MicroPython compatibility
            calib_status = "Yes" if calibrated else "No"
            norm_percent = int(norm * 100)
            
            html = "<html>"
            html += "<head><title>Pico Orchestra</title></head>"
            html += "<body style='font-family: Arial; padding: 20px;'>"
            html += "<h1>Pico Light Orchestra</h1>"
            html += "<p><b>Device:</b> " + str(device_id) + "</p>"
            html += "<p><b>Mode:</b> " + str(current_mode) + "</p>"
            html += "<p><b>Calibrated:</b> " + calib_status + "</p>"
            html += "<hr>"
            html += "<p><b>Light Level:</b> " + str(raw) + "</p>"
            html += "<p><b>Normalized:</b> " + str(norm_percent) + "%</p>"
            html += "<p><b>Range:</b> " + str(ambient_light_floor) + " - " + str(ambient_light_ceiling) + "</p>"
            html += "<hr>"
            html += "<h3>Controls</h3>"
            html += "<button onclick=\"fetch('/calibrate', {method:'POST'})\">Calibrate</button>"
            html += "<button onclick=\"fetch('/post_mode', {method:'POST', body:JSON.stringify({mode:'Live Play'})})\">Live Play</button>"
            html += "<button onclick=\"fetch('/post_mode', {method:'POST', body:JSON.stringify({mode:'Record & Play'})})\">Record Mode</button>"
            
            if current_mode == "Record & Play":
                html += "<p><b>Recording:</b> " + str(is_recording) + "</p>"
            
            if recorded_melody:
                html += "<p><b>Melody Length:</b> " + str(len(recorded_melody)) + " events</p>"
            
            html += "<script>setTimeout(function(){location.reload()}, 3000)</script>"
            html += "</body></html>"
            
            writer.write(b"HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n")
            writer.write(html.encode())
        
        elif path == "/get_range":
            response = json.dumps({
                "floor": ambient_light_floor,
                "ceiling": ambient_light_ceiling,
                "range": ambient_light_ceiling - ambient_light_floor
            })
            writer.write(b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n")
            writer.write(response.encode())
            
        else:
            writer.write(b"HTTP/1.0 404 Not Found\r\n\r\n")
            
    except Exception as e:
        print(f"Request error: {e}")
    finally:
        await writer.drain()
        writer.close()
        await writer.wait_closed()

async def async_calibrate():
    """Async wrapper for calibration."""
    calibrate_sensor()

async def play_api_tone(freq, ms, duty):
    """Play tone from API."""
    try:
        if freq > 0:
            buzzer_pin.freq(freq)
            buzzer_pin.duty_u16(int(duty * 65535))
            await asyncio.sleep_ms(ms)
            stop_tone()
    except asyncio.CancelledError:
        stop_tone()

# --- Main Sensor Loop ---

async def sensor_loop():
    """Main sensor loop for Live Play and Recording."""
    global recorded_melody
    
    last_note_index = -1
    last_freq = 0
    
    while True:
        try:
            # Skip if API is playing or we're in playback
            if (api_note_task and not api_note_task.done()) or is_playing_back:
                await asyncio.sleep_ms(50)
                continue
            
            raw, norm = read_sensor_calibrated()
            
            if current_mode == "Live Play":
                # Live play with calibrated range
                if norm > 0.05:  # Threshold to avoid noise
                    note_index = light_to_note_index(norm)
                    
                    # Only change note if it's different (reduces jitter)
                    if note_index != last_note_index:
                        freq = NOTES[note_index]
                        buzzer_pin.freq(freq)
                        buzzer_pin.duty_u16(32768)
                        last_note_index = note_index
                else:
                    stop_tone()
                    last_note_index = -1
                    
            elif current_mode == "Record & Play" and is_recording:
                # Record mode - capture events with timing
                current_time = time.ticks_diff(time.ticks_ms(), recording_start_time)
                
                if norm > 0.05:
                    note_index = light_to_note_index(norm)
                    freq = NOTES[note_index]
                    
                    # Only record if note changed significantly
                    if abs(freq - last_freq) > 10:
                        recorded_melody.append({
                            "time": current_time,
                            "freq": freq,
                            "norm": norm,
                            "duty": 32768
                        })
                        
                        # Also play the note
                        buzzer_pin.freq(freq)
                        buzzer_pin.duty_u16(32768)
                        last_freq = freq
                else:
                    # Record silence if it's a change
                    if last_freq > 0:
                        recorded_melody.append({
                            "time": current_time,
                            "freq": 0,
                            "norm": 0,
                            "duty": 0
                        })
                    stop_tone()
                    last_freq = 0
                
                # Auto-stop after 30 seconds
                if current_time > 30000:
                    stop_recording()
            
            await asyncio.sleep_ms(25)  # 40Hz sampling rate
            
        except Exception as e:
            print(f"Sensor loop error: {e}")
            await asyncio.sleep_ms(1000)

# --- WiFi Connection ---

def connect_to_wifi(wifi_config="wifi_config.json"):
    """Connect to WiFi network."""
    try:
        with open(wifi_config, "r") as f:
            data = json.load(f)
    except:
        print("wifi_config.json not found")
        return None
    
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    print(f"Connecting to {data['ssid']}...")
    wlan.connect(data["ssid"], data["password"])
    
    max_wait = 15
    while max_wait > 0:
        if wlan.status() == 3:
            break
        max_wait -= 1
        time.sleep(1)
    
    if wlan.status() != 3:
        print(f"Connection failed")
        return None
    
    ip = wlan.ifconfig()[0]
    print(f"Connected! IP: {ip}")
    return ip

# --- Main Entry ---

async def main():
    """Main program."""
    global ip_address
    
    print("\n=== Pico Light Orchestra v2.0 ===")
    
    # Initial calibration
    print("\nCalibrating sensor...")
    calibrate_sensor()
    
    # Connect WiFi
    ip_address = connect_to_wifi()
    if not ip_address:
        print("Running offline")
        # Could still run with buttons
    
    # Start tasks
    tasks = [sensor_loop(), button_monitor()]
    
    if ip_address:
        print(f"Web server: http://{ip_address}/")
        await asyncio.start_server(handle_request, "0.0.0.0", 80)
    
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    stop_tone()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown")
        stop_tone()
    except Exception as e:
        print(f"Error: {e}")
        stop_tone()
        time.sleep(5)