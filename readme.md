# Personal Home Network System

A system for having your own network for your devices, that make you able to control it. This service uses TCP sockets to connect to your devices, and you can control it as it was an website API.

## Info

This is a python program I made for my server, that I have decided to make public. This may not be the most efficient system, but it works fine for me.

## Requirements

- Python 3.10+
- FastAPI
- Uvicorn
- Pydantic

## Installation

1. Clone the repository:
```bash
git clone https://github.com/BenjiPindsvin/Personal-Home-Network-System.git
cd Personal-Home-Network-System
```

2. Install dependencies:
```bash
pip install fastapi uvicorn pydantic
```

3. Run the server:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

The device handler will automatically start on port 8080.

## API Endpoints

### List Devices
```bash
POST /devices
```
Returns a list of all connected device IDs.

### Send Command
```bash
POST /command
Body: {
  "device": 1,
  "function": "play_beep",
  "data": {"frequency": 1000, "duration": 500}
}
```

### Get Device Info
```bash
POST /info
Body: {
  "device": 1
}
```

### Disconnect Device
```bash
POST /disconnect
Body: {
  "device": 1
}
```

## Device Protocol

Devices connect via TCP on port 8080 (Can be changed in the config file) and communicate using JSON messages delimited by `\n`.

### Connection Flow

1. Device connects to server
2. Server sends: `Connection successfull\n`
3. Device sends registration:
```json
{"device_type": "Dummy device", "commands": ["print_data", "get_status"]}
```

### Command Format

Server to device:
```json
{"function": "print_data", "data": {"data": "Data to print on the dummy device"}}
```

Device to server (response):
```json
{"status": "success", "message": "Printed the data"}
```

## Example Python Client

See the example device code at examples/example_device.py.