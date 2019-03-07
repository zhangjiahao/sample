from datetime import datetime

import numpy
import pandas as pandas
from my.sdp.api import (Order, Logger, Direction, OrderStatus)
import os
from algorithm import ExecutionAlgorithm
from order import OrdMgr
from position import PosMgrBase

parameter_bar_length = 100

def month_price(first_half_month_flag, primary_contract_price,
                secondary_contract_price, thirdary_contract_price, current_date_int):
    if first_half_month_flag is True:
        return (int((primary_contract_price + ((current_date_int + 15) / 30) *
                     (secondary_contract_price - primary_contract_price)) / 10)) * 10
    else:
        return (int((secondary_contract_price + ((current_date_int - 15) / 30) *
                     (thirdary_contract_price - secondary_contract_price)) / 10)) * 10


def month_price_adding(current_price, primary_contract_price, secondary_contract_price):
    return current_price + (secondary_contract_price - primary_contract_price) * 3


def validating_date(input_year, input_month, input_day):
    try:
        if datetime(input_year, input_month, input_day):
            return True
    except:
        return False


def validating_weekday(input_year, input_month, input_day):
    if datetime(input_year, input_month, input_day).weekday() < 5:
        return True
    else:
        return False


def array_date_recursive_validdate(input_year, input_month, input_day):
    if validating_date(input_year, input_month, input_day) is False:
        input_day = input_day - 1
        return array_date_recursive_validdate(input_year, input_month, input_day)
    else:
        return [input_year, input_month, input_day]


def array_date_recursive_working_date(input_year, input_month, input_day):
    if validating_weekday(input_year, input_month, input_day) is False:
        input_day = input_day - 1
        return array_date_recursive_working_date(input_year, input_month, input_day)
    else:
        return [input_year, input_month, input_day]


def validated_working_date(input_year, input_month, input_day):
    valid_date = array_date_recursive_validdate(input_year, input_month, input_day)
    valid_working_date = array_date_recursive_working_date(valid_date[0], valid_date[1], valid_date[2])
    return valid_working_date


def array_date_add_months(input_year, input_month, input_day, input_monthsamount):
    year = input_year
    month = input_month
    day = input_day
    if input_month + input_monthsamount > 12:
        year = input_year + 1
        month = input_month + input_monthsamount - 12
        return [year, month, day]
    else:
        return [year, month, day]


def array_year_month_add_months(input_year, input_month, input_monthsamount):
    year = input_year
    month = input_month
    if input_month + input_monthsamount > 12:
        year = input_year + 1
        month = input_month + input_monthsamount - 12
        return [year, month]
    else:
        return [year, month + input_monthsamount]


def array_date_from_trading_date(trading_date):
    return [int(str(trading_date)[0:-4]), int(str(trading_date)[4:-2]), int(str(trading_date)[6:])]


def trading_date_from_array(year, month, day):
    return year * 10000 + month * 100 + day


def trading_month_from_array(year, month):
    return year * 100 + month


def return_year(trading_date):
    return int(str(trading_date)[0:-4])


def return_month(trading_date):
    return int(str(trading_date)[4:-2])


def return_day(trading_date):
    return int(str(trading_date)[6:])


def double_digit(number):
    if number < 10:
        return str("0" + str(number))
    else:
        return str(number)


def triple_digit(number):
    if number < 10:
        return str("0" + "0" + str(number))
    elif number < 100:
        return str("0" + str(number))
    else:
        return str(number)


def kdb_date(input_date, input_time):
    m_year = str(input_date)[0:-4]
    m_month = str(input_date)[4:-2]
    m_day = str(input_date)[6:]
    m_hour = double_digit(int(input_time / 10000000))
    m_minute = double_digit(int((input_time - int(m_hour) * 10000000) / 100000))
    m_second = double_digit(int((input_time - int(m_hour) * 10000000 - int(m_minute) * 100000) / 1000))
    m_millisecond = triple_digit(int(input_time % 1000))
    return m_year + "." + m_month + "." + m_day + "D" + m_hour + ":" + m_minute + ":" + m_second + "." + m_millisecond


def arbitrage_price(price_china, price_abroad, price_currency):
    return price_abroad * price_currency - price_china * 0.85


def calculate_order_price(symbol, bid_price_1, ask_price_1, direction, order_position):
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


def quantile_ladder_list_builder(quantile_ladder_list, amount_multiple):
    ladder_start_point = 0.0
    ladder_distance_size = 0.05
    exit_distance = 0.4
    quantile_ladder_list.append(QuantileLadder("BUY", ladder_start_point + ladder_distance_size * 1, ladder_start_point + ladder_distance_size * 1 + exit_distance, 1 * amount_multiple))
    quantile_ladder_list.append(QuantileLadder("BUY", ladder_start_point + ladder_distance_size * 2, ladder_start_point + ladder_distance_size * 2 + exit_distance, 1 * amount_multiple))
    quantile_ladder_list.append(QuantileLadder("BUY", ladder_start_point + ladder_distance_size * 3, ladder_start_point + ladder_distance_size * 3 + exit_distance, 1 * amount_multiple))
    quantile_ladder_list.append(QuantileLadder("BUY", ladder_start_point + ladder_distance_size * 4, ladder_start_point + ladder_distance_size * 4 + exit_distance, 1 * amount_multiple))
    quantile_ladder_list.append(QuantileLadder("SELL", 1 - ladder_start_point - ladder_distance_size * 4, 1 - ladder_start_point - ladder_distance_size * 4 - exit_distance, -1 * amount_multiple))
    quantile_ladder_list.append(QuantileLadder("SELL", 1 - ladder_start_point - ladder_distance_size * 3, 1 - ladder_start_point - ladder_distance_size * 3  - exit_distance, -1 * amount_multiple))
    quantile_ladder_list.append(QuantileLadder("SELL", 1 - ladder_start_point - ladder_distance_size * 2, 1 - ladder_start_point - ladder_distance_size * 2  - exit_distance, -1 * amount_multiple))
    quantile_ladder_list.append(QuantileLadder("SELL", 1 - ladder_start_point - ladder_distance_size * 1, 1 - ladder_start_point - ladder_distance_size * 1  - exit_distance, -1 * amount_multiple))


def valid_quote(quote):
    if quote.bp_array[0] > 0 and quote.ap_array[0] > 0:
        return True
    else:
        return False


def market_open_flag(exchange, time):
    if exchange == "SHFE":
        if (((time > 90000000) and (time < 113000000)) or ((time > 101500000) and (time <= 103000000)) or
                ((time > 133000000) and (time <= 150000000)) or ((time > 210000000) and (time < 250000000))):
            return True


