#--( Dependencies )------------------------------------------#
from werkzeug.security import generate_password_hash, check_password_hash
from math import floor
from time import time
from os import path
import phonenumbers
import sqlite3

UTIL_FOLDER_PATH = path.dirname(path.dirname(path.abspath(__file__)))
DATABASE_PATH = path.join(UTIL_FOLDER_PATH, "Resources", "Database.db")

#--( Interacting With Database )-----------------------------#
def fetch_one(query:str, parameters:tuple|None=None) -> any:
	try:
		with sqlite3.connect(DATABASE_PATH) as connection:
			cursor = connection.cursor()
			if not parameters: cursor.execute(query)
			else: cursor.execute(query, parameters)
			data = cursor.fetchone()

			if data is None: return ()
			elif len(data) == 1: return data[0]
			else: return data
			#return data if len(data) > 1 else data[0]
	except Exception as err:
		print("ERROR [Database.fetch_one()]:", err)
		return ()

def fetch_all(query:str, parameters:tuple|None=None) -> list:
	try:
		with sqlite3.connect(DATABASE_PATH) as connection:
			cursor = connection.cursor()
			if not parameters: cursor.execute(query)
			else: cursor.execute(query, parameters)
			return cursor.fetchall()
	except Exception as err:
		print("ERROR [Database.fetch_all()]:", err)
		return []

def execute(query:str, parameters:tuple) -> bool:
	try:
		with sqlite3.connect(DATABASE_PATH) as connection:
			cursor = connection.cursor()
			cursor.execute(query, parameters)
			connection.commit()
		return True
	except Exception as err:
		print("ERROR [Database.execute()]:", err)
		return False

#--( Utilities )---------------------------------------------#
def generate_timestamp() -> int:
	return floor(time())

def convert_phone_number(phone_number:str|None=None) -> str:
	if not phone_number: return None

	phone_number = phonenumbers.parse(phone_number)
	if not phonenumbers.is_possible_number(phone_number): return None
	#if not phonenumbers.is_valid_number(phone_number): return None

	return phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.E164)

#--( Login & Signup )----------------------------------------#
def login_customer(password:str, email:str|None=None, phone_number:str|None=None) -> dict:
	if phone_number: phone_number = convert_phone_number(phone_number)
	assert email or phone_number, "No email or phone number provided."

	if email:
		data = fetch_one('''SELECT customer_id, first_name, password FROM customers WHERE email == ?''', (email,))
	elif phone_number:
		data = fetch_one('''SELECT customer_id, first_name, password FROM customers WHERE phone_number == ?''', (phone_number,))
	if len(data) == 0: print("Unable to find data for customer."); return None

	return {
		"id": data[0],
		"first_name": data[1]
	} if check_password_hash(data[2], password) else None

def signup_customer(first_name:str, last_name:str, password:str, email:str|None=None, phone_number:str|None=None) -> dict:
	if phone_number: phone_number = convert_phone_number(phone_number)
	assert email or phone_number, "No email or phone number provided."
	
	data = login_customer(
		password	 = password,
		email		 = email,
		phone_number = phone_number )
	if data: return data

	created = generate_timestamp(); updated = created
	hashed_password = generate_password_hash(password)
	execute('''INSERT INTO customers (first_name, last_name, password, email, phone_number, created, updated) VALUES (?, ?, ?, ?, ?, ?, ?)''', 
		(first_name, last_name, hashed_password, email, phone_number, created, updated))
	print(created)

	return login_customer(password, email, phone_number)

