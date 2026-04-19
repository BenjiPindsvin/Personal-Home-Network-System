import socket
import threading
import queue
import json
import time

class DataSender:
    devices = {}

    def __init__(self, host="0.0.0.0", port=8080):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #Make the socket

        #Connect to the port
        print("Connecting to port")
        while True:
            try:
                self.server_socket.bind((host, port)) #Try to bind to port
                break #Break out of the loop in case the bind works
            except OSError:
                print(".", end=" ", flush=True) #Print . to make it look like a loading screen
                time.sleep(2) #Sleep so it doesn't spam bind and crash the program

        self.server_socket.listen(5) #Start listening on the server for devices. There can be a maximum of 5 devices connected
        self.lock = threading.Lock() #Does some stuff to make the threads safer
        print("Connected to port")
        print(f"Server listening on {host}:{port}")
        t = threading.Thread(target=self.MainLoop, name="DataSender: MainLoop") #Create a new thread to handle devices connecting and give them each their own thread
        t.start() #Start the thread

    def MainLoop(self):
        while True:
            client_socket, address = self.server_socket.accept() #Wait for a device to connect and accept it
            print(f"Client connected from {address}")

            q1 = queue.Queue() #Create queue 1 for requests
            q2 = queue.Queue() #Create queue 2 for responses
            thread = threading.Thread(target=ClientHandler, args=(client_socket, address, q1, q2, self), name="ClientHandler: Device handler") #Create a thread for the connecting device
            thread.start() #Start the thread
        
    def MakeDevice(self, thread, socket, address, q1, q2, device_info):
        used_ids = {int(id) for id in self.devices.keys()} #Get all IDs being used

        id = 1 
        while id in used_ids: #While the current ID is being used
            id += 1 #Make the ID one larger

        self.devices[str(id)] = {"thread": thread, "socket": socket, "address": address, "queue": {"1": q1, "2": q2}, "info": device_info} #Make the device entry in the devices dict
        return str(id) #Return the ID
    
    def DisconnectDevice(self, device_id):
        q: queue.Queue = self.devices[str(device_id)]["queue"]["1"] #Get the device's queue via its ID
        q.put({"function": "closeSocket"}) #Send the close socket command

    def ListDevices(self):
        return list(self.devices.keys()) #Return all the keys of devices. A key is the name of it, like {"This is the key": {"This is the data"}}

    def SendCommand(self, device_id, function, data):
        q1: queue.Queue = self.devices[str(device_id)]["queue"]["1"] #Get the first queue for sending requests
        q2: queue.Queue = self.devices[str(device_id)]["queue"]["2"] #Get the second queue for getting responses
        
        q1.put({"function": function, "data": data}) #Send the request

        response = q2.get(timeout=5) #Try to receive the response. If there is no response after 5 seconds, it returns null
        return response #Return the response or null
    
    def GetInfo(self, device_id):
        info: dict = self.devices[str(device_id)]["info"] #Get the device's info via the given ID
        if not info: return #If there was no info because there was no device with the specified ID

        device_type = info["device_type"] #Get the device type from the info
        print(device_type) #Print it for debug/monitoring reasons
        device_command = info["device_commands"] #Get the device's commands from the info
        print(device_command) #Print it for debug/monitoring reasons

        return device_type, device_command
    
    def ThreadCheck(self): #This is mostly for debug, to check if there is a memory leak and if there are threads that aren't deleted when they should be
        threads = threading.enumerate() #Get all threads

        for t in threads: #For each thread
            print(t.name, t.ident, t.is_alive()) #Print their name, ID, and if they're alive