def data_frame_quantile_cut(data_output, lowest_quantile, highest_quantile):
    data_output_cut = data_output[
        data_output.product_arbitrage_price > data_output.product_arbitrage_price.quantile(lowest_quantile)]
    data_output_cut = data_output_cut[
        data_output_cut.product_arbitrage_price < data_output.product_arbitrage_price.quantile(highest_quantile)]
    return data_output_cut


def update_quantile_ladder_list(quantile_ladder_list, data_output_cut):
    calculated_max_buy_price = -999999
    calculated_min_sell_price = 999999
    for ladder in quantile_ladder_list:
        if ladder.direction == "BUY":
            ladder.entry_price = data_output_cut.product_arbitrage_price.quantile(
                ladder.entry_quantile)
            ladder.exit_price = data_output_cut.product_arbitrage_price.quantile(
                ladder.exit_quantile)
            if ladder.entry_price > calculated_max_buy_price:
                calculated_max_buy_price = ladder.entry_price
        if ladder.direction == "SELL":
            ladder.entry_price = data_output_cut.product_arbitrage_price.quantile(
                ladder.entry_quantile)
            ladder.exit_price = data_output_cut.product_arbitrage_price.quantile(
                ladder.exit_quantile)
            if ladder.entry_price < calculated_min_sell_price:
                calculated_min_sell_price = ladder.entry_price
    return [calculated_max_buy_price, calculated_min_sell_price]


def update_target_active_leg_position(context, last_arbitrage_price,
                                      calculated_max_buy_price, calculated_min_sell_price):
        # context.logger.info('calculated_max_buy {0},  last_arbitrage_price {1}, calculated_min_sell is {2} '.format(calculated_max_buy_price, last_arbitrage_price, calculated_min_sell_price))
        # print('calculated_max_buy {0},  last_arbitrage_price {1}, calculated_min_sell is {2} '.format(calculated_max_buy_price, last_arbitrage_price, calculated_min_sell_price))
        if last_arbitrage_price < calculated_max_buy_price:
            for ladder in context.QuantileLadder_list:
                if ladder.direction == "BUY":
                    if last_arbitrage_price < ladder.entry_price:
                        context.calculated_Leg1_target_position = context.calculated_Leg1_target_position\
                                                                  + ladder.quantile_amount
                    else:
                        context.calculated_Leg1_target_position = context.calculated_Leg1_target_position + 0
            if context.calculated_Leg1_target_position < context.AccountPosition.Leg1Position:
                context.calculated_Leg1_target_position = context.AccountPosition.Leg1Position

        if last_arbitrage_price > calculated_min_sell_price:
            for ladder in context.QuantileLadder_list:
                if ladder.direction == "SELL":
                    if last_arbitrage_price > ladder.entry_price:
                        context.calculated_Leg1_target_position = context.calculated_Leg1_target_position\
                                                                  + ladder.quantile_amount
                    else:
                        context.calculated_Leg1_target_position = context.calculated_Leg1_target_position + 0
            if context.calculated_Leg1_target_position > context.AccountPosition.Leg1Position:
                context.calculated_Leg1_target_position = context.AccountPosition.Leg1Position

        if calculated_max_buy_price <= last_arbitrage_price <= calculated_min_sell_price:
            if context.AccountPosition.Leg1Position > 0:
                for ladder in context.QuantileLadder_list:
                    if ladder.direction == "BUY":
                        if last_arbitrage_price > ladder.exit_price:
                            context.calculated_Leg1_target_position = context.calculated_Leg1_target_position + 0
                        else:
                            context.calculated_Leg1_target_position = context.calculated_Leg1_target_position\
                                                                      + ladder.quantile_amount
                if context.calculated_Leg1_target_position > context.AccountPosition.Leg1Position:
                    context.calculated_Leg1_target_position = context.AccountPosition.Leg1Position

        if calculated_max_buy_price <= last_arbitrage_price <= calculated_min_sell_price:
            if context.AccountPosition.Leg1Position < 0:
                for ladder in context.QuantileLadder_list:
                    if ladder.direction == "SELL":
                        if last_arbitrage_price < ladder.exit_price:
                            context.calculated_Leg1_target_position = context.calculated_Leg1_target_position + 0
                        else:
                            context.calculated_Leg1_target_position = context.calculated_Leg1_target_position\
                                                                      + ladder.quantile_amount
                if context.calculated_Leg1_target_position < context.AccountPosition.Leg1Position:
                    context.calculated_Leg1_target_position = context.AccountPosition.Leg1Position
        context.TargetPosition.Leg1Position = context.calculated_Leg1_target_position
        context.TargetPosition.calculate_leg2_position()


class QuantileLadder:
    def __init__(self, direction, entry_quantile, exit_quantile, quantile_amount):
        self.direction = direction
        self.entry_quantile = entry_quantile
        self.entry_price = 999999
        self.exit_quantile = exit_quantile
        self.exit_price = 888888
        self.quantile_amount = quantile_amount


class TargetPosition:

    is_calculated_flag = False

    Leg1Symbol = ""
    Leg1BidPrice1 = 0.0
    Leg1AskPrice1 = 0.0
    Leg1Position = 0
    Leg1Direction = 0
    Leg2Symbol = ""
    Leg2BidPrice1 = 0.0
    Leg2AskPrice1 = 0.0
    Leg2Position = 0
    Leg2Direction = 0
    Leg3Symbol = ""
    Leg3BidPrice1 = 0.0
    Leg3AskPrice1 = 0.0
    Leg3Position = 0
    Leg3Direction = 0

    def __init__(self, name, leg1symbol, leg1bidprice1, leg1askprice1, leg1position, leg1direction, leg2symbol,
                 leg2bidprice1, leg2askprice1, leg2position, leg2direction, leg3symbol, leg3bidprice1, leg3askprice1,
                 leg3position, leg3direction):
        self.name = name
        self.Leg1Symbol = leg1symbol
        self.Leg1BidPrice1 = leg1bidprice1
        self.Leg1AskPrice1 = leg1askprice1
        self.Leg1Position = leg1position
        self.Leg1Direction = leg1direction
        self.Leg2Symbol = leg2symbol
        self.Leg2BidPrice1 = leg2bidprice1
        self.Leg2AskPrice1 = leg2askprice1
        self.Leg2Position = leg2position
        self.Leg2Direction = leg2direction
        self.Leg3Symbol = leg3symbol
        self.Leg3BidPrice1 = leg3bidprice1
        self.Leg3AskPrice1 = leg3askprice1
        self.Leg3Position = leg3position
        self.Leg3Direction = leg3direction

    def calculate_leg2_position(self):
        if self.Leg1Position > 0:
            if self.Leg1Position % 4 == 0:
                self.Leg2Position = (self.Leg1Position / 4) * 17 * self.Leg1Direction * self.Leg2Direction
            elif self.Leg1Position % 4 > 0:
                self.Leg2Position = (self.Leg1Position % 4) * 4 * self.Leg1Direction * self.Leg2Direction + (
                    int(self.Leg1Position / 4)) * 17 * self.Leg1Direction * self.Leg2Direction
        elif self.Leg1Position < 0:
            if abs(self.Leg1Position) % 4 == 0:
                self.Leg2Position = -1 * ((abs(self.Leg1Position) / 4) * 17 * self.Leg1Direction * self.Leg2Direction)
            elif abs(self.Leg1Position) % 4 > 0:
                self.Leg2Position = -1 * ((abs(self.Leg1Position) % 4) * 4 * self.Leg1Direction * self.Leg2Direction + (
                    int(abs(self.Leg1Position) / 4)) * 17 * self.Leg1Direction * self.Leg2Direction)
        elif self.Leg1Position == 0:
            self.Leg2Position = 0


