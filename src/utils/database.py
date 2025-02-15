import asyncio
import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    delete,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import joinedload, relationship
from sqlalchemy.schema import UniqueConstraint
from telebot import types as telebot_types

from src.utils.logger import MessageSpan

Base = declarative_base()

# NOTE: it is generally a good idea to make your database schema match your domain model
# At the moment all of our fields are the same, allowing us to interchange telebot types with our database types


class User(Base):  # type: ignore
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    # NOTE: Api docs says that a username maybe None, but we'll assume that it's always present
    # This will make it more straightforward in enforcing the unique constraint
    username = Column(String, nullable=True)
    first_name = Column(String)
    last_name = Column(String)
    language_code = Column(String)
    messages = relationship("Message", back_populates="from_user")


class Message(Base):  # type: ignore
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)

    # Chat ID and message ID are unique together
    chat_id = Column(Integer, nullable=False)

    from_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    from_user = relationship("User", back_populates="messages")

    reply_to_message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    reply_to_message = relationship("Message", remote_side=[id], backref="replies")

    text = Column(String)

    timestamp = Column(DateTime)

    __table_args__ = (UniqueConstraint("id", "chat_id", name="uix_id_chat_id"),)


# Database Initialization and helpers
class AsyncDatabase:
    def __init__(self, database_path: str):
        database_url = f"sqlite+aiosqlite:///{database_path}"
        self.engine = create_async_engine(database_url)
        self.async_session = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )
        # If this is an in-memory database, we need to create the tables
        asyncio.run(self.create_tables())

    async def create_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def add_message(
        self,
        message: telebot_types.Message,
        use_edit_date: bool = False,
        reply_to_message_id: int | None = None,
        span: MessageSpan | None = None,
    ):
        """
        Add a message to the database

        message: The message to add
        use_edit_date: Whether to use the edit date instead of the message date when the message is edited.
        This is useful in the context of recording finalized responses from our bot
        reply_to_message_id: The message ID this message is replying to. This is None in some cases, even when the message is a reply
        span: The span to use for tracing. If None, no tracing is done
        """

        async with self.async_session() as session:
            try:
                async with session.begin():
                    user = (
                        (
                            await session.execute(
                                select(User).filter(
                                    User.username == message.from_user.username
                                )
                            )
                        )
                        .scalars()
                        .first()
                    )
                    if not user:
                        user = User(
                            id=message.from_user.id,
                            username=message.from_user.username,
                            first_name=message.from_user.first_name,
                            last_name=message.from_user.last_name,
                            language_code=message.from_user.language_code,
                        )
                        session.add(user)

                    reply_to_id = reply_to_message_id or (
                        message.reply_to_message.message_id
                        if message.reply_to_message
                        else None
                    )
                    new_message = Message(
                        id=message.message_id,
                        chat_id=message.chat.id,
                        from_user_id=user.id,
                        reply_to_message_id=reply_to_id,
                        text=message.text,
                        timestamp=datetime.datetime.fromtimestamp(
                            message.edit_date if use_edit_date else message.date
                        ),
                    )
                    session.add(new_message)
            except Exception as e:
                if span:
                    span.error(
                        f"AsyncDatabase::add_message(): Error adding message: {e}"
                    )
                raise e

    async def get_chat_last_messages(
        self,
        chat_id: int,
        limit: int = 10,
        offset: int = 0,
        span: MessageSpan | None = None,
    ) -> list[Message]:
        """
        Get the last messages in a chat in batches and returns them in desc order

        chat_id: The chat ID to get the messages from
        limit: The maximum number of messages to get
        offset: The number of messages to skip
        span: The span to use for tracing. If None, no tracing is done
        """
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    select(Message)
                    .options(joinedload(Message.from_user))
                    .options(
                        joinedload(Message.reply_to_message).joinedload(
                            Message.from_user
                        )
                    )
                    .where(Message.chat_id == chat_id)
                    .order_by(Message.timestamp.desc())
                    .limit(limit)
                    .offset(offset)
                )

                messages = result.scalars().all()

                return list(messages)
        except Exception as e:
            if span:
                span.error(
                    f"AsyncDatabase::get_chat_last_message(): Error getting chat last messages: {e}"
                )
            raise e

    async def clear_chat_history(self, chat_id: int, span: MessageSpan | None = None):
        """
        Clear the chat history

        chat_id: The chat ID to clear the history of
        """
        try:
            async with self.async_session() as session:
                async with session.begin():
                    await session.execute(
                        delete(Message).where(Message.chat_id == chat_id)
                    )
        except Exception as e:
            if span:
                span.error(
                    f"AsyncDatabase::clear_chat_history(): Error clearing chat history: {e}"
                )
            raise e
