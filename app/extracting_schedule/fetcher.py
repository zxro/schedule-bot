"""
HTTP-клиент для scheduler API: извлекает группы и расписания.
Использует httpx (асинхронный) с повторными попытками и ограничением скорости.
"""
import asyncio
import httpx
import logging
from urllib.parse import quote_plus
from app.config import settings

logger = logging.getLogger(__name__)

class TimetableClient:
    """
    Асинхронный клиент для получения данных с расписания.

    Поля:
        base (str): Базовый URL (по умолчанию из настроек).
        semaphore (asyncio.Semaphore): Ограничение числа одновременно выполняющихся запросов.
        delay (float): Задержка между запросами (rate-limiting).
        client (httpx.AsyncClient): Асинхронный HTTP-клиент для выполнения запросов.

    Методы:
        close(): Закрывает клиент и освобождает ресурсы.
        fetch_groups(): Получает список всех групп.
        fetch_timetable_for_group(group_name, type_idx=0): Получает расписание для конкретной группы.
    """

    def __init__(self, base_url: str = None, concurrency: int = None, delay: float = None):
        """
        Инициализация клиента.

        Параметры:
            base_url (str, optional): URL API. Если None, берётся из настроек.
            concurrency (int, optional): Максимальное число одновременных запросов.
            delay (float, optional): Задержка между запросами в секундах.

        Создаёт httpx.AsyncClient с таймаутом 20 секунд и заголовками:
            Accept: application/json
            User-Agent: tversu-schedule/1.0
        """

        self.base = base_url or settings.TIMETABLE_API_BASE
        self.semaphore = asyncio.Semaphore(concurrency or settings.REQUEST_CONCURRENCY)
        self.delay = delay if delay is not None else settings.REQUEST_DELAY
        self.client = httpx.AsyncClient(timeout=20.0, headers={"Accept": "application/json", "User-Agent": "tversu-schedule"})

    async def close(self):
        """
        Закрывает асинхронный HTTP-клиент.
        Обязательно вызывать после завершения работы с клиентом, чтобы корректно освободить соединения.
        """

        await self.client.aclose()

    async def request_with_retry(self, url: str, max_retries: int = None):
        """
        Выполняет GET-запрос с повторными попытками при ошибках сети или сервера.

        Логика:
        - Ограничение числа одновременно выполняющихся запросов через semaphore.
        - Задержка между запросами (self.delay) для polite rate-limiting.
        - Обработка ошибок:
            - 404: возвращает JSON или словарь {"status": 404, "message": "Not found"}.
            - 429: экспоненциальная пауза и повторная попытка.
            - 5xx: экспоненциальная пауза и повторная попытка.
            - Прочие ошибки: выброс исключения.
        - Экспоненциальный backoff: backoff^attempt.

        Параметры:
            url (str): URL для GET-запроса.
            max_retries (int, optional): Максимальное число повторных попыток.

        Возвращает:
            dict: Распарсенный JSON-ответ от сервера.

        Исключения:
            Любые ошибки, которые не удалось обработать после всех попыток, пробрасываются.
        """

        max_retries = max_retries or settings.MAX_RETRIES
        backoff = settings.RETRY_BACKOFF_FACTOR
        last_exc = None
        for attempt in range(1, max_retries + 1):
            try:
                async with self.semaphore:
                    r = await self.client.get(url)
                    await asyncio.sleep(self.delay)
                r.raise_for_status()
                return r.json()
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status == 404:
                    try:
                        return e.response.json()
                    except Exception:
                        return {"status": status, "message": "Not found"}
                if status == 429:
                    wait = backoff ** attempt
                    logger.warning("Ошибка сервера %s; повторная попытка через %.1fs (попытка %d/%d)", wait)
                    await asyncio.sleep(wait)
                    last_exc = e
                    continue
                last_exc = e
                if 500 <= status < 600:
                    wait = backoff ** attempt
                    logger.warning("Ошибка сервера %s; повторная попытка через %.1fs (попытка %d/%d)", status, wait, attempt, max_retries)
                    await asyncio.sleep(wait)
                    continue
                raise
            except Exception as e:
                last_exc = e
                wait = backoff ** attempt
                logger.warning("Ошибка запроса: %s; повторная попытка  через %.1fs (попытка %d/%d)", e, wait, attempt, max_retries)
                await asyncio.sleep(wait)

        raise last_exc

    async def fetch_groups(self):
        """
        Получает список всех групп с URL.

        Возвращает:
            dict: JSON с данными групп.
        """

        url = f"{self.base}/groups"
        return await self.request_with_retry(url)

    async def fetch_timetable_for_group(self, group_name: str, type_idx: int = 0):
        """
        Получает расписание для конкретной группы.

        Параметры:
            group_name (str): Название группы (будет закодировано в URL).
            type_idx (int, optional): Тип расписания (по умолчанию 0).

        Возвращает:
            dict: JSON с данными расписания группы.
        """

        q = quote_plus(group_name, safe='')
        url = f"{self.base}/timetable?group_name={q}&type={type_idx}"
        return await self.request_with_retry(url)
