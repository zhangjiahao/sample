import numpy as np

try:
    """Configuration for Simulation
    Under Linux simulation, api in included as part of strategy
    by cython, therefore anything from api module should not included.
    """
    from my.sdp.api import (Direction, OpenClose, OrderStatus,
                            InvestorType, OrderType, TIF)
except ImportError:
    pass


class OrdMgr(object):
    """Order management
    """

    class Order(object):
        """Order class
        """
        def __init__(self, order_id, symbol, volume, price, direction, open_close, investor_type,
                    order_type, time_in_force):
            self.order_id = order_id
            self.symbol = symbol
            self.volume = volume
            self.price = price
            self.direction = direction
            self.open_close = open_close
            self.investor_type = investor_type
            self.order_type = order_type
            self.time_in_force = time_in_force
            # additional info
            self.last_px = 0
            self.last_qty = 0
            self.cum_qty = 0
            self.cum_amount = 0
            self.pending_cancel = False
            self.status = OrderStatus.INIT.value

        @property
        def leaves_qty(self):
            """quantity not filled
            """
            if self.volume > self.cum_qty:
                return self.volume - self.cum_qty
            else:
                return 0

        @property
        def left_to_buy(self):
            """quantity left to buy
            """
            if self.direction == Direction.BUY.value:
                return self.leaves_qty
            else:
                return 0

        @property
        def left_to_sell(self):
            """quantity left to sell
            """
            if self.direction == Direction.SELL.value:
                return self.leaves_qty
            else:
                return 0

        def update(self, response_type, response):
            """update order status

            Parameters
            ----------
            response_type : int
                type of response
            response : response
                update order based on response

            Returns
            -------
            None

            """
            if response.status in (OrderStatus.SUCCEED.value, OrderStatus.PARTED.value):
                if response.exe_volume == 0:
                    return
                self.cum_amount += response.exe_volume * response.exe_price
                self.cum_qty += response.exe_volume
                self.last_px = response.exe_price
                self.last_qty = response.exe_volume
            if self.status != OrderStatus.INIT.value and response.status == OrderStatus.ENTRUSTED.value:
                pass    # If already entrusted, no need to update response status
            else:
                self.status = response.status

    def __init__(self):
        self.orders = {}
        self.orders_symbol = {}

    @property
    def active_orders(self):
        """return all active orders
        """
        return self.orders

    def send_order(self, order_id, symbol, price, size, direction, open_close, *args, **kwargs):
        """record orders sent order

        Parameters
        ----------
        order_id : int
        symbol : str
        price : float
        size : int
        direction : int
        open_close : int

        Returns
        -------

        """
        self.orders[order_id] = self.Order(
            order_id=order_id,
            symbol=symbol,
            volume=size,
            price=price,
            direction=direction,
            open_close=open_close,
            investor_type=kwargs.get('investor_type', InvestorType.SPECULATOR),
            order_type=kwargs.get('order_type', OrderType.LIMIT),
            time_in_force=kwargs.get('time_in_force', TIF.DAY)
        )

    def cancel_order(self, org_ord_id):
        """record cancelled order
        """
        self.orders[org_ord_id].pending_cancel = True

    def on_response(self, response_type, response):
        """update order status at each response

        Parameters
        ----------
        response_type : int
        response : response

        Returns
        -------

        """
        # calculate pos
        if response.status in (OrderStatus.SUCCEED.value, OrderStatus.PARTED.value) and response.exe_volume == 0:
            return

        order = self.orders[response.order_id]
        order.update(response_type, response)

        if order.status != OrderStatus.INIT.value and response.status == OrderStatus.ENTRUSTED.value:
            # If already entrusted, no need to call update_order_list()
            pass
        else:
            order.status = response.status

        # delete order from dict once finished
        if response.status == OrderStatus.SUCCEED.value and order.last_qty > 0:
            self.orders.pop(response.order_id)
        elif response.status == OrderStatus.CANCELED.value:
            self.orders.pop(response.order_id)
        elif response.status in (OrderStatus.REJECTED.value,
                                 OrderStatus.INTERREJECTED.value, OrderStatus.CANCEL_REJECTED.value):
            if self.orders[response.order_id].pending_cancel is True:
                self.orders[response.order_id].pending_cancel = False
            else:
                self.orders.pop(response.order_id)

        # self.orders_symbol = {}
        # for key, value in self.orders.items():
        #     if value.symbol == symbol:
        #         self.orders_symbol[key] = self.orders[key]

    def on_book_order_management(self, context, symbol, bid_price_1, ask_price_1, order_position):
        if len(self.orders) > 0:
            for key, value in self.orders.items():
                if (value.symbol == symbol):
                    current_target_price = self.calculate_order_price(symbol, bid_price_1, ask_price_1, value.direction, order_position)
                    # context.logger.info('Order: {0}, current_target_price: {1}'.format(value.order_id, current_target_price - value.price))
                    if value.direction == Direction.BUY.value and abs(current_target_price - value.price) >= abs(order_position[symbol].Order_Type_Tick_Price_Constraint * order_position[symbol].Order_Tick_Size) and current_target_price > value.price:
                        value.pending_cancel = True
                        self.cancel_order(value.order_id)
                        return value.order_id
                    if value.direction == Direction.SELL.value and abs(value.price - current_target_price) >= abs(order_position[symbol].Order_Type_Tick_Price_Constraint * order_position[symbol].Order_Tick_Size) and current_target_price < value.price:
                        value.pending_cancel = True
                        self.cancel_order(value.order_id)
                        return value.order_id
                else:
                    return -999999
        return -999999



    def cancel_all_order(self, context):
        if len(self.orders) > 0:
            for key, value in self.orders.items():
                self.cancel_order(value.order_id)
                return value.order_id
                break
        else:
            return -999999





    def calculate_order_price(self, symbol, bid_price_1, ask_price_1, direction, order_position):
        order_position_symbol = order_position[symbol]
        if direction == Direction.BUY.value:
            if order_position_symbol.Order_Type_Position > 0:
                return ask_price_1 + order_position_symbol.Order_Type_Tick_Jump * order_position_symbol.Order_Tick_Size
            elif order_position_symbol.Order_Type_Position < 0:
                return bid_price_1 + order_position_symbol.Order_Type_Tick_Jump * order_position_symbol.Order_Tick_Size
        if direction == Direction.SELL.value:
            if order_position_symbol.Order_Type_Position > 0:
                return bid_price_1 - order_position_symbol.Order_Type_Tick_Jump * order_position_symbol.Order_Tick_Size
            elif order_position_symbol.Order_Type_Position < 0:
                return ask_price_1 - order_position_symbol.Order_Type_Tick_Jump * order_position_symbol.Order_Tick_Size

