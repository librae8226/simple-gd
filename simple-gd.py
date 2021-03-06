import datetime
import calendar
import json
import collections
import pandas as pd
from scipy.stats import norm

# Retrieve N months of history data before starting date
N = 12*5
POOL = [
    # in basket
    '002415.XSHE', # 海康威视
    '600422.XSHG', # 昆药集团
    '600594.XSHG', # 益佰制药
    '601633.XSHG', # 长城汽车
    # target
    #'600887.XSHG', # 伊利股份
    '600104.XSHG', # 上汽集团
    #'000651.XSHE', # 格力电器
    #'601668.XSHG', # 中国建筑
    #'600690.XSHG', # 青岛海尔
    '600048.XSHG', # 保利地产
    #'600030.XSHG', # 中信证券
    #'601318.XSHG', # 中国平安
    '601222.XSHG', # 林洋
    #'000895.XSHE', # 双汇
    #'000538.XSHE', # 云南白药
    '002241.XSHE', # 歌尔声学
    #'601231.XSHG', # 环旭电子
    '601877.XSHG', # 正泰电器
    #'600332.XSHG', # 白云山
    #'000963.XSHE', # 华东医药
    #'600177.XSHG', # 雅戈尔
    '600315.XSHG', # 上海家化
    '600066.XSHG', # 宇通客车
]

POOL_watch = [
    # watch
    '000826.XSHE', # 启迪桑德
    '000590.XSHE', # 启迪古汉
]

POOL_test = [
    '601222.XSHG', # 林洋
]

def get_last_quarters(date):
    """
    Get last 4 quarters, including year index and quarter index.
    """
    #quarter = (date.month-1)//3 + 1
    quarter = (date.month-1)//3
    y = range(0, 5)
    q = range(0, 5)
    for i in range(1, 5):
        q[i] = quarter - (4 - i)
        if q[i] <= 0:
            q[i] = q[i] + 4
            y[i] = date.year - 1
        else:
            y[i] = date.year
    return y, q

def get_month_day_range(date):
    """
    For a date 'date' returns the start and end date for the month of 'date'.

    Month with 31 days:
    >>> date = datetime.date(2011, 7, 27)
    >>> get_month_day_range(date)
    (datetime.date(2011, 7, 1), datetime.date(2011, 7, 31))

    Month with 28 days:
    >>> date = datetime.date(2011, 2, 15)
    >>> get_month_day_range(date)
    (datetime.date(2011, 2, 1), datetime.date(2011, 2, 28))
    """
    first_day = date.replace(day = 1)
    last_day = date.replace(day = calendar.monthrange(date.year, date.month)[1])
    return first_day, last_day

def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = int(sourcedate.year + month / 12 )
    month = month % 12 + 1
    day = min(sourcedate.day,calendar.monthrange(year,month)[1])
    return datetime.datetime(year,month,day)

def estimation_formula_bg_dynamic(growth, eps, pe):
    """
    BG formula, integrate with the normal pe (based on Gaussian Distribution)
    """
    return (2*growth+pe)*eps

def estimation_formula_bg(growth, eps):
    """
    The stock price estimation formula suggested by Benjamin Graham
    According to "The Intelligent Investor"
    """
    return (2*growth+8.5)*eps

