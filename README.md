# LXMBridge

This script allows users to run a 'bridge' between the Meshtastic network and LXM. When running, LXM clients can send messages to the mesh and vise-versa

If the script is running, you can visit it on the nomad network here: ```06fb193ff7c307fc796251fcc66709d2:/page/index.mu```

## Features

 - Allow meshtastic nodes to send messages to any LXMF address (once established, it can be done vise-versa)
 - Allow any LXMF node to send a message to LongFast
 - Allow LXMF nodes to read LongFast messages

## Running

I didn't really intend for anyone to run my script, but if you insist:

### Hardware

1. A PC / raspberry pi to run the bridge as our host
2. A meshtastic node (eg, a Heltec V3) connected via serial / usb to the main host
3. (optional, but recommended) an rnode-compatible device on the network

### Instructions

1. Download this repo to your server ([link](git@github.com:Aveygo/LXMBridge.git))
2. Download the requirements: ```pip install meshtastic pubsub dotenv RNS LXMF better_profanity peewee git+https://github.com/Aveygo/LXMKit.git```
3. Install sqlite3 if you haven't already and create a database:
```bash
sudo apt install sqlite3
sqlite3 main.db
```
4. Create a file with the name: ```.env```, and fill in the following details:

```bash
BRIDGE_NAME = "My Epic Bridge"       # Your bridge name here
BRIDGE_SECRET = "1234567890qqwerty"  # smash your keyboard or whatever to generate a key
MESHTASTIC_REMOTE = "192.168.0.123"  # if using wifi, enter the meshtasic node's ip address
# MESHTASTIC_SERIAL = "/dev/ttyACM1" # if using usb, enter the usb port to meshtastic node
BRIDGE_LOCATION = "My beloved city" # name of location in title of the bridge
DATABASE_NAME = "main.db"            # name of local sqlite3 database
```
5. add to 'load_dotenv("example.env)' in main.py path to .env file, if his not see .enf file
6. Run ```python3 main.py``` and copy the delivery destination hash
7. Message the node (the copied hash) ```\help``` to get started.

