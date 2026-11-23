const MAX_QUEUED_MESSAGES = 100;

let socket;
let queuedMessages = [];
let queueLimitReported = false;

function postStatus(message) {
  // Keep the existing page-side status protocol: [true, message].
  self.postMessage([true, message]);
}

function connect(address) {
  address = String(address).toLocaleLowerCase();

  try {
    if (String(address).includes('http://')) {
      postStatus("[ WebSocket error: Incorrect address ]");
      return;
    }
    else if (String(address).includes('https://')) {
      address = String(address).replace('https://', '')
    }

    const url = new URL(`wss://${String(address).trim()}`);
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
    postStatus(`[ WebSocket setup error: ${error} ]`);
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

  // Init format: address.
  // Once initialized, all later client messages are forwarded to the socket.
  if (!socket && data) {
    console.log(data)
    connect(data);
    return;
  }

  sendMessage(data);
};
