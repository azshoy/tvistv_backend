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
    return error_response("notfound")


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
    return error_response("notfound")




@app.route('/edit-content/<iid>', methods=['POST', 'PATCH', 'DELETE'])
@basic_auth.required
def edit_contents_param(iid):
    data = request.json
    if iid:
        return edit_content_with_id(iid, data, request.method)
    return error_response("end")

@app.route('/edit-content', methods=['POST', 'PATCH', 'DELETE'])
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
                    return error_response("exists")
                obj = BoxIframe.create(id=iid)
                if obj:
                    obj.update_with_dict(data, True)
                ret = BoxIframe.select().where(BoxIframe.id==iid)
                if ret.exists():
                    return jsonify(ret.get().as_a_dict())
                return error_response()
            elif ("type" in data and data["type"] == "text") or "text" in data:
                ret = BoxText.select().where(BoxText.id==iid)
                if ret.exists():
                    return error_response("exists")
                obj = BoxText.create(id=iid)
                if obj:
                    obj.update_with_dict(data, True)
                ret = BoxText.select().where(BoxText.id==iid)
                if ret.exists():
                    return jsonify(ret.get().as_a_dict())
            return error_response()
    if method == 'PATCH':
        if data and iid:
            obj = BoxText.select().where(BoxText.id==iid)
            if not obj.exists():
                obj = BoxIframe.select().where(BoxIframe.id==iid)
            if obj.exists():
                ret = obj.get()
                ret.update_with_dict(data)
                return jsonify(ret.as_a_dict())
            return error_response("notfound", "No such object")
    if method == 'DELETE':
        if iid:
            obj = BoxText.select().where(BoxText.id==iid)
            if not obj.exists():
                obj = BoxIframe.select().where(BoxIframe.id==iid)
            if obj.exists():
                obj.get().delete_instance()
                return jsonify({"message": "Deleted!"}), 200
            return error_response("notfound", "No such object")
    return error_response("end")

@app.route('/random-image', methods=['GET'])
def get_random_image():
    images = list(Image.select().where(Image.hidden == False))
    if len(images) == 0:
        return error_response("notfound")
    if len(images) == 1:
        return jsonify(images[0].as_a_dict())
    now = datetime.datetime.now()
    aged_images = []
    oldest = 0
    for image in images:
        age = (now - image.modified).seconds / (60*60)
        if age > oldest:
            oldest = age
        aged_images.append({"age": age, "image": image})
        boost = 128
        while age < boost and boost > 1:
            aged_images.append({"age": age, "image": image})
            boost = boost/2

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
    return error_response("end")






@app.route('/image', methods=['GET'])
def get_images():
    imgs = Image.select()
    if imgs.exists():
        return jsonify(as_a_dict(list(imgs)))
    return error_response("notfound")



@app.route('/image/<iid>', methods=['GET'])
def get_image_param(iid):
    if iid:
        return get_image_with_id(iid)
    return error_response("end")

def get_image_with_id(iid):
    img = Image.get_or_none(id=iid)
    if img:
        return jsonify(img.as_a_dict())
    return error_response("notfound", "No such object")


@app.route('/edit-image', methods=['POST', 'PATCH', 'DELETE'])
@basic_auth.required
def edit_images():
    data = request.json

    if "id" in data:
        return edit_image_with_id(data["id"], data, request.method)
    else:
        return edit_image_with_id(None, data, request.method)

@app.route('/edit-image/<iid>', methods=['PATCH', 'DELETE'])
@basic_auth.required
def edit_image(iid):
    data = request.json
    if iid:
        return edit_image_with_id(iid, data, request.method)
    return error_response("end")

def edit_image_with_id(iid, data, method):
    author = "unknown"
    if isinstance(iid, str):
        if iid.isdigit():
            iid = int(iid)
    if "author" in data:
        author = data["author"]
    if method == 'POST':
        if data and "url" in data:
            img = Image.create(url=data["url"], created_by=author)
            if img:
                return jsonify(img.as_a_dict())
    if method == 'PATCH':
        if data and iid:
            obj = Image.get_or_none(id=iid)
            if obj:
                obj.update_with_dict(data)
                return jsonify(obj.as_a_dict())
            return error_response("notfound", "No such object")
        return error_response("notfound", "No such object")
    if method == 'DELETE':
        if iid:
            obj = Image.get_or_none(id=iid)
            if obj:
                obj.delete_instance()
                return jsonify({"message": "Deleted!"}), 200
            return error_response("notfound", "No such object")
    return error_response("end")


@app.route('/keyvalue/<key>', methods=['GET'])
def get_keyvalue(key):
    if key:
        obj = KeyValue.get_or_none(key=key)
        if obj:
            return jsonify(obj.as_a_dict())
        return error_response("notfound", "No such object")
    return error_response("end")

@app.route('/keyvalue', methods=['GET'])
def get_keyvalues():
    data = request.json
    if data and "key" in data:
        kv = KeyValue.get_or_none(key=data["key"])
        if kv:
            return jsonify(kv.as_a_dict())
        return error_response("notfound", "No such object")

    return jsonify(key_values_as_a_dict())



@app.route('/edit-keyvalue/<key>', methods=['POST', 'PATCH', 'DELETE'])
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
    return error_response("end")


@app.route('/edit-keyvalue', methods=['POST', 'PATCH', 'DELETE'])
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
    return error_response("end")

def edit_parsed_keyvalue(key, value, author, method):
    if key:
        if method == 'POST':
            if value:

                if KeyValue.get_or_none(key=key):
                    return error_response("exists")
                r = create_new_key_value(key, value, author)
                if r:
                    kv = KeyValue.get_or_none(key=key)
                    if kv:
                        return jsonify(kv.as_a_dict())
        if method == 'PATCH':
            if value:
                res = update_key_value(key, value, author)
                if res:
                    return jsonify(res.as_a_dict())
        if method == 'DELETE':
            obj = KeyValue.get_or_none(key=key)
            if obj:
                obj.delete_instance()
                return jsonify({"message": "Deleted!"}), 200

            return error_response("notfound", "No such object")
    return error_response("end")




@app.teardown_appcontext
def close_db_connection(exception):
    close_connection(exception)

def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def error_response(e="?", msg=""):
    code = 418
    error = {"error": "Unknown error"}
    if msg != "":
        error["message"] = msg

    if e == "notfound":
        error["error"] = "Not found"
        code = 404
    if e == "exists":
        error["error"] = "Already exists"
        code = 400
    if e == "end":
        error["error"] = "Could not execute"
        code = 409


    return jsonify(error), code


if __name__ == '__main__':
    app.run(debug=True)