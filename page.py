from LXMKit.mu import *
from db import MeshtasticNode
from log_f import logger
from dotenv import load_dotenv, find_dotenv
import os

load_dotenv("bridge.env") # add your path

BRIDGE_LOCATION = os.environ.get("BRIDGE_LOCATION", "Unknown")

logo = r"""

         ________ ____  __.               __________        .__    .___              
 ___.__./   __   \    |/ _|____  ______   \______   \_______|__| __| _/ ____   ____  
<   |  |\____    /      < \__  \ \____ \   |    |  _/\_  __ \  |/ __ | / ___\_/ __ \ 
 \___  |   /    /|    |  \ / __ \|  |_> >  |    |   \ |  | \/  / /_/ |/ /_/  >  ___/ 
 / ____|  /____/ |____|__ (____  /   __/   |______  / |__|  |__\____ |\___  / \___  >
 \/                      \/    \/|__|             \/                \/_____/      \/ 

"""


def format_string(text, target_length):
    if len(text) > target_length:
        return text[:target_length-3] + "..."
    return text.ljust(target_length)

def create_canvas(primary_router, routers={}):
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
                style=[CENTER]
            )
        )

    if len(available) == 0:
        available = [
            Paragraph("No nodes loaded...")
        ]

    our_dest = str(list(primary_router.delivery_destinations.values())[0].hash.hex())

    # ---- Visible Nodes Block ----
    visible_nodes_list = []
    for node_id in routers.keys():
        node = MeshtasticNode.get_or_none(MeshtasticNode.node_id == node_id)
        if node:
            name = f"{format_string(node.long_name, 20)} ({format_string(node.short_name, 4)})"
        else:
            name = "(unknown)"
        visible_nodes_list.append(
            Paragraph(f"{node_id} : {name}", style=[CENTER])
        )
    if len(visible_nodes_list) == 0:
        visible_nodes_list = [Paragraph("No visible nodes detected...", style=[CENTER])]

    return Micron(
        subnodes=[
            Div(
                subnodes=[
                    Paragraph(logo, style=[FOREGROUND_LIGHT_GREY, CENTER]),
                    Br(),
                    Header(
                        content="What is this?",
                        subnodes=[
                            Paragraph(
                                f"This is an experimental 'bridge' between the Meshtastic network in {BRIDGE_LOCATION} and LXM. When running, LXM clients can send messages to the mesh and vise-versa. Message {our_dest} with '/help' to see more details."),
                            Br(),
                            Paragraph("Please note that development is still underway, so bugs are expected.",
                                      style=[FOREGROUND_RED]),
                            Br(),
                        ]
                    ),
                    Br(),
                    Header(
                        content="More info",
                        subnodes=[
                            Paragraph(
                                "You can read the source code (and more) here: https://github.com/y9Kap/LXMBridge"),
                            Br(),
                        ]
                    ),
                    Br(),
                    Header(
                        content="Available Nodes",
                        subnodes=[
                            Br(),
                            Paragraph(
                                "Below is a list of registered meshtastic nodes and their associated LXM addresses. By sending a message to one of these addresses, the bridge will (hopefully) relay it to that node."),
                            Br(),
                            Hr(),
                            Div(available),
                            Hr(),
                            Br(),
                        ]
                    ),
                    Br(),
                    Header(
                        content="Visible Nodes",
                        subnodes=[
                            Br(),
                            Paragraph(
                                "Below are all currently visible node IDs on the mesh:",
                                style=[CENTER]),
                            Br(),
                            Hr(),
                            Div(visible_nodes_list),
                            Hr(),
                            Br(),
                            Br(),
                        ]
                    ),
                    Br(),
                ]
            )
        ]
    )
