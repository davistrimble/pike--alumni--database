from flask import Flask, request, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from search import search_it
from members import get_member, set_password

app = Flask(__name__)

@app.route("/")
def home():
    return "Welcome Brother of Pike"

@app.route("/test")
def test():
    s=request.args.get("q","")
    return search_it(s)
@app.route("/search")
def search_page():
    s=(request.args.get("q",""))
    r = search_it(s)
    return render_template("search.html", query = s, results = r)
@app.route("/signup", methods = ["GET", "POST"])
def signup():
    if (request.method == "POST"):      
        e = request.form.get("email")
        p = request.form.get("password")
        member = get_member(e)
        if (not member):
            return render_template("signup.html", message = "Sorry, this email is not approved!")
        elif (not member["password_hash"]):
            h = generate_password_hash(p)
            set_password(e, h)
            return render_template("signup.html", message = "Password Created. Click here to Log In!")
        else:
            return render_template("signup.html", message = "This account already has a password associated with it. Click here to Log In!")
    else:
        return render_template("signup.html")
