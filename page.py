from LXMKit.mu import *
from db import MeshtasticNode, VisibleMeshtasticNode
from log_f import logger
from dotenv import load_dotenv, find_dotenv
import os
import time

load_dotenv("bridge.env") # add your path

BRIDGE_LOCATION = os.environ.get("BRIDGE_LOCATION", "Unknown")

logo = r"""

            Y9KAP SAINT-PETERSBURG BRIDGE

"""


def format_string(text, target_length):
    if len(text) > target_length:
        return text[:target_length-3] + "..."
    return text.ljust(target_length)

def create_canvas(primary_router, routers={}):
    now = int(time.time())
    ONLINE_THRESHOLD = 60 * 60 * 3 # hours
    cutoff = now - ONLINE_THRESHOLD

    available = []
    for node_id, router in routers.items():
        node = MeshtasticNode.get_or_none(MeshtasticNode.node_id == node_id)
        if node is None:
            continue

        name = f"{node.long_name} ({node.short_name})"
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

    # ---- Visible Nodes Block using VisibleMeshtasticNode ----
    online_nodes = VisibleMeshtasticNode.select().where(
        VisibleMeshtasticNode.last_seen >= cutoff
    )

    visible_nodes_list = []
    for node in online_nodes:
        name = f"{format_string(node.long_name, 20)} ({format_string(node.short_name, 4)})"

        seconds_ago = now - node.last_seen
        if seconds_ago < 0:
            seconds_ago = 0  # на случай кривого времени в БД

        hours = seconds_ago // 3600
        minutes = (seconds_ago % 3600) // 60
        last_seen_str = f"{hours} h {minutes} m ago"

        router = routers.get(node.node_id)
        if router:
            dst = str(list(router.delivery_destinations.values())[0].hash.hex())
        else:
            dst = "N/A"

        visible_nodes_list.append(
            Paragraph(f"{name} : {last_seen_str} : {dst}", style=[CENTER])
        )

    if len(visible_nodes_list) == 0:
        visible_nodes_list = [Paragraph("No visible nodes detected...", style=[CENTER])]

    # ---- Return Canvas ----
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
                                f"This is an experimental 'bridge' between the Meshtastic network in {BRIDGE_LOCATION} "
                                f"and LXM. When running, LXM clients can send messages to the mesh and vise-versa. "
                                f"Message {our_dest} with '/help' to see more details."
                            ),
                            Br(),
                            Paragraph(
                                "Please note that development is still underway, so bugs are expected.",
                                style=[FOREGROUND_RED]
                            ),
                            Br(),
                        ]
                    ),
                    Br(),
                    Header(
                        content="More info",
                        subnodes=[
                            Paragraph(
                                "You can read the source code (and more) here: https://github.com/y9Kap/LXMBridge"
                            ),
                            Br(),
                        ]
                    ),
                    Br(),
                    Header(
                        content="Available Nodes",
                        subnodes=[
                            Br(),
                            Paragraph(
                                "Below is a list of registered meshtastic nodes and their associated LXM addresses. "
                                "By sending a message to one of these addresses, the bridge will (hopefully) relay it to that node."
                            ),
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
                                f"Below are all currently visible node IDs on the mesh in {ONLINE_THRESHOLD / 3600} hour:",
                                style=[CENTER]
                            ),
                            Br(),
                            Hr(),
                            Div(visible_nodes_list),
                            Hr(),
                            Br(),
                            Br(),
                        ]
                    ),
                    Br(),
                    Header(
                        "Login Form Example",
                        [
                            Div([
                                Br(),
                                Span([Paragraph("Username: "),
                                      Input("name", "Anonymous", 16, style=[BACKGROUND_DARK_GREY])]),
                                Span([Paragraph("Password: "),
                                      Input("pass", "password123", 16, style=[BACKGROUND_DARK_GREY])]),
                                Br(),
                                Anchor("   Submit   ", href=None, style=[BACKGROUND_DARK_GREY]),
                                Br(),
                            ], style=[BACKGROUND_DARKER_GREY, CENTER])
                        ]
                    )
                ]
            )
        ]
    )
