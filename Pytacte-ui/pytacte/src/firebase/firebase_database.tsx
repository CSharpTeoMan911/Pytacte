import { app } from "./firebase_app";
import { getDatabase, ref, get, query, orderByChild, limitToFirst } from "firebase/database";
import type { DatabaseReference, Query, DataSnapshot } from "firebase/database";

const database = getDatabase(app);

type ReturnValue = {
    isSucessful: boolean,
    payload: [string, string] | string
}

export async function getAvailableServer(): Promise<ReturnValue> {
    const availableServersReference: DatabaseReference = ref(database, 'Client_Available_Pytacte_Servers/');
    const availableServersQuery: Query = query(availableServersReference, orderByChild('cpu_usage'), limitToFirst(1))
    
    console.log(availableServersQuery)
    const availableServerSnapshot: DataSnapshot = await get(availableServersQuery);

    const availableServer: Record<string, unknown> | unknown[] | string | number | boolean | null = availableServerSnapshot.val() as Record<string, unknown> | unknown[] | string | number | boolean | null;

    console.log(availableServer)

    if (availableServer !== null) {
        if (typeof availableServer === "object" && !Array.isArray(availableServer)) {
            const availableServerRecord = availableServer as Record<string, unknown>;
            const serverKey = Object.keys(availableServerRecord)[0];
            const serverData = serverKey ? availableServerRecord[serverKey] : null;

            console.log(serverData)

            if (serverData && typeof serverData === "object") {
                const serverRecord = serverData as Record<string, unknown>;
                const address: string | null = serverRecord["server_address"] as string;
                const protocol: string | null = serverRecord["tls"] ? 'wss' : 'ws';

                return address && protocol ? { isSucessful: true, payload: [address, protocol] } : { isSucessful: false, payload: 'No server is available' } as ReturnValue;
            }

            return { isSucessful: false, payload: 'No server is available' } as ReturnValue;
        }

        return { isSucessful: false, payload: 'No server is available' } as ReturnValue;
    }

    return { isSucessful: false, payload: 'No server is available' } as ReturnValue;
}