class AccountPosition:

    is_calculated_flag = False

    Leg1Symbol = ""
    Leg1BidPrice1 = 0.0
    Leg1AskPrice1 = 0.0
    Leg1Position = 0
    Leg1Direction = 0
    Leg2Symbol = ""
    Leg2BidPrice1 = 0.0
    Leg2AskPrice1 = 0.0
    Leg2Position = 0
    Leg2TargetPosition = 0
    Leg2Direction = 0
    Leg3Symbol = ""
    Leg3BidPrice1 = 0.0
    Leg3AskPrice1 = 0.0
    Leg3Position = 0
    Leg3Direction = 0

    def __init__(self, name, leg1symbol, leg1bidprice1, leg1askprice1, leg1position, leg1direction, leg2symbol,
                 leg2bidprice1, leg2askprice1, leg2position, leg2direction, leg3symbol, leg3bidprice1, leg3askprice1,
                 leg3position, leg3direction):
        self.name = name
        self.Leg1Symbol = leg1symbol
        self.Leg1BidPrice1 = leg1bidprice1
        self.Leg1AskPrice1 = leg1askprice1
        self.Leg1Position = leg1position
        self.Leg1Direction = leg1direction
        self.Leg2Symbol = leg2symbol
        self.Leg2BidPrice1 = leg2bidprice1
        self.Leg2AskPrice1 = leg2askprice1
        self.Leg2Position = leg2position
        self.Leg2Direction = leg2direction
        self.Leg3Symbol = leg3symbol
        self.Leg3BidPrice1 = leg3bidprice1
        self.Leg3AskPrice1 = leg3askprice1
        self.Leg3Position = leg3position
        self.Leg3Direction = leg3direction

    def calculate_leg2_position_distance(self):
        self.Leg2TargetPosition = 0
        if self.Leg1Position % 4 == 0:
            self.Leg2TargetPosition = (self.Leg1Position / 4) * 17 * self.Leg1Direction * self.Leg2Direction
        elif self.Leg1Position > 0:
            self.Leg2TargetPosition = (self.Leg1Position % 4) * 4 * self.Leg1Direction * self.Leg2Direction + (
                int(self.Leg1Position / 4)) * 17 * self.Leg1Direction * self.Leg2Direction
        elif self.Leg1Position < 0:
            self.Leg2TargetPosition = ((abs(self.Leg1Position) % 4) * 4 * self.Leg1Direction * self.Leg2Direction + (
                int(abs(self.Leg1Position) / 4)) * 17 * self.Leg1Direction * self.Leg2Direction) * (-1)
        if self.Leg2TargetPosition != self.Leg2Position:
            return self.Leg2TargetPosition - self.Leg2Position
        else:
            return 0


class SymbolOrderType:
    Symbol = ""
    Order_Type_Position = 0
    Order_Type_Tick_Jump = 0
    Order_Type_Tick_Time_Constraint = 0
    Order_Type_Tick_Price_Constraint = 0
    Order_Type_Tick_Max_Amount = 0
    Order_Tick_Size = 0

    def __init__(self, symbol: object, order_type_position: object, order_type_tick_jump: object,
                 order_type_tick_time_contraint: object, order_type_tick_price_constraint: object,
                 order_type_tick_max_amount: object, order_tick_size: object) -> object:
        self.Symbol = symbol
        self.Order_Type_Position = order_type_position
        self.Order_Type_Tick_Jump = order_type_tick_jump
        self.Order_Type_Tick_Time_Constraint = order_type_tick_time_contraint
        self.Order_Type_Tick_Price_Constraint = order_type_tick_price_constraint
        self.Order_Type_Tick_Max_Amount = order_type_tick_max_amount
        self.Order_Tick_Size = order_tick_size


