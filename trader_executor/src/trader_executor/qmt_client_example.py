# 导入所需的库
import random
import time

from trade_callback import MyTradingCallback
from xtquant import xtconstant, xttrader
from xtquant.xttype import StockAccount

# 基本配置
min_path = r"D:\国金证券QMT交易端\userdata_mini"
account_number = '8885385377'

# 生成会话ID,创建 XtQuantTrader 实例
session_id = int(random.randint(100000, 999999))
xt_trader = xttrader.XtQuantTrader(min_path, session_id)

# 注册回调类
callback = MyTradingCallback()
xt_trader.register_callback(callback)

# 启动交易线程
xt_trader.start()

# 连接 QMT 交易端
connect_result = xt_trader.connect()
if connect_result == 0:
    print('连接成功')
else:
    print('连接失败')
    xt_trader.stop()
    exit()

# 获取账户信息
account = StockAccount(account_number)

# 订阅账户
res = xt_trader.subscribe(account)
if res == 0:
    print('订阅成功')
else:
    print('订阅失败')
    xt_trader.stop()
    exit()


# 5. 下单 (示例：买入中航光电 100 股)
order_id = xt_trader.order_stock(account, "002179.SZ", xtconstant.STOCK_BUY, 100, xtconstant.FIX_PRICE, 35)

if order_id > 0:
    print(f"下单指令发送成功，本地订单ID: {order_id}")
    print("请等待 on_order_stock 或 on_trade_stock 回调确认最终结果...")
else:
    print("下单指令发送失败（可能是本地参数错误）")

# 保持程序运行以接收回调
while True:
    print("主线程正在运行，等待回调...")
    # 输入 Ctrl+C 可退出程序
    try:
        time.sleep(5)
    except KeyboardInterrupt:
        print("程序终止，正在断开连接...")
        xt_trader.stop()
        break
