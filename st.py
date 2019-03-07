# encoding: utf-8
"""
This is a minimal working version of sample strategy
"""

from my.sdp.api import (Order, Logger, Direction, OpenClose, OrderStatus, OrderError)

def on_init(context, config_type, config):
    """Start of trading session

    Parameters
    ----------
    context : object
        An global object for users to carry variables
        across functions. Contains private attributes critical
        for sending orders, attributes starting with "_" should
        not be overwritten.

    config_type : {0}
        0 for default configuration type

    config: object
        Refer to https://www.mycapital.net/support/wiki.html for detailed
        description.

    """
    print(repr(config))
    context.order = Order(context, config)
    context.logger = Logger(context, config)
    # for simple position management
    context.pos_dict = {}
    for cont in config.contracts:
        context.pos_dict[cont.symbol] = {
            "long_volume": cont.today_pos["long_volume"],
            "short_volume": cont.today_pos["short_volume"]
            }
    context.long_position = lambda x: context.pos_dict[x]["long_volume"]
    context.short_position = lambda x: context.pos_dict[x]["short_volume"]

    context.ORDER_SENT_FLAG = False


def on_book(context, quote_type, quote):
    """
    Receiving tick data and do computations

    Parameters
    ----------
    context : object
        Same as `context` field in on_init

    quote_type : {0, 1, 3, 4, 5}
        type of quote

    quote : object
        Refer to https://www.mycapital.net/support/wiki.html for detailed
        description.
        - futures quote <=> 0
        - stock quote <=> 1
        - bar_quote <=> 3
        - coin_quote <=> 4
        - forex_quote <=> 5

    """
    print("on_book")
    if context.long_position(quote.symbol) > 0 and not context.ORDER_SENT_FLAG:
        return_code = context.order.send_single_order(
            quote.symbol, quote.bp_array[0], 5, Direction.SELL, OpenClose.CLOSE
        )
        # if send order failed
        if return_code < 0:
            context.logger.err("{} {} {} {}@{} ret:{}".format(
                Direction.SELL, OpenClose.CLOSE, quote.symbol, 5, quote.bp_array[0], OrderError(return_code).name
            ))
        context.ORDER_SENT_FLAG = True
    elif 90000000 < quote.int_time < 93000000 and not context.ORDER_SENT_FLAG:
        return_code = context.order.send_single_order(
            quote.symbol, quote.ap_array[0], 5, Direction.BUY, OpenClose.OPEN
            )
        # if send order failed
        if return_code < 0:
            context.logger.err("{} {} {} {}@{} ret:{}".format(
                Direction.BUY, OpenClose.OPEN, quote.symbol, 5, quote.ap_array[0], OrderError(return_code).name
            ))
        context.ORDER_SENT_FLAG = True
    else:
        pass


def on_response(context, response_type, response):
    """
    Receiving information on trade results

    Parameters
    ----------
    context : object
        Same as `context` field in on_init

    response_type: {0}
        0 for default response type

    response: object
        Refer to https://www.mycapital.net/support/wiki.html for detailed
        description.

    """
    if response.status in (OrderStatus.SUCCEED.value, OrderStatus.PARTED.value) and response_type == 0:
        if response.exe_volume == 0:
            return
        if response.direction == Direction.BUY.value:
            if response.open_close == OpenClose.OPEN.value:
                context.pos_dict[response.symbol]['long_volume'] += response.exe_volume
            elif response.open_close in (OpenClose.CLOSE.value, OpenClose.CLOSE_YES.value):
                context.pos_dict[response.symbol]['short_volume'] -= response.exe_volume
        elif response.direction == Direction.SELL.value:
            if response.open_close == OpenClose.OPEN.value:
                context.pos_dict[response.symbol]['short_volume'] += response.exe_volume
            elif response.open_close in (OpenClose.CLOSE.value, OpenClose.CLOSE_YES.value):
                context.pos_dict[response.symbol]['long_volume'] -= response.exe_volume


def on_timer(context, data_type, data):
    """
    A Timer function with preset timer interval.

    Parameters
    ----------
    context : object
        Same as `context` field in on_init

    data_type: int
        Currently not in use.

    data : object
        Customized data structure for future use.(currently not in use)

    """
    pass


def on_session_finish(context):
    """
    Call at the end of each trading session, clear all variables

    Parameters
    ----------
    context : object
        Same as `context` field in on_init

    """
    pass


if __name__ == "__main__":
    pass
