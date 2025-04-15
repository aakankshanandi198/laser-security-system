# Laser security system
This project detect a trespasser using a laser trip wire and captures a photograph of the trespasser while ringing the buzzer. 
The project is build using the following things:
1. Raspberry pi 500 
2. Laser emitter
3. Laser sensor
4. Buzzer
5. USB webcam
6. Miscellaneous electronics parts

## How to start the project
1. Connect to Raspberry pi via remote SSH
2. Change director to project folder : 
    <code>cd ~/Repos/laser-security-system</code>
3. Activate the python environment for the project : 
    <code>source laser-security-system/bin/activate</code>
4. Execute the main script :
    <code>python main.py</code>
5. To stop script execution hit Ctrl+C

## How to view the evidence photos
1. Determine the IP address of the Raspberry pi
    a. Connect to Raspberry pi via remote SSH
    b. Type the following command and pick the IP with starting with 192.x.x.x :
        <code>ifconfig</code>
2. Visit http://192.x.x.x:8000 to view the collected evidence

Note : The evidence website is available only when the main script is being executed.
You cannot view it when the main script's execution has been stopped. 

## How to delete old evidence/photos
1. Connect to Raspberry pi via remote SSH
2. Change directory to project's evidence folder :
    <code>cd ~/Repos/laser-security-system/evidence</code>
3. Delete all the stored photos :
    <code>rm -r \*.jpg </code>

## Running the same code on new Raspberry pi
1. Create a python environment :
    <code>python -m venv laser-security-system</code>
2. Activate the environment :
    <code>source laser-security-system/bin/activate</code>
3. Install the requirements :
    <code>pip install -r requirements.txt</code>
