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
        self._waiting_for_server = False
        self._total_orders_sent = 0

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
        self._total_orders_sent += 1
        self.inform(f"Accepted: {order}")

    def order_rejected(self, info, order: Order):
        self._waiting_for_server = False
        self.inform(f"Rejected: {order}")

    def received_orders(self, orders: List[Order]):
        for o in orders:
            self.inform(o)
        if self._bot_type == BotType.REACTIVE:
            pass
        elif self._bot_type == BotType.MARKET_MAKER:
            self._make_market()

    def _make_market(self):

        num_pending_orders = 0
        num_manager_orders = 0
        manager_order = None

        for _, order in Order.current().items():
            if order.mine and not order.is_consumed:
                num_pending_orders += 1
            elif order.is_private and not order.mine and order.is_pending:
                num_manager_orders += 1
                manager_order = order
        self.inform(f"{num_pending_orders}, {num_manager_orders}")
        # if there is a manager order present
        if num_manager_orders > 0:
            if manager_order.order_side == OrderSide.BUY:
                self._role = Role.BUYER
            elif manager_order.order_side == OrderSide.SELL:
                self._role = Role.SELLER

        # if there is a private order from manager, but no public order
        if num_pending_orders == 0 and not self._waiting_for_server \
                and num_manager_orders > 0:
            # create new public order ==============================================
            if self._role == Role.BUYER:
                price = manager_order.price - PROFIT_MARGIN
                order_side = OrderSide.BUY
            elif self._role == Role.SELLER:
                price = manager_order.price + PROFIT_MARGIN
                order_side = OrderSide.SELL

            is_private = False
            units = 1
            order_type = OrderType.LIMIT
            ref = f"Order: {self._total_orders_sent} - SM"

            self._create_new_order(price, units, order_side, order_type, ref, is_private)

            # create corresponding private order ===================================
            is_private = True
            price = manager_order.price
            if manager_order.order_side == OrderSide.BUY:
                order_side = OrderSide.SELL
            elif manager_order.order_side == OrderSide.SELL:
                order_side = OrderSide.BUY
            ref = f"Order: {self._total_orders_sent} - SM"

            self._create_new_order(price, units, order_side, order_type, ref, is_private)

        # if stale orders in either market, cancel them
        if num_manager_orders == 0 and num_pending_orders >= 0:
            for _, order in Order.current().items():
                if order.mine:
                    cancel_order = copy.copy(order)
                    cancel_order.order_type = OrderType.CANCEL
                    cancel_order.ref = f"Cancelled: {order.ref}"
                    self.send_order(cancel_order)


    def _create_new_order(self,
                          price: int,
                          units: int,
                          order_side: OrderSide,
                          order_type: OrderType,
                          ref: str,
                          is_private: bool):
        """
        :param price: determined price
        :param units: # of units to be submitted, fixed to 1
        :param order_side: buy or sell
        :param order_type: limit or market, fixed to limit
        :param ref: customer string of format "Order: {self._sent_order_count} - SM"
        :return:
        """
        new_order = Order.create_new()

        if is_private:
            market = self._private_market_id
            new_order.owner_or_target = "T033"
        else:
            market = self._public_market_id

        new_order.market = Market(market)
        new_order.price = price
        new_order.units = units
        new_order.order_side = order_side
        new_order.order_type = order_type
        new_order.ref = ref

        self.send_order(new_order)
        self._waiting_for_server = True

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