def on_init(context, config_type, config):
    context.logger = Logger(context, config)
    context.leg2_position_diff = 0
    context.QuantileLadder_list = []
    # amount_multiple = int(config.accounts[0].cash_available * config.accounts[0].exch_rate / 2800000)
    amount_multiple = 1
    context.logger.info('Cash_available {0},  Cash_asset {1}, Amount_multiple is {2}, exch_rate is {3}'.format(
        config.accounts[0].cash_available, config.accounts[0].cash_asset, amount_multiple,
        config.accounts[0].exch_rate))
    context.logger.info('Cash_available {0},  Cash_asset {1}, Amount_multiple is {2}, exch_rate is {3}'.format(
        config.accounts[1].cash_available, config.accounts[1].cash_asset, amount_multiple,
        config.accounts[1].exch_rate))
    quantile_ladder_list_builder(context.QuantileLadder_list, amount_multiple)
    context.head = ["Date", "context.product_china_bid", "context.product_china_ask", "context.product_abroad_bid",
                    "context.product_abroad_ask",
                    "product_currency_bid", "product_currency_ask", "product_arbitrage_price_bid",
                    "product_arbitrage_price_ask", "product_arbitrage_price"]
    context.output_file_string = config.output_file_path + "/ARB_CAD_V3T2_3L_Strategy_Data.csv"
    context.output_file_string_detail = "/home/rss/demo_strategy/EVFolder/ARB_CAD_V3T2_3L_Strategy_Data_Detail.csv"
    context.is_data_exist = os.path.exists(context.output_file_string)
    context.data_output = pandas.DataFrame(columns=context.head)
    context.data_output_detail = pandas.DataFrame(columns=context.head)
    context.data_output_cut = pandas.DataFrame(columns=context.head)
    if context.is_data_exist:
        context.data_output = pandas.read_csv(context.output_file_string)
    # context.logger.info('Length of Datas {0}'.format(len(context.data_output)))
    context.factor_head = ["product_china", "product_abroad", "product_currency_spot", "product_currency_future",
                           "last_full_position_time", "last_position_time", "FUL_POS_FLAG", "EMP_POS_FLAG",
                           "account_leg1position", "account_leg2position", "time_standard_exchange",
                           "millisecond_threshold",
                           "window_length"]
    context.input_factors_file = config.output_file_path + "/ARB_CAD_V3T2_3L_Strategy_Factor_ZN.csv"
    context.is_input_factor_exist = os.path.exists(context.input_factors_file)
    data_input_factor_original = [['pb', 'PB3M', 'USD.CNH', 'UC', 0, 0, False, False, 4, -17, 'SHFE', 100000, int(parameter_bar_length)]]
    context.data_input_factor = pandas.DataFrame(data_input_factor_original, columns=context.factor_head)
    context.product_china = context.data_input_factor.iloc[0]['product_china']
    context.product_abroad = context.data_input_factor.iloc[0]['product_abroad']
    context.product_currency_spot = context.data_input_factor.iloc[0]['product_currency_spot']
    context.product_currency_future = context.data_input_factor.iloc[0]['product_currency_future']
    context.data_input_factor.loc[0, 'last_position_time'] = context.data_input_factor.iloc[0]['last_position_time']
    context.FUL_POS_FLAG = context.data_input_factor.iloc[0]['FUL_POS_FLAG']
    context.account_leg1position = context.data_input_factor.iloc[0]['account_leg1position']
    context.account_leg2position = context.data_input_factor.iloc[0]['account_leg2position']
    context.time_standard_exchange = context.data_input_factor.iloc[0]['time_standard_exchange']
    context.millisecond_threshold = context.data_input_factor.iloc[0]['millisecond_threshold']
    context.window_length = context.data_input_factor.iloc[0]['window_length']
    context.bar_number = 0
    context.window_count = 9
    context.combined_data_arbitrage_price = numpy.zeros(shape=(context.window_length, context.window_count))
    context.trade_handler = ExecutionAlgorithm(context, config)
    context.config = config
    context.dic = {}
    context.market_quote_datetime_ready = 0
    context.date = ""
    context.time = ""
    # position manager
    context.posmgr = PosMgrBase()
    context.posmgr.init_position(config_type, config)
    ##############################
    #   Order Position Handler   #
    ##############################
    # context.order_dic = {}
    context.order_position = {}
    context.order = Order(context, config)
    context.ordmgr = OrdMgr()
    # context.order = SyncOrder(context, config
    context.pos_dict = {}
    context.symbol_exchange = {}
    for cont in config.contracts:
        context.pos_dict[cont.symbol] = {
            "today_long_volume": cont.today_pos["long_volume"],
            "today_short_volume": cont.today_pos["short_volume"],
            "yesterday_long_volume": cont.yesterday_pos["long_volume"],
            "yesterday_short_volume": cont.yesterday_pos["short_volume"]
        }
        context.symbol_exchange[cont.symbol] = cont
    context.long_position = lambda x: context.pos_dict[x]["long_volume"]
    context.short_position = lambda x: context.pos_dict[x]["short_volume"]
    context.ORDER_SENT_FLAG = False
    # contracts = config.contracts
    # for i in range(len(contracts)):
    #     context.logger.info('Yesterday_pos {0}, long: {1} short: {2}'.format(
    #         contracts[i].symbol, contracts[i].yesterday_pos['long_volume'],
    #           contracts[i].yesterday_pos['short_volume']))
    ##############################
    #   Order Position Handler   #
    ##############################
    context.trading_contract = {}
    context.first_half_month_flag = True
    context.prefix_contract_trading_change_date = 10
    context.prefix_contract_rollover_date_inside = 15
    context.prefix_contract_inside = context.product_china
    context.prefix_contract_UC = context.product_currency_future
    context.primary_contract_UC = ""
    context.secondary_contract_UC = ""
    context.primary_contract_inside = ""
    context.secondary_contract_inside = ""
    context.additional_spread_inside = ""
    context.primary_contract_inside = context.prefix_contract_inside + ((str(trading_month_from_array(
        array_year_month_add_months(return_year(context.config.trading_date),
                                    return_month(context.config.trading_date), 2)[0],
        array_year_month_add_months(return_year(context.config.trading_date),
                                    return_month(context.config.trading_date), 2)[1])))[2:])
    context.secondary_contract_inside = context.prefix_contract_inside + ((str(trading_month_from_array(
        array_year_month_add_months(return_year(context.config.trading_date),
                                    return_month(context.config.trading_date), 3)[0],
        array_year_month_add_months(return_year(context.config.trading_date),
                                    return_month(context.config.trading_date), 3)[1])))[2:])
    context.thirdary_contract_inside = context.prefix_contract_inside + ((str(trading_month_from_array(
        array_year_month_add_months(return_year(context.config.trading_date),
                                    return_month(context.config.trading_date), 4)[0],
        array_year_month_add_months(return_year(context.config.trading_date),
                                    return_month(context.config.trading_date), 4)[1])))[2:])
    context.primary_contract_UC = context.prefix_contract_UC + ((str(trading_month_from_array(
        array_year_month_add_months(return_year(context.config.trading_date),
                                    return_month(context.config.trading_date), 1)[0],
        array_year_month_add_months(return_year(context.config.trading_date),
                                    return_month(context.config.trading_date), 1)[1])))[2:])
    context.secondary_contract_UC = context.prefix_contract_UC + ((str(trading_month_from_array(
        array_year_month_add_months(return_year(context.config.trading_date),
                                    return_month(context.config.trading_date), 2)[0],
        array_year_month_add_months(return_year(context.config.trading_date),
                                    return_month(context.config.trading_date), 2)[1])))[2:])
    context.order_position[context.product_abroad] = SymbolOrderType(context.product_abroad, -1, 0, 999999, 1, 5, 0.5)
    context.order_position[context.primary_contract_inside] = SymbolOrderType(context.product_abroad, -1, 0, 999999, 2,
                                                                              99, 5)
    context.order_position[context.secondary_contract_inside] = SymbolOrderType(context.product_abroad, -1, 0, 999999,
                                                                                2, 99, 5)
    if context.config.trading_date % 100 < context.prefix_contract_rollover_date_inside:
        context.first_half_month_flag = True
    else:
        context.first_half_month_flag = False
    if context.config.trading_date % 100 < context.prefix_contract_trading_change_date:
        context.TargetPosition = TargetPosition("TargetPosition", context.product_abroad, 0.0, 0.0, 0, -1,
                                                context.primary_contract_inside, 0.0, 0.0, 0, 1,
                                                context.primary_contract_UC, 0.0, 0.0, 0, -1)
        context.AccountPosition = AccountPosition("AccountPosition", context.product_abroad, 0.0, 0.0,
                                                  context.posmgr.get_net_position(context.product_abroad), -1,
                                                  context.primary_contract_inside, 0.0, 0.0,
                                                  context.posmgr.get_net_position(context.primary_contract_inside), 1,
                                                  context.primary_contract_UC, 0.0, 0.0, 0, -1)
    else:
        context.TargetPosition = TargetPosition("TargetPosition", context.product_abroad, 0.0, 0.0, 0, -1,
                                                context.secondary_contract_inside, 0.0, 0.0, 0, 1,
                                                context.primary_contract_UC, 0.0, 0.0, 0, -1)
        context.AccountPosition = AccountPosition("AccountPosition", context.product_abroad, 0.0, 0.0,
                                                  context.posmgr.get_net_position(context.product_abroad), -1,
                                                  context.secondary_contract_inside, 0.0, 0.0,
                                                  context.posmgr.get_net_position(context.secondary_contract_inside), 1,
                                                  context.primary_contract_UC, 0.0, 0.0, 0, -1)
    context.TargetPosition.calculate_leg2_position()
    context.calculated_Leg1_target_position = 0
    context.valid_symbol_tuple = (
        context.primary_contract_UC, context.secondary_contract_UC, context.product_currency_spot,
        context.primary_contract_inside, context.secondary_contract_inside,
        context.thirdary_contract_inside, context.product_abroad)
    context.valid_symbol_tuple_matter = (
        context.primary_contract_inside, context.secondary_contract_inside, context.product_abroad)
    context.CANCEL_ALL_FLAG = False
    context.execution_count = 0
    context.logger.info('Point of Start: {0}, count is :{1}'.format(datetime.now(), context.execution_count))
    print('Point of Start: {0}, count is : {1}, parameter_bar_length is : {2}'.format(datetime.now(), context.execution_count, parameter_bar_length))