#--( Product Information )-----------------------------------#
def get_all_products() -> list:
	data = fetch_all('''
		SELECT
			products.product_id,
			product_variants.product_variant_id,
			products.product_name,
			product_variants.product_variant_name,
			products.description,
			product_type_ids.product_type,
			product_variants.unit_price,
			product_variants.image
		FROM product_variants
			LEFT JOIN products ON product_variants.product_id = products.product_id
			LEFT JOIN product_type_ids ON products.product_type_id = product_type_ids.product_type_id
	''')

	products = {}
	for product_variant in data:
		if not product_variant[0] in products:
			products[ product_variant[0] ] = {
				"name": product_variant[2],
				"description": product_variant[4],
				"type": product_variant[5],
				"variants": []
			}

		products[ product_variant[0] ]["variants"].append({
			"id": product_variant[1],
			"name": product_variant[3],
			"price": product_variant[6],
			"image": product_variant[7]
		})

	return [products[id] for id in products]

def get_product(product_variant_id:int) -> dict:
	assert product_variant_id, "No Product Id provided."

	data = fetch_one('''
		SELECT
			product_variants.product_variant_id,
			products.product_name,
			product_variants.product_variant_name,
			products.description,
			product_type_ids.product_type,
			product_variants.unit_price,
			product_variants.image
		FROM product_variants
			LEFT JOIN products ON product_variants.product_id = products.product_id
			LEFT JOIN product_type_ids ON products.product_type_id = product_type_ids.product_type_id		  
		WHERE product_variant_id = ?
		LIMIT 1
	''', (product_variant_id,))

	if data: return {
		"id"	: data[0],
		"name"	: f"{data[1]} - {data[2]}",
		"description": data[3],
		"type"	: data[4],
		"price" : data[5],
		"image"	: data[6]
	}

#--( Order Information )-------------------------------------#
def get_orders(customer_id:int) -> list:
	assert customer_id, "No customer id provided."

	def fetch_orders(customer_id:int) -> list:
		return fetch_all('''
			SELECT
				orders.order_id,
				order_statuses.status,
				orders.created
			FROM orders
				LEFT JOIN order_statuses ON orders.status_id = order_statuses.status_id
			WHERE 1 = 1
				AND orders.customer_id = ?
			GROUP BY orders.order_id
			ORDER BY orders.created DESC
		''', (customer_id,))
	
	def fetch_order_items(order_id:int) -> list:
		return fetch_all('''
			SELECT
				order_items.product_variant_id,
				products.product_name,
				product_variants.product_variant_name,
				product_variants.image,
				order_items.quantity,
				order_items.unit_price,
				ROUND(SUM(order_items.quantity * order_items.unit_price), 2) as total_price
			FROM order_items
				LEFT JOIN product_variants ON order_items.product_variant_id = product_variants.product_variant_id
				LEFT JOIN products ON product_variants.product_id = products.product_id	 
			WHERE 1 = 1
				AND order_items.order_id = ?
			GROUP BY order_items.product_variant_id
			ORDER BY total_price DESC
		''', (order_id, ))
	
	orders = []
	for order_data in fetch_orders(customer_id):
		order_items = []
		total_price = 0.00
		total_items = 0
		
		for item_data in fetch_order_items(order_data[0]):
			total_items += item_data[4]
			total_price += item_data[6]
			order_items.append({
				"id"		: item_data[0],
				"name"		: f"{item_data[1]} - {item_data[2]}",
				"image"		: item_data[3],
				"quantity"	: item_data[4],
				"unit_price"  : item_data[5]
				#"total_price" : item_data[6]
			})
		
		orders.append({
			"id"		: order_data[0],
			"status"	: order_data[1],
			"created"	: order_data[2],
			"items" 	: order_items,
			"total_items" : total_items,
			"total_price" : round(total_price, 2)
		})

	return orders

