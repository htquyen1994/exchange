import threading
import asyncio
import ccxt.pro as ccxtpro

class WSOrderbookWatcher:
    def __init__(self, primary_id, secondary_id, symbol):
        # Tạo ccxt pro riêng
        self.primary_ccxt = getattr(ccxtpro, primary_id)()
        self.secondary_ccxt = getattr(ccxtpro, secondary_id)()
        self.symbol = symbol

        self.shared_dict = {'primary': None, 'secondary': None}
        self.update_event = threading.Event()
        self.start_flag = False

        self.prev_primary = None
        self.prev_secondary = None

        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._start_loop, daemon=True)
        self.thread.start()

    def _start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._watch_loop())
        self.loop.run_forever()

    async def _watch_loop(self):
        while True:
            try:
                primary_task = asyncio.create_task(self.primary_ccxt.watch_order_book(self.symbol))
                secondary_task = asyncio.create_task(self.secondary_ccxt.watch_order_book(self.symbol))
                done, pending = await asyncio.wait(
                    [primary_task, secondary_task],
                    return_when=asyncio.FIRST_COMPLETED
                )
                for task in done:
                    ob = task.result()
                    if task == primary_task:
                        self.shared_dict['primary'] = ob
                    else:
                        self.shared_dict['secondary'] = ob
                for task in pending:
                    task.cancel()
                self.update_event.set()
            except Exception as e:
                print("Watcher error:", e)
                await asyncio.sleep(1)

    def wait_update(self, timeout=None):
        updated = self.update_event.wait(timeout)
        self.update_event.clear()
        return updated

    def get_orderbooks(self):
        return self.shared_dict['primary'], self.shared_dict['secondary']

    def stop(self):
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(timeout=1)