class ClientHandler:
    def __init__(self, client_socket: socket.SocketType, address, q1: queue.Queue, q2: queue.Queue, data_sender):
        #Save all the data for future use
        self.socket = client_socket
        self.socket.settimeout(5.0)
        self.address = address
        self.queue1 = q1
        self.queue2 = q2
        self.data_sender = data_sender
        self.info = None

        #A bunch of settings for making it work
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)

        self.socket.send(b"Connection successfull\n") #Send the client a message to indicate that the server connected successfully to the device

        
        #Receive device info
        buffer = "" #The message variable
        while True:
            try:
                chunk = self.socket.recv(512).decode() #Receive data sent by the device
                if not chunk: #If there was no data, the connection is closed
                    socket.close() #Close the socket
                    return #End the thread
                
                buffer += chunk #Add the received data to the message variable

                if '\n' in buffer: #If \n is in the message variable
                    lines = buffer.split('\n', 1) #Split the message into parts, one before \n and one after \n
                    message = lines[0] #Get the actual message from the sent data

                    try:
                        response = json.loads(buffer) #Try to parse the message as a JSON object
                        device_type = response["device_type"] #Try to get the device type from the JSON object
                        device_commands = response["commands"] #Try to get the commands from the JSON object
                        self.info = {"device_type": device_type, "device_commands": device_commands} #The device registration is valid and is stored as info
                        break #Break out of the loop
                    except (json.JSONDecodeError, KeyError): #If the device registration is invalid
                        print("Invalid device registration") #Print it for debug/monitoring reasons
                        self.socket.close() #Close the socket
                        return #End the thread

            except socket.timeout: #The device did not respond
                break #Break out of the loop
            except (ConnectionResetError, BrokenPipeError, OSError): #An error has occurred, like disconnecting from the internet
                break #Break out of the loop
        if self.info is None: #If the info is None and the device registration failed
            print("Client disconnected") #Print it for debug/monitoring reasons
            self.socket.close() #Close the socket
            return #End the thread
        self.id = self.data_sender.MakeDevice(threading.current_thread(), socket, address, q1, q2, self.info) #Create the device in the devices dict and get the device's ID
        print("Device registration complete") #Print it for debug/monitoring reasons

        thread = threading.Thread(target=self.Ping, name="ClientHandler Ping") #Create the loop that checks if the device is still connected by pings
        thread.start() #Start the thread
        self.MainLoop() #Run the MainLoop that handles all of the requests
    
    def MainLoop(self):
        while True:
            data = self.queue1.get() #Get the data that the MainLoop in DataSender sends
            if data is None: return #If the data is nothing and the queue got called accidentally

            if data.get("function") == "closeSocket": #If the function is the closeSocket function
                print("Device disconnected") #Print it for debug/monitoring reasons
                self.CloseSocket() #Close the socket
                break #Exit the loop so the thread gets closed

            self.SendCommand(data.get("function"), data.get("data")) #Send the command to the device
            response = self.ReciveData() #Receive the data
            if response is None: #If the socket timed out or another error occurred like the internet disconnecting
                print("Device disconnected") #Print it for debug/monitoring reasons
                self.CloseSocket() #Close the socket
                break #Exit the loop so the thread gets closed

            print(response) #Print the response for debug/monitoring reasons
            self.queue2.put(response) #Use the second queue to send data back to DataSender

    def CloseSocket(self):
        self.socket.close() #Close the socket
        devices: dict = self.data_sender.devices #Get the devices dict
        devices.pop(self.id, None) #Delete the device from the dict
    
    def SendCommand(self, function: str, data: dict):
        payload = json.dumps({"function": function, "data": data}).encode() #Make the payload and encode it
        self.socket.send(payload + b'\n') #Send the payload and the \n to tell the device where the message ends
    
    def ReciveData(self):
        buffer = "" #The message variable
        while True:
            try:
                chunk = self.socket.recv(512).decode() #Receive data sent by the device
                if not chunk: #If there was no data
                    return None #Return None to indicate that there is no data
                
                buffer += chunk #Add the data to the message variable
                
                if '\n' in buffer: #If \n is in the message variable
                    lines = buffer.split('\n', 1) #Split the message into parts, one before \n and one after \n
                    message = lines[0] #Get the actual message from the sent data
                    
                    try:
                        return json.loads(message) #Try to parse the data as a JSON object and return it
                    except json.JSONDecodeError:
                        print(f"Invalid JSON received: {message}") #Print it for debug/monitoring reasons
                        return None #Return None to indicate that the data was invalid
                        
            except socket.timeout: #If the socket timed out because either the device is not connected or the device doesn't send a response
                print(f"Socket timeout while reading") #Print it for debug/monitoring reasons
                return None #Return None to indicate that there is no data
            
            except (ConnectionResetError, BrokenPipeError, OSError) as e:
                print(f"Connection error: {e}") #Print it for debug/monitoring reasons
                return None #Return None to indicate that an error occurred
            
    def Ping(self):
        while True:
            time.sleep(30) #Wait 30 seconds so it doesn't flood the device with pings
            try:
                request = json.dumps({"function": "ping", "data": {}}).encode() #Create the request and encode it
                self.socket.send(request + b'\n') #Send the request and the \n to show where the message ends
                
                response = self.ReciveData() #Receive data to check if the device is connected

                if response is None: #If the device did not respond
                    print("Device disconnected - no ping response") #Print it for debug/monitoring reasons
                    self.queue1.put({"function": "closeSocket"}) #Send the close socket command
                    break #Break out of the loop that sends a ping every 30 seconds

                elif response.get("status") != "pong": #If the response is something else. It is still connected, but it's still good to note
                    print(f"Unexpected ping response: {response}") #Print it for debug/monitoring reasons

            except socket.timeout: #If the receive timed out because the device is not responding
                print("Device disconnected - ping timeout") #Print it for debug/monitoring reasons
                self.queue1.put({"function": "closeSocket"}) #Send the close socket command
                break #Break out of the loop that sends a ping every 30 seconds

            except Exception as e:
                print(f"Device disconnected during ping: {e}") #Print the error for debug/monitoring reasons
                self.queue1.put({"function": "closeSocket"}) #Send the close socket command
                break #Break out of the loop that sends a ping every 30 seconds