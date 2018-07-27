# LightBerry
An open source home automation platform with Alexa integration

Server exposes a REST API for device control, as well as provides a user dashboard for linking devices to accounts. User management provided by Auth0. Client devices communicate via MQTT.

### Setup
The default client implementations contain device metadata within the `config.py` files. Values to be changed include `deviceId` and `pairingCode`.
These values must be unique across devices, so a UUID should be used for the device ID and a randomly generated, yet easily typed code, should be used for the pairing code.
See the below [Environment Variables](#environment-variables) section for necessary variables to be set.

### REST Endpoints
All endpoints require an authorization token provided by Auth0 passed through the `Authorization` header.
- `GET /api/devices`
  - List of devices as JSON
  - Returns `[{ <deviceId>: <status> }, ...]`
- `GET /api/devices/alex`
  - Returns list of devices in JSON format appropriate for Alexa device discovery
- `POST /api/devices/link`
  - endpoint to link device to account
  - Request body JSON: `{ 'pairingCode': '<pairingCode>' }`
- `GET /api/devices/<deviceId>`
  - Status of device as JSON:
  - Returns `{ status: <status> }`
- `GET /api/devices/<deviceId>`
  - Set new state for device
  - Request body JSON: `{ 'status': '<status>' }`

### Supported Device Types
This list will be updated as more device implementations become supported:
- Host (server)
  - MQTT Topics
    - `host/online`: Subscribe to receive messages when server comes online (useful for registering devices)
- Switch (on/off)
  - Valid States
    - Off: `0`
    - On: `1`
  - MQTT Topics
    - `{deviceId}/online`: Subscribe to receive messages when the device requests to register with the server
    - `{deviceId}/on`: Publish to turn on the device
    - `{deviceId}/off`: Publish to turn off the device
    - `{deviceId}/status`: Subscribe to receive status updates about the device

### Environment Variables
#### Server
The supplied server implementation requires the following variables to defined in a `.env` file within the `server` directory:
```
MQTT_SERVER: server hosting MQTT broker

MQTT_PORT: port on which to connect to MQTT broker

HTTP_PORT: port on which to host client dashboard

EXTERNAL_URL: external URL dashboard site may be accessed at (used for Auth0 authentication)

SECRET: random secret used to authenticate clients to server (will be changed for more secure method)

AUTH0_CLIENT_ID: client ID obtained from Auth0

AUTH0_CLIENT_SECRET: client SECRET obtained from Auth0

AUTH0_API_BASE_URL: base URL of Auth0 API

AUTH0_ACCESS_TOKEN_URL: access token URL of Auth0 API (usually AUTH0_API_BASE_URL+'/oauth/token')

AUTH0_AUTHORIZE_URL: authorize URL of Auth0 API (usually AUTH0_API_BASE_URL+'/authorize')

AUTH0_CALLBACK_URL: callback URL of Auth0 API (usually EXTERNAL_URL+'/callback')

AUTH0_AUDIENCE: user info URL of Auth0 API (usually AUTH0_API_BASE_URL+'/userinfo')
```

#### Client
The supplied client implementations require the following variables to defined in a `.env` file within the associated client's base directory:
```
MQTT_SERVER: server hosting MQTT broker

MQTT_PORT: port on which to connect to MQTT broker

SECRET: random secret used to authenticate clients to server (defined in server environment)
```

For more info, see https://github.com/theskumar/python-dotenv
