"""
This is a template for Project 1, Task 1 (Induced demand-supply)
"""
import copy
from enum import Enum
from fmclient import Agent, OrderSide, Order, OrderType, Session, Market
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
        self._sent_order_count = 0
        self._waiting_for_server = False
        self._priv_order_exists = False  # tracks if there is a manager priv order that exists

    def role(self):
        return self._role

    def pre_start_tasks(self):
        pass

    def initialised(self):
        """
        Initialises bot
        Stores the market id parameters for Order Management
        """
        # dict to track market attributes
        markets_to_trade = self.markets
        for key in markets_to_trade:
            self.inform(markets_to_trade[key])

            # initialise market ids
            if markets_to_trade[key].private_market:
                self._private_market_id = key
            else:
                self._public_market_id = key

    def order_accepted(self, order: Order):
        self._waiting_for_server = False

    def order_rejected(self, info, order: Order):
        self._waiting_for_server = False

    def received_orders(self, orders: List[Order]):
        """
        Subscribed to Order book updates
        :param orders: list of order objects
        """

        for order in orders:
            self.inform(order)

            # track if there is a private market order from manager
            # SIMULATION
            # if order.is_private and order.is_pending and not order.mine:
            if order.is_private and order.is_pending:
                self._priv_order_exists = True
            elif order.is_private and order.is_consumed:
                self._priv_order_exists = False

        # call strategy based on bot type
        if self._bot_type == BotType.MARKET_MAKER:
            self._make_market()

    def _make_market(self):
        """
        Market Making Strategy
        Parts:
            1. Iterate over all orders, track number of active public orders by me
            2. Track active private orders
            3. Cancel stale orders
            4. If private order by manager exists, and no public orders by me, create one
        """
        num_pending_orders = 0
        num_manager_order = 0
        manager_order = None

        for _, order in Order.all().items():

            # 1. if i have a current order in the public market
            if order.mine and not order.is_private and not order.is_consumed:
                num_pending_orders += 1

                # 3. cancel stale orders in public market
                if not self._priv_order_exists and not self._waiting_for_server:
                    cancel_order = copy.copy(order)
                    cancel_order.ref = f"Cancel {order.ref}"
                    cancel_order.order_type = OrderType.CANCEL
                    self.send_order(cancel_order)
                    self._waiting_for_server = True
                    self._sent_order_count -= 1

            # 2. track active private orders
            # SIMULATION
            # if order.is_private and not order.mine:
            if order.is_private and not order.is_consumed:

                # set role of bot
                if order.order_side == OrderSide.BUY:
                    self._role = Role.BUYER
                else:
                    self._role = Role.SELLER

                num_manager_order += 1
                manager_order = order

        # 4. if 0 mine orders in public, and not waiting for server, and there is a
        # private order to be serviced
        if num_pending_orders == 0 and not self._waiting_for_server \
                and num_manager_order > 0:

            is_private = False

            # PUBLIC ORDER SIDE - Determine attributes of order to be created==========
            market = self._public_market_id

            if self._role == Role.BUYER:
                price = manager_order.price - PROFIT_MARGIN
                order_side = OrderSide.BUY
            else:
                price = manager_order.price + PROFIT_MARGIN
                order_side = OrderSide.SELL

            units = 1
            order_type = OrderType.LIMIT
            ref = f"Order: {self._sent_order_count} - SM"

            self._create_new_order(market, price, units, order_side, order_type, ref, is_private)

            # PRIVATE ORDER SIDE - Determine attributes of order to be created========
            # flip attributes
            is_private = True
            market = self._private_market_id
            price = manager_order.price

            if self._role == Role.BUYER:
                order_side = OrderSide.SELL
            else:
                order_side = OrderSide.BUY

            units = 1
            order_type = OrderType.LIMIT
            ref = f"Order: {self._sent_order_count} - SM"
            self._create_new_order(market, price, units, order_side, order_type, ref,
                                   is_private)

    def _create_new_order(self, market: int,
                          price: int,
                          units: int,
                          order_side: OrderSide,
                          order_type: OrderType,
                          ref: str,
                          is_private: bool):
        """
        :param market: market ID for the order
        :param price: determined price
        :param units: # of units to be submitted, fixed to 1
        :param order_side: buy or sell
        :param order_type: limit or market, fixed to limit
        :param ref: customer string of format "Order: {self._sent_order_count} - SM"
        :return:
        """
        new_order = Order.create_new()
        new_order.market = Market(market)
        new_order.price = price
        new_order.units = units
        new_order.order_side = order_side
        new_order.order_type = order_type
        new_order.ref = ref

        if is_private:
            new_order.owner_or_target = "M000"

        self.send_order(new_order)
        self._waiting_for_server = True
        self._sent_order_count += 1

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
    MARKETPLACE_ID = 898

    B_TYPE = BotType.MARKET_MAKER
    # B_TYPE = BotType.REACTIVE

    ds_bot = DSBot(FM_ACCOUNT, FM_EMAIL, FM_PASSWORD, MARKETPLACE_ID, B_TYPE)
    ds_bot.run()
