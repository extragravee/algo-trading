"""
Order for orders, OrderSide for buy or sell, OrderType - Limit or Cancel
PLACING ORDER:
        1. receive an Order object with the details of the order
        2. shows the two asset objects with balances for private and public widgets

CANCELLING ORDERS:
    use the copy package
        1. first order received is the initial order with the is_cancelled set to True
        2. a new "cancel" OrderType is received

TRADE OCCURRING:
        1. receive the initial buy order/sell order with updated attribute
        2. receive the corresponding buy / sell
        3. receive a third order, which is the notification of the trade occurring

"""
import copy
from typing import List
from fmclient import Agent, Order, OrderSide, OrderType, Session, Holding, Market


class MyFirstBot(Agent):

    def __init__(self, account, email, password, marketplace_id):
        # check what needs to be passed to parent
        super().__init__(account, email, password, marketplace_id, name="FirstBot")
        self._order_sent = False

    def initialised(self):
        markets_to_trade = self.markets
        for key in markets_to_trade:
            self.inform(markets_to_trade[key])

        # click debugger, and expand markets to trade to see the key,val pairs
        # price is in cents
        # 1572 is public, 1573 is private market key

    # automatically called when order we submit is accepted, callback from server
    # make use of "REF" variable to track which order was accepted
    def order_accepted(self, order: Order):
        pass

    # automatically called when order we submit is rejected
    def order_rejected(self, info: dict, order: Order):
        pass

    # automatically pushed by server to get orders (observer)
    # called when bot starts, and when new orders received
    def received_orders(self, orders: List[Order]):
        orders_avail = orders
        for o in orders_avail:
            # inform method just logs the messages
            self.inform(o)

            # cancelling an order, make sure to check all orders sent are accepted
            if o.mine:
                cancel_order = copy.copy(o)
                cancel_order.order_type = OrderType.CANCEL
                self.send_order(cancel_order)

        # order has attribute mine (bool) to know if our order or not

        # order.all() fetches all previous orders, and we don't need to physically track all changes,
        # we can query this order.all() data to find the status of the order
        # all_orders = Order.all()

        if not self._order_sent:
            order = Order.create_new()
            order.market = Market(1572)
            order.order_side = OrderSide.BUY
            order.order_type = OrderType.LIMIT
            order.price = 600
            order.ref = "rip"
            order.units = 1

            # we will know this owner/target from the private orders we receive
            # Manager is always M000
            order.owner_or_target = "M000"  # sending private orders, the market code should be changed to 1573
            self.send_order(order)
            self._order_sent = True

    # called at start when bot runs, and when holdings change
    def received_holdings(self, holdings: Holding):
        cash = holdings.cash
        cash_avail = holdings.cash_available

        # assets is a dict
        assets = holdings.assets
        for key in assets:
            self.inform(assets[key])

    # to know when market opens / closes, called by server
    def received_session_info(self, session: Session):
        pass

    def pre_start_tasks(self):
        pass


if __name__ == "__main__":
    bot = MyFirstBot("ardent-founder", "s.mann4@student.unimelb.edu.au", "921322", 898)
    bot.run()