# growth rate in N years
NYG = 3
def est(security, date, pe_mu=8.5, pe_std=0):
    """
    """
    np = []
    delta = 0
    # collect net profit in last NYG years, and work out a average growth rate
    for i in range(0, NYG+1):
        d = add_months(date, -i*12)
        tmp_np = get_net_profit(security, d)
        if math.isnan(tmp_np):
            date = add_months(date, -3)
            d = add_months(date, -i*12)
            np.append(get_net_profit(security, d))
        else:
            np.append(tmp_np)
        #log.debug("%s np: %.2f", d.strftime("%Y-%m-%d"), np[i])
        if i != 0:
            delta += (np[i-1] - np[i])/np[i]
            #log.debug("%s growth: %.2f", add_months(date, -(i-1)*12).strftime("%Y-%m-%d"), (np[i-1] - np[i])/np[i])
    growth = delta/NYG

    eps = 0
    cap = 1
    # collect average eps in last NYG years
    for i in range(0, NYG):
        d = add_months(date, -i*12)
        factor = 1
        df = get_fundamentals(query(
            valuation.code,
            valuation.capitalization
        ).filter(
            valuation.code == security
        ), date = d.strftime("%Y-%m-%d"))
        if i == 0:
            cap = float(df['capitalization'])
        else:
            factor = float(df['capitalization'])/cap
        e = get_eps(security, d)*factor
        #log.debug("%d %s cap: %d, factor: %f, eps: %.2f", i, d.strftime("%Y-%m-%d"), df['capitalization'], factor, e)
        eps = eps + e
    eps = eps/NYG

    log.info("growth: %.4f, eps: %.2f", growth, eps)
    est = estimation_formula_bg(growth, eps)
    est_left = estimation_formula_bg_dynamic(growth, eps, pe_mu-pe_std)
    est_centrum = estimation_formula_bg_dynamic(growth, eps, pe_mu)
    est_right = estimation_formula_bg_dynamic(growth, eps, pe_mu+pe_std)
    return est, est_left, est_centrum, est_right

def get_net_profit(security, date):
    """
    """
    np = 0
    y, q = get_last_quarters(date)
    res = query(
        valuation.code, income.net_profit
        ).filter(
        valuation.code == security
    )
    for i in range(1, 5):
        ret = get_fundamentals(res, statDate=str(y[i])+'q'+str(q[i]))
        #log.info(ret)
        np += ret['net_profit'].mean()
        #log.debug("%dq%d %d/4 np: %.2f", y[i], q[i], i, ret['net_profit'].mean())
    return np

def get_eps(security, date):
    """
    """
    y, q = get_last_quarters(date)
    res = query(
            valuation.code,
            valuation.capitalization,
            income.net_profit
        ).filter(
        valuation.code == security
    )
    np = 0
    cap = 0
    for i in range(1, 5):
        ret = get_fundamentals(res, statDate=str(y[i])+'q'+str(q[i]))
        np += ret['net_profit'].mean();
        #log.info(ret)
        #e += ret['basic_eps'].mean()
        #e += ret['diluted_eps'].mean()
        #log.debug("%dq%d 1/4 eps: %.2f", y[i], q[i], ret['basic_eps'].mean())
        #log.debug("%dq%d 1/4 net profit: %d cap: %d", y[i], q[i], ret['net_profit'].mean(), ret['capitalization'])
        if i == 4:
            cap = ret['capitalization']*10000
    eps = float(np) / cap
    return eps

def get_pe_in_period(security, start, end):
    ''' old eps calc
    df = get_price(
        security,
        start_date = start.strftime("%Y-%m-%d"),
        end_date = end.strftime("%Y-%m-%d"),
        frequency = 'daily',
        fields = ['close', 'factor'])
    close = df['close']/df['factor']
    p = close.mean()
    #log.info('price mean: %f', p)
    '''
    df = get_fundamentals(query(
                valuation.market_cap,
                valuation.capitalization,
                valuation.pe_ratio
            ).filter(
                valuation.code == security
            ), date = end.strftime("%Y-%m-%d"))
    #p = df['market_cap']
    #log.debug('<%s> market_cap: %f', end.strftime("%Y-%m-%d"), p)
    #log.debug('<%s> cap: %d', end.strftime("%Y-%m-%d"), int(df['capitalization']))

    pe = float(df['pe_ratio'])

    ''' old eps calc
    e = get_eps(security, end)
    '''
    ''' old net profit, pe calc
    e = get_net_profit(security, end)
    if math.isnan(e):
        #log.warn("get_pe_in_period, e is nan!")
        pass

    pe = round(p*10000*10000/e, 2)
    log.debug('P/E Ratio of %s at %s: %.2f', security, end.strftime("%Y-%m"), pe)
    '''
    #log.debug('P/E Ratio of %s at %s: %.2f', security, end.strftime("%Y-%m"), pe)
    return pe

