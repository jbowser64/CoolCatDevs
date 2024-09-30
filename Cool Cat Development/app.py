
#----------------------[ Dependencies ]----------------------#
from flask import Flask, request, session, redirect, render_template, jsonify
from flask_session import Session
from Util import Database

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

#-------------------------[ Pages ]------------------------- #
@app.route("/")
@app.route("/home")
def index():
	if not session.get("customer_id"): return redirect("/login")
	return render_template('index.html')

@app.route("/login", methods=["GET", "POST"])
def login():
	match request.method:
		case "GET":
			return render_template("login.html")
		case "POST":
			customer_id = Database.get_customer_id(
				password = request.form.get("password"),
				email = request.form.get("email"),
				phone_number = request.form.get("phone_number") )
			if customer_id == -1: return render_template("login.html")
			# iflowers@example.org
			
			session["customer_id"] = customer_id
			return redirect("/")

@app.route("/logout")
def logout():
	session.clear()
	return redirect("/")

@app.route("/testing")
def test_page():
	return render_template('testing.html')

@app.route("/api", methods=["GET"])
def api():
	print("API CALLED")
	data = {"index": "value"}
	return jsonify(data)

#@app.route("/participants")
#def participants():
#	data = Database.get_participants()
#	return render_template("participants.html", data=data)

#--------------------------[ Run ]-------------------------- #
if __name__ == "__main__":
	#Database.populate_tables()
	app.run(debug=False)