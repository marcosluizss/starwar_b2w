import requests
import datetime

from flask import Flask, jsonify, url_for, redirect, request
from pymongo import MongoClient 
from flask_restful import Api, Resource, reqparse

app = Flask(__name__)
mongo = MongoClient('localhost:27017')

app_url = 'http://127.0.0.1:5000/api'

url_swapi = 'https://swapi.co/api/planets/?search='

def get_next_sequence(name):
	sequence = 0
	try: 
		mongo.db.counters.update({"_id":name},{"$inc": {"seq": 1}})
		ret = mongo.db.counters.find_one({"_id":name}).json()
		sequence = ret['seq']
	except:
		#mongo.db.counters.insert({"_id":name, "seq":0})
		mongo.db.counters.update({"_id":name},{"$inc": {"seq": 1}})
		ret = mongo.db.counters.find_one({"_id":name})
		sequence = ret['seq']

	return sequence

def get_diff_days(update_time):
	now_time = datetime.datetime.now()
	diff_date = now_time - update_time
	return diff_date.days

def get_films_count(name):
	film_count = 0
	try:
		url = url_swapi + name
		r = requests.get(url)
		p = r.json()
		film_count = len(p['results'][0]['films'])
	except:
		print("erro na acesso a swapi")		

	return film_count

def get_films_count_select(name,update_time,films_count_old):
	films_count = films_count_old
	if get_diff_days(update_time) > 30: #atualiza se tiver mais de 30 dias da ultima atualização
		films_count = get_films_count(name)
		if films_count != films_count_old:
			update_films_count(name,films_count) 
			
	return films_count

def update_films_count(name,films_count):
	planet = {
		'films_count': films_count
	} 
	mongo.db.b2w_starwar.update({"name":name},{ "$set": planet})
	return

def search_planets(planet_id:None, data, search:None):
	if planet_id:
		planet = mongo.db.b2w_starwar.find_one({"_id":planet_id},{"_id": 0})
		if planet: 
			planet['films_count'] = get_films_count_select(name= planet['name'], update_time=planet['update_time'],films_count_old=planet['films_count'])
			del planet['update_time']
			data.append(planet)
	else:
		if search:			
			cursor = mongo.db.b2w_starwar.find({"name":{ "$regex": search} }, {"_id": 0 })
		else:
			cursor = mongo.db.b2w_starwar.find({}, {"_id": 0 })
		for planet in cursor:
			planet['films_count'] = get_films_count_select(name= planet['name'], update_time=planet['update_time'],films_count_old=planet['films_count'])
			del planet['update_time']
			data.append(planet)	

	return

class PlanetById(Resource):

	def __init__(self):
		self.reqparse = reqparse.RequestParser()
		self.reqparse.add_argument('name', type=str, required=True,
									help='Por favor, informe o nome do planeta.',
									location='json')
		self.reqparse.add_argument('climate', type=str, required=True,
									help='Por favor, informe o clima do planeta.',
									location='json')
		self.reqparse.add_argument('terrain', type=str, required=True,
									help='Por favor, informe o terreno do planeta.',
									location='json')
		super(PlanetById, self).__init__()

	def get(self, planet_id):
		data = []
		search_planets(planet_id = planet_id, data = data, search= None)
		print(data)
		return jsonify({"response": data})

	def put(self,planet_id):
		args = self.reqparse.parse_args()

		if mongo.db.b2w_starwar.find_one({"_id": planet_id}):
			if mongo.db.b2w_starwar.find_one({"name": args['name'], "_id" :{"$ne" : planet_id}}):
				return {"response": "Já existe um Planeta com o nome "+args['name']+"."}
			else:
				planet = {
					'name': args['name'],
					'climate': args['climate'],
					'terrain': args['terrain'],
					'films_count': get_films_count(args['name']),
					'update_time': datetime.datetime.now()
				} 
				mongo.db.b2w_starwar.update({"_id":planet_id},{ "$set": planet})
				return redirect(url_for("planets"))
		else:
			return {"response": "Planeta "+str(planet_id)+" não encontrado."},404

	def delete(self, planet_id):
		
		if mongo.db.b2w_starwar.find_one({"_id": planet_id}):				
			mongo.db.b2w_starwar.remove({'_id': planet_id})
			return redirect(url_for("planets"))
		else:
			return {"response": "Planeta "+str(planet_id)+" não encontrado."},404

class Planets(Resource):

	def __init__(self):
		self.reqparse = reqparse.RequestParser()
		self.reqparse.add_argument('name', type=str, required=True,
									help='Por favor, informe o nome do planeta.',
									location='json')
		self.reqparse.add_argument('climate', type=str, required=True,
									help='Por favor, informe o clima do planeta.',
									location='json')
		self.reqparse.add_argument('terrain', type=str, required=True,
									help='Por favor, informe o terreno do planeta.',
									location='json')
		super(Planets, self).__init__()

	def get(self):
		data = []
		search = None

		args = request.args
		if 'search' in args:
			search =  args['search']

		search_planets(planet_id = None, data = data, search = search)
		return jsonify({"response": data})

	def post(self):
		args = self.reqparse.parse_args()
		print(args['name'])
		if mongo.db.b2w_starwar.find_one({"name": args['name']}):
			print(args['name'])
			return {"response": "Já existe um planeta com o nome "+args['name']+"."}
		else:
			print(args['name'])
			planet = {
				'_id': get_next_sequence("planetsid"),
				'name': args['name'],
				'climate': args['climate'],
				'terrain': args['terrain'],
				'films_count': get_films_count(args['name']),
				'update_time': datetime.datetime.now()
			}
			mongo.db.b2w_starwar.insert(planet)
			return redirect(url_for("planets"))

class Index(Resource):
	def get(self):
		return redirect(url_for("planets"))


api = Api(app)
api.add_resource(Index, "/", endpoint="index")
api.add_resource(Planets, "/api/planets", endpoint="planets")
api.add_resource(PlanetById, "/api/planets/<int:planet_id>", endpoint="planetById")

if __name__ == "__main__":
	app.run(debug=True)