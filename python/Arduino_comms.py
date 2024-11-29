import socket
import time
import json  # Add this line
import os     # Add this line

# Configure the Ethernet connection
arduino_ip = '192.168.100.115'  # Change this to your Arduino's IP address
arduino_port = 80  # Change this to your Arduino's port if different
buffer_size = 1024

def send_command(command):
    """
    Send a command to the Arduino and print the response.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(20)  # Set timeout to 20 seconds
        try:
            sock.connect((arduino_ip, arduino_port))
            sock.sendall((command + '\n').encode())  # Send the command
            response = ""
            while True:
                try:
                    part = sock.recv(buffer_size).decode().strip()  # Read the response
                    if not part:
                        break
                    response += part + "\n"
                except socket.timeout:
                    break
            return response.strip()
        except socket.error as e:
            return f"Socket error: {e}"

def perform_scan():
    """
    Perform a scan by reading positions from positions.json and moving motors.
    """
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))  # Add this line
        positions_path = os.path.join(script_dir, 'positions.json')  # Add this line
        with open(positions_path, 'r') as file:  # Modify this line
            positions = json.load(file)  # Load JSON data
        
        for entry in positions:
            pos_a = entry['pos_a']
            pos_b = entry['pos_b']
            command_a = f"MOVE_ABS A {pos_a}"
            command_b = f"MOVE_ABS B {pos_b}"
            
            response_a = send_command(command_a)
            print(f"Motor A: {response_a}")
            
            response_b = send_command(command_b)
            print(f"Motor B: {response_b}")
            
            time.sleep(1)  # Wait for 1 seconds between positions
        print("Scan complete.")
    except Exception as e:
        print(f"Error during scan: {e}")

def main():
    # Wait for the Arduino to initialize
    time.sleep(2)
    
    print("Arduino Ethernet Communication Initialized.")
    print("Available Commands:")
    print("  HOME                     - Home both drivers A and B")
    print("  HOME_LOOP                - Home both drivers A and B, loops continuously until STOP_HOME_LOOP is sent")
    print("  MOVE_REL A <steps>       - Move Driver A relative steps")
    print("  MOVE_REL B <steps>       - Move Driver B relative steps")
    print("  MOVE_ABS A <position>    - Move Driver A to absolute position")
    print("  MOVE_ABS B <position>    - Move Driver B to absolute position")
    print("  GETPOS                   - Get current positions")
    print("  PERFORM_SCAN             - Perform scan with predefined positions")
    while True:
        command = input("Enter command: ")
        if command.lower() == 'exit':
            break
        elif command.upper() == 'PERFORM_SCAN':
            perform_scan()
        elif command.upper() == 'START_HOME_LOOP':
            response = send_command("HOME_LOOP")
            print(f"Response: {response}")
        elif command.upper() == 'STOP_HOME_LOOP':
            response = send_command("HOME_LOOP")
            print(f"Response: {response}")
        else:
            response = send_command(command)
            print(f"Response: {response}")
    
    # No need to manually close the socket as 'with' handles it

if __name__ == "__main__":
    main()