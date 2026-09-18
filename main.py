import datetime
import random
import sys

from flask import Flask, jsonify, request, g
from database.database import init_database, config_to_db
from flask_cors import CORS

from flask_basicauth import BasicAuth

import configparser

from database.model import BoxContent, BoxText, BoxIframe, Image, KeyValue, key_values_as_a_dict, create_new_key_value, update_key_value, as_a_dict

CFG_FILE_NAME = './config.ini'
config_file = configparser.ConfigParser()
config_file.read(CFG_FILE_NAME)

config_file.sections()

app = Flask(__name__)

cors = CORS(app) # allow CORS for all domains on all routes.
app.config['CORS_HEADERS'] = 'Content-Type'
app.config['BASIC_AUTH_USERNAME'] = config_file["CONF"]["API_USER"]
app.config['BASIC_AUTH_PASSWORD'] = config_file["CONF"]["API_KEY"]



init_database()
if "DATA" in config_file:
    config_to_db(config_file["DATA"])

basic_auth = BasicAuth(app)
@app.route('/', methods=['GET'])
def home():
    return "Moro t. luuranki"


@app.route('/content', methods=['GET'])
def get_content():
    res = {"text": [], "iframe": []}
    texts = BoxText.select()
    if texts.exists():
        res["text"] = as_a_dict(list(texts))
    iframes = BoxIframe.select()
    if iframes.exists():
        res["iframe"] = as_a_dict(list(texts))
    return jsonify(res)

@app.route('/content/<iid>', methods=['GET'])
def get_content_param(iid):
    data = request.json
    if iid:
        return edit_content_with_id(iid, data, request.method)
    return "Error"


def content_exists(iid):
    obj = BoxText.select().where(BoxText.id==iid)
    if obj.exists():
        return True, obj, "text"
    obj = BoxIframe.select().where(BoxIframe.id==iid)
    if obj.exists():
        return True, obj, "iframe"
    return False, None, "none"



def get_content_with_id(iid):
    ex, obj, t = content_exists(iid)
    if ex:
        return jsonify(obj.get().as_a_dict())
    return "Error"




@app.route('/content/<iid>', methods=['POST', 'PATCH', 'DELETE'])
@basic_auth.required
def edit_contents_param(iid):
    data = request.json
    if iid:
        return edit_content_with_id(iid, data, request.method)
    return "Error"

@app.route('/content', methods=['POST', 'PATCH', 'DELETE'])
@basic_auth.required
def edit_contents():
    data = request.json
    if "id" in data:
        return edit_content_with_id(data["id"], data, request.method)
    else:
        return edit_content_with_id(None, data, request.method)




def edit_content_with_id(iid, data, method):
    if method == 'POST':
        if data and iid and ("type" in data or "text" in data or "url" in data) and "box" in data:
            if ("type" in data and data["type"] == "iframe") or "url" in data:
                ret = BoxIframe.select().where(BoxText.id==iid)
                if ret.exists():
                    return "error: already exists"
                obj = BoxIframe.create(id=iid)
                if obj:
                    obj.update_with_dict(data, True)
                ret = BoxIframe.select().where(BoxIframe.id==iid)
                if ret.exists():
                    return jsonify(ret.get().as_a_dict())
                return "error. Could not create"
            elif ("type" in data and data["type"] == "text") or "text" in data:
                ret = BoxText.select().where(BoxText.id==iid)
                if ret.exists():
                    return "error: already exists"
                obj = BoxText.create(id=iid)
                if obj:
                    obj.update_with_dict(data, True)
                ret = BoxText.select().where(BoxText.id==iid)
                if ret.exists():
                    return jsonify(ret.get().as_a_dict())
                return "error. Could not create"
            return "error"
    if method == 'PATCH':
        if data and iid:
            obj = BoxText.select().where(BoxText.id==iid)
            if not obj.exists():
                obj = BoxIframe.select().where(BoxIframe.id==iid)
            if obj.exists():
                ret = obj.get()
                ret.update_with_dict(data)
                return jsonify(ret.as_a_dict())
        return "No such object"
    if method == 'DELETE':
        if iid:
            obj = BoxContent.select().where(BoxContent.id==id)
            if obj.exists():
                obj.get().delete()
                return "ok"
            return "No such object"
    return "Error"

