"""

FNCE30010 - Algorithmic Trading
921322
Sidakpreet Mann
Project 1, Task 1 (Induced demand-supply)

Completed:
1
2. is role what we are doing the the public market?
    eg. private market has buy order, we need to buy in public, but sell in private
        so is the role buy? or sell?

        **assuming role is what we do in the public market**
3.
4.

For now using naive approach and cycling all orders to find best bid,ask
"""

import copy
from enum import Enum
from fmclient import Agent, OrderSide, Order, OrderType, Session
from typing import List

# Student details
SUBMISSION = {"number": "921322", "name": "Sidakpreet Mann"}

# ------ Add a variable called PROFIT_MARGIN -----
PROFIT_MARGIN = 0


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

        # New instance vars
        self._spread = [0, 1000]  # tracks current best bid and ask
        self._active_orders = {}

    def role(self):
        return self._role

    def pre_start_tasks(self):
        pass

    def initialised(self):
        """
        Stores the market parameters
        1572 - PublicWidget Market
        1573 - PrivateWidget Market
        """

        # dict to track market params
        markets_to_trade = self.markets
        for key in markets_to_trade:
            self.inform(markets_to_trade[key])

    def order_accepted(self, order: Order):
        pass

    def order_rejected(self, info, order: Order):
        pass

    def received_orders(self, orders: List[Order]):
        """
        Subscriber to Order book updates
        :param orders: list of order objects
        """
        for order in orders:
            self.inform(order)

            # track pending orders
            if order.is_pending:
                self._active_orders[order.fm_id] = order

            # delete completed orders
            elif not order.is_pending and order.fm_id in self._active_orders:
                del self._active_orders[order.fm_id]

        # only call this when there is a new order from the manager
        self._get_best_bid_ask()
        print(self._spread)
            # # track orders received by manager
            # if order.is_private and not order.mine:
            #     self._role = order.order_side
            #
            #     bid, ask = self._best_bid_ask()
            #     # based on bot type, implement strategy
            #     if self._bot_type == BotType.REACTIVE:
            #         pass
            #     else:  # BotType.MarketMaker
            #         pass

    def _get_best_bid_ask(self):
        """
        Returns the bid and ask order, quantity pairs
        :param orders: List of all orders
        :return:
        """
        # reset bid and asks! important if not tracking individual orders
        self._spread = [0, 1000]

        # # key is order fmid, value is order object
        # all_orders = Order.all()

        for _, order in self._active_orders.items():

            if order.is_pending and not order.is_private:

                # update best bids
                if order.order_side == OrderSide.BUY:
                    if order.price > self._spread[0]:
                        self._spread[0] = order.price

                # update best ask
                if order.order_side == OrderSide.SELL:
                    if order.price < self._spread[1]:
                        self._spread[1] = order.price


    def _print_trade_opportunity(self, other_order):
        self.inform(f"I am a {self.role()} with profitable order {other_order}")

    def received_completed_orders(self, orders, market_id=None):
        pass

    def received_holdings(self, holdings):
        """
        Tracks the portfolio holdings
        :param holdings: attributes of interest cash, cash_available, assets
        """

        cash = holdings.cash
        cash_available = holdings.cash_available

        # dict to track units of widgets and private widgets
        assets = holdings.assets
        # print(assets)

    def received_session_info(self, session: Session):
        pass


if __name__ == "__main__":
    FM_ACCOUNT = "ardent-founder"
    FM_EMAIL = "s.mann4@student.unimelb.edu.au"
    FM_PASSWORD = "921322"

    # For testing
    # use Marketplace_ID 898 - trial market
    # bot type is reactive atm
    MARKETPLACE_ID = 898
    BOT_TYPE = BotType.REACTIVE

    ds_bot = DSBot(FM_ACCOUNT, FM_EMAIL, FM_PASSWORD, MARKETPLACE_ID, BOT_TYPE)
    ds_bot.run()
