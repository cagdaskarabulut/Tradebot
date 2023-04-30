

'''
def main_page_values(request):
    news_list = News.objects.all()

    paginator = Paginator(news_list, 9)
    page = request.GET.get('page')
    news = paginator.get_page(page)

    announcement_list = Announcement.objects.all()
    slider_list = News.objects.order_by('-id').exclude(image__isnull=True).exclude(image__exact='')[:10]
    values = {'news_list': news, ,'announcement_list': announcement_list, 'slider_list': slider_list}
    return values

def mainPage(request):
    return render(request, 'trade/index.html', main_page_values(request))
'''
########### 
'''
def Test_Karalama():
    #buyWithMarketPriceByTotalPriceAction('SOL','USDT',15,False) #for manuel buy
    #param interval example: 30m, 1h, 1d, 1w, 1M
    
    # get balances for all assets & some account information
    print(client.get_account())

    # get balance for a specific asset only (BTC)
    print(client.get_asset_balance(asset='BTC'))

    # get balances for futures account
    print(client.futures_account_balance())

    btc_price = client.get_symbol_ticker(symbol='BTCUSDT')
    return ''


def Test_stopLossOrder():
    try:
        order = client.create_oco_order(
            symbol='ETHUSDT',
            side='SELL',
            quantity=100,
            price=250,
            stopPrice=150,
            stopLimitPrice=150,
            stopLimitTimeInForce='GTC')
    except BinanceAPIException as e:
        # error handling goes here
        print(e)
    except BinanceOrderException as e:
        # error handling goes here
        print(e)
    return '''
