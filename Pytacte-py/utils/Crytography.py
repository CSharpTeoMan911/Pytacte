import secrets
import string
from datetime import UTC, datetime, timedelta, timezone
from ipaddress import IPv4Address
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from utils.GoogleSecretsManager import GoogleSecretsManager, ReturnValue


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



    async def serialise_rsa_key_pair(self, password_length:int = 10, passwordless:bool = True, key: rsa.RSAPrivateKey = None) -> tuple[bytes, bytes]:
        secretsManager = GoogleSecretsManager()
        auth_result = secretsManager.verifyGoogleCloudAuthentication() if not passwordless else ReturnValue('No auth needed', True, None)
        
        if auth_result.successful:
            password = self.__cryptographycally_secure_random_password_generator__(password_length)
                        
            secret_insertion_result:ReturnValue = await secretsManager.setSecret(name='private_key_password', secret=password) if not passwordless else ReturnValue('No secret gen needed', True, None)
            
            if secret_insertion_result.successful:
                password_bytes = str.encode(password, encoding='utf-8')
                public_pem = key.public_key().public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo,
                )
                private_pem = key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm= serialization.NoEncryption() if passwordless else serialization.BestAvailableEncryption(password_bytes),
                )
            else:
                raise RuntimeError(secret_insertion_result.message)
            
            print(secret_insertion_result.message)
            return public_pem, private_pem
        else:
            raise RuntimeError(f'Internal Error: {auth_result.message}\nError: Password encryption not valid if Google Cloud Secrets are not configured')
        
        
    def write_rsa_key_to_file(self, file_name:str, cert:bytes) -> str:
        path = Path(Path.cwd(), 'data', file_name)
        with open(path, 'wb') as fw:
            fw.write(cert)
            fw.flush()
        return path


    async def write_keys_to_cert(
        self,
        file_name: str,
        p_key: bytes,
        pr_key: bytes,
        passwrodless:bool = True
    ) -> str:
        public_key = serialization.load_pem_public_key(p_key)
        
        if not passwrodless:
            secretsManager = GoogleSecretsManager()
            result = await secretsManager.getSecret('private_key_password')
        
            if result.successful:
                password_bytes = str.encode(result.payload, 'utf-8')
                private_key = serialization.load_pem_private_key(pr_key, password= password_bytes if not passwrodless else None)
            else:
                raise RuntimeError(result.message)
        else:
            private_key = serialization.load_pem_private_key(pr_key, password=None)

        if not isinstance(public_key, rsa.RSAPublicKey):
            raise TypeError('The public key is not an RSA public key')
        if not isinstance(private_key, rsa.RSAPrivateKey):
            raise TypeError('The private key is not an RSA private key')
        if public_key.public_numbers() != private_key.public_key().public_numbers():
            raise ValueError('The public and private keys do not match')

        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, 'pytacte'),
        ])
        now = datetime.now(UTC)
        certificate = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(public_key)
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + timedelta(days=365))
            .add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName('localhost'),
                    x509.IPAddress(IPv4Address('127.0.0.1')),
                ]),
                critical=False,
            )
            .sign(private_key, hashes.SHA256())
        )

        path = Path(Path.cwd(), 'data', file_name)
        path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
        return str(path)
    
    
    async def get_private_key_password(self) -> str:
        secretsManager = GoogleSecretsManager()
        result = await secretsManager.getSecret('private_key_password')
        
        if result.successful:
            return result.payload
        else:
            raise RuntimeError(result.message)

