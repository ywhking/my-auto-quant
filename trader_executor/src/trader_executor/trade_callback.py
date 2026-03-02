from xtquant.xttrader import XtQuantTraderCallback


class MyTradingCallback(XtQuantTraderCallback):
    def on_disconnected(self):
        print("连接断开")

    def on_order_stock(self, order):
        """
        委托状态回调
        order.order_status: 委托状态 (50:已报, 51:待撤, 52:部成, 53:全成, 54:已撤, 55:部撤, 56:废单)
        """
        print(f"【委托更新】订单ID: {order.order_id}, 状态码: {order.order_status}, 消息: {order.status_msg}")

        # 判断是否完全成交
        if order.order_status == 53:
            print(">>> 交易成功：订单已全部成交！")
        elif order.order_status == 56:
            print(">>> 交易失败：订单被废单！")

    def on_trade_stock(self, trade):
        """
        成交回调 (真正成交发生时触发)
        """
        print(f"【成交回报】订单ID: {trade.order_id}, 成交数量: {trade.traded_volume}, 成交价格: {trade.traded_price}")
        print(">>> 确认：发生了一笔真实成交！")

    def on_order_error(self, order_error):
        """
        下单错误回调 (下单请求直接被拒)
        """
        print(f"【下单错误】订单ID: {order_error.order_id}, 错误信息: {order_error.error_msg}")

