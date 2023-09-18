import time

from flask import *
from markupsafe import Markup
from requests_oauthlib import OAuth2Session
import getpass
import threading
import asyncio
import requests
import os
import pickle
import json
import owncloud

nc_folder = "https://nextcloudpijonas.ddns.net/index.php/s/KEiaHGa5TkQnY4J"
nc = owncloud.Client("https://nextcloudpijonas.ddns.net/")
nc.login("ncp", "BrauchteNeGruppe")

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
UPLOAD_FOLDER = os.path.join("static", "uploads")

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
os.environ["CLIENT_ID"] = "1152244097269112853"
os.environ["SECRET"] = "fBCyvxRiX089RzlW1usUysQn9_KFEHyq"
os.environ["TOKEN"] = "MTE1MjI0NDA5NzI2OTExMjg1Mw.GaYgm5.SeSZcBzr_sUJQc21BmyIoff5jnNhuownHZ6RtM"

# Settings for your app
base_discord_api_url = 'https://discordapp.com/api'
client_id = os.getenv("CLIENT_ID")  # Get from https://discordapp.com/developers/applications
client_secret = os.getenv("SECRET")
redirect_uri = "http://localhost:3000/oauth_callback"  # 'https://unikameraden.pythonanywhere.com/oauth_callback'
scope = ['identify', 'email']
token_url = 'https://discordapp.com/api/oauth2/token'
authorize_url = 'https://discordapp.com/api/oauth2/authorize'

app = Flask(__name__)
app.static_url_path = '/static'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.secret_key = os.urandom(24)

headers = {'Authorization': f'Bot {os.getenv("TOKEN")}'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/home")
def home():
    if request.cookies.get("username") is not None:
        f = open(f"users/{request.cookies.get('username')}", "rb")
        user = pickle.load(f)
        return render_template("home.html",
                               avatar_url=f"https://cdn.discordapp.com/avatars/{user['id']}/{user['avatar']}.jpg",
                               name=user["username"])
    else:
        resp = make_response(redirect("/profile"))
        return resp


@app.route("/profile")
def profile():
    oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)
    login_url, state = oauth.authorization_url(authorize_url)
    session['state'] = state

    print(state, session["state"], "lol", login_url)
    print(session)
    if request.cookies.get("username") is not None:
        f = open(f"users/{request.cookies.get('username')}", "rb")
        user = pickle.load(f)
        return render_template("profile.html",
                                     avatar_url=f"https://cdn.discordapp.com/avatars/{user['id']}/{user['avatar']}.jpg",
                                     name=user["username"], login_url=login_url)
    else:
        return render_template("login.html", login_url=login_url)


@app.route("/oauth_callback")
def oauth_callback():
    print(session)
    discord = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)
    token = discord.fetch_token(
        token_url,
        client_secret=client_secret,
        authorization_response=request.url,
    )
    session['discord_token'] = token
    discord = OAuth2Session(client_id, token=session['discord_token'])
    response = discord.get(base_discord_api_url + '/users/@me')
    print(response.json())
    with open(f"users/{response.json()['username']}", "wb") as f:
        pickle.dump(response.json(), f)
    print(response.json()["id"])
    resp = make_response(redirect("/home"))
    resp.set_cookie("username", response.json()["username"], max_age=60*60*24*31)
    return resp


@app.route("/logout")
def logout():
    resp = make_response(redirect("/home"))
    resp.delete_cookie('username')
    return resp


filenames = {}


@app.route("/files", methods=["GET", "POST"])
def files():
    img_string = ""
    if request.method == "POST":
        file = request.files
        file = file["file"]
        if file and allowed_file(file.filename) and file.filename not in filenames:
            file.save(f"temporary/{file.filename}")
            nc.put_file("/UniKameraden/Photos/", f"temporary/{file.filename}")
            nc.share_file_with_link("/UniKameraden/Photos/" + file.filename)
            os.remove(f"temporary/{file.filename}")
            # file.save(os.path.join("/home/DerCooleBoi/mysite/static/uploads", file.filename))
            filenames[str(len(filenames) + 1)] = file.filename
            print(filenames)
            redirect("/images")
        else:
            if request.cookies.get("username") is not None:
                f = open(f"users/{request.cookies.get('username')}", "rb")
                user = pickle.load(f)
                return render_template("login/images_login.html",
                                       avatar_url=f"https://cdn.discordapp.com/avatars/{user['id']}/{user['avatar']}.jpg",
                                       name=user["username"],
                                       message="Error: invalid filename. Vielleicht ist dieser schon benutzt!",
                                       image_render=Markup(img_string))
            else:
                return render_template("images.html",
                                       message="Error: invalid filename. Vielleicht ist dieser schon benutzt!",
                                       image_render=Markup(img_string))

    if request.cookies.get("username") is not None:
        f = open(f"users/{request.cookies.get('username')}", "rb")
        user = pickle.load(f)
        return render_template("files.html",
                               avatar_url=f"https://cdn.discordapp.com/avatars/{user['id']}/{user['avatar']}.jpg",
                               name=user["username"], message="", image_render=Markup(img_string))
    else:
        return render_template("images.html", message="", image_render=Markup(img_string))


@app.route("/photos")
def photos():
    img_string = ""
    for pic in nc.list("/UniKameraden/Photos"):
        img_string += f'<img src="https://nextcloudpijonas.ddns.net/index.php/s/{nc.get_shares(pic.path)[0].token}/preview" alt="User Image" class="image-size">'
    f = open(f"users/{request.cookies.get('username')}", "rb")
    user = pickle.load(f)
    return render_template("photos.html",
                           avatar_url=f"https://cdn.discordapp.com/avatars/{user['id']}/{user['avatar']}.jpg",
                           name=user["username"], message="", image_render=Markup(img_string))


@app.route("/")
def redirect_home():
    return redirect("/home")


@app.errorhandler(404)
def page_not_found(error):
    return render_template("page_not_found.html"), 404


if __name__ == '__main__':
    app.run(port=3000)

