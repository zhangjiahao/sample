# -*- coding: utf-8 -*-

from my.simu.loader import load_env
# 初始化环境，优先执行
load_env()

#from my.simu.notebook.draw_tool import DrawPNL
from my.simu.notebook.task import TaskConstructor
from my.simu.simulator.simu_handler import execute_task
import json
from datetime import datetime
import numpy
import pandas as pandas
import math
# from algorithm import ExecutionAlgorithm


# settlement_pnl_head = ['Date', 'Cumulative_PNL']
settlement_pnl_head_data_frame = pandas.DataFrame()

class SettlementPNL:
    def __init__(self):
        self.cum_pnl_list = []
        self.date_list = []
        self.night_pnl = 0

    def settlement_message_analysis(self, str_data,  settlement_pnl_head_data_frame):
        if isinstance(str_data, str):
            data = json.loads(str_data)
        else:
            data = str_data
        if 'pnl_nodes' not in data:
            print("msg: ", data)
            return
        session_pnl = sum(symbol_pnl['net_pnl'] for symbol_pnl in data["pnl_nodes"])
        date = data["date"]
        day_night = data["day_night"]
        # print("date:%s, day_night:%s, pnl:%s" % (date, day_night, session_pnl))
        if day_night == 1:
            self.night_pnl = session_pnl
            return
        else:
            session_pnl += self.night_pnl
        if len(self.cum_pnl_list) != 0:
            accumulated_pnl = session_pnl + self.cum_pnl_list[-1]
            self.cum_pnl_list.append(accumulated_pnl)
        else:
            self.cum_pnl_list.append(session_pnl)
        self.date_list.append(datetime.strptime(str(date), '%Y%m%d').date())
        for i in range(len(self.date_list)):
            temp_settlement_pnl = [(self.date_list[i], self.cum_pnl_list[i])]
            settlement_pnl_head_data_frame = settlement_pnl_head_data_frame.append(temp_settlement_pnl, ignore_index=False)
        csv_location = str('./ParallelPNL/' + str(data["task_id"]) + '.csv')
        settlement_pnl_head_data_frame.to_csv(csv_location, index=False)

settlement_pnl = SettlementPNL()


def contruct_task():
    # 任务构造器
    task_hdl = TaskConstructor()
    # 配置资金与账户，合约订阅中的账户需与当前账户保持一致
    # task_hdl.set_cash(cash=1000000, account='AccountSHFE')
    task_hdl.task['strat_item']['accounts'] = [
        'AccountSHFE|5000000|5000000|CNY|1.0',
        'AccountLME|5000000|5000000|USD|6.5'
    ]
    # 设置外部参数文件的路径，其中[DATE]-> 模拟交易日的日期YYYYMMDD，[DAYNIGHT]->模拟日夜盘(day 或者 night)
    task_hdl.set_ev_path('./param1/abc_[DATE]_[DAYNIGHT].csv')
    # 策略可写文件夹
    task_hdl.set_output_path(output_dir='./output')
    # 定时调用 on_timer 的时间
    task_hdl.set_time_interval(interval=1)
    # 撮合类型： MY_tick_0%, MY_tick_50%, MY_tick_100%, MY_tick_default, MY_ideal_matching
    task_hdl.set_match_type('MY_tick_default')
    # so_path 为策略路径，st_name & st_id 可不设置，used_se 标识是否使用 smart_execution，默认不使用
    # 策略文件可以是 python 源码，例如 st.py
    task_hdl.set_strat_so(so_path='./ARB_CAD_V3T2_3L_Strategy_V2.py', st_name='demo', st_id=100)
    # task_hdl.set_strat_so(so_path='./st.py', st_name='demo', st_id=100, used_se=True)
    # start是模拟起始日期，end是模拟终止日期，day_night是模拟范围，0-日盘，1-夜盘，2-夜日盘
    task_hdl.set_simu_range(start=20190221, end=20190221, day_night=2)
    # settlement setting
    task_hdl.set_settle_kwargs(is_btc_strategy=False, is_foreign_strategy=True)
    # 订阅合约配置参考 wiki 描述(品台配置->合约及账户配置)
    task_hdl.set_contracts([
        # "cu|R1|SHFE|12|1|0|AccountSHFE",
        "pb|RA|SHFE|12|1|0|AccountSHFE",
        "PB3M||LME|25|10|0|AccountLME",
        # "UC|RA|SGX|25|10|192.168.30.106|AccountSHFE",
        "UC|RA|SGX|25|10|0|AccountLME",
        "USD.CNH||IDEALPRO|59|1|0|AccountLME",
        # "HG|R1|NYMEX|25|1000000|0|AccountLME",
        # "GC|R1|NYMEX|25|1000000|0|AccountLME",
        # "CU3M||LME|25|1|0|AccountLME"
    ])
    return task_hdl

