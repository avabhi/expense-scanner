import boto3
from botocore.exceptions import ClientError
from app.core.config import settings

def get_s3_client():
    return boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION
    )

def create_presigned_post(object_name: str, expiration: int = 3600):
    """
    Generate a presigned URL POST to upload a file to S3.
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
    except ClientError as e:
        print(e)
        return None
    return response