@app.route('/random-image', methods=['GET'])
def get_random_image():
    images = list(Image.select().where(Image.hidden == False))
    if len(images) == 0:
        return jsonify({})
    if len(images) == 1:
        return jsonify(images[0].as_a_dict())
    now = datetime.datetime.now()
    aged_images = []
    oldest = 0
    for image in images:
        age = (now - image.modified).hours
        if age > oldest:
            oldest = age
        aged_images.append({"age": age, "image": image})
    total_weight = 0
    for ai in aged_images:
        ai["weight"] = (oldest+10-ai["age"])/(oldest+1)
        total_weight += ai["weight"]
    r = random.random()*total_weight
    cursor = 0
    for ai in aged_images:
        cursor += ai["weight"]
        if cursor > r:
            return jsonify(ai["image"].as_a_dict())
    return jsonify({})






@app.route('/image', methods=['GET'])
def get_images():
    data = request.json
    if data and "id" in data:
        return get_image_with_id(data["id"])
    else:
        return jsonify(as_a_dict(Image.get()))


@app.route('/image/<iid>', methods=['GET'])
def get_image_param(iid):
    if iid:
        return get_image_with_id(iid)
    return "Error"

def get_image_with_id(iid):
    return jsonify(Image.get(id=iid).as_a_dict())


@app.route('/image', methods=['POST', 'PATCH', 'DELETE'])
@basic_auth.required
def edit_images():
    data = request.json

    if "id" in data:
        return edit_image_with_id(data["id"], data, request.method)
    else:
        return edit_image_with_id(None, data, request.method)

@app.route('/image/<iid>', methods=['PATCH', 'DELETE'])
@basic_auth.required
def edit_image(iid):
    data = request.json
    if iid:
        return edit_image_with_id(iid, data, request.method)
    return "Error"

def edit_image_with_id(iid, data, method):
    author = "unknown"
    if "author" in data:
        author = data["author"]
    if method == 'POST':
        if data and "url" in data:
            img = Image.create(url=data["url"], created_by=author)
            if img:
                return jsonify(img.as_a_dict())
    if method == 'PATCH':
        if data and iid:
            obj = Image.get(id=iid)
            if obj:
                obj.update_with_dict(data)
                return jsonify(obj.as_a_dict())
        return "No such object"
    if method == 'DELETE':
        if iid:
            obj = Image.get(id=iid)
            if obj:
                obj.delete()
                return "ok"
    return "Error"


@app.route('/keyvalue/<key>', methods=['GET'])
def get_keyvalue(key):
    if key:
        obj = KeyValue.get(key=key)
        if obj:
            return jsonify(obj.as_a_dict())
    return "Error"

@app.route('/keyvalue', methods=['GET'])
def get_keyvalues():
    data = request.json
    if data and "key" in data:
        return jsonify(KeyValue.get(key=data["key"]).as_a_dict())
    return jsonify(key_values_as_a_dict())



@app.route('/keyvalue/<key>', methods=['POST', 'PATCH', 'DELETE'])
@basic_auth.required
def edit_keyvalue(key):
    data = request.json
    if key:
        value = None
        author = None
        if "value" in data:
            value = data["value"]
        if "author" in data:
            author = data["author"]
        return edit_parsed_keyvalue(key, value, author, request.method)
    return "Error"


@app.route('/keyvalue', methods=['POST', 'PATCH', 'DELETE'])
@basic_auth.required
def edit_keyvalues():
    data = request.json
    if data and "key" in data:
        value = None
        author = None
        if "value" in data:
            value = data["value"]
        if "author" in data:
            author = data["author"]
        return edit_parsed_keyvalue(data["key"], value, author, request.method)
    return "Error"

def edit_parsed_keyvalue(key, value, author, method):
    if key:
        if method == 'POST':
            if value:
                return jsonify(create_new_key_value(key, value, author))
        if method == 'PATCH':
            if value:
                res = update_key_value(key, value, author)
                if res:
                    return jsonify(res.as_a_dict())
        if method == 'DELETE':
            obj = KeyValue.get(key=key)
            if obj:
                obj.delete()
                return "ok"
            return "No such object"
    return "Error"




@app.teardown_appcontext
def close_db_connection(exception):
    close_connection(exception)

def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


if __name__ == '__main__':
    app.run(debug=True)