def get_order_info(customer_id:int, order_id:int) -> list:
	assert customer_id, "No customer id provided."
	assert order_id, "No order id provided."

	def fetch_order(customer_id:int, order_id:int) -> list:
		return fetch_one('''
			SELECT
				orders.order_id,
				order_statuses.status,
				orders.created
			FROM orders
				LEFT JOIN order_statuses ON orders.status_id = order_statuses.status_id
			WHERE 1 = 1
				AND orders.customer_id = ?
				AND orders.order_id = ?
			GROUP BY orders.order_id
			LIMIT 1
		''', (customer_id, order_id))
	
	def fetch_order_items(order_id:int) -> list:
		return fetch_all('''
			SELECT
				order_items.product_variant_id,
				products.product_name,
				product_variants.product_variant_name,
				product_variants.image,
				order_items.quantity,
				order_items.unit_price,
				ROUND(SUM(order_items.quantity * order_items.unit_price), 2) as total_price
			FROM order_items
				LEFT JOIN product_variants ON order_items.product_variant_id = product_variants.product_variant_id
				LEFT JOIN products ON product_variants.product_id = products.product_id	 
			WHERE 1 = 1
				AND order_items.order_id = ?
			GROUP BY order_items.product_variant_id
			ORDER BY total_price DESC
		''', (order_id, ))
	
	order_data = fetch_order(customer_id, order_id)
	order_items = []
	total_price = 0.00
	total_items = 0
		
	for item_data in fetch_order_items(order_data[0]):
		total_items += item_data[4]
		total_price += item_data[6]
		order_items.append({
			"id"		: item_data[0],
			"name"		: f"{item_data[1]} - {item_data[2]}",
			"image"		: item_data[3],
			"quantity"	: item_data[4],
			"unit_price"  : item_data[5]
			#"total_price" : item_data[6]
		})
		
	return {
		"id"		: order_data[0],
		"status"	: order_data[1],
		"created"	: order_data[2],
		"items" 	: order_items,
		"total_items" : total_items,
		"total_price" : round(total_price, 2)
	}

#--( Cart Information )--------------------------------------#
def get_cart(customer_id:int) -> list:
	assert customer_id, "No customer id provided."

	cart_items = fetch_all('''
		SELECT
			cart_items.product_variant_id,
			products.product_name,
			product_variants.product_variant_name,
			products.description,
			product_variants.image,
			product_variants.unit_price,
			cart_items.quantity,
			product_type_ids.product_type
		FROM cart_items
			LEFT JOIN product_variants ON cart_items.product_variant_id = product_variants.product_variant_id
			LEFT JOIN products ON product_variants.product_id = products.product_id
			LEFT JOIN product_type_ids on products.product_type_id = product_type_ids.product_type_id
		WHERE 1=1
			AND cart_items.customer_id = ?
		GROUP BY cart_items.product_variant_id
		ORDER BY cart_items.quantity DESC
	''', (customer_id, ))

	return [{
		"id"		: cart_item[0],
		"name"		: f"{cart_item[1]} - {cart_item[2]}",
		"description": cart_item[3],
		"image"		: cart_item[4],
		"unit_price": cart_item[5],
		"quantity"	: cart_item[6],
		"type"		: cart_item[7]
	} for cart_item in cart_items]

def add_to_cart(customer_id:int, product_variant_id:int, quantity:int=1):
	assert customer_id, "No customer id provided."
	assert product_variant_id and quantity, "Product id or quantity weren't provided."

	quantity_in_cart = fetch_one('''
		SELECT quantity
		FROM cart_items
		WHERE 1 = 1
			AND customer_id = ?
			AND product_variant_id = ?
		LIMIT 1''',
		(customer_id, product_variant_id))
	quantity_in_cart = quantity_in_cart if type(quantity_in_cart) == int else 0

	if quantity_in_cart > 0:
		execute('''
			UPDATE cart_items 
			SET quantity = ?
			WHERE 1 = 1
		  		AND customer_id = ?
		  		AND product_variant_id = ?''', 
			(quantity_in_cart + quantity, customer_id, product_variant_id))
	else:
		execute('''INSERT INTO cart_items (customer_id, product_variant_id, quantity) VALUES (?, ?, ?)''', 
			(customer_id, product_variant_id, quantity))

