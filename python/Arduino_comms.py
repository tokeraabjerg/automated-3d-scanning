import socket
import time

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

            # Parse the response
            try:
                state, message = response.split(',', 1)
                state = state.strip().strip('"')
                message = message.strip().strip('"')
                
                if state.lower() == "success":
                    if "Motor A Position" in message and "Motor B Position" in message:
                        # Extract positions
                        parts = message.split(',')
                        pos_a = parts[0].split(':')[1].strip()
                        pos_b = parts[1].split(':')[1].strip()
                        print(f"Success: Motor A Position: {pos_a}, Motor B Position: {pos_b}")
                    else:
                        print(f"Success: {message}")
                elif state.lower() == "error":
                    print(f"Error: {message}")
                else:
                    print(f"Unknown state '{state}': {message}")
            except ValueError:
                print(f"Invalid response format: {response}")

            return response.strip()
        except socket.error as e:
            return f"Socket error: {e}"

def main():
    # Wait for the Arduino to initialize
    time.sleep(2)
    
    print("Arduino Ethernet Communication Initialized.")
    print("Available Commands:")
    print("  HOME                     - Home both drivers A and B")
    print("  MOVE_REL A <steps>       - Move Driver A relative steps")
    print("  MOVE_REL B <steps>       - Move Driver B relative steps")
    print("  MOVE_ABS A <position>    - Move Driver A to absolute position")
    print("  MOVE_ABS B <position>    - Move Driver B to absolute position")
    print("  GETPOS                   - Get current positions")
    
    while True:
        command = input("Enter command: ")
        if command.lower() == 'exit':
            break
        response = send_command(command)
        print(f"Response: {response}")
    
    # No need to manually close the socket as 'with' handles it

if __name__ == "__main__":
    main()