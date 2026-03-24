import asyncio
import aiohttp
import json
import logging
import time
import os
from typing import Dict, Tuple, Optional

PROXY_PUBLIC_IP = os.getenv("PROXY_PUBLIC_IP", "127.0.0.1")
REAL_API_URL = os.getenv("REAL_API_URL", "http://localhost/config")
HTTP_PORT = int(os.getenv("INTERNAL_HTTP_PORT", "8080"))
GAME_PORT_START = int(os.getenv("GAME_PORT_START", "20000"))
GAME_PORT_END = int(os.getenv("GAME_PORT_END", "20250"))
MAPPING_TTL = int(os.getenv("MAPPING_TTL", "300"))

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PortMapper:
    def __init__(self):
        self.mapping: Dict[int, Tuple[str, int, float]] = {}
        self.lock = asyncio.Lock()

    async def set_mapping(self, port: int, real_ip: str, real_port: int):
        async with self.lock:
            self.mapping[port] = (real_ip, real_port, time.time())
            logger.debug(f"Mapping: Port {port} -> {real_ip}:{real_port}")

    async def get_mapping(self, port: int) -> Optional[Tuple[str, int]]:
        async with self.lock:
            if port in self.mapping:
                real_ip, real_port, created_at = self.mapping[port]
                if time.time() - created_at < MAPPING_TTL:
                    return real_ip, real_port
                else:
                    del self.mapping[port]
            return None

    async def cleanup(self):
        while True:
            await asyncio.sleep(60)
            async with self.lock:
                now = time.time()
                expired = [p for p, (_, _, t) in self.mapping.items() if now - t > MAPPING_TTL]
                for p in expired:
                    del self.mapping[p]


mapper = PortMapper()

async def handle_http_request(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    client_addr = writer.get_extra_info('peername')
    logger.info(f"HTTP Request from {client_addr}")
    try:
        request_line = await reader.readline()
        if not request_line:
            return
        headers = b""
        while True:
            line = await reader.readline()
            headers += line
            if line == b"\r\n":
                break
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(REAL_API_URL, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'ipAddress' in data and 'port' in data:
                            if data.get('underMaintenance', 0) == 1:
                                logger.warning("Game server is under maintenance")
                            real_ip = data['ipAddress']
                            real_port = data['port']
                            await mapper.set_mapping(real_port, real_ip, real_port)
                            data['ipAddress'] = PROXY_PUBLIC_IP
                            response_body = json.dumps(data).encode('utf-8')
                            http_response = (
                                                b"HTTP/1.1 200 OK\r\n"
                                                b"Content-Type: application/json\r\n"
                                                b"Connection: close\r\n"
                                                b"\r\n"
                                            ) + response_body

                            writer.write(http_response)
                            await writer.drain()
                            logger.info(f"Config sent: {real_ip}:{real_port} -> {PROXY_PUBLIC_IP}:{real_port}")
                        else:
                            logger.error(f"Invalid JSON structure: {data}")
                            writer.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\nInvalid Config Format")
                    else:
                        logger.error(f"API Error: {response.status}")
                        writer.write(f"HTTP/1.1 {response.status} Error\r\n\r\n".encode())
            except Exception as e:
                logger.error(f"Failed to fetch config from real API: {e}")
                writer.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\nProxy API Error")
    except Exception as e:
        logger.error(f"HTTP Handler error: {e}")
    finally:
        writer.close()
        await writer.wait_closed()


async def forward_data(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, direction: str):
    try:
        while True:
            data = await reader.read(8192)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.debug(f"Forward error ({direction}): {e}")
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except:
            pass


async def handle_game_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, port: int):
    client_addr = writer.get_extra_info('peername')
    logger.info(f"Game connection on port {port} from {client_addr}")
    try:
        target = await mapper.get_mapping(port)
        if not target:
            logger.warning(f"No mapping found for port {port}. Closing connection.")
            writer.close()
            return
        real_ip, real_port = target
        logger.info(f"Connecting to real server {real_ip}:{real_port}")
        try:
            game_reader, game_writer = await asyncio.wait_for(
                asyncio.open_connection(real_ip, real_port),
                timeout=10
            )
        except Exception as e:
            logger.error(f"Cannot connect to real game server: {e}")
            writer.close()
            return
        task_c2g = asyncio.create_task(forward_data(reader, game_writer, "Client->Game"))
        task_g2c = asyncio.create_task(forward_data(game_reader, writer, "Game->Client"))
        done, pending = await asyncio.wait([task_c2g, task_g2c], return_when=asyncio.FIRST_COMPLETED)
        for p in pending:
            p.cancel()
            try:
                await p
            except asyncio.CancelledError:
                pass
    except Exception as e:
        logger.error(f"Game handler error: {e}")
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except:
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

    async with http_server:
        await http_server.serve_forever()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down...")