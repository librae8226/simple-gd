import datetime
import calendar

def get_last_quarters(date):
    """
    Get last 4 quarters, including year index and quarter index.
    """
    quarter = (date.month-1)//3 + 1
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

def gd_init(context):
    """
    Gaussian Distribution
    """
    log.info('gd_init: in')

    curr = context.current_dt
    date = add_months(curr, -1)
    first, date = get_month_day_range(date)
    while True:
        datestr = first.strftime("%Y-%m-%d")
        log.info(datestr)
        first, date = get_month_day_range(date)
        if date > curr:
            log.info('gd_init: break')
            break
        for security in g.pool:
            log.info(security)
            df = get_price(
                security,
                start_date=first.strftime("%Y-%m-%d"),
                end_date= date.strftime("%Y-%m-%d"),
                frequency='daily',
                fields=['close', 'factor'])
            #log.info(df)
            #log.info(df['close'])
            #log.info('mean: %f', df['close'].mean())
            #p = (df['close'].mean/df['factor'][-1])
            p = df['close'].mean
            e = 0
            y, q = get_last_quarters(date)
            log.info("last quarter1: %dq%d", y[1], q[1])
            log.info("last quarter2: %dq%d", y[2], q[2])
            log.info("last quarter3: %dq%d", y[3], q[3])
            log.info("last quarter4: %dq%d", y[4], q[4])
            res = query(
                valuation.code, valuation.day, income.statDate, valuation.pe_ratio, valuation.pb_ratio, income.basic_eps
                ).filter(
                valuation.code == security
            )
            for i in range(1, 5):
                ret = get_fundamentals(res, statDate=str(y[i])+'q'+str(q[i]))
                log.info(ret)
                e += ret['basic_eps']
                log.info("1/4 eps: %f", e)

            log.info("eps: %f", e)
            #g.security_gd_pe[security].append(p/e)

        date = add_months(date, +1)

    log.info('gd_init: out')

def gd_update(context, security):
    curr = context.current_dt
    pass

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
    g.pool = [
        '600030.XSHG', # 中信证券
        '600887.XSHG', # 伊利股份
        '600104.XSHG', # 上汽集团
        '600594.XSHG', # 益佰制药
        '601668.XSHG', # 中国建筑
        '600690.XSHG', # 青岛海尔
        '600048.XSHG', # 保利地产
    ]
    log.info(g.pool)
    log.info("initialize: amount of securities: %d", len(g.pool))

    g.security_gd_pe = range(0, len(g.pool))

    gd_init(context)

    set_universe(g.pool)
    set_commission(PerTrade(buy_cost=0.0025, sell_cost=0.0025, min_cost=5))

    run_monthly(on_month_end, 0, time='after_close')

def before_trading_start(context):
    pass

def after_trading_end(context):
    pass

# 每个单位时间(如果按天回测,则每天调用一次,如果按分钟,则每分钟调用一次)调用一次
def handle_data(context, data):
    pass
    return
    for security in g.pool:
        average_price_5d = data[security].mavg(5)
        average_price_10d = data[security].mavg(10)
        average_price_10w = data[security].mavg(50)
        average_price_20w = data[security].mavg(100)
        average_price_30w = data[security].mavg(150)
        current_price = data[security].price
        # 取得当前的现金
        cash = context.portfolio.cash
        value = context.portfolio.portfolio_value
        amount = context.portfolio.positions[security].amount
        buy_price = average_price_10w
        buy_amount = int((0.05*value)/current_price)
        sell_price = 1.05*average_price_10w
        sell_amount = 0.5*amount

        if current_price < buy_price:
            # 购买量大于0时，下单
            if buy_amount > 0:
                # 买入股票
                order(security, +buy_amount)
                # 记录这次买入
                log.info("Buying %s %d", security, buy_amount)
        elif current_price > sell_price and amount > 0:
            order(security, -sell_amount)
            # 记录这次卖出
            log.info("Selling %s %d", security, sell_amount)

        record(stock_price=data[security].price, average_price_10w=data[security].mavg(50))

