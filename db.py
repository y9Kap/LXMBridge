
from peewee import * # type: ignore

DATABASE = 'tmp/main.db'

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


database.create_tables([MeshtasticNode, MeshtasticMessage, LXMFUser])