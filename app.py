
#--( Dependencies )------------------------------------------#
from flask import Flask, send_from_directory, session, request, Response, redirect, render_template, jsonify
from flask_session import Session
from Util import Database
from pprint import pprint

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

#--( Base Pages )--------------------------------------------#
@app.route("/")
@app.route("/home")
def home():
	return render_template("home.html")

@app.route("/about")
def about():
	return render_template("aboutus.html")

@app.route("/contact")
def contact():
	return render_template("contactus.html")

#--( Credentials )-------------------------------------------#
def logged_in() -> bool:
	return session.get("customer_id") != None

@app.route("/login", methods=["GET", "POST"])
def login():
	match request.method:
		case "GET":
			return render_template("login.html")
		case "POST":
			data = Database.login_customer(
				password = request.form.get("password"),
				email = request.form.get("email"),
				phone_number = request.form.get("phone_number") )
			if not data: return render_template("login.html")
			
			session["customer_id"] = data["id"]
			session["first_name"]  = data["first_name"]
			return redirect("/")

@app.route("/signup", methods=["GET", "POST"])
def signup():
	match request.method:
		case "GET":
			return render_template("signup.html")
		case "POST":
			assert request.form.get("password_1") == request.form.get("password_2"), "Password's don't match."
			
			print(
				request.form.get("name"),
				request.form.get("contact"),
				request.form.get("password_1"),
				request.form.get("password_2")
			)

			name = str.split(request.form.get("name"), " ")
			first_name, last_name = name[0], name[-1]
			
			contact = request.form.get("contact")
			email, phone_number = None, None
			if "@" in contact:
				assert str.find(contact, ".") > str.find(contact, "@"), "Period found in front of @ in email."
				email = contact
				print("Email:", contact)
			else:
				phone_number = contact
				print("Phone:", contact)
			
			data = Database.signup_customer(
				first_name = first_name,
				last_name  = last_name,
				password   = request.form.get("password_1"),
				email		 = email,
				phone_number = phone_number )

			session["customer_id"] = data["id"]
			session["first_name"]  = data["first_name"]
			return redirect("/")

@app.route("/logout")
def logout():
	session.clear()
	return redirect("/")

#--( Products )----------------------------------------------#
@app.route("/catalog")
def catalog():
	data = Database.get_all_products()
	return render_template("catalog.html", products = data)
	#return render_template("catalog.html")

@app.route("/catalog/info")
def all_products():
	products = Database.get_all_products()
	if len(products) == 0: print("No products.")
	return jsonify(products)

@app.route("/catalog/info/<int:product_id>")
def product_info(product_id):
	product = Database.get_product(product_id)
	if len(product) == 0: print("Product Id doesn't exist.")
	return jsonify(product)

#--( Cart )--------------------------------------------------#
@app.route("/cart")
def cart():
	if not logged_in():
		return redirect("/login")
	return render_template("cart.html")  

@app.route("/cart/info")
def cart_items():
	if not logged_in():
		return Response("Unauthorized", status=400)

	cart_items = Database.get_cart_items(
		customer_id = session.get("customer_id") )
	if len(cart_items) == 0: print("No items in cart.")
	return jsonify(cart_items)

@app.route("/cart/add", methods=["POST"])
def add_to_cart():
	if not logged_in():
		return redirect("/login")

	print("Add item to cart")

@app.route("/cart/remove", methods=["POST"])
def remove_from_cart():
	if not logged_in():
		return redirect("/login")

	print("Remove item from cart")

#--( Orders )------------------------------------------------# 
@app.route("/orders")
def orders():
	return render_template("orders.html")

@app.route("/orders/info")
def all_orders():
	if not logged_in():
		return Response("Unauthorized", status=400)

	orders = Database.get_orders(
		customer_id = session.get("customer_id") )
	if len(orders) == 0: print("No orders.")
	return jsonify(orders)

@app.route("/orders/info/<int:order_id>", methods=["GET"]) #, "PUT", "DELETE"
def order_details(order_id):
	match request.method:
		case "GET":
			order_items = Database.get_order_items(
				customer_id = session.get("customer_id"), 
				order_id	= order_id )
			if len(order_items) == 0: print("No items in order.")
			return jsonify(order_items)
	
	#case "PUT":
	#	# Handle PUT requests to update an order
	#	data = request.get_json()
	#	updated_order = update_order(order_id, data)
	#	return jsonify(updated_order)
	#case "DELETE":
	#	# Handle DELETE requests to delete an order
	#	delete_order(order_id)
	#	return jsonify({"message": "Order deleted successfully"})

#--( Run )---------------------------------------------------# 
if __name__ == "__main__":
	app.run(debug=False)
	#pprint(Database.get_product(6))

#@app.route("/participants")
#def participants():
#	data = Database.get_participants()
#	return render_template("participants.html", data=data)