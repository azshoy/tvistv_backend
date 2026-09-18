import datetime

from .db import db
from peewee import Model, CharField, IntegerField, BooleanField, DateTimeField, ForeignKeyField, FloatField




class BaseModel(Model):
    class Meta:
        database = db
    created = DateTimeField(default=datetime.datetime.now)
    modified = DateTimeField(default=datetime.datetime.now)
    created_by = CharField(default="unknown")
    modified_by = CharField(default="nobody")
    def defaults_dict(self):
        return {
            "created": self.created,
            "created_by": self.created_by,
            "modified": self.modified,
            "modified_by": self.modified_by
            }

    def save(self, *args, **kwargs):
        self.modified = datetime.datetime.now()
        return super(BaseModel, self).save(*args, **kwargs)

    def update_with_dict(self, data, is_new=False,non_updatable_keys=None):
        if non_updatable_keys is None:
            non_updatable_keys = []
        if "author" in data:
            if is_new:
                self.created_by = data["author"]
            else:
                self.modified_by = data["author"]
                self.modified = datetime.datetime.now()
        for k in data.keys():
            if k in non_updatable_keys or k in ["id", "created", "modified", "author", "created_by", "modified_by"]:
                continue
            if hasattr(self, k):
                setattr(self, k, data[k])
        self.save()


class Image(BaseModel):
    id = IntegerField(primary_key=True)
    url = CharField()
    hidden = BooleanField(default=False)
    def as_a_dict(self):
        return {
            "id": self.id,
            "url": self.url,
            "hidden": self.hidden,
            **self.defaults_dict()
        }
    def update_with_dict(self, data, is_new=False, _non_updatable_keys=None):
        return super(Image, self).update_with_dict(data, is_new, ["url"])


class TextBoxContainer(BaseModel):
    id = CharField(primary_key=True)
    header = CharField()

class BoxContent(BaseModel):
    id = CharField(primary_key=True)
    css_class = CharField(default="")
    header = CharField(default="")
    page = IntegerField(default=0)
    box = CharField(default="")
    order = IntegerField(default=0)
    content_type = CharField(default="none")

class BoxText(BoxContent):
    text = CharField(default="")
    content_type = CharField(default="text")

    def update_with_dict(self, data, is_new=False, _non_updatable_keys=None):
        return super(BoxText, self).update_with_dict(data, is_new, ["content_type"])

    def as_a_dict(self):
        return {
            "id": self.id,
            "header": self.header,
            "page": self.page,
            "box": self.box,
            "text": self.text,
            "css_class": self.css_class,
            "order": self.order,
            **self.defaults_dict()
        }


class BoxIframe(BoxContent):
    url = CharField()
    width = IntegerField(default=-1)
    height = IntegerField(default=-1)
    content_type = CharField(default="iframe")

    def update_with_dict(self, data, is_new=False, _non_updatable_keys=None):
        return super(BoxIframe, self).update_with_dict(data, is_new, ["content_type"])

    def as_a_dict(self):
        return {
            "id": self.id,
            "header": self.header,
            "page": self.page,
            "box": self.box,
            "url": self.url,
            "width": self.width,
            "height": self.height,
            "css_class": self.css_class,
            "order": self.order,
            "styles": self.get_styles_as_dict(),
            **self.defaults_dict()
        }
    def get_styles_as_dict(self):
        styles = Style.select().where(Style.target == self.id)
        d = {}
        for style in styles:
            d[style.property] = style.value
        return d

    def delete(self):
        Style.delete().where(Style.target == self.id)
        return super(BoxIframe, self).delete()


class Style(BaseModel):
    id = CharField(primary_key=True)
    property = CharField()
    value = CharField()
    target = CharField()

keyValueTypes = ["none", "str", "int", "float", "bool"]

class KeyValue(BaseModel):
    key = CharField(primary_key=True)
    value_type = CharField(default="str")
    value = CharField(default="none")
    def update_with_dict(self, _d=None, d=None, _n=None):
        return None
    def as_a_dict(self):
        value = self.value_as_type()
        return {"key": self.key, "value": value, "value_type": self.value_type}

    def value_as_type(self):
        value = self.value
        if self.value_type == "int":
            value = int(value)
        if self.value_type == "float":
            value = float(value)
        if self.value_type == "bool":
            value = bool(value)
        if self.value_type == "date":
            datetime.datetime.fromisoformat(value)
        return value


def key_value_type_by_value_type(value):
    if isinstance(value, datetime.datetime):
        return "date"
    if isinstance(value, str):
        return "str"
    if isinstance(value, float):
        return "float"
    if isinstance(value, int):
        return "int"
    if isinstance(value, bool):
        return "bool"
    return None

def create_new_key_value(key, value, author="unknown"):
    if KeyValue.select().where(key==key).exists():
        return None
    if datetime_valid(value):
        value = datetime.datetime.fromisoformat(value)
    v_type = key_value_type_by_value_type(value)
    if v_type:
        return KeyValue.create(key=key, value=str(value), value_type=v_type, created_by=author)
    return None

def update_key_value(key, value, author="unknown"):
    if datetime_valid(value):
        value = datetime.datetime.fromisoformat(value)
    v_type = key_value_type_by_value_type(value)
    if not author:
        author = "unknown"
    if v_type:
        KeyValue.update({KeyValue.value: str(value), KeyValue.value_type: v_type, KeyValue.modified_by: author, KeyValue.modified: datetime.datetime.now()}).where(KeyValue.key == key)
        return KeyValue.get(KeyValue.key == key)
    return None


def datetime_valid(dt_str):
    try:
        datetime.datetime.fromisoformat(dt_str)
    except:
        return False
    return True


def key_values_as_a_dict():
    d = {}
    kvs = KeyValue.select()
    for kv in kvs:
        d[kv.key] = kv.value_as_type()
    return d

def as_a_dict(obj):
    if isinstance(obj, list):
        l = []
        for o in obj:
            l.append(o.as_a_dict())
        return l
    return obj.as_a_dict()
