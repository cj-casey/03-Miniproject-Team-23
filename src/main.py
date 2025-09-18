# main.py - Pico Light Orchestra Firmware (Fixed)
# For Raspberry Pi Pico 2W with MicroPython

import machine
import time
import network
import json
import asyncio
import gc
import ubinascii

# --- Pin Configuration ---
# IMPORTANT: Using GP26 for ADC (not GP28 which is reserved on Pico W)
photo_sensor_pin = machine.ADC(26)  # ADC0 on GP26

# Buzzer on GP16 with PWM
buzzer_pin = machine.PWM(machine.Pin(16))

# --- Global State ---
device_id = ubinascii.hexlify(machine.unique_id()).decode()
current_mode = "Live Play"
sensor_range = 100
api_note_task = None
recorded_melody = []
recording_start_time = 0
is_recording = False
last_sensor_value = 0
normalized_value = 0
ip_address = "0.0.0.0"  # Initialize to prevent undefined errors

# Musical notes
NOTES = {
    'C4': 262, 'D4': 294, 'E4': 330, 'F4': 349,
    'G4': 392, 'A4': 440, 'B4': 494, 'C5': 523
}

# --- Core Functions ---

def connect_to_wifi(wifi_config="wifi_config.json"):
    """Connects the Pico W to WiFi."""
    try:
        with open(wifi_config, "r") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading wifi_config.json: {e}")
        return None

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    print(f"Connecting to {data['ssid']}...")
    wlan.connect(data["ssid"], data["password"])

    # Wait for connection
    max_wait = 15
    while max_wait > 0:
        status = wlan.status()
        if status < 0 or status >= 3:
            break
        max_wait -= 1
        print(f"Waiting... status: {status}")
        time.sleep(1)

    if wlan.status() != 3:
        print(f"Failed to connect. Status: {wlan.status()}")
        return None
    
    ip = wlan.ifconfig()[0]
    print(f"Connected! IP: {ip}")
    print(f"Device ID: {device_id}")
    return ip

def read_sensor():
    """Read and normalize the light sensor value."""
    global last_sensor_value, normalized_value
    
    raw_value = photo_sensor_pin.read_u16()
    last_sensor_value = raw_value
    
    # Normalize to 0.0 - 1.0 range
    min_light = 1000
    max_light = 65000
    
    clamped = max(min_light, min(raw_value, max_light))
    normalized_value = (clamped - min_light) / (max_light - min_light)
    
    return raw_value, normalized_value

def estimate_lux(raw_value):
    """Estimate lux from ADC reading."""
    max_lux = 10000
    lux = (raw_value / 65535) * max_lux
    return int(lux)

def light_to_frequency(norm_value):
    """Map normalized light value to frequency."""
    if norm_value < 0.1:
        return 0
    
    min_freq = NOTES['C4']
    max_freq = NOTES['C5']
    freq = min_freq + (norm_value * (max_freq - min_freq))
    return int(freq)

def stop_tone():
    """Stop any sound from playing."""
    try:
        buzzer_pin.duty_u16(0)
    except:
        pass

async def play_api_note(frequency, duration_ms, duty=0.5):
    """Async coroutine to play a note from API call."""
    try:
        if frequency > 0:
            buzzer_pin.freq(int(frequency))
            duty_u16 = int(duty * 65535)
            buzzer_pin.duty_u16(duty_u16)
            await asyncio.sleep_ms(duration_ms)
            stop_tone()
    except asyncio.CancelledError:
        stop_tone()

# --- Simplified Web Server ---

