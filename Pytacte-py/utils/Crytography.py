import secrets
import string
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from GoogleSecretsManager import GoogleSecretsManager, ReturnValue


class RSA_Crypto:
    def __init__(self):
        self.LOWERCASE_LETTERS = string.ascii_lowercase
        self.UPPERCASE_LETTERS = string.ascii_uppercase
        self.SYMBOLS = string.punctuation
        self.NUMBERS = string.digits
    
    def __cryptographycally_secure_random_password_generator__(self, length:int = 10) -> string:
        password = ''
        while(length > 0):
            char_type = secrets.randbelow(4)
            char = ''
            match char_type:
                case 0:
                    char = secrets.choice(self.LOWERCASE_LETTERS)
                case 1: 
                    char = secrets.choice(self.UPPERCASE_LETTERS)
                case 2:
                    char = secrets.choice(self.SYMBOLS)
                case 3:
                    char = secrets.choice(self.NUMBERS)
                    
            password += char
            length -= 1
            
        return password

    def generate_rsa_key(self) -> rsa.RSAPrivateKey:
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048 * 2,
        )
        return private_key

    def serialise_rsa_key(self, password_length:int = 10, passwordless:bool = True, key: rsa.RSAPrivateKey = None) -> bytes:
        auth_result = GoogleSecretsManager().verifyGoogleCloudAuthentication()
        
        if auth_result.successful:
            password_bytes = str.encode(self.__cryptographycally_secure_random_password_generator__(password_length), encoding='utf-8')
            pem = key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm= serialization.NoEncryption() if passwordless else serialization.BestAvailableEncryption(password_bytes),
            )
            return pem
        else:
            raise RuntimeError(f'Internal Error: {auth_result.message}\nError: Password encryption not valid if Google Cloud Secrets are not configured')
        
        
        
    def write_rsa_key_to_file(self, file_name:str, cert:bytes) -> str:
        _file_name = file_name + '.pem'
        path = Path(Path.cwd(), 'data', _file_name)
        with open(path, 'wb') as fw:
            fw.write(cert)
        return path
            
    def read_rsa_key_from_file(
        self,
        path: str | Path,
        password: str | bytes | None = None,
    ) -> rsa.RSAPrivateKey:
        password_bytes = password.encode('utf-8') if isinstance(password, str) else password

        with Path(path).open('rb') as fr:
            private_key = serialization.load_pem_private_key(
                fr.read(),
                password=password_bytes,
            )

        if not isinstance(private_key, rsa.RSAPrivateKey):
            raise TypeError('The file does not contain an RSA private key')

        return private_key
            
        