def contruct_task_specific(output_path):
    # 任务构造器
    task_hdl = TaskConstructor()
    # 配置资金与账户，合约订阅中的账户需与当前账户保持一致
    # task_hdl.set_cash(cash=1000000, account='AccountSHFE')
    task_hdl.task['strat_item']['accounts'] = [
        'AccountSHFE|5000000|5000000|CNY|1.0',
        'AccountLME|5000000|5000000|USD|6.5'
    ]
    # 设置外部参数文件的路径，其中[DATE]-> 模拟交易日的日期YYYYMMDD，[DAYNIGHT]->模拟日夜盘(day 或者 night)
    task_hdl.set_ev_path('./param1/abc_[DATE]_[DAYNIGHT].csv')
    # 策略可写文件夹
    task_hdl.set_output_path(output_dir=output_path)
    # 定时调用 on_timer 的时间
    task_hdl.set_time_interval(interval=1)
    # 撮合类型： MY_tick_0%, MY_tick_50%, MY_tick_100%, MY_tick_default, MY_ideal_matching
    task_hdl.set_match_type('MY_tick_default')
    # so_path 为策略路径，st_name & st_id 可不设置，used_se 标识是否使用 smart_execution，默认不使用
    # 策略文件可以是 python 源码，例如 st.py
    task_hdl.set_strat_so(so_path='/home/rss/demo_strategy/ARB_CAD_V3T2_3L_Strategy_V2.py', st_name='demo', st_id=100)
    # task_hdl.set_strat_so(so_path='./st.py', st_name='demo', st_id=100, used_se=True)
    # start是模拟起始日期，end是模拟终止日期，day_night是模拟范围，0-日盘，1-夜盘，2-夜日盘
    task_hdl.set_simu_range(start=20180730, end=20190215, day_night=2)
    # settlement setting
    task_hdl.set_settle_kwargs(is_btc_strategy=False, is_foreign_strategy=True)
    # 订阅合约配置参考 wiki 描述(品台配置->合约及账户配置)
    task_hdl.set_contracts([
        # "cu|R1|SHFE|12|1|0|AccountSHFE",
        "pb|RA|SHFE|12|1|0|AccountSHFE",
        "PB3M||LME|25|10|0|AccountLME",
        # "UC|RA|SGX|25|10|192.168.30.106|AccountSHFE",
        "UC|RA|SGX|25|10|0|AccountLME",
        "USD.CNH||IDEALPRO|59|1|0|AccountLME",
        # "HG|R1|NYMEX|25|1000000|0|AccountLME",
        # "GC|R1|NYMEX|25|1000000|0|AccountLME",
        # "CU3M||LME|25|1|0|AccountLME"
    ])
    return task_hdl


# drawer = DrawPNL()


def return_hdl(message):
    # 执行清算得到的结果，每天执行完成会调用该回调
    if isinstance(message, str):
        data = json.loads(message)
    else:
        data = message
    task_id_key = data["task_id"]
    settlement_pnl.settlement_message_analysis(message, settlement_pnl_head_data_frame)

    # 动态绘制 PNL 曲线
    # drawer.add_settle_result(message)
    # drawer.interactive_draw()
    

def information_hdl(type_t, message):
    # 记录信息传递接口，用户无需关注，当 type_t = 0 时，消息内容为 crash context 信息
    if type_t == 0:
        print(message)


if __name__ == "__main__":
    # # trigger to execute simulation
    # task_hdl = contruct_task()
    # execute_task(task_hdl.get_task(), return_hdl, information_hdl)
    # drawer.save_fig()

    # parallel experiment
    #import sys
    #sys.path.append('/home/rss/demo_strategy/')
    #import ARB_CAD_V3T2_3L_Strategy_V2
    #from multiprocessing import Process
    #import time
    #import my.simu.config
    #procs = []
    #bar_length = 5000
    #for i in range(1):
    #    time.sleep(5)
    #    ARB_CAD_V3T2_3L_Strategy_V2.parameter_bar_length = bar_length * math.pow(2, i)
    #    task_hdl = contruct_task_specific('./output{0}'.format('_parallel_test_' + str(i)))
    #    task_hdl.task['flag_write_tunnel_log'] = False
    #    task_hdl_instance = task_hdl.get_task()
    #    process = Process(target = execute_task, args = (task_hdl_instance, return_hdl, information_hdl))
    #    procs.append(process)
    #    process.start()
    #for process in procs:
    #    process.join()

    task_hdl = contruct_task()
    # 执行回测
    execute_task(task_hdl.get_task(), return_hdl, information_hdl)

