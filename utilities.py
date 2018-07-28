import requests
from data import Store
import pickle
import os


def getUserFromLogin(auth0):
    # Handles response from token endpoint
    resp = auth0.authorize_access_token()

    token = resp['access_token']

    return getUserFromToken(token)


def getUserFromToken(token):
    url = 'https://samclarkme.auth0.com/userinfo'
    headers = {'authorization': 'Bearer {}'.format(token)}
    resp = requests.get(url, headers=headers)
    if resp.ok:
        return resp.json()
    else:
        print(resp.status_code)
        return None


def toEndpoint(device):
    metadata = device.get('metadata')
    alexa = metadata.get('alexa')
    endpoint = {
        "endpointId": metadata.get('deviceId'),
        "manufacturerName": metadata.get('manufacturerName'),
        "friendlyName": metadata.get('friendlyName'),
        "description": metadata.get('description'),
        "displayCategories": alexa.get('displayCategories'),
        "cookie": alexa.get('additionalDetails'),
        "capabilities": alexa.get('capabilities')
    }
    return endpoint


def loadData(filename):
    try:
        pickleFile = open(filename, 'rb')
        unpickler = pickle.Unpickler(pickleFile)
        store = unpickler.load()
        pickleFile.close()
        print('Data loaded.')
    except Exception as error:
        store = Store()
        print('New data store.')
        print(error)
    return store


def saveData(filename, store):
    try:
        pickleFile = open(filename, 'wb')
        pickler = pickle.Pickler(pickleFile)
        pickler.dump(store)
        pickleFile.close()
        print('Data saved.')
    except:
        print('Error saving data!')
