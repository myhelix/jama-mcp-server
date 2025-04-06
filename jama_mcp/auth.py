import os
import json
import logging
from typing import Tuple

# Define custom exceptions for clearer error handling
class CredentialsError(Exception):
    """Base class for credential-related errors."""
    pass

class MissingCredentialsError(CredentialsError):
    """Raised when required credentials are not found."""
    pass

class AWSParameterStoreError(CredentialsError):
    """Raised when there's an error interacting with AWS Parameter Store."""
    pass

class InvalidSecretFormatError(CredentialsError):
    """Raised when the secret fetched from Parameter Store has an invalid format."""
    pass

logger = logging.getLogger(__name__)

def get_jama_credentials() -> Tuple[str, str]:
    """
    Retrieves Jama OAuth credentials (client_id, client_secret).

    Resolution order:
    1. AWS Parameter Store (if JAMA_AWS_SECRET_PATH is set)
    2. Environment variables (JAMA_CLIENT_ID, JAMA_CLIENT_SECRET)

    Environment Variables:
        JAMA_AWS_SECRET_PATH (str, optional): The name/path of the secret in AWS Parameter Store.
        JAMA_AWS_PROFILE (str, optional): The AWS profile name to use with boto3.
        JAMA_CLIENT_ID (str, optional): Jama OAuth Client ID (used if AWS path not set).
        JAMA_CLIENT_SECRET (str, optional): Jama OAuth Client Secret (used if AWS path not set).

    Returns:
        Tuple[str, str]: A tuple containing (client_id, client_secret).

    Raises:
        MissingCredentialsError: If neither AWS path nor direct env vars provide credentials.
        AWSParameterStoreError: If fetching from AWS fails (requires boto3).
        InvalidSecretFormatError: If the AWS secret format is incorrect.
        ImportError: If boto3 is required but not installed.
    """
    aws_secret_path = os.environ.get("JAMA_AWS_SECRET_PATH")

    if aws_secret_path:
        logger.info(f"Attempting to fetch Jama credentials from AWS Parameter Store path: {aws_secret_path}")
        try:
            import boto3
        except ImportError:
            raise ImportError("boto3 is required for AWS Parameter Store integration. Please install it.")

        aws_profile = os.environ.get("JAMA_AWS_PROFILE")
        try:
            logger.info(f"Using AWS profile: {aws_profile if aws_profile else 'default'}")
            session = boto3.Session(profile_name=aws_profile)
            ssm_client = session.client('ssm')

            parameter = ssm_client.get_parameter(Name=aws_secret_path, WithDecryption=True)
            secret_string = parameter['Parameter']['Value']
            logger.info("Successfully retrieved secret from AWS Parameter Store.")

        except Exception as e:
            raise AWSParameterStoreError(f"Failed to retrieve secret from AWS Parameter Store path '{aws_secret_path}': {e}") from e

        try:
            secret_data = json.loads(secret_string)
            client_id = secret_data.get("client_id")
            client_secret = secret_data.get("client_secret")

            if not client_id or not client_secret:
                raise InvalidSecretFormatError("AWS Parameter Store secret JSON must contain 'client_id' and 'client_secret' keys.")

            logger.info("Successfully parsed client_id and client_secret from AWS secret.")
            return client_id, client_secret

        except json.JSONDecodeError as e:
            raise InvalidSecretFormatError(f"Failed to parse JSON secret from AWS Parameter Store path '{aws_secret_path}': {e}") from e
        except InvalidSecretFormatError: # Re-raise specific error
             raise
        except Exception as e: # Catch any other parsing/access errors
            raise InvalidSecretFormatError(f"Error processing secret data from AWS Parameter Store path '{aws_secret_path}': {e}") from e

    else:
        logger.info("JAMA_AWS_SECRET_PATH not set. Checking for direct environment variables.")
        client_id = os.environ.get("JAMA_CLIENT_ID")
        client_secret = os.environ.get("JAMA_CLIENT_SECRET")

        if client_id and client_secret:
            logger.info("Using JAMA_CLIENT_ID and JAMA_CLIENT_SECRET from environment variables.")
            return client_id, client_secret
        else:
            raise MissingCredentialsError("Missing Jama OAuth credentials. Configure AWS Parameter Store (JAMA_AWS_SECRET_PATH) or set environment variables (JAMA_CLIENT_ID, JAMA_CLIENT_SECRET).")