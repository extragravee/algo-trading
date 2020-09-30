"""
FNCE30010 - Algorithmic Trading
Assignment 2 - CAPM
Sidakpreet Mann
921322

PLEASE READ:
    0. Selling notes is independent from strategies
    1. Best set of orders to trade gets selected based on aggressiveness_param
        be default set to 0% (new portfolio performance must be at least 0%
        better than the  current performance for those trades to go through,
        this can be custom set when instantiating the bot. Increasing this param
        makes multi-unit orders more probable)
    2. EVERY 6 SECONDS: Notes sold if cash drops below arbitrary threshold.
    3. EVERY 1 SECOND:
        3.1 Clear all current orders
        3.2 If portfolio not optimal, execute reactive strategy
        3.3 If portfolio is optimal, execute market maker strategy
            3.3.1 With MM strategy, send orders, then wait 1.25 seconds before
            3.3.2 proceeding. Rationale is that portfolio is currently optimal
            3.3.3 any trades that go through past now would be favourable.
"""
import copy
import logging
import itertools
import time
from enum import Enum
from typing import List
import numpy as np
from fmclient import Agent, Session, Market
from fmclient import Order, OrderSide, OrderType

# Submission details
SUBMISSION = {"number": "921322", "name": "Sidakpreet Mann"}

# CONSTANTS
CENTS_IN_DOLLAR = 100
WAIT_6_SECONDS = 6
WAIT_1_SECOND = 1
MIN_CASH_THRESHOLD = 500
NOTE_SELLING_PRICE = 495
MM_STALL_TIME = 1.25
PROFIT_MARGIN = 50


# Bot type enum
class BotType(Enum):
    MARKET_MAKER = 0
    REACTIVE = 1


