import meshtastic, time, base64, json, hashlib, os
import meshtastic.tcp_interface
import meshtastic.serial_interface
import traceback
from pubsub import pub
from db import database, MeshtasticNode, VisibleMeshtasticNode, MeshtasticMessage, LXMFUser
from dotenv import load_dotenv
import threading
import time
import random
import string
import hashlib

from LXMKit.app import LXMFApp, Message, Author

import RNS, LXMF
from log_f import logger
from page import create_canvas
from cooldown import AntiSpam

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, PublicFormat, NoEncryption

from better_profanity import profanity
from fixed_interface import Injector

load_dotenv("bridge.env") # add your path

profanity.load_censor_words()

COOLDOWN = 5 # seconds
SECRET = os.environ.get("BRIDGE_SECRET", None)
BRIDGE_LOCATION = os.environ.get("BRIDGE_LOCATION", "Unknown")

assert not SECRET is None, "Secret cannot be none, missing .env file?"


class Bridge(LXMFApp):
    def __init__(self):
        LXMFApp.__init__(self, app_name=f"{BRIDGE_LOCATION} Meshtastic Bridge", storage_path="tmp")
        self.mesh = Injector(self.create_interface)
        def periodic_scan():
            while True:
                try:
                    self.scan_visible_nodes()
                except Exception as e:
                    logger.error(f"Visible nodes scan failed: {e}")
                time.sleep(60)

        threading.Thread(target=periodic_scan, daemon=True).start()

        self.routers:dict[str, LXMF.LXMRouter] = {} # meshtastic_node_id: LXMRouter
        self.build_routers()

        @self.request_handler("/page/index.mu")
        def sample(path:str, link:RNS.Link):
            return self.handleIndex(path, link)

        @self.delivery_callback
        def delivery_callback(message: Message):
            self.handleUser(message)

        logger.info('Bridge is ready')

        # Because anyone can make an identity on LXM, I would rather limit
        # the number of messages that get sent to the mesh as opposed to 
        # the other way around
        self.LXMF_global_cooldown = AntiSpam()

        self.router.enable_propagation()



    def create_interface(self):
        remote_address = os.environ.get("MESHTASTIC_REMOTE", None)
        serial_port = os.environ.get("MESHTASTIC_SERIAL", None)
        
        if remote_address:
            interface = meshtastic.tcp_interface.TCPInterface(hostname=remote_address)    
        elif serial_port:
            interface = meshtastic.serial_interface.SerialInterface(devPath=serial_port)
        else:
            interface = meshtastic.serial_interface.SerialInterface()
        
        assert hasattr(interface, "stream"), "Could not detect & open a meshtastic device via wifi or serial..."
        pub.subscribe(self.onReceive, 'meshtastic.receive')
        return interface

    def create_router_visible(self, user: VisibleMeshtasticNode):
        if user.node_id in self.routers:
            del self.routers[str(user.node_id)]

        identity = self.meshtastic_user_visible_to_identity(user)
        router = LXMF.LXMRouter(identity, storagepath=self.storage_path)

        def send_to_meshtastic_node(lxmessage: LXMF.LXMessage):
            logger.info("Received message from LXMF")
            to_node = str(user.node_id)

            content = lxmessage.content_as_string()
            message_source = lxmessage.source_hash

            assert isinstance(message_source, bytes), "bad hash"
            assert isinstance(content, str), "bad message"
            from_display_name = self.get_name(message_source)
            from_display_name = ''.join(
                c for c in from_display_name.decode('ascii', errors='ignore') if c.isprintable())

            msg = f"{from_display_name}: {content}"

            if not self.LXMF_global_cooldown.try_perform_action():
                logger.info("Blocked message due to cooldown")
                source = list(router.delivery_destinations.values())[0]
                router.announce(source.hash)
                message = Message(lxmessage, router, source, self.get_name)
                message.author.send(
                    f"Sorry, a global cooldown has been activated to prevent spam from reaching the meshtastic network. Current cooldown timer is {int(self.LXMF_global_cooldown.cooldown)} seconds")
                return

            logger.info(msg)
            self.mesh.interface.sendText(profanity.censor(msg), to_node, wantAck=True)

        router.register_delivery_callback(send_to_meshtastic_node)
        self.routers[str(user.node_id)] = router

        source = router.register_delivery_identity(
            identity,
            display_name=user.long_name
        )

        router.announce(source.hash)  # type: ignore

        logger.info(f"Ready to receive messages for {user.long_name}")

    def create_router(self, user: MeshtasticNode):
        if user.node_id in self.routers:
            del self.routers[str(user.node_id)]

        identity = self.meshtastic_user_to_identity(user)
        router = LXMF.LXMRouter(identity, storagepath=self.storage_path)

        def send_to_meshtastic_node(lxmessage: LXMF.LXMessage):
            logger.info("Received message from LXMF")
            to_node = str(user.node_id)
            
            content = lxmessage.content_as_string()
            message_source = lxmessage.source_hash

            assert isinstance(message_source, bytes), "bad hash"
            assert isinstance(content, str), "bad message"
            from_display_name = self.get_name(message_source)
            from_display_name = ''.join(c for c in from_display_name.decode('ascii', errors='ignore') if c.isprintable())

            msg = f"{from_display_name}: {content}"
            
            if not self.LXMF_global_cooldown.try_perform_action():
                logger.info("Blocked message due to cooldown")
                source = list(router.delivery_destinations.values())[0]
                router.announce(source.hash)
                message = Message(lxmessage, router, source, self.get_name)
                message.author.send(f"Sorry, a global cooldown has been activated to prevent spam from reaching the meshtastic network. Current cooldown timer is {int(self.LXMF_global_cooldown.cooldown)} seconds")
                return
            
            logger.info(msg)
            self.mesh.interface.sendText(profanity.censor(msg), to_node, wantAck=True)

        router.register_delivery_callback(send_to_meshtastic_node)
        self.routers[str(user.node_id)] = router

        source = router.register_delivery_identity(
            identity,
            display_name=user.long_name
        )

        router.announce(source.hash) # type: ignore

        logger.info(f"Ready to receive messages for {user.long_name}")



    def build_routers(self):
        for user in MeshtasticNode.select():
            self.create_router(user)

        for user in VisibleMeshtasticNode.select():
            self.create_router_visible(user)

    def handleUser(self, message:Message):
        logger.info(f'Received LXMF message: "{message.content}"')
        user = LXMFUser.get_or_none(LXMFUser.identity_hash==base64.b64encode(message.author.identity_hash))
        if user is None:
            display_name = message.author.display_name
            user = LXMFUser.create(
                identity_hash = base64.b64encode(message.author.identity_hash),
                name = "UNK" if display_name is None else display_name,
                is_subscribed = False,
                log = "{}"
            )

        log = json.loads(user.log)

        if not message.content.startswith("/"):
            message.author.send("Please type '/help' to view available commands.")

        if message.content == "/help":
            message.author.send("Commands:\n/help, shows available commands\n/listen, start receiving messages\n/stop, stop receiving messages\n/send, send a message to the public channel\n/whoami, shows user configuration")
            return
        
        if message.content == "/listen":
            user.is_subscribed = True
            user.save()
            message.author.send("Congrats! You are now listening to the public channel!")
            return

        if message.content == "/stop":
            user.is_subscribed = False
            user.save()
            message.author.send("Stopped sharing the public channel!")
            return
        
        if message.content == "/whoami":
            message.author.send(f"You are '{user.name}'.\nYou are {'not ' if not user.is_subscribed else ''}subscribed")
            return
        
        if message.content.startswith("/send "):

            if not self.LXMF_global_cooldown.try_perform_action():
                message.author.send(f"Sorry, a global cooldown has been activated to prevent spam from reaching the meshtastic network. Current cooldown timer is {int(self.LXMF_global_cooldown.cooldown)} seconds")
                return

            if user.name == "UNK":
                message.author.send("Sorry, to prevent spam, we need your RNS identity first.\nYou can try announcing it, but it may take a while for it to propagate through the network...")
            else:
                msg = message.content.split("/send ")[1]
                msg = f"{message.author.display_name}: {msg}"
                self.mesh.interface.sendText(profanity.censor(msg), wantAck=True)
                message.author.send("Your message has been sent!")
            
            return

    def handleIndex(self, path:str, link:RNS.Link):
        try:
            return create_canvas(self.router, self.routers).render().encode("utf-8")
        except Exception as e:
            print(traceback.format_exc())
            logger.warning(f"Could not serve page: {e}")
            return "Sorry, but an internal server error occurred...".encode("utf-8")

    def handle_meshtastic_message(self, user:MeshtasticNode, message:str, from_id:str):
        if not message.startswith("/"):
            self.mesh.interface.sendText('Hi!\nThis is a bridge node for LXMF.\nType /info or /help for more information', from_id, wantAck=True)
            return

        if message.startswith("/info"):
            self.mesh.interface.sendText('This bot was made to allow meshtastic users to send LXMF messages; which is kind of like an email system for nerds.', from_id, wantAck=True)

        if message.startswith("/help"):
            self.mesh.interface.sendText('Commands:\n/register <base32 key>, load an existing identity\n/deregister, remove identity\n/send <LXMF id> <message>, send a message to a node', from_id, wantAck=True)

        if message.startswith("/register"):
            try:
                key = message.split("/register")[1]
                print(f'{key}')
                identity = RNS.Identity.from_bytes(base64.b32decode(key[:128]))
            except:
                self.mesh.interface.sendText('Sorry, your provided identity could not be loaded.', from_id, wantAck=True)
                return

            user.lxmf_identity = identity # type: ignore
            user.save()

            self.mesh.interface.sendText('Successfully loaded your identity!', from_id, wantAck=True)
            return

        if message.startswith("/deregister"):
            if user.lxmf_identity is None:
                self.mesh.interface.sendText('No identity to deregister!', from_id, wantAck=True)
                return

        if message.startswith("/send"):

            try:
                command, dst_node, to_send = message.split(" ")[0], message.split(" ")[1], " ".join(message.split(" ")[2:])
            except:
                self.mesh.interface.sendText('Invalid command structure, please see /help.', from_id, wantAck=True)
                return

            if dst_node == self.source.hash.hex(): # type: ignore
                self.mesh.interface.sendText('https://imgflip.com/i/7ogz7h', from_id, wantAck=True)
                return

            identity = self.meshtastic_user_to_identity(user)
            router = self.routers.get(str(user.node_id), None)
            if router is None:
                self.mesh.interface.sendText('Your router does not exist?', from_id, wantAck=True)
                return

            #to_send = f"[MTS -> LXMF] {user.long_name}: {to_send}" # A little verbose

            destination = RNS.Destination(
                RNS.Identity.recall(bytes.fromhex(dst_node)),
                RNS.Destination.OUT,
                RNS.Destination.SINGLE,
                "lxmf",
                "delivery"
            )

            # A bit hacky
            source = list(router.delivery_destinations.values())[0]
            router.announce(source.hash)

            lxm = LXMF.LXMessage(
                destination,
                source,
                profanity.censor(to_send),
                desired_method=LXMF.LXMessage.OPPORTUNISTIC,
                include_ticket=True
            )
            router.handle_outbound(lxm)

            self.mesh.interface.sendText('Sent!', from_id, wantAck=True)

    def scan_visible_nodes(self):
        try:
            interface = self.mesh.interface
            assert isinstance(interface.nodes, dict), "interface.nodes not loaded"

            my_node_info = interface.getMyNodeInfo()
            my_node_id = my_node_info.get("user", {}).get("id", None)

            updated_count = 0

            for node_id, node_info in interface.nodes.items():
                if node_id == my_node_id:
                    continue

                last_heard = node_info.get("lastHeard")
                user_info = node_info.get("user")

                if last_heard is None:
                    last_heard = 0

                if user_info is None:
                    continue

                long_name = user_info.get("longName", "UnknownLongName")
                short_name = user_info.get("shortName", "UnknownShortName")

                prv_bytes = os.urandom(64)
                node_public_key = base64.b32encode(prv_bytes).decode()
                logger.info(f'{node_public_key}')

                visible_node = VisibleMeshtasticNode.get_or_none(node_id=user_info["id"])

                if visible_node is None:
                    visible_node = VisibleMeshtasticNode.create(
                        node_id=user_info["id"],
                        long_name=long_name,
                        short_name=short_name,
                        last_seen=last_heard,
                        public_key=node_public_key,
                        lxmf_identity=None
                    )
                else:
                    visible_node.long_name = long_name
                    visible_node.short_name = short_name
                    visible_node.last_seen = last_heard
                    visible_node.public_key = node_public_key
                    visible_node.save()

                if visible_node.lxmf_identity is None:
                    visible_node.lxmf_identity = RNS.Identity.from_bytes(base64.b32decode(str(node_public_key)))
                    visible_node.save()
                    logger.info(f"Issued LXMF identity for visible node: {long_name}")

                updated_count += 1

            logger.info(f"Scanned and updated {updated_count} visible nodes")

        except Exception as e:
            logger.error(f"Error during visible nodes scan: {node_public_key}")

    def meshtastic_user_to_identity(self, user: MeshtasticNode):
        if user.node_id in self.routers:
            return self.routers[str(user.node_id)].identity

        if user.lxmf_identity is None:
            logger.info("Building user identity from public key")
            return self.meshtastic_public_to_identity(str(user.public_key))
        else:
            logger.info("Building user identity from custom identity")
            return RNS.Identity.from_bytes(base64.b32decode(str(user.lxmf_identity)))

    def meshtastic_user_visible_to_identity(self, user: VisibleMeshtasticNode):
        if user.node_id in self.routers:
            return self.routers[str(user.node_id)].identity

        if user.lxmf_identity is None:
            logger.info("Building user identity from public key")
            return self.meshtastic_public_to_identity(str(user.public_key))
        else:
            logger.info("Building user identity from custom identity")
            return RNS.Identity.from_bytes(base64.b32decode(str(user.lxmf_identity)))

    def create_keys(self, seed: bytes):
        assert len(seed) == 32, f"Seed must be 32 bytes, got {len(seed)}"

        self.prv = X25519PrivateKey.from_private_bytes(seed)
        self.prv_bytes = self.prv.private_bytes(
            encoding=Encoding.Raw,
            format=PrivateFormat.Raw,
            encryption_algorithm=NoEncryption()
        )

        self.sig_prv = Ed25519PrivateKey.from_private_bytes(seed)
        self.sig_prv_bytes = self.sig_prv.private_bytes(
            encoding=Encoding.Raw,
            format=PrivateFormat.Raw,
            encryption_algorithm=NoEncryption()
        )

        return self.prv_bytes+self.sig_prv_bytes

    def meshtastic_public_to_identity(self, public_key:str):
        return RNS.Identity.from_bytes(self.create_keys(hashlib.sha256((public_key + str(SECRET)).encode("utf-8")).digest()))

    def onReceive(self, packet, interface:meshtastic.tcp_interface.TCPInterface):
        assert isinstance(interface.nodes, dict), "interface nodes not loaded?"
        raw_node = interface.nodes.get(packet["fromId"], None)
        if raw_node is None:
            return
        
        if not ('decoded' in packet and packet['decoded']['portnum'] == 'TEXT_MESSAGE_APP'):
            return
        
        # If we found ourself in the public channel
        out_node_info = interface.getMyNodeInfo()
        out_nodes = interface.nodes
        logger.info(out_nodes)

        if not isinstance(out_node_info, dict):
            logger.warning("Node info was none, broken pipe?")
            return

        our_node_id = out_node_info.get("user", {}).get("id", None)

        if our_node_id is None or packet["fromId"] == our_node_id:
            return
        
        mesh_node:MeshtasticNode = MeshtasticNode.get_or_none(MeshtasticNode.node_id==raw_node["user"]["id"])
        if mesh_node is None:
            mesh_node = MeshtasticNode.create(
                node_id = raw_node["user"]["id"],
                long_name = raw_node["user"]["longName"],
                short_name = raw_node["user"]["shortName"],
                last_seen = int(time.time()),
                public_key = raw_node["user"]["publicKey"],
                lxmf_identity = None
            )
        else:
            # Update the names in the event that the node updated them
            mesh_node.long_name = raw_node["user"]["longName"]
            mesh_node.short_name = raw_node["user"]["shortName"]
            mesh_node.last_seen = int(time.time()) # type: ignore
            mesh_node.public_key = raw_node["user"]["publicKey"]
            logger.info(f'{raw_node["user"]["publicKey"]}')
            mesh_node.save()

        message_bytes = packet['decoded']['payload']
        try:
            message_string:str = message_bytes.decode('utf-8')
        except:
            return
        
        logger.info(f'Received meshtastic message: "{message_string}"')
    
        MeshtasticMessage.create(
            author = mesh_node,
            content = message_string,
            received = int(time.time())
        )

        if not packet["toId"] == meshtastic.BROADCAST_ADDR:
            if packet["toId"] == our_node_id:
                self.handle_meshtastic_message(mesh_node, message_string, packet["fromId"])
            return
        
        if "@brdg" in message_string.lower():
            interface.sendText('Hi! This is an automated response because you mentioned me.\nPlease DM me with "/info" if you want to know what I do.', packet["toId"], wantAck=True)
        
        count = LXMFUser.select().where(LXMFUser.is_subscribed==True).count()
        logger.info(f'Alerting {count} LXMF users of the incoming message...')

        assert isinstance(self.source, RNS.Destination), "source not loaded"

        for lxmf_user in LXMFUser.select():
            lxmf_user: LXMFUser

            if lxmf_user.is_subscribed:
                dest = Author(
                    base64.b64decode(str(lxmf_user.identity_hash)), 
                    self.router, 
                    self.source
                )

                dest.send(f"{raw_node['user']['longName']}: {profanity.censor(message_string)}")

        logger.info(f'Done')

if __name__ == "__main__":
    Bridge().run()