async def handle_request(reader, writer):
    """Handle incoming HTTP requests."""
    global api_note_task, current_mode, sensor_range
    
    try:
        # Read request
        request_line = await reader.readline()
        
        # Skip headers
        while True:
            line = await reader.readline()
            if line == b"\r\n":
                break
        
        # Parse request
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
        
        # Simple routing
        if path == "/health":
            response = json.dumps({
                "status": "active",
                "device_id": device_id,
                "api": "v1.0"
            })
            writer.write(b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n")
            writer.write(response.encode())
            
        elif path == "/sensor":
            raw, norm = read_sensor()
            response = json.dumps({
                "raw": raw,
                "norm": round(norm, 3),
                "lux_est": estimate_lux(raw)
            })
            writer.write(b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n")
            writer.write(response.encode())
            
        elif path == "/get_mode":
            response = json.dumps({"mode": current_mode})
            writer.write(b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n")
            writer.write(response.encode())
            
        elif path == "/get_range":
            response = json.dumps({"range": sensor_range})
            writer.write(b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n")
            writer.write(response.encode())
            
        elif method == "POST" and path == "/tone":
            # Read body (simplified - assumes small payload)
            body = await reader.read(200)
            try:
                data = json.loads(body)
                freq = int(data.get("freq", 440))
                ms = int(data.get("ms", 100))
                duty = float(data.get("duty", 0.5))
                
                # Cancel existing note
                if api_note_task and not api_note_task.done():
                    api_note_task.cancel()
                
                # Play new note
                api_note_task = asyncio.create_task(play_api_note(freq, ms, duty))
                
                response = json.dumps({"status": "ok"})
                writer.write(b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n")
                writer.write(response.encode())
            except Exception as e:
                print(f"Tone error: {e}")
                writer.write(b"HTTP/1.0 400 Bad Request\r\n\r\n")
                
        elif method == "POST" and path == "/stop":
            if api_note_task and not api_note_task.done():
                api_note_task.cancel()
            stop_tone()
            response = json.dumps({"status": "ok"})
            writer.write(b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n")
            writer.write(response.encode())
            
        elif method == "POST" and path == "/post_mode":
            body = await reader.read(200)
            try:
                data = json.loads(body)
                mode = data.get("mode", "")
                if mode in ["l", "L", "Live Play"]:
                    current_mode = "Live Play"
                elif mode in ["r", "R", "Record & Play"]:
                    current_mode = "Record & Play"
                response = json.dumps({"status": "ok", "mode": current_mode})
                writer.write(b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n")
                writer.write(response.encode())
            except:
                writer.write(b"HTTP/1.0 400 Bad Request\r\n\r\n")
                
        elif method == "POST" and path == "/post_range":
            body = await reader.read(200)
            try:
                data = json.loads(body)
                sensor_range = int(data.get("range", 100))
                response = json.dumps({"status": "ok", "range": sensor_range})
                writer.write(b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n")
                writer.write(response.encode())
            except:
                writer.write(b"HTTP/1.0 400 Bad Request\r\n\r\n")
                
        elif path == "/":
            raw, norm = read_sensor()
            html = f"""<html><body>
            <h1>Pico Light Orchestra</h1>
            <p>Device: {device_id}</p>
            <p>IP: {ip_address}</p>
            <p>Mode: {current_mode}</p>
            <p>Sensor: {raw} (norm: {norm:.3f})</p>
            </body></html>"""
            writer.write(b"HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n")
            writer.write(html.encode())
            
        else:
            writer.write(b"HTTP/1.0 404 Not Found\r\n\r\n")
            
    except Exception as e:
        print(f"Request error: {e}")
    finally:
        await writer.drain()
        writer.close()
        await writer.wait_closed()

async def sensor_loop():
    """Main sensor reading loop."""
    while True:
        try:
            # Skip if API note is playing
            if api_note_task and not api_note_task.done():
                await asyncio.sleep_ms(100)
                continue
            
            # Read sensor and play tone in Live Play mode
            if current_mode == "Live Play":
                raw, norm = read_sensor()
                if norm > 0.1:
                    freq = light_to_frequency(norm)
                    if freq > 0:
                        buzzer_pin.freq(freq)
                        buzzer_pin.duty_u16(32768)  # 50% duty
                else:
                    stop_tone()
            
            await asyncio.sleep_ms(100)
            
        except Exception as e:
            print(f"Sensor loop error: {e}")
            await asyncio.sleep_ms(1000)

async def main():
    """Main entry point."""
    global ip_address
    
    print("\n=== Pico Light Orchestra Starting ===")
    
    # Connect to WiFi
    ip_address = connect_to_wifi()
    if not ip_address:
        print("Running in offline mode - WiFi failed")
        # Could still run sensor loop without network
        return
    
    # Start web server
    print(f"Starting web server on port 80...")
    try:
        server = await asyncio.start_server(handle_request, "0.0.0.0", 80)
    except Exception as e:
        print(f"Server start error: {e}")
        return
    
    # Start sensor loop
    sensor_task = asyncio.create_task(sensor_loop())
    
    # Keep running
    print("System ready!")
    print(f"Dashboard: http://{ip_address}/")
    
    while True:
        await asyncio.sleep(1)
        gc.collect()  # Periodic garbage collection

# --- Entry Point ---

if __name__ == "__main__":
    # Initialize hardware
    stop_tone()
    
    try:
        # Run async main
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested")
        stop_tone()
    except Exception as e:
        print(f"Fatal error: {e}")
        stop_tone()
        # Wait before potential restart
        time.sleep(5)
    # Removed machine.reset() - no more boot loops!
    