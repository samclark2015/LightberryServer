import os
from pymongo import MongoClient

HOST = os.getenv('DB_HOST')
PORT = os.getenv('DB_PORT')

client = MongoClient(HOST, int(PORT))
db = client.lightberry
