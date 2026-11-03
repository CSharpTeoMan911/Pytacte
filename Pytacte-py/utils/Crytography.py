from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import secrets
import string


class Crypto:
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

    def serialise_rsa_key(self, password_length, key: rsa.RSAPrivateKey):
        password_bytes = str.encode(self.__cryptographycally_secure_random_password_generator__(password_length), encoding='utf-8')
        public_key = key.public_key()
        pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(password_bytes),
        )
        
