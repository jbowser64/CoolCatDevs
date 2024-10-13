
#----------------------[ Dependencies ]----------------------#
from werkzeug.security import generate_password_hash, check_password_hash
from math import floor
from time import time
from os import path
import phonenumbers
import sqlite3

UTIL_FOLDER_PATH = path.dirname(path.dirname(path.abspath(__file__)))
DATABASE_PATH = path.join(UTIL_FOLDER_PATH, "Resources", "database.db")

#------------------------[ Database ]------------------------#
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

def generate_timestamp() -> int:
	return floor(time())

def convert_phone_number(phone_number:str|None=None) -> str:
	if not phone_number: return None

	phone_number = phonenumbers.parse(phone_number)
	if not phonenumbers.is_possible_number(phone_number): return None
	#if not phonenumbers.is_valid_number(phone_number): return None

	return phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.E164)

#--------------------------[ Get ]-------------------------- #
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

def get_orders(customer_id:int) -> list:
	assert customer_id, "No customer id provided."

	def fetch_orders(customer_id:int) -> list:
		return fetch_all('''
			SELECT
				orders.order_id,
				statuses.status,
				orders.created
			FROM orders
				LEFT JOIN statuses ON orders.status_id = statuses.status_id
			WHERE 1 = 1
				AND orders.customer_id = ?
			GROUP BY orders.order_id
			ORDER BY orders.created DESC
		''', (customer_id,))
	
	def fetch_order_items(order_id:int) -> list:
		return fetch_all('''
			SELECT
				order_items.product_id,
				products.product_name,
				order_items.quantity,
				order_items.unit_price,
				ROUND(SUM(order_items.quantity * order_items.unit_price), 2) as total_price
			FROM order_items
				LEFT JOIN products ON order_items.product_id = products.product_id	  
			WHERE 1 = 1
				AND order_items.order_id = ?
			GROUP BY order_items.product_id
			ORDER BY total_price DESC
		''', (order_id, ))
	
	orders = []
	for order_data in fetch_orders(customer_id):
		order_items = []
		total_price = 0.00
		total_items = 0
		
		for item_data in fetch_order_items(order_data[0]):
			total_items += item_data[2]
			total_price += item_data[4]
			order_items.append({
				"id"		: item_data[0],
				"name"		: item_data[1],
				"quantity"	: item_data[2],
				"unit_price"  : item_data[3]
				#"total_price" : item_data[4]
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

def get_order_items(customer_id:int, order_id:int) -> list:
	assert customer_id, "No customer id provided."
	assert order_id, "No order id provided."

	order_items = fetch_all('''
		SELECT
			order_items.product_id,
			products.product_name,
			order_items.quantity,
			order_items.unit_price,
			ROUND(SUM(order_items.quantity * order_items.unit_price), 2) as total_price
		FROM orders
			LEFT JOIN order_items ON orders.order_id = order_items.order_id
			LEFT JOIN products ON order_items.product_id = products.product_id	  
		WHERE 1 = 1
			AND orders.customer_id = ?
			AND orders.order_id = ?
		GROUP BY order_items.product_id
		ORDER BY order_items.quantity DESC
	''', (customer_id, order_id))

	return [{
			"id"		: order_item[0],
			"name"		: order_item[1],
			"quantity"	: order_item[2],
			"unit_price"  : order_item[3],
			"total_price" : order_item[4]
		} for order_item in order_items]

#-------------------------[ Insert ]-------------------------#
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

#---------------------[ Create Tables ]--------------------- #
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
			CREATE TABLE IF NOT EXISTS product_types (
				product_type_id INTEGER PRIMARY KEY,
				product_type TEXT )''')
	
		# Products Table
		connection.execute('''
			CREATE TABLE IF NOT EXISTS products (
				product_id INTEGER PRIMARY KEY AUTOINCREMENT,
				product_name TEXT NOT NULL,
				description TEXT NOT NULL,
				unit_price NUMERIC(4, 2) NOT NULL,
				product_type_id INTEGER REFERENCES product_types (product_type_id),
				quantity_available INTEGER NOT NULL )''')
		connection.execute('''CREATE INDEX IF NOT EXISTS index_product_name ON products (product_name)''')
		connection.execute('''CREATE INDEX IF NOT EXISTS index_product_type ON products (product_type_id)''')
	
		# Cart Items Table
		connection.execute('''
			CREATE TABLE IF NOT EXISTS cart_items (
				cart_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
				customer_id INTEGER NOT NULL REFERENCES customers (customer_id),
				product_id INTEGER NOT NULL REFERENCES products (product_id),
				quantity INTEGER NOT NULL )''')
		connection.execute('''CREATE INDEX IF NOT EXISTS index_cart_item_customer ON cart_items (customer_id)''')
		
		# Cart Status Types Table
		connection.execute('''
			CREATE TABLE IF NOT EXISTS statuses (
				status_id INTEGER PRIMARY KEY,
				status TEXT )''')
		connection.execute('''INSERT OR IGNORE INTO statuses (status_id, status) VALUES (1, 'Pending Payment')''')
		connection.execute('''INSERT OR IGNORE INTO statuses (status_id, status) VALUES (2, 'Failed')''')
		connection.execute('''INSERT OR IGNORE INTO statuses (status_id, status) VALUES (3, 'On Hold')''')
		connection.execute('''INSERT OR IGNORE INTO statuses (status_id, status) VALUES (4, 'Processing')''')
		connection.execute('''INSERT OR IGNORE INTO statuses (status_id, status) VALUES (5, 'Completed')''')
		connection.execute('''INSERT OR IGNORE INTO statuses (status_id, status) VALUES (6, 'Canceled')''')
		connection.execute('''INSERT OR IGNORE INTO statuses (status_id, status) VALUES (7, 'Refunded')''')
		connection.execute('''INSERT OR IGNORE INTO statuses (status_id, status) VALUES (8, 'Backordered')''')
		connection.execute('''INSERT OR IGNORE INTO statuses (status_id, status) VALUES (9, 'Partially Shipped')''')
		connection.execute('''INSERT OR IGNORE INTO statuses (status_id, status) VALUES (10, 'Shipped')''')
		connection.execute('''INSERT OR IGNORE INTO statuses (status_id, status) VALUES (11, 'Out for Delivery')''')
		connection.execute('''INSERT OR IGNORE INTO statuses (status_id, status) VALUES (12, 'Delivered')''')
		
		# Orders Table
		connection.execute('''
			CREATE TABLE IF NOT EXISTS orders (
				order_id INTEGER PRIMARY KEY AUTOINCREMENT,
				customer_id INTEGER NOT NULL REFERENCES customers (customer_id),
				status_id INTEGER NOT NULL REFERENCES statuses (status_id),
				created INTEGER NOT NULL,
				updated INTEGER NOT NULL )''')
		connection.execute('''CREATE INDEX IF NOT EXISTS index_order_customer ON orders (customer_id)''')
		
		# Order Items Table
		connection.execute('''
			CREATE TABLE IF NOT EXISTS order_items (
				order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
				order_id INTEGER NOT NULL REFERENCES orders (order_id),
				product_id INTEGER NOT NULL REFERENCES products (product_id),
				quantity INTEGER NOT NULL,
				unit_price NUMERIC(4, 2) NOT NULL )''')
		connection.execute('''CREATE INDEX IF NOT EXISTS index_order_item_order ON order_items (order_id)''')
	
		connection.commit()
	print("Finished Creating Database and Tables.")

#---------------------[ Populate Tables ]--------------------#
def populate_tables():
	from faker import Faker
	fake = Faker()

	with sqlite3.connect(DATABASE_PATH) as connection:
		cursor = connection.cursor()

		# Generate sample data for customers
		for _ in range(100):
			first_name = fake.first_name()
			last_name = fake.last_name()
			email = fake.email()
			#phone_number = fake.phone_number()
			phone_number = "+1" + str(fake.random_int(min=1000000000, max=9999999999))
			password = generate_password_hash("PASSWORD") #fake.password()
			street = fake.street_address()
			city = fake.city()
			state = fake.state()
			zip_code = fake.zipcode()
			created = int(fake.unix_time())
			updated = created

			cursor.execute("""
				INSERT INTO customers (first_name, last_name, email, phone_number, password, street, city, state, zip_code, created, updated)
				VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
			""", (first_name, last_name, email, phone_number, password, street, city, state, zip_code, created, updated))

		# Generate sample data for product types
		product_types = ["Shirt", "Pants", "Sweater", "Dress"]
		for product_type in product_types:
			cursor.execute("INSERT INTO product_types (product_type) VALUES (?)", (product_type,))

		# Generate sample data for products
		for _ in range(50):
			product_name = fake.word()
			description = fake.sentence()
			unit_price = round(fake.random_int(min=10, max=25000)/100, 2)
			quantity_available = fake.random_int(min=0, max=100)
			product_type_id = fake.random_int(min=1, max=len(product_types))

			cursor.execute("""
				INSERT INTO products (product_name, description, unit_price, quantity_available, product_type_id)
				VALUES (?, ?, ?, ?, ?)
			""", (product_name, description, unit_price, quantity_available, product_type_id))

		# Generate sample data for cart items
		for _ in range(100):
			customer_id = fake.random_element([row[0] for row in cursor.execute("SELECT customer_id FROM customers").fetchall()])
			product_id = fake.random_element([row[0] for row in cursor.execute("SELECT product_id FROM products").fetchall()])
			quantity = fake.random_int(min=1, max=10)

			cursor.execute("""
				INSERT INTO cart_items (customer_id, product_id, quantity)
				VALUES (?, ?, ?)
			""", (customer_id, product_id, quantity))

		# Generate sample data for orders
		for _ in range(50):
			customer_id = fake.random_element([row[0] for row in cursor.execute("SELECT customer_id FROM customers").fetchall()])
			status_id = fake.random_int(min=1, max=12)
			created = int(fake.unix_time())
			updated = fake.random_int(min=created, max=1728000000)

			cursor.execute("""
				INSERT INTO orders (customer_id, status_id, created, updated)
				VALUES (?, ?, ?, ?)
			""", (customer_id, status_id, created, updated) )

		# Generate sample data for order items
		for _ in range(200):
			order_id = fake.random_element([row[0] for row in cursor.execute("SELECT order_id FROM orders").fetchall()])
			product_id = fake.random_element([row[0] for row in cursor.execute("SELECT product_id FROM products").fetchall()])
			quantity = fake.random_int(min=1, max=3)
			unit_price = fake.random_element([row[2] for row in cursor.execute("SELECT product_id, product_name, unit_price FROM products").fetchall()])

			cursor.execute("""
				INSERT INTO order_items (order_id, product_id, quantity, unit_price)
				VALUES (?, ?, ?, ?)
			""", (order_id, product_id, quantity, unit_price))

		print("Finished Populating Tables.")

#--------------------------[ Run ]-------------------------- #
try:
	with sqlite3.connect(DATABASE_PATH) as connection: pass
except sqlite3.OperationalError: DATABASE_PATH = path.basename(DATABASE_PATH)

if __name__ == "__main__":
	create_tables()
	#populate_tables()