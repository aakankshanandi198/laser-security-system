import os
import cv2
import time
import RPi.GPIO as GPIO
import threading
import http.server
import socketserver


# GPIO pin setup
BUZZER_PIN = 26
LASER_SENSOR_PIN = 5

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUZZER_PIN, GPIO.OUT)
GPIO.setup(LASER_SENSOR_PIN, GPIO.IN)

# setup laser debounce counter
debounce_counter = 0

# Setup camera capture stream
# 0 refer to the first connected camera
cap = cv2.VideoCapture(0)
# init fps and frame dimensions
fps = 10
frame_width = int(cap.get(3))
frame_height = int(cap.get(4))
# var to hold frames from camera 
frame = None
# var to hold camera output stream
out = None

# Get parent directory of the script
script_dir = os.path.dirname(os.path.abspath(__file__))
evidence_dir = os.path.join(script_dir, 'evidence')

# HTTP Server setup
PORT = 8000
Handler = http.server.SimpleHTTPRequestHandler

# Custom handler to serve files from the evidence directory
class EvidenceHandler(Handler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=evidence_dir, **kwargs)

# Function to start the HTTP server
def start_http_server():
    with socketserver.TCPServer(("", PORT), EvidenceHandler) as httpd:
        print(f"Serving HTTP on port {PORT} at http://localhost:{PORT}")
        httpd.serve_forever()


# hack to allow us use a 5v laser sensor with 3v3 volt
# return 0 when line-break and 1 when laser is detected
def read_sensor():
    time.sleep(0.05)
    global debounce_counter
    # the laser sensor is active low
    if(GPIO.input(LASER_SENSOR_PIN)==0):
        debounce_counter+=1
        # return 1 when laser is detected consistently for 10 times
        if(debounce_counter>10):
            value = 1
        # else return 0 meaning laser is not detected, until the debounce counter reaches the threashold
        value = 0
    else:
        # reset the debounce counter if laser is not detected 
        debounce_counter = 0
        # return 0 when laser is not detected
        value = 0
    return value

def buzz(state):
    if state:
        # buzzer buzzes when signal is low
        GPIO.output(BUZZER_PIN, GPIO.LOW)
    else:
        GPIO.output(BUZZER_PIN, GPIO.HIGH)

# execute the code only when main.py is run
# not when this main.py is imported 
if __name__=="__main__":
    try:
        # Start HTTP server in a separate thread
        http_thread = threading.Thread(target=start_http_server, daemon=True)
        http_thread.start()
        # check if camera capture stream could be opened
        if not cap.isOpened():
            print("Error: Could not open webcam")
            exit()
        # check if evidence folder exists, if not create it
        if not os.path.exists(evidence_dir):
            os.makedirs(evidence_dir)
        # Initialize system state and print startup message
        print("Laser detection started, Press Ctrl+C to stop.\n")
        # state var decides when buzz + camera should start/stop
        state = 0
        # Start camera rolling
        _, frame = cap.read()
        # Execute the below code until ctrl+C is not pressed
        while True:
            value = read_sensor()
            print("laser sensor value is "+str(value)+" state value "+str(state)+"\n")
            # sensor detected line break and was not capturing/buzzing
            # start buzzing and capturing
            if value == 0 and state == 0:
                print("Laser not detected! Activating alarm...\n")
                state = 1
                buzz(state)
                # prep camera output stream
                timestamp =  time.strftime("%Y%m%d-%H%M%S")
                filename = os.path.join(evidence_dir,f"suspect_{timestamp}.jpg")
                cv2.imwrite(filename,frame)
            # sensor detected back laser but was capturing/buzzing
            # stop buzzing and capturing, write capture frames
            elif value == 1 and state == 1:
                print("Laser detected\n")
                state = 0
                buzz(state)
    except KeyboardInterrupt:
        print("Program terminated by user\n")
    finally:
        # cleanup GPIO
        GPIO.cleanup()
        print("GPIO cleaned up.")
        # release camera resources
        cap.release()
        print("Camera released.")
        # close the evidence website
        http_thread.join(timeout=1.0)  # Wait for thread to terminate
        print("HTTP server stopped.")