def remove_from_cart(customer_id:int, product_variant_id:int, quantity:int=999):
	assert customer_id, "No customer id provided."
	assert product_variant_id and quantity, "Product id or quantity weren't provided."
	
	quantity_in_cart = fetch_one('''
		SELECT quantity
		FROM cart_items
		WHERE 1 = 1
			AND customer_id = ?
			AND product_variant_id = ?
		LIMIT 1''',
		(customer_id, product_variant_id))
	new_quantity = (quantity_in_cart if type(quantity_in_cart) == int else 0) - quantity
	print(new_quantity)

	if new_quantity > 0:
		execute('''
			UPDATE cart_items 
			SET quantity = ?
			WHERE 1 = 1
		  		AND customer_id = ?
		  		AND product_variant_id = ?''', 
			(new_quantity, customer_id, product_variant_id))
	else:
		execute('''
			DELETE FROM cart_items
			WHERE 1 = 1
		  		AND customer_id = ?
		  		AND product_variant_id = ?''', 
			(customer_id, product_variant_id))

#--( Create Tables )-----------------------------------------#
def create_tables():
	with sqlite3.connect(DATABASE_PATH) as connection:
		# Customers Table
		connection.execute('''
			CREATE TABLE IF NOT EXISTS customers (
				customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
				first_name TEXT NOT NULL,
				last_name TEXT NOT NULL,
				email TEXT UNIQUE,
				phone_number TEXT UNIQUE,
				password TEXT NOT NULL,
				street TEXT,
				city TEXT,
				state TEXT,
				zip_code INTEGER,
				created INTEGER NOT NULL,
				updated INTEGER NOT NULL )''')
		connection.execute('''CREATE INDEX IF NOT EXISTS index_customer_email ON customers (email)''')
		connection.execute('''CREATE INDEX IF NOT EXISTS index_customer_phone ON customers (phone_number)''')
		
		# Product Types Table
		connection.execute('''
			CREATE TABLE IF NOT EXISTS product_type_ids (
				product_type_id INTEGER PRIMARY KEY,
				product_type TEXT )''')
		connection.execute("INSERT INTO product_type_ids (product_type) VALUES ('Shirt')")
		connection.execute("INSERT INTO product_type_ids (product_type) VALUES ('Pants')")
	
		# Products Table
		connection.execute('''
			CREATE TABLE IF NOT EXISTS products (
				product_id INTEGER PRIMARY KEY,
				product_name TEXT NOT NULL,
				description TEXT NOT NULL,
				product_type_id INTEGER REFERENCES product_type_ids (product_type_id) )''')
		connection.execute('''CREATE INDEX IF NOT EXISTS index_product_name ON products (product_name)''')
		connection.execute('''CREATE INDEX IF NOT EXISTS index_product_type ON products (product_type_id)''')

		# Products Variants Table
		connection.execute('''
			CREATE TABLE IF NOT EXISTS product_variants (
				product_variant_id INTEGER PRIMARY KEY AUTOINCREMENT,
				product_id INTEGER NOT NULL,
				product_variant_name TEXT,
				unit_price NUMERIC(4, 2) NOT NULL,
				quantity_available INTEGER NOT NULL,
				image TEXT )''')
		
		products = [
			{
				"Id": 1,
				"Name": "Cool Cat Poker",
				"Description": "Because only the coolest cats play poker.",
				"Type Id": 1,
				"Variants": [
					{
						"Name": "Black",
						"Price": 25.99,
						"Available": 5,
						"Image": "static/product_images/poker_tee_black.png"
					}, {
						"Name": "White",
						"Price": 25.99,
						"Available": 5,
						"Image": "static/product_images/poker_tee_white.png"
					}, {
						"Name": "Red",
						"Price": 25.99,
						"Available": 5,
						"Image": "static/product_images/poker_tee_red.png"
					}, {
						"Name": "Blue",
						"Price": 25.99,
						"Available": 5,
						"Image": "static/product_images/poker_tee_blue.png"
					}
				]
			}, {
				"Id": 2,
				"Name": "A Cat Named Slickback",
				"Description": "A doggy bag is 90 bucks, a tee shirt is 30.",
				"Type Id": 1,
				"Variants": [
					{
						"Name": "Black",
						"Price": 29.99,
						"Available": 5,
						"Image": "static/product_images/cns_tee_black.png"
					}, {
						"Name": "White",
						"Price": 29.99,
						"Available": 5,
						"Image": "static/product_images/cns_tee_white.png"
					}, {
						"Name": "Red",
						"Price": 29.99,
						"Available": 5,
						"Image": "static/product_images/cns_tee_red.png"
					}, {
						"Name": "Blue",
						"Price": 29.99,
						"Available": 5,
						"Image": "static/product_images/cns_tee_blue.png"
					}
				]
			}, {
				"Id": 3,
				"Name": "Cool Cat Cash",
				"Description": "Just a baker kneading his dough.",
				"Type Id": 1,
				"Variants": [
					{
						"Name": "Black",
						"Price": 29.99,
						"Available": 5,
						"Image": "static/product_images/money_tee_black.png"
					}, {
						"Name": "White",
						"Price": 29.99,
						"Available": 5,
						"Image": "static/product_images/money_tee_white.png"
					}, {
						"Name": "Red",
						"Price": 29.99,
						"Available": 5,
						"Image": "static/product_images/money_tee_red.png"
					}, {
						"Name": "Blue",
						"Price": 29.99,
						"Available": 5,
						"Image": "static/product_images/money_tee_blue.png"
					}
				]
			}
		]

		for product in products:
			connection.execute("""
				INSERT INTO products (product_id, product_name, description, product_type_id)
				VALUES (?, ?, ?, ?)
			""", (product['Id'], product['Name'], product['Description'], product['Type Id']))
			for variant in product['Variants']:
				connection.execute("""
					INSERT INTO product_variants (product_id, product_variant_name, unit_price, quantity_available, image)
					VALUES (?, ?, ?, ?, ?)
				""", (product['Id'], variant['Name'], variant['Price'], variant['Available'], variant['Image']))
	
		# Cart Items Table
		connection.execute('''
			CREATE TABLE IF NOT EXISTS cart_items (
				cart_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
				customer_id INTEGER NOT NULL REFERENCES customers (customer_id),
				product_variant_id INTEGER NOT NULL REFERENCES product_variants (product_variant_id),
				quantity INTEGER NOT NULL )''')
		connection.execute('''CREATE INDEX IF NOT EXISTS index_cart_item_customer ON cart_items (customer_id)''')
		
		# Cart Status Types Table
		connection.execute('''
			CREATE TABLE IF NOT EXISTS order_statuses (
				status_id INTEGER PRIMARY KEY,
				status TEXT )''')
		connection.execute('''INSERT OR IGNORE INTO order_statuses (status_id, status) VALUES (1, 'Pending Payment')''')
		connection.execute('''INSERT OR IGNORE INTO order_statuses (status_id, status) VALUES (2, 'Failed')''')
		connection.execute('''INSERT OR IGNORE INTO order_statuses (status_id, status) VALUES (3, 'On Hold')''')
		connection.execute('''INSERT OR IGNORE INTO order_statuses (status_id, status) VALUES (4, 'Processing')''')
		connection.execute('''INSERT OR IGNORE INTO order_statuses (status_id, status) VALUES (5, 'Completed')''')
		connection.execute('''INSERT OR IGNORE INTO order_statuses (status_id, status) VALUES (6, 'Canceled')''')
		connection.execute('''INSERT OR IGNORE INTO order_statuses (status_id, status) VALUES (7, 'Refunded')''')
		connection.execute('''INSERT OR IGNORE INTO order_statuses (status_id, status) VALUES (8, 'Backordered')''')
		connection.execute('''INSERT OR IGNORE INTO order_statuses (status_id, status) VALUES (9, 'Partially Shipped')''')
		connection.execute('''INSERT OR IGNORE INTO order_statuses (status_id, status) VALUES (10, 'Shipped')''')
		connection.execute('''INSERT OR IGNORE INTO order_statuses (status_id, status) VALUES (11, 'Out for Delivery')''')
		connection.execute('''INSERT OR IGNORE INTO order_statuses (status_id, status) VALUES (12, 'Delivered')''')
		
		# Orders Table
		connection.execute('''
			CREATE TABLE IF NOT EXISTS orders (
				order_id INTEGER PRIMARY KEY AUTOINCREMENT,
				customer_id INTEGER NOT NULL REFERENCES customers (customer_id),
				status_id INTEGER NOT NULL REFERENCES order_statuses (status_id),
				created INTEGER NOT NULL,
				updated INTEGER NOT NULL )''')
		connection.execute('''CREATE INDEX IF NOT EXISTS index_order_customer ON orders (customer_id)''')
		
		# Order Items Table
		connection.execute('''
			CREATE TABLE IF NOT EXISTS order_items (
				order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
				order_id INTEGER NOT NULL REFERENCES orders (order_id),
				product_variant_id INTEGER NOT NULL REFERENCES product_variants (product_variant_id),
				quantity INTEGER NOT NULL,
				unit_price NUMERIC(4, 2) NOT NULL )''')
		connection.execute('''CREATE INDEX IF NOT EXISTS index_order_item_order ON order_items (order_id)''')
	
		connection.commit()
	print("Finished Creating Database and Tables.")

