# 2025 Fall ECE Senior Design Miniproject

[Project definition](./Project.md)

This project uses the Raspberry Pi Pico 2WH SC1634 (wireless, with header pins).

Each team must provide a micro-USB cable that connects to their laptop to plug into the Pi Pico.
The cord must have the data pins connected.
Splitter cords with multiple types of connectors fanning out may not have data pins connected.
Such micro-USB cords can be found locally at Microcenter, convenience stores, etc.
The student laptop is used to program the Pi Pico.
The laptop software to program and debug the Pi Pico works on macOS, Windows, and Linux.

This miniproject focuses on using
[MicroPython](./doc/micropython.md)
using
[Thonny IDE](./doc/thonny.md).
Other IDE can be used, including Visual Studio Code or
[rshell](./doc/rshell.md).

## Hardware

* Raspberry Pi Pico WH [SC1634](https://pip.raspberrypi.com/categories/1088-raspberry-pi-pico-2-w) (WiFi, Bluetooth, with header pins)
* Freenove Pico breakout board [FNK0081](https://store.freenove.com/products/fnk0081)
* Piezo Buzzer SameSky CPT-3095C-300
* 10k ohm resistor
* 2 [tactile switches](hhttps://www.mouser.com/ProductDetail/E-Switch/TL59NF160Q?qs=QtyuwXswaQgJqDRR55vEFA%3D%3D)

### Photoresistor details

The photoresistor uses the 10k ohm resistor as a voltage divider
[circuit](./doc/photoresistor.md).
The 10k ohm resistor connects to "3V3" and to ADC2.
The photoresistor connects to the ADC2 and to AGND.
Polarity is not important for this resistor and photoresistor.

The MicroPython
[machine.ADC](https://docs.micropython.org/en/latest/library/machine.ADC.html)
class is used to read the analog voltage from the photoresistor.
The `machine.ADC(id)` value corresponds to the "GP" pin number.
On the Pico W, GP28 is ADC2, accessed with `machine.ADC(28)`.

### Piezo buzzer details

PWM (Pulse Width Modulation) can be used to generate analog signals from digital outputs.
The Raspberry Pi Pico has eight PWM groups each with two PWM channels.
The [Pico WH pinout diagram](https://datasheets.raspberrypi.com/picow/PicoW-A4-Pinout.pdf)
shows that almost all Pico pins can be used for multiple distinct tasks as configured by MicroPython code or other software.
In this exercise, we will generate a PWM signal to drive a speaker.

GP16 is one of the pins that can be used to generate PWM signals.
Connect the speaker with the black wire (negative) to GND and the red wire (positive) to GP16.

In a more complete project, we would use additional resistors and capacitors with an amplifer to boost the sound output to a louder level with a bigger speaker.
The sound output is quiet but usable for this exercise.

Musical notes correspond to particular base frequencies and typically have rich harmonics in typical musical instruments.
An example soundboard showing note frequencies is [clickable](https://muted.io/note-frequencies/).
Over human history, the corresspondance of notes to frequencies has changed over time and location and musical cultures.
For the question below, feel free to use musical scale of your choice!

[Music Examples](https://github.com/twisst/Music-for-Raspberry-Pi-Pico/blob/main/play.py)


## Notes

Pico MicroPython time.sleep() doesn't error for negative values even though such are obviously incorrect--it is undefined for a system to sleep for negative time.
Duty cycle greater than 1 is undefined, so we clip the duty cycle to the range [0, 1].


## Reference

* [Pico 2WH pinout diagram](https://datasheets.raspberrypi.com/picow/pico-2-w-pinout.pdf) shows the connections to analog and digital IO.
* Getting Started with Pi Pico [book](https://datasheets.raspberrypi.com/pico/getting-started-with-pico.pdf)

# Team 23 Agile Miniproject

## Initial Design Drafts
The initial design for the project is shown here: [chassis](./doc/chassis_product_design_draft.png)

The design created on onshape is shown here: https://cad.onshape.com/documents/3d0e02dee876016a6d19eae0 (Copy & paste into your browser)

The flowchart for the processes is shown here: [operation](./doc/operational_flowchart_draft.png)

The overall circuit diagram is shown here: [circuit](MiniProjectSchematic.pdf)

## Design Aspects
We designed a kid-friendly product to allow kids to play music using light, while allowing parents or guardians to listen in and calibrate additional devices via their computer. 
### Appearance
To keep things simple, we went for a classic happy ghost appearance for the chassis of the product. It is 6 inches tall, 4 inches wide, and 1.5 inches thick. These dimensions should make it easy to hold, move, and stand up for use by a user. 
### Device Locations in Chassis
In each of the eyes, we will place the photoresistors (currently only 1) to allow for stereo music playing. Where the ears of the ghost would be, we place each of the buzzers one on each side once again to support stereo in the future. On the back, is an opening that will allow you to either directly plug into the pico, or in the future, we'd like it to be battery operated. Two LEDs on the lower portion indicate the device's power and its current mode. This setup should give a fun experience for kids to flash a ghost with different lights and have it sing different tunes. 
### Features
Our main design goal was to allow the product to achieve two different modes: Live Play, and Record & Play. Live Play is more akin to playing an instrument, light goes in, sound comes out immediately. Record & Play waits until the user shines light at it, and then begins to record until the user stops or the maximum length song is reached. Afterwards, it plays back the full song. On the parent side, in the conductor app, we developed a CLI that allows them to see which Pico Light Orchestras are available to connect to, and enter specific commands to interact with any or all of them. Instead of needing to remember the IPs, we map them to device names, which makes interacting with them much easier as a user.
### Commands / API Calls for Conductor
play_note_all -freq -duration : plays a note on all available devices for a given duration  
play_melody_all -song -note_gap : plays a melody on all available devices with a given note gap  
play_note -targeted_devices -freq -duration : plays a note on listed devices for a given duration  
play_melody -targeted_devices -song -note_gap : plays a melody on specific available devices with a given note gap  
get_health -device : returns the status of a specific device  
get_mode -device : returns the current mode of a specific device  
get_range -device : returns the light level range of detection for a specific device  
get_sensor_data -device : returns the current sensor's reading for a specific device  
get_events -device -sampling_rate : returns the current sensors reading in a live feed at a chosen sampling rate for a specific device  
get_melody -device -sampling_rate : returns the playing notes in a live feed at a chosen sampling rate for a specific device  
set_mode -device -mode : sets the mode of a specific to device to either "Record & Play" or "Live Play"  
set_range -device -range : sets the light level range of detection for a specific device (good for calibrating for better detection)
