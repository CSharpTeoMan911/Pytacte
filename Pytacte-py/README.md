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

On first launch, if `data/server_config.json` does not exist, the app creates it
with the defaults below. Set the Firebase values before relying on the server.
Caddy starts automatically whenever the app starts; there is no setting to turn
the reverse proxy or TLS off.

```json
{
    "general": {
        "ip_address": "127.0.0.1",
        "port_number": 80,
        "address": "127.0.0.1:8443",
        "is_load_balancer_node": true,
        "database_url": "REPLACE_WITH_FIREBASE_YOUR_DATABASE_URL",
        "server_id": "server_1",
        "max_requests_per_minute": 100
    },
    "transcription": {
        "max_transcription_jobs_per_user": 10
    },
    "firebase": {
        "firebase_key_name": "KEY_NAME"
    },
    "caddy_reverse_proxy": {
        "is_dev": true
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
3. If you already have a `data/server_config.json`, add
   `max_requests_per_minute` under `general`; existing configuration files are
   not automatically updated with new defaults.

After updating these values, restart the server.

### Choose a deployment setup

The same server app can run as a single instance or across several instances.
Each instance serves transcription requests and publishes its availability to
the shared Firebase Realtime Database. The `is_load_balancer_node` setting
selects which instance also cleans up expired records and orders available
servers for clients.

The server always runs behind Caddy. The `caddy_reverse_proxy.is_dev` setting
selects the development or production Caddyfile. The number of server instances
and the load-balancer role are separate deployment choices.
The JSON fragments below are partial; merge them into the configuration file
created on first launch. Set `is_dev` to `false` when following the production
examples.

#### Using the bundled Caddy reverse proxy

The app downloads the matching Caddy binary if needed and starts Caddy
automatically. Caddy terminates TLS and forwards WebSocket traffic to the local
Python server. TLS is always used for client connections; the app no longer has
certificate-file, certificate-generation, direct-TLS, or TLS-toggle settings.

| Setting | Value | Effect |
| --- | --- | --- |
| `caddy_reverse_proxy.is_dev` | `true` | Uses `Caddy/Caddyfile-dev.caddy` for local development. This is the default. |
| `caddy_reverse_proxy.is_dev` | `false` | Uses `Caddy/Caddyfile-prod.caddy` for production. |

The app creates either Caddyfile if it is missing and leaves existing files
unchanged. The binary is stored in `Caddy/caddy-server.exe` on Windows and
`Caddy/caddy-server` on other supported systems. Caddy output is appended to
`Caddy/caddy_server_log.txt`. Stop the Python server normally so it can stop the
Caddy process it started.

##### Development Caddy setup

The default `Caddy/Caddyfile-dev.caddy` listens on `127.0.0.1:8443`, uses a
certificate from Caddy's internal CA, and forwards requests to the app at
`127.0.0.1:80`. The matching settings are:

```json
{
    "general": {
        "ip_address": "127.0.0.1",
        "port_number": 80,
        "address": "127.0.0.1:8443"
    },
    "caddy_reverse_proxy": {
        "is_dev": true
    }
}
```

This development listener is loopback-only, so clients must run on the same
machine. Trust Caddy's local root certificate on each client that connects;
otherwise secure WebSocket clients will reject the certificate. Caddy tries to
install the root certificate automatically. On Windows, its default storage
location is under `%AppData%\Caddy\pki\authorities\local\root.crt`. See Caddy's
[Local HTTPS documentation](https://caddyserver.com/docs/automatic-https#local-https)
for trust-store details.

##### Production Caddy setup

Before using `Caddy/Caddyfile-prod.caddy`, edit its site address, `default_sni`,
ACME contact email, and upstream to match your deployment. The current template
uses public TCP port `3000` and forwards requests to the app at
`127.0.0.1:5000`. Set the app's `general.ip_address` to `127.0.0.1`,
`general.port_number` to `5000`, and `general.address` to the public host with
port `3000`. Set `caddy_reverse_proxy.is_dev` to `false`. For example:

```json
{
    "general": {
        "ip_address": "127.0.0.1",
        "port_number": 5000,
        "address": "api.example.com:3000"
    },
    "caddy_reverse_proxy": {
        "is_dev": false
    }
}
```

Point public DNS at the server and configure both the VPS host firewall and any
cloud firewall to allow inbound TCP connections on ports 80 and 443 for Caddy's
ACME certificate validation and renewal, and port 3000 for clients to reach the
reverse proxy. The supplied template requests Let's Encrypt's `shortlived`
profile; keep Caddy running so it can renew certificates automatically. Use the
same public hostname or IP in the Caddyfile and `general.address`. Configure
clients with that public address and port `3000`; loopback addresses are
reachable only from the server machine. See Let's Encrypt's
[certificate profile information](https://letsencrypt.org/docs/profiles/) for
details.

##### Oracle Cloud VPS firewall rules

Configure both the Oracle Linux host firewall and the Oracle Cloud ingress
rules so the server is reachable from the public internet. In the OCI VCN,
create and enable an Internet Gateway, associate the VPS subnet with a route
table containing `0.0.0.0/0` routed to that gateway, and ensure the subnet is
public and the instance has a public IP address. Then add ingress rules to the
instance's Network Security Group (NSG) or subnet security list for TCP ports
`80`, `443`, and `3000`. On the VPS, allow the same traffic through
`firewalld`. First identify the active zone attached to the network interface:

```bash
sudo firewall-cmd --get-active-zones
```

Replace `public` below with that zone if it has a different name, then add the
rules permanently and reload the firewall:

```bash
sudo firewall-cmd --permanent --zone=public --add-service=ssh
sudo firewall-cmd --permanent --zone=public --add-service=http
sudo firewall-cmd --permanent --zone=public --add-service=https
sudo firewall-cmd --permanent --zone=public --add-port=3000/tcp
sudo firewall-cmd --reload
sudo firewall-cmd --zone=public --list-all
```

See Oracle's [Internet Gateway documentation](https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/managingIGs.htm)
for VCN gateway and route-table setup details.

When the application runs as a non-root user, grant the downloaded Caddy binary
permission to bind the privileged ports 80 and 443. Run this after Caddy has
been downloaded; repeat it if the binary is replaced:

```bash
sudo setcap 'cap_net_bind_service=+ep' /home/opc/Pytacte-py/Caddy/caddy-server
```

Keep the app backend on `127.0.0.1:5000` when Caddy runs on the
same machine; port `5000/tcp` does not need to be exposed publicly in that
setup. Open it only when clients or a proxy on another machine need direct
access to the backend. WebSocket connections use the same public Caddy listener
on port `3000`; the `ws-discovery-client` and `ws-discovery-tcp` firewalld
services are for WS-Discovery and are not required for ordinary WebSocket
traffic.

#### One server

Use one instance when a single machine will handle transcription and coordinate
the available-server list. Set `is_load_balancer_node` to `true`.

| Setting | Example | Purpose |
| --- | --- | --- |
| `server_id` | `server_1` | Identifies this instance in Firebase. |
| `address` | `api.example.com:3000` | Public Caddy address clients use to reach this instance. |
| `is_load_balancer_node` | `true` | Runs cleanup and server-ordering tasks. |

```json
{
    "general": {
        "server_id": "server_1",
        "address": "api.example.com:3000",
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
| `address` | `server-a.example.com:3000` | `server-b.example.com:3000` |
| `is_load_balancer_node` | `true` | `false` |
| `database_url` | Same Firebase database URL | Same Firebase database URL |
| `max_transcription_jobs_per_user` | Same limit | Same limit |

Save a separate full configuration file on each machine. For example, the
`general` section on the coordinator and worker would contain:

```json
{
    "general": {
        "server_id": "server_a",
        "address": "server-a.example.com:3000",
        "is_load_balancer_node": true
    }
}
```

```json
{
    "general": {
        "server_id": "server_b",
        "address": "server-b.example.com:3000",
        "is_load_balancer_node": false
    }
}
```

#### Connection and TLS behavior

Clients always connect to the public Caddy address using secure WebSockets
(`wss://`). The `address` value contains only the host and port; clients should
use `wss://` when opening the connection. Caddy terminates TLS and forwards the
connection to the Python app over the local network. The app uses
`X-Forwarded-For`, which Caddy sets, to determine the client IP for rate
limiting.

| Connection | Development default | Production template |
| --- | --- | --- |
| Client to Caddy | `wss://127.0.0.1:8443` | `wss://api.example.com:3000` |
| Caddy to Python app | `ws://127.0.0.1:80` | `ws://127.0.0.1:5000` |
| TLS certificate management | Caddy internal CA | Caddy ACME issuer |

The Python app does not load or generate TLS certificates. Caddy manages the
certificates needed for its HTTPS/WSS listener. The development certificate is
issued by Caddy's local CA; the production configuration uses ACME.

### Configuration reference

#### General

**`ip_address`** sets the address where the Python server listens for
transcription requests. Keep it local when Caddy runs on the same machine.

**`port_number`** sets the backend port where the Python server listens. The
default development Caddyfile forwards to `127.0.0.1:80`.

**`address`** is the public Caddy host and port that clients use to reach the
server. Store it without a scheme, such as `127.0.0.1:8443` or
`api.example.com:3000`; clients connect using `wss://`. The `ip_address` and
`port_number` values determine where the Python app listens behind Caddy.

**`is_load_balancer_node`** determines whether this instance performs load
balancing tasks, such as removing expired server records and ordering available
servers by CPU usage. For a deployment with multiple server instances, enable
this on **only one instance**.

**`database_url`** is the Firebase Realtime Database URL used by the application.

**`server_id`** is the required identifier for this server instance.

**`max_requests_per_minute`** limits new WebSocket connections from each client
IP during a rolling 60-second window. It defaults to `100`. The app uses the
client IP forwarded by Caddy; connections over the limit are closed with WebSocket
status code `1013`. The counter is kept in memory and resets when the app restarts.

#### Caddy reverse proxy

**`caddy_reverse_proxy.is_dev`** selects which Caddyfile to use. It defaults to
`true`, which selects the development Caddyfile. Set it to `false` to use the
production Caddyfile. Caddy is always started; this setting does not enable or
disable the reverse proxy or TLS.

TLS is always used between clients and Caddy. Caddy manages the required
certificates; the Python app has no certificate or TLS configuration options.

#### Transcription

**`max_transcription_jobs_per_user`** sets the maximum number of active
transcription jobs allowed for each user.

#### Firebase

**`firebase_key_name`** is the filename of the Firebase Admin SDK service account
key in the app's `data` directory. On first use, the app stores the key in Google
Cloud Secret Manager and removes the local key file.




