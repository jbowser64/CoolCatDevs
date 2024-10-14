

class Participant:
	def __init__(self, name:str|None=None, email:str|None=None, city:str|None=None, country:str|None=None, phone:str|None=None):
		self.name	 = name
		self.email	 = email
		self.city	 = city
		self.country = country
		self.phone	 = phone

	def __str__(self) -> str:
		return f"Participant: {self.name}\n ├ Location: {self.city} [{self.country}]\n ├ Email: {self.email}\n └ Phone: {self.phone}"

	def data(self) -> tuple:
		return (self.name, self.email, self.city, self.country, self.phone)