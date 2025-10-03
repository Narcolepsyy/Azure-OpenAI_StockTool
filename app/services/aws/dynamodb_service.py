"""AWS DynamoDB service for conversation history and caching."""
import os
import json
import logging
import time
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from botocore.config import Config

logger = logging.getLogger(__name__)


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder for Decimal types."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


class DynamoDBService:
    """Service for managing data in DynamoDB."""
    
    def __init__(
        self,
        table_name: str,
        endpoint_url: Optional[str] = None,
        ttl_hours: int = 24
    ):
        """
        Initialize DynamoDB service.
        
        Args:
            table_name: Name of the DynamoDB table
            endpoint_url: Optional endpoint URL (for LocalStack)
            ttl_hours: Default TTL in hours for items
        """
        self.table_name = table_name
        self.ttl_hours = ttl_hours
        
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
        
        self.dynamodb_client = boto3.client('dynamodb', **client_kwargs)
        self.dynamodb_resource = boto3.resource('dynamodb', **client_kwargs)
        self.table = self.dynamodb_resource.Table(table_name)
    
    def _get_ttl_timestamp(self, hours: Optional[int] = None) -> int:
        """Calculate TTL timestamp."""
        hours = hours or self.ttl_hours
        return int((datetime.utcnow() + timedelta(hours=hours)).timestamp())
    
    def put_conversation(
        self,
        conversation_id: str,
        messages: List[Dict[str, Any]],
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ttl_hours: Optional[int] = None
    ) -> bool:
        """
        Store conversation history.
        
        Args:
            conversation_id: Unique conversation ID
            messages: List of message dicts
            user_id: Optional user ID
            metadata: Optional metadata dict
            ttl_hours: Optional TTL in hours (defaults to instance ttl_hours)
            
        Returns:
            True if stored successfully
        """
        try:
            item = {
                'conversation_id': conversation_id,
                'timestamp': int(time.time() * 1000),  # milliseconds
                'messages': json.dumps(messages),  # Serialize to JSON string
                'ttl': self._get_ttl_timestamp(ttl_hours),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            if user_id:
                item['user_id'] = user_id
            if metadata:
                item['metadata'] = json.dumps(metadata)
            
            self.table.put_item(Item=item)
            logger.info(f"Stored conversation {conversation_id} with {len(messages)} messages")
            return True
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to store conversation: {e}")
            return False
    
    def get_conversation(
        self,
        conversation_id: str,
        limit: Optional[int] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve conversation history.
        
        Args:
            conversation_id: Conversation ID to retrieve
            limit: Optional limit on number of recent turns
            
        Returns:
            List of messages or None if not found
        """
        try:
            response = self.table.query(
                KeyConditionExpression='conversation_id = :conv_id',
                ExpressionAttributeValues={':conv_id': conversation_id},
                ScanIndexForward=False,  # Latest first
                Limit=limit or 1
            )
            
            if response['Items']:
                item = response['Items'][0]
                messages = json.loads(item['messages'])
                logger.info(f"Retrieved conversation {conversation_id} with {len(messages)} messages")
                return messages
            
            logger.info(f"Conversation {conversation_id} not found")
            return None
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to retrieve conversation: {e}")
            return None
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation.
        
        Args:
            conversation_id: Conversation ID to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            # Get all items with this conversation_id
            response = self.table.query(
                KeyConditionExpression='conversation_id = :conv_id',
                ExpressionAttributeValues={':conv_id': conversation_id}
            )
            
            # Batch delete
            with self.table.batch_writer() as batch:
                for item in response['Items']:
                    batch.delete_item(
                        Key={
                            'conversation_id': item['conversation_id'],
                            'timestamp': item['timestamp']
                        }
                    )
            
            logger.info(f"Deleted conversation {conversation_id}")
            return True
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to delete conversation: {e}")
            return False
    
    def list_conversations(
        self,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List conversations.
        
        Args:
            user_id: Optional filter by user ID
            limit: Maximum conversations to return
            
        Returns:
            List of conversation metadata
        """
        try:
            if user_id:
                # Need a GSI on user_id for efficient queries
                # For now, scan (not recommended for production)
                response = self.table.scan(
                    FilterExpression='user_id = :uid',
                    ExpressionAttributeValues={':uid': user_id},
                    Limit=limit
                )
            else:
                response = self.table.scan(Limit=limit)
            
            conversations = []
            seen_ids = set()
            
            for item in response['Items']:
                conv_id = item['conversation_id']
                if conv_id not in seen_ids:
                    seen_ids.add(conv_id)
                    conversations.append({
                        'conversation_id': conv_id,
                        'timestamp': item['timestamp'],
                        'updated_at': item.get('updated_at'),
                        'user_id': item.get('user_id'),
                        'message_count': len(json.loads(item['messages']))
                    })
            
            # Sort by timestamp descending
            conversations.sort(key=lambda x: x['timestamp'], reverse=True)
            logger.info(f"Listed {len(conversations)} conversations")
            return conversations
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to list conversations: {e}")
            return []
    
    def put_cache_item(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = 300,
        namespace: str = "default"
    ) -> bool:
        """
        Store a cache item.
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl_seconds: TTL in seconds
            namespace: Cache namespace
            
        Returns:
            True if stored successfully
        """
        try:
            item = {
                'symbol': f"{namespace}#{key}",  # Composite key
                'data_type': 'cache',
                'value': json.dumps(value, cls=DecimalEncoder),
                'ttl': int(time.time() + ttl_seconds),
                'created_at': datetime.utcnow().isoformat()
            }
            
            self.table.put_item(Item=item)
            logger.debug(f"Cached item {namespace}#{key} with TTL {ttl_seconds}s")
            return True
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to cache item: {e}")
            return False
    
    def get_cache_item(self, key: str, namespace: str = "default") -> Optional[Any]:
        """
        Retrieve a cache item.
        
        Args:
            key: Cache key
            namespace: Cache namespace
            
        Returns:
            Cached value or None if not found/expired
        """
        try:
            response = self.table.get_item(
                Key={
                    'symbol': f"{namespace}#{key}",
                    'data_type': 'cache'
                }
            )
            
            if 'Item' in response:
                item = response['Item']
                # Check TTL
                if item['ttl'] > int(time.time()):
                    value = json.loads(item['value'])
                    logger.debug(f"Cache hit for {namespace}#{key}")
                    return value
                else:
                    logger.debug(f"Cache expired for {namespace}#{key}")
                    return None
            
            logger.debug(f"Cache miss for {namespace}#{key}")
            return None
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to retrieve cache item: {e}")
            return None


# Singleton instances
_conversation_service: Optional[DynamoDBService] = None
_cache_service: Optional[DynamoDBService] = None


def get_dynamodb_service(service_type: str = "conversation") -> DynamoDBService:
    """
    Get or create DynamoDB service singleton.
    
    Args:
        service_type: Type of service ("conversation" or "cache")
    """
    global _conversation_service, _cache_service
    
    endpoint_url = os.getenv('AWS_ENDPOINT_URL') if os.getenv('USE_LOCALSTACK', 'false').lower() == 'true' else None
    
    if service_type == "conversation":
        if _conversation_service is None:
            table_name = os.getenv('DYNAMODB_TABLE_CONVERSATIONS', 'stocktool-conversations')
            _conversation_service = DynamoDBService(table_name, endpoint_url, ttl_hours=24)
        return _conversation_service
    elif service_type == "cache":
        if _cache_service is None:
            table_name = os.getenv('DYNAMODB_TABLE_CACHE', 'stocktool-stock-cache')
            _cache_service = DynamoDBService(table_name, endpoint_url, ttl_hours=1)
        return _cache_service
    else:
        raise ValueError(f"Unknown service type: {service_type}")
