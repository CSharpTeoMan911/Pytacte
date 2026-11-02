function getMessageEncoding(message:string) {
  let enc = new TextEncoder();
  return enc.encode(message);
}

async function encryptMessage(key:CryptoKey, message:string):Promise<ArrayBuffer> {
  let encoded = getMessageEncoding(message);
  // counter will be needed for decryption
  const counter = window.crypto.getRandomValues(new Uint8Array(16));
  return await window.crypto.subtle.encrypt(
    {
      name: "AES-CTR",
      counter,
      length: 64,
    },
    key,
    encoded,
  );
}

async function generateKey():Promise<CryptoKey> {
  return await window.crypto.subtle.generateKey(
    {
      name: "AES-CTR",
      length: 256,
    },
    true,
    ["encrypt", "decrypt"]
  );
}