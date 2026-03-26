import asyncio
import aiohttp
import json
import logging
import time
import os
from typing import Dict, Tuple, Optional

# --- КОНФИГУРАЦИЯ ИЗ ENV ---
PROXY_PUBLIC_IP = os.getenv("PROXY_PUBLIC_IP", "127.0.0.1")
REAL_API_URL = os.getenv("REAL_API_URL", "http://localhost/config")
HTTP_PORT = int(os.getenv("INTERNAL_HTTP_PORT", "80"))
GAME_PORT_START = int(os.getenv("GAME_PORT_START", "20000"))
GAME_PORT_END = int(os.getenv("GAME_PORT_END", "20500"))
MAPPING_TTL = int(os.getenv("MAPPING_TTL", "300"))
CLEANUP_INTERVAL = int(os.getenv("CLEANUP_INTERVAL", "120"))

# Настройка логгирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PortMapper:
    def __init__(self):
        self.mapping: Dict[int, Dict] = {}
        self.lock = asyncio.Lock()
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'start_time': time.time()
        }

    async def get_free_port(self) -> Optional[int]:
        async with self.lock:
            now = time.time()
            expired = [p for p, m in self.mapping.items() if now - m['created_at'] > MAPPING_TTL]
            for p in expired:
                del self.mapping[p]
            for port in range(GAME_PORT_START, GAME_PORT_END + 1):
                if port not in self.mapping:
                    return port
            return None

    async def set_mapping(self, real_ip: str, real_port: int) -> Optional[int]:
        proxy_port = await self.get_free_port()
        if not proxy_port:
            logger.error("No free proxy ports available in pool!")
            return None

        async with self.lock:
            self.mapping[proxy_port] = {
                'real_ip': real_ip,
                'real_port': real_port,
                'created_at': time.time(),
                'last_activity': time.time()
            }
            self.stats['total_connections'] += 1
            self.stats['active_connections'] = len(self.mapping)
            logger.info(f"Mapping created: Proxy:{proxy_port} -> Real:{real_ip}:{real_port}")
            return proxy_port

    async def update_activity(self, proxy_port: int):
        async with self.lock:
            if proxy_port in self.mapping:
                self.mapping[proxy_port]['last_activity'] = time.time()

    async def get_mapping(self, proxy_port: int) -> Optional[Tuple[str, int]]:
        async with self.lock:
            if proxy_port in self.mapping:
                m = self.mapping[proxy_port]
                now = time.time()
                if now - m['created_at'] > MAPPING_TTL:
                    del self.mapping[proxy_port]
                    self.stats['active_connections'] = len(self.mapping)
                    return None
                return m['real_ip'], m['real_port']
            return None

    async def remove_mapping(self, proxy_port: int):
        async with self.lock:
            if proxy_port in self.mapping:
                del self.mapping[proxy_port]
                self.stats['active_connections'] = len(self.mapping)
                logger.info(f"Port {proxy_port} released (connection closed)")

    async def cleanup(self):
        while True:
            await asyncio.sleep(CLEANUP_INTERVAL)
            async with self.lock:
                now = time.time()
                expired = [p for p, m in self.mapping.items() if now - m['created_at'] > MAPPING_TTL]
                for p in expired:
                    del self.mapping[p]
                if expired:
                    self.stats['active_connections'] = len(self.mapping)
                    logger.info(f"Cleaned up {len(expired)} expired mappings")

    def get_stats(self) -> Dict:
        uptime = time.time() - self.stats['start_time']
        return {
            'status': 'running',
            'uptime_seconds': round(uptime, 2),
            'total_connections': self.stats['total_connections'],
            'active_connections': self.stats['active_connections'],
            'port_pool_size': GAME_PORT_END - GAME_PORT_START + 1,
            'ports_available': GAME_PORT_END - GAME_PORT_START + 1 - len(self.mapping)
        }


mapper = PortMapper()

async def handle_health_check(writer: asyncio.StreamWriter):
    stats = mapper.get_stats()
    response_body = json.dumps(stats, indent=2).encode('utf-8')
    http_response = (
                        b"HTTP/1.1 200 OK\r\n"
                        b"Content-Type: application/json\r\n"
                        b"Connection: close\r\n"
                        b"\r\n"
                    ) + response_body
    writer.write(http_response)
    await writer.drain()


