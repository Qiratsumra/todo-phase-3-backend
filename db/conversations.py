"""
Database helper functions for conversation and message management.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import logging
import json

from models import Conversation, Message

logger = logging.getLogger("db.conversations")


def create_conversation(db: Session, user_id: str) -> Conversation:
    """
    Create a new conversation for a user.

    Args:
        db: Database session
        user_id: ID of the user

    Returns:
        Created Conversation object
    """
    conversation = Conversation(
        user_id=user_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    logger.info(f"Created conversation {conversation.id} for user {user_id}")
    return conversation


def get_conversation(db: Session, conversation_id: int, user_id: str) -> Optional[Conversation]:
    """
    Get a conversation by ID, ensuring it belongs to the user.

    Args:
        db: Database session
        conversation_id: ID of the conversation
        user_id: ID of the user (for security check)

    Returns:
        Conversation object if found and belongs to user, None otherwise
    """
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user_id
    ).first()
    return conversation


def get_or_create_conversation(db: Session, user_id: str, conversation_id: Optional[int] = None) -> Conversation:
    """
    Get an existing conversation or create a new one.

    Args:
        db: Database session
        user_id: ID of the user
        conversation_id: Optional existing conversation ID

    Returns:
        Conversation object
    """
    if conversation_id:
        conversation = get_conversation(db, conversation_id, user_id)
        if conversation:
            return conversation

    # Get most recent conversation for user or create new
    conversation = db.query(Conversation).filter(
        Conversation.user_id == user_id
    ).order_by(Conversation.updated_at.desc()).first()

    if not conversation:
        conversation = create_conversation(db, user_id)

    return conversation


def store_message(
    db: Session,
    conversation_id: int,
    user_id: str,
    role: str,
    content: str,
    tool_calls: Optional[List[dict]] = None,
    skill_used: Optional[str] = None
) -> Message:
    """
    Store a message in the conversation.

    Args:
        db: Database session
        conversation_id: ID of the conversation
        user_id: ID of the user
        role: Message role ("user" or "assistant")
        content: Message content
        tool_calls: Optional list of tool call dicts
        skill_used: Optional skill name that processed this message

    Returns:
        Created Message object
    """
    message = Message(
        conversation_id=conversation_id,
        user_id=user_id,
        role=role,
        content=content,
        tool_calls=tool_calls,
        skill_used=skill_used,
        created_at=datetime.now(timezone.utc)
    )
    db.add(message)

    # Update conversation timestamp
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conversation:
        conversation.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(message)
    logger.info(f"Stored {role} message {message.id} in conversation {conversation_id}")
    return message


def get_conversation_history(
    db: Session,
    conversation_id: int,
    user_id: str,
    limit: int = 50
) -> List[Message]:
    """
    Get conversation history (most recent messages).

    Args:
        db: Database session
        conversation_id: ID of the conversation
        user_id: ID of the user (for security check)
        limit: Maximum number of messages to return

    Returns:
        List of Message objects, oldest first
    """
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id,
        Message.user_id == user_id
    ).order_by(Message.created_at.asc()).limit(limit).all()

    return messages


def delete_conversation(db: Session, conversation_id: int, user_id: str) -> bool:
    """
    Delete a conversation and all its messages.

    Args:
        db: Database session
        conversation_id: ID of the conversation
        user_id: ID of the user (for security check)

    Returns:
        True if deleted, False if not found
    """
    conversation = get_conversation(db, conversation_id, user_id)
    if not conversation:
        return False

    db.delete(conversation)
    db.commit()
    logger.info(f"Deleted conversation {conversation_id}")
    return True


def format_history_for_llm(messages: List[Message]) -> List[dict]:
    """
    Format message history for LLM API calls.

    Args:
        messages: List of Message objects

    Returns:
        List of message dicts with 'role' and 'content'
    """
    return [
        {"role": msg.role, "content": msg.content}
        for msg in messages
    ]
