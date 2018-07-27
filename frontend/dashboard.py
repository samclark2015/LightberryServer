from flask import Blueprint, session, redirect, request, render_template, url_for, flash
from functools import wraps
from utilities import getUserFromLogin
from six.moves.urllib.parse import urlencode
import os
from dotenv import load_dotenv

from pathlib import Path  # python3 only
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

def getDashboard(auth0, store):
    dashboard = Blueprint('dashboard', __name__, template_folder='templates')

    def requires_auth(f):
      @wraps(f)
      def decorated(*args, **kwargs):
        if 'profile' not in session:
          # Redirect to Login page here
          return redirect('/login')
        return f(*args, **kwargs)

      return decorated

    @dashboard.route('/')
    @requires_auth
    def index():
        return redirect(url_for('dashboard.dash'))


    @dashboard.route('/dashboard')
    @requires_auth
    def dash():
        userId = session['profile']['user_id']
        devices = [store.getDevice(x[1]) for x in store.Links if x[0] == userId]
        return render_template('dashboard.html', devices=devices)

    @dashboard.route('/login')
    def login():
        return render_template('login.html')

    @dashboard.route('/login-redirect')
    def loginAuth():
        callbackUrl = os.getenv('AUTH0_CALLBACK_URL')
        return auth0.authorize_redirect(redirect_uri=callbackUrl, audience=os.getenv('AUTH0_AUDIENCE'))

    @dashboard.route('/logout')
    @requires_auth
    def logout():
        # Clear session stored data
        session.clear()
        # Redirect user to logout endpoint
        params = {'returnTo': os.getenv('EXTERNAL_URL'), 'client_id': os.getenv('AUTH0_CLIENT_ID')}
        return redirect(auth0.api_base_url + '/v2/logout?' + urlencode(params))

    @dashboard.route('/callback')
    def callback_handling():
        userInfo = getUserFromLogin(auth0)

        # Store the tue user information in flask session.
        session['jwt_payload'] = userInfo

        session['profile'] = {
            'user_id': userInfo['sub'],
            'name': userInfo['name'],
            'picture': userInfo['picture']
        }

        return redirect(url_for('dashboard.dash'))

    @dashboard.route('/link', methods=['POST'])
    @requires_auth
    def device_linking():
        userId = session['profile']['user_id']
        if request.method == 'POST':
            content = request.form
            if content.get('method') == 'DELETE':
                deviceId = content.get('device-id')
                devices = [x for x in store.Devices if x.deviceId == deviceId]
                if len(devices) < 1:
                    return 'Device not found!'
                device = devices[0]
                store.deleteLink(device.deviceId)
                return redirect(url_for('dashboard.dash'))
            else:
                pairingCode = content.get('pairing-code')
                devices = [x for x in store.Devices if x.pairingCode == pairingCode]
                if len(devices) < 1:
                    flash('Device not registered!')
                    return redirect(url_for('dashboard.dash'))
                device = devices[0]

                linkedDevices = [x for x in store.Links if x[1] == device.deviceId]
                if len(linkedDevices) != 0:
                    flash('Device is already linked.')
                else:
                    store.addLink((userId, device.deviceId))
                return redirect(url_for('dashboard.dash'))
        else:
            return redirect(url_for('dashboard.dash'))


    return dashboard
