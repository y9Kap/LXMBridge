import  os
from peewee import * # type: ignore
from dotenv import load_dotenv
from log_f import logger

load_dotenv("example.env") # add your path

DATABASE_NAME = os.environ.get("DATABASE_NAME", None)

DATABASE = f'{DATABASE_NAME}'

database = SqliteDatabase(DATABASE)

class BaseModel(Model):
    class Meta:
        database = database

class MeshtasticNode(BaseModel):
    node_id = CharField(unique=True)
    long_name = CharField()
    short_name = CharField()
    last_seen = IntegerField()
    public_key = CharField()
    lxmf_identity = TextField(null=True)

class VisibleMeshtasticNode(BaseModel):
    node_id = CharField(unique=True)
    long_name = CharField()
    short_name = CharField()
    last_seen = IntegerField()
    public_key = CharField()
    lxmf_identity = TextField(null=True)

class MeshtasticMessage(BaseModel):
    message_id = IntegerField(primary_key=True)
    author = ForeignKeyField(MeshtasticNode, backref='messages')
    content = CharField()
    received = IntegerField()

class LXMFUser(BaseModel):
    identity_hash = CharField(unique=True)
    name = CharField()
    is_subscribed = BooleanField()
    log = TextField()



database.create_tables([MeshtasticNode, VisibleMeshtasticNode, MeshtasticMessage, LXMFUser])
logger.info(f'tables was created')