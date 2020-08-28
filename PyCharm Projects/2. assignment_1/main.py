"""
This is a template for Project 1, Task 1 (Induced demand-supply)

IMPLEMENTATION NOTES: I only buy in private if public order succeeds
                        so in the event private expires right as public trades, i will
                        have sent the order in the private - this will automatically
                        get cleared out in some time - see timed function

0. public market orders based on private done
0. public order deletion when private expire done
1. implement corresponding orders in the private market - ONLY when public trade goes through
2. Ensure code keeps running if there are multiple units / unit changes in private
2. do a timed function where i check if there are ONLY my orders in private market (look at implementation notes above)
    then i delete my own private orders






REWRITE ALL LOGIC IN MAKE_MARKET, AND ENSURE THAT WALKING THE ORDER.CURRENT BOOK EACH TIME
THERE IS AN UPDATE

AFTER WALKING TEH BOOK, TRACK IF THERE IS A PRIV ORDER, TRACK IF U HAVE PENDIN IN MARKET
AND MAKE A DECISION ACCORDINGLY
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


# Differentiate between orders, for self._create_order() function
class OrderForMarket(Enum):
    PUBLIC = 0
    PRIVATE = 1


class DSBot(Agent):
    # ------ Add an extra argument bot_type to the constructor -----
    def __init__(self, account, email, password, marketplace_id, bot_type):
        super().__init__(account, email, password, marketplace_id, name="DSBot")
        self._public_market_id = 0
        self._private_market_id = 0
        self._role = None
        # ------ Add new class variable _bot_type to store the type of the bot
        self._bot_type = bot_type
        self._waiting_for_server = False
        self._sent_order_count = 0
        self._pending_order = False

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

            # pending order in private market
            # even if order is partially filled out, it returns 3 entries
            # the buy for x units going through (consumed, not pending)
            # the sell (how many units were sold) (consumed not pending)
            # an order update, with outstanding quantity and price (pending)
            if order.is_private and order.is_pending:
                # if order.is_private and not order.mine: FOR ACTUAL SIMULATION TIMES
                # assign correct role to bot

                if order.order_side == OrderSide.BUY:
                    self._role = Role.BUYER

                elif order.order_side == OrderSide.SELL:
                    self._role = Role.SELLER

                # call strategy based on bot type
                if self._bot_type == BotType.MARKET_MAKER:
                    self._make_market(order)
                elif self._bot_type == BotType.REACTIVE:
                    self._react_to_market(order)

            # during actual simulation add a not order.mine to this
            # if the private order gets cancelled, delete our order from public market
            if order.is_private and order.order_type == OrderType.CANCEL:
                # for some reason, all the order attributes need to be present, so it's not
                # possible to keep track of your old order by reference
                # old order reference only contain the specific attributes we define, everything
                # else is None type
                orders = Order.current()
                for _, o in orders.items():

                    # future proofing, if multiple types of orders in priv and one type expires
                    # only delete the corresponding orders in public
                    if o.mine and not o.is_private and order.order_side == o.order_side\
                            and not self._waiting_for_server:
                        cancel_order = copy.copy(o)
                        cancel_order.ref = f"Cancel {o.ref}"
                        cancel_order.order_type = OrderType.CANCEL
                        self.send_order(cancel_order)
                        self._waiting_for_server = True
                        break

            # if our order gets consumed
            if order.mine and not order.is_private and order.is_consumed:
                self._pending_order = False

    def _make_market(self, priv_order: Order):
        """
        Implements market-maker functionality

        Public order price determination -
            private order price - Profit margin for buying
            private order price + Profit margin for selling
        """
        self._pending_order = False

        # ensure we don't have an already active/pending order
        for _, order in Order.current().items():
            if order.mine and not order.is_consumed and not order.is_private:
                self._pending_order = True

        # PUBLIC MARKET SIDE ======================================================

        market = self._public_market_id

        if self._role == Role.BUYER:
            price = priv_order.price - PROFIT_MARGIN
            order_side = OrderSide.BUY
        else:
            price = priv_order.price + PROFIT_MARGIN
            order_side = OrderSide.SELL

        # fixed attributes
        units = 1
        order_type = OrderType.LIMIT
        ref = f"Order: {self._sent_order_count} - SM"

        # submit order
        if not self._pending_order and not self._waiting_for_server:
            self._create_new_order(market, price, units, order_side, order_type, ref)

        # PRIVATE MARKET SIDE =====================================================

    def _create_new_order(self, market: int,
                          price: int,
                          units: int,
                          order_side: OrderSide,
                          order_type: OrderType,
                          ref: str):
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
