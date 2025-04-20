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
PIR_SENSOR_PIN = 27

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUZZER_PIN, GPIO.OUT)
GPIO.setup(LASER_SENSOR_PIN, GPIO.IN)
GPIO.setup(PIR_SENSOR_PIN, GPIO.IN)

# setup laser debounce counter
laser_debounce_counter = 0

# Setup camera capture stream
# 0 refer to the first connected camera
cap = cv2.VideoCapture(0)
# init fps and frame dimensions
fps = 10
frame_width = int(cap.get(3))
frame_height = int(cap.get(4))
fourcc = cv2.VideoWriter_fourcc(*'XVID')
# var to hold frames from camera 
frame = None
# var to hold camera output stream
out = None

# Get parent directory of the script
script_dir = os.path.dirname(os.path.abspath(__file__))
evidence_dir = os.path.join(script_dir, 'evidence')
event_file = None

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
def read_laser_sensor():
    time.sleep(0.05)
    global laser_debounce_counter
    # the laser sensor is active low
    if(GPIO.input(LASER_SENSOR_PIN)==0):
        laser_debounce_counter+=1
        # return 1 when laser is detected consistently for 10 times
        if(laser_debounce_counter>10):
            value = 1
        # else return 0 meaning laser is not detected, until the debounce counter reaches the threashold
        else:
            value = 0
    else:
        # reset the debounce counter if laser is not detected 
        laser_debounce_counter = 0
        # return 0 when laser is not detected
        value = 0
    return value

def read_pir_sensor():
    time.sleep(0.05)
    # the pir sensor is active high
    return GPIO.input(PIR_SENSOR_PIN)

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
            if not os.path.exists(os.path.join(evidence_dir,"photos")):
                os.makedirs(os.path.join(evidence_dir,"photos"))
            if not os.path.exists(os.path.join(evidence_dir,"videos")):
                os.makedirs(os.path.join(evidence_dir,"videos"))
        # Create a csv files to record the events
        if not os.path.exists(os.path.join(evidence_dir,"events.csv")):
            with open(os.path.join(evidence_dir,"events.csv"),'w') as f:
                f.write("Timestamp, Laser, Pir, Image, Video\n")
        event_file = open(os.path.join(evidence_dir,"events.csv"),'a')
        # Initialize system state and print startup message
        print("Laser detection started, Press Ctrl+C to stop.\n")
        # state var decides when buzz + camera should start/stop
        buzzer_state = 0
        # state var decides when camera should start/stop
        camera_state = 0
        # Start camera rolling
        _, frame = cap.read()
        # Execute the below code until ctrl+C is not pressed
        while True:
            pir_sensor_value = read_pir_sensor()
            laser_sensor_value = read_laser_sensor()
            print("PIR sensor value is "+str(pir_sensor_value)+" camera state value is "+str(laser_sensor_value))
            print("Laser sensor value is "+str(laser_sensor_value)+" buzzer state value "+str(buzzer_state))
            
            # when PIR sensor detects motion and camera is not capturing
            # start camera capture stream
            
            if pir_sensor_value == 1 and camera_state == 0:
                print("PIR sensor detected motion! Starting camera...\n")
                # start camera capture stream
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                video_filename = os.path.join(evidence_dir+"/videos", f"video_{timestamp}.avi")
                out = cv2.VideoWriter(video_filename, fourcc, fps, (frame_width, frame_height))
                camera_state = 1
            # when PIR sensor does not detect motion and camera is capturing
            # stop camera capture stream
            elif pir_sensor_value == 0 and camera_state == 1:
                print("PIR sensor not detected motion! Stopping camera...\n")
                # stop camera capture stream
                out.release()
                video_filename = None
                camera_state = 0
            
            # sensor detected line break and was not capturing/buzzing
            # start buzzing and capturing
            if laser_sensor_value == 0 and buzzer_state == 0:
                print("Laser not detected! Activating alarm...\n")
                buzzer_state = 1
                buzz(buzzer_state)
                # prep camera output stream
                timestamp =  time.strftime("%Y%m%d-%H%M%S")
                image_filename = os.path.join(evidence_dir+"/photos",f"suspect_{timestamp}.jpg")
                cv2.imwrite(image_filename,frame)
                # record the event 
                event_file.write(str(timestamp)+", 1, "+str(pir_sensor_value)+", "+image_filename+", "+video_filename+"\n")
            # sensor detected back laser but was capturing/buzzing
            # stop buzzing and capturing, write capture frames
            elif laser_sensor_value == 1 and buzzer_state == 1:
                print("Laser detected\n")
                buzzer_state = 0
                buzz(buzzer_state)
    except KeyboardInterrupt:
        print("Program terminated by user\n")
    finally:
        # cleanup GPIO
        GPIO.cleanup()
        print("GPIO cleaned up.")
        # close event_file
        event_file.close()
        print("Event file closed.")
        # release camera resources
        cap.release()
        print("Camera released.")
        # close the evidence website
        http_thread.join(timeout=1.0)  # Wait for thread to terminate
        print("HTTP server stopped.")