def on_book(context, quote_type, quote):
    if quote.bp_array[0] > 0.1 and quote.ap_array[0] > 0.1:
        if quote.symbol == context.primary_contract_UC:
            context.dic[quote.symbol] = [quote.bp_array[0], quote.ap_array[0]]
        if quote.symbol == context.secondary_contract_UC:
            context.dic[quote.symbol] = [quote.bp_array[0], quote.ap_array[0]]
        if quote.symbol == context.product_currency_spot:
            context.dic[quote.symbol] = [quote.bp_array[0], quote.ap_array[0]]
        if quote.symbol == context.primary_contract_inside:
            context.dic[quote.symbol] = [quote.bp_array[0], quote.ap_array[0]]
        if quote.symbol == context.secondary_contract_inside:
            context.dic[quote.symbol] = [quote.bp_array[0], quote.ap_array[0]]
        if quote.symbol == context.thirdary_contract_inside:
            context.dic[quote.symbol] = [quote.bp_array[0], quote.ap_array[0]]
        if quote.symbol == context.product_abroad:
            context.dic[quote.symbol] = [quote.bp_array[0], quote.ap_array[0]]
        context.dic['USD.CNH'] = [6.4999, 6.5000]
        if quote.symbol in context.valid_symbol_tuple_matter:
            context.execution_count = context.execution_count + 1
            context.posmgr.update_last_px(quote_type, quote)
            context.trade_handler.on_book(quote_type, quote)
            ###############################################
            #        Maintain Order                       #
            ###############################################
            if quote.symbol in context.dic:
                cancelling_order_id = context.ordmgr.on_book_order_management(context, quote.symbol,
                                                                              context.dic[quote.symbol][0],
                                                                              context.dic[quote.symbol][1],
                                                                              context.order_position)
                if cancelling_order_id > 0:
                    context.order.cancel_single_order(cancelling_order_id)
            if quote.symbol.startswith(context.product_china):
                context.date, context.time = str(context.config.trading_date), int(quote.int_time)
                context.date_time = context.config.trading_date * 1000000000 + quote.int_time
                context.market_quote_datetime_ready = 1
            if quote.int_time >= 245930000:
                cancel_all_order_id = context.ordmgr.cancel_all_order(context)
                if cancel_all_order_id > 0:
                    context.order.cancel_single_order(cancel_all_order_id)
                context.CANCEL_ALL_FLAG = True
            if context.market_quote_datetime_ready == 1 and quote.symbol in context.valid_symbol_tuple and\
                    market_open_flag(context.time_standard_exchange, context.time) and valid_quote(quote) and\
                    context.CANCEL_ALL_FLAG is False:
                context.dic[quote.symbol] = [quote.bp_array[0], quote.ap_array[0]]
                if context.posmgr.get_net_position(
                        context.primary_contract_inside) != 0 and quote.symbol == context.primary_contract_inside \
                        and context.config.trading_date % 100 >= context.prefix_contract_trading_change_date and len(
                        context.ordmgr.active_orders) == 0:
                    ###############################################
                    #        Change The Main Contract             #
                    ###############################################
                    print(context.primary_contract_inside)
                    order_symbol = context.primary_contract_inside
                    order_amount = context.posmgr.get_net_position(context.primary_contract_inside)
                    # order_price = 0.0
                    order_symbol_bid = quote.bp_array[0]
                    order_symbol_ask = quote.ap_array[0]
                    if order_amount > 0:
                        order_price = calculate_order_price(order_symbol, order_symbol_bid,
                                                            order_symbol_ask, Direction.SELL, context.order_position)
                        order_info = context.posmgr.get_open_close(order_symbol, order_amount, Direction.SELL,
                                                                   "YES_TOD_SHFE_FLAG")
                        order_amount = order_info[0]
                        order_open_close = order_info[1]
                        _id = context.order.send_single_order(order_symbol, order_price,
                                                              order_amount, Direction.SELL, order_open_close)
                        context.ordmgr.send_order(_id, order_amount, order_price,
                                                  order_amount, Direction.SELL, order_open_close)
                    if order_amount < 0:
                        order_price = calculate_order_price(order_symbol, order_symbol_bid,
                                                            order_symbol_ask, Direction.BUY, context.order_position)
                        order_info = context.posmgr.get_open_close(order_symbol, abs(order_amount), Direction.BUY,
                                                                   "YES_TOD_SHFE_FLAG")
                        order_amount = abs(order_info[0])
                        order_open_close = order_info[1]
                        _id = context.order.send_single_order(order_symbol, order_price,
                                                              order_amount, Direction.BUY, order_open_close)
                        context.ordmgr.send_order(_id, order_symbol, order_price,
                                                  order_amount, Direction.BUY, order_open_close)

                if len(context.dic.keys()) >= len(context.valid_symbol_tuple):
                    ###############################################
                    #        Insert Manipulated Data              #
                    ###############################################
                    context.dic[context.product_china] = [
                        month_price(context.first_half_month_flag, context.dic[context.primary_contract_inside][0],
                                    context.dic[context.secondary_contract_inside][0],
                                    context.dic[context.thirdary_contract_inside][0],
                                    context.config.trading_date % 100),
                        month_price(context.first_half_month_flag, context.dic[context.primary_contract_inside][1],
                                    context.dic[context.secondary_contract_inside][1],
                                    context.dic[context.thirdary_contract_inside][1],
                                    context.config.trading_date % 100)]
                    context.dic[context.product_currency_future] = [
                        month_price_adding(context.dic[context.product_currency_spot][0], (
                                    context.dic[context.primary_contract_UC][0] +
                                    context.dic[context.primary_contract_UC][1]) / 2, (
                                                       context.dic[context.secondary_contract_UC][0] +
                                                       context.dic[context.secondary_contract_UC][1]) / 2),
                        month_price_adding(context.dic[context.product_currency_spot][1],
                                           (context.dic[context.primary_contract_UC][0] +
                                            context.dic[context.primary_contract_UC][1]) / 2,
                                           (context.dic[context.secondary_contract_UC][0] +
                                            context.dic[context.secondary_contract_UC][1]) / 2)]
                    middle_arbitrage_price = arbitrage_price(
                        (context.dic[context.product_china][0] + context.dic[context.product_china][1]) / 2,
                        (context.dic[context.product_abroad][0] + context.dic[context.product_abroad][1]) / 2,
                        (context.dic[context.product_currency_future][0] + context.dic[context.product_currency_future][
                            1]) / 2)
                    temp_data_output = [(kdb_date(context.config.trading_date, context.time),
                                         context.dic[context.product_china][0], context.dic[context.product_china][1],
                                         context.dic[context.product_abroad][0], context.dic[context.product_abroad][1],
                                         context.dic[context.product_currency_future][0],
                                         context.dic[context.product_currency_future][1],
                                         arbitrage_price(context.dic[context.product_china][1],
                                                         context.dic[context.product_abroad][0],
                                                         context.dic[context.product_currency_future][0]),
                                         arbitrage_price(context.dic[context.product_china][0],
                                                         context.dic[context.product_abroad][1],
                                                         context.dic[context.product_currency_future][1]),
                                         middle_arbitrage_price)]
                    # context.logger.info(
                    #     'time {0},  china_leg1_bid {1}, china_leg1_ask {2}, abroad_leg2_bid {3}, abroad_leg2_bid {4},
                    #  currency_leg3_bid {5}, currency_leg3_bid {6}, '.format(kdb_date(context.config.trading_date,
                    # context.time),
                    #                      context.dic[context.primary_contract_inside][0],
                    # context.dic[context.product_china][1],
                    #                      context.dic[context.product_abroad][0],
                    # context.dic[context.product_abroad][1],
                    # context.dic[context.product_currency_future][0],
                    # context.dic[context.product_currency_future][1]))
                    # context.logger.info('time {0},  china_primary_bid {1}, china_primary_ask {2},
                    # china_primary_bid {3}, china_primary_ask {4}, china_primary_bid {5}, china_primary_ask {6},
                    #  '.format(
                    #         kdb_date(context.config.trading_date, context.time),
                    #         context.dic[context.primary_contract_inside][0],
                    #         context.dic[context.primary_contract_inside][1],
                    #         context.dic[context.secondary_contract_inside][0],
                    #         context.dic[context.secondary_contract_inside][1],
                    #         context.dic[context.thirdary_contract_inside][0],
                    #         context.dic[context.thirdary_contract_inside][1]))
                    # temp_data_output_df = pandas.DataFrame.from_records(temp_data_output, columns=context.head)
                    # context.data_output_detail = context.data_output_detail.append(temp_data_output_df,
                    #  ignore_index=False)

                    last_arbitrage_price = middle_arbitrage_price
                    ###############################################
                    #        Update Quantile                      #
                    ###############################################
                    if (context.time < 145900000) or ((context.time > 200000000) and (context.time < 245900000)):
                        current_bar_number = int(context.time / context.millisecond_threshold)
                        if current_bar_number > context.bar_number:
                            # last_position_time_copy = context.data_input_factor.iloc[0]['last_position_time']
                            context.data_input_factor.loc[0, 'last_position_time'] = \
                                context.data_input_factor.loc[0]['last_position_time'] + 1
                            context.bar_number = current_bar_number
                            temp_data_output_df = pandas.DataFrame.from_records(temp_data_output, columns=context.head)
                            context.data_output = context.data_output.append(temp_data_output_df, ignore_index=False)
                            if len(context.data_output) > context.window_length:
                                drop_rate = len(context.data_output) - context.window_length
                                context.data_output = context.data_output.iloc[drop_rate:]
                    elif (context.time > 145900000) and (context.time < 150000000):
                        current_bar_number = int((context.time + 100000) / context.millisecond_threshold)
                        if current_bar_number > context.bar_number:
                            # last_position_time_copy = context.data_input_factor.iloc[0]['last_position_time']
                            context.data_input_factor.loc[0, 'last_position_time'] = context.data_input_factor.loc[0][
                                                                                         'last_position_time'] + 1
                            context.bar_number = current_bar_number
                            temp_data_output_df = pandas.DataFrame.from_records(temp_data_output, columns=context.head)
                            context.data_output = context.data_output.append(temp_data_output_df, ignore_index=False)
                            if len(context.data_output) > context.window_length:
                                drop_rate = len(context.data_output) - context.window_length
                                context.data_output = context.data_output.iloc[drop_rate:]
                    elif (context.time > 245900000) and (context.time < 250000000):
                        current_bar_number = int((context.time + 100000) / context.millisecond_threshold)
                        if current_bar_number > context.bar_number:
                            # last_position_time_copy = context.data_input_factor.iloc[0]['last_position_time']
                            context.data_input_factor.loc[0, 'last_position_time'] = context.data_input_factor.loc[0][
                                                                                         'last_position_time'] + 1
                            context.bar_number = current_bar_number
                            temp_data_output_df = pandas.DataFrame.from_records(temp_data_output, columns=context.head)
                            context.data_output = context.data_output.append(temp_data_output_df, ignore_index=False)
                            if len(context.data_output) > context.window_length:
                                drop_rate = len(context.data_output) - context.window_length
                                context.data_output = context.data_output.iloc[drop_rate:]
                    ###############################################
                    #        Check Leg2 Condition                 #
                    ###############################################
                    context.leg2_position_diff = context.AccountPosition.calculate_leg2_position_distance()
                    ###############################################
                    #        Balance The Active Leg               #
                    ###############################################
                    # if quote.symbol in (context.product_abroad, context.primary_contract_inside,
                    # context.secondary_contract_inside) and len(context.data_output) == context.window_length
                    #  and context.leg2_position_diff == 0:
                    if len(context.data_output) == context.window_length and context.leg2_position_diff == 0:
                        context.data_output_cut = data_frame_quantile_cut(context.data_output, 0.05, 0.95)
                        context.calculated_Leg1_target_position = 0
                        quantile_ladder_buy_sell_price = update_quantile_ladder_list(context.QuantileLadder_list,
                                                                                     context.data_output_cut)
                        calculated_max_buy_price = quantile_ladder_buy_sell_price[0]
                        calculated_min_sell_price = quantile_ladder_buy_sell_price[1]
                        if context.data_input_factor.loc[0, 'FUL_POS_FLAG'] == True and context.data_input_factor.loc[0, 'EMP_POS_FLAG'] == True:
                            if context.AccountPosition.Leg1Position == 0 and context.AccountPosition.Leg2Position == 0:
                                context.AccountPosition.Leg1Position = context.data_input_factor.loc[0, 'account_leg1position']
                                context.AccountPosition.Leg2Position = context.data_input_factor.loc[0, 'account_leg2position']
                                update_target_active_leg_position(context, last_arbitrage_price,
                                                                  calculated_max_buy_price, calculated_min_sell_price)
                                if context.TargetPosition.Leg1Position == 0:
                                    context.data_input_factor.loc[0, 'FUL_POS_FLAG'] = False
                                    context.data_input_factor.loc[0, 'EMP_POS_FLAG'] = False
                                    context.data_input_factor.loc[0, 'last_full_position_time'] = context.data_input_factor.loc[0, 'last_position_time']
                                context.TargetPosition.Leg1Position = 0
                                context.TargetPosition.Leg2Position = 0
                                context.AccountPosition.Leg1Position = 0
                                context.AccountPosition.Leg2Position = 0
                        elif context.data_input_factor.loc[0, 'FUL_POS_FLAG'] == True and context.data_input_factor.loc[0, 'EMP_POS_FLAG'] == False:
                            if abs(context.AccountPosition.Leg1Position) != 4:
                                context.data_input_factor.loc[0, 'FUL_POS_FLAG'] = False
                                context.data_input_factor.loc[0, 'last_full_position_time'] = context.data_input_factor.loc[0, 'last_position_time']
                            update_target_active_leg_position(context, last_arbitrage_price,
                                                              calculated_max_buy_price,
                                                              calculated_min_sell_price)
                        elif context.data_input_factor.loc[0, 'FUL_POS_FLAG'] == False and context.data_input_factor.loc[0, 'EMP_POS_FLAG'] == False:
                            context.data_input_factor.loc[0, 'last_full_position_time'] = context.data_input_factor.loc[0, 'last_position_time']
                            update_target_active_leg_position(context, last_arbitrage_price,
                                                                  calculated_max_buy_price, calculated_min_sell_price)
                            if context.data_input_factor.iloc[0]['last_position_time'] -  context.data_input_factor.iloc[0]['last_full_position_time'] > 45 and \
                                    context.data_input_factor.loc[0, 'EMP_POS_FLAG'] is False:
                                context.data_input_factor.loc[0, 'EMP_POS_FLAG'] = True
                                context.TargetPosition.Leg1Position = 0
                                context.TargetPosition.Leg2Position = 0
                                context.data_input_factor.loc[
                                    0, 'account_leg1position'] = context.AccountPosition.Leg1Position
                                context.data_input_factor.loc[
                                    0, 'account_leg2position'] = context.AccountPosition.Leg2Position
                        # context.logger.info('Full position: {0}, last position: {1}'.
                        # format(context.data_input_factor.loc[0]['last_full_position_time'],
                        # context.data_input_factor.loc[0]['last_position_time']))
                        # context.logger.info(
                        #     'Length of Datas {0}  Leg2 Diff : {1}  Symbol: {2}, last_arb: {3}, max_buy: {4},
                        #         min_sell: {5}'.format(
                        #         len(context.data_output), context.leg2_position_diff,
                        #         quote.symbol, last_arbitrage_price,
                        #         calculated_max_buy_price, calculated_min_sell_price))
                        ###############################################
                        #        Placing Active Leg Order             #
                        ###############################################
                        order_symbol = context.TargetPosition.Leg1Symbol
                        order_amount = 1
                        # order_price = 0.0
                        order_symbol_bid = context.dic[context.TargetPosition.Leg1Symbol][0]
                        order_symbol_ask = context.dic[context.TargetPosition.Leg1Symbol][1]
                        if context.TargetPosition.Leg1Position != context.AccountPosition.Leg1Position and len(
                                context.ordmgr.active_orders) == 0:
                            if context.TargetPosition.Leg1Position - context.AccountPosition.Leg1Position > 0:
                                order_price = calculate_order_price(context.TargetPosition.Leg1Symbol,
                                                                    order_symbol_bid, order_symbol_ask, Direction.BUY,
                                                                    context.order_position)
                                order_info = context.posmgr.get_open_close(order_symbol, order_amount, Direction.BUY,
                                                                           "YES_TOD_FLAG")
                                order_amount = order_info[0]
                                order_open_close = order_info[1]
                                print(order_open_close)
                                _id = context.order.send_single_order(context.TargetPosition.Leg1Symbol,
                                                                      order_price, order_amount, Direction.BUY,
                                                                      order_open_close)
                                context.ordmgr.send_order(_id, context.TargetPosition.Leg1Symbol, order_price,
                                                          order_amount, Direction.BUY, order_open_close)
                            if context.TargetPosition.Leg1Position - context.AccountPosition.Leg1Position < 0:
                                order_price = calculate_order_price(context.TargetPosition.Leg1Symbol, order_symbol_bid,
                                                                    order_symbol_ask, Direction.SELL,
                                                                    context.order_position)
                                order_info = context.posmgr.get_open_close(order_symbol, order_amount, Direction.SELL,
                                                                            "YES_TOD_FLAG")
                                order_amount = order_info[0]
                                order_open_close = order_info[1]
                                print(order_open_close)
                                _id = context.order.send_single_order(context.TargetPosition.Leg1Symbol,
                                                                      order_price, order_amount, Direction.SELL,
                                                                      order_open_close)
                                context.ordmgr.send_order(_id, context.TargetPosition.Leg1Symbol,
                                                          order_price, order_amount, Direction.SELL, order_open_close)
                    ###############################################
                    #        Balance Passive Leg                  #
                    ###############################################
                    if quote.symbol in (context.product_abroad, context.primary_contract_inside,
                                        context.secondary_contract_inside) and (
                            context.leg2_position_diff != 0) and len(context.ordmgr.active_orders) == 0:
                        order_symbol = context.TargetPosition.Leg2Symbol
                        order_amount = abs(context.leg2_position_diff)
                        order_symbol_bid = context.dic[context.TargetPosition.Leg2Symbol][0]
                        order_symbol_ask = context.dic[context.TargetPosition.Leg2Symbol][1]
                        # context.logger.info('Leg2_position_diff: {0}'.format(context.leg2_position_diff))
                        if len(context.ordmgr.active_orders) == 0:
                            if context.leg2_position_diff > 0:
                                order_price = calculate_order_price(context.TargetPosition.Leg2Symbol, order_symbol_bid,
                                                                    order_symbol_ask, Direction.BUY,
                                                                    context.order_position)
                                order_info = context.posmgr.get_open_close(order_symbol, order_amount, Direction.BUY,
                                                                           "YES_TOD_SHFE_FLAG")
                                order_amount = order_info[0]
                                order_open_close = order_info[1]
                                if order_amount > 0:
                                    _id = context.order.send_single_order(context.TargetPosition.Leg2Symbol,
                                                                          order_price,
                                                                          order_amount, Direction.BUY, order_open_close)
                                    context.ordmgr.send_order(_id, context.TargetPosition.Leg2Symbol, order_price,
                                                              order_amount, Direction.BUY, order_open_close)
                                    # context.logger.info(
                                    #     'China Send Order Symbol:{0}, order_price: {1},
                                    #       order_direction: {2} order_amount: {3}
                                    #       order_open_close: {4}, at id: {5}'.format(
                                    #       order_symbol, order_price, Direction.BUY, order_amount,
                                    #        order_open_close, _id))
                            if context.leg2_position_diff < 0:
                                order_price = calculate_order_price(context.TargetPosition.Leg2Symbol, order_symbol_bid,
                                                                    order_symbol_ask, Direction.SELL,
                                                                    context.order_position)
                                order_info = context.posmgr.get_open_close(order_symbol, order_amount, Direction.SELL,
                                                                           "YES_TOD_SHFE_FLAG")
                                order_amount = order_info[0]
                                order_open_close = order_info[1]
                                if order_amount > 0:
                                    _id = context.order.send_single_order(context.TargetPosition.Leg2Symbol,
                                                                          order_price, order_amount,
                                                                          Direction.SELL, order_open_close)
                                    context.ordmgr.send_order(_id, context.TargetPosition.Leg2Symbol, order_price,
                                                              order_amount, Direction.SELL, order_open_close)
                                    # context.logger.info(
                                    #  'China Send Order Symbol:{0}, order_price: {1}, order_direction: {2}
                                    #  order_amount: {3} order_open_close: {4}, at id: {5}'.format(
                                    #  order_symbol, order_price, Direction.SELL, order_amount, order_open_close, _id))


