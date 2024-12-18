import socket
import time
import json  
import os     

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

def interpret_command(positions):
    """
    Args:
        positions (list or dict): A list of dictionaries or a single dictionary specifying the positions to move the motors.
            Each dictionary can have the following keys:
                - 'home' (bool): If True, the motors will be homed.
                - 'pos_a' (int or float): The absolute position to move motor A.
                - 'pos_b' (int or float): The absolute position to move motor B.
    Returns:
        str: "success" if all commands are executed successfully, otherwise an error message.
    Raises:
        Exception: If an error occurs during the scan.
    Example:
        positions = [
            {'home': True},
            {'pos_a': 10, 'pos_b': 20},
            {'pos_a': 30, 'pos_b': 40}
        ]
        result = interpret_command(positions)
    """
    try:
        if not isinstance(positions, list):
            positions = [positions]  # Ensure positions is a list

        for entry in positions:
            if isinstance(entry, dict) and 'home' in entry and entry['home']:
                response_home = send_command("HOME")
                print(f"Homing: {response_home}")
                if "success" not in response_home.lower():
                    print("Error homing. Aborting scan.")
                    return "Error homing"
                continue  # Skip to the next entry after homing

            if 'pos_a' in entry and 'pos_b' in entry:
                pos_a = entry['pos_a']
                pos_b = entry['pos_b']
                command_a = f"MOVE_ABS A {pos_a}"
                command_b = f"MOVE_ABS B {pos_b}"
                
                response_a = send_command(command_a)
                print(f"Motor A: {response_a}")
                if "success" not in response_a.lower():
                    print("Error moving Motor A. Aborting scan.")
                    return "Error moving Motor A"
                
                response_b = send_command(command_b)
                print(f"Motor B: {response_b}")
                if "success" not in response_b.lower():
                    print("Error moving Motor B. Aborting scan.")
                    return "Error moving Motor B"
            
            time.sleep(0.5)  # Wait for 0.5 seconds between positions
        return "success"
    except Exception as e:
        print(f"Error during scan: {e}")
        return f"Error during scan: {e}"

def test():
    """
    Test function to send a test position to interpret_command.
    """
    test_position = {
        "pos_a": 2716,
        "pos_b": 619,
        "deg_a": 0,
        "deg_b": 90
    }
    interpret_command(test_position)

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
    print("  START                    - Move to starting position")
    while True:
        command = input("Enter command: ")
        if command.lower() == 'exit':
            break
        elif command.upper() == 'START':
            test()
        elif command.upper() == 'PERFORM_SCAN':
            interpret_command()
        elif command.upper() == 'START_HOME_LOOP':
            response = send_command("HOME_LOOP")
            print(f"Response: {response}")
        elif command.upper() == 'STOP_HOME_LOOP':
            response = send_command("HOME_LOOP")
            print(f"Response: {response}")
        else:
            response = send_command(command)
            print(f"Response: {response}")
    

if __name__ == "__main__":
    main()