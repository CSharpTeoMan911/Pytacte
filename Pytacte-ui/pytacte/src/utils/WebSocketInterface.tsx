export class WebSocketInterface {
    open_event:void | undefined = undefined
    message_event:void | undefined = undefined

    web_socket: WebSocket | undefined;
    use_encryption: boolean = false;
    connection_initiated: boolean = false;
    ssl_handshake_completed: boolean = false;

    public constructor(ip_address: string = 'localhost', port: number = 80) {
        this.web_socket = new WebSocket(`ws://${ip_address}:${port}`);

        // Connection opened
        this.open_event = this.web_socket?.addEventListener("open", (event) => {
            this.web_socket?.send("[ Client request: (use_encryption)]");
        });

        // Listen for messages
        this.web_socket.addEventListener("message", (event) => {
            if (!this.connection_initiated) {
                if (event.data === '[ Server response: (use_encryption == true)]') {
                    this.use_encryption = true;
                }
                this.connection_initiated = true;
                this.__send_data__('Mock clinet response');
            }
            else {
                this.__send_data__('Mock clinet response');
            }
            console.log("Message from server ", event.data);
        });
    }

    public __send_data__(data: Blob | string) {
        this.web_socket?.send(data);
    }
}
