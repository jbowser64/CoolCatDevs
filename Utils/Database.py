#--( Dependencies )------------------------------------------#
from werkzeug.security import generate_password_hash, check_password_hash
from math import floor
from time import time
from os import path
import sqlite3

UTIL_FOLDER_PATH = path.dirname(path.dirname(path.abspath(__file__)))
DATABASE_PATH = path.join(UTIL_FOLDER_PATH, "Resources", "database.db")

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

#--( Login & Signup )----------------------------------------#
def login_customer(email:str, password:str) -> dict:
	assert email, "No email provided."
	assert password, "No password provided."

	data = fetch_one('''SELECT customer_id, first_name, password FROM customers WHERE email == ?''', (email,))
	if len(data) == 0: print("Unable to find data for customer."); return None

	return {
		"id": data[0],
		"first_name": data[1]
	} if check_password_hash(data[2], password) else None

def signup_customer(first_name:str, last_name:str, email:str, password:str) -> dict:
	assert email, "No email provided."
	assert password, "No password provided."
	
	data = login_customer(
		email	 = email, 
		password = password )
	if data: return data

	created = generate_timestamp(); updated = created
	hashed_password = generate_password_hash(password)
	execute('''INSERT INTO customers (first_name, last_name, password, email, created, updated) VALUES (?, ?, ?, ?, ?, ?)''', 
		(first_name, last_name, hashed_password, email, created, updated))
	print(created)

	return login_customer(email, password)

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
def place_order(customer_id:int) -> bool:
	assert customer_id, "No customer id provided."

	print("PLACE ORDER")

	timestamp = generate_timestamp()

	execute('''
		INSERT INTO orders (
			customer_id, 
			status_id, 
			created,
			updated )
		VALUES (?, 1, ?, ?)
	''', (customer_id, timestamp, timestamp))

	order_id = fetch_one('''
		SELECT order_id
		FROM orders
		WHERE customer_id = ?
		ORDER BY created DESC
		LIMIT 1
	''', (customer_id,))

	cart_items = fetch_all('''
		SELECT
			product_variant_id,
			quantity
		WHERE customer_id = ?
	''', (customer_id,))

	for item in cart_items:
		product_variant_id, quantity = item
		unit_price = fetch_one('''
			SELECT unit_price
			FROM product_variants
			WHERE product_variant_id = ?
		''', (product_variant_id,))

		execute('''
			INSERT INTO order_items (
				order_id,
				product_variant_id,
		  		quantity,
				unit_price )
			VALUES (?, ?, ?, ?)
		''', (order_id, product_variant_id, quantity, unit_price))

	execute('''
		DELETE FROM cart_items
		WHERE customer_id = ?
	''', customer_id)

	return True

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

#--( Run )---------------------------------------------------#
try:
	with sqlite3.connect(DATABASE_PATH) as connection: pass
except sqlite3.OperationalError: DATABASE_PATH = path.basename(DATABASE_PATH)

