"""
This is a template for Project 1, Task 1 (Induced demand-supply)
"""

from enum import Enum
from fmclient import Agent, OrderSide, Order, OrderType, Session
from typing import List

# Student details
SUBMISSION = {"number": "921322", "name": "Sidakpreet Mann"}

# ------ Add a variable called PROFIT_MARGIN -----
PROFIT_MARGIN = 10


# Enum for the roles of the bot
class Role(Enum):
    BUYER = 0
    SELLER = 1


# Let us define another enumeration to deal with the type of bot
class BotType(Enum):
    MARKET_MAKER = 0
    REACTIVE = 1


class DSBot(Agent):
    # ------ Add an extra argument bot_type to the constructor -----
    def __init__(self, account, email, password, marketplace_id, bot_type):
        super().__init__(account, email, password, marketplace_id, name="DSBot")
        self._public_market_id = 0
        self._private_market_id = 0
        self._role = None
        # ------ Add new class variable _bot_type to store the type of the bot
        self._bot_type = bot_type

    def role(self):
        return self._role

    def pre_start_tasks(self):
        pass

    def initialised(self):
        pass

    def order_accepted(self, order: Order):
        pass

    def order_rejected(self, info, order: Order):
        pass

    def received_orders(self, orders: List[Order]):
        # for o in orders:
        #     # if o.mine or o.is_private:
        #     self.inform(o)

        if self._bot_type == BotType.REACTIVE:
            self._react_to_market()

    def _react_to_market(self):
        # track best bid and asks
        best_bid, best_ask = self._get_best_bid_ask()

        num_private_orders = 0
        num_my_public_orders = 0
        # ORDER.CURRENT - no cancelled orders, all is_pending, all not consumed
        for fm_id, order in Order.current().items():
            # # if there is a private order not created by me
            # if order.is_private and not order.mine:
            #     num_private_orders += 1
            # elif not order.is_private and
            # self.inform(order)
            self.inform(f"type = {order.order_type==OrderType.CANCEL} Is_private: {order.is_private},\n"
                        f" is_pending: {order.is_pending}, is_consumed: {order.is_consumed}")

        self.inform(f"Best bid: {best_bid}, Best ask: {best_ask}")

    @staticmethod
    def _get_best_bid_ask():
        # initial bid and asks unrealistic / out of bound
        best_bid = 0
        best_ask = 999999

        for fm_id, order in Order.current().items():
            if not order.is_consumed and not order.is_private:
                if order.order_side == OrderSide.BUY and order.price > best_bid:
                    best_bid = order.price
                elif order.order_side == OrderSide.SELL and order.price < best_ask:
                    best_ask = order.price

        return best_bid, best_ask

    def _print_trade_opportunity(self, other_order):
        self.inform(f"I am a {self.role()} with profitable order {other_order}")

    def received_completed_orders(self, orders, market_id=None):
        pass

    def received_holdings(self, holdings):
        pass

    def received_session_info(self, session: Session):
        pass


if __name__ == "__main__":
    FM_ACCOUNT = "ardent-founder"
    FM_EMAIL = "s.mann4@student.unimelb.edu.au"
    FM_PASSWORD = "921322"
    MARKETPLACE_ID = 915

    # B_TYPE = BotType.MARKET_MAKER
    B_TYPE = BotType.REACTIVE

    ds_bot = DSBot(FM_ACCOUNT, FM_EMAIL, FM_PASSWORD, MARKETPLACE_ID, B_TYPE)
    ds_bot.run()
