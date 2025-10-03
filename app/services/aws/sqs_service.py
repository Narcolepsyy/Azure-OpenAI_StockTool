"""AWS SQS service for async task processing."""
import os
import json
import logging
from typing import Optional, List, Dict, Any, Callable
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from botocore.config import Config

logger = logging.getLogger(__name__)


class SQSService:
    """Service for managing SQS queues and messages."""
    
    def __init__(self, queue_name: str, endpoint_url: Optional[str] = None):
        """
        Initialize SQS service.
        
        Args:
            queue_name: Name of the SQS queue
            endpoint_url: Optional endpoint URL (for LocalStack)
        """
        self.queue_name = queue_name
        
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
            client_kwargs['aws_access_key_id'] = os.getenv('AWS_ACCESS_KEY_ID', 'test')
            client_kwargs['aws_secret_access_key'] = os.getenv('AWS_SECRET_ACCESS_KEY', 'test')
        
        self.sqs_client = boto3.client('sqs', **client_kwargs)
        self.queue_url = self._get_queue_url()
    
    def _get_queue_url(self) -> str:
        """Get or create queue URL."""
        try:
            response = self.sqs_client.get_queue_url(QueueName=self.queue_name)
            queue_url = response['QueueUrl']
            logger.info(f"Using SQS queue: {queue_url}")
            return queue_url
        except ClientError as e:
            if e.response['Error']['Code'] == 'AWS.SimpleQueueService.NonExistentQueue':
                logger.warning(f"Queue {self.queue_name} not found, creating...")
                response = self.sqs_client.create_queue(
                    QueueName=self.queue_name,
                    Attributes={
                        'VisibilityTimeout': '300',  # 5 minutes
                        'MessageRetentionPeriod': '86400'  # 24 hours
                    }
                )
                queue_url = response['QueueUrl']
                logger.info(f"Created SQS queue: {queue_url}")
                return queue_url
            else:
                logger.error(f"Error getting queue URL: {e}")
                raise
    
    def send_message(
        self,
        message_body: Dict[str, Any],
        message_attributes: Optional[Dict[str, Any]] = None,
        delay_seconds: int = 0
    ) -> Optional[str]:
        """
        Send a message to the queue.
        
        Args:
            message_body: Message body as dict (will be JSON serialized)
            message_attributes: Optional message attributes
            delay_seconds: Optional message delay (0-900 seconds)
            
        Returns:
            Message ID if sent successfully, None otherwise
        """
        try:
            params = {
                'QueueUrl': self.queue_url,
                'MessageBody': json.dumps(message_body),
                'DelaySeconds': delay_seconds
            }
            
            if message_attributes:
                # Convert to SQS format
                formatted_attrs = {}
                for key, value in message_attributes.items():
                    if isinstance(value, str):
                        formatted_attrs[key] = {'StringValue': value, 'DataType': 'String'}
                    elif isinstance(value, (int, float)):
                        formatted_attrs[key] = {'StringValue': str(value), 'DataType': 'Number'}
                params['MessageAttributes'] = formatted_attrs
            
            response = self.sqs_client.send_message(**params)
            message_id = response['MessageId']
            logger.info(f"Sent message {message_id} to queue")
            return message_id
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to send message: {e}")
            return None
    
    def send_batch_messages(
        self,
        messages: List[Dict[str, Any]],
        batch_size: int = 10
    ) -> Dict[str, int]:
        """
        Send multiple messages in batches.
        
        Args:
            messages: List of message dicts
            batch_size: Batch size (max 10 for SQS)
            
        Returns:
            Dict with success/failure counts
        """
        stats = {'successful': 0, 'failed': 0}
        
        for i in range(0, len(messages), batch_size):
            batch = messages[i:i+batch_size]
            entries = []
            
            for idx, msg in enumerate(batch):
                entries.append({
                    'Id': str(idx),
                    'MessageBody': json.dumps(msg)
                })
            
            try:
                response = self.sqs_client.send_message_batch(
                    QueueUrl=self.queue_url,
                    Entries=entries
                )
                
                stats['successful'] += len(response.get('Successful', []))
                stats['failed'] += len(response.get('Failed', []))
                
                if response.get('Failed'):
                    logger.warning(f"Failed to send {len(response['Failed'])} messages in batch")
            except (ClientError, BotoCoreError) as e:
                logger.error(f"Failed to send message batch: {e}")
                stats['failed'] += len(batch)
        
        logger.info(f"Batch send complete: {stats}")
        return stats
    
    def receive_messages(
        self,
        max_messages: int = 1,
        wait_time_seconds: int = 0,
        visibility_timeout: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Receive messages from the queue.
        
        Args:
            max_messages: Maximum number of messages to receive (1-10)
            wait_time_seconds: Long polling wait time (0-20 seconds)
            visibility_timeout: Visibility timeout (0-43200 seconds)
            
        Returns:
            List of message dicts
        """
        try:
            response = self.sqs_client.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=min(max_messages, 10),
                WaitTimeSeconds=wait_time_seconds,
                VisibilityTimeout=visibility_timeout,
                MessageAttributeNames=['All']
            )
            
            messages = []
            if 'Messages' in response:
                for msg in response['Messages']:
                    messages.append({
                        'message_id': msg['MessageId'],
                        'receipt_handle': msg['ReceiptHandle'],
                        'body': json.loads(msg['Body']),
                        'attributes': msg.get('Attributes', {}),
                        'message_attributes': msg.get('MessageAttributes', {})
                    })
                
                logger.info(f"Received {len(messages)} messages from queue")
            
            return messages
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to receive messages: {e}")
            return []
    
    def delete_message(self, receipt_handle: str) -> bool:
        """
        Delete a message from the queue.
        
        Args:
            receipt_handle: Receipt handle from received message
            
        Returns:
            True if deleted successfully
        """
        try:
            self.sqs_client.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle
            )
            logger.debug("Deleted message from queue")
            return True
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to delete message: {e}")
            return False
    
    def purge_queue(self) -> bool:
        """
        Purge all messages from the queue.
        
        Returns:
            True if purged successfully
        """
        try:
            self.sqs_client.purge_queue(QueueUrl=self.queue_url)
            logger.warning(f"Purged queue {self.queue_name}")
            return True
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to purge queue: {e}")
            return False
    
    def get_queue_attributes(self) -> Dict[str, Any]:
        """
        Get queue attributes.
        
        Returns:
            Dict with queue attributes
        """
        try:
            response = self.sqs_client.get_queue_attributes(
                QueueUrl=self.queue_url,
                AttributeNames=['All']
            )
            return response.get('Attributes', {})
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to get queue attributes: {e}")
            return {}
    
    def process_messages(
        self,
        handler: Callable[[Dict[str, Any]], bool],
        max_messages: int = 10,
        wait_time_seconds: int = 20,
        auto_delete: bool = True
    ) -> Dict[str, int]:
        """
        Process messages with a handler function.
        
        Args:
            handler: Function that processes message body, returns True on success
            max_messages: Maximum messages to process
            wait_time_seconds: Long polling wait time
            auto_delete: Auto-delete on successful processing
            
        Returns:
            Dict with processing statistics
        """
        stats = {'processed': 0, 'failed': 0, 'deleted': 0}
        
        messages = self.receive_messages(max_messages, wait_time_seconds)
        
        for msg in messages:
            try:
                success = handler(msg['body'])
                
                if success:
                    stats['processed'] += 1
                    if auto_delete:
                        if self.delete_message(msg['receipt_handle']):
                            stats['deleted'] += 1
                else:
                    stats['failed'] += 1
                    logger.warning(f"Handler failed for message {msg['message_id']}")
            except Exception as e:
                stats['failed'] += 1
                logger.error(f"Error processing message: {e}")
        
        logger.info(f"Processed {stats['processed']}/{len(messages)} messages")
        return stats


# Singleton instance
_sqs_service: Optional[SQSService] = None


def get_sqs_service() -> SQSService:
    """Get or create SQS service singleton."""
    global _sqs_service
    
    if _sqs_service is None:
        queue_name = os.getenv('SQS_QUEUE_ANALYSIS', 'stocktool-analysis-queue')
        endpoint_url = os.getenv('AWS_ENDPOINT_URL') if os.getenv('USE_LOCALSTACK', 'false').lower() == 'true' else None
        _sqs_service = SQSService(queue_name, endpoint_url)
    
    return _sqs_service