def on_response(context, response_type, response):
    context.ordmgr.on_response(response_type, response)
    context.posmgr.update_position(response_type, response)
    context.trade_handler.on_response(response_type, response)
    context.AccountPosition.Leg1Position = context.posmgr.get_net_position(context.AccountPosition.Leg1Symbol)
    context.AccountPosition.Leg2Position = context.posmgr.get_net_position(context.AccountPosition.Leg2Symbol)
    # context.logger.info('Leg1_position: {0} , Leg2_position: {1},
    # Response status: {2}'.format(context.AccountPosition.Leg1Position,
    # context.AccountPosition.Leg2Position, response.status))
    print('Leg1_position: {0} , Leg2_position: {1}, Response status: {2}'.format(context.AccountPosition.Leg1Position,
                                                                                 context.AccountPosition.Leg2Position,
                                                                                 response.status))
    # if abs(context.AccountPosition.Leg1Position) == 4 and abs(context.AccountPosition.Leg2Position) == 17
    #  and response.status in (OrderStatus.SUCCEED.value, OrderStatus.PARTED.value):
    #     context.data_input_factor.loc[0, 'last_full_position_time'] =
    #       context.data_input_factor.iloc[0]['last_position_time']
    #     context.data_input_factor.loc[0, 'FUL_POS_FLAG'] = True
    #     context.logger.info('Full position: %d, last position: %d' % (
    #     context.data_input_factor.loc[0]['last_full_position_time'],
    #     context.data_input_factor.loc[0]['last_position_time']))
    print(context.AccountPosition.Leg1Position)
    print(context.AccountPosition.Leg2Position)


