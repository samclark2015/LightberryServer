from functools import wraps

from bson import json_util
from flask import Blueprint

from db import db
from routes.api import requires_auth

admin = Blueprint('admin', __name__, )

def requires_admin(f):
    """Determines if the Access Token is valid
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        print(kwargs)
        return f(*args, **kwargs)

    return decorated

@admin.route('/devices')
@requires_auth
@requires_admin
def listDevices(user=None):
    devices = db.devices.find({})
    return json_util.dumps(devices)