#--( Add Sample Data To Tables )-----------------------------#
def populate_tables():
	from faker import Faker
	fake = Faker()

	with sqlite3.connect(DATABASE_PATH) as connection:
		cursor = connection.cursor()

		# Sample Customer
		first_name = "Test"
		last_name = "Account"
		email = "admin@email.com"
		phone_number = "+11234567890" #+ str(fake.random_int(min=1000000000, max=9999999999))
		password = generate_password_hash("PASSWORD")

		street = fake.street_address()
		city = fake.city()
		state = fake.state()
		zip_code = fake.zipcode()
		created = generate_timestamp()
		updated = created

		cursor.execute("""
			INSERT INTO customers (first_name, last_name, email, phone_number, password, street, city, state, zip_code, created, updated)
			VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
		""", (first_name, last_name, email, phone_number, password, street, city, state, zip_code, created, updated))


		# Generate sample data for cart items
		customer_id = 1
		product_variant_id = fake.random_element([row[0] for row in cursor.execute("SELECT product_variant_id FROM product_variants").fetchall()])
		quantity = fake.random_int(min=1, max=10)

		cursor.execute("""
			INSERT INTO cart_items (customer_id, product_variant_id, quantity)
			VALUES (?, ?, ?)
		""", (customer_id, product_variant_id, quantity))

		for order_id in range(1, 3):
			status_id = fake.random_int(min=1, max=12)
			created = generate_timestamp()
			updated = created

			cursor.execute("""
				INSERT INTO orders (customer_id, status_id, created, updated)
				VALUES (?, ?, ?, ?)
			""", (1, status_id, created, updated) )

			for _ in range(fake.random_int(min=1, max=4)):
				product = fake.random_element([(row[0], row[1]) for row in cursor.execute("SELECT product_variant_id, unit_price FROM product_variants").fetchall()])
				product_variant_id	= product[0]
				unit_price			= product[1]
				quantity = fake.random_int(min=1, max=3)

				cursor.execute("""
					INSERT INTO order_items (order_id, product_variant_id, quantity, unit_price)
					VALUES (?, ?, ?, ?)
				""", (order_id, product_variant_id, quantity, unit_price))


		print("Finished Populating Tables.")

#--( Run )---------------------------------------------------#
try:
	with sqlite3.connect(DATABASE_PATH) as connection: pass
except sqlite3.OperationalError: DATABASE_PATH = path.basename(DATABASE_PATH)

#if __name__ == "__main__":
#	create_tables()
#	populate_tables()