def on_timer(context, data_type, data):
    pass


def on_session_finish(context):
    context.data_output.to_csv(context.output_file_string, index=False)
    context.logger.info('Point of End: {0}, count is :{1}'.format(datetime.now(), context.execution_count))
    print('Point of End: {0}, count is :{1}, parameter_bar_length is : {2}'.format(datetime.now(), context.execution_count, parameter_bar_length))
    # context.data_input_factor.to_csv(context.input_factors_file, index=False)
    # context.data_output_detail.to_csv(context.output_file_string_detail, index=False)
    pass


if __name__ == "__main__":
    import os
    from my.sdp.simu.config import StratConfig
    from my.sdp.simu.simulator import execute_task

    st1 = StratConfig.StratItem(strat_name="test", strat_id=1)
    st1.contracts = ["cu|R1|SHFE|12|1|0|AccountSHFE", "CU3M||LME|25|10|0|AccountSHFE", "ru|R1|SHFE|12|1|0|AccountSHFE"]
    st1.accounts = ["AccountSHFE|999999.99|888888.88|CNY|1.0"]
    cfg1 = StratConfig()
    cfg1.start_date = 20161201
    cfg1.end_date = 20161231
    cfg1.day_night_flag = 0
    cfg1.strat_item = st1.items()
    cfg1.strategy = os.path.basename(__file__)
    execute_task(cfg1.totask())
