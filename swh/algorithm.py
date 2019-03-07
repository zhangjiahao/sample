# encoding: utf-8
from my.sdp.api import Order, Logger, OrderStatus, Direction, OpenClose
from string import digits
from enum import IntEnum, Enum


class OrderSplitMode(IntEnum):
    NORMAL = 0
    LOCK = 1


class ExecutionAlgorithm(Order, Logger):
    def __init__(self, context, config):
        self.flag_log_info = True   # switch to turn on/off strategy log
        super(ExecutionAlgorithm, self).__init__(context, config)
        self.active_orders = {}
        self._long_position, self._short_position = {}, {}
        self._yes_long_position, self._yes_short_position = {}, {}
        # initialize position
        for cont in config.contracts:
            self._long_position[cont.symbol] = cont.today_pos["long_volume"]
            self._short_position[cont.symbol] = cont.today_pos["short_volume"]
            self._yes_long_position[cont.symbol] = cont.yesterday_pos["long_volume"]
            self._yes_short_position[cont.symbol] = cont.yesterday_pos["short_volume"]
        if not self.flag_log_info:
            self.info = self.null_func
        else:
            self.info = self.log_with_time
        self.cur_time = 0
        self.bp1 = {}
        self.ap1 = {}
        self.switch_map = {}

    def null_func(self, *args, **kwargs):
        return

    def log_with_time(self, contents):
        print("[{}] {}".format(str(self.cur_time).zfill(9), contents))
        Logger.info(self, "[{}] {}".format(str(self.cur_time).zfill(9), contents))

    def long_position(self, symbol):
        """long position of given contract

        Parameters
        ----------
        symbol: str
            symbol of given contract

        Returns
        -------
        position: int
            return 0 if symbol is not tracked
        """   
        if symbol in self._long_position:
            return self._long_position[symbol]
        else:
            return 0

    def short_position(self, symbol):
        """short position of given contract

        Parameters
        ----------
        symbol: str
            symbol of given contract

        Returns
        -------
        position: int
            return 0 if symbol is not tracted

        """
        if symbol in self._short_position:
            return self._short_position[symbol]
        else:
            return 0

    def yes_long_position(self, symbol):
        """yesterday long position of given contract

        Parameters
        ----------
        symbol: str
            symbol of given contract

        Returns
        -------
        position: int
            return 0 if symbol is not tracted

        """
        if symbol in self._yes_long_position:
            return self._yes_long_position[symbol]
        else:
            return 0

    def yes_short_position(self, symbol):
        """yesterday short position of given contract

        Parameters
        ----------
        symbol: str
            symbol of given contract

        Returns
        -------
        position: int
            return 0 if symbol is not tracted

        """
        if symbol in self._yes_short_position:
            return self._yes_short_position[symbol]
        else:
            return 0

    def _record_order(self, order_id, symbol, price, size, direction, open_close, *args, **kwargs):
        """record sending single order"""
        self.active_orders[order_id] = {
            "order_id": order_id,
            "symbol": symbol,
            "price": price,
            "size": size,
            "direction": direction,
            "open_close": open_close,
            "investor_type": kwargs.get("investor_type"),
            "order_type": kwargs.get("order_type"),
            "time_in_force": kwargs.get("time_in_force"),
            # additional fields
            "pending_cancel": False,
            "cum_amount": 0.0,
            "cum_qty": 0,
            "last_px": 0.0,
            "last_qty": 0,
            "status": OrderStatus.INIT.value
        }

    def cancelling(self, symbol):
        """check if is cancelling orders of given symbol"""
        if any([order['pending_cancel'] for order in self.active_orders.values() if order['symbol'] == symbol]):
            return True
        else:
            return False

    def pending(self, symbol, direction):
        if any([order['direction'] == direction and order['symbol'] == symbol
                for order in self.active_orders.values()]):
            return True
        else:
            return False

    def send_split_orders(self, symbol, price, size, direction, mode=OrderSplitMode.NORMAL):
        ids = []
        # Close yesterday position first
        if direction == Direction.BUY:
            available_to_close_yes = self.yes_short_position(symbol)
        elif direction == Direction.SELL: 
            available_to_close_yes = self.yes_long_position(symbol)
        # split order
        if available_to_close_yes <= size:
            ids.append(self.send_single_order(symbol, price, available_to_close_yes, direction, OpenClose.CLOSE_YES))
            if mode == OrderSplitMode.NORMAL:
                ids.append(self.send_single_order(symbol, price, size - available_to_close_yes, direction, OpenClose.CLOSE))
            elif mode == OrderSplitMode.LOCK:
                ids.append(self.send_single_order(symbol, price, size - available_to_close_yes, direction, OpenClose.OPEN))
        else:
            ids.append(self.send_single_order(symbol, price, size, direction, OpenClose.CLOSE_YES))
        return ids

    def send_single_order(self, symbol, price, size, direction, open_close, *args, **kwargs):
        """wrapped send single order with logging and recording order """
        if size == 0 or self.cancelling(symbol):
            return 0
        order_id = Order.send_single_order(self, symbol, price, size, direction, open_close, args, kwargs)
        self.info("Send order: {} {} {} {} {} @ {}".format(
            order_id, symbol, Direction(direction).name, OpenClose(open_close).name, size, price)
        )
        if order_id > 0:
            self._record_order(order_id, symbol, price, size, direction, open_close, args, kwargs)
        return order_id

    def on_response(self, response_type, response):
        """includes following functions:
        1. logging responses.
        2. update positions.
        3. update orders if order is entrusted or finished.

        Parameters
        ----------
        response_type: int
        response: `obj:
            trade returns and response from counter and exchange 

        Returns
        -------
        None

        """
        self.info("Order Resp: {} {} {} {} {} @ {} {} {} {}".format(
            response.order_id, response.symbol, Direction(response.direction).name,
            OpenClose(response.open_close).name, response.exe_volume, response.exe_price,
            OrderStatus(response.status).name, response.error_no, response.error_info
        ))
        # update position
        if response.status in (OrderStatus.SUCCEED.value, OrderStatus.PARTED.value) and response.exe_volume > 0:
            close_actions = (OpenClose.CLOSE.value, OpenClose.CLOSE_TOD.value, OpenClose.CLOSE_YES.value)
            if response.direction == Direction.BUY.value:
                if response.open_close == OpenClose.OPEN.value:
                    self._long_position[response.symbol] += response.exe_volume
                elif response.open_close in close_actions:
                    self._short_position[response.symbol] -= response.exe_volume
                if response.open_close == OpenClose.CLOSE_YES.value:
                    self._yes_short_position[response.symbol] -= response.exe_volume
            elif response.direction == Direction.SELL.value:
                if response.open_close == OpenClose.OPEN.value:
                    self._short_position[response.symbol] += response.exe_volume
                elif response.open_close in close_actions:
                    self._long_position[response.symbol] -= response.exe_volume
                if response.open_close == OpenClose.CLOSE_YES.value:
                    self._yes_long_position[response.symbol] -= response.exe_volume

        # update order
        if (response.status == OrderStatus.SUCCEED.value and response.exe_volume > 0) or \
            response.status in (OrderStatus.CANCELED.value, OrderStatus.REJECTED.value, OrderStatus.INTERREJECTED.value):
            if response.order_id in self.active_orders:
                self.active_orders.pop(response.order_id)
        else:
            if response.order_id in self.active_orders:
                order = self.active_orders[response.order_id]
                if order["status"] == OrderStatus.INIT.value and response.status == OrderStatus.ENTRUSTED.value:
                    order["status"] = response.status
                elif response.status == OrderStatus.PARTED.value and response.exe_volume > 0:
                    order["cum_amount"] += response.exe_volume * response.exe_price
                    order["cum_qty"] += response.exe_volume
                    order["last_px"] = response.exe_price
                    order["last_qty"] = response.exe_volume
                    order["status"] = response.status
                elif response.status == OrderStatus.CANCEL_REJECTED.value:
                    if order["pending_cancel"]:
                        order["pending_cancel"] = False
                    order["status"] = response.status
                self.active_orders[response.order_id] = order

    def _record_cancel(self, order_id):
        """record cancelling single order"""
        if not self.active_orders[order_id]["pending_cancel"]:
            self.active_orders[order_id]["pending_cancel"] = True

    def cancel_single_order(self, order_id):
        """wrapped cancel single order with logging and recording cancel"""
        ret = 0
        if not self.active_orders[order_id]["pending_cancel"]:
            ret = Order.cancel_single_order(self, order_id)
            self.info("Cancel order: {}, ret: {}".format(order_id, ret))
            if ret == 0:
                self._record_cancel(order_id)
        return ret

    def cancel_all_orders(self):
        """Cancel all active orders

        Parameters
        ----------
        None

        Returns
        -------
        None

        """
        for order_id in self.active_orders.keys():
            self.cancel_single_order(order_id)

    def cancel_orders_by_side(self, symbol, side):
        """Cancel orders on given contract by side(BUY/SELL)

        Parameters
        ----------
        symbol: str
            symbol of contract
        side: my.sdp.api.Direction
            BUY/SELL

        Returns
        -------
        None

        """   
        for order_id, order in self.active_orders.items():
            if order['direction'] == side:
                self.cancel_single_order(order_id)

    def cancel_orders_by_side_flag(self, symbol, side, open_close):
        """Cancel orders on given contract by side(BUY/SELL) and flag(OPEN/CLOSE)

        Parameters
        ----------
        symbol: str
            symbol of contract
        side: my.sdp.api.Direction
            BUY/SELL
        open_close: my.sdp.api.OpenClose
            OPEN/CLOSE/CLOSE_YES

        Returns
        -------
        None

        """
        for order_id, order in self.active_orders.items():
            if order['direction'] == side and order['open_close'] == open_close:
                self.cancel_single_order(order_id)

    def cancel_orders_by_symbol(self, symbol):
        """Cancel all orders on given contract

        Parameters
        ----------
        symbol: str
            symbol of contract

        Returns
        -------
        None

        """   
        for order_id, order in self.active_orders.items():
            if order['symbol'] == symbol:
                self.cancel_single_order(order_id)
    
    def cancel_orders_by_idlist(self, idlist):
        """Cancel all orders in idlist

        Parameters
        ----------
        idlist: list
            list of id

        Returns
        -------
        None

        """
        for order_id in self.active_orders.keys():
            if order_id in idlist:
                self.cancel_single_order(order_id)

    def on_book(self, quote_type, quote):
        """set time in log and contract switching execution"""
        if quote_type == 0:
            self.cur_time = quote.int_time
            self.bp1[quote.symbol] = quote.bp_array[0]
            self.ap1[quote.symbol] = quote.ap_array[0]
            self.switch_with_target_pos(quote)
        elif quote_type == 1:
            self.cur_time = quote.exch_time
            self.bp1[quote.ticker] = quote.bp_array[0]
            self.ap1[quote.ticker] = quote.ap_array[0]

    def register_switch(self, from_con, to_con, position):
        """register contract to be switched at start of session

        Parameters
        ----------
        from_con: str
            switch-from symbol
        to_con: str
            swich-to symbol
        position: int
            amount of position to be switched

        Returns
        -------

        """
        self.switch_map[from_con] = {
            'target': to_con,
            'position': position,
            'from_ids': [],
            'to_ids': []
        }

    def switch_with_target_pos(self, quote):
        """switch execution"""
        if quote.symbol in self.switch_map:
            from_symbol, to_symbol = quote.symbol, self.switch_map[quote.symbol]['target']
            if to_symbol not in self.ap1:
                return
            from_long_pos, from_short_pos = self.long_position(from_symbol), self.short_position(from_symbol)
            to_long_pos, to_short_pos = self.long_position(to_symbol), self.short_position(to_symbol)
            _position = self.switch_map[from_symbol]['position']
            # exit

            if from_long_pos == from_short_pos and to_long_pos - to_short_pos == _position:
                self.switch_map.pop(from_symbol)
            if from_long_pos > from_short_pos:
                self.send_orders_target_pos(from_symbol, Direction.SELL, 0, self.bp1[from_symbol])
            elif from_long_pos < from_short_pos:
                self.send_orders_target_pos(from_symbol, Direction.BUY, 0, self.ap1[from_symbol])
            if _position > 0:
                self.send_orders_target_pos(to_symbol, Direction.BUY, _position, self.ap1[to_symbol])
            elif _position < 0:
                self.send_orders_target_pos(to_symbol, Direction.SELL, _position, self.bp1[to_symbol])