import socket
import json
import threading

class TestDevice:
    def __init__(self, host="127.0.0.1", port=8080):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((host, port))
        print(f"Connected to {host}:{port}")
        
        # Receive connection confirmation FIRST
        confirmation = self.socket.recv(1024).decode()
        print(f"Server says: {confirmation.strip()}")
        
        # Send device info with \n delimiter
        device_info = {
            "device_type": "test_device",
            "commands": ["print_data", "get_status"]
        }
        message = json.dumps(device_info) + '\n'
        self.socket.send(message.encode())
        print(f"Sent device info: {device_info}")
        
        # Start listening for commands
        thread = threading.Thread(target=self.listen_for_commands)
        thread.daemon = True
        thread.start()
    
    def listen_for_commands(self):
        buffer = ""
        while True:
            try:
                chunk = self.socket.recv(1024).decode()
                if not chunk:
                    print("Connection disconnected")
                    break
                
                buffer += chunk
                
                # Process all complete messages (separated by \n)
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    
                    if not line.strip():
                        continue
                    
                    command = json.loads(line)
                    print(f"Received command: {command}")
                    
                    # Simple command handler
                    function = command.get("function")
                    cmd_data = command.get("data", {})
                    
                    if function == "print_data":
                        print(f"Data to print: {cmd_data}")
                        response = {"status": "success", "message": "Printed the data"}
                    elif function == "get_status":
                        response = {"status": "success", "message": "Device is running"}
                    elif function == "ping":
                        response = {"status": "pong"}
                    else:
                        response = {"status": "error", "message": "Unknown command"}
                    
                    # Send response back with \n delimiter
                    response_msg = json.dumps(response) + '\n'
                    self.socket.send(response_msg.encode())
                    print(f"Sent response: {response}")
                    
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                response = {"status": "error", "message": "Invalid JSON"}
                self.socket.send((json.dumps(response) + '\n').encode())
            except Exception as e:
                print(f"Error: {e}")
                break

if __name__ == "__main__":
    device = TestDevice()
    print("Device running... (Ctrl+C to stop)")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("\nDevice stopped")