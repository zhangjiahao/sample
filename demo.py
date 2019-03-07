# -*- coding: utf-8 -*-

from my.simu.loader import load_env

# 初始化环境，优先执行
load_env()

# from my.simu.notebook.draw_tool import DrawPNL
from my.simu.notebook.task import TaskConstructor
from my.simu.simulator.simu_handler import execute_task


def contruct_task():
    # 任务构造器
    task_hdl = TaskConstructor()
    # 账户配置, 合约订阅中的账户需与当前账户保持一致
    task_hdl.set_accounts([
        "account1|999999.99|999999.99|CNY|1.0"
    ])
    # 设置外部参数文件的路径，其中[DATE]-> 模拟交易日的日期YYYYMMDD，[DAYNIGHT]->模拟日夜盘(day 或者 night)
    task_hdl.set_ev_path('./param1/abc_[DATE]_[DAYNIGHT].csv')
    # 策略可写文件夹
    task_hdl.set_output_path(output_dir='./output')
    # 定时调用 on_timer 的时间
    task_hdl.set_time_interval(interval=60)
    # 撮合类型： MY_tick_0%, MY_tick_50%, MY_tick_100%, MY_tick_default, MY_ideal_matching
    task_hdl.set_match_type('MY_tick_default')
    # so_path 为策略路径，st_name & st_id 可不设置
    # 策略文件可以是 python 源码，例如 st.py
    task_hdl.set_strat_so(so_path='./st.py', st_name='demo', st_id=100)
    # start是模拟起始日期，end是模拟终止日期，day_night是模拟范围，0-日盘，1-夜盘，2-夜日盘
    task_hdl.set_simu_range(start=20161010, end=20161010, day_night=0)
    # 订阅合约配置参考 wiki 描述(品台配置->合约及账户配置)
    task_hdl.set_contracts(["rb|R1|SHFE|12|1|0|account1"])
    # 传递撮合需要的参数，目前针对比特币需要设置is_btc_strategy为True.
    task_hdl.set_settle_kwargs(is_btc_strategy=False)
    # 支持设置运行模式，如果没有特别需求，不需要执行, 0 - live, 1 - simulate, 2 - enable sell open stock
    task_hdl.set_running_mode(1)
    return task_hdl


#drawer = DrawPNL()


def return_hdl(message):
    # 执行清算得到的结果，每天执行完成会调用该回调
    print(message)
    # 动态绘制 PNL 曲线
    #drawer.add_settle_result(message)
    #drawer.interactive_draw()


def information_hdl(type_t, message):
    # 记录信息传递接口，用户无需关注，当 type_t = 0 时，消息内容为 crash context 信息
    if type_t == 0:
        print(message)


if __name__ == "__main__":
    # 组织回测任务
    task_hdl = contruct_task()
    # 执行回测
    execute_task(task_hdl.get_task(), return_hdl, information_hdl)
    # 将 pnl 结果保存到当前目录中
    #drawer.save_fig()
