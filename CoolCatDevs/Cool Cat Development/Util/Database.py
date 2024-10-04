
#----------------------[ Dependencies ]----------------------#
#from . import Data_Types
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

DATABASE_PATH = "database.db"
			#For longer file extension copy and paste: .\\Resources\\ in front of database.db above #
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

#--------------------------[ Get ]-------------------------- #
def get_customer_id(password:str, email:str|None=None, phone_number:str|None=None) -> int:
	assert email or phone_number, "No email or phone number provided."

	if email:
		data = fetch_one('''SELECT customer_id, password FROM customers WHERE email == ?''', (email,))
	elif phone_number:
		data = fetch_one('''SELECT customer_id, password FROM customers WHERE phone_number == ?''', (phone_number,))
	if len(data) == 0: print("Unable to find data for customer."); return -1

	return data[0] if check_password_hash(data[1], password) else -1

#def get_participants() -> list:
#	return fetch_all('''SELECT * FROM PARTICIPANTS''')

#-------------------------[ Insert ]-------------------------#
#def insert_participant(participant:Data_Types.Participant):
#	execute('''INSERT INTO PARTICIPANTS (name,email,city,country,phone) VALUES (?,?,?,?,?)''', participant.data())
#	print(participant)

#---------------------[ Create Tables ]--------------------- #
with sqlite3.connect(DATABASE_PATH) as connection:
	# Customers Table
	connection.execute('''
		CREATE TABLE IF NOT EXISTS customers (
			customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
			first_name TEXT NOT NULL,
			last_name TEXT NOT NULL,
			email TEXT UNIQUE NOT NULL,
			phone_number TEXT UNIQUE NOT NULL,
			password TEXT NOT NULL,
			street TEXT NOT NULL,
			city TEXT NOT NULL,
			state TEXT NOT NULL,
			zip_code INTEGER NOT NULL,
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
			quantity_available INTEGER NOT NULL,
			product_type_id INTEGER REFERENCES product_types (product_type_id) )''')
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
		CREATE TABLE IF NOT EXISTS status (
			status_id INTEGER PRIMARY KEY,
			status TEXT )''')
	
	# Orders Table
	connection.execute('''
		CREATE TABLE IF NOT EXISTS orders (
			order_id INTEGER PRIMARY KEY AUTOINCREMENT,
			customer_id INTEGER NOT NULL REFERENCES customers (customer_id),
			status_id INTEGER NOT NULL REFERENCES status (status_id),
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
			phone_number = fake.phone_number()
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
			unit_price = round(fake.random_int(min=10, max=100000)/100, 2)
			quantity_available = fake.random_int(min=0, max=100)
			product_type_id = fake.random_element(product_types)  # Assuming product_types are stored as strings

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
			status_id = 1  # Assuming status_id 1 is a default or initial status

			cursor.execute("""
				INSERT INTO orders (customer_id, status_id, created, updated)
				VALUES (?, ?, ?, ?)
			""", (customer_id, status_id, int(fake.unix_time()), int(fake.unix_time())))

		# Generate sample data for order items
		for _ in range(200):
			order_id = fake.random_element([row[0] for row in cursor.execute("SELECT order_id FROM orders").fetchall()])
			product_id = fake.random_element([row[0] for row in cursor.execute("SELECT product_id FROM products").fetchall()])
			quantity = fake.random_int(min=1, max=10)
			unit_price = fake.random_element([row[2] for row in cursor.execute("SELECT product_id, product_name, unit_price FROM products").fetchall()])

			cursor.execute("""
				INSERT INTO order_items (order_id, product_id, quantity, unit_price)
				VALUES (?, ?, ?, ?)
			""", (order_id, product_id, quantity, unit_price))

		print("DONE")