## Set up the Google Secrets cloud service

This project uses **Google Cloud Secret Manager**. Enable the **Secret Manager API**
once for the Google Cloud project that will store the application's secrets.
This feature is used to store and retrieve SSL certificate passwords and the
**Firebase Admin SDK** key file.

### Create a Google Cloud project

1. Open [Manage resources](https://console.cloud.google.com/cloud-resource-manager).
2. Click **Create project**.
3. Enter a project name. Select a billing account if applicable, and choose the
   parent organization or folder if prompted.
4. Click **Create** and wait for the project to finish provisioning.
5. Note the project ID. Select the new project in the project selector before
   continuing.

Creating a project requires the Project Creator role. To attach a billing
account, you may also need permission to use that billing account.

### Enable the Secret Manager API in the console

1. Open the [Secret Manager API page](https://console.cloud.google.com/apis/library/secretmanager.googleapis.com).
2. Confirm the newly created project is selected in the project selector.
3. Click **Enable**. If the API is already enabled, the page will show that instead.

You need permission to enable services in the project. If you cannot enable the
API, ask a project administrator to enable it for you.

### Enable it with the Google Cloud CLI

If you prefer the CLI, create the project and enable the API with:

```sh
gcloud projects create PROJECT_ID --name="PROJECT_NAME"
gcloud config set project PROJECT_ID
gcloud services enable secretmanager.googleapis.com
gcloud services list --enabled
```

Replace `PROJECT_ID` with a unique project ID and `PROJECT_NAME` with a display
name. If your organization requires a parent organization or folder, add
`--organization=ORGANIZATION_ID` or `--folder=FOLDER_ID` to the project creation
command. Confirm that `secretmanager.googleapis.com` appears in the enabled
services.

For details, see Google's [project creation guide](https://cloud.google.com/resource-manager/docs/creating-managing-projects) and [Secret Manager API setup guide](https://cloud.google.com/secret-manager/docs/configuring-secret-manager).

### Download and configure Google Cloud Console

The Google Cloud Console must be downloaded because it is used by the app to
extract the **ADC (Application Default Credentials)** to perform actions on
the cloud with **Google Services** such as **Firebase**.

### Download the CLI

```powershell
# Windows

(New-Object Net.WebClient).DownloadFile("https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe", "$env:Temp\GoogleCloudSDKInstaller.exe")

& $env:Temp\GoogleCloudSDKInstaller.exe


gcloud init

```


```bash

# Linux

'''
Linux 64-bit
(x86_64)

google-cloud-cli-linux-x86_64.tar.gz	94.8 MB	8cf5b2d7987e7aac008264fecda7c083423227ecfb26878707bd20c6219d7dab
Linux 64-bit
(Arm)

google-cloud-cli-linux-arm.tar.gz	90.8 MB	024e450ccaa5d82e146c6acadfc6e12d29dd158a39862c304e07632a47287d00
Linux 32-bit
(x86)

google-cloud-cli-linux-x86.tar.gz	54.9 MB	8ef10f57958336804967b638d4b34e8d003ad98fd4660533d8c7720ed57d6e19
'''


curl -O https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz

tar -xf google-cloud-cli-linux-x86_64.tar.gz

# From inside the directory of the extracted file
./google-cloud-sdk/install.sh

gcloud init

```

## Configure the Python environment

The server app is a configuration-driven hybrid architecture.
This means that the app's operation and behaviour is controlled
through the app's configuration file and also that the app
can be ran as in a monolithic architecture configuration
as well as a microservices archtecture configuration.

### Create the Python virtual environment

```powershell

cd "Pytacte\Pytacte-py"

python -m venv ./

```

```bash
cd Pytacte/Pytacte-py

python3 -m venv ./ | python -m ./venv ./

```


### Download the dependencies

```powershell

# Windows

(& .\Scripts\Activate.ps1)

pip install -r requirements.txt

```

```bash

# Linux

./Scripts/activate

pip install -r requirements.txt
```

## Initialise the app

On first launch, if no configuration file exists, the app creates one and stops
so you can fill in the required settings.

```json
{
    "general": {
        "ip_address": "127.0.0.1",
        "port_number": 80,
        "address": "127.0.0.1:80",
        "is_load_balancer_node": true,
        "audio_stream_byte_rate_per_second": 80000,
        "database_url": "REPLACE_WITH_FIREBASE_YOUR_DATABASE_URL",
        "server_id": "server_1"
    },
    "security": {
        "encrypt_stream": true,
        "tls": true,
        "encrypt_cert": false,
        "generate_self_signed": false,
        "server_cert": "server_cert.pem",
        "private_key": "private_key.pem",
        "reverse_proxy": false
    },
    "transcription": {
        "max_transcription_jobs_per_user": 10
    },
    "firebase": {
        "firebase_key_name": "KEY_NAME"
    }
}
```

### Set the required values

1. Set `database_url` to the URL of your Firebase Realtime Database. The server
   uses it to read and write transcription session metadata and server metrics.
   Load balancers use those metrics to determine which servers are available to
   clients.
2. In Firebase, open **Settings > Service Accounts** and generate a new private
   key. Save the downloaded key in `Pytacte-py/data`, then set `firebase_key_name`
   in the configuration to the key's filename.

After updating these values, restart the server.

### Choose a deployment setup

The same server app can run as a single instance or across several instances.
Each instance serves transcription requests and publishes its availability to
the shared Firebase Realtime Database. The `is_load_balancer_node` setting
selects which instance also cleans up expired records and orders available
servers for clients.

The tables and JSON fragments below show the settings that change for each
deployment. The fragments are partial: merge them into the matching sections of
the full configuration file created on first launch. The number of server
instances and the network transport are independent choices: first choose one
server or multiple servers, then choose a reverse proxy or direct TLS below.

#### One server

Use one instance when a single machine will handle transcription and coordinate
the available-server list. Set `is_load_balancer_node` to `true`.

| Setting | Example | Purpose |
| --- | --- | --- |
| `server_id` | `server_1` | Identifies this instance in Firebase. |
| `address` | `server.example.com:443` | Address clients use to reach this instance. |
| `is_load_balancer_node` | `true` | Runs cleanup and server-ordering tasks. |

```json
{
    "general": {
        "server_id": "server_1",
        "address": "server.example.com:443",
        "is_load_balancer_node": true
    }
}
```

#### Multiple servers

Run the app on each machine and give every instance a unique `server_id` and a
client-reachable `address`. Set `is_load_balancer_node` to `true` on exactly one
instance; set it to `false` on all worker instances. All instances should use the
same `database_url`, Firebase credentials, and `max_transcription_jobs_per_user`
so they share server and transcription-job data consistently.

| Setting | Coordinator | Worker |
| --- | --- | --- |
| `server_id` | `server_a` | `server_b` |
| `address` | `server-a.example.com:443` | `server-b.example.com:443` |
| `is_load_balancer_node` | `true` | `false` |
| `database_url` | Same Firebase database URL | Same Firebase database URL |
| `max_transcription_jobs_per_user` | Same limit | Same limit |

Save a separate full configuration file on each machine. For example, the
`general` section on the coordinator and worker would contain:

```json
{
    "general": {
        "server_id": "server_a",
        "address": "server-a.example.com:443",
        "is_load_balancer_node": true
    }
}
```

```json
{
    "general": {
        "server_id": "server_b",
        "address": "server-b.example.com:443",
        "is_load_balancer_node": false
    }
}
```

#### Running behind a reverse proxy

You can place a reverse proxy in front of either deployment. The proxy accepts
the public connection and forwards it to the app. Set `address` to the public
host and port, and set `ip_address` and `port_number` to the app's listener
behind the proxy. Enable `reverse_proxy`; the proxy should terminate TLS and set
`X-Forwarded-For` to the actual client address. Set `tls` to `true` when the
public endpoint uses HTTPS/WSS. The app does not terminate TLS in reverse-proxy
mode, so the proxy-to-app connection can use plain HTTP/WebSocket on a trusted
network.

| Setting | Example | Purpose |
| --- | --- | --- |
| `ip_address` | `127.0.0.1` | App's local listener, reachable by the proxy. |
| `port_number` | `80` | Port the proxy forwards requests to. |
| `address` | `api.example.com:443` | Public address clients use. |
| `reverse_proxy` | `true` | Uses the forwarded client IP for rate limiting. |
| `encrypt_stream` | `false` | TLS is terminated by the proxy. |
| `tls` | `true` | Tells clients to use a secure WebSocket. |

```json
{
    "general": {
        "ip_address": "127.0.0.1",
        "port_number": 80,
        "address": "api.example.com:443"
    },
    "security": {
        "reverse_proxy": true,
        "encrypt_stream": false,
        "tls": true
    }
}
```

#### Direct TLS without a reverse proxy

If clients connect directly to the app, the app itself must terminate TLS. Set
`reverse_proxy` to `false`, `encrypt_stream` to `true`, and `tls` to `true`.
Provide a trusted certificate and private key in the `data` directory using the
filenames set by `server_cert` and `private_key`. Self-signed certificates are
available for development or testing, but production clients should use a
certificate trusted for the server's public hostname.

| Setting | Example | Purpose |
| --- | --- | --- |
| `ip_address` | `0.0.0.0` | Listens on the server's network interfaces. |
| `port_number` | `443` | TLS port clients connect to. |
| `address` | `server.example.com:443` | Public server address clients use. |
| `reverse_proxy` | `false` | No reverse proxy is forwarding connections. |
| `encrypt_stream` | `true` | Enables TLS on the app's WebSocket listener. |
| `tls` | `true` | Tells clients to use a secure WebSocket. |
| `server_cert` / `private_key` | `server_cert.pem` / `private_key.pem` | Certificate and key files in `data`. |

```json
{
    "general": {
        "ip_address": "0.0.0.0",
        "port_number": 443,
        "address": "server.example.com:443"
    },
    "security": {
        "reverse_proxy": false,
        "encrypt_stream": true,
        "tls": true,
        "generate_self_signed": false,
        "server_cert": "server_cert.pem",
        "private_key": "private_key.pem"
    }
}
```

### Configuration reference

#### General

**`ip_address`** sets the address where the server listens for transcription requests.

**`port_number`** sets the port where the server listens for client requests.

**`address`** is the address clients use to reach the server. It can be the
server's IP address, a DNS name that points to that IP, or a reverse proxy
address. The `ip_address` and `port_number` values determine where the server
application itself listens.

**`is_load_balancer_node`** determines whether this instance performs load
balancing tasks, such as removing expired server records and ordering available
servers by CPU usage. For a deployment with multiple server instances, enable
this on **only one instance**.

**`audio_stream_byte_rate_per_second`** sets how many bytes a client can send per
second on the audio stream. The bytes are queued through a leaky bucket and sent
to the transcription pipeline.

**`database_url`** is the Firebase Realtime Database URL used by the application.

**`server_id`** is the required identifier for this server instance.

#### Security

**`encrypt_stream`** controls whether the server uses a secure WebSocket
connection (`wss://`) or an unencrypted one (`ws://`). This setting is ignored
when a reverse proxy is configured. Without a reverse proxy, enable it when the
server listens on an address other than loopback.

**`tls`** controls whether the client connects using a secure WebSocket. Enable
it for production deployments; unencrypted WebSocket connections are restricted
to loopback addresses during development.

**`encrypt_cert`** controls whether the generated private key is password
protected. When enabled, the app stores the password in Google Cloud Secret
Manager, so Secret Manager must be configured and accessible to the app.

**`generate_self_signed`** tells the app to create a self-signed certificate and
private key when the configured certificate file does not already exist. If it
is disabled and the certificate file is missing, startup fails.

**`server_cert`** is the certificate filename in the app's `data` directory.

**`private_key`** is the private key filename in the app's `data` directory.
If you use a custom certificate with a password-protected private key, create a
Google Cloud Secret Manager secret named `private_key_password` and set its
value to the private key's password.

**`reverse_proxy`** tells the app it is behind a reverse proxy. When enabled,
the app uses the first address in the `X-Forwarded-For` header for client IP
rate limiting, falling back to the connection address if the header is absent.

#### Transcription

**`max_transcription_jobs_per_user`** sets the maximum number of active
transcription jobs allowed for each user.

#### Firebase

**`firebase_key_name`** is the filename of the Firebase Admin SDK service account
key in the app's `data` directory. On first use, the app stores the key in Google
Cloud Secret Manager and removes the local key file.




