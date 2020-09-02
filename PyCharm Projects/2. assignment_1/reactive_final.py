"""
FNCE30010 - Algorithmic Trading
Assignment 1
Sidakpreet Mann
921322

Notes:
    1. Profitable trade printing only implemented for reactive bot type
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
        self._tradeID = 0
        self._last_accepted_public_order_id = 0

        self._cash_available = 0
        self._cash = 0
        self._assets = {}
        self._private_widgets_available = 0
        self._public_widgets_available = 0

    # MARKET MAKER FUNCTIONALITY ##########################################################
    def _make_market(self):

        # track state of order book
        num_private_orders, num_my_public_orders, \
            my_stale_priv_order, manager_order = self._get_order_book_state()
        self.inform(f"{num_my_public_orders}, {num_private_orders}")

        # check if my last public order has traded, and there is a private order
        if not self._last_accepted_public_order_id == 0 and \
                (self._last_accepted_public_order_id not in Order.current()) and \
                num_private_orders > 0:
            self.inform("Last order traded fine, make private order ==============")
            #     # reset the flag
            self._last_accepted_public_order_id = 0
            self._create_market_maker_private_order(manager_order)

        # if i have no active public orders, and there are manager order(s)
        if num_my_public_orders == 0 and num_private_orders > 0:
            self._create_market_maker_public_order(manager_order)

        # if stale public order
        if num_my_public_orders > 0 and num_private_orders < 1:
            self.inform(f"Stale order - {my_stale_priv_order.ref} being cleared.")
            self._cancel_order(my_stale_priv_order)
            self._last_accepted_public_order_id = 0

    def _create_market_maker_private_order(self, manager_order):

        # determine attributes for private order
        is_private = True
        price = manager_order.price
        units = 1

        if manager_order.order_side == OrderSide.BUY:
            order_side = OrderSide.SELL
        else:
            order_side = OrderSide.BUY

        order_type = OrderType.LIMIT
        ref = f"Private order - {self._tradeID}"
        self.inform(f"Order side is: {order_side}")
        self._create_new_order(price, units, order_side, order_type, ref, is_private)

    def _create_market_maker_public_order(self, manager_order):

        # if waiting for server, don't do anything
        if self._waiting_for_server:
            return

        # determine attributes for public order
        # simple strategy - make minimum profit
        is_private = False

        if self.role() == Role.BUYER:
            price = manager_order.price - PROFIT_MARGIN
            order_side = OrderSide.BUY
        elif self.role() == Role.SELLER:
            price = manager_order.price + PROFIT_MARGIN
            order_side = OrderSide.SELL

        units = 1
        order_type = OrderType.LIMIT
        ref = f"SM - {order_side}-{self._tradeID}"

        self._create_new_order(price, units, order_side, order_type, ref, is_private)

    # SHARED FUNCTIONALITY ################################################################

    def role(self):
        return self._role

    def pre_start_tasks(self):
        pass

    def received_holdings(self, holdings):
        """
        Tracks the portfolio holdings
        :param holdings: attributes of interest cash, cash_available, assets
        """
        # track cash assets
        self._cash = holdings.cash
        self._cash_available = holdings.cash_available

        # dict to track units of widgets and private widgets
        self._assets = holdings.assets

        # track available public and private units
        for key in self._assets:
            if key.fm_id == self._public_market_id:
                self._public_widgets_available = self._assets[key].units_available
            elif key.fm_id == self._private_market_id:
                self._private_widgets_available = self._assets[key].units_available

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
        """
        Notifies last order being accepted
        Async - no longer waiting for the server
        :param order: previous accepted order
        """
        self._waiting_for_server = False

        # track my last accepted public order
        if not order.is_private:
            self._last_accepted_public_order_id = order.fm_id

    def order_rejected(self, info, order: Order):
        """
        Notifies last order being rejected
        Async - no longer waiting for the server
        :param info: details of rejected order
        :param order: previous rejected order
        """
        self._waiting_for_server = False

    def received_orders(self, orders: List[Order]):
        """
        Subscriber to order updates
        Notifies new updates in the market
        :param orders: list of order objects (updates)
        """
        for o in orders:
            if o.mine or o.is_private:
                self.inform(o)

        if self._bot_type == BotType.REACTIVE:
            self._react_to_market()
        elif self._bot_type == BotType.MARKET_MAKER:
            self._make_market()

    def _create_new_order(self,
                          price: int,
                          units: int,
                          order_side: OrderSide,
                          order_type: OrderType,
                          ref: str,
                          is_private: bool):
        """
        Creates a new order given the parameters
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
            new_order.owner_or_target = "M000"
        else:
            market = self._public_market_id

        new_order.market = Market(market)
        new_order.price = price
        new_order.units = units
        new_order.order_side = order_side
        new_order.order_type = order_type
        new_order.ref = ref

        self._waiting_for_server = True
        self.send_order(new_order)
        self._tradeID += 1

    def _cancel_order(self, order):
        """
        Helper function to cancel given order
        :param order: order to be cancelled
        """
        cancel_order = copy.copy(order)
        cancel_order.order_type = OrderType.CANCEL
        cancel_order.ref = f"SM - Cancel - {order.ref}"
        self.send_order(cancel_order)

    def received_completed_orders(self, orders, market_id=None):
        pass

    def received_session_info(self, session: Session):
        pass

    # REACTIVE FUNCTIONALITY ##########################################################

    def _react_to_market(self):
        """
        Ascertains state of the market, best bid and asks
        Creates orders in public and private market
        """
        # track best bid and asks
        best_bid, best_ask, best_bid_order, best_ask_order = self._get_best_bid_ask()

        # track state of order book
        num_private_orders, num_my_public_orders, my_stale_priv_order, \
            manager_order = self._get_order_book_state()

        # if i have ANY orders in the public book, it's stale, so cancel it
        if my_stale_priv_order is not None and \
                self._last_accepted_public_order_id not in Order.current():
            self.inform(f"Stale order - {my_stale_priv_order.ref} being cleared.")
            self._cancel_order(my_stale_priv_order)
            self._last_accepted_public_order_id = 0

        # PRIVATE ORDER CREATION ==============================================================
        # only create private order if public order traded successfully, and there exists
        # a corresponding manager order
        if (not self._last_accepted_public_order_id == 0) and \
                (self._last_accepted_public_order_id not in Order.current()) and \
                num_private_orders > 0:

            self._last_accepted_public_order_id = 0
            self.inform("Last public order traded, creating private order.")

            # Order attributes
            is_private = True
            price = manager_order.price
            units = 1
            if self.role() == Role.BUYER:
                order_side = OrderSide.SELL
            else:
                order_side = OrderSide.BUY
            order_type = OrderType.LIMIT
            ref = f"Private order - {self._tradeID}"

            # if we are a buyer, we sell in private market. Ensure have enough priv widgets
            # if we are a seller, we buy in private market. Ensure have enough cash
            if (self.role() == Role.BUYER and self._private_widgets_available > 0) or \
                    (self.role() == Role.SELLER and self._cash_available >= price):
                self._create_new_order(price, units, order_side, order_type, ref, is_private)

        # END PRIVATE ORDER CREATION ==========================================================

        # PUBLIC ORDER CREATION ===============================================================
        # stale orders should be cleared at this stage; there exists a private order
        # create an order based on best bid / ask
        if num_private_orders > 0 and not self._waiting_for_server:
            is_private = False
            self._create_profitable_order(best_ask, best_bid, manager_order, is_private,
                                          best_bid_order, best_ask_order)
        # END PUBLIC ORDER CREATION ===========================================================

    @staticmethod
    def _get_best_bid_ask():
        """
        Determine and return best active bid and asks in the order book
        :return: best_bid: best buy price
                 best_ask: best sell price
                 best_ask_order: best bid order object
                 best_bid_order:  best ask order object

        """
        # initial bid and asks unrealistic / out of bound
        best_bid = 0
        best_ask = 999999
        best_ask_order = None
        best_bid_order = None

        # run through the order book, determine best bid and asks
        for fm_id, order in Order.current().items():
            if not order.is_consumed and not order.is_private:
                if order.order_side == OrderSide.BUY and order.price > best_bid:
                    best_bid = order.price
                    best_bid_order = order
                elif order.order_side == OrderSide.SELL and order.price < best_ask:
                    best_ask = order.price
                    best_ask_order = order

        return best_bid, best_ask, best_bid_order, best_ask_order

    def _print_trade_opportunity(self, other_order):
        """
        Print profitable trade opportunities
        :param other_order: order that's profitable given the profit margin
        :return:
        """
        self.inform(f"I am a {self.role()} with profitable order {other_order}")

    def _get_order_book_state(self):
        """
        Ascertain how many active orders are mine, or from the manager to me,
            and if I have a stale order in the markets
        :return: num_private_orders : number of active private orders
                 num_my_public_orders : number of my non-trade public orders
                 my_stale_priv_order : which order of mine is stale
                 manager_order : order object created by the manager
        """
        num_private_orders = 0
        manager_order = None
        num_my_public_orders = 0
        my_stale_priv_order = None

        for fm_id, order in Order.current().items():
            # if there is a private order not created by me
            if order.is_private and not order.mine:
                num_private_orders += 1
                manager_order = order

                # figure out our role based on private order
                if manager_order.order_side == OrderSide.BUY:
                    self._role = Role.BUYER
                else:
                    self._role = Role.SELLER

            # if i created a public order that DID NOT EXECUTE IMMEDIATELY
            elif not order.is_private and order.mine:
                num_my_public_orders += 1
                my_stale_priv_order = order


        return num_private_orders, num_my_public_orders, my_stale_priv_order, manager_order

    def _create_profitable_order(self, best_ask, best_bid, manager_order, is_private,
                                 best_bid_order, best_ask_order):
        """
        Handle the creation of profitable orders in the public market
        :param best_ask: best asking price
        :param best_bid: best bidding price
        :param manager_order: manager's order object
        :param is_private: if order to be created is private or not
        :param best_bid_order: order object of best bidder
        :param best_ask_order: order object of best seller
        """
        # if buyer
        if self.role() == Role.BUYER:
            # if the best selling price is less than
            # or equal to the price we want to buy at, submit order
            if best_ask <= manager_order.price - PROFIT_MARGIN:
                self.inform("Creating public order========================")
                price = best_ask
                units = 1
                order_side = OrderSide.BUY
                order_type = OrderType.LIMIT
                ref = f"SM - {order_side}-{self._tradeID}"

                # if we have enough cash available, make the order
                if self._cash_available >= price:
                    self._create_new_order(price, units, order_side, order_type, ref, is_private)
                    self.inform("Responding to: ")
                    self._print_trade_opportunity(best_ask_order)
                else:
                    self.inform("Not enough cash, but want to respond to: ")
                    self._print_trade_opportunity(best_ask_order)

        # if we are sellers
        else:
            # if the best asking price is more than
            # or equal to the price we want to sell at, submit order
            if best_bid >= manager_order.price + PROFIT_MARGIN:
                self.inform("Creating public order========================")
                price = best_bid
                units = 1
                order_side = OrderSide.SELL
                order_type = OrderType.LIMIT
                ref = f"SM - {order_side}-{self._tradeID}"

                # only sell if have any public widgets available
                if self._public_widgets_available > 0:
                    self._create_new_order(price, units, order_side, order_type, ref, is_private)
                    self.inform("Responding to: ")
                    self._print_trade_opportunity(best_bid_order)
                else:
                    self.inform("Not enough widgets, but want to respond to: ")
                    self._print_trade_opportunity(best_bid_order)


if __name__ == "__main__":
    FM_ACCOUNT = "ardent-founder"
    FM_EMAIL = "s.mann4@student.unimelb.edu.au"
    FM_PASSWORD = "921322"
    MARKETPLACE_ID = 915

    # B_TYPE = BotType.MARKET_MAKER
    B_TYPE = BotType.REACTIVE

    ds_bot = DSBot(FM_ACCOUNT, FM_EMAIL, FM_PASSWORD, MARKETPLACE_ID, B_TYPE)
    ds_bot.run()
