import logging
import os

from authlib.flask.client import OAuth
from flask import Flask
from flask_cors import CORS

from routes.admin import admin
from routes.api import api

secret = os.getenv('SECRET')

app = Flask(__name__)
CORS(app)
oauth = OAuth(app)
app.secret_key = secret

# Logging setup
logger = logging.getLogger('lightberry_server')
logger.setLevel(logging.DEBUG)
# logging.basicConfig(format='%(asctime)s %(message)s', filename='/var/log/lightberry.log')


auth0 = oauth.register(
    'auth0',
    client_id=os.getenv('AUTH0_CLIENT_ID'),
    client_secret=os.getenv('AUTH0_CLIENT_SECRET'),
    api_base_url='https://{}'.format(os.getenv('AUTH0_DOMAIN')),
    access_token_url='https://{}/oauth/token'.format(os.getenv('AUTH0_DOMAIN')),
    authorize_url='https://{}/authorize'.format(os.getenv('AUTH0_DOMAIN')),
    client_kwargs={
        'scope': 'openid profile',
    },
)

# store = loadData('data.pkl')

app.register_blueprint(api, url_prefix='/api')
app.register_blueprint(admin, url_prefix='/api/admin')


if __name__ == '__main__':
    port = os.getenv('HTTP_PORT', 1997)
    app.run(host='0.0.0.0', port=port, debug=True)
