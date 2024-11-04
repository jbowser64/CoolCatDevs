
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
	return session.get("customer_id") is not None

@app.route("/login", methods=["GET", "POST"])
def login():
	if request.method == "GET":
		return render_template("login.html")
	else:
		data = Database.login_customer(
			email = request.form.get("email"),
			password = request.form.get("password") )
		if not data:
			return render_template("login.html", login_error="Invalid email, phone number, or password.")
		
		session["customer_id"] = data["id"]
		session["first_name"] = data["first_name"]
		return redirect("/")

@app.route("/signup", methods=["GET", "POST"]) 
def signup():
	if request.method == "GET":
		return render_template("signup.html")
	elif request.method == "POST":
		password_1 = request.form.get("password_1")
		password_2 = request.form.get("password_2")
		
		if password_1 != password_2:
			return render_template("signup.html", signup_error="Passwords don't match.")
		
		name = request.form.get("name").split(" ")
		first_name, last_name = name[0], name[-1]
		
		email = request.form.get("email")
		email = email if email and "@" in email else None
		
		try:
			data = Database.signup_customer(
				first_name	= first_name,
				last_name	= last_name,
				email		= email,
				password = password_1 )
		except Exception as err:
			return render_template(
				"signup.html", 
				signup_error="Error creating account. Please try again.",
				name=request.form.get("name"),
				contact=request.form.get("contact")
			)
		
		session["customer_id"] = data["id"]
		session["first_name"] = data["first_name"]

		return render_template("home.html", success_message="Account successfully created!")

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

	cart_items = Database.get_cart( session.get("customer_id") )
	if len(cart_items) == 0: print("No items in cart.")
	return jsonify(cart_items)

@app.route("/cart/add", methods=["POST"])
def add_to_cart():
	if not logged_in():
		return redirect("/login")
	
	data = request.get_json()
	product_variant_id = data["product_variant_id"]
	quantity = data["quantity"] if "quantity" in data else 1
	
	Database.add_to_cart(
		customer_id = session.get("customer_id"),
		product_variant_id = product_variant_id,
		quantity = quantity )

	return jsonify({"message": "Item(s) added to cart successfully"}), 201

@app.route("/cart/remove", methods=["POST"])
def remove_from_cart():
	if not logged_in():
		return redirect("/login")
	
	data = request.get_json()
	product_variant_id = data["product_variant_id"]
	quantity = data["quantity"] if "quantity" in data else 999
	
	Database.remove_from_cart(
		customer_id = session.get("customer_id"),
		product_variant_id = product_variant_id,
		quantity = quantity )

	return jsonify({"message": "Item(s) removed to cart successfully"}), 201


#--( Orders )------------------------------------------------# 
@app.route("/orders")
def orders():
	return render_template("orders.html")

@app.route("/orders/info")
def all_orders():
	if not logged_in():
		return Response("Unauthorized", status=400)

	orders = Database.get_orders( session.get("customer_id") )
	if len(orders) == 0: print("No orders.")
	return jsonify(orders)

@app.route("/orders/info/<int:order_id>", methods=["GET"]) #, "PUT", "DELETE"
def order_details(order_id):
	match request.method:
		case "GET":
			order_info = Database.get_order_info(
				customer_id = session.get("customer_id"), 
				order_id	= order_id )
			if len(order_info) == 0: print("No items in order.")
			return jsonify(order_info)
	
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