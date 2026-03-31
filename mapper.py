# mapper.py
import asyncio
import time
from typing import Dict, Tuple, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class Mapping:
    """Маппинг для одного клиента"""
    client_ip: str
    client_port: int
    real_ip: str
    real_port: int
    proxy_port: int
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)

    def is_expired(self, timeout: float = 1800) -> bool:
        return time.time() - self.last_activity > timeout


class PortMapper:
    """Менеджер маппингов: клиент → реальный сервер"""

    def __init__(self, proxy_ip: str):
        self.proxy_ip = proxy_ip
        self.mappings: Dict[Tuple[str, int], Mapping] = {}
        self.lock = asyncio.Lock()

    async def create_mapping(self, client_ip: str, client_port: int,
                             real_ip: str, real_port: int) -> Optional[int]:
        """Создаёт маппинг для клиента"""
        async with self.lock:
            key = (client_ip, client_port)

            # Если уже есть маппинг — обновляем
            if key in self.mappings:
                m = self.mappings[key]
                m.real_ip = real_ip
                m.real_port = real_port
                m.last_activity = time.time()
                logger.info(f"Updated mapping: {client_ip}:{client_port} → {real_ip}:{real_port}")
                return m.proxy_port

            # Создаём новый (порт = порт реального сервера)
            proxy_port = real_port

            self.mappings[key] = Mapping(
                client_ip=client_ip,
                client_port=client_port,
                real_ip=real_ip,
                real_port=real_port,
                proxy_port=proxy_port
            )

            logger.info(f"Created mapping: {client_ip}:{client_port} → {real_ip}:{real_port}")
            return proxy_port

    async def get_mapping(self, client_ip: str, client_port: int) -> Optional[Mapping]:
        """Получает маппинг для клиента"""
        async with self.lock:
            return self.mappings.get((client_ip, client_port))

    async def remove_mapping(self, client_ip: str, client_port: int):
        """Удаляет маппинг"""
        async with self.lock:
            key = (client_ip, client_port)
            if key in self.mappings:
                del self.mappings[key]
                logger.debug(f"Removed mapping: {client_ip}:{client_port}")

    async def cleanup_expired(self, timeout: float = 1800):
        """Очищает устаревшие маппинги"""
        async with self.lock:
            expired = [k for k, m in self.mappings.items() if m.is_expired(timeout)]
            for key in expired:
                del self.mappings[key]
            if expired:
                logger.info(f"Cleaned up {len(expired)} expired mappings")