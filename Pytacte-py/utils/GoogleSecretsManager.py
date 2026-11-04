import google.auth
from google.api_core import exceptions as api_exceptions
from google.auth import exceptions as auth_exceptions
from google.cloud import secretmanager_v1
from google.cloud.secretmanager_v1.types import resources


class ReturnValue:
    def __init__(self, message: str, successful: bool, payload: object):
        self.message = message
        self.successful = successful
        self.payload = payload


class GoogleSecretsManager:
    def __init__(self):
        pass

    def __createSecretManager__(
        self,
    ) -> secretmanager_v1.SecretManagerServiceAsyncClient:
        try:
            return secretmanager_v1.SecretManagerServiceAsyncClient()

        except auth_exceptions.DefaultCredentialsError as exc:
            raise RuntimeError("ADC credentials unavailable") from exc

        except auth_exceptions.RefreshError as exc:
            raise RuntimeError("Credential refresh failed") from exc

    def __getProjectSource__(self):
        try:
            credentials, project_id = google.auth.default()
            return f"projects/{project_id}"

        except auth_exceptions.DefaultCredentialsError as exc:
            raise RuntimeError("ADC credentials unavailable") from exc

        except auth_exceptions.RefreshError as exc:
            raise RuntimeError("Credential refresh failed") from exc

    async def __getSecret__(
        self,
        secret_name: str,
        secrets_manager: secretmanager_v1.SecretManagerServiceAsyncClient,
    ) -> resources.Secret:
        try:
            resource_path = f"{self.__getProjectSource__()}/{'secrets'}/{secret_name}"
            request = secretmanager_v1.GetSecretRequest(
                name=resource_path,
            )
            response = await secrets_manager.get_secret(request=request)
            return response

        except auth_exceptions.DefaultCredentialsError as exc:
            raise RuntimeError("ADC credentials unavailable") from exc

        except auth_exceptions.RefreshError as exc:
            raise RuntimeError("Credential refresh failed") from exc

        except api_exceptions.Unauthorized as exc:
            raise RuntimeError("Authentication failed") from exc

        except api_exceptions.PermissionDenied as exc:
            raise PermissionError("Insufficient IAM permissions") from exc

        except api_exceptions.NotFound as exc:
            raise LookupError("Secret not found") from exc

    async def __setSecret__(
        self,
        secret_name: str,
        secrets_manager: secretmanager_v1.SecretManagerServiceAsyncClient,
    ) -> resources.Secret:
        try:
            request = secretmanager_v1.CreateSecretRequest(
                parent=self.__getProjectSource__(),
                secret_id=secret_name,
            )

            response = await secrets_manager.create_secret(request=request)
            return response

        except auth_exceptions.DefaultCredentialsError as exc:
            raise RuntimeError("ADC credentials unavailable") from exc

        except auth_exceptions.RefreshError as exc:
            raise RuntimeError("Credential refresh failed") from exc

        except api_exceptions.Unauthorized as exc:
            raise RuntimeError("Authentication failed") from exc

        except api_exceptions.PermissionDenied as exc:
            raise PermissionError("Insufficient IAM permissions") from exc

        except api_exceptions.NotFound as exc:
            raise LookupError("Project not found") from exc

        except api_exceptions.AlreadyExists as exc:
            raise RuntimeError("Secret already exists") from exc

    async def __setSecretVersion__(
        self,
        secret_name: str,
        secret:str,
        secrets_manager: secretmanager_v1.SecretManagerServiceAsyncClient,
    ):
        try:
            resource_path = f"{self.__getProjectSource__()}/{'secrets'}/{secret_name}"

            # Initialize request argument(s)
            request = secretmanager_v1.AddSecretVersionRequest(
                parent=resource_path,
                payload=secretmanager_v1.SecretPayload(
                    data=secret.encode('utf-8')
                )
            )

            # Make the request
            response = await secrets_manager.add_secret_version(request=request)
            return response

        except auth_exceptions.DefaultCredentialsError as exc:
            raise RuntimeError("ADC credentials unavailable") from exc

        except auth_exceptions.RefreshError as exc:
            raise RuntimeError("Credential refresh failed") from exc

    async def getSecret(self, name:str) -> ReturnValue:
        try:
            manager = self.__createSecretManager__()
            version = await self.__getSecret__(name, manager)
            return ReturnValue("Secret retrieval successful", True, version)
        except RuntimeError as e:
            return ReturnValue(str(e), False, None)

    async def setSecret(self, name:str, secret:str) -> ReturnValue:
        try:
            manager = self.__createSecretManager__()
            await self.__setSecret__(name, secret, manager)
            _secret = await self.__setSecretVersion__(name, secret, manager)
            return ReturnValue("Secret addition successful", True, _secret)
        except RuntimeError as e:
            if str(e) == "Secret already exists":
                try:     
                    manager = self.__createSecretManager__()
                    _secret = await self.__setSecretVersion__(name, secret, manager)
                    return ReturnValue("Secret addition successful", True, _secret)
                except RuntimeError as _e:
                    return ReturnValue(str(_e), False, None)
            else:
                return ReturnValue(str(e), False, None)
            
    def verifyGoogleCloudAuthentication(self) -> ReturnValue:
        try:
            self.__getProjectSource__()
            return ReturnValue('Google cloud authentication successful', True, None)
        except RuntimeError as e:
            return ReturnValue(str(e), False, None)
