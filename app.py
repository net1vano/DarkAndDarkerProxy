# app.py
import asyncio
import aiohttp
import json
import logging
import signal
import sys

from config import (
    PROXY_PUBLIC_IP, PROXY_HTTP_PORT,
    TARGET_HOST, TARGET_PATH, TARGET_API_URL, LOG_LEVEL
)
from mapper import PortMapper

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Глобальный маппер
mapper = PortMapper(PROXY_PUBLIC_IP)


async def handle_http_request(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """
    HTTP парсер: перехватывает конфиг, сохраняет маппинг, отправляет модифицированный ответ.
    """
    client_addr = writer.get_extra_info('peername')
    if not client_addr:
        writer.close()
        return

    client_ip, client_port = client_addr

    try:
        # Читаем первую строку
        request_line = await asyncio.wait_for(reader.readline(), timeout=10)
        if not request_line:
            return

        # Парсим метод и путь
        parts = request_line.decode().strip().split()
        if len(parts) < 3 or parts[0].upper() != 'GET':
            writer.close()
            return

        path = parts[1]

        # Читаем заголовки
        headers = {}
        while True:
            line = await asyncio.wait_for(reader.readline(), timeout=10)
            if line in (b'\r\n', b'\n', b''):
                break
            if b':' in line:
                k, v = line.decode().split(':', 1)
                headers[k.strip().lower()] = v.strip()

        # 🔐 Фильтр: только целевой домен + путь
        host = headers.get('host', '').split(':')[0].lower()
        if host != TARGET_HOST.lower() or path != TARGET_PATH:
            logger.debug(f"Rejected: {host}{path} from {client_ip}")
            writer.close()
            return

        logger.info(f"✓ Intercepted: {host}{path} from {client_ip}:{client_port}")

        # Запрашиваем реальный конфиг
        async with aiohttp.ClientSession() as session:
            async with session.get(TARGET_API_URL, timeout=10) as response:
                if response.status != 200:
                    writer.write(f"HTTP/1.1 {response.status} Error\r\n\r\n".encode())
                    await writer.drain()
                    return

                config = await response.json()

                # Валидация
                if 'ipAddress' not in config or 'port' not in config:
                    writer.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\nInvalid Config")
                    await writer.drain()
                    return

                # 🎯 Сохраняем маппинг
                real_ip = config['ipAddress']
                real_port = config['port']

                await mapper.create_mapping(client_ip, client_port, real_ip, real_port)

                # 🔑 ПОДМЕНА: реальный IP → прокси IP
                config['ipAddress'] = PROXY_PUBLIC_IP
                # Порт оставляем тот же (клиент подключится на proxy_ip:real_port)

                # Отправляем модифицированный JSON
                body = json.dumps(config).encode()
                http_response = (
                                        b"HTTP/1.1 200 OK\r\n"
                                        b"Content-Type: application/json\r\n"
                                        b"Content-Length: " + str(len(body)).encode() + b"\r\n"
                                                                                        b"Connection: close\r\n"
                                                                                        b"\r\n"
                                ) + body

                writer.write(http_response)
                await writer.drain()

                logger.info(f"✅ Sent to {client_ip}: {PROXY_PUBLIC_IP}:{real_port} (real: {real_ip}:{real_port})")

    except asyncio.TimeoutError:
        logger.warning(f"HTTP timeout from {client_ip}")
    except Exception as e:
        logger.error(f"Handler error: {e}")
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except:
            pass


async def cleanup_task():
    """Фоновая задача очистки устаревших маппингов"""
    while True:
        await asyncio.sleep(60)
        await mapper.cleanup_expired()


async def main():
    logger.info(f"🚀 Starting HTTP Proxy on {PROXY_PUBLIC_IP}:{PROXY_HTTP_PORT}")
    logger.info(f"🎯 Target: http://{TARGET_HOST}{TARGET_PATH}")

    # Запуск очистки
    asyncio.create_task(cleanup_task())

    # HTTP сервер
    server = await asyncio.start_server(
        handle_http_request,
        '0.0.0.0', PROXY_HTTP_PORT
    )

    logger.info(f"✅ Listening on port {PROXY_HTTP_PORT}")

    # Обработка остановки
    def shutdown():
        logger.info("🛑 Shutting down...")
        server.close()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda s, f: shutdown())

    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass