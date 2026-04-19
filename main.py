import fastapi
from fastapi import HTTPException
import devicehandler
from pydantic import BaseModel
from typing import Any

thing = devicehandler.DataSender()
app = fastapi.FastAPI()

#Forms
class DisconnectForm(BaseModel):
    device: int

class CommandForm(BaseModel):
    device: int
    function: str
    data: dict[str, Any] | None = None

class InfoForm(BaseModel):
    device: int

#Endpoints
@app.post("/devices")
def devices(): #List all connected devices
    return thing.ListDevices() #Return the client a list of every device's ID

@app.post("/disconnect")
def device(body: DisconnectForm): #Disconnect a specific device
    try:
        thing.DisconnectDevice(body.device) #Disconnect the device
    except:
        raise HTTPException(500, detail="There is no device with the specified ID") #Return 500 because there is no device with that ID
    return

@app.post("/command")
def send_command(body: CommandForm): #Send a command to a specific device
    try:
        response = thing.SendCommand(body.device, body.function, body.data) #Send the command and get the response
        return response #Return the response to the client
    except:
        raise HTTPException(500, detail="There is no device with the specified ID") #Return 500 because there is no device with that ID, or a device with that ID was detected to be disconnected when running the command

@app.post("/info")
def get_info(body: InfoForm): #Get info about a specific device
    try:
        type, commands = thing.GetInfo(body.device) #Get the device's type and commands
        return {"device_type": type, "device_commands": commands} #Return them to the client
    except Exception as e:
        raise HTTPException(500, detail="There is no device with the specified ID") #Return 500 because there is no device with that ID

@app.post("/threads")
def threads_test(): #This is mostly for debug, to check if there is a memory leak and if there are threads that aren't deleted when they should be
    thing.ThreadCheck() #Run the thread check
    return 1 #Return anything, it doesn't really matter