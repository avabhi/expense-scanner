import boto3
from botocore.exceptions import ClientError
from botocore.client import Config
from app.core.config import settings

def get_s3_client():
    client_kwargs = {
        'aws_access_key_id': settings.AWS_ACCESS_KEY_ID or 'mock_key',
        'aws_secret_access_key': settings.AWS_SECRET_ACCESS_KEY or 'mock_secret',
        'region_name': settings.AWS_REGION,
        'config': Config(signature_version='s3v4')
    }
    
    if settings.AWS_ENDPOINT_URL:
        client_kwargs['endpoint_url'] = settings.AWS_ENDPOINT_URL
        
    return boto3.client('s3', **client_kwargs)

def create_presigned_post(object_name: str, expiration: int = 3600):
    """
    Generate a presigned URL POST to upload a file to S3 (used for local MinIO multipart upload).
    """
    s3_client = get_s3_client()
    try:
        response = s3_client.generate_presigned_post(
            Bucket=settings.AWS_BUCKET_NAME,
            Key=object_name,
            Fields={"acl": "private"},
            Conditions=[{"acl": "private"}],
            ExpiresIn=expiration
        )
        if response and "url" in response and settings.ENVIRONMENT == "development" and "http://minio:9000" in response["url"]:
            response["url"] = response["url"].replace("http://minio:9000", "http://localhost:9000")
    except ClientError as e:
        print(e)
        return None
    return response

def create_presigned_put(object_name: str, expiration: int = 3600) -> str | None:
    """
    Generate a presigned URL PUT to upload a file to S3/R2 directly.
    """
    s3_client = get_s3_client()
    try:
        url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': settings.AWS_BUCKET_NAME,
                'Key': object_name
            },
            ExpiresIn=expiration
        )
        if url and settings.ENVIRONMENT == "development" and "http://minio:9000" in url:
            url = url.replace("http://minio:9000", "http://localhost:9000")
    except ClientError as e:
        print(e)
        return None
    return url

def get_presigned_download_url(object_name: str, expiration: int = 3600) -> str | None:
    """
    Generate a presigned URL to retrieve (GET) a file from S3.
    """
    s3_client = get_s3_client()
    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': settings.AWS_BUCKET_NAME,
                'Key': object_name
            },
            ExpiresIn=expiration
        )
        if url and settings.ENVIRONMENT == "development" and "http://minio:9000" in url:
            url = url.replace("http://minio:9000", "http://localhost:9000")
    except ClientError as e:
        print(e)
        return None
    return url
