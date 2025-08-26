from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
import os
import logging
import asyncio


class MongoDB:
    client: Optional[AsyncIOMotorClient] = None
    database: Optional[AsyncIOMotorDatabase] = None
    _pid: Optional[int] = None
    _loop_id: Optional[int] = None

    @classmethod
    async def connect_to_mongo(cls, connection_string: str, database_name: str):
        """Create database connection"""
        logging.debug("[MongoDB] connecting url=%s db=%s", connection_string, database_name)
        cls.client = AsyncIOMotorClient(connection_string)
        cls.database = cls.client[database_name]
        cls._pid = os.getpid()
        try:
            cls._loop_id = id(asyncio.get_running_loop())
        except RuntimeError:
            # Not in an event loop; leave as None
            cls._loop_id = None

    @classmethod
    async def ensure_connection(cls, connection_string: str, database_name: str):
        """Ensure a valid connection exists in the current process (fork-safe)."""
        current_pid = os.getpid()
        try:
            current_loop_id = id(asyncio.get_running_loop())
        except RuntimeError:
            current_loop_id = None

        need_reconnect = False
        reasons = []
        if cls.database is None:
            need_reconnect = True
            reasons.append("uninitialized")
        if cls._pid is not None and cls._pid != current_pid:
            need_reconnect = True
            reasons.append(f"pid_changed old={cls._pid} new={current_pid}")
        if (cls._loop_id is not None and current_loop_id is not None and cls._loop_id != current_loop_id):
            need_reconnect = True
            reasons.append(f"loop_changed old={cls._loop_id} new={current_loop_id}")

        if need_reconnect:
            logging.debug("[MongoDB] ensure_connection reconnecting due to %s", ", ".join(reasons) or "unknown")
            # (Re)initialize client in this process/loop
            await cls.connect_to_mongo(connection_string, database_name)

    @classmethod
    async def close_mongo_connection(cls):
        """Close database connection"""
        if cls.client:
            cls.client.close()
        cls.client = None
        cls.database = None
        cls._pid = None
        cls._loop_id = None

    @classmethod
    def get_database(cls) -> AsyncIOMotorDatabase:
        """Get database instance"""
        if cls.database is None:
            raise RuntimeError("Database not initialized")
        return cls.database
