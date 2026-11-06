const MAX_QUEUED_MESSAGES = 100;

let socket;
let queuedMessages = [];
let queueLimitReported = false;

function postStatus(message) {
  // Keep the existing page-side status protocol: [true, message].
  self.postMessage([true, message]);
}

function connect(hostValue, portValue) {
  const host = String(hostValue).trim();
  const port = Number(portValue);

  if (!host) {
    postStatus('[ WebSocket error: host is empty ]');
    return;
  }

  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    postStatus(`[ WebSocket error: invalid port "${portValue}" ]`);
    return;
  }

  const protocol = self.location.protocol === 'https:' ? 'wss:' : 'ws:';

  try {
    const url = new URL(`${protocol}//${host}`);
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

  // The page initializes the worker with [host, port], then sends audio Blobs.
  if (Array.isArray(data) && data.length >= 2) {
    if (socket) {
      postStatus('[ WebSocket is already initialized ]');
      return;
    }

    connect(data[0], data[1]);
    return;
  }

  sendMessage(data);
};
