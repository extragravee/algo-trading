"""
FNCE30010 - Algorithmic Trading
Assignment 2 - CAPM
Sidakpreet Mann
921322

Notes:
    1. Covar matrix is calculated only initially, as it's known
"""
import itertools
from typing import List
import numpy as np
from fmclient import Agent, Session
from fmclient import Order, OrderSide, OrderType

# Submission details
SUBMISSION = {"number": "921322", "name": "Sidakpreet Mann"}

# CONSTANTS
CENTS_IN_DOLLAR = 100
VERY_HIGH_ASK = 999999


class CAPMBot(Agent):

    def __init__(self, account, email, password, marketplace_id,
            risk_penalty=0.001, session_time=20):
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

        self._asset_units = []
        self._cash_available = 0
        self._cash_settled = 0
        self._current_port_variance = 0
        self._current_exp_return = 0
        self._current_performance = 0

    def initialised(self):
        # Extract payoff distribution for each security
        for market_id, market_info in self.markets.items():
            # store market id for each item -- see if it's more efficient to
            # also store the Market() objects here
            # instead of creating them every time a new order is needed
            self._market_ids[market_info.item] = market_id

            security = market_info.item
            description = market_info.description
            self._payoffs[security] = [int(a) for a in description.split(",")]

        self.inform(f"Market IDs: {self._market_ids}")
        self.inform(f"Payoffs   : {self._payoffs}")

    @staticmethod
    # this shouldn't really exist, just use this in the potential
    # performance function
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
        :param units: vector of weights of portfolio
        :return     : scalar variance of the portfolio
        """
        weights = np.array(units)
        covar_matrix = np.dot(1 / (CENTS_IN_DOLLAR ** 2),
                              np.cov(list(self._payoffs.values()), bias=True))
        return np.dot(np.dot(weights, covar_matrix),
                      weights.transpose())

    def _get_best_bid_ask(self):
        """
        Walks the order book and determines what the best bid and asks are
        for each market
        :return     : dictionaries of best bid and ask orders for each
                        market
        """

        # track best bid_ask prices and orders
        # key - market, value - [best price, best price order]
        best_bids = {'A': [-1, None], 'B': [-1, None],
                     'C': [-1, None], 'note': [-1, None]}
        best_asks = {'A': [VERY_HIGH_ASK, None], 'B': [VERY_HIGH_ASK, None],
                     'C': [VERY_HIGH_ASK, None], 'note': [VERY_HIGH_ASK, None]}

        # track current best bids and asks
        for order_id, order in Order.current().items():
            # self.inform(order)
            # self.inform(order.market.item)

            if order.order_side == OrderSide.BUY:
                if order.price > best_bids[order.market.item][0]:
                    best_bids[order.market.item][0] = order.price
                    best_bids[order.market.item][1] = order
            else:
                if order.price < best_asks[order.market.item][0]:
                    best_asks[order.market.item][0] = order.price
                    best_asks[order.market.item][1] = order

        return best_bids, best_asks

    def _generate_combinations_potential_orders(self):

        bids, asks = self._get_best_bid_ask()

        # filter out when there is NO order in the bid side / ask side
        bids = [x[1] for x in list(bids.values()) if x[1] is not None]
        asks = [x[1] for x in list(asks.values()) if x[1] is not None]

        orders = bids + asks
        self.inform("Best bid and asks: ")
        self.inform(f"Orders: {orders}")

        valid_combinations = []

        # in case there is only one valid trade-able order
        if len(orders) == 1:
            valid_combinations = orders

        # generate combinations of possible orders to be executed
        for i in range(1, len(orders)):
            combs = list(itertools.combinations(orders, i))

            # filter out order combinations where bid and ask is from
            # the same market
            for comb in combs:
                if not self._duplicates_in_list(comb):
                    valid_combinations.append(comb)

        # scaffolding
        self.inform(f"Valid combinations: ")
        for z in valid_combinations:
            self.inform(z)

        # now that valid combinations are being generated, they need to be
        # simulated for potential change in performance
        return valid_combinations

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

        return len(set(list_of_orders)) < len(list_of_orders)

    def get_potential_performance(self, orders):
        """
        Returns the portfolio performance if the given list of orders is
        executed. The performance as per the following formula: Performance
        = ExpectedPayoff - b * PayoffVariance, where b is the penalty for
        risk. :param orders: list of orders :return:
        """
        pass

    def is_portfolio_optimal(self):
        """
        Returns true if the current holdings are optimal (as per the
        performance formula), false otherwise. :return:
        """
        pass

    def order_accepted(self, order):
        pass

    def order_rejected(self, info, order):
        pass

    def received_orders(self, orders: List[Order]):
        # seems to be called before received holdings, so don't calculate
        # the portfolio variance here! As this has old number of units
        # self.inform(f"{self._get_best_bid_ask()}")
        self._generate_combinations_potential_orders()

    def received_session_info(self, session: Session):
        pass

    def pre_start_tasks(self):
        pass

    def received_holdings(self, holdings):

        # have to assume here that assets are arranged here in the same
        # order as the order in which payoffs were received

        self._cash_available = holdings.cash_available
        self._cash_settled = holdings.cash

        self._asset_units = []
        for market in holdings.assets:
            self._asset_units.append(holdings.assets[market].units)

        # update portfolio variance
        self._current_port_variance = self._get_portfolio_variance(
            self._asset_units)

        # update portfolio return
        # return is based on SETTLED cash, and not on cash available
        self._current_exp_return = \
            self._get_expected_return(self._asset_units,
                                      self._cash_settled)

        # update current performance
        self._current_performance = self._portfolio_performance(
            self._current_exp_return,
            self._risk_penalty,
            self._current_port_variance)

        # scaffolding
        self.inform(f"=============================")
        self.inform(f"Portfolio var: {self._current_port_variance}")
        self.inform(f"Exp return   : {self._current_exp_return}")
        self.inform(f"Performance  : {self._current_performance}")


if __name__ == "__main__":
    FM_ACCOUNT = "ardent-founder"
    FM_EMAIL = "s.mann4@student.unimelb.edu.au"
    FM_PASSWORD = "921322"
    MARKETPLACE_ID = 1017  # replace this with the marketplace id

    bot = CAPMBot(FM_ACCOUNT, FM_EMAIL, FM_PASSWORD, MARKETPLACE_ID,
                  risk_penalty=0.007)
    bot.run()
