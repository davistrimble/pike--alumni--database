from flask import Flask
from flask import request
from search import search

app = Flask(__name__)

@app.route("/")
def home():
    return "Welcome Brother of Pike"

@app.route("/test")
def test():
    s=request.args.get("q","")
    return search(s)