async def handle_http_request(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    client_addr = writer.get_extra_info('peername')
    try:
        request_line = await reader.readline()
        if not request_line:
            return
        try:
            request_text = request_line.decode('utf-8', errors='ignore').strip()
            parts = request_text.split(' ')
            if len(parts) != 3 or not parts[0].upper() in ('GET', 'POST', 'HEAD'):
                logger.warning(f"Invalid HTTP from {client_addr}: {request_text[:50]}")
                writer.write(b"HTTP/1.1 400 Bad Request\r\n\r\n")
                await writer.drain()
                writer.close()
                return
            method, path, version = parts[0], parts[1], parts[2]
            if not version.startswith('HTTP/'):
                writer.write(b"HTTP/1.1 400 Bad Request\r\n\r\n")
                await writer.drain()
                writer.close()
                return
        except Exception as e:
            logger.warning(f"HTTP parse error from {client_addr}: {e}")
            writer.close()
            return
        headers = b""
        while True:
            line = await reader.readline()
            headers += line
            if line == b"\r\n":
                break
        if path == '/health':
            logger.info(f"Health check from {client_addr}")
            await handle_health_check(writer)
            writer.close()
            await writer.wait_closed()
            return
        logger.info(f"Config request from {client_addr}")
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(REAL_API_URL, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'ipAddress' in data and 'port' in data:
                            real_ip = data['ipAddress']
                            real_port = data['port']
                            proxy_port = await mapper.set_mapping(real_ip, real_port)
                            if not proxy_port:
                                writer.write(b"HTTP/1.1 503 Service Unavailable\r\n\r\nProxy Port Pool Exhausted")
                                await writer.drain()
                                return
                            data['ipAddress'] = PROXY_PUBLIC_IP
                            data['port'] = proxy_port
                            response_body = json.dumps(data).encode('utf-8')
                            http_response = (
                                                b"HTTP/1.1 200 OK\r\n"
                                                b"Content-Type: application/json\r\n"
                                                b"Connection: close\r\n"
                                                b"\r\n"
                                            ) + response_body
                            writer.write(http_response)
                            await writer.drain()
                            logger.info(f"Config sent: {real_ip}:{real_port} -> {PROXY_PUBLIC_IP}:{proxy_port}")
                        else:
                            logger.error(f"Invalid JSON structure: {data}")
                            writer.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\nInvalid Config Format")
                            await writer.drain()
                    else:
                        logger.error(f"API Error: {response.status}")
                        writer.write(f"HTTP/1.1 {response.status} Error\r\n\r\n".encode())
                        await writer.drain()
            except Exception as e:
                logger.error(f"Failed to fetch config from real API: {e}")
                writer.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\nProxy API Error")
                await writer.drain()
    except Exception as e:
        logger.error(f"HTTP Handler error: {e}")
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except (ConnectionResetError, BrokenPipeError, RuntimeError):
            pass


async def forward_data(reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
                       direction: str, proxy_port: int = None):
    try:
        while True:
            data = await reader.read(8192)
            if not data:
                break
            if proxy_port:
                await mapper.update_activity(proxy_port)
            writer.write(data)
            await writer.drain()
    except asyncio.CancelledError:
        pass
    except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
        logger.debug(f"Connection closed naturally ({direction})")
    except Exception as e:
        logger.debug(f"Forward error ({direction}): {type(e).__name__}")
    finally:
        if proxy_port:
            await mapper.remove_mapping(proxy_port)
        try:
            writer.close()
            await writer.wait_closed()
        except (ConnectionResetError, BrokenPipeError, RuntimeError):
            pass


async def handle_game_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, port: int):
    try:
        target = await mapper.get_mapping(port)
        if not target:
            writer.close()
            await writer.wait_closed()
            return
        real_ip, real_port = target
        logger.info(f"Connecting to real server {real_ip}:{real_port}")
        game_reader, game_writer = await asyncio.open_connection(real_ip, real_port)
        task_c2g = asyncio.create_task(forward_data(reader, game_writer, "Client->Game", port))
        task_g2c = asyncio.create_task(forward_data(game_reader, writer, "Game->Client", port))
        done, pending = await asyncio.wait([task_c2g, task_g2c], return_when=asyncio.FIRST_COMPLETED)
        for p in pending:
            p.cancel()
            try:
                await p
            except asyncio.CancelledError:
                pass
    except Exception as e:
        logger.error(f"Game handler error: {e}")
        await mapper.remove_mapping(port)
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except (ConnectionResetError, BrokenPipeError, RuntimeError):
            pass


async def start_game_server(port: int):
    server = await asyncio.start_server(
        lambda r, w: handle_game_client(r, w, port),
        '0.0.0.0',
        port
    )
    logger.info(f"Game listener started on port {port}")
    async with server:
        await server.serve_forever()


async def main():
    asyncio.create_task(mapper.cleanup())
    http_server = await asyncio.start_server(handle_http_request, '0.0.0.0', HTTP_PORT)
    logger.info(f"HTTP Config Proxy started on port {HTTP_PORT}")
    game_tasks = []
    for port in range(GAME_PORT_START, GAME_PORT_END + 1):
        task = asyncio.create_task(start_game_server(port))
        game_tasks.append(task)
    logger.info(f"Game Proxy started on ports {GAME_PORT_START}-{GAME_PORT_END}")
    logger.info(f"Health check available at: http://{PROXY_PUBLIC_IP}:{HTTP_PORT}/health")
    async with http_server:
        await http_server.serve_forever()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down...")