import datetime
from .db import db
from .model import Image, TextBoxContainer, BoxText, BoxIframe, KeyValue, create_new_key_value


def init_database():
    db.connect()
    db.create_tables([Image, TextBoxContainer, BoxText, BoxIframe, KeyValue])
    TextBoxContainer.get_or_create(id="mainBox", defaults={"header": "Potentially relevant information:"})
    TextBoxContainer.get_or_create(id="secondaryBox", defaults={"header": "Add something here"})
    create_new_key_value("perttiStuck", datetime.datetime(2026, 1,1), "database_init")



def config_to_db(cfg):
    for key in cfg.keys():
        create_new_key_value(key, cfg[key])
