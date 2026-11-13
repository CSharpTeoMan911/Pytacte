import json
from pathlib import Path

import firebase_admin
from aiofile import async_open
from firebase_admin import App, auth, credentials

from utils.GoogleSecretsManager import GoogleSecretsManager, ReturnValue


class FirebaseAuth:
    def __init__(self):
        self.secrets_manager:GoogleSecretsManager = GoogleSecretsManager()
        self.firebase_app:App | None = None
        
    async def initiate_app(self, key_name:str | None):
        result:ReturnValue = await self.secrets_manager.getSecret('admin_sdk_key')
        if result.successful:
            self.__initialise_app__(json.loads(result.payload))
        else:
            key_path = Path(Path.cwd(), 'data', key_name)

            if key_path.exists():
                async with async_open(key_path, 'r') as fr:
                    key = await fr.read()
                await self.secrets_manager.setSecret('admin_sdk_key', key)
                await self.__initialise_app__(json.loads(key))
            else:
                raise RuntimeError(
                    "--> [ Error: Generate a Firebase private key, save it in 'data', "
                    "and set its name under the value 'firebase_key_name' "
                    "in the config. ]"
                )
        
    async def __initialise_app__(self, key:dict):
        try:
            cred = credentials.Certificate(key)
            self.firebase_app = firebase_admin.initialize_app(cred)
        except ValueError as e:
            raise RuntimeError(f'--> [ Error: {e} ]')
        
    def validate_id_token(self, token:str) -> tuple[bool, str]:
        '''
        ValueError: If ``id_token`` is a not a string or is empty.
        InvalidIdTokenError: If ``id_token`` is not a valid Firebase ID token.
        ExpiredIdTokenError: If the specified ID token has expired.
        RevokedIdTokenError: If ``check_revoked`` is ``True`` and the ID token has been revoked.
        CertificateFetchError: If an error occurs while fetching the public key certificates
            required to verify the ID token.
        UserDisabledError: If ``check_revoked`` is ``True`` and the corresponding user
            record is disabled.
        '''
        try:
            result = auth.verify_id_token(token)
            
            if result['email_verified'] is False:
                self.__remove_id_token__(result['user_id'])
                return [False, 'Email not verified']

            return [True, result]
        except auth.InvalidIdTokenError:
            return [False, 'Invalid token.']
        except auth.ExpiredIdTokenError:
            return [False, 'Expired token']
        except auth.RevokedIdTokenError:
            return [False, 'Token revoked']
        except auth.UserDisabledError:
            return [False, 'Internal server error']
        except auth.CertificateFetchError:
            return [False, 'Internal server error']


    def __remove_id_token__(self, uid:str) -> bool:
        try:
            auth.revoke_refresh_tokens(uid=uid)
        except ValueError, auth.FirebaseError:
            pass
