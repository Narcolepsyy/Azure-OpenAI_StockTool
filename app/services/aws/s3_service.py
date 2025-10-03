"""AWS S3 service for knowledge base document storage."""
import os
import io
import logging
from typing import Optional, List, Dict, BinaryIO
from datetime import datetime
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from botocore.config import Config

logger = logging.getLogger(__name__)


class S3Service:
    """Service for managing documents in S3."""
    
    def __init__(self, bucket_name: str, endpoint_url: Optional[str] = None):
        """
        Initialize S3 service.
        
        Args:
            bucket_name: Name of the S3 bucket
            endpoint_url: Optional endpoint URL (for LocalStack)
        """
        self.bucket_name = bucket_name
        
        # Configure with timeouts and retries
        config = Config(
            retries={'max_attempts': 3, 'mode': 'adaptive'},
            connect_timeout=5,
            read_timeout=10
        )
        
        # Use endpoint_url if provided (LocalStack)
        client_kwargs = {
            'config': config,
            'region_name': os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        }
        
        if endpoint_url:
            client_kwargs['endpoint_url'] = endpoint_url
            # For LocalStack, use dummy credentials
            client_kwargs['aws_access_key_id'] = os.getenv('AWS_ACCESS_KEY_ID', 'test')
            client_kwargs['aws_secret_access_key'] = os.getenv('AWS_SECRET_ACCESS_KEY', 'test')
        
        self.s3_client = boto3.client('s3', **client_kwargs)
        self.s3_resource = boto3.resource('s3', **client_kwargs)
        
        # Ensure bucket exists
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Ensure the S3 bucket exists, create if it doesn't."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"S3 bucket '{self.bucket_name}' exists")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.info(f"Creating S3 bucket: {self.bucket_name}")
                try:
                    self.s3_client.create_bucket(Bucket=self.bucket_name)
                    # Enable versioning
                    self.s3_client.put_bucket_versioning(
                        Bucket=self.bucket_name,
                        VersioningConfiguration={'Status': 'Enabled'}
                    )
                    logger.info(f"Created bucket with versioning enabled")
                except ClientError as create_error:
                    logger.error(f"Failed to create bucket: {create_error}")
                    raise
            else:
                logger.error(f"Error checking bucket: {e}")
                raise
    
    def upload_file(
        self,
        file_path: str,
        s3_key: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None
    ) -> str:
        """
        Upload a file to S3.
        
        Args:
            file_path: Local file path to upload
            s3_key: Optional S3 key (defaults to filename)
            metadata: Optional metadata dict
            content_type: Optional content type
            
        Returns:
            S3 key of uploaded file
        """
        if s3_key is None:
            s3_key = os.path.basename(file_path)
        
        extra_args = {}
        if metadata:
            extra_args['Metadata'] = metadata
        if content_type:
            extra_args['ContentType'] = content_type
        else:
            # Auto-detect content type
            if file_path.endswith('.pdf'):
                extra_args['ContentType'] = 'application/pdf'
            elif file_path.endswith('.txt'):
                extra_args['ContentType'] = 'text/plain'
            elif file_path.endswith('.md'):
                extra_args['ContentType'] = 'text/markdown'
            elif file_path.endswith('.json'):
                extra_args['ContentType'] = 'application/json'
        
        try:
            self.s3_client.upload_file(
                file_path,
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args if extra_args else None
            )
            logger.info(f"Uploaded {file_path} to s3://{self.bucket_name}/{s3_key}")
            return s3_key
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to upload {file_path}: {e}")
            raise
    
    def upload_fileobj(
        self,
        file_obj: BinaryIO,
        s3_key: str,
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None
    ) -> str:
        """
        Upload a file object to S3.
        
        Args:
            file_obj: File-like object to upload
            s3_key: S3 key
            metadata: Optional metadata dict
            content_type: Optional content type
            
        Returns:
            S3 key of uploaded file
        """
        extra_args = {}
        if metadata:
            extra_args['Metadata'] = metadata
        if content_type:
            extra_args['ContentType'] = content_type
        
        try:
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args if extra_args else None
            )
            logger.info(f"Uploaded file object to s3://{self.bucket_name}/{s3_key}")
            return s3_key
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to upload file object: {e}")
            raise
    
    def download_file(self, s3_key: str, local_path: str) -> str:
        """
        Download a file from S3.
        
        Args:
            s3_key: S3 key to download
            local_path: Local path to save file
            
        Returns:
            Local file path
        """
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            self.s3_client.download_file(self.bucket_name, s3_key, local_path)
            logger.info(f"Downloaded s3://{self.bucket_name}/{s3_key} to {local_path}")
            return local_path
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to download {s3_key}: {e}")
            raise
    
    def download_fileobj(self, s3_key: str) -> bytes:
        """
        Download a file from S3 as bytes.
        
        Args:
            s3_key: S3 key to download
            
        Returns:
            File contents as bytes
        """
        try:
            buffer = io.BytesIO()
            self.s3_client.download_fileobj(self.bucket_name, s3_key, buffer)
            buffer.seek(0)
            logger.info(f"Downloaded s3://{self.bucket_name}/{s3_key} to memory")
            return buffer.read()
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to download {s3_key}: {e}")
            raise
    
    def list_files(self, prefix: str = "", max_keys: int = 1000) -> List[Dict]:
        """
        List files in S3 bucket.
        
        Args:
            prefix: Optional prefix filter
            max_keys: Maximum number of keys to return
            
        Returns:
            List of file metadata dicts
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    files.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'],
                        'etag': obj['ETag'].strip('"')
                    })
            
            logger.info(f"Listed {len(files)} files with prefix '{prefix}'")
            return files
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to list files: {e}")
            raise
    
    def file_exists(self, s3_key: str) -> bool:
        """
        Check if a file exists in S3.
        
        Args:
            s3_key: S3 key to check
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            logger.error(f"Error checking file existence: {e}")
            raise
    
    def delete_file(self, s3_key: str) -> bool:
        """
        Delete a file from S3.
        
        Args:
            s3_key: S3 key to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"Deleted s3://{self.bucket_name}/{s3_key}")
            return True
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to delete {s3_key}: {e}")
            raise
    
    def get_metadata(self, s3_key: str) -> Dict:
        """
        Get file metadata from S3.
        
        Args:
            s3_key: S3 key
            
        Returns:
            Metadata dict
        """
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return {
                'content_type': response.get('ContentType'),
                'content_length': response.get('ContentLength'),
                'last_modified': response.get('LastModified'),
                'etag': response.get('ETag', '').strip('"'),
                'metadata': response.get('Metadata', {}),
                'version_id': response.get('VersionId')
            }
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to get metadata for {s3_key}: {e}")
            raise
    
    def get_presigned_url(
        self,
        s3_key: str,
        expiration: int = 3600,
        http_method: str = 'get_object'
    ) -> str:
        """
        Generate a presigned URL for temporary access.
        
        Args:
            s3_key: S3 key
            expiration: URL expiration time in seconds (default 1 hour)
            http_method: HTTP method (get_object, put_object, etc.)
            
        Returns:
            Presigned URL string
        """
        try:
            url = self.s3_client.generate_presigned_url(
                http_method,
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            logger.info(f"Generated presigned URL for {s3_key} (expires in {expiration}s)")
            return url
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise
    
    def sync_directory(self, local_dir: str, s3_prefix: str = "") -> Dict[str, int]:
        """
        Sync a local directory to S3.
        
        Args:
            local_dir: Local directory to sync
            s3_prefix: Optional S3 prefix
            
        Returns:
            Dict with upload statistics
        """
        stats = {'uploaded': 0, 'skipped': 0, 'errors': 0}
        
        for root, dirs, files in os.walk(local_dir):
            for filename in files:
                local_path = os.path.join(root, filename)
                relative_path = os.path.relpath(local_path, local_dir)
                s3_key = os.path.join(s3_prefix, relative_path).replace('\\', '/')
                
                try:
                    # Check if file exists and has same size (basic deduplication)
                    if self.file_exists(s3_key):
                        metadata = self.get_metadata(s3_key)
                        local_size = os.path.getsize(local_path)
                        if metadata['content_length'] == local_size:
                            logger.debug(f"Skipping {s3_key} (already synced)")
                            stats['skipped'] += 1
                            continue
                    
                    self.upload_file(local_path, s3_key)
                    stats['uploaded'] += 1
                except Exception as e:
                    logger.error(f"Failed to sync {local_path}: {e}")
                    stats['errors'] += 1
        
        logger.info(f"Sync complete: {stats}")
        return stats


# Singleton instance
_s3_service: Optional[S3Service] = None


def get_s3_service() -> S3Service:
    """Get or create S3 service singleton."""
    global _s3_service
    
    if _s3_service is None:
        bucket_name = os.getenv('S3_BUCKET_NAME', 'stocktool-knowledge')
        endpoint_url = os.getenv('AWS_ENDPOINT_URL') if os.getenv('USE_LOCALSTACK', 'false').lower() == 'true' else None
        _s3_service = S3Service(bucket_name, endpoint_url)
    
    return _s3_service