def gd_init(context):
    """
    Gaussian Distribution
    """
    #log.debug('gd_init: in')

    curr = context.current_dt
    date = add_months(curr, -N)
    while True:
        first, last = get_month_day_range(date)
        #datestr = last.strftime("%Y-%m-%d")
        #log.info(datestr)
        if last > curr:
            #log.debug('gd_init: break')
            break
        for security in g.pool:
            #log.info(security)

            # we need to get eps of last 4 quaters
            # so it is necessary to ensure this security is valid then
            tmp = get_fundamentals(query(
                valuation.market_cap
            ).filter(
                valuation.code == security
            ), add_months(first, -12).strftime("%Y-%m-%d"))
            if tmp['market_cap'].empty == True:
                #print 'security invalid!'
                continue
            else:
                #print tmp['market_cap'].mean()
                pass
            pe = get_pe_in_period(security, first, last)
            if math.isnan(pe) == False:
                g.security_gd_pe[g.pool.index(security)][last.strftime("%Y-%m-%d")] = pe

        date = add_months(date, +1)
    '''
    for security in g.pool:
        j = g.security_gd_pe[g.pool.index(security)]
        j = collections.OrderedDict(sorted(j.items()))
        log.info('%d entries for %s within %s~%s', len(j), security, j.keys()[0], j.keys()[-1])
        for k in range(0, len(j)):
            print '<' + security + '> ' + j.keys()[k] + ': ' + str(j.values()[k])
            pass
        # save to .json and .csv for future use
        file = str('data/' + security + '.json')
        print 'write to ' + file
        write_file(file, json.dumps(j, sort_keys=True), append=False)
        df_from_dict = pd.DataFrame(j.items(), columns = ['date', 'pe'])
        file = str('data/' + security + '.csv')
        print 'write to ' + file
        write_file(file, df_from_dict.to_csv(), append=False)
    '''
    #log.debug('gd_init: out')

def gd_update(context, security):
    curr = context.current_dt
    first, last = get_month_day_range(curr)
    pe = get_pe_in_period(security, first, last)
    if math.isnan(pe) == False:
        g.security_gd_pe[g.pool.index(security)][last.strftime("%Y-%m-%d")] = pe

    ''' update file '''
    #for security in g.pool:
    j = g.security_gd_pe[g.pool.index(security)]
    j = collections.OrderedDict(sorted(j.items()))
    #log.info('%d entries for %s within %s~%s', len(j), security, j.keys()[0], j.keys()[-1])
    for k in range(0, len(j)):
        #print '<' + security + '> ' + j.keys()[k] + ': ' + str(j.values()[k])
        pass
    # save to .json and .csv for future use
    file = str('data/' + security + '.json')
    #print 'write to ' + file
    write_file(file, json.dumps(j, sort_keys=True), append=False)
    df_from_dict = pd.DataFrame(j.items(), columns = ['date', 'pe'])
    file = str('data/' + security + '.csv')
    #print 'write to ' + file
    write_file(file, df_from_dict.to_csv(), append=False)

    '''
    q = query(
        valuation.code, valuation.day, income.statDate, valuation.pe_ratio, valuation.pb_ratio, income.basic_eps
    ).filter(
        valuation.code == security
    )
    rets = [get_fundamentals(q, statDate='2014q'+str(i)) for i in range(1, 5)]
    print rets
    '''

    '''
    for i in range(1, months):
        df = get_fundamentals(query(
                valuation.code, valuation.pe_ratio, valuation.pb_ratio, income.basic_eps
            ).filter(
                valuation.code == security
            ), date = (curr + timedelta(-i*365/12)))
        log.info("%s %f %f %f", df.valuation)
    '''

