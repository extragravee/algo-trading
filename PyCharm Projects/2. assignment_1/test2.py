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
        self._active_private_orders = {}
        self._active_private_orders_count = 0
        self._active_public_orders = {}
        self._active_public_orders_count = 0
        self._order_tracking_number = 0
        self._waiting_for_server = False

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
        self.inform(f"{order.ref} accepted.")
        self.inform(order)
        self._order_tracking_number += 1

    def order_rejected(self, info, order: Order):
        self._waiting_for_server = False
        self.inform(f"***************** {order.ref} rejected *****************")
        self.inform(info)

    def received_orders(self, orders: List[Order]):
        """
        Tracks active public and private orders in internal store
        Calls bot strategy
        :param orders:
        :return:
        """
        for order_update in orders:
            if order_update.mine or order_update.is_private:
                self.inform(order_update)

            # track all active private orders
            if order_update.is_private:

                # add active orders to internal tracker
                if order_update.is_pending:
                    self._active_private_orders[order_update.fm_id] = order_update
                    self._active_private_orders_count += 1

                # if fully consumed or cancelled, stop tracking it
                else:
                    if order_update.original_id in self._active_private_orders:
                        del self._active_private_orders[order_update.original_id]
                        self._active_private_orders_count -= 1
                # self.inform(self._active_private_orders)
            # track only my public orders
            else:
                # track only orders which are mine
                if order_update.mine:

                    # if order is active, add to internal tracker
                    if order_update.is_pending:
                        self._active_public_orders[order_update.fm_id] = order_update
                        self._active_public_orders_count += 1
                    # if order is now consumed, remove order
                    elif order_update.is_consumed:
                        if order_update.original_id in self._active_public_orders:
                            del self._active_public_orders[order_update.original_id]
                            self._active_public_orders_count -= 1
                # self.inform(self._active_public_orders)

        # call strategy based on bot type AFTER all updates are accounted for
        if self._bot_type == BotType.MARKET_MAKER:
            self._make_market()

    def _make_market(self):
        # if there is a private order, and no public order, CREATE NEW ORDER(S)
        self._active_public_orders_count = len(self._active_public_orders)
        self.inform(f"Private: {self._active_private_orders_count}, Public: {self._active_public_orders_count}")
        self.inform(f"{self._active_private_orders}, {self._active_public_orders}")
        if self._active_private_orders_count > 0 and self._active_public_orders_count < 1\
                and not self._waiting_for_server:
            self.inform("Order required ====================================")
            # for each active order in private market (for task 1, just 1)
            for fm_id in self._active_private_orders:

                # PUBLIC ORDER CREATION ==================================================
                is_private = False
                priv_order = self._active_private_orders[fm_id]

                # if manager order is a bid
                if priv_order.order_side == OrderSide.BUY:
                    self._role = Role.BUYER
                    price = priv_order.price - PROFIT_MARGIN
                    order_side = OrderSide.BUY

                # if manager order is an ask
                else:
                    self._role = Role.SELLER
                    price = priv_order.price + PROFIT_MARGIN
                    order_side = OrderSide.SELL

                units = 1
                order_type = OrderType.LIMIT
                ref = f"Order: {self._order_tracking_number} - SM"

                self._create_new_order(price, units, order_side, order_type, ref, is_private)

        # if there is a public order, but not private order (STALE PUBLIC ORDER)
        # walk through current orders, delete my orders
        if self._active_public_orders_count > 0 and self._active_private_orders_count < 1\
                and not self._waiting_for_server:
            current_orders = Order.current()
            for _, o in current_orders.items():
                if o.mine:
                    cancel_order = copy.copy(o)
                    cancel_order.order_type = OrderType.CANCEL
                    cancel_order.ref = f"Cancel {o.ref}"
                    self.send_order(cancel_order)
                    self._waiting_for_server = True

        # if there is a public order, and a private order, do nothing

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
            self._active_private_orders_count += 1
            new_order.owner_or_target = "M000"
        else:
            market = self._public_market_id
            self._active_public_orders_count += 1

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
    MARKETPLACE_ID = 915

    B_TYPE = BotType.MARKET_MAKER
    # B_TYPE = BotType.REACTIVE

    ds_bot = DSBot(FM_ACCOUNT, FM_EMAIL, FM_PASSWORD, MARKETPLACE_ID, B_TYPE)
    ds_bot.run()
