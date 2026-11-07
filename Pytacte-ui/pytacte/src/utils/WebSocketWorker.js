const MAX_QUEUED_MESSAGES = 100;

let socket;
let queuedMessages = [];
let queueLimitReported = false;

function postStatus(message) {
  // Keep the existing page-side status protocol: [true, message].
  self.postMessage([true, message]);
}

function connect(protocolValue, hostValue, portValue) {
  let protocol;
  const host = String(hostValue).trim();
  const port = Number(portValue);

  if (protocolValue == null || protocolValue === '') {
    // Keep the current two-item init message working as a fallback.
    protocol = 'ws';
  } else {
    const requestedProtocol = String(protocolValue).trim().toLowerCase();
    if (requestedProtocol === 'ws') {
      protocol = 'ws';
    } else if (requestedProtocol === 'wss') {
      protocol = 'wss';
    } else {
      postStatus(`[ WebSocket error: unsupported protocol "${protocolValue}"; expected "ws" or "wss" ]`);
      return;
    }
  }

  if (!host) {
    postStatus('[ WebSocket error: host is empty ]');
    return;
  }

  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    postStatus(`[ WebSocket error: invalid port "${portValue}" ]`);
    return;
  }

  try {
    const url = new URL(`${protocol}://${host}`);
    url.port = String(port);

    const connection = new WebSocket(url);
    socket = connection;

    connection.onopen = () => {
      if (socket !== connection) return;

      postStatus(`[ Socket connected to: ${connection.url} ]`);
      queueLimitReported = false;

      while (queuedMessages.length > 0 && connection.readyState === WebSocket.OPEN) {
        const message = queuedMessages.shift();

        try {
          connection.send(message);
        } catch (error) {
          queuedMessages.unshift(message);
          const detail = error instanceof Error ? error.message : String(error);
          postStatus(`[ WebSocket send error: ${detail} ]`);
          break;
        }
      }
    };

    connection.onerror = () => {
      postStatus(`[ WebSocket error: unable to connect to ${connection.url} ]`);
    };

    connection.onclose = (event) => {
      queuedMessages = [];
      postStatus(`[ Socket closed: code ${event.code}${event.reason ? `, ${event.reason}` : ''} ]`);
    };

    connection.onmessage = (event) => {
      // Keep server data distinct from status messages for the existing page handler.
      self.postMessage([false, event.data]);
    };
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    postStatus(`[ WebSocket setup error: ${detail} ]`);
  }
}

function sendMessage(message) {
  if (!socket) {
    postStatus('[ WebSocket not initialized; message dropped ]');
    return;
  }

  if (socket.readyState === WebSocket.CONNECTING) {
    if (queuedMessages.length < MAX_QUEUED_MESSAGES) {
      queuedMessages.push(message);
    } else if (!queueLimitReported) {
      queueLimitReported = true;
      postStatus('[ WebSocket is still connecting; audio queue is full, dropping frames ]');
    }
    return;
  }

  if (socket.readyState !== WebSocket.OPEN) {
    return;
  }

  try {
    socket.send(message);
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    postStatus(`[ WebSocket send error: ${detail} ]`);
  }
}

self.onmessage = (event) => {
  const { data } = event;

  if (data === '<Shutdown/>') {
    queuedMessages = [];
    if (socket && (socket.readyState === WebSocket.CONNECTING || socket.readyState === WebSocket.OPEN)) {
      socket.close(1000, 'Client stopped');
    } else {
      postStatus('[ Socket closed: client stopped ]');
    }
    return;
  }

  // Init format: [host, port, protocol]. The protocol accepts "ws"/"ws:" or "wss"/"wss:".
  // Once initialized, all later client messages are forwarded to the socket.
  if (!socket && Array.isArray(data) && data.length === 3) {
    connect(data[2], data[0], data[1]);
    return;
  }

  sendMessage(data);
};
