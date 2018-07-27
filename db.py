from pymongo import MongoClient

client = MongoClient('192.168.1.3', 27017)
db = client.lightberry