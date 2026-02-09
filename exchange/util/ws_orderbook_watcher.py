import threading
import asyncio
import ccxt.pro as ccxtpro


class WSOrderbookWatcher:
    def __init__(self, primary_id, secondary_id, symbol):

        self.primary_ccxt = getattr(ccxtpro, primary_id)({
            "enableRateLimit": True,
            "options": {"defaultType": "spot"}
        })

        self.secondary_ccxt = getattr(ccxtpro, secondary_id)({
            "enableRateLimit": True,
            "options": {"defaultType": "spot"}
        })

        self.symbol = symbol
        self.shared_dict = {'primary': None, 'secondary': None}

        self.update_event = threading.Event()

        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._start_loop, daemon=True)
        self.thread.start()

    def _start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.create_task(self._watch_primary())
        self.loop.create_task(self._watch_secondary())
        self.loop.run_forever()

    async def _watch_primary(self):
        await self.primary_ccxt.load_markets()
        while True:
            try:
                ob = await self.primary_ccxt.watch_order_book(self.symbol)
                self.shared_dict['primary'] = ob
                self.update_event.set()
            except Exception as e:
                print("Primary error:", e)
                await asyncio.sleep(1)

    async def _watch_secondary(self):
        await self.secondary_ccxt.load_markets()
        while True:
            try:
                ob = await self.secondary_ccxt.watch_order_book(self.symbol)
                self.shared_dict['secondary'] = ob
                self.update_event.set()
            except Exception as e:
                print("Secondary error:", e)
                await asyncio.sleep(1)

    def wait_update(self, timeout=None):
        updated = self.update_event.wait(timeout)
        self.update_event.clear()
        return updated

    def get_orderbooks(self):
        return self.shared_dict['primary'], self.shared_dict['secondary']

    def stop(self):
        for task in asyncio.all_tasks(self.loop):
            task.cancel()
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(timeout=1)
