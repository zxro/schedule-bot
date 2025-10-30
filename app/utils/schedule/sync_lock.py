import asyncio

# глобальный lock
_sync_lock = asyncio.Lock()

async def set_sync_running():
    """Установить флаг, что синхронизация идёт."""
    await _sync_lock.acquire()

def set_sync_finished():
    """Снять флаг (синхронизация закончена)."""
    if _sync_lock.locked():
        _sync_lock.release()

def is_sync_running() -> bool:
    """Проверить, идёт ли сейчас синхронизация."""
    return _sync_lock.locked()