def gd_pe_get_mu_std(security):
    j = g.security_gd_pe[g.pool.index(security)]
    x_data = j.values()
    #x_data.sort()
    mu, std = norm.fit(x_data)
    return mu, std

def on_month_end(context):
    date = context.current_dt
    log.debug('on_month_end: ' + str(date) + '\r\n')
    for security in g.pool:
        log.info('[%s %s]', security, get_security_info(security).display_name)

        # update
        gd_update(context, security);

        # p/e ratio
        df = get_price(
            security,
            start_date = date.strftime("%Y-%m-%d"),
            end_date = date.strftime("%Y-%m-%d"),
            frequency = 'daily',
            fields = ['close', 'factor'])
        close = df['close']/df['factor']
        close = close.mean()
        ''' old calc
        e = get_eps(security, date)
        if math.isnan(e):
            e = get_eps(security, add_months(date, -3))
        pe = round(close/e, 2)
        '''
        pe = get_pe_in_period(security, date, date)
        log.info('p/e ratio: %.2f @ price: %.2f', pe, close)

        # get p/e array mu and std
        mu, std = gd_pe_get_mu_std(security)
        log.info('p/e ratio mu: %.2f, std: %.2f', mu, std)

        # estimation
        est_value, est_left, est_centrum, est_right = est(security, date, mu, std)
        log.info('estimated value: %.2f', est_value)
        log.info('dynamic est: %.2f~%.2f~%.2f', est_left, est_centrum, est_right)
        log.info('range from left: %.2f%%', (close-est_left)/est_left*100.0)
        log.info('position: %.2f%%', (close-est_left)/(est_right-est_left)*100.0)
        log.info('----------------------------------------')

def initialize(context):
    g.pool = POOL
    log.debug(g.pool)
    log.debug("initialize: amount of securities: %d", len(g.pool))

    g.security_gd_pe = range(0, len(g.pool))
    for security in g.pool:
        # e.g.
        # [
        #   {
        #     "2012-09-31": 11.13, # timestamp: pe
        #     "2012-10-31": 12.19,
        #     ...
        #   }
        # ],
        # [
        #   {},
        # ], ...
        g.security_gd_pe[g.pool.index(security)] = {}

    gd_init(context)

    set_universe(g.pool)
    set_commission(PerTrade(buy_cost=0.0025, sell_cost=0.0025, min_cost=5))

    run_monthly(on_month_end, -1, time='after_close')

def before_trading_start(context):
    pass

def after_trading_end(context):
    date = context.current_dt
    for security in g.pool:
        pass
    return

def handle_data(context, data):
    cash = context.portfolio.cash
    value = context.portfolio.portfolio_value
    for security in g.pool:
        record(price=data[security].close, m50=data[security].mavg(50))
        pass
    return

    '''
    for security in g.pool:
        average_price_5d = data[security].mavg(5)
        average_price_10d = data[security].mavg(10)
        average_price_10w = data[security].mavg(50)
        average_price_20w = data[security].mavg(100)
        average_price_30w = data[security].mavg(150)
        current_price = data[security].price
        cash = context.portfolio.cash
        value = context.portfolio.portfolio_value
        amount = context.portfolio.positions[security].amount
        buy_price = average_price_10w
        buy_amount = int((0.05*value)/current_price)
        sell_price = 1.05*average_price_10w
        sell_amount = 0.5*amount

        if current_price < buy_price:
            if buy_amount > 0:
                order(security, +buy_amount)
                log.info("Buying %s %d", security, buy_amount)
        elif current_price > sell_price and amount > 0:
            order(security, -sell_amount)
            log.info("Selling %s %d", security, sell_amount)

        record(stock_price=data[security].price, average_price_10w=data[security].mavg(50))
    '''
