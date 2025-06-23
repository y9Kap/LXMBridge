from LXMKit.mu import *
from db import MeshtasticNode
from log_f import logger
from dotenv import load_dotenv, find_dotenv
import os

find_dotenv()
load_dotenv("example.env") # add your path


BRIDGE_LOCATION = os.environ.get("BRIDGE_LOCATION", "Unknown")


logo = r"""
    ___                              _          ____       _     __         
   /   |_   _____  __  ______ _____ ( )_____   / __ )_____(_)___/ /___ ____ 
  / /| | | / / _ \\/ / / / __ '/ __ \\|// ___/  / __  / ___/ / __  / __ '/ _ \\
 / ___ | |/ /  __/ /_/ / /_/ / /_/ / (__  )  / /_/ / /  / / /_/ / /_/ /  __/
/_/  |_|___/\\___/\\__, /\\__, /\\____/ /____/  /_____/_/  /_/\\__,_/\\__, /\___/ 
                /____//____/                                   /____/       
"""


def format_string(text, target_length):
    if len(text) > target_length:
        return text[:target_length-3] + "..."
    return text.ljust(target_length)

def create_canvas(primary_router, routers=[]):
    
    available = []
    for node_id, router in routers.items():
        logger.info(node_id)

        node = MeshtasticNode.get_or_none(MeshtasticNode.node_id == node_id)

        if node is None:
            logger.info("Meshtastic node is none")
            continue

        name = f"{format_string(node.long_name, 25)} ({format_string(node.short_name, 4)})"
        dst = str(list(router.delivery_destinations.values())[0].hash.hex())

        available.append(
            Span(
                [
                    Paragraph(name),
                    Paragraph(" : "),
                    Paragraph(dst)
                ],
                style = [CENTER]
            )
        )
    
    if len(available) == 0:
        available = [
            Paragraph("No nodes loaded...")
        ]

    our_dest = str(list(primary_router.delivery_destinations.values())[0].hash.hex())

    return Micron(
        subnodes=[
            Div(
                subnodes = [
                    Paragraph(logo, style=[FOREGROUND_LIGHT_GREY, CENTER]),
                    Br(),
                    Header(
                        content="What is this?",
                        subnodes=[
                            Paragraph(f"This is an experimental 'bridge' between the Meshtastic network in {BRIDGE_LOCATION} and LXM. When running, LXM clients can send messages to the mesh and vise-versa. Message {our_dest} with '/help' to see more details."),
                            Br(),
                            Paragraph("Please note that development is still underway, so bugs are expected.", style=[FOREGROUND_RED]),
                            Br(),
                        ]
                    ),
                    Br(),
                    Header(
                        content="More info",
                        subnodes=[
                            Paragraph("You can read the source code (and more) here: https://github.com/Aveygo/LXMBridge"),
                            Br(),
                        ]
                    ),
                    Br(),
                    Header(
                        content = "Available Nodes",
                        subnodes = [
                            Br(),
                            Paragraph("Below is a list of registered meshtastic nodes and their associated LXM addresses. By sending a message to to one of these addresses, the bridge will (hopefully) relay it to that node."),
                            Br(),
                            Hr(),
                            Div(
                                available
                            ),
                            Hr(),
                            Br(),
                            Br(),
                            Br(),   
                        ]
                    )

                ]
            )
        ]
    )

        