class CAPMBot(Agent):

    def __init__(self, account, email, password, marketplace_id,
            risk_penalty=0.007, session_time=20, aggressiveness_param=0.00):
        """
        Constructor for the Bot
        :param account: Account name
        :param email: Email id
        :param password: password
        :param marketplace_id: id of the marketplace
        :param risk_penalty: Penalty for risk
        :param session_time: Total trading time for one session
        """
        super().__init__(account, email, password, marketplace_id,
                         name="CAPM Bot")

        self._payoffs = {}
        self._risk_penalty = risk_penalty
        self._session_time = session_time
        self._market_ids = {}
        self._short_units_allowed = {}

        self._asset_units = {}
        self._cash_available = 0
        self._cash_settled = 0
        self._current_port_variance = 0
        self._current_exp_return = 0
        self._current_performance = 0

        self._aggressiveness_param = aggressiveness_param + 1
        self._waiting = False
        self._bot_type = BotType.REACTIVE
        self._order_id = 0

        # reactive bot
        self._reactive_orders = []
        self._num_orders_sent = 0

        # market maker bot
        self._mm_orders = {}
        self._num_active_mm_orders = 0

    @staticmethod
    def _initialise_custom_log():
        logging.getLogger("agent").setLevel(10)
        for handler in logging.getLogger("agent").handlers:
            handler.setLevel(10)

    def initialised(self):
        # self._initialise_custom_log()

        """
        Called once at the beginning to initialse periodic functions and
        instance attributes
        :return:
        """
        # Extract payoff distribution for each security
        for market_id, market_info in self.markets.items():
            # store market id for each item
            self._market_ids[market_info.item] = market_id

            security = market_info.item
            description = market_info.description
            self._payoffs[security] = [int(a) for a in description.split(",")]

        # every second, determine which strategy to trade with
        self.execute_periodically(
            self._execute_appropriate_strategy,
            WAIT_1_SECOND
        )

        # sell notes if not enough cash every 10 seconds
        self.execute_periodically(
            self._sell_notes,
            WAIT_6_SECONDS
        )

        self.inform(f"Market IDs: {self._market_ids}")
        self.inform(f"Payoffs   : {self._payoffs}")
        self._bot_type = BotType.REACTIVE

        return

    def _execute_appropriate_strategy(self):

        if self._current_performance == 0:
            return

        self.inform(f"=============================")
        self.inform(f"Portfolio var: {self._current_port_variance}")
        self.inform(f"Exp return   : {self._current_exp_return}")
        self.inform(f"Performance  : {self._current_performance}")
        self.inform(f"=============================")

        # ff bot is market maker, stall for 1.25 seconds (check notes)
        if self._bot_type == BotType.MARKET_MAKER:
            time.sleep(MM_STALL_TIME)

        # cancel all current orders
        self._cancel_my_orders()

        self._bot_type = BotType.REACTIVE
        # run reactive strategy - (determines if portfolio is optimal)
        is_optimal = self._reactive_strategy()
        if not is_optimal:
            self.inform("Reactive strategy")

        else:
            self.inform("Market Maker strategy")
            self.inform("Waiting 1. 25 seconds")

        # any orders that didn't immediately trade are stale
        # cancel stale orders
        self._cancel_my_orders()

        # market make only if we are at an optimal state
        if is_optimal:
            self._bot_type = BotType.MARKET_MAKER
            self._market_making_strategy()

    # conditions for periodic orders, for some reason only works properly
    # with function pointers
    def _is_bot_reactive(self):
        return self._bot_type == BotType.REACTIVE

    def _is_bot_mm(self):
        return self._bot_type == BotType.MARKET_MAKER

    def _market_making_strategy(self):
        """
        MARKET MAKER STRATEGY
        =====================
        Simulate acquiring/disposing off one unit of each security to calculate
        the change in performance because of this balancing.

        This change in performance is determined to be the price the security
        should by bought/sold for (accounts for changing variance and
        changing expected return)

        That price is then adjusted by a PROFIT MARGIN, and submitted to the
        market
        """
        # do nothing if sending through orders
        if self._waiting or (len(self._asset_units.keys()) == 0):
            return

        self._mm_orders = {}

        # acquire list of all securities
        securities = list(self._payoffs.keys())

        # for each security, determine the prices of valid buys and sells that
        # can be created in the market
        order = Order.create_new()
        order.price = 0

        for security in securities:

            order.market = Market(self._market_ids[security])

            # create quasi buy order
            order.order_side = OrderSide.BUY
            self.is_portfolio_optimal([order])

            # create quasi sell order
            order.order_side = OrderSide.SELL
            self.is_portfolio_optimal([order])

        # filter out orders from potential orders that can't be executed
        # due to not enough cash / units
        self._remove_invalid_mm_orders()

        # # send valid market maker orders in the market
        if not self._waiting:
            self._waiting = True
            self._send_valid_mm_orders()

    def _send_valid_mm_orders(self):
        """
        Executes list of valid market maker orders
        :return: List[Order] of valid orders
        """
        for key in self._mm_orders:

            order = Order.create_new()
            order.market = Market(self._market_ids[key[0]])
            price_tick = order.market.price_tick

            price = self._mm_orders[key] - \
                          (self._mm_orders[key] % price_tick)

            if price <= order.market.min_price:
                price = order.market.min_price
            elif price >= order.market.max_price:
                price = order.market.max_price

            order.price = price

            order.order_side = key[-1]
            order.order_type = OrderType.LIMIT
            order.units = 1

            if order.market.min_price <= order.price <= order.market.max_price:
                self._order_id += 1
                self._num_orders_sent += 1
                self._num_active_mm_orders += 1
                self.send_order(order)
        return

    def _remove_invalid_mm_orders(self):
        """
        Removes invalid market maker orders from list of potential orders
        Records the price adjusted by the profit margin of the orders
        """
        cash_avail = self._cash_available

        # track invalid order keys
        to_del = []

        # set price for order = change in ($) performance * 100 cents
        for key in self._mm_orders.keys():
            self._mm_orders[key] = \
                int(100*abs(self._current_performance - self._mm_orders[key]))

            # if we need to create a buy order
            if key[-1] == OrderSide.BUY:
                self._mm_orders[key] -= PROFIT_MARGIN

                # if have to spend more than available cash, delete that order
                if self._mm_orders[key] > cash_avail:
                    to_del.append(key)

                # otherwise adjust cash available
                else:
                    cash_avail -= self._mm_orders[key]

            # if we need to create a sell order
            else:
                self._mm_orders[key] += PROFIT_MARGIN

        for key in to_del:
            del self._mm_orders[key]

    def get_potential_performance(self, orders: List[Order]):
        """
        Returns the portfolio performance if the given list of orders is
        executed. The performance as per the following formula: Performance
        = ExpectedPayoff - b * PayoffVariance, where b is the penalty for
        risk.
        :param orders      : list of orders to be simulated on portfolio
        :return performance: percentage increase in portfolio performance
        """

        cash = self._cash_settled
        units = self._asset_units.copy()

        # simulate list of orders executing
        for order in orders:
            # for a buy order that exists in the market, we sell to it
            if order.order_side == OrderSide.BUY:
                cash += order.price
                units[order.market.item] -= 1

            # for a sell order, we buy from it
            else:
                cash -= order.price
                units[order.market.item] += 1

        x = list(units.values())

        variance = self._get_portfolio_variance(x)

        performance = self._portfolio_performance(
            self._get_expected_return(x, cash),
            self._risk_penalty,
            variance)

        return performance

    def _sell_notes(self):
        """
        Determines if current cash level is below arbitrary threshold,
        if it yes, sells notes at a small loss
        :return:
        """
        # stop if initialising OR if have enough cash
        if len(self._asset_units.keys()) == 0 or \
                self._cash_available > MIN_CASH_THRESHOLD:
            return

        # find the note key
        note_key = ""
        for asset in self._asset_units:
            if asset.lower() == "note":
                note_key = asset

        # check if have notes available to short
        if self._asset_units[note_key] > self._short_units_allowed[note_key]:
            self.inform(f"Cash avail: {self._cash_available}")
            self.inform(f"Selling notes+++++++++++++++++++++++++++")

            # create note sell orders for some price to obtain quick cash
            market = Market(self._market_ids[note_key])
            price_tick = market.price_tick
            new_order = Order.create_new()
            new_order.price = NOTE_SELLING_PRICE - \
                              (NOTE_SELLING_PRICE % price_tick)
            new_order.market = market
            new_order.units = 1
            new_order.order_side = OrderSide.SELL
            new_order.order_type = OrderType.LIMIT

            new_order.ref = "Order need_cash - SM"

            self._waiting = True
            self._order_id += 1
            self._num_orders_sent += 1
            self.send_order(new_order)

    def _cancel_my_orders(self):
        """
        Cancels all of my orders in the market
        """
        for _, order in Order.current().items():

            # if I have an active order, cancel it UNLESS
            if order.mine and not self._waiting:
                self._waiting = True
                cancel_order = copy.copy(order)
                cancel_order.order_type = OrderType.CANCEL
                cancel_order.ref = f"Cancel - {order.ref} - SM"
                self.send_order(cancel_order)
                self._waiting = False

    @staticmethod
    def _portfolio_performance(exp_return, risk_penalty, variance):
        """
        Calculates portfolio performance based on the risk preference
        :param exp_return   : expected payoff / return of portfolio
        :param risk_penalty : risk preference parameter
        :param variance     : variance of the portfolio
        :return             : score/utility for performance
        """
        return exp_return - risk_penalty * variance

    def _get_expected_return(self, units, cash):
        """
        Calculates expected return of a portfolio given units and
        available cash
        :param units: vector of units in some portfolio
        :param cash : available cash
        :return     : exp. return of portfolio based on diff. state payoffs
        """
        x = list(self._payoffs.values())

        return (sum(np.dot(np.dot(1 / (len(x)),
                                  units), x)) + cash) / CENTS_IN_DOLLAR

    def _get_portfolio_variance(self, units):
        """
        Calculates variance (scalar) of portfolio given units vector and stored
        payoff values

        Portfolio variance = W . Covar Matrix . Wt
        Where W is vector of units, Wt is W transpose

        :param units: vector of weights of portfolio
        :return     : scalar variance of the portfolio
        """
        weights = np.array(units)
        covar_matrix = np.dot(1 / (CENTS_IN_DOLLAR ** 2),
                              np.cov(list(self._payoffs.values()), bias=True))
        return np.dot(np.dot(weights, covar_matrix),
                      weights.transpose())

    @staticmethod
    def _get_best_bid_ask():
        """
        Walks the order book and determines what the best bid and asks are
        for each market
        :return     : dictionaries of best bid and ask orders for each
                        market
        """
        VERY_HIGH_ASK = 999999
        VERY_LOW_BID = -1

        # track best bid_ask prices and orders
        # key - market, value - [best price, best price order]
        best_bids = {'a': [VERY_LOW_BID, None], 'b': [VERY_LOW_BID, None],
                     'c': [VERY_LOW_BID, None], 'note': [VERY_LOW_BID, None]}
        best_asks = {'a': [VERY_HIGH_ASK, None], 'b': [VERY_HIGH_ASK, None],
                     'c': [VERY_HIGH_ASK, None], 'note': [VERY_HIGH_ASK, None]}

        # track current best bids and asks
        for order_id, order in Order.current().items():

            dict_key = order.market.item.lower()

            if order.order_side == OrderSide.BUY:
                if order.price > best_bids[dict_key][0]:
                    best_bids[dict_key][0] = order.price
                    best_bids[dict_key][1] = order
            else:
                if order.price < best_asks[dict_key][0]:
                    best_asks[dict_key][0] = order.price
                    best_asks[dict_key][1] = order

        return best_bids, best_asks

    def _reactive_strategy(self):
        """
        REACTIVE STRATEGY
        =================
        Generates combinations of profitable orders currently in the order book
        Called every 3 seconds periodically
        sets reactive_orders attribute to a list of orders to be executed

        :return: Returns True if portfolio is currently optimal & no reactive
                    orders were executed
        """

        portfolio_currently_optimal = True

        # do nothing if sending through orders
        if self._waiting:
            return

        bids, asks = self._get_best_bid_ask()

        # filter out when there is NO order in the bid side / ask side
        bids = [x[1] for x in list(bids.values()) if x[1] is not None]
        asks = [x[1] for x in list(asks.values()) if x[1] is not None]

        orders = bids + asks

        # initially no valid orders
        self._reactive_orders = None

        # generate combinations of possible orders to be executed
        # when first order that is good enough is found, stop looking
        for i in range(1, len(orders) + 1):

            combs = list(itertools.combinations(orders, i))
            new_set = filter(self._duplicates_in_list, combs)

            if not self.is_portfolio_optimal(new_set):
                portfolio_currently_optimal = False
                break

        # if there are profitable orders, send them through
        if not portfolio_currently_optimal and not self._waiting:
            self._waiting = True
            self._send_orders(self._reactive_orders)
            self._num_orders_sent += len(self._reactive_orders)
            self._reactive_orders = None

        return portfolio_currently_optimal

    def is_portfolio_optimal(self, new_set):
        """
        Returns true if the current holdings are optimal (as per the
        performance formula), false otherwise.
        :new_set: a set of orders to be tested

        :return: Returns true if given set(orders) will not improve performance
        """
        # for each order in this set, test if profitable
        for order_set in new_set:

            if self._is_bot_reactive():
                list_orders = list(order_set)
            else:
                list_orders = [order_set]

            # self.inform(f"Order set: {list_orders}")
            # check if have enough cash/units for order_set
            if self.check_if_enough_assets(list_orders):

                # check if performance of order_set > current performance
                performance = self.get_potential_performance(list_orders)

                # market maker bot
                if self._is_bot_mm():

                    # change order side to the action WE will be taking
                    if list_orders[0].order_side == OrderSide.BUY:
                        os = OrderSide.SELL
                    else:
                        os = OrderSide.BUY

                    key = (list_orders[0].market.item,
                           os)
                    self._mm_orders[key] = performance

                # reactive bot
                else:
                    if performance > self._aggressiveness_param * \
                            self._current_performance:

                        # when the first profitable order set found, stop
                        self._reactive_orders = list_orders

                        return False

        return True

    def check_if_enough_assets(self, orders: List[Order]):
        """
        Received orders are the orders in the market! so for a buy order,
        we sell to it, and for a sell order, we buy from it
        :param orders: Order set received
        :return      : True if there are enough assets to execute each order
                        in the order set received
        """
        to_spend = 0

        # orders are the PRESENT orders in the market
        for order in orders:

            if order.order_side == OrderSide.SELL:
                to_spend += order.price

            else:

                # if reached the shorting quota, then invalid order set
                if self._asset_units[order.market.item] == \
                        self._short_units_allowed[order.market.item]:
                    return False

        # if not enough cash to buy, then invalid order set
        if to_spend > self._cash_available:
            return False

        return True

    def _send_orders(self, orders):
        """
        Creates *corresponding* orders to the list of orders received
        :param orders: list of favourable orders
        """

        if not self.is_session_active():
            return

        # REACTIVE ORDERS
        for order in orders:

            price_tick = order.market.price_tick

            new_order = Order.create_new()
            new_order.price = order.price - (order.price % price_tick)
            new_order.market = order.market
            new_order.units = 1

            if order.order_side == OrderSide.BUY:
                new_order.order_side = OrderSide.SELL
            else:
                new_order.order_side = OrderSide.BUY

                # don't send invalid orders, kill switch for edge cases
                if new_order.price > self._cash_available:
                    return

            new_order.order_type = OrderType.LIMIT
            new_order.ref = f"Order {self._order_id} - SM"
            self._order_id += 1
            self.send_order(new_order)

    @staticmethod
    def _duplicates_in_list(list_of_orders):
        """
        Receives a list of orders and determines if those orders exist in the
        same market
        :param list_of_orders: list of 8 best bid and asks from the 4 markets
        :return              : True if orders list contains order in the same
                                market.
        """
        list_of_orders = [x.market for x in list_of_orders]

        return len(set(list_of_orders)) == len(list_of_orders)

    def order_accepted(self, order):
        """
        If sent order accepted by server, inform user of the reason and order
        Tracks number of orders sent to server not yet accepted/rejected
        :param order: The accepted order
        :return:
        """
        # make sure that all orders are accepted, till then keep
        # waiting for server
        if not order.order_type == OrderType.CANCEL:
            self._num_orders_sent -= 1

        if self._num_orders_sent == 0:
            self._waiting = False

    def order_rejected(self, info, order):
        """
        If sent order rejected by server, inform user of the reason and order
        :param info: Info object sent by FM regarding rejection reason
        :param order: The rejected order
        """
        pass

    def received_orders(self, orders: List[Order]):
        pass

    def received_session_info(self, session: Session):
        """
        Called when session info updates
        :param session: Session object sent by FlexeMarkets
        :return:
        """
        # at every session update, reset valid instance vars
        self._reactive_orders = None
        self._waiting = False
        self._order_id = 0
        self._num_orders_sent = 0

        self._mm_orders = {}
        self._num_active_mm_orders = 0

    def pre_start_tasks(self):
        pass

    def received_holdings(self, holdings):
        """
        Called when holdings update
        Tracks current bot's expected payoff, variance and current
        performance
        :param holdings: Holdings object sent by FlexeMarkets
        """
        # have to assume here that assets are arranged here in the same
        # order as the order in which payoffs were received
        self._cash_available = holdings.cash_available
        self._cash_settled = holdings.cash

        self._asset_units = {}
        for market in holdings.assets:
            key = market.item
            self._asset_units[key] = holdings.assets[market].units
            self._short_units_allowed[key] = \
                -1 * holdings.assets[market].units_granted_short

        # update portfolio variance - don't need to update everytime
        # but doing it in case "new info" arrives
        self._current_port_variance = self._get_portfolio_variance(
            list(self._asset_units.values()))

        # update portfolio return
        # return is based on SETTLED cash, and not on cash available
        self._current_exp_return = \
            self._get_expected_return(list(self._asset_units.values()),
                                      self._cash_settled)

        # update current performance
        self._current_performance = self._portfolio_performance(
            self._current_exp_return,
            self._risk_penalty,
            self._current_port_variance)


if __name__ == "__main__":
    FM_ACCOUNT = "ardent-founder"
    FM_EMAIL = "s.mann4@student.unimelb.edu.au"
    FM_PASSWORD = "921322"
    MARKETPLACE_ID = 1054  # replace this with the marketplace id

    # risk penalty based on my student ID
    bot = CAPMBot(FM_ACCOUNT, FM_EMAIL, FM_PASSWORD, MARKETPLACE_ID,
                  risk_penalty=0.007)
    bot.run()
