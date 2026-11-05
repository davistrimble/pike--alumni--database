from flask import Flask, request, render_template
from search import search

app = Flask(__name__)

@app.route("/")
def home():
    return "Welcome Brother of Pike"

@app.route("/test")
def test():
    s=request.args.get("q","")
    return search(s)
@app.route("/search")
def search_page():
    s=(request.args.get("q",""))
    r = search(s)
    return render_template("search.html", query = s, results = r)