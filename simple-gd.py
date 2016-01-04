import datetime
import calendar
import json
import collections
import pandas as pd

# Retrieve N months of history data before starting date
N = 12 * 6
POOL = [
    '600030.XSHG', # 中信证券
    '600887.XSHG', # 伊利股份
    '600104.XSHG', # 上汽集团
    '600594.XSHG', # 益佰制药
    '601668.XSHG', # 中国建筑
    '600690.XSHG', # 青岛海尔
    '600048.XSHG', # 保利地产
    '601222.XSHG',
]

def get_eps(security, date):
    """
    """
    e = 0
    y, q = get_last_quarters(date)
    #log.info("last quarters: %dq%d ~ %dq%d", y[1], q[1], y[4], q[4])
    res = query(
        valuation.code, valuation.day, income.statDate, valuation.pe_ratio, valuation.pb_ratio, income.basic_eps
        ).filter(
        valuation.code == security
    )
    for i in range(1, 5):
        ret = get_fundamentals(res, statDate=str(y[i])+'q'+str(q[i]))
        #log.info(ret)
        e += ret['basic_eps']
        #log.info("%dq%d 1/4 eps: %f", y[i], q[i], e)
    #log.info("eps: %f", e)
    return e

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

def get_pe_of_period(security, start, end):
    df = get_price(
        security,
        start_date = start.strftime("%Y-%m-%d"),
        end_date = end.strftime("%Y-%m-%d"),
        frequency = 'daily',
        fields = ['close', 'factor'])
    close = df['close']/df['factor']
    p = close.mean()
    #log.info('price mean: %f', p)
    e = get_eps(security, end)
    pe = round(p/e, 2)
    #log.debug('P/E Ratio of %s at %s: %f', security, end.strftime("%Y-%m"), pe)
    return pe

def gd_init(context):
    """
    Gaussian Distribution
    """
    log.info('gd_init: in')

    curr = context.current_dt
    date = add_months(curr, -N)
    while True:
        first, last = get_month_day_range(date)
        #datestr = last.strftime("%Y-%m-%d")
        #log.info(datestr)
        if last > curr:
            log.info('gd_init: break')
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
            pe = get_pe_of_period(security, first, last)
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
    log.info('gd_init: out')

def gd_update(context, security):
    curr = context.current_dt
    first, last = get_month_day_range(curr)
    pe = get_pe_of_period(security, first, last)
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
    print 'write to ' + file
    write_file(file, json.dumps(j, sort_keys=True), append=False)
    df_from_dict = pd.DataFrame(j.items(), columns = ['date', 'pe'])
    file = str('data/' + security + '.csv')
    print 'write to ' + file
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

def gd_get_left(security):
    pass

def gd_get_right(security):
    pass

def gd_get_centrum(security):
    pass

def on_month_end(context):
    log.info('on_month_end: ' + str(context.current_dt))
    for security in g.pool:
        gd_update(context, security);
    pass

def initialize(context):
    g.pool = POOL
    log.info(g.pool)
    log.info("initialize: amount of securities: %d", len(g.pool))

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

    run_monthly(on_month_end, 0, time='after_close')

def before_trading_start(context):
    pass

def after_trading_end(context):
    pass

def handle_data(context, data):
    cash = context.portfolio.cash
    value = context.portfolio.portfolio_value
    date = context.current_dt
    for security in g.pool:
        current_price = data[security].price
        e = get_eps(security, date)
        if math.isnan(e):
            e = get_eps(security, add_months(date, -4))
        pe = round(current_price/e, 2)
        log.info('P/E Ratio of %s at %s: %f', security, date.strftime("%Y-%m-%d"), pe)

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
