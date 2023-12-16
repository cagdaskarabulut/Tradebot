from __future__ import unicode_literals
from operator import truediv
from django.shortcuts import render, reverse, HttpResponse, HttpResponseRedirect, get_object_or_404
from django.http import HttpResponseBadRequest
from trade.apps.binance.models import *; #from .models import *
from trade.apps.binance.forms import *; #from .forms import *
from django.contrib import messages
from django.contrib.auth import login,logout,authenticate
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, redirect
from django.views.generic.list import ListView
import os
from django.conf import settings
from binance.client import Client
from binance.enums import *
from binance.exceptions import BinanceAPIException, BinanceOrderException
from time import sleep
from binance import ThreadedWebsocketManager
import talib as ta
import numpy as np
from django.utils import timezone
from datetime import datetime, time, timedelta
import time as timet
import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from celery import shared_task
import sys
import xlwt
from django.http import HttpResponse
sys.setrecursionlimit(5000)
mailSubject=''
resultMail=''
boughtCoins=''
boughtCoinsTotalUsdt=0
soldCoins=''
notBoughSignalComeButNoLimit=''
nearlyBuyCoins=''
nearlySellCoins=''
api_key='NgjPWEp4U02npzVTayLPyBky9z5rV6tfEAexgtHrRnyi1kZh9oFd4KVTlh635FI1'
api_secret='03aNCJOXLebwN4aoCAR2LpgD4ARmjRUkpPTgz0NGmVbDBQriMlsuYgfq6ui53hpJ'
client=Client(api_key,api_secret)
workTimeCounter=0
workTimeDateForRSI15m=datetime.now()
workTimeDateForSavingTotalBalanceHistory=datetime.now()
workTimeDateForRSI15mWITHRealMargin=datetime.now()

def getActivePrice(firstCoin,secondCoin):
    return float(client.get_symbol_ticker(symbol=firstCoin+secondCoin)['price'])

def allMarketPairs():
    exchange_info = client.get_exchange_info()
    pairs = []
    for s in exchange_info['symbols']:
        pairs.append(s['symbol'])
    return pairs

marketPairsList=allMarketPairs()
    
def getDateFromTimestamp(last_date_draft):
    last_date_string=str(last_date_draft)
    last_date=datetime.fromtimestamp(int(last_date_string[:-5]))
    return last_date

def getStringFromDate(selectedDate):
    return selectedDate.strftime("%d/%m/%Y, %H:%M:%S")

def addOrRemoveRobotUsingUsdt(addOrRemoveUsdt):
    myPreferences=Preferences.objects.all().first()
    myPreferences.maxLimitForRobotAsUsdt=myPreferences.maxLimitForRobotAsUsdt+float(addOrRemoveUsdt)
    myPreferences.save()
    totalBalanceHistoryList=TotalBalanceHistory.objects.all()
    for item in totalBalanceHistoryList:
        item.freeUsdt=item.freeUsdt+float(addOrRemoveUsdt)
        item.robotResultHistory=myPreferences.robotResultHistoryAsUsdt
        item.save()
    return ''

def addCompletelyNewMoney(usdt,tl):
    myPreferences=Preferences.objects.all().first()
    myPreferences.maxLimitForRobotAsUsdt=myPreferences.maxLimitForRobotAsUsdt+float(usdt)
    myPreferences.commonTotalStartMoneyAsUSDT=myPreferences.commonTotalStartMoneyAsUSDT+float(usdt)
    myPreferences.commonTotalStartMoneyAsTL=myPreferences.commonTotalStartMoneyAsTL+float(tl)
    myPreferences.save()
    totalBalanceHistoryList=TotalBalanceHistory.objects.all()
    for item in totalBalanceHistoryList:
        item.freeUsdt=item.freeUsdt+float(usdt)
        item.robotResultHistory=myPreferences.robotResultHistoryAsUsdt
        item.save()
    return ''

###################################################################################################################################################################1
def getTradeListForMargin():
    return Trade.objects.filter(isMargin=True).exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS')).exclude(coin__in=Coin.objects.filter(name__startswith='BTC')).order_by('-transactionDate')

def getTradeListForMarginBTC():
    return Trade.objects.filter(isMargin=True,coin__in=Coin.objects.filter(name__startswith='BTC')).order_by('-transactionDate')

def getTradeListForRobot15m():
    return Trade.objects.filter(isMargin=False,strategy='RSI_15m').exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS')).order_by('-transactionDate')

def getTradeListForRobot15mWITHRealMargin():
    return Trade.objects.filter(isMargin=False,strategy='RSI_15m_WITHRealMargin').exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS')).order_by('-transactionDate')

def getTradeListForRobot15mSlow():
    return Trade.objects.filter(isMargin=False,strategy='RSI_15m_Slow').exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS')).order_by('-transactionDate')

def getTradeListForRobot1h():
    return Trade.objects.filter(isMargin=False,strategy='RSI_1h').exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS')).order_by('-transactionDate')

def getTradeList():
    return Trade.objects.filter(isMargin=False,strategy='RSI_4h').exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS')).order_by('-transactionDate')

def getAllTradeList():
    return Trade.objects.exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS')).order_by('-transactionDate')

def getKlines(symbol,interval,limit):
    klines=None
    try:
        klines=client.get_klines(symbol=symbol, interval=interval, limit=limit)
    except BinanceAPIException as e:
        print('getKlines',e)
    return klines

def getRSI(symbol,interval,limit):
    #print('working with : ',symbol)#HATA TESPİT => Compare karşılığı olmayan coin i tespit etmek için kullanılır
    klines=getKlines(symbol,interval,limit)
    while klines is None or len(klines)<1:  
        #print('Klines listesi bos geldi. 1dk sonra tekrar denenecek. İslem saati: ',datetime.now())
        timet.sleep(60)
        klinesNew=getKlines(symbol,interval,limit)
        klines=klinesNew
    date=[float(entry[0]) for entry in klines]
    #open=[float(entry[1]) for entry in klines]
    #high=[float(entry[2]) for entry in klines]
    #low=[float(entry[3]) for entry in klines]
    close=[float(entry[4]) for entry in klines]
    last_date=getDateFromTimestamp(date[-1])
    last_closing_price=close[-1]
    close_array=np.asarray(close)
    close_finished=close_array[:-1]
    rsi=ta.RSI(close_finished*100000000000,14)
    rsi_last=rsi[-1]
    if rsi_last==0:
        rsi_last=100
    #print(symbol,'icin ',interval,' parametresi ile RSI calistirildiginda ',rsi_last,'sonucuna ulasilmistir.','Ayrica anlik kapanis fiyati:',last_closing_price,' ve islenen tarih',last_date)
    return rsi_last

def getWilliamR(symbol,interval,limit):
    klines=getKlines(symbol,interval,limit)
    while klines is None or len(klines)<1:
        #print('Klines listesi bos geldi. 1dk sonra tekrar denenecek. İslem saati: ',datetime.now())
        timet.sleep(60)
        klinesNew=getKlines(symbol,interval,limit)
        klines=klinesNew
    date=[float(entry[0]) for entry in klines]
    #open=[float(entry[1]) for entry in klines]
    high=[float(entry[2]) for entry in klines]
    low=[float(entry[3]) for entry in klines]
    close=[float(entry[4]) for entry in klines]
    last_date=getDateFromTimestamp(date[-1])
    last_closing_price=close[-1]
    high_array=np.asarray(high)
    high_finished=high_array[:-1]
    low_array=np.asarray(low)
    low_finished=low_array[:-1]
    close_array=np.asarray(close)
    close_finished=close_array[:-1]
    wil=ta.WILLR(high_finished, low_finished, close_finished, timeperiod=14)
    WilliamR_1d=wil[-1]
    #print(symbol,'icin ',interval,' parametresi ile WilliamR calistirildiginda ',WilliamR_1d,'sonucuna ulasilmistir.','Ayrica anlik kapanis fiyati:',last_closing_price,' ve islenen tarih',last_date)
    return WilliamR_1d

def getEMA(symbol,interval,limit,ema_timeperiod):
    klines=getKlines(symbol,interval,limit)
    while klines is None or len(klines)<1:
        #print('Klines listesi bos geldi. 1dk sonra tekrar denenecek. İslem saati: ',datetime.now())
        timet.sleep(60)
        klinesNew=getKlines(symbol,interval,limit)
        klines=klinesNew
    date=[float(entry[0]) for entry in klines]
    close=[float(entry[4]) for entry in klines]
    last_date=getDateFromTimestamp(date[-1])
    last_closing_price=close[-1]
    close_array=np.asarray(close)
    ema=ta.EMA(close_array,timeperiod=ema_timeperiod)
    ema_last=ema[-1]
    #print(symbol,'icin ',interval,' parametresi ile EMA calistirildiginda ',ema_last,'sonucuna ulasilmistir.','Ayrica anlik kapanis fiyati:',last_closing_price,' ve islenen tarih',last_date)
    return ema_last

def getIsEmaHigherThan4hBTCPrice():
    global resultMail
    buyResult=0
    symbol='BTCUSDT'
    interval='4h'
    limit=100000000000
    timeperiod=20
    klines=getKlines(symbol,interval,limit)
    while klines is None or len(klines)<1:  
        #print('Klines listesi bos geldi. 1dk sonra tekrar denenecek. İslem saati:', datetime.now())
        timet.sleep(60)
        klinesNew=getKlines(symbol,interval,limit)
        klines=klinesNew
    date=[float(entry[0]) for entry in klines]
    close=[float(entry[4]) for entry in klines]
    last_date=getDateFromTimestamp(date[-1])
    last_closing_price=close[-1]
    close_array=np.asarray(close)
    ema_20=ta.EMA(close_array,timeperiod=timeperiod)
    ema_last=ema_20[-1]
    if ema_last<last_closing_price:
        buyResult=1
        body='Satin alma icin onay sonucu: ', buyResult,'. detay; ',symbol,' icin ' ,interval,' parametresi ile EMA calistirildiginda ',ema_last,'sonucuna ulasilmistir.','Ayrica anlik kapanis fiyati:',last_closing_price,' ve islenen tarih',last_date
        resultMail=resultMail,' <br>  ',body
    else:
        buyResult=0
        body='Satin alma icin onay sonucu: ',buyResult,'. detay; ',symbol,' icin ' ,interval,' parametresi ile EMA calistirildiginda ',ema_last,'sonucuna ulasilmistir.','Ayrica anlik kapanis fiyati:',last_closing_price,' ve islenen tarih',last_date
        resultMail=resultMail,' <br>  ',body
    #print('Satin alma icin onay sonucu: ',buyResult,'. detay; ',symbol,' icin ' ,interval,' parametresi ile EMA calistirildiginda ',ema_last,'sonucuna ulasilmistir.','Ayrica anlik kapanis fiyati:',last_closing_price,' ve islenen tarih',last_date)
    return buyResult

def getIsEmaHigherThanBTCPrice():
    global resultMail
    buyResult=0
    symbol='BTCUSDT'
    interval='1d'
    limit=100000000000
    timeperiod=20
    klines=getKlines(symbol,interval,limit)
    while klines is None or len(klines)<1:  
        #print('Klines listesi bos geldi. 1dk sonra tekrar denenecek. İslem saati:', datetime.now())
        timet.sleep(60)
        klinesNew=getKlines(symbol,interval,limit)
        klines=klinesNew
    date=[float(entry[0]) for entry in klines]
    close=[float(entry[4]) for entry in klines]
    last_date=getDateFromTimestamp(date[-1])
    last_closing_price=close[-1]
    close_array=np.asarray(close)
    ema_20=ta.EMA(close_array,timeperiod=timeperiod)
    ema_last=ema_20[-1]
    if ema_last<last_closing_price:
        buyResult=1
        body='Satin alma icin onay sonucu: ', buyResult,'. detay; ',symbol,' icin ' ,interval,' parametresi ile EMA calistirildiginda ',ema_last,'sonucuna ulasilmistir.','Ayrica anlik kapanis fiyati:',last_closing_price,' ve islenen tarih',last_date
        resultMail=resultMail,' <br>  ',body
    else:
        buyResult=0
        body='Satin alma icin onay sonucu: ',buyResult,'. detay; ',symbol,' icin ' ,interval,' parametresi ile EMA calistirildiginda ',ema_last,'sonucuna ulasilmistir.','Ayrica anlik kapanis fiyati:',last_closing_price,' ve islenen tarih',last_date
        resultMail=resultMail,' <br>  ',body
    #print('Satin alma icin onay sonucu: ',buyResult,'. detay; ',symbol,' icin ' ,interval,' parametresi ile EMA calistirildiginda ',ema_last,'sonucuna ulasilmistir.','Ayrica anlik kapanis fiyati:',last_closing_price,' ve islenen tarih',last_date)
    return buyResult

def getIsEmaHigherThanBTCPriceForFivePercPassed():
    global resultMail
    buyResult=0
    symbol='BTCUSDT'
    interval='1d'
    limit=100000000000
    timeperiod=20
    klines=getKlines(symbol,interval,limit)
    while klines is None or len(klines)<1:  
        #print('Klines listesi bos geldi. 1dk sonra tekrar denenecek. İslem saati:', datetime.now())
        timet.sleep(60)
        klinesNew=getKlines(symbol,interval,limit)
        klines=klinesNew
    date=[float(entry[0]) for entry in klines]
    close=[float(entry[4]) for entry in klines]
    last_date=getDateFromTimestamp(date[-1])
    last_closing_price=close[-1]
    close_array=np.asarray(close)
    ema_20=ta.EMA(close_array,timeperiod=timeperiod)
    ema_last=ema_20[-1]
    ema_last = ema_last * 1.05 #yüzde 5 üzeri yapıldı. alım yaparken yüzde beş üzerindeyken alması için.
    if ema_last<last_closing_price:
        buyResult=1
        body='%5 üzeri için Satin alma icin onay sonucu: ', buyResult,'. detay; ',symbol,' icin ' ,interval,' parametresi ile EMA calistirildiginda ',ema_last,'sonucuna ulasilmistir.','Ayrica anlik kapanis fiyati:',last_closing_price,' ve islenen tarih',last_date
        resultMail=resultMail,' <br>  ',body
    else:
        buyResult=0
        body='%5 üzeri için Satin alma icin onay sonucu: ',buyResult,'. detay; ',symbol,' icin ' ,interval,' parametresi ile EMA calistirildiginda ',ema_last,'sonucuna ulasilmistir.','Ayrica anlik kapanis fiyati:',last_closing_price,' ve islenen tarih',last_date
        resultMail=resultMail,' <br>  ',body
    #print('Satin alma icin onay sonucu: ',buyResult,'. detay; ',symbol,' icin ' ,interval,' parametresi ile EMA calistirildiginda ',ema_last,'sonucuna ulasilmistir.','Ayrica anlik kapanis fiyati:',last_closing_price,' ve islenen tarih',last_date)
    return buyResult

def getIsEmaLowerThanBTC10Perc():
    global resultMail
    buyResult=0
    symbol='BTCUSDT'
    interval='1d'
    limit=100000000000
    timeperiod=20
    klines=getKlines(symbol,interval,limit)
    while klines is None or len(klines)<1:  
        #print('Klines listesi bos geldi. 1dk sonra tekrar denenecek. İslem saati:', datetime.now())
        timet.sleep(60)
        klinesNew=getKlines(symbol,interval,limit)
        klines=klinesNew
    date=[float(entry[0]) for entry in klines]
    close=[float(entry[4]) for entry in klines]
    last_date=getDateFromTimestamp(date[-1])
    last_closing_price=close[-1]
    close_array=np.asarray(close)
    ema_20=ta.EMA(close_array,timeperiod=timeperiod)
    ema_last=ema_20[-1]
    ema_last = ema_last * 0.9 #yüzde 10 aşağısı yapıldı. satış yaparken yüzde beş altındayken satması için.
    if ema_last>last_closing_price:
        buyResult=1
    else:
        buyResult=0
    #print('Ema %10 aşağısı: ',buyResult,'. detay; ',symbol,' icin ' ,interval,' parametresi ile EMA calistirildiginda ',ema_last,'sonucuna ulasilmistir.','Ayrica anlik kapanis fiyati:',last_closing_price,' ve islenen tarih',last_date)
    return buyResult

def getIsEmaLowerThanBTC5Perc():
    global resultMail
    buyResult=0
    symbol='BTCUSDT'
    interval='1d'
    limit=100000000000
    timeperiod=20
    klines=getKlines(symbol,interval,limit)
    while klines is None or len(klines)<1:  
        #print('Klines listesi bos geldi. 1dk sonra tekrar denenecek. İslem saati:', datetime.now())
        timet.sleep(60)
        klinesNew=getKlines(symbol,interval,limit)
        klines=klinesNew
    date=[float(entry[0]) for entry in klines]
    close=[float(entry[4]) for entry in klines]
    last_date=getDateFromTimestamp(date[-1])
    last_closing_price=close[-1]
    close_array=np.asarray(close)
    ema_20=ta.EMA(close_array,timeperiod=timeperiod)
    ema_last=ema_20[-1]
    ema_last = ema_last * 0.95 #yüzde 5 aşağısı yapıldı. satış yaparken yüzde beş altındayken satması için.
    if ema_last>last_closing_price:
        buyResult=1
    else:
        buyResult=0
    #print('Ema %5 aşağısı: ',buyResult,'. detay; ',symbol,' icin ' ,interval,' parametresi ile EMA calistirildiginda ',ema_last,'sonucuna ulasilmistir.','Ayrica anlik kapanis fiyati:',last_closing_price,' ve islenen tarih',last_date)
    return buyResult

def getLastEma20DayBTCPrice():
    symbol='BTCUSDT'
    interval='1d'
    limit=100000000000
    timeperiod=20
    klines=getKlines(symbol,interval,limit)
    while klines is None or len(klines)<1:  
        #print('Klines listesi bos geldi. 1dk sonra tekrar denenecek. İslem saati:', datetime.now())
        timet.sleep(60)
        klinesNew=getKlines(symbol,interval,limit)
        klines=klinesNew
    close=[float(entry[4]) for entry in klines]
    close_array=np.asarray(close)
    ema_20=ta.EMA(close_array,timeperiod=timeperiod)
    ema_last=ema_20[-1]
    return ema_last

def getLastEma50DayBTCPrice():
    symbol='BTCUSDT'
    interval='1d'
    limit=100000000000
    timeperiod=50
    klines=getKlines(symbol,interval,limit)
    while klines is None or len(klines)<1:  
        #print('Klines listesi bos geldi. 1dk sonra tekrar denenecek. İslem saati:', datetime.now())
        timet.sleep(60)
        klinesNew=getKlines(symbol,interval,limit)
        klines=klinesNew
    close=[float(entry[4]) for entry in klines]
    close_array=np.asarray(close)
    ema_50=ta.EMA(close_array,timeperiod=timeperiod)
    ema_last=ema_50[-1]
    return ema_last

def getIsStillCheap():#BtcPassedFromEma20AndEma50Control
    #btc fiyatına göre ema 20 günlüğün(getLastEma20DayBTCPrice()) fiyatı ema 50 günlük(getLastEma50DayBTCPrice()) fiyatının altındaysa 
    #ve mevcut btc fiyatı ema 50 günlüğün üzerine çıktıysa pahalı olmuş demektir 
    isStillCheap = True
    activeBtcPrice = getActivePrice('BTC','USDT')
    ema20BtcPrice = getLastEma20DayBTCPrice()
    ema50BtcPrice = getLastEma50DayBTCPrice()
    if ema20BtcPrice < ema50BtcPrice :
        if activeBtcPrice > ema50BtcPrice : 
            isStillCheap = False
    return isStillCheap

def findQuantityByCurrentPriceAndTrustRateToBuy(firstCoinForBuyParameter,secondCoinForBuyParameter):
    activeCoin=Coin.objects.get(name=firstCoinForBuyParameter)
    buyPrice=activeCoin.getBuyPriceAsUSDT()
    price=getActivePrice(firstCoinForBuyParameter,secondCoinForBuyParameter)
    quantity=(buyPrice*1)/price
    return quantity

def findQuantityByCurrentPriceAndTrustRateToBuyForRobot15m(firstCoinForBuyParameter,secondCoinForBuyParameter):
    activeCoin=Coin.objects.get(name=firstCoinForBuyParameter)
    buyPrice=activeCoin.getBuyPriceAsUSDTForRobot15m()
    price=getActivePrice(firstCoinForBuyParameter,secondCoinForBuyParameter)
    quantity=(buyPrice*1)/price
    return quantity

def findQuantityByCurrentPriceAndTrustRateToBuyForRobot15mWITHRealMargin(firstCoinForBuyParameter,secondCoinForBuyParameter):
    activeCoin=Coin.objects.get(name=firstCoinForBuyParameter)
    buyPrice=activeCoin.getBuyPriceAsUSDTForRobot15mWITHRealMargin()
    price=getActivePrice(firstCoinForBuyParameter,secondCoinForBuyParameter)
    quantity=(buyPrice*1)/price
    return quantity

def findQuantityByCurrentPriceAndTrustRateToBuyForRobot15mSlow(firstCoinForBuyParameter,secondCoinForBuyParameter):
    activeCoin=Coin.objects.get(name=firstCoinForBuyParameter)
    buyPrice=activeCoin.getBuyPriceAsUSDTForRobot15mSlow()
    price=getActivePrice(firstCoinForBuyParameter,secondCoinForBuyParameter)
    quantity=(buyPrice*1)/price
    return quantity

def findQuantityByCurrentPriceAndTrustRateToBuyForRobot1h(firstCoinForBuyParameter,secondCoinForBuyParameter):
    activeCoin=Coin.objects.get(name=firstCoinForBuyParameter)
    buyPrice=activeCoin.getBuyPriceAsUSDTForRobot1h()
    price=getActivePrice(firstCoinForBuyParameter,secondCoinForBuyParameter)
    quantity=(buyPrice*1)/price
    return quantity

def findQuantityByCurrentPriceAndTrustRateToBuyForRobotMarginBTC(firstCoinForBuyParameter,secondCoinForBuyParameter):
    activeCoin=Coin.objects.get(name=firstCoinForBuyParameter)
    buyPrice=activeCoin.getBuyPriceAsUSDTForRobotMarginBTC()
    price=getActivePrice(firstCoinForBuyParameter,secondCoinForBuyParameter)
    quantity=(buyPrice*1)/price
    return quantity

def findQuantityByTradeToSell(myTrade):
    return myTrade.count*myTrade.getSellPercentage()/100

def getIsMovedPercentForBuySignal(activeCoin):
    result=False
    if activeCoin is not None:
        myPreferences=Preferences.objects.all().first()
        if Trade.objects.filter(buyedByRobot=True,coin=activeCoin).exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS')).exists():
            latestTrade=Trade.objects.filter(buyedByRobot=True,coin=activeCoin).exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS')).latest('transactionDate')
            priceNow=getActivePrice(latestTrade.coin.name,latestTrade.exchangePair.name)
            percentage=priceNow*100/latestTrade.price-100
            if percentage > myPreferences.targetPercentageForBuying or percentage < float(-1*myPreferences.targetPercentageForBuying):
                result=True
            else :
                result=False
        else:
            result=True
    else:
        result=True
    return result

def updateTradesWithIndicatorResults(coinName,indicatorResults):
    tradeList=Trade.objects.filter(coin=(Coin.objects.get(name=coinName)))
    if tradeList is not None:
        for item in tradeList:
            item.indicatorResults=indicatorResults
            item.save()

def updateRobot15mTradesWithIndicatorResults(coinName,indicatorResults):
    tradeList=Trade.objects.filter(coin=(Coin.objects.get(name=coinName)),strategy='RSI_15m')
    if tradeList is not None:
        for item in tradeList:
            item.indicatorResults=indicatorResults
            item.save()

def updateRobot15mTradesWITHRealMarginWithIndicatorResults(coinName,indicatorResults):
    tradeList=Trade.objects.filter(coin=(Coin.objects.get(name=coinName)),strategy='RSI_15m_WITHRealMargin')
    if tradeList is not None:
        for item in tradeList:
            item.indicatorResults=indicatorResults
            item.save()

def updateRobot15mSlowTradesWithIndicatorResults(coinName,indicatorResults):
    tradeList=Trade.objects.filter(coin=(Coin.objects.get(name=coinName)),strategy='RSI_15m_Slow')
    if tradeList is not None:
        for item in tradeList:
            item.indicatorResults=indicatorResults
            item.save()

def updateRobot1hTradesWithIndicatorResults(coinName,indicatorResults):
    tradeList=Trade.objects.filter(coin=(Coin.objects.get(name=coinName)),strategy='RSI_1h')
    if tradeList is not None:
        for item in tradeList:
            #item.indicatorResults=((indicatorResults.replace(",", "")).replace("(", "")).replace(")", "")
            item.indicatorResults=indicatorResults
            item.save()

def fixString(myString):
    return " ".join(str(x) for x in myString)

def getActiveMinRSI(myPreferences):
    minRSI=myPreferences.minRSI
    '''if getIsBtcHigherThan10PercentageFromEma() and (myPreferences.isFlexWhileBuying):#Emanın %10 üzerinde değilse sabit değerini kullanır. Öncelikle ema nın yüzde 10 üzerindeyse ve sonra Robot kendine ayrılan tutarın %25 inden az kullanıyorsa Alım yapılırken buysignal daki minRsi değeri 10 yukarı (varsayılan 20 ise, 30kullanılır) çekilir.eğer %25 i geçmiş ve %50 den az ise minRsi değeri 5 yukarı(25 yani) çekilir. Robot limitinin %50 sini geçtiyse varsayılan minRsi değeri kullanılır 
        usedPercentageOfRobot=getUsedPercentageOfRobot()
        if usedPercentageOfRobot<25:
            minRSI=minRSI+10
        elif usedPercentageOfRobot<50:
            minRSI=minRSI+6
        elif usedPercentageOfRobot<65:
            minRSI=minRSI+4
        elif usedPercentageOfRobot<75:
            minRSI=minRSI+2
        elif usedPercentageOfRobot>=90:
            minRSI=minRSI-2
        elif usedPercentageOfRobot>=95:
            minRSI=minRSI-5'''
    return minRSI

def getActiveMaxRSI(myPreferences,isBtcHigherThan10PercentageFromEma):
    maxRSI=myPreferences.maxRSI
    if(myPreferences.isFlexWhileBuying):
        if isBtcHigherThan10PercentageFromEma == False:
            maxRSI=maxRSI-20
        else : 
            usedPercentageOfRobot=getUsedPercentageOfRobot()
            if usedPercentageOfRobot<50:
                maxRSI=maxRSI+5
            elif usedPercentageOfRobot>=70:
                maxRSI=maxRSI-5
            elif usedPercentageOfRobot>=85:
                maxRSI=maxRSI-10
    return maxRSI
###################################################################################################################################################################2

# def buySignal(firstCoinToCompareParameter,secondCoinToCompareParameter,firstCoinForBuyParameter,secondCoinForBuyParameter,maxLimit):
#     signal_buy=0
#     if getIsMarginCoin(firstCoinForBuyParameter) == False:
#         global resultMail
#         global notBoughSignalComeButNoLimit
#         global nearlyBuyCoins
#         activeCoinToCompare=firstCoinToCompareParameter+secondCoinToCompareParameter
#         RSI_30m=RSI_1h=RSI_2h=RSI_4h=WilliamR_1d=0
#         activeCoin=Coin.objects.get(name=firstCoinForBuyParameter)
#         myPreferences=Preferences.objects.all().first()
#         minRSI=getActiveMinRSI(myPreferences)
#         midRSI=myPreferences.midRSI
#         williamR=myPreferences.williamR
#         remainingUsdtToUsePassed=getRemainingUsdtToUseForRobot(maxLimit)>0 
#         maxOpenTradeControlPassed=(Trade.objects.filter(coin=activeCoin,isPassiveInEarn=False,isDifferentExchange=False,strategy='RSI_4h').exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS')).count())<(myPreferences.maxOpenTradeCountForSameCoin)
#         cooldownPassed=getIsCooldownBuyPassedForCoin(activeCoin)
#         minOrMaxFivePercChangePassed=getIsMovedPercentForBuySignal(activeCoin)
#         RSI_30m=int(getRSI(activeCoinToCompare,'30m',5000))
#         RSI_1h=int(getRSI(activeCoinToCompare,'1h',5000))
#         RSI_2h=int(getRSI(activeCoinToCompare,'2h',5000))
#         RSI_4h=int(getRSI(activeCoinToCompare,'4h',5000))
#         WilliamR_1d=int(getWilliamR(activeCoinToCompare,'1d',5000))
#         # allUnderMidRSIControlPassed=RSI_15m<midRSI and RSI_30m<midRSI and RSI_1h<midRSI and RSI_2h<midRSI and RSI_4h<midRSI
#         allUnderMidRSIControlPassed=RSI_30m<midRSI and RSI_1h<midRSI and RSI_4h<midRSI
#         # minRSIControlFor4hAndOneAnotherControlPassed=(RSI_15m<minRSI or RSI_30m<minRSI or RSI_1h<minRSI or RSI_2h<minRSI) and (RSI_4h<minRSI)
#         minRSIControlFor4hAndOneAnotherControlPassed=RSI_4h<minRSI
#         williamRControlPassed=WilliamR_1d<williamR
#         indicatorResultsStringForMail = ' R30:',RSI_30m,' - R1h:',RSI_1h,' - R2h:',RSI_2h,' - <b>R4h:</b><b>',RSI_4h,'</b> - W1d:',WilliamR_1d
#         indicatorResultsForMail = fixString(indicatorResultsStringForMail)
#         coinDetailsForMailString=' R30:',RSI_30m,' - R1h:',RSI_1h,' - R2h:',RSI_2h,' - <b>R4h:</b> ',RSI_4h,' - W1d: ',WilliamR_1d,' -allUnderMidRSIControlPassed:',allUnderMidRSIControlPassed,' - minRSIControlFor4hAndOneAnotherControlPassed:',minRSIControlFor4hAndOneAnotherControlPassed,'williamRControlPassed:',williamRControlPassed,' maxOpenTradeControlPassed:',maxOpenTradeControlPassed,'cooldownPassed ve minOrMaxFivePercChangePassed:',cooldownPassed,' / ',minOrMaxFivePercChangePassed,' remainingUsdtToUsePassed:',remainingUsdtToUsePassed,' - Buy Signal:- ',firstCoinToCompareParameter
#         coinDetailsForMail = fixString(coinDetailsForMailString)
#         resultMail=resultMail,' <br> ' , coinDetailsForMail
#         if (RSI_4h-5)<minRSI and cooldownPassed:
#             nearlyBuyCoins=nearlyBuyCoins,' <br> ',firstCoinToCompareParameter,' => ', indicatorResultsForMail
#         if maxOpenTradeControlPassed and cooldownPassed and minOrMaxFivePercChangePassed: 
#             if (allUnderMidRSIControlPassed and minRSIControlFor4hAndOneAnotherControlPassed and williamRControlPassed):
#                 if remainingUsdtToUsePassed:
#                     signal_buy=1
#                     finalQuantity=minimizeNumber(findQuantityByCurrentPriceAndTrustRateToBuy(firstCoinForBuyParameter,secondCoinForBuyParameter))
#                     finalQuantity=finalQuantity*2 #Robot4h cok nadir çalıştığı için beklenenin 2 katı kadar alım yapsın
#                     buyWithMarketPriceByQuantityAction(firstCoinForBuyParameter,secondCoinForBuyParameter,finalQuantity,True,'RSI_4h')
#                 else :
#                     notBoughSignalComeButNoLimit=notBoughSignalComeButNoLimit,'  ',firstCoinForBuyParameter,' => ', indicatorResultsForMail
#                     signal_buy=0
#             else :
#                 signal_buy=0
#     return signal_buy

def buySignalForRobot1h(firstCoinToCompareParameter,secondCoinToCompareParameter,firstCoinForBuyParameter,secondCoinForBuyParameter):
    signal_buy=0
    if getIsMarginCoin(firstCoinForBuyParameter) == False:
        global resultMail
        global nearlyBuyCoins
        cooldownPassed=readyToBuy=False
        activeCoinToCompareForBTC=firstCoinToCompareParameter+'BTC'
        activeCoinToCompareForUSDT=firstCoinToCompareParameter+'USDT'
        activeCoin=Coin.objects.get(name=firstCoinForBuyParameter)
        if Coin.objects.filter(name=firstCoinForBuyParameter+'UP').exists():
            activeCoinForUp=Coin.objects.get(name=firstCoinForBuyParameter+'UP')
            cooldownPassed=getIsCooldownBuyPassedForCoinForRobot1h(activeCoin) and getIsCooldownBuyPassedForCoinForMargin(activeCoinForUp)
        else : 
            cooldownPassed=getIsCooldownBuyPassedForCoinForRobot1h(activeCoin)
        myPreferences=Preferences.objects.all().first()
        minRSI=myPreferences.minRSIForRobot1h
        remainingUsdtToUsePassed=getRemainingUsdtToUseForRobot1h()>0 
        maxOpenTradeControlPassed=(Trade.objects.filter(coin=activeCoin,isPassiveInEarn=False,isDifferentExchange=False,strategy='RSI_1h').exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS')).count())<(myPreferences.maxOpenTradeCountForRobot1h)
        minOrMaxFivePercChangePassed=getIsMovedPercentForBuySignal(activeCoin)
        RSI_1h_BTC=int(getRSI(activeCoinToCompareForBTC,'1h',5000))
        RSI_1h_USDT=int(getRSI(activeCoinToCompareForUSDT,'1h',5000))
        buyingAccordingToBTC=RSI_1h_BTC<minRSI and RSI_1h_USDT<50
        buyingAccordingToUSDT=RSI_1h_USDT<minRSI and RSI_1h_BTC<50
        minRSIControlPassed=buyingAccordingToBTC or buyingAccordingToUSDT
        coinDetailsForMailString=' R15: btc:',RSI_1h_BTC,'usdt:',RSI_1h_USDT,' - Robot RSI_15m Signal:- ',firstCoinToCompareParameter
        coinDetailsForMail = fixString(coinDetailsForMailString)
        resultMail=resultMail,' <br> ' , coinDetailsForMail
        #if ((RSI_1h_BTC-5)<minRSI or (RSI_1h_USDT-5)<minRSI) and cooldownPassed:
        #    nearlyBuyCoins=nearlyBuyCoins,' <br> ',firstCoinToCompareParameter,' => ', coinDetailsForMail
        if maxOpenTradeControlPassed and cooldownPassed and minOrMaxFivePercChangePassed: 
            if minRSIControlPassed :
                if buyingAccordingToUSDT: 
                    if activeCoin.moveRSI1hComeBackRSIValueForUsdt == 0 or activeCoin.moveRSI1hComeBackRSIValueForUsdt>RSI_1h_USDT:
                        activeCoin.moveRSI1hComeBackRSIValueForUsdt = RSI_1h_USDT
                if buyingAccordingToBTC: 
                    if activeCoin.moveRSI1hComeBackRSIValueForBtc == 0 or activeCoin.moveRSI1hComeBackRSIValueForBtc>RSI_1h_BTC:
                        activeCoin.moveRSI1hComeBackRSIValueForBtc = RSI_1h_BTC
                activeCoin.save()
                nearlyBuyCoins=nearlyBuyCoins,' <br> ',firstCoinToCompareParameter,' => ', coinDetailsForMail
            readyToBuy= (activeCoin.moveRSI1hComeBackRSIValueForUsdt>0 and ((RSI_1h_USDT - activeCoin.moveRSI1hComeBackRSIValueForUsdt)>myPreferences.moveRSIComeBackPercentage)) or (activeCoin.moveRSI1hComeBackRSIValueForBtc>0 and ((RSI_1h_BTC - activeCoin.moveRSI1hComeBackRSIValueForBtc)>myPreferences.moveRSIComeBackPercentage))
            if readyToBuy:
                activeCoin.moveRSI1hComeBackRSIValueForBtc=0
                activeCoin.moveRSI1hComeBackRSIValueForUsdt=0
                activeCoin.save()
                if remainingUsdtToUsePassed:
                    cleanAllPastCoinSignals(firstCoinForBuyParameter)
                    signal_buy=1
                    finalQuantity=minimizeNumber(findQuantityByCurrentPriceAndTrustRateToBuyForRobot1h(firstCoinForBuyParameter,secondCoinForBuyParameter))
                    buyWithMarketPriceByQuantityAction(firstCoinForBuyParameter,secondCoinForBuyParameter,finalQuantity,True,'RSI_1h')
                else :
                    signal_buy=0
            else :
                signal_buy=0
    return signal_buy

#CHECK BTC AND USDT BOTH ... DONT USE WITH CRYPTOS WHICH DOESNT HAVE VALUES TO COMPARE WITH BTC OR USDT !!!
def buySignalForRobot15m(firstCoinToCompareParameter,secondCoinToCompareParameter,firstCoinForBuyParameter,secondCoinForBuyParameter):
    signal_buy=0
    if getIsMarginCoin(firstCoinForBuyParameter) == False:
        global resultMail
        global nearlyBuyCoins
        cooldownPassed=readyToBuy=False
        activeCoinToCompareForBTC=firstCoinToCompareParameter+'BTC'
        activeCoinToCompareForUSDT=firstCoinToCompareParameter+'USDT'
        activeCoin=Coin.objects.get(name=firstCoinForBuyParameter)
        if Coin.objects.filter(name=firstCoinForBuyParameter+'UP').exists():
            activeCoinForUp=Coin.objects.get(name=firstCoinForBuyParameter+'UP')
            cooldownPassed=getIsCooldownBuyPassedForCoinForRobot15m(activeCoin) and getIsCooldownBuyPassedForCoinForMargin(activeCoinForUp)
        else : 
            cooldownPassed=getIsCooldownBuyPassedForCoinForRobot15m(activeCoin)
        myPreferences=Preferences.objects.all().first()
        minRSI=myPreferences.minRSIForLong
        remainingUsdtToUsePassed=getRemainingUsdtToUseForRobot15m()>0 
        maxOpenTradeControlPassed=(Trade.objects.filter(coin=activeCoin,isPassiveInEarn=False,isDifferentExchange=False,strategy='RSI_15m').exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS')).count())<(myPreferences.maxOpenTradeCountForRobot15m)
        minOrMaxFivePercChangePassed=getIsMovedPercentForBuySignal(activeCoin)
        RSI_15m_BTC=int(getRSI(activeCoinToCompareForBTC,'15m',5000))
        RSI_15m_USDT=int(getRSI(activeCoinToCompareForUSDT,'15m',5000))
        #RSI_5m_USDT=int(getRSI(activeCoinToCompareForUSDT,'5m',5000))
        minRSIControlPassed=False
        test='dontBuy'
        if RSI_15m_USDT<minRSI and RSI_15m_USDT<50 and RSI_15m_BTC<50: #and RSI_5m_USDT<minRSI 
            minRSIControlPassed=True
            test='buyForUSDT'
        elif RSI_15m_BTC<minRSI and RSI_15m_USDT<50 and RSI_15m_BTC<50: #and RSI_5m_USDT<minRSI 
            minRSIControlPassed=True
            test='buyForBTC'
        else :
            minRSIControlPassed=False
            test='dontBuy'
        coinDetailsForMailString=' test:',test,'R15: btc:',RSI_15m_BTC,'usdt:',RSI_15m_USDT,' before:btc/usdt:',activeCoin.moveRSI15mComeBackRSIValueForBtc,'/',activeCoin.moveRSI15mComeBackRSIValueForUsdt,'/',' - Robot RSI_15m Signal:- ',firstCoinToCompareParameter
        #if ((RSI_15m_BTC-5)<minRSI or (RSI_15m_USDT-5)<minRSI) and cooldownPassed:
        #    nearlyBuyCoins=nearlyBuyCoins,' <br> ',firstCoinToCompareParameter,' => ', fixString(coinDetailsForMailString)
        if maxOpenTradeControlPassed and cooldownPassed and minOrMaxFivePercChangePassed: 
            if minRSIControlPassed :
                if RSI_15m_USDT<minRSI: 
                    if activeCoin.moveRSI15mComeBackRSIValueForUsdt == 0 or activeCoin.moveRSI15mComeBackRSIValueForUsdt>RSI_15m_USDT:
                        activeCoin.moveRSI15mComeBackRSIValueForUsdt = RSI_15m_USDT
                        coinDetailsForMailString = 'setted usdt',coinDetailsForMailString
                if RSI_15m_BTC<minRSI: 
                    if activeCoin.moveRSI15mComeBackRSIValueForBtc == 0 or activeCoin.moveRSI15mComeBackRSIValueForBtc>RSI_15m_BTC:
                        activeCoin.moveRSI15mComeBackRSIValueForBtc = RSI_15m_BTC
                        coinDetailsForMailString = 'setted btc',coinDetailsForMailString
                activeCoin.save()
                nearlyBuyCoins=nearlyBuyCoins,' <br> ',firstCoinToCompareParameter,' => ', fixString(coinDetailsForMailString)
            rsiUsdtDiff = RSI_15m_USDT - activeCoin.moveRSI15mComeBackRSIValueForUsdt
            rsiBtcDiff = RSI_15m_BTC - activeCoin.moveRSI15mComeBackRSIValueForBtc
            if activeCoin.moveRSI15mComeBackRSIValueForUsdt>0 and rsiUsdtDiff>myPreferences.moveRSIComeBackPercentage: 
                coinDetailsForMailString = 'usdt sebebiyle alınacak.. sıfırlanmadan once son durum:btc/usdt',myPreferences.moveRSIComeBackPercentage,'-',activeCoin.moveRSI15mComeBackRSIValueForUsdt,'/',RSI_15m_USDT,'/',activeCoin.moveRSI15mComeBackRSIValueForBtc,'/',RSI_15m_BTC,'/',coinDetailsForMailString
                activeCoin.moveRSI15mComeBackRSIValueForUsdt=0
                activeCoin.moveRSI15mComeBackRSIValueForBtc=0
                activeCoin.save()
                if remainingUsdtToUsePassed and getIsCooldownPassedForLastNegativeTradeByCoin(firstCoinToCompareParameter):
                    cleanAllPastCoinSignals(firstCoinForBuyParameter)
                    signal_buy=1
                    finalQuantity=minimizeNumber(findQuantityByCurrentPriceAndTrustRateToBuyForRobot15m(firstCoinForBuyParameter,secondCoinForBuyParameter))
                    buyWithMarketPriceByQuantityAction(firstCoinForBuyParameter,secondCoinForBuyParameter,finalQuantity,True,'RSI_15m')
                else :
                    signal_buy=0
            elif activeCoin.moveRSI15mComeBackRSIValueForBtc>0 and rsiBtcDiff>myPreferences.moveRSIComeBackPercentage:
                coinDetailsForMailString = 'btc sebebiyle alınacak.. sıfırlanmadan once son durum:btc/usdt',myPreferences.moveRSIComeBackPercentage,'-',activeCoin.moveRSI15mComeBackRSIValueForUsdt,'/',RSI_15m_USDT,'/',activeCoin.moveRSI15mComeBackRSIValueForBtc,'/',RSI_15m_BTC,'/',coinDetailsForMailString
                activeCoin.moveRSI15mComeBackRSIValueForUsdt=0
                activeCoin.moveRSI15mComeBackRSIValueForBtc=0
                activeCoin.save()
                if remainingUsdtToUsePassed and getIsCooldownPassedForLastNegativeTradeByCoin(firstCoinToCompareParameter):
                    cleanAllPastCoinSignals(firstCoinForBuyParameter)
                    signal_buy=1
                    finalQuantity=minimizeNumber(findQuantityByCurrentPriceAndTrustRateToBuyForRobot15m(firstCoinForBuyParameter,secondCoinForBuyParameter))
                    buyWithMarketPriceByQuantityAction(firstCoinForBuyParameter,secondCoinForBuyParameter,finalQuantity,True,'RSI_15m')
                else :
                    signal_buy=0
            else :
                signal_buy=0
        coinDetailsForMail = fixString(coinDetailsForMailString)
        resultMail=resultMail,' <br> ' , coinDetailsForMail
        activeCoin.last15RSIUSDT=RSI_15m_USDT
        activeCoin.last15RSIBTC=RSI_15m_BTC
        activeCoin.save()
    return signal_buy

def buySignalForRobot15mWITHRealMargin(firstCoinToCompareParameter,secondCoinToCompareParameter,firstCoinForBuyParameter,secondCoinForBuyParameter):
    signal_buy=0
    if getIsMarginCoin(firstCoinForBuyParameter) == False:
        global resultMail
        global nearlyBuyCoins
        cooldownPassed=readyToBuy=False
        activeCoinToCompareForBTC=firstCoinToCompareParameter+'BTC'
        activeCoinToCompareForUSDT=firstCoinToCompareParameter+'USDT'
        activeCoin=Coin.objects.get(name=firstCoinForBuyParameter)
        if Coin.objects.filter(name=firstCoinForBuyParameter+'UP').exists():
            activeCoinForUp=Coin.objects.get(name=firstCoinForBuyParameter+'UP')
            cooldownPassed=getIsCooldownBuyPassedForCoinForRobot15mWITHRealMargin(activeCoin) and getIsCooldownBuyPassedForCoinForMargin(activeCoinForUp) # and getIsCooldownBuyPassedForCoinForRobot15m(activeCoin)
        else : 
            cooldownPassed=getIsCooldownBuyPassedForCoinForRobot15mWITHRealMargin(activeCoin) # and getIsCooldownBuyPassedForCoinForRobot15m(activeCoin)
        myPreferences=Preferences.objects.all().first()
        minRSI=myPreferences.minRSIFor15mWITHRealMargin
        remainingUsdtToUsePassed=getRemainingUsdtToUseForRobot15mWITHRealMargin()>0 
        maxOpenTradeControlPassed=(Trade.objects.filter(coin=activeCoin,isPassiveInEarn=False,isDifferentExchange=False,strategy='RSI_15m_WITHRealMargin').exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS')).count())<(myPreferences.maxOpenTradeCountForRobot15m)
        minOrMaxFivePercChangePassed=getIsMovedPercentForBuySignal(activeCoin)
        RSI_15m_BTC=int(getRSI(activeCoinToCompareForBTC,'15m',5000))
        RSI_15m_USDT=int(getRSI(activeCoinToCompareForUSDT,'15m',5000))
        minRSIControlPassed=False
        test='dontBuy'
        if RSI_15m_USDT<minRSI and RSI_15m_USDT<50 and RSI_15m_BTC<50: #and RSI_5m_USDT<minRSI 
            minRSIControlPassed=True
            test='buyForUSDT'
        elif RSI_15m_BTC<minRSI and RSI_15m_USDT<50 and RSI_15m_BTC<50: #and RSI_5m_USDT<minRSI 
            minRSIControlPassed=True
            test='buyForBTC'
        else :
            minRSIControlPassed=False
            test='dontBuy'
        coinDetailsForMailString=' test:',test,'R15: btc:',RSI_15m_BTC,'usdt:',RSI_15m_USDT,' before:btc/usdt:',activeCoin.moveRSI15mWITHRealMarginComeBackRSIValueForBtc,'/',activeCoin.moveRSI15mWITHRealMarginComeBackRSIValueForUsdt,'/',' - Robot RSI_15m Signal:- ',firstCoinToCompareParameter
        if maxOpenTradeControlPassed and cooldownPassed and minOrMaxFivePercChangePassed: 
            if minRSIControlPassed :
                if RSI_15m_USDT<minRSI: 
                    if activeCoin.moveRSI15mWITHRealMarginComeBackRSIValueForUsdt == 0 or activeCoin.moveRSI15mWITHRealMarginComeBackRSIValueForUsdt>RSI_15m_USDT:
                        activeCoin.moveRSI15mWITHRealMarginComeBackRSIValueForUsdt = RSI_15m_USDT
                        coinDetailsForMailString = 'setted usdt',coinDetailsForMailString
                if RSI_15m_BTC<minRSI: 
                    if activeCoin.moveRSI15mWITHRealMarginComeBackRSIValueForBtc == 0 or activeCoin.moveRSI15mWITHRealMarginComeBackRSIValueForBtc>RSI_15m_BTC:
                        activeCoin.moveRSI15mWITHRealMarginComeBackRSIValueForBtc = RSI_15m_BTC
                        coinDetailsForMailString = 'setted btc',coinDetailsForMailString
                activeCoin.save()
                nearlyBuyCoins=nearlyBuyCoins,' <br> ',firstCoinToCompareParameter,' => ', fixString(coinDetailsForMailString)
            rsiUsdtDiff = RSI_15m_USDT - activeCoin.moveRSI15mWITHRealMarginComeBackRSIValueForUsdt
            rsiBtcDiff = RSI_15m_BTC - activeCoin.moveRSI15mWITHRealMarginComeBackRSIValueForBtc
            if activeCoin.moveRSI15mWITHRealMarginComeBackRSIValueForUsdt>0 and rsiUsdtDiff>myPreferences.moveRSIComeBackPercentage: 
                coinDetailsForMailString = 'usdt sebebiyle alınacak.. sıfırlanmadan once son durum:btc/usdt',myPreferences.moveRSIComeBackPercentage,'-',activeCoin.moveRSI15mWITHRealMarginComeBackRSIValueForUsdt,'/',RSI_15m_USDT,'/',activeCoin.moveRSI15mWITHRealMarginComeBackRSIValueForBtc,'/',RSI_15m_BTC,'/',coinDetailsForMailString
                activeCoin.moveRSI15mWITHRealMarginComeBackRSIValueForUsdt=0
                activeCoin.moveRSI15mWITHRealMarginComeBackRSIValueForBtc=0
                activeCoin.save()
                if remainingUsdtToUsePassed and getIsCooldownPassedForLastNegativeTradeByCoin(firstCoinToCompareParameter):
                    cleanAllPastCoinSignals(firstCoinForBuyParameter)
                    signal_buy=1
                    finalQuantity=minimizeNumber(findQuantityByCurrentPriceAndTrustRateToBuyForRobot15mWITHRealMargin(firstCoinForBuyParameter,secondCoinForBuyParameter))
                    buyWithMarketPriceByQuantityAction(firstCoinForBuyParameter,secondCoinForBuyParameter,finalQuantity,True,'RSI_15m_WITHRealMargin')
                else :
                    signal_buy=0
            elif activeCoin.moveRSI15mWITHRealMarginComeBackRSIValueForBtc>0 and rsiBtcDiff>myPreferences.moveRSIComeBackPercentage:
                coinDetailsForMailString = 'btc sebebiyle alınacak.. sıfırlanmadan once son durum:btc/usdt',myPreferences.moveRSIComeBackPercentage,'-',activeCoin.moveRSI15mWITHRealMarginComeBackRSIValueForUsdt,'/',RSI_15m_USDT,'/',activeCoin.moveRSI15mWITHRealMarginComeBackRSIValueForBtc,'/',RSI_15m_BTC,'/',coinDetailsForMailString
                activeCoin.moveRSI15mWITHRealMarginComeBackRSIValueForUsdt=0
                activeCoin.moveRSI15mWITHRealMarginComeBackRSIValueForBtc=0
                activeCoin.save()
                if remainingUsdtToUsePassed and getIsCooldownPassedForLastNegativeTradeByCoin(firstCoinToCompareParameter):
                    cleanAllPastCoinSignals(firstCoinForBuyParameter)
                    signal_buy=1
                    finalQuantity=minimizeNumber(findQuantityByCurrentPriceAndTrustRateToBuyForRobot15mWITHRealMargin(firstCoinForBuyParameter,secondCoinForBuyParameter))
                    buyWithMarketPriceByQuantityAction(firstCoinForBuyParameter,secondCoinForBuyParameter,finalQuantity,True,'RSI_15m_WITHRealMargin')
                else :
                    signal_buy=0
            else :
                signal_buy=0
        coinDetailsForMail = fixString(coinDetailsForMailString)
        resultMail=resultMail,' <br> ' , coinDetailsForMail
        activeCoin.last15RSIUSDT=RSI_15m_USDT
        activeCoin.last15RSIBTC=RSI_15m_BTC
        activeCoin.save()
    return signal_buy

def buySignalForRobot15mSlow(firstCoinToCompareParameter,secondCoinToCompareParameter,firstCoinForBuyParameter,secondCoinForBuyParameter):
    signal_buy=0
    if getIsMarginCoin(firstCoinForBuyParameter) == False:
        global resultMail
        global nearlyBuyCoins
        cooldownPassed=readyToBuy=False
        activeCoinToCompareForBTC=firstCoinToCompareParameter+'BTC'
        activeCoinToCompareForUSDT=firstCoinToCompareParameter+'USDT'
        activeCoin=Coin.objects.get(name=firstCoinForBuyParameter)
        if Coin.objects.filter(name=firstCoinForBuyParameter+'UP').exists():
            activeCoinForUp=Coin.objects.get(name=firstCoinForBuyParameter+'UP')
            cooldownPassed=getIsCooldownBuyPassedForCoinForRobot15mSlow(activeCoin) and getIsCooldownBuyPassedForCoinForMargin(activeCoinForUp)
        else : 
            cooldownPassed=getIsCooldownBuyPassedForCoinForRobot15mSlow(activeCoin)
        myPreferences=Preferences.objects.all().first()
        minRSI=myPreferences.minRSIFor15mSlow
        minRSIFor1hSlow=myPreferences.minRSIFor1hSlow
        remainingUsdtToUsePassed=getRemainingUsdtToUseForRobot15mSlow()>0 
        maxOpenTradeControlPassed=(Trade.objects.filter(coin=activeCoin,isPassiveInEarn=False,isDifferentExchange=False,strategy='RSI_15m_Slow').exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS')).count())<(myPreferences.maxOpenTradeCountForRobot15mSlow)
        minOrMaxFivePercChangePassed=getIsMovedPercentForBuySignal(activeCoin)
        RSI_15m_BTC=int(getRSI(activeCoinToCompareForBTC,'15m',5000))
        RSI_15m_USDT=int(getRSI(activeCoinToCompareForUSDT,'15m',5000))
        RSI_1h_BTC=int(getRSI(activeCoinToCompareForBTC,'1h',5000))
        RSI_1h_USDT=int(getRSI(activeCoinToCompareForUSDT,'1h',5000))
        buyingAccordingToBTC=RSI_15m_BTC<minRSI and RSI_1h_BTC<minRSIFor1hSlow and RSI_15m_USDT<50 and RSI_1h_USDT<50
        buyingAccordingToUSDT=RSI_15m_USDT<minRSI and RSI_1h_USDT<minRSIFor1hSlow and RSI_15m_BTC<50 and RSI_1h_BTC<50
        minRSIControlPassed=buyingAccordingToBTC or buyingAccordingToUSDT
        coinDetailsForMailString=' R15: btc:',RSI_15m_BTC,'usdt:',RSI_15m_USDT,'usdt1h:',RSI_1h_USDT,' - Robot RSI_15m Signal:- ',firstCoinToCompareParameter
        coinDetailsForMail = fixString(coinDetailsForMailString)
        resultMail=resultMail,' <br> ' , coinDetailsForMail
        #if ((RSI_15m_BTC-5)<minRSI or (RSI_15m_USDT-5)<minRSI) and cooldownPassed:
        #    nearlyBuyCoins=nearlyBuyCoins,' <br> ',firstCoinToCompareParameter,' => ', coinDetailsForMail
        if maxOpenTradeControlPassed and cooldownPassed and minOrMaxFivePercChangePassed: 
            if minRSIControlPassed :
                if buyingAccordingToUSDT: 
                    if activeCoin.moveRSI15mSlowComeBackRSIValueForUsdt == 0 or activeCoin.moveRSI15mSlowComeBackRSIValueForUsdt>RSI_15m_USDT:
                        activeCoin.moveRSI15mSlowComeBackRSIValueForUsdt = RSI_15m_USDT
                if buyingAccordingToBTC: 
                    if activeCoin.moveRSI15mSlowComeBackRSIValueForBtc == 0 or activeCoin.moveRSI15mSlowComeBackRSIValueForBtc>RSI_15m_BTC:
                        activeCoin.moveRSI15mSlowComeBackRSIValueForBtc = RSI_15m_BTC
                activeCoin.save()
                nearlyBuyCoins=nearlyBuyCoins,' <br> ',firstCoinToCompareParameter,' => ', coinDetailsForMail
            readyToBuy= (activeCoin.moveRSI15mSlowComeBackRSIValueForUsdt>0 and ((RSI_15m_USDT - activeCoin.moveRSI15mSlowComeBackRSIValueForUsdt)>myPreferences.moveRSIComeBackPercentage)) or (activeCoin.moveRSI15mSlowComeBackRSIValueForBtc>0 and ((RSI_15m_BTC - activeCoin.moveRSI15mSlowComeBackRSIValueForBtc)>myPreferences.moveRSIComeBackPercentage))
            if readyToBuy:
                activeCoin.moveRSI15mSlowComeBackRSIValueForUsdt=0
                activeCoin.moveRSI15mSlowComeBackRSIValueForBtc=0
                activeCoin.save()
                if remainingUsdtToUsePassed:
                    cleanAllPastCoinSignals(firstCoinForBuyParameter)
                    signal_buy=1
                    finalQuantity=minimizeNumber(findQuantityByCurrentPriceAndTrustRateToBuyForRobot15mSlow(firstCoinForBuyParameter,secondCoinForBuyParameter))
                    buyWithMarketPriceByQuantityAction(firstCoinForBuyParameter,secondCoinForBuyParameter,finalQuantity,True,'RSI_15m_Slow')
                else :
                    signal_buy=0
            else :
                signal_buy=0
    return signal_buy


def buySignalForMarginLongForBtc(firstCoinToCompareParameter,secondCoinToCompareParameter,firstCoinForBuyParameter,secondCoinForBuyParameter):
    signal_buy=0
    if getIsMarginCoin(firstCoinForBuyParameter) == True:
        global resultMail
        activeCoinToCompare=firstCoinToCompareParameter+secondCoinToCompareParameter
        cooldownPassed=readyToBuy=False
        RSI_15m=0
        activeCoin=Coin.objects.get(name=firstCoinForBuyParameter)
        myPreferences=Preferences.objects.all().first()
        minRSI=myPreferences.minRSIForLongForBTC
        remainingUsdtToUsePassed=getRemainingUsdtToUseForMarginBTC()>0 
        maxOpenTradeControlPassed=(Trade.objects.filter(isMargin=True,coin__in=Coin.objects.filter(name__startswith='BTC')).count())<(myPreferences.maxOpenTradeCountForMarginBTC)
        if Coin.objects.filter(name=firstCoinForBuyParameter.replace('UP', '')).exists():
            activeCoinNormal=Coin.objects.get(name=firstCoinForBuyParameter.replace('UP', ''))
            cooldownPassed=getIsCooldownBuyPassedForCoinForMarginBTC(activeCoin)
        else : 
            cooldownPassed=getIsCooldownBuyPassedForCoinForMarginBTC(activeCoin)
        RSI_15m=int(getRSI(activeCoinToCompare,'15m',5000))
        RSI_5m=int(getRSI(activeCoinToCompare,'5m',5000))
        minRSIControlPassed=RSI_15m<minRSI and RSI_5m<(minRSI+10)
        coinDetailsForMailString=' R15:',RSI_15m,' - MarginBTC Long Buy Signal:- ',firstCoinToCompareParameter
        coinDetailsForMail = fixString(coinDetailsForMailString)
        resultMail=resultMail,' <br> ' , coinDetailsForMail
        if maxOpenTradeControlPassed and cooldownPassed:#and minOrMaxFivePercChangePassed
            if minRSIControlPassed :
                if RSI_15m<minRSI : 
                    if activeCoin.moveRSIMarginBtcComeBackRSIValueForUsdt == 0 or activeCoin.moveRSIMarginBtcComeBackRSIValueForUsdt>RSI_15m:
                        activeCoin.moveRSIMarginBtcComeBackRSIValueForUsdt = RSI_15m
                activeCoin.save()
            readyToBuy= (activeCoin.moveRSIMarginBtcComeBackRSIValueForUsdt>0 and (RSI_15m - activeCoin.moveRSIMarginBtcComeBackRSIValueForUsdt)>myPreferences.moveRSIComeBackPercentage)
            if readyToBuy:
                activeCoin.moveRSIMarginBtcComeBackRSIValueForUsdt=0
                activeCoin.save()
                if remainingUsdtToUsePassed:
                    cleanAllPastCoinSignals(firstCoinForBuyParameter)
                    signal_buy=1
                    finalQuantity=minimizeNumber(findQuantityByCurrentPriceAndTrustRateToBuyForRobotMarginBTC(firstCoinForBuyParameter,secondCoinForBuyParameter))
                    buyWithMarketPriceByQuantityAction(firstCoinForBuyParameter,secondCoinForBuyParameter,finalQuantity,True,'MarginBTC_RSI_15m')
                else :
                    signal_buy=0
            else :
                signal_buy=0
    return signal_buy

#CHECK BTC AND USDT BOTH ... DONT USE WITH CRYPTOS WHICH DOESNT HAVE VALUES TO COMPARE WITH BTC OR USDT !!!
def buySignalForMarginLong(firstCoinToCompareParameter,secondCoinToCompareParameter,firstCoinForBuyParameter,secondCoinForBuyParameter):
    signal_buy=0
    if getIsMarginCoin(firstCoinForBuyParameter) == True:
        global resultMail
        activeCoinToCompareForBTC=firstCoinToCompareParameter+'BTC'
        activeCoinToCompareForUSDT=firstCoinToCompareParameter+'USDT'
        cooldownPassed=readyToBuy=False
        activeCoin=Coin.objects.get(name=firstCoinForBuyParameter)
        myPreferences=Preferences.objects.all().first()
        minRSI=myPreferences.minRSIForLong
        remainingUsdtToUsePassed=getRemainingUsdtToUseForMargin()>0 
        maxOpenTradeControlPassed=(Trade.objects.filter(coin=activeCoin,isPassiveInEarn=False,isDifferentExchange=False,isMargin=True).exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS')).count())<(myPreferences.maxOpenTradeCountForMargin)
        if Coin.objects.filter(name=firstCoinForBuyParameter.replace('UP', '')).exists():
            activeCoinNormal=Coin.objects.get(name=firstCoinForBuyParameter.replace('UP', ''))
            cooldownPassed=getIsCooldownBuyPassedForCoinForRobot15m(activeCoinNormal) and getIsCooldownBuyPassedForCoinForMargin(activeCoin)
        else : 
            cooldownPassed=getIsCooldownBuyPassedForCoinForMargin(activeCoin)
        minOrMaxFivePercChangePassed=getIsMovedPercentForBuySignal(activeCoin)
        RSI_15m_BTC=int(getRSI(activeCoinToCompareForBTC,'15m',5000))
        RSI_15m_USDT=int(getRSI(activeCoinToCompareForUSDT,'15m',5000))
        #RSI_5m_USDT=int(getRSI(activeCoinToCompareForUSDT,'5m',5000))
        #buyingAccordingToBTC=RSI_15m_BTC<minRSI and RSI_15m_USDT<50
        buyingAccordingToUSDT=RSI_15m_USDT<minRSI and RSI_15m_BTC<50
        minRSIControlPassed=buyingAccordingToUSDT #and RSI_5m_USDT<minRSI or buyingAccordingToBTC
        coinDetailsForMailString=' R15: btc:',RSI_15m_BTC,' usdt:',RSI_15m_USDT,' - Margin Long Buy Signal:- ',firstCoinToCompareParameter
        coinDetailsForMail = fixString(coinDetailsForMailString)
        resultMail=resultMail,' <br> ' , coinDetailsForMail
        if maxOpenTradeControlPassed and cooldownPassed and minOrMaxFivePercChangePassed: 
            if minRSIControlPassed :
                if buyingAccordingToUSDT : 
                    if activeCoin.moveRSIMarginLongComeBackRSIValueForUsdt == 0 or activeCoin.moveRSIMarginLongComeBackRSIValueForUsdt>RSI_15m_USDT:
                        activeCoin.moveRSIMarginLongComeBackRSIValueForUsdt = RSI_15m_USDT
                activeCoin.save()
            readyToBuy= (activeCoin.moveRSIMarginLongComeBackRSIValueForUsdt>0 and (RSI_15m_USDT - activeCoin.moveRSIMarginLongComeBackRSIValueForUsdt)>myPreferences.moveRSIComeBackPercentage)
            if readyToBuy:
                activeCoin.moveRSIMarginLongComeBackRSIValueForUsdt=0
                activeCoin.save()
                if remainingUsdtToUsePassed:
                    cleanAllPastCoinSignals(firstCoinForBuyParameter)
                    signal_buy=1
                    finalQuantity=minimizeNumber(findQuantityByCurrentPriceAndTrustRateToBuyForRobot15m(firstCoinForBuyParameter,secondCoinForBuyParameter))
                    buyWithMarketPriceByQuantityAction(firstCoinForBuyParameter,secondCoinForBuyParameter,finalQuantity,True,'Margin_RSI_15m')
                else :
                    signal_buy=0
            else :
                signal_buy=0
    return signal_buy

def buySignalForMarginShort(firstCoinToCompareParameter,secondCoinToCompareParameter,firstCoinForBuyParameter,secondCoinForBuyParameter):
    signal_buy=0
    if getIsMarginCoin(firstCoinForBuyParameter) == True:
        global resultMail
        activeCoinToCompare=firstCoinToCompareParameter+secondCoinToCompareParameter
        RSI_15m=0
        activeCoin=Coin.objects.get(name=firstCoinForBuyParameter)
        myPreferences=Preferences.objects.all().first()
        maxRSI=myPreferences.maxRSIForShort
        remainingUsdtToUsePassed=getRemainingUsdtToUseForMargin()>0 
        maxOpenTradeControlPassed=(Trade.objects.filter(coin=activeCoin,isPassiveInEarn=False,isDifferentExchange=False,isMargin=True).exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS')).count())<(myPreferences.maxOpenTradeCountForMargin)
        cooldownPassed=getIsCooldownBuyPassedForCoinForMargin(activeCoin)
        minOrMaxFivePercChangePassed=getIsMovedPercentForBuySignal(activeCoin)
        RSI_15m=int(getRSI(activeCoinToCompare,'15m',5000))
        maxRSIControlPassed=RSI_15m>=maxRSI
        coinDetailsForMailString=' R15:',RSI_15m,' - Margin Short Buy Signal:- ',firstCoinToCompareParameter
        coinDetailsForMail = fixString(coinDetailsForMailString)
        resultMail=resultMail,' <br> ' , coinDetailsForMail
        if maxOpenTradeControlPassed and cooldownPassed and minOrMaxFivePercChangePassed: 
            if maxRSIControlPassed:
                if remainingUsdtToUsePassed:
                    cleanAllPastCoinSignals(firstCoinForBuyParameter)
                    signal_buy=1
                    finalQuantity=minimizeNumber(findQuantityByCurrentPriceAndTrustRateToBuyForRobot15m(firstCoinForBuyParameter,secondCoinForBuyParameter))
                    buyWithMarketPriceByQuantityAction(firstCoinForBuyParameter,secondCoinForBuyParameter,finalQuantity,True,'Margin_RSI_15m')
                else :
                    signal_buy=0
            else :
                signal_buy=0
    return signal_buy
        
def getRemainingUsdtToUseForRobot(maxLimit):
    return maxLimit-getUsedUsdtForRobotAsUsdt()

def getRemainingUsdtToUseForMargin():
    myPreferences=Preferences.objects.all().first()
    return myPreferences.maxLimitForMarginAsUsdt-getUsedUsdtForMarginRobotAsUsdt()

def getRemainingUsdtToUseForMarginBTC():
    myPreferences=Preferences.objects.all().first()
    return myPreferences.maxLimitForMarginBTCAsUsdt-getUsedUsdtForMarginBTCRobotAsUsdt()

def getRemainingUsdtToUseForRobot15m():
    myPreferences=Preferences.objects.all().first()
    return myPreferences.maxLimitForRobot15mAsUsdt-getUsedUsdtForRobot15mAsUsdt()

def getRemainingUsdtToUseForRobot15mWITHRealMargin():
    myPreferences=Preferences.objects.all().first()
    return myPreferences.maxLimitForRobot15mWITHRealMarginAsUsdt-getUsedUsdtForRobot15mWITHRealMarginAsUsdt()

def getRemainingUsdtToUseForRobot15mSlow():
    myPreferences=Preferences.objects.all().first()
    return myPreferences.maxLimitForRobot15mSlowAsUsdt-getUsedUsdtForRobot15mSlowAsUsdt()

def getRemainingUsdtToUseForRobot1h():
    myPreferences=Preferences.objects.all().first()
    return myPreferences.maxLimitForRobot1hAsUsdt-getUsedUsdtForRobot1hAsUsdt()

def getUsedPercentageOfRobot():
    myPreferences=Preferences.objects.all().first()
    return getUsedUsdtForRobotAsUsdt()*100/myPreferences.maxLimitForRobotAsUsdt#robotun ilk alım fiyatları toplamının toplam robot limitine oranı

def getUsedPercentageOfRobot15m():
    myPreferences=Preferences.objects.all().first()
    return getUsedUsdtForRobot15mAsUsdt()*100/myPreferences.maxLimitForRobot15mAsUsdt

def getUsedPercentageOfRobot15mWITHRealMargin():
    myPreferences=Preferences.objects.all().first()
    return getUsedUsdtForRobot15mWITHRealMarginAsUsdt()*100/myPreferences.maxLimitForRobot15mWITHRealMarginAsUsdt

def getUsedPercentageOfRobot15mSlow():
    myPreferences=Preferences.objects.all().first()
    return getUsedUsdtForRobot15mSlowAsUsdt()*100/myPreferences.maxLimitForRobot15mSlowAsUsdt

def getUsedPercentageOfRobot1h():
    myPreferences=Preferences.objects.all().first()
    return getUsedUsdtForRobot1hAsUsdt()*100/myPreferences.maxLimitForRobot1hAsUsdt

def getUsedPercentageOfMarginRobot():
    myPreferences=Preferences.objects.all().first()
    return getUsedUsdtForMarginRobotAsUsdt()*100/myPreferences.maxLimitForMarginAsUsdt

def getUsedPercentageOfMarginBTCRobot():
    myPreferences=Preferences.objects.all().first()
    return getUsedUsdtForMarginBTCRobotAsUsdt()*100/myPreferences.maxLimitForMarginBTCAsUsdt

def getUsedUsdtForRobotAsUsdt():
    result=0.0
    tradesAll=Trade.objects.filter(buyedByRobot=True,isMargin=False,strategy='RSI_4h').exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS'))
    for trade in tradesAll:
        result=result+trade.getTotalPrice()
    return result

def getUsedUsdtForRobot15mAsUsdt():
    result=0.0
    tradesAll=Trade.objects.filter(buyedByRobot=True,isMargin=False,strategy='RSI_15m').exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS'))
    for trade in tradesAll:
        result=result+trade.getTotalPrice()
    return result

def getUsedUsdtForRobot15mWITHRealMarginAsUsdt():
    result=0.0
    tradesAll=Trade.objects.filter(buyedByRobot=True,isMargin=False,strategy='RSI_15m_WITHRealMargin').exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS'))
    for trade in tradesAll:
        result=result+trade.getTotalPrice()
    return result

def getUsedUsdtForRobot15mSlowAsUsdt():
    result=0.0
    tradesAll=Trade.objects.filter(buyedByRobot=True,isMargin=False,strategy='RSI_15m_Slow').exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS'))
    for trade in tradesAll:
        result=result+trade.getTotalPrice()
    return result

def getUsedUsdtForRobot1hAsUsdt():
    result=0.0
    tradesAll=Trade.objects.filter(buyedByRobot=True,isMargin=False,strategy='RSI_1h').exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS'))
    for trade in tradesAll:
        result=result+trade.getTotalPrice()
    return result

def getUsedUsdtForMarginRobotAsUsdt():
    result=0.0
    tradesAll=Trade.objects.filter(isMargin=True).exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS'))
    for trade in tradesAll:
        result=result+trade.getTotalPrice()
    return result

def getUsedUsdtForMarginBTCRobotAsUsdt():
    result=0.0
    tradesAll=Trade.objects.filter(isMargin=True,coin__in=Coin.objects.filter(name__startswith='BTC'))
    for trade in tradesAll:
        result=result+trade.getTotalPrice()
    return result

def getNewValuesOfUsedUsdtForRobotAsUsdt():
    result=0.0
    tradesAll=Trade.objects.filter(buyedByRobot=True,isMargin=False,strategy='RSI_4h').exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS'))
    for trade in tradesAll:
        newPrice=getActivePrice(trade.coin.name,trade.exchangePair.name)
        result=result+(trade.count*newPrice)
    return result

def getNewValuesOfUsedUsdtForRobot15mAsUsdt():
    result=0.0
    tradesAll=Trade.objects.filter(buyedByRobot=True,isMargin=False,strategy='RSI_15m').exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS'))
    for trade in tradesAll:
        newPrice=getActivePrice(trade.coin.name,trade.exchangePair.name)
        result=result+(trade.count*newPrice)
    return result
    
def getNewValuesOfUsedUsdtForRobot15mWITHRealMarginAsUsdt():
    result=0.0
    tradesAll=Trade.objects.filter(buyedByRobot=True,isMargin=False,strategy='RSI_15m_WITHRealMargin').exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS'))
    for trade in tradesAll:
        newPrice=getActivePrice(trade.coin.name,trade.exchangePair.name)
        result=result+(trade.count*newPrice)
    return result

def getNewValuesOfUsedUsdtForRobot15mSlowAsUsdt():
    result=0.0
    tradesAll=Trade.objects.filter(buyedByRobot=True,isMargin=False,strategy='RSI_15m_Slow').exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS'))
    for trade in tradesAll:
        newPrice=getActivePrice(trade.coin.name,trade.exchangePair.name)
        result=result+(trade.count*newPrice)
    return result

def getNewValuesOfUsedUsdtForRobot1hAsUsdt():
    result=0.0
    tradesAll=Trade.objects.filter(buyedByRobot=True,isMargin=False,strategy='RSI_1h').exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS'))
    for trade in tradesAll:
        newPrice=getActivePrice(trade.coin.name,trade.exchangePair.name)
        result=result+(trade.count*newPrice)
    return result

def getNewValuesOfUsedUsdtForMarginRobotAsUsdt():
    result=0.0
    tradesAll=Trade.objects.filter(isMargin=True).exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS'))
    for trade in tradesAll:
        newPrice=getActivePrice(trade.coin.name,trade.exchangePair.name)
        result=result+(trade.count*newPrice)
    return result

def getNewValuesOfUsedUsdtForMarginBTCRobotAsUsdt():
    result=0.0
    tradesAll=Trade.objects.filter(isMargin=True,coin__in=Coin.objects.filter(name__startswith='BTC'))
    for trade in tradesAll:
        newPrice=getActivePrice(trade.coin.name,trade.exchangePair.name)
        result=result+(trade.count*newPrice)
    return result

def getUsedUsdtForEarn():
    result=0.0
    tradesAll=Trade.objects.filter(coin=(Coin.objects.get(name='USDT')),isPassiveInEarn=True)
    for trade in tradesAll:
        result=result+(trade.count*trade.price)
    return result

def getNewUsedTradeForEarn():
    result=0.0
    tradesAll=Trade.objects.filter(isPassiveInEarn=True).exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS'))
    for trade in tradesAll:
        newPrice=getActivePrice(trade.coin.name,trade.exchangePair.name)
        result=result+(trade.count*newPrice)
    return result

def getOldUsedTradeForEarn():
    result=0.0
    tradesAll=Trade.objects.filter(isPassiveInEarn=True).exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS'))
    for trade in tradesAll:
        result=result+(trade.count*trade.price)
    return result

def getOldOtherExchangeUsdt():
    result=0.0
    tradesAll=Trade.objects.filter(isDifferentExchange=True)
    for trade in tradesAll:
        result=result+(trade.count*trade.price)
    return result

def getNewOtherExchangeUsdt():
    result=0.0
    tradesAll=Trade.objects.filter(isDifferentExchange=True)
    for trade in tradesAll:
        result=result+(trade.count*trade.temp_currentPrice)
    return result

def getUsedUsdtForManuelAsUsdt():
    result=0.0
    tradesAll=Trade.objects.filter(buyedByRobot=False).exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS'))
    for trade in tradesAll:
        result=result+trade.getTotalPrice()
    return result

def getOldValuesOfUsedUsdtForManuelAsUsdt():
    result=0.0
    tradesAll=Trade.objects.filter(buyedByRobot=False,isPassiveInEarn=False).exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS'))
    for trade in tradesAll:
        result=result+(trade.count*trade.price)
    return result

def getNewValuesOfUsedUsdtForManuelAsUsdt():
    result=0.0
    tradesAll=Trade.objects.filter(buyedByRobot=False,isPassiveInEarn=False).exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS'))
    for trade in tradesAll:
        newPrice=getActivePrice(trade.coin.name,trade.exchangePair.name)
        result=result+(trade.count*newPrice)
    return result

def cleanAllPastCoinSignals(coinName):
    activeCoin=Coin.objects.get(name=coinName)
    activeCoin.moveRSI15mComeBackRSIValueForUsdt=0
    activeCoin.moveRSI15mComeBackRSIValueForBtc=0
    activeCoin.moveRSI15mWITHRealMarginComeBackRSIValueForUsdt=0
    activeCoin.moveRSI15mWITHRealMarginComeBackRSIValueForBtc=0
    activeCoin.moveRSI15mSlowComeBackRSIValueForUsdt=0
    activeCoin.moveRSI15mSlowComeBackRSIValueForBtc=0
    activeCoin.moveRSI1hComeBackRSIValueForUsdt=0
    activeCoin.moveRSI1hComeBackRSIValueForBtc=0
    activeCoin.moveRSIMarginBtcComeBackRSIValueForUsdt=0
    activeCoin.moveRSIMarginLongComeBackRSIValueForUsdt=0
    activeCoin.save()
    return activeCoin

def isStopLossTriggeredForTrade(myTrade,prefStopLossTriggerStartPercentage,prefStopLossTriggerStopPercentage):
    sellForStopLossTriggerResult= False
    gainByTradeAsPercentage=getGainByTradeAsPercentage(myTrade)
    if myTrade.stopLossLastTriggeredPercentage>0:
        if myTrade.stopLossLastTriggeredPercentage<gainByTradeAsPercentage:
            myTrade.stopLossLastTriggeredPercentage=gainByTradeAsPercentage
            myTrade.save()#Sorun olursa bu if icerisinde nesneyi bastan çağırıp save edeceğim.
        elif (myTrade.stopLossLastTriggeredPercentage>gainByTradeAsPercentage) and (gainByTradeAsPercentage<(myTrade.stopLossLastTriggeredPercentage-prefStopLossTriggerStopPercentage)):
            sellForStopLossTriggerResult=True
    elif gainByTradeAsPercentage>=prefStopLossTriggerStartPercentage:
        myTrade.stopLossLastTriggeredPercentage=gainByTradeAsPercentage# stopLossTriggerStopPercentage
        myTrade.save()#Sorun olursa bu if icerisinde nesneyi bastan çağırıp save edeceğim.
    return sellForStopLossTriggerResult

###################################################################################################################################################################3
def sellSignal(firstCoinToCompareParameter,secondCoinToCompareParameter,firstCoinForSellParameter,secondCoinForSellParameter,myTrade,isBtcHigherThan10PercentageFromEma):
    signal_sell=0
    if getIsMarginCoin(firstCoinForSellParameter) == False:
        global resultMail
        global nearlySellCoins
        activeCoinToCompare=firstCoinToCompareParameter+secondCoinToCompareParameter
        myPreferences=Preferences.objects.all().first()
        midRSI=myPreferences.midRSI# maxRSI=getActiveMaxRSI(myPreferences,isBtcHigherThan10PercentageFromEma)
        maxRSI=myPreferences.maxRSI
        RSI_15m=RSI_30m=RSI_1h=RSI_2h=RSI_4h=0
        RSI_15m=int(getRSI(activeCoinToCompare,'15m',5000))
        RSI_30m=int(getRSI(activeCoinToCompare,'30m',5000))
        RSI_1h=int(getRSI(activeCoinToCompare,'1h',5000))
        RSI_2h=int(getRSI(activeCoinToCompare,'2h',5000))
        RSI_4h=int(getRSI(activeCoinToCompare,'4h',5000))
        WilliamR_1d=int(getWilliamR(activeCoinToCompare,'1d',5000))
        cooldownPassed=getIsCooldownSellPassedForTrade(myTrade)
        indicatorResultsString = 'R15:',RSI_15m,'R30:',RSI_30m,'R1h:',RSI_1h,'<br>R2h:',RSI_2h,'<b>R4h:</b><b class="blue">',RSI_4h,'</b>W1d:',WilliamR_1d
        indicatorResults = fixString(indicatorResultsString)
        updateTradesWithIndicatorResults(firstCoinToCompareParameter,indicatorResults)
        minOrMaxFivePercChangePassed= True
        isStopLossTriggered = False
        if myTrade is not None:
            minOrMaxFivePercChangePassed=getGainByTradeAsPercentage(myTrade)>myPreferences.targetPercentageForSelling
            isStopLossTriggered = getGainByTradeAsPercentage(myTrade)<(myPreferences.stopPercentageForSellingForRobot15m -5)
        allOverMidRSIControlPassed=RSI_15m>midRSI and RSI_30m>midRSI and RSI_1h>midRSI and RSI_2h>midRSI and RSI_4h>midRSI
        maxRSIControlFor4hAndOneAnotherControlPassed=((RSI_15m!=100 and RSI_15m>maxRSI) or (RSI_30m!=100 and RSI_30m>maxRSI) or (RSI_1h!=100 and RSI_1h>maxRSI) or (RSI_2h!=100 and RSI_2h>maxRSI)) and (RSI_4h!=100 and RSI_4h>maxRSI)
        resultMail=resultMail,' <br>  R15:',RSI_15m,' - R30:',RSI_30m ,' - R1h:',RSI_1h ,' - R2h:',RSI_2h  ,' - <b>R4h:</b> ',RSI_4h ,' - allOverMidRSIControlPassed:',allOverMidRSIControlPassed,' - maxRSIControlFor4hAndOneAnotherControlPassed:',maxRSIControlFor4hAndOneAnotherControlPassed, ' minOrMaxFivePercChangePassed:',minOrMaxFivePercChangePassed,' cooldownPassed:',cooldownPassed ,' - Sell Signal:- ',firstCoinToCompareParameter 
        if (RSI_4h+5)>=maxRSI and cooldownPassed:
            indicatorResultsStringForMail = 'R15:',RSI_15m,' - R30:',RSI_30m,' - R1h:',RSI_1h,' - R2h:',RSI_2h,' - <b>R4h:</b><b>',RSI_4h,'</b>'
            indicatorResultsForMail = fixString(indicatorResultsStringForMail)
            nearlySellCoins=nearlySellCoins,' <br> ',firstCoinToCompareParameter,' => ', indicatorResultsForMail
        if (allOverMidRSIControlPassed and maxRSIControlFor4hAndOneAnotherControlPassed):
            if myTrade == None and firstCoinForSellParameter=='BTC' and secondCoinForSellParameter:
                signal_sell=1#print('Sell signal sadece Btc durumu sorguladigi icin satis yapmadi')
            elif (cooldownPassed and minOrMaxFivePercChangePassed) or isStopLossTriggered:
                signal_sell=1
                finalQuantity=minimizeNumber(findQuantityByTradeToSell(myTrade))
                sellWithMarketPriceByQuantityAction(firstCoinForSellParameter,secondCoinForSellParameter,finalQuantity,myTrade)
        else :
            signal_sell=0
    return signal_sell

def sellSignalForRobot1h(firstCoinToCompareParameter,secondCoinToCompareParameter,firstCoinForSellParameter,secondCoinForSellParameter,myTrade):
    signal_sell=0
    if getIsMarginCoin(firstCoinForSellParameter) == False:
        global resultMail
        global nearlySellCoins
        activeCoinToCompareForBTC=firstCoinToCompareParameter+'BTC'
        activeCoinToCompareForUSDT=firstCoinToCompareParameter+'USDT'
        myPreferences=Preferences.objects.all().first()
        maxRSI=myPreferences.maxRSIForRobot1h
        RSI_1h_BTC=int(getRSI(activeCoinToCompareForBTC,'1h',5000))
        RSI_1h_USDT=int(getRSI(activeCoinToCompareForUSDT,'1h',5000))
        minPercChangePassed= True
        isStopLossTriggered = givenLimitHoursPassed =False
        #isLimitTriggered = False
        resultMail=resultMail,' <br>  R1h: btc:',RSI_1h_BTC,'usdt:',RSI_1h_USDT,' - Robot RSI_1h Sell Signal:- ',firstCoinToCompareParameter 
        indicatorResultsString = '<b>R1h:</b><b class="blue">btc:',RSI_1h_BTC,' usdt:',RSI_1h_USDT,'</b>'
        indicatorResults = fixString(indicatorResultsString)
        updateRobot1hTradesWithIndicatorResults(firstCoinForSellParameter,indicatorResults)
        #sellForStopLossTriggerResult= False
        if myTrade is not None:
            gainTrade = getGainByTradeAsPercentage(myTrade)
            minPercChangePassed=gainTrade>myPreferences.targetPercentageForSellingForRobot1h
            givenLimitHoursPassed=gainTrade>0.15 and hourDiff(myTrade.transactionDate,datetime.now())>myPreferences.givenLimitHoursForRobot1hThenTryToSell #sat sinyaline aşağıda bakacak ama burada "kar oranı limiti geçtiyse" veya "4 saati geçmişse kar oranına bakmadan + daysa" geriye true döner
            #sellForStopLossTriggerResult=isStopLossTriggeredForTrade(myTrade,myPreferences.stopLossTriggerStartPercentage,myPreferences.stopLossTriggerStopPercentage)
            isStopLossTriggered = gainTrade<myPreferences.stopPercentageForSellingForRobot1h
            #isLimitTriggered = getGainByTradeAsPercentage(myTrade)>myPreferences.limitPercentageForSellingForRobot15m
        sellingAccordingToBTC=(RSI_1h_BTC!=100 and RSI_1h_BTC>=maxRSI) and RSI_1h_USDT>50
        sellingAccordingToUSDT=(RSI_1h_USDT!=100 and RSI_1h_USDT>=maxRSI) and RSI_1h_BTC>50
        maxRSIControlPassed=sellingAccordingToBTC or sellingAccordingToUSDT
        if ((RSI_1h_USDT+5)>=maxRSI or (RSI_1h_BTC+5)>=maxRSI):
            indicatorResultsStringForMail = 'R1h: btc:',RSI_1h_BTC,' usdt:',RSI_1h_USDT
            indicatorResultsForMail = fixString(indicatorResultsStringForMail)
            nearlySellCoins=nearlySellCoins,' <br> ',firstCoinToCompareParameter,' => ', indicatorResultsForMail
        if (maxRSIControlPassed and minPercChangePassed) or givenLimitHoursPassed or isStopLossTriggered :# or isLimitTriggered sellForStopLossTriggerResult
            cleanAllPastCoinSignals(firstCoinForSellParameter)
            signal_sell=1
            finalQuantity=minimizeNumber(myTrade.count)
            sellWithMarketPriceByQuantityAction(firstCoinForSellParameter,secondCoinForSellParameter,finalQuantity,myTrade)
        else :
            signal_sell=0
    return signal_sell

def sellSignalForRobot15m(firstCoinToCompareParameter,secondCoinToCompareParameter,firstCoinForSellParameter,secondCoinForSellParameter,myTrade):
    signal_sell=0
    if getIsMarginCoin(firstCoinForSellParameter) == False:
        global resultMail
        global nearlySellCoins
        #activeCoinToCompareForBTC=firstCoinToCompareParameter+'BTC'
        activeCoinToCompareForUSDT=firstCoinToCompareParameter+'USDT'
        myPreferences=Preferences.objects.all().first()
        maxRSI=myPreferences.maxRSIFor15mWITHRealMargin
        #RSI_15m_BTC=int(getRSI(activeCoinToCompareForBTC,'15m',5000))
        RSI_15m_USDT=int(getRSI(activeCoinToCompareForUSDT,'15m',5000))
        #RSI_5m_USDT=int(getRSI(activeCoinToCompareForUSDT,'5m',5000))
        minPercChangePassed= True
        isStopLossTriggered = givenLimitHoursPassed =False
        #isLimitTriggered = False
        resultMail=resultMail,' <br>  R15: usdt:',RSI_15m_USDT,' - Robot RSI_15m Sell Signal:- ',firstCoinToCompareParameter 
        indicatorResultsString = '<b>R15:</b><b class="blue">usdt:',RSI_15m_USDT,'</b>'
        indicatorResults = fixString(indicatorResultsString)
        updateRobot15mTradesWithIndicatorResults(firstCoinForSellParameter,indicatorResults)
        #sellForStopLossTriggerResult= False
        if myTrade is not None:
            gainTrade = getGainByTradeAsPercentage(myTrade)
            minPercChangePassed=gainTrade>myPreferences.targetPercentageForSellingForRobot15m
            givenLimitHoursPassed=gainTrade>0.15 and hourDiff(myTrade.transactionDate,datetime.now())>myPreferences.givenLimitHoursForRobot15mThenTryToSell #sat sinyaline aşağıda bakacak ama burada "kar oranı limiti geçtiyse" veya "4 saati geçmişse kar oranına bakmadan + daysa" geriye true döner
            #sellForStopLossTriggerResult=isStopLossTriggeredForTrade(myTrade,myPreferences.stopLossTriggerStartPercentage,myPreferences.stopLossTriggerStopPercentage)
            isStopLossTriggered = gainTrade<myPreferences.stopPercentageForSellingForRobot15m
            #isLimitTriggered = getGainByTradeAsPercentage(myTrade)>myPreferences.limitPercentageForSellingForRobot15m
        #sellingAccordingToBTC=(RSI_15m_BTC!=100 and RSI_15m_BTC>=maxRSI) and RSI_15m_USDT>50
        sellingAccordingToUSDT=(RSI_15m_USDT!=100 and RSI_15m_USDT>=maxRSI) #and RSI_5m_USDT>=maxRSI #and RSI_15m_BTC>50
        maxRSIControlPassed=sellingAccordingToUSDT #or sellingAccordingToBTC
        if ((RSI_15m_USDT+5)>=maxRSI) : #or (RSI_15m_BTC+5)>=maxRSI
            indicatorResultsStringForMail = 'R15: usdt:',RSI_15m_USDT
            indicatorResultsForMail = fixString(indicatorResultsStringForMail)
            nearlySellCoins=nearlySellCoins,' <br> ',firstCoinToCompareParameter,' => ', indicatorResultsForMail
        if (maxRSIControlPassed and minPercChangePassed) or givenLimitHoursPassed or isStopLossTriggered:# or isLimitTriggered  or sellForStopLossTriggerResult
            cleanAllPastCoinSignals(firstCoinForSellParameter)
            signal_sell=1
            finalQuantity=minimizeNumber(myTrade.count)
            sellWithMarketPriceByQuantityAction(firstCoinForSellParameter,secondCoinForSellParameter,finalQuantity,myTrade)
        else :
            signal_sell=0
    return signal_sell

""" def sellSignalForRobot15m(firstCoinToCompareParameter,secondCoinToCompareParameter,firstCoinForSellParameter,secondCoinForSellParameter,myTrade):
    signal_sell=0
    if getIsMarginCoin(firstCoinForSellParameter) == False:
        global resultMail
        global nearlySellCoins
        #activeCoinToCompareForBTC=firstCoinToCompareParameter+'BTC'
        activeCoinToCompareForUSDT=firstCoinToCompareParameter+'USDT'
        myPreferences=Preferences.objects.all().first()
        maxRSI=myPreferences.maxRSIForLong
        #RSI_15m_BTC=int(getRSI(activeCoinToCompareForBTC,'15m',5000))
        RSI_15m_USDT=int(getRSI(activeCoinToCompareForUSDT,'15m',5000))
        #RSI_5m_USDT=int(getRSI(activeCoinToCompareForUSDT,'5m',5000))
        minPercChangePassed= True
        isStopLossTriggered = givenLimitHoursPassed =False
        #isLimitTriggered = False
        resultMail=resultMail,' <br>  R15: usdt:',RSI_15m_USDT,' - Robot RSI_15m Sell Signal:- ',firstCoinToCompareParameter 
        indicatorResultsString = '<b>R15:</b><b class="blue">usdt:',RSI_15m_USDT,'</b>'
        indicatorResults = fixString(indicatorResultsString)
        updateRobot15mTradesWithIndicatorResults(firstCoinForSellParameter,indicatorResults)
        #sellForStopLossTriggerResult= False
        if myTrade is not None:
            gainTrade = getGainByTradeAsPercentage(myTrade)
            minPercChangePassed=gainTrade>myPreferences.targetPercentageForSellingForRobot15m
            givenLimitHoursPassed=gainTrade>0.15 and hourDiff(myTrade.transactionDate,datetime.now())>myPreferences.givenLimitHoursForRobot15mThenTryToSell #sat sinyaline aşağıda bakacak ama burada "kar oranı limiti geçtiyse" veya "4 saati geçmişse kar oranına bakmadan + daysa" geriye true döner
            #sellForStopLossTriggerResult=isStopLossTriggeredForTrade(myTrade,myPreferences.stopLossTriggerStartPercentage,myPreferences.stopLossTriggerStopPercentage)
            isStopLossTriggered = gainTrade<myPreferences.stopPercentageForSellingForRobot15m
            #isLimitTriggered = getGainByTradeAsPercentage(myTrade)>myPreferences.limitPercentageForSellingForRobot15m
        #sellingAccordingToBTC=(RSI_15m_BTC!=100 and RSI_15m_BTC>=maxRSI) and RSI_15m_USDT>50
        sellingAccordingToUSDT=(RSI_15m_USDT!=100 and RSI_15m_USDT>=maxRSI) #and RSI_5m_USDT>=maxRSI #and RSI_15m_BTC>50
        maxRSIControlPassed=sellingAccordingToUSDT #or sellingAccordingToBTC
        if ((RSI_15m_USDT+5)>=maxRSI) : #or (RSI_15m_BTC+5)>=maxRSI
            indicatorResultsStringForMail = 'R15: usdt:',RSI_15m_USDT
            indicatorResultsForMail = fixString(indicatorResultsStringForMail)
            nearlySellCoins=nearlySellCoins,' <br> ',firstCoinToCompareParameter,' => ', indicatorResultsForMail
        if (maxRSIControlPassed and minPercChangePassed) or givenLimitHoursPassed or isStopLossTriggered:# or isLimitTriggered  or sellForStopLossTriggerResult
            cleanAllPastCoinSignals(firstCoinForSellParameter)
            signal_sell=1
            finalQuantity=minimizeNumber(myTrade.count)
            sellWithMarketPriceByQuantityAction(firstCoinForSellParameter,secondCoinForSellParameter,finalQuantity,myTrade)
        else :
            signal_sell=0
    return signal_sell """

def sellSignalForRobot15mWITHRealMargin(firstCoinToCompareParameter,secondCoinToCompareParameter,firstCoinForSellParameter,secondCoinForSellParameter,myTrade):
    signal_sell=0
    if getIsMarginCoin(firstCoinForSellParameter) == False:
        global resultMail
        global nearlySellCoins
        activeCoinToCompareForUSDT=firstCoinToCompareParameter+'USDT'
        myPreferences=Preferences.objects.all().first()
        maxRSI=myPreferences.maxRSIFor15mWITHRealMargin
        RSI_15m_USDT=int(getRSI(activeCoinToCompareForUSDT,'15m',5000))
        minPercChangePassed= True
        isStopLossTriggered = givenLimitHoursPassed =False
        resultMail=resultMail,' <br>  R15: usdt:',RSI_15m_USDT,' - Robot RSI_15m Sell Signal:- ',firstCoinToCompareParameter 
        indicatorResultsString = '<b>R15:</b><b class="blue">usdt:',RSI_15m_USDT,'</b>'
        indicatorResults = fixString(indicatorResultsString)
        updateRobot15mTradesWITHRealMarginWithIndicatorResults(firstCoinForSellParameter,indicatorResults)
        if myTrade is not None:
            gainTrade = getGainByTradeAsPercentage(myTrade)
            minPercChangePassed=gainTrade>myPreferences.targetPercentageForSellingForRobot15m
            givenLimitHoursPassed=gainTrade>0.15 and hourDiff(myTrade.transactionDate,datetime.now())>myPreferences.givenLimitHoursForRobot15mThenTryToSell #sat sinyaline aşağıda bakacak ama burada "kar oranı limiti geçtiyse" veya "4 saati geçmişse kar oranına bakmadan + daysa" geriye true döner
            isStopLossTriggered = gainTrade<myPreferences.stopPercentageForSellingForRobot15m
        sellingAccordingToUSDT=(RSI_15m_USDT!=100 and RSI_15m_USDT>=maxRSI) #and RSI_5m_USDT>=maxRSI #and RSI_15m_BTC>50
        maxRSIControlPassed=sellingAccordingToUSDT #or sellingAccordingToBTC
        if ((RSI_15m_USDT+5)>=maxRSI) : #or (RSI_15m_BTC+5)>=maxRSI
            indicatorResultsStringForMail = 'R15: usdt:',RSI_15m_USDT
            indicatorResultsForMail = fixString(indicatorResultsStringForMail)
            nearlySellCoins=nearlySellCoins,' <br> ',firstCoinToCompareParameter,' => ', indicatorResultsForMail
        if (maxRSIControlPassed and minPercChangePassed) or givenLimitHoursPassed or isStopLossTriggered:# or isLimitTriggered  or sellForStopLossTriggerResult
            cleanAllPastCoinSignals(firstCoinForSellParameter)
            signal_sell=1
            finalQuantity=minimizeNumber(myTrade.count)
            sellWithMarketPriceByQuantityAction(firstCoinForSellParameter,secondCoinForSellParameter,finalQuantity,myTrade)
        else :
            signal_sell=0
    return signal_sell

def sellSignalForRobot15mSlow(firstCoinToCompareParameter,secondCoinToCompareParameter,firstCoinForSellParameter,secondCoinForSellParameter,myTrade):
    signal_sell=0
    if getIsMarginCoin(firstCoinForSellParameter) == False:
        global resultMail
        global nearlySellCoins
        activeCoinToCompareForBTC=firstCoinToCompareParameter+'BTC'
        activeCoinToCompareForUSDT=firstCoinToCompareParameter+'USDT'
        myPreferences=Preferences.objects.all().first()
        maxRSI=myPreferences.maxRSIFor15mSlow
        maxRSI1h=myPreferences.maxRSIFor1hSlow
        RSI_15m_BTC=int(getRSI(activeCoinToCompareForBTC,'15m',5000))
        RSI_15m_USDT=int(getRSI(activeCoinToCompareForUSDT,'15m',5000))
        RSI_1h_BTC=int(getRSI(activeCoinToCompareForBTC,'1h',5000))
        RSI_1h_USDT=int(getRSI(activeCoinToCompareForUSDT,'1h',5000))
        minPercChangePassed= True
        isStopLossTriggered = givenLimitHoursPassed =False
        resultMail=resultMail,' <br>  R15: btc:',RSI_15m_BTC,'usdt:',RSI_15m_USDT,'usdt1h:',RSI_1h_USDT,' - Robot RSI_15m_Slow Sell Signal:- ',firstCoinToCompareParameter 
        indicatorResultsString = '<b>R15:</b><b class="blue">btc:',RSI_15m_BTC,' usdt:',RSI_15m_USDT,'</b>'
        indicatorResults = fixString(indicatorResultsString)
        updateRobot15mSlowTradesWithIndicatorResults(firstCoinForSellParameter,indicatorResults)
        #sellForStopLossTriggerResult= False
        if myTrade is not None:
            gainTrade = getGainByTradeAsPercentage(myTrade)
            givenLimitHoursPassed=gainTrade>0.15 and hourDiff(myTrade.transactionDate,datetime.now())>myPreferences.givenLimitHoursForRobot15mSlowThenTryToSell #sat sinyaline aşağıda bakacak ama burada "kar oranı limiti geçtiyse" veya "4 saati geçmişse kar oranına bakmadan + daysa" geriye true döner
            minPercChangePassed=gainTrade>myPreferences.targetPercentageForSellingForRobot15mSlow
            #sellForStopLossTriggerResult=isStopLossTriggeredForTrade(myTrade,myPreferences)
            isStopLossTriggered = gainTrade<myPreferences.stopPercentageForSellingForRobot15mSlow
        sellingAccordingToBTC=(RSI_15m_BTC!=100 and RSI_15m_BTC>=maxRSI) and (RSI_1h_BTC!=100 and RSI_1h_BTC>=maxRSI1h) and RSI_15m_USDT>50 and RSI_1h_USDT>50 
        sellingAccordingToUSDT=(RSI_15m_USDT!=100 and RSI_15m_USDT>=maxRSI) and (RSI_1h_USDT!=100 and RSI_1h_USDT>=maxRSI1h) and RSI_15m_BTC>50 and RSI_1h_BTC>50
        maxRSIControlPassed=sellingAccordingToBTC or sellingAccordingToUSDT
        if ((RSI_15m_USDT+5)>=maxRSI or (RSI_15m_BTC+5)>=maxRSI):
            indicatorResultsStringForMail = 'R15: btc:',RSI_15m_BTC,' usdt:',RSI_15m_USDT, ' usdt1h:', RSI_1h_USDT
            indicatorResultsForMail = fixString(indicatorResultsStringForMail)
            nearlySellCoins=nearlySellCoins,' <br> ',firstCoinToCompareParameter,' => ', indicatorResultsForMail
        if (maxRSIControlPassed and minPercChangePassed) or givenLimitHoursPassed or isStopLossTriggered:# or isLimitTriggered  or sellForStopLossTriggerResult
            cleanAllPastCoinSignals(firstCoinForSellParameter)
            signal_sell=1
            finalQuantity=minimizeNumber(myTrade.count)
            sellWithMarketPriceByQuantityAction(firstCoinForSellParameter,secondCoinForSellParameter,finalQuantity,myTrade)
        else :
            signal_sell=0
    return signal_sell

def sellSignalForMarginLong(firstCoinToCompareParameter,secondCoinToCompareParameter,firstCoinForSellParameter,secondCoinForSellParameter,myTrade):
    signal_sell=0
    if getIsMarginCoin(firstCoinForSellParameter) == True:
        global resultMail
        #activeCoinToCompareForBTC=firstCoinToCompareParameter+'BTC'
        activeCoinToCompareForUSDT=firstCoinToCompareParameter+'USDT'
        myPreferences=Preferences.objects.all().first()
        maxRSI=myPreferences.maxRSIForLong
        #RSI_15m_BTC=int(getRSI(activeCoinToCompareForBTC,'15m',5000))
        RSI_15m_USDT=int(getRSI(activeCoinToCompareForUSDT,'15m',5000))
        #RSI_5m_USDT=int(getRSI(activeCoinToCompareForUSDT,'5m',5000))
        minPercChangePassed= True
        isStopLossTriggered = givenLimitHoursPassed =False
        #isLimitTriggered = False
        resultMail=resultMail,' <br>  R15: usdt:',RSI_15m_USDT,' - Margin Long Sell Signal:- ',firstCoinToCompareParameter 
        indicatorResultsString = '<b>R15:</b><b class="blue">usdt:',RSI_15m_USDT,'</b>'
        indicatorResults = fixString(indicatorResultsString)
        updateTradesWithIndicatorResults(firstCoinForSellParameter,indicatorResults)
        sellForStopLossTriggerResult= False
        if myTrade is not None:
            gainTrade = getGainByTradeAsPercentage(myTrade)
            minPercChangePassed=gainTrade>myPreferences.targetPercentageForLongSellingForMargin
            givenLimitHoursPassed=gainTrade>0.15 and hourDiff(myTrade.transactionDate,datetime.now())>myPreferences.givenLimitHoursForRobotMarginThenTryToSell #sat sinyaline aşağıda bakacak ama burada "kar oranı limiti geçtiyse" veya "2 saati geçmişse kar oranına bakmadan + daysa" geriye true döner
            sellForStopLossTriggerResult=isStopLossTriggeredForTrade(myTrade,myPreferences.stopLossTriggerStartPercentage,myPreferences.stopLossTriggerStopPercentage)
            isStopLossTriggered = gainTrade<myPreferences.stopPercentageForSellingForMargin
            #isLimitTriggered = getGainByTradeAsPercentage(myTrade)>myPreferences.limitPercentageForSellingForMargin
        #sellingAccordingToBTC=(RSI_15m_BTC!=100 and RSI_15m_BTC>=maxRSI) and RSI_15m_USDT>50
        sellingAccordingToUSDT=(RSI_15m_USDT!=100 and RSI_15m_USDT>=maxRSI) #and RSI_5m_USDT>=maxRSI #and RSI_15m_BTC>50
        maxRSIControlPassed=sellingAccordingToUSDT #or sellingAccordingToBTC
        if (maxRSIControlPassed and minPercChangePassed) or givenLimitHoursPassed or isStopLossTriggered or sellForStopLossTriggerResult:# or isLimitTriggered
            cleanAllPastCoinSignals(firstCoinForSellParameter)
            signal_sell=1
            finalQuantity=minimizeNumber(myTrade.count)
            sellWithMarketPriceByQuantityAction(firstCoinForSellParameter,secondCoinForSellParameter,finalQuantity,myTrade)
        else :
            signal_sell=0
    return signal_sell

def sellSignalForMarginLongForBtc(firstCoinToCompareParameter,secondCoinToCompareParameter,firstCoinForSellParameter,secondCoinForSellParameter,myTrade):
    signal_sell=0
    if getIsMarginCoin(firstCoinForSellParameter) == True:
        global resultMail
        activeCoinToCompare=firstCoinToCompareParameter+secondCoinToCompareParameter
        myPreferences=Preferences.objects.all().first()
        maxRSI=myPreferences.maxRSIForLongForBTC
        RSI_15m=0
        RSI_15m=int(getRSI(activeCoinToCompare,'15m',5000))
        RSI_5m=int(getRSI(activeCoinToCompare,'5m',5000))
        minPercChangePassed= True
        isStopLossTriggered = givenLimitHoursPassed =False
        resultMail=resultMail,' <br>  R15: ',RSI_15m,' - MarginBTC Long Sell Signal:- ',firstCoinToCompareParameter 
        indicatorResultsString = '<b>R15:</b><b class="blue">',RSI_15m,'</b>'
        indicatorResults = fixString(indicatorResultsString)
        updateTradesWithIndicatorResults(firstCoinForSellParameter,indicatorResults)
        sellForStopLossTriggerResult= False
        if myTrade is not None:
            gainTrade = getGainByTradeAsPercentage(myTrade)
            minPercChangePassed=(gainTrade>myPreferences.targetPercentageForLongSellingForMarginBTC)
            givenLimitHoursPassed=gainTrade>0.15 and hourDiff(myTrade.transactionDate,datetime.now())>myPreferences.givenLimitHoursForRobotMarginThenTryToSell #sat sinyaline aşağıda bakacak ama burada "kar oranı limiti geçtiyse" veya "2 saati geçmişse kar oranına bakmadan + daysa" geriye true döner
            sellForStopLossTriggerResult=isStopLossTriggeredForTrade(myTrade,myPreferences.stopLossTriggerStartPercentageMarginBTC,myPreferences.stopLossTriggerStopPercentageMarginBTC)
            isStopLossTriggered = gainTrade<myPreferences.stopPercentageForSellingForMarginBTC
        maxRSIControlPassed= (RSI_15m!=100 and RSI_15m>=maxRSI and RSI_5m>=maxRSI)
        if (maxRSIControlPassed and minPercChangePassed) or givenLimitHoursPassed or isStopLossTriggered or sellForStopLossTriggerResult:
            cleanAllPastCoinSignals(firstCoinForSellParameter)
            signal_sell=1
            finalQuantity=minimizeNumber(myTrade.count)
            sellWithMarketPriceByQuantityAction(firstCoinForSellParameter,secondCoinForSellParameter,finalQuantity,myTrade)
        else :
            signal_sell=0
    return signal_sell

def sellSignalForMarginShort(firstCoinToCompareParameter,secondCoinToCompareParameter,firstCoinForSellParameter,secondCoinForSellParameter,myTrade):
    signal_sell=0
    if getIsMarginCoin(firstCoinForSellParameter) == True:
        global resultMail
        activeCoinToCompare=firstCoinToCompareParameter+secondCoinToCompareParameter
        myPreferences=Preferences.objects.all().first()
        minRSI=myPreferences.minRSIForShort
        RSI_15m=0
        RSI_15m=int(getRSI(activeCoinToCompare,'15m',5000))
        minPercChangePassed= True
        isStopLossTriggered = givenLimitHoursPassed =False
        isLimitTriggered = False
        resultMail=resultMail,' <br>  R15: ',RSI_15m,' - Margin Short Sell Signal:- ',firstCoinToCompareParameter
        indicatorResultsString = '<b>R15:</b><b class="blue">',RSI_15m,'</b>'
        indicatorResults = fixString(indicatorResultsString)
        updateTradesWithIndicatorResults(firstCoinForSellParameter,indicatorResults)
        if myTrade is not None:
            gainTrade = getGainByTradeAsPercentage(myTrade)
            minPercChangePassed=gainTrade>myPreferences.targetPercentageForShortSellingForMargin
            isStopLossTriggered = gainTrade<myPreferences.stopPercentageForSellingForMargin
            isLimitTriggered = gainTrade>myPreferences.limitPercentageForSellingForMargin
        minRSIControlPassed= (RSI_15m!=100 and RSI_15m<minRSI)
        if (minRSIControlPassed and minPercChangePassed) or isStopLossTriggered or isLimitTriggered:
            cleanAllPastCoinSignals(firstCoinForSellParameter)
            signal_sell=1
            finalQuantity=minimizeNumber(myTrade.count)
            sellWithMarketPriceByQuantityAction(firstCoinForSellParameter,secondCoinForSellParameter,finalQuantity,myTrade)
        else :
            signal_sell=0
    return signal_sell

def getGainByTradeAsPercentage(myTrade):
    priceNow=getActivePrice(myTrade.coin.name,myTrade.exchangePair.name)
    return getGainPercentage(myTrade.price,priceNow)

def getGainPercentage(oldPrice,newPrice):
    if newPrice==0 or oldPrice==0:
        return 0
    else:
        return newPrice*100/oldPrice-100

def getGainByTradeAsHowManyTimes(myTrade):
    priceNow=getActivePrice(myTrade.coin.name,myTrade.exchangePair.name)
    return priceNow/myTrade.price

def isTimeToSellForManuelTradesCalculatedByPowerOfTwo(myTrade):
    result=False
    priceNow=getActivePrice(myTrade.coin.name,myTrade.exchangePair.name)
    if priceNow/myTrade.price >= pow(2, (myTrade.howManyTimesSold+1)):
        result=True
    return result

def getYesterdayPrice(firstCoin,secondCoin):
    symbol=firstCoin+secondCoin
    klines=getKlines(symbol,'1h',5000)
    while klines is None or len(klines)<1:  
        timet.sleep(60)
        klines=getKlines(symbol,'1h',5000)
    date=[float(entry[0]) for entry in klines]
    open=[float(entry[1]) for entry in klines]
    high=[float(entry[2]) for entry in klines]
    low=[float(entry[3]) for entry in klines]
    close=[float(entry[4]) for entry in klines]
    last_date=getDateFromTimestamp(date[-24])
    last_closing_price=close[-24]
    close_array=np.asarray(close)
    close_finished=close_array[-24]
    return close_finished

def getIsCooldownBuyPassedForCoin(myCoin):
    global resultMail
    result=False
    if Trade.objects.filter(buyedByRobot=True,coin=myCoin,isMargin=False,strategy='RSI_4h').exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS')).exists():
        latestTrade=Trade.objects.filter(buyedByRobot=True,coin=myCoin,isMargin=False,strategy='RSI_4h').exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS')).latest('transactionDate')
        days=dateDiff(latestTrade.transactionDate,datetime.now())
        myPreferences=Preferences.objects.all().first()
        cooldownForNewBuyFromSameCoin=myPreferences.cooldownForNewBuyFromSameCoin
        if days > cooldownForNewBuyFromSameCoin:
            result=True
        else:
            result=False
        resultMail=resultMail,'<br/><span style="color:red">Coin ve Alınmasından geçen gün sayısı :</span>',myCoin.name,'-',days,', IsCooldownSellPassedForTrade:',result,'<br/>'
    else :
        result=True
    return result

###################################################################################################################################################################4
def getIsCooldownPassedForLastNegativeTradeByCoin(myCoinName):
    global resultMail
    result=True
    adet = TradeLog.objects.filter(coinName=myCoinName,processType='SELL').exclude(coinName='USDT').exclude(coinName='OTHERS').count()
    if adet>0:
        latestTrade=TradeLog.objects.filter(coinName=myCoinName,processType='SELL').exclude(coinName='USDT').exclude(coinName='OTHERS').latest('transactionDate')
        if latestTrade.profitLossPercentage<0:
            hours=hourDiff(latestTrade.transactionDate,datetime.now())
            myPreferences=Preferences.objects.all().first()
            if hours > myPreferences.waitHoursAfterNegativeSell:
                result=True
            else:
                result=False
        else:
            result=True
    else :
        result=True
    return result

def getIsCooldownBuyPassedForCoinForRobot15m(myCoin):
    global resultMail
    result=False
    adet = Trade.objects.filter(buyedByRobot=True,coin=myCoin,isMargin=False,strategy='RSI_15m').exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS')).count()
    if adet>0:
        latestTrade=Trade.objects.filter(buyedByRobot=True,coin=myCoin,isMargin=False,strategy='RSI_15m').exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS')).latest('transactionDate')
        hours=hourDiffNormal(latestTrade.transactionDate,datetime.now())
        myPreferences=Preferences.objects.all().first()
        cooldownAsHoursForNewBuyFromSameCoinBaseForMargin= myPreferences.cooldownAsHoursForNewBuyFromSameCoinBaseForMargin * adet
        if hours > cooldownAsHoursForNewBuyFromSameCoinBaseForMargin:
            result=True
        else:
            result=False
    else :
        result=True
    return result

def getIsCooldownBuyPassedForCoinForRobot15mWITHRealMargin(myCoin):
    global resultMail
    result=False
    adet = Trade.objects.filter(buyedByRobot=True,coin=myCoin,isMargin=False,strategy='RSI_15m_WITHRealMargin').exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS')).count()
    if adet>0:
        latestTrade=Trade.objects.filter(buyedByRobot=True,coin=myCoin,isMargin=False,strategy='RSI_15m_WITHRealMargin').exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS')).latest('transactionDate')
        hours=hourDiffNormal(latestTrade.transactionDate,datetime.now())
        myPreferences=Preferences.objects.all().first()
        cooldownAsHoursForNewBuyFromSameCoinBaseForMargin= myPreferences.cooldownAsHoursForNewBuyFromSameCoinBaseForMargin * adet
        if hours > cooldownAsHoursForNewBuyFromSameCoinBaseForMargin:
            result=True
        else:
            result=False
    else :
        result=True
    return result

def getIsCooldownBuyPassedForCoinForRobot15mSlow(myCoin):
    global resultMail
    result=False
    adet = Trade.objects.filter(buyedByRobot=True,coin=myCoin,isMargin=False,strategy='RSI_15m_Slow').exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS')).count()
    if adet>0:
        latestTrade=Trade.objects.filter(buyedByRobot=True,coin=myCoin,isMargin=False,strategy='RSI_15m_Slow').exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS')).latest('transactionDate')
        hours=hourDiffNormal(latestTrade.transactionDate,datetime.now())
        myPreferences=Preferences.objects.all().first()
        cooldownAsHoursForNewBuyFromSameCoinBaseForRsi15Slow= myPreferences.cooldownAsHoursForNewBuyFromSameCoinBaseForRsi15Slow * adet
        if hours > cooldownAsHoursForNewBuyFromSameCoinBaseForRsi15Slow:
            result=True
        else:
            result=False
    else :
        result=True
    return result

def getIsCooldownBuyPassedForCoinForRobot1h(myCoin):
    global resultMail
    result=False
    adet = Trade.objects.filter(buyedByRobot=True,coin=myCoin,isMargin=False,strategy='RSI_1h').exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS')).count()
    if adet>0:
        latestTrade=Trade.objects.filter(buyedByRobot=True,coin=myCoin,isMargin=False,strategy='RSI_1h').exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS')).latest('transactionDate')
        hours=hourDiffNormal(latestTrade.transactionDate,datetime.now())
        myPreferences=Preferences.objects.all().first()
        cooldownAsHoursForNewBuyFromSameCoinBaseFor1h= myPreferences.cooldownAsHoursForNewBuyFromSameCoinBaseFor1h * adet
        if hours > cooldownAsHoursForNewBuyFromSameCoinBaseFor1h:
            result=True
        else:
            result=False
    else :
        result=True
    return result
    
def getIsCooldownBuyPassedForCoinForMargin(myCoin):
    global resultMail
    result=False
    adet = Trade.objects.filter(buyedByRobot=True,coin=myCoin,isMargin=True).exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS')).count()
    if adet>0:
        latestTrade=Trade.objects.filter(buyedByRobot=True,coin=myCoin,isMargin=True).exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS')).latest('transactionDate')
        hours=hourDiffNormal(latestTrade.transactionDate,datetime.now())
        myPreferences=Preferences.objects.all().first()
        cooldownAsHoursForNewBuyFromSameCoinBaseForMargin= myPreferences.cooldownAsHoursForNewBuyFromSameCoinBaseForMargin * adet
        if hours > cooldownAsHoursForNewBuyFromSameCoinBaseForMargin:
            result=True
        else:
            result=False
    else :
        result=True
    return result

def getIsCooldownBuyPassedForCoinForMarginBTC(myCoin):
    global resultMail
    result=False
    adet = Trade.objects.filter(isMargin=True,coin__in=Coin.objects.filter(name__startswith='BTC')).count()
    if adet>0:
        latestTrade=Trade.objects.filter(isMargin=True,coin__in=Coin.objects.filter(name__startswith='BTC')).latest('transactionDate')
        hours=hourDiffNormal(latestTrade.transactionDate,datetime.now())
        myPreferences=Preferences.objects.all().first()
        if hours > myPreferences.cooldownAsHoursForNewBuyFromSameCoinBaseForMarginBTC:
            result=True
        else:
            result=False
    else :
        result=True
    return result

def getIsCooldownSellPassedForTrade(myTrade):
    global resultMail
    result=False
    if myTrade is None or myTrade.lastSellDate is None:
        result=True 
    else:#td=datetime.now() - myTrade.lastSellDate #myTrade.lastSellDate.replace(tzinfo=None)
        days=dateDiff(myTrade.lastSellDate,datetime.now())
        myPreferences=Preferences.objects.all().first()
        cooldownForNewSellFromSameCoin=myPreferences.cooldownForNewSellFromSameCoin
        if days > cooldownForNewSellFromSameCoin:
            result=True
        else:
            result=False
        resultMail= resultMail,'<br/><span style="color:red">Coin ve Satılmasından geçen gün sayısı :</span>',myTrade.coin.name ,'-',days,', IsCooldownSellPassedForTrade:',result,'<br/>'
    return result

def dateDiff(startDate,endDate):
    return abs((endDate.replace(tzinfo=None) - startDate.replace(tzinfo=None)).days)

def hourDiff(startDate,endDate):
    activeDateDiff = dateDiff(startDate,endDate)
    activeHourDiff = abs((endDate.replace(tzinfo=None) - startDate.replace(tzinfo=None)).seconds)/(60*60)
    result = activeHourDiff + (activeDateDiff*24) -3 #3 saat fark olduğundan dolayı sonunda çıkarttım
    return result

def minutesDiff(startDate,endDate):
    activeHourDiff = hourDiff(startDate,endDate)
    return activeHourDiff*60

def hourDiffNormal(startDate,endDate):
    activeDateDiff = dateDiff(startDate,endDate)
    activeHourDiff = abs((endDate.replace(tzinfo=None) - startDate.replace(tzinfo=None)).seconds)/(60*60)
    result = activeHourDiff + (activeDateDiff*24)
    return result
    
def allCoinsList():
    allCoins=[]
    exchange_info=client.get_exchange_info()
    for s in exchange_info['symbols']:
        if 'USDT' in s['symbol']:
            allCoins.append(s['symbol'])
    return allCoins

#def sendMail(subject,bodyField):
#    return ''

def sendMail(subject,bodyField):
    sender_email="cagdas.python@gmail.com"
    receiver_email="cagdas.karabulut@gmail.com"
    password='uoggxbmtuxkycudb'
    message=MIMEMultipart("alternative")
    message["Subject"]=subject
    message["From"]=sender_email
    message["To"]=receiver_email
    html="""\
    <html>
    <body>
        <p>"""+str(bodyField)+"""\
        </p>
    </body>
    </html>
    """
    try:
        part2=MIMEText(html, "html")
        message.attach(part2)
        context=ssl.create_default_context()
        
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(
                sender_email, receiver_email, message.as_string()
            )
    except Exception as e:
        print(sendMail,e)
        timet.sleep(60)
        sendMail(subject,bodyField)
    return ''

def panicModeActivateButton():
    myPreferences=Preferences.objects.all().first()
    if myPreferences.coinTargetToCollect=='BTC':
        sellEverythingAndBuyBtc()
    else:
        sellEverythingAndBuyUsdt()
    myPreferences=Preferences.objects.all().first()
    myPreferences.isBuyingModeActive=False
    myPreferences.isSellingModeActive=False
    myPreferences.isPanicModeActive=True
    myPreferences.save()
    return ''

def panicModeDisableButton():
    myPreferences=Preferences.objects.all().first()
    myPreferences.isBuyingModeActive=True
    myPreferences.isSellingModeActive=True
    myPreferences.isPanicModeActive=False
    myPreferences.temp_emaLowWarningStartDate=None
    myPreferences.save()
    return ''

def isControlForPanicModeAutomaticallyWorked(isEmaHigherThanBTCPrice):
    #ema altına düştüğünden beri x gün geçtiyse panik moduna geç veya 1 günde %10 dan fazla düştüyse panik moduna geç
    isWorked=False
    myPrefe=Preferences.objects.all().first()
    if isEmaHigherThanBTCPrice == 1:
        myPrefe.temp_emaLowWarningStartDate = None
        myPrefe.save()
    if myPrefe.isControlForPanicMode  is True:
        if isEmaHigherThanBTCPrice == 0:
            changeAsPercentage=getActivePrice('BTC','USDT') * 100 / getYesterdayPrice('BTC','USDT')-100
            if myPrefe.temp_emaLowWarningStartDate is None:
                myPrefe.temp_emaLowWarningStartDate = datetime.now()
                myPrefe.save()
            if (changeAsPercentage < float(-10)) and myPrefe.isPanicModeActive is False:
                panicModeActivateButton()
                isWorked=True
            if dateDiff(myPrefe.temp_emaLowWarningStartDate,datetime.now()) > myPrefe.cooldownForNewSellFromSameCoin :
                panicModeActivateButton()
                isWorked=True
    return isWorked

def isControlForEmaLowWarningStartDate(isEmaHigherThanBTCPrice):
    myPrefe=Preferences.objects.all().first()
    if isEmaHigherThanBTCPrice == 1:
        myPrefe.temp_emaLowWarningStartDate = None
        myPrefe.save()
    elif isEmaHigherThanBTCPrice==0 and myPrefe.temp_emaLowWarningStartDate is None:
        myPrefe.temp_emaLowWarningStartDate = datetime.now()
        myPrefe.save()

def isLast3SellsNegativeForMargin():
    isAllNegativeAndStopBuying = True
    tradeLogList = TradeLog.objects.filter(processType='SELL',strategy='Margin_RSI_15m').order_by('-transactionDate')[:3]
    for tradeLog in tradeLogList:
        if tradeLog.profitLossPercentage>0:
            isAllNegativeAndStopBuying = False
    return isAllNegativeAndStopBuying

def isLastSellsNegativeForMarginBTC():
    isAllNegativeAndStopBuying = True
    tradeLogList = TradeLog.objects.filter(processType='SELL',strategy='MarginBTC_RSI_15m',coinName__startswith='BTC').order_by('-transactionDate')[:1]
    for tradeLog in tradeLogList:
        if tradeLog.profitLossPercentage>0:
            isAllNegativeAndStopBuying = False
    return isAllNegativeAndStopBuying

def isLast3SellsNegativeFor4h():
    isAllNegativeAndStopBuying = True
    tradeLogList = TradeLog.objects.filter(processType='SELL',strategy='RSI_4h').order_by('-transactionDate')[:3]
    for tradeLog in tradeLogList:
        if tradeLog.profitLossPercentage>0:
            isAllNegativeAndStopBuying = False
    return isAllNegativeAndStopBuying
    
def isLast3SellsNegativeFor15m():
    isAllNegativeAndStopBuying = True
    tradeLogList = TradeLog.objects.filter(processType='SELL',strategy='RSI_15m').order_by('-transactionDate')[:3]
    for tradeLog in tradeLogList:
        if tradeLog.profitLossPercentage>0:
            isAllNegativeAndStopBuying = False
    return isAllNegativeAndStopBuying

def isLast3SellsNegativeFor15mWITHRealMargin():
    isAllNegativeAndStopBuying = True
    tradeLogList = TradeLog.objects.filter(processType='SELL',strategy='RSI_15m_WITHRealMargin').order_by('-transactionDate')[:3]
    for tradeLog in tradeLogList:
        if tradeLog.profitLossPercentage>0:
            isAllNegativeAndStopBuying = False
    return isAllNegativeAndStopBuying

def isLast3SellsNegativeFor1h():
    isAllNegativeAndStopBuying = True
    tradeLogList = TradeLog.objects.filter(processType='SELL',strategy='RSI_1h').order_by('-transactionDate')[:3]
    for tradeLog in tradeLogList:
        if tradeLog.profitLossPercentage>0:
            isAllNegativeAndStopBuying = False
    return isAllNegativeAndStopBuying

def sellOneStepFromAllCoinsButton():
    tradeList=getTradeList()
    for activeTrade in tradeList:
        finalQuantity=minimizeNumber(findQuantityByTradeToSell(activeTrade))
        sellWithMarketPriceByQuantityAction(activeTrade.coin.name,activeTrade.exchangePair.name,finalQuantity,activeTrade) 
    return ''

def sellEverythingAndBuyUsdt():
    tradeList=getTradeList()
    for activeTrade in tradeList:
        finalQuantity=minimizeNumber(activeTrade.count)
        sellWithMarketPriceByQuantityAction(activeTrade.coin.name,activeTrade.exchangePair.name,finalQuantity,activeTrade)
    return ''

def sellEverythingRobot15mAndBuyUsdt():
    tradeList=getTradeListForRobot15m()
    for activeTrade in tradeList:
        finalQuantity=minimizeNumber(activeTrade.count)
        sellWithMarketPriceByQuantityAction(activeTrade.coin.name,activeTrade.exchangePair.name,finalQuantity,activeTrade)
    return ''

def sellEverythingRobot15mWITHRealMarginAndBuyUsdt():
    tradeList=getTradeListForRobot15mWITHRealMargin()
    for activeTrade in tradeList:
        finalQuantity=minimizeNumber(activeTrade.count)
        sellWithMarketPriceByQuantityAction(activeTrade.coin.name,activeTrade.exchangePair.name,finalQuantity,activeTrade)
    return ''

def sellEverythingRobot15mSlowAndBuyUsdt():
    tradeList=getTradeListForRobot15mSlow()
    for activeTrade in tradeList:
        finalQuantity=minimizeNumber(activeTrade.count)
        sellWithMarketPriceByQuantityAction(activeTrade.coin.name,activeTrade.exchangePair.name,finalQuantity,activeTrade)
    return ''

def sellEverythingRobot1hAndBuyUsdt():
    tradeList=getTradeListForRobot1h()
    for activeTrade in tradeList:
        finalQuantity=minimizeNumber(activeTrade.count)
        sellWithMarketPriceByQuantityAction(activeTrade.coin.name,activeTrade.exchangePair.name,finalQuantity,activeTrade)
    return ''

def sellEverythingAndBuyBtc():
    sellEverythingAndBuyUsdt()
    totalUsdt=client.get_asset_balance(asset='USDT')['free']
    buyWithMarketPriceByTotalPriceAction('BTC','USDT',totalUsdt,False,'RSI_4h')
    return ''

def sellOneStepFromAllPositiveCoinsButton():
    global resultMail
    tradeList=getTradeList()
    for myTrade in tradeList:
        if myTrade.isPassiveInEarn is False and myTrade.isDifferentExchange is False and getIsCooldownSellPassedForTrade(myTrade) and (myTrade.price > getActivePrice(myTrade.coin.name,myTrade.exchangePair.name)):
            finalQuantity=minimizeNumber(findQuantityByTradeToSell(myTrade))
            sellWithMarketPriceByQuantityAction(myTrade.coin.name,myTrade.exchangePair.name,finalQuantity,myTrade)
            resultMail=resultMail,' <br>  birer kademe satis sebebiyle',myTrade.coin.name, ' den bir kademe satiliyor'
    return ''

def minimizeNumber(myNumber):
    finalNumber=myNumber
    return finalNumber
    '''myNumber=float(myNumber)
    finalNumber=0
    finalNumber=float('{:0.0{}f}'.format(myNumber, 3))
    if finalNumber < 0 :
        finalNumber=float('{:0.0{}f}'.format(myNumber, 4))
        if finalNumber < 0 :
            finalNumber=float('{:0.0{}f}'.format(myNumber, 5))'''
    
def buyWithMarketPriceByQuantityForLongAction(firstCoinNameForBuyParameter,secondCoinNameForBuyParameter,quantity,buyedByRobot):
    global resultMail
    global boughtCoins
    try:
        firstCoinForBuyParameter=Coin.objects.get(name=firstCoinNameForBuyParameter)
        secondCoinForBuyParameter=Coin.objects.get(name=secondCoinNameForBuyParameter)
        quantity=float(quantity)
        #quantity=quantity * 0.995
        process=commonBuySellByMarketPriceAction(firstCoinNameForBuyParameter,secondCoinNameForBuyParameter,quantity,'BUY',None,buyedByRobot,'Margin_RSI_15m')
        if process is not None and float(process['executedQty']): 
            processQuantity=float(process['executedQty'])
            processPrice=(float(process['cummulativeQuoteQty'])/float(process['executedQty']))
            newTrade=Trade(coin=firstCoinForBuyParameter,exchangePair=secondCoinForBuyParameter,count=processQuantity,price=processPrice,buyedByRobot=buyedByRobot,howManyTimesSold=0,firstCount=processQuantity,firstPriceAgainstBtc=(processPrice/getActivePrice('BTC','USDT')),isMargin=getIsMarginCoin(firstCoinNameForBuyParameter),strategy='Margin_RSI_15m')
            newTrade.save() 
            if buyedByRobot is False : 
                removeMaxLimitForRobotAsUsdtFromPrefAfterManuelBuy(newTrade.getTotalPrice())
            resultMail=resultMail,' <br> Alis Coin:',firstCoinNameForBuyParameter, ' adet:',processQuantity,' fiyat:', processPrice
            boughtCoins=boughtCoins,' <br>  ',firstCoinNameForBuyParameter
    except BinanceAPIException as e:
        print('buyWithMarketPriceByQuantityForLongAction',e)
    except BinanceOrderException as e:
        print('buyWithMarketPriceByQuantityForLongAction',e)

def buyWithMarketPriceByQuantityAction(firstCoinNameForBuyParameter,secondCoinNameForBuyParameter,quantity,buyedByRobot,buyingStrategy):
    global resultMail
    global boughtCoins
    try:
        firstCoinForBuyParameter=Coin.objects.get(name=firstCoinNameForBuyParameter)
        secondCoinForBuyParameter=Coin.objects.get(name=secondCoinNameForBuyParameter)
        quantity=float(quantity)
        #quantity=quantity * 0.995
        process=commonBuySellByMarketPriceAction(firstCoinNameForBuyParameter,secondCoinNameForBuyParameter,quantity,'BUY',None,buyedByRobot,buyingStrategy)
        if process is not None and float(process['executedQty']): 
            processQuantity=float(process['executedQty'])
            processPrice=(float(process['cummulativeQuoteQty'])/float(process['executedQty']))
            newTrade=Trade(coin=firstCoinForBuyParameter,exchangePair=secondCoinForBuyParameter,count=processQuantity,price=processPrice,buyedByRobot=buyedByRobot,howManyTimesSold=0,firstCount=processQuantity,firstPriceAgainstBtc=(processPrice/getActivePrice('BTC','USDT')),isMargin=getIsMarginCoin(firstCoinNameForBuyParameter),strategy=buyingStrategy)
            newTrade.save() 
            if buyedByRobot is False : 
                removeMaxLimitForRobotAsUsdtFromPrefAfterManuelBuy(newTrade.getTotalPrice())
            resultMail=resultMail,' <br> Alis Coin:',firstCoinNameForBuyParameter, ' adet:',processQuantity,' fiyat:', processPrice
            boughtCoins=boughtCoins,' <br>  ',firstCoinNameForBuyParameter
    except BinanceAPIException as e:
        print('buyWithMarketPriceByQuantityAction',e)
    except BinanceOrderException as e:
        print('buyWithMarketPriceByQuantityAction',e)

def sellWithMarketPriceByQuantityAction(firstCoinNameForSellParameter,secondCoinNameForSellParameter,quantity,myTrade):
    global resultMail
    global soldCoins
    sellResult=False
    sellInfo=''
    priceNow=getActivePrice(firstCoinNameForSellParameter,secondCoinNameForSellParameter)
    finalQuantity=float(round(quantity, 5))
    #quantityRemaining=float(client.get_asset_balance(asset=firstCoinNameForSellParameter)['free'])
    quantityRemaining=getRemainingAsset(firstCoinNameForSellParameter,secondCoinNameForSellParameter,myTrade)
    if quantityRemaining<finalQuantity:
        finalQuantity=quantityRemaining
    try:
        #finalQuantity=finalQuantity * 0.995
        if ((priceNow*finalQuantity)<11 and (priceNow*quantityRemaining)<22) or isSellingAll(myTrade):
            sellAllForCoinAction(firstCoinNameForSellParameter,secondCoinNameForSellParameter,myTrade) 
        else:
            if myTrade is not None :
                process=commonBuySellByMarketPriceAction(firstCoinNameForSellParameter,secondCoinNameForSellParameter,finalQuantity,'SELL',myTrade,myTrade.buyedByRobot,myTrade.strategy)
                if priceNow>myTrade.price:
                    sellInfo=' KARLI '
                else : 
                    sellInfo=' ZARARINA '
            else : 
                process=commonBuySellByMarketPriceAction(firstCoinNameForSellParameter,secondCoinNameForSellParameter,finalQuantity,'SELL',None,False,'')
            if process is not None and float(process['executedQty']):
                processQuantity=float(process['executedQty'])
                processPrice=(float(process['cummulativeQuoteQty'])/float(process['executedQty']))
                sellResult=True
                soldCoins=soldCoins,',',firstCoinNameForSellParameter,',',sellInfo
                if myTrade is not None:
                    quantityFinal=myTrade.count - processQuantity
                    resultMail=resultMail,' <br> Satis Coin:',firstCoinNameForSellParameter, ' adet:',processQuantity,' fiyat:', processPrice,' toplam:', processQuantity*processPrice
                    if quantityFinal > 0 and (getActivePrice(firstCoinNameForSellParameter,secondCoinNameForSellParameter)*quantityFinal>10):
                        myTrade.count=quantityFinal
                        myTrade.howManyTimesSold=myTrade.howManyTimesSold+1
                        myTrade.lastSellDate=datetime.now()
                        myTrade.save()
                    else:
                        myTrade.delete()
    except BinanceAPIException as e:
        print('sellWithMarketPriceByQuantityAction',e)
        sellResult=False
    except BinanceOrderException as e:
        print('sellWithMarketPriceByQuantityAction',e)
        sellResult=False
    return sellResult

def buyWithMarketPriceByTotalPriceAction(firstCoinNameForBuyParameter,secondCoinNameForBuyParameter,totalPriceToBuy,buyedByRobot,buyingStrategy):
    global resultMail
    global boughtCoins
    try:
        firstCoinForBuyParameter=Coin.objects.get(name=firstCoinNameForBuyParameter)
        secondCoinForBuyParameter=Coin.objects.get(name=secondCoinNameForBuyParameter)
        priceNow=getActivePrice(firstCoinNameForBuyParameter,secondCoinNameForBuyParameter)
        quantity=totalPriceToBuy/priceNow
        quantity=float(quantity)
        #quantity=quantity * 0.995
        if quantity > 0: 
            process=commonBuySellByMarketPriceAction(firstCoinNameForBuyParameter,secondCoinNameForBuyParameter,quantity,'BUY',None,buyedByRobot,buyingStrategy)
            if process is not None and float(process['executedQty']):
                processQuantity=float(process['executedQty'])
                processPrice=(float(process['cummulativeQuoteQty'])/float(process['executedQty']))
                newTrade=Trade(coin=firstCoinForBuyParameter,exchangePair=secondCoinForBuyParameter,count=processQuantity,price=processPrice,buyedByRobot=buyedByRobot,howManyTimesSold=0,firstCount=processQuantity,firstPriceAgainstBtc=(priceNow/getActivePrice('BTC','USDT')),isMargin=getIsMarginCoin(firstCoinNameForBuyParameter))
                newTrade.save() 
                if buyedByRobot is False : 
                    removeMaxLimitForRobotAsUsdtFromPrefAfterManuelBuy(newTrade.getTotalPrice())
                resultMail=resultMail,' <br> Alis Coin:',firstCoinNameForBuyParameter, ' adet:',processQuantity,' fiyat:', processPrice
                boughtCoins=boughtCoins,' <br>  ',firstCoinNameForBuyParameter
    except BinanceAPIException as e:
        print('buyWithMarketPriceByTotalPriceAction',e)
    except BinanceOrderException as e:
        print('buyWithMarketPriceByTotalPriceAction',e)

def sellWithMarketPriceByTotalPriceAction(firstCoinNameForSellParameter,secondCoinNameForSellParameter,totalPriceToSell,myTrade):
    global resultMail
    global soldCoins
    try:
        priceNow=getActivePrice(firstCoinNameForSellParameter,secondCoinNameForSellParameter)
        #quantityRemaining=float(client.get_asset_balance(asset=firstCoinNameForSellParameter)['free'])
        quantityRemaining=getRemainingAsset(firstCoinNameForSellParameter,secondCoinNameForSellParameter,myTrade)
        quantity=totalPriceToSell/priceNow
        quantity=float(quantity)
        #quantity=quantity * 0.995
        if ((priceNow*quantity)<11 and (priceNow*quantityRemaining)<22) or isSellingAll(myTrade):
            sellAllForCoinAction(firstCoinNameForSellParameter,secondCoinNameForSellParameter,myTrade)
        else:
            if myTrade is not None:
                process=commonBuySellByMarketPriceAction(firstCoinNameForSellParameter,secondCoinNameForSellParameter,quantity,'SELL',myTrade,myTrade.buyedByRobot,myTrade.strategy)
            else : 
                process=commonBuySellByMarketPriceAction(firstCoinNameForSellParameter,secondCoinNameForSellParameter,quantity,'SELL',None,False,'')
            if process is not None and float(process['executedQty']):
                processQuantity=float(process['executedQty'])
                processPrice=(float(process['cummulativeQuoteQty'])/float(process['executedQty']))
                soldCoins=soldCoins,',',firstCoinNameForSellParameter
                if myTrade is not None:
                    resultMail=resultMail,' <br> Satis Coin:',firstCoinNameForSellParameter, ' adet:',processQuantity,' fiyat:', processPrice,' toplam:', processQuantity*processPrice
                    quantityFinal=myTrade.count - processQuantity
                    if quantityFinal > 0 and (getActivePrice(firstCoinNameForSellParameter,secondCoinNameForSellParameter)*quantityFinal>10):
                        myTrade.count=quantityFinal
                        myTrade.howManyTimesSold=myTrade.howManyTimesSold+1
                        myTrade.lastSellDate=datetime.now()
                        myTrade.save()
                    else:
                        myTrade.delete()
                sellResult=True
    except BinanceAPIException as e:
        print('sellWithMarketPriceByTotalPriceAction',e)
    except BinanceOrderException as e:
        print('sellWithMarketPriceByTotalPriceAction',e)

##################################################################################################################################################################5
def export_tradesHistory_xls(request):
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename="users.xls"'
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Users')
    # Sheet header, first row
    row_num = 0
    font_style = xlwt.XFStyle()
    font_style.font.bold = True
    columns = ['processType', 'coinName', 'exchangeCoinName', 'count','price','gainUsdt','passedDaysToSell','profitLossPercentage']
    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num], font_style)
    # Sheet body, remaining rows
    font_style = xlwt.XFStyle()
    rows = TradeLog.objects.all().values_list('processType', 'coinName', 'exchangeCoinName', 'count','price','gainUsdt','passedDaysToSell','profitLossPercentage')
    for row in rows:
        row_num += 1
        for col_num in range(len(row)):
            ws.write(row_num, col_num, row[col_num], font_style)
    wb.save(response)
    return response

def getRemainingAsset(firstCoinName,secondCoinName,myTrade):
    quantity=0
    if myTrade is not None and (myTrade.strategy == 'RSI_15m_WITHRealMargin'):
        try :
            #mySymbol=firstCoinName+secondCoinName
            #quantity = float(client.get_max_margin_transfer(asset=firstCoinName)['amount'])
            quantity=myTrade.count
        except BinanceAPIException as e1:
            quantity = 0 #açık isolated hesap yoksa buraya düşer
    else :
        quantity=float(client.get_asset_balance(asset=firstCoinName)['free'])
    return quantity

def sellAllForCoinAction(firstCoinNameForSellParameter,secondCoinNameForSellParameter,myTrade):
    global resultMail
    global soldCoins
    try:
        firstCoinForBuyParameter=Coin.objects.get(name=firstCoinNameForSellParameter)
        secondCoinForBuyParameter=Coin.objects.get(name=secondCoinNameForSellParameter)
        quantity=getRemainingAsset(firstCoinNameForSellParameter,secondCoinNameForSellParameter,myTrade)
        if quantity>0:
            if myTrade is None : 
                myTrade = Trade.objects.filter(coin=firstCoinForBuyParameter).first()
            if myTrade is not None : 
                process=commonBuySellByMarketPriceAction(firstCoinNameForSellParameter,secondCoinNameForSellParameter,quantity,'SELL',myTrade,myTrade.buyedByRobot,myTrade.strategy)
            else :     
                process=commonBuySellByMarketPriceAction(firstCoinNameForSellParameter,secondCoinNameForSellParameter,quantity,'SELL',None,False,'')
            if process is not None and float(process['executedQty']):
                processQuantity=float(process['executedQty'])
                processPrice=(float(process['cummulativeQuoteQty'])/float(process['executedQty']))
                soldCoins=soldCoins,',',firstCoinNameForSellParameter
                trades=Trade.objects.filter(coin=firstCoinForBuyParameter,isPassiveInEarn=False,isDifferentExchange=False).exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS'))
                for trade in trades:
                    if trade is not None:
                        resultMail=resultMail,' <br> Satis Coin:',firstCoinNameForSellParameter, ' adet:',processQuantity,' fiyat:', processPrice,' toplam:', processQuantity*processPrice
                        trade.delete()
                sellResult=True
    except BinanceAPIException as e:
        print('sellAllForCoinAction',e)
    except BinanceOrderException as e:
        print('sellAllForCoinAction',e)

def marginBuySellByMarketPriceAction(firstCoinNameForBuyOrSellParameter,secondCoinNameForBuyOrSellParameter,usdtAmount,exhangeQuantity,buyOrSell):
    process = None
    mySymbol = firstCoinNameForBuyOrSellParameter+secondCoinNameForBuyOrSellParameter
    currentAmountBuy = 0
    mySideEffectType=''
    if buyOrSell=='BUY': #alış yapmak için gerekiyorsa önce transfer et
        mySideEffectType="MARGIN_BUY"
        transferFromSpotToMargin = client.transfer_spot_to_margin(asset=secondCoinNameForBuyOrSellParameter,amount=usdtAmount) #spottan cross a usdt transfer et #1
        maxBorrowAmount = client.get_max_margin_loan(asset=firstCoinNameForBuyOrSellParameter)["amount"] #kullanılabilecek max krediyi tespit et
        maxBorrowAmount = '{:0.0{}f}'.format(float(maxBorrowAmount), 6)
        marginLoanProcess = client.create_margin_loan(asset=firstCoinNameForBuyOrSellParameter, amount=maxBorrowAmount) #krediyi çek
        timet.sleep(1)
    elif buyOrSell=='SELL':
        mySideEffectType="AUTO_REPAY"
        try :
            repayAmount = client.get_margin_loan_details(asset=firstCoinNameForBuyOrSellParameter)['rows'][0]['principal'] # Kredi ödemesi TODO Eskisi geliyor
            repayResult = client.repay_margin_loan(asset=firstCoinNameForBuyOrSellParameter, amount=repayAmount) #KREDİYİ ÖDE
        except BinanceAPIException as e1:
            print('ödenecek kredi yok: ',firstCoinNameForBuyOrSellParameter )
        #remainingCoinAmount = client.get_max_margin_transfer(asset=firstCoinNameForBuyOrSellParameter)["amount"]
        #remainingCoinAmount = '{:0.0{}f}'.format(float(remainingCoinAmount), 6)
    try:#alış veya satış yap
        process = client.create_margin_order(symbol=mySymbol,side=buyOrSell,type='MARKET',quantity=exhangeQuantity,sideEffectType=mySideEffectType) #satın al
    except BinanceAPIException as e1:
        try:
            exhangeQuantity=str(exhangeQuantity)[0:-1]
            process = client.create_margin_order(symbol=mySymbol,side=buyOrSell,type='MARKET',quantity=exhangeQuantity,sideEffectType=mySideEffectType) #satın al
        except BinanceAPIException as e2:
            try:
                exhangeQuantity=str(exhangeQuantity)[0:-2]
                process = client.create_margin_order(symbol=mySymbol,side=buyOrSell,type='MARKET',quantity=exhangeQuantity,sideEffectType=mySideEffectType) #satın al
            except BinanceAPIException as e3:
                try:
                    exhangeQuantity=str(exhangeQuantity)[0:-3]
                    process = client.create_margin_order(symbol=mySymbol,side=buyOrSell,type='MARKET',quantity=exhangeQuantity,sideEffectType=mySideEffectType) #satın al
                except BinanceAPIException as e4:
                    try:
                        exhangeQuantity=str(exhangeQuantity)[0:-4]
                        process = client.create_margin_order(symbol=mySymbol,side=buyOrSell,type='MARKET',quantity=exhangeQuantity,sideEffectType=mySideEffectType) #satın al
                    except BinanceAPIException as e5:
                        try:
                            exhangeQuantity=str(exhangeQuantity)[0:-5]
                            process = client.create_margin_order(symbol=mySymbol,side=buyOrSell,type='MARKET',quantity=exhangeQuantity,sideEffectType=mySideEffectType) #satın al
                        except BinanceAPIException as e:
                            print('commonBuySellByMarketPriceAction',e)
    if buyOrSell=='SELL': 
        timet.sleep(2)
        currentAmountSell = 0
        try :
            transferFromMarginToSpotCount = float(client.get_max_margin_transfer(asset=secondCoinNameForBuyOrSellParameter)['amount']) #aktarılacak usdt miktarı tespit et
        except BinanceAPIException as e1:
            currentAmountSell = 0 #açık isolated hesap yoksa buraya düşer
        timet.sleep(1)
        transferFromMarginToSpotProcess = client.transfer_margin_to_spot(asset=secondCoinNameForBuyOrSellParameter, amount=transferFromMarginToSpotCount) #miktarı cross dan spot a transfer et
    return process

def commonBuySellByMarketPriceAction(firstCoinNameForBuyOrSellParameter,secondCoinNameForBuyOrSellParameter,quantity,buyOrSell,myTrade,buyedByRobot,buyingStrategy):
    global boughtCoinsTotalUsdt
    process=None 
    finalQuantity=quantity
    activePrice=getActivePrice(firstCoinNameForBuyOrSellParameter,secondCoinNameForBuyOrSellParameter)
    isMarginCoin=getIsMarginCoin(firstCoinNameForBuyOrSellParameter)
    isMarginBTCCoin=getIsMarginBTCCoin(firstCoinNameForBuyOrSellParameter)
    #quantityFromExchange=float(client.get_asset_balance(asset=firstCoinNameForBuyOrSellParameter)['free'])
    quantityFromExchange=getRemainingAsset(firstCoinNameForBuyOrSellParameter,secondCoinNameForBuyOrSellParameter,myTrade)#TODO
    if buyOrSell=='SELL':
        if myTrade is None: 
            activeCoin=Coin.objects.filter(name=firstCoinNameForBuyOrSellParameter).first()
            myTrade=Trade.objects.filter(coin=activeCoin).first()
        if myTrade is not None:
            if isSellingAll(myTrade):
                finalQuantity=quantityFromExchange
            else:
                finalQuantity=quantity
    if (activePrice * finalQuantity) < 11:
        finalQuantity=quantityFromExchange
    if quantityFromExchange<finalQuantity:
        finalQuantity=quantityFromExchange
    exhangeQuantity='{:0.0{}f}'.format(quantity, 6)
    exhangeQuantity=exhangeQuantity[0:-1]
    if buyingStrategy == 'RSI_15m_WITHRealMargin':#isolated margin işlemleri için
        usdtAmountAsFloat = (float(exhangeQuantity)*float(activePrice))+2
        usdtAmount=float(str(int(usdtAmountAsFloat)))
        process = marginBuySellByMarketPriceAction(firstCoinNameForBuyOrSellParameter,secondCoinNameForBuyOrSellParameter,usdtAmount,exhangeQuantity,buyOrSell)
    else :
        try:
            process=client.create_order(symbol=firstCoinNameForBuyOrSellParameter+secondCoinNameForBuyOrSellParameter, side=buyOrSell,type='MARKET',quantity=exhangeQuantity)
        except BinanceAPIException as e1:
            try:
                exhangeQuantity=exhangeQuantity[0:-1]
                process=client.create_order(symbol=firstCoinNameForBuyOrSellParameter+secondCoinNameForBuyOrSellParameter, side=buyOrSell,type='MARKET',quantity=exhangeQuantity)
            except BinanceAPIException as e2:
                try:
                    exhangeQuantity=exhangeQuantity[0:-2]
                    process=client.create_order(symbol=firstCoinNameForBuyOrSellParameter+secondCoinNameForBuyOrSellParameter, side=buyOrSell,type='MARKET',quantity=exhangeQuantity)
                except BinanceAPIException as e3:
                    try:
                        exhangeQuantity=exhangeQuantity[0:-3]
                        process=client.create_order(symbol=firstCoinNameForBuyOrSellParameter+secondCoinNameForBuyOrSellParameter, side=buyOrSell,type='MARKET',quantity=exhangeQuantity)
                    except BinanceAPIException as e:
                        print('commonBuySellByMarketPriceAction',e)
    if process is not None:
        processQuantity=float(process['executedQty'])
        processPrice=(float(process['cummulativeQuoteQty'])/float(process['executedQty']))
        gainPercentage=gainUsdt=passedDaysToSell=passedHoursToSell=0
        isSellResultPositive=False
        coinForIndicator=Coin.objects.filter(name=firstCoinNameForBuyOrSellParameter).first()
        if buyOrSell=='SELL':
            if myTrade is not None:
                gainUsdt=(processPrice * processQuantity)-(myTrade.price * processQuantity)
                gainPercentage=getGainPercentage(myTrade.price,processPrice)
                passedDaysToSell=dateDiff(myTrade.transactionDate,datetime.now())
                passedHoursToSell=hourDiff(myTrade.transactionDate,datetime.now())
                if passedDaysToSell==0:
                    passedDaysToSell=1
                if gainPercentage>0:
                    isSellResultPositive=True
                else: 
                    isSellResultPositive=False
                if isMarginCoin:
                    if isMarginBTCCoin:
                        myPreferences=Preferences.objects.all().first()
                        myPreferences.marginBTCResultHistoryAsUsdt=myPreferences.marginBTCResultHistoryAsUsdt+((processPrice * processQuantity)-(myTrade.price * processQuantity))
                        myPreferences.save()
                    else:
                        myPreferences=Preferences.objects.all().first()
                        myPreferences.marginResultHistoryAsUsdt=myPreferences.marginResultHistoryAsUsdt+((processPrice * processQuantity)-(myTrade.price * processQuantity))
                        myPreferences.save()
                else: 
                    if buyingStrategy == 'RSI_4h':
                        myPreferences=Preferences.objects.all().first()
                        myPreferences.robotResultHistoryAsUsdt=myPreferences.robotResultHistoryAsUsdt+((processPrice * processQuantity)-(myTrade.price * processQuantity))
                        myPreferences.save()
                    elif buyingStrategy == 'RSI_15m':
                        myPreferences=Preferences.objects.all().first()
                        myPreferences.robot15mResultHistoryAsUsdt=myPreferences.robot15mResultHistoryAsUsdt+((processPrice * processQuantity)-(myTrade.price * processQuantity))
                        myPreferences.save()
                    elif buyingStrategy == 'RSI_15m_WITHRealMargin':
                        myPreferences=Preferences.objects.all().first()
                        myPreferences.robot15mWITHRealMarginResultHistoryAsUsdt=myPreferences.robot15mWITHRealMarginResultHistoryAsUsdt+((processPrice * processQuantity)-(myTrade.price * processQuantity))
                        myPreferences.save()
                    elif buyingStrategy == 'RSI_15m_Slow':
                        myPreferences=Preferences.objects.all().first()
                        myPreferences.robot15mSlowResultHistoryAsUsdt=myPreferences.robot15mSlowResultHistoryAsUsdt+((processPrice * processQuantity)-(myTrade.price * processQuantity))
                        myPreferences.save()
                    elif buyingStrategy == 'RSI_1h':
                        myPreferences=Preferences.objects.all().first()
                        myPreferences.robot1hResultHistoryAsUsdt=myPreferences.robot1hResultHistoryAsUsdt+((processPrice * processQuantity)-(myTrade.price * processQuantity))
                        myPreferences.save()
        else: 
            boughtCoinsTotalUsdt=boughtCoinsTotalUsdt+float(processQuantity*processPrice)
        indicatorResults=""
        if isMarginCoin:
            if isMarginBTCCoin:
                compareCoin=coinForIndicator.name.replace('UP', '')+secondCoinNameForBuyOrSellParameter
                indicatorResults=getIndicatorResults(compareCoin,isMarginCoin)
                if buyOrSell=='BUY':
                    myPreferences=Preferences.objects.all().first()
                    myPreferences.marginBTCRobotTotalBuyCount=myPreferences.marginBTCRobotTotalBuyCount+1
                    myPreferences.save()
                else:
                    if isSellResultPositive:
                        myPreferences=Preferences.objects.all().first()
                        myPreferences.marginBTCRobotPositiveSellCount=myPreferences.marginBTCRobotPositiveSellCount+1
                        myPreferences.save()
                    else:
                        myPreferences=Preferences.objects.all().first()
                        myPreferences.marginBTCRobotNegativeSellCount=myPreferences.marginBTCRobotNegativeSellCount+1
                        if isLastSellsNegativeForMarginBTC():
                            myPreferences.stopBuyingDateForMarginBTC=datetime.now()
                        myPreferences.save()
            else:
                if coinForIndicator.name.endswith('DOWN'):
                    compareCoin=coinForIndicator.name.replace('DOWN', '')+secondCoinNameForBuyOrSellParameter
                    indicatorResults=getIndicatorResults(compareCoin,isMarginCoin)
                elif coinForIndicator.name.endswith('UP'):
                    compareCoin=coinForIndicator.name.replace('UP', '')+secondCoinNameForBuyOrSellParameter
                    indicatorResults=getIndicatorResults(compareCoin,isMarginCoin)
                if buyOrSell=='BUY':
                    myPreferences=Preferences.objects.all().first()
                    myPreferences.marginRobotTotalBuyCount=myPreferences.marginRobotTotalBuyCount+1
                    myPreferences.save()
                else:
                    if isSellResultPositive:
                        if isSellingAll(myTrade): 
                            myPreferences=Preferences.objects.all().first()
                            myPreferences.marginRobotPositiveSellCount=myPreferences.marginRobotPositiveSellCount+1
                            myPreferences.save()
                        else:
                            myPreferences=Preferences.objects.all().first()
                            myPreferences.marginRobotPositiveSellCount=myPreferences.marginRobotPositiveSellCount+1
                            myPreferences.marginRobotTotalBuyCount=myPreferences.marginRobotTotalBuyCount+1
                            myPreferences.save()
                    else:
                        if isSellingAll(myTrade):
                            myPreferences=Preferences.objects.all().first()
                            myPreferences.marginRobotNegativeSellCount=myPreferences.marginRobotNegativeSellCount+1
                            if isLast3SellsNegativeForMargin():
                                myPreferences.stopBuyingDateForMargin=datetime.now()
                            myPreferences.save()
                        else: 
                            myPreferences=Preferences.objects.all().first()
                            myPreferences.marginRobotNegativeSellCount=myPreferences.marginRobotNegativeSellCount+1
                            myPreferences.marginRobotTotalBuyCount=myPreferences.marginRobotTotalBuyCount+1
                            if isLast3SellsNegativeForMargin():
                                myPreferences.stopBuyingDateForMargin=datetime.now()
                            myPreferences.save()
        elif buyingStrategy == 'RSI_4h':
            indicatorResults=getIndicatorResults(coinForIndicator.name+coinForIndicator.preferredCompareCoinName,isMarginCoin)
            if buyOrSell=='BUY':
                myPreferences=Preferences.objects.all().first()
                myPreferences.robotTotalBuyCount=myPreferences.robotTotalBuyCount+1
                myPreferences.save()
            else:
                if isSellResultPositive:
                    if isSellingAll(myTrade):
                        myPreferences=Preferences.objects.all().first()
                        myPreferences.robotPositiveSellCount=myPreferences.robotPositiveSellCount+1
                        myPreferences.save()
                    else: 
                        myPreferences=Preferences.objects.all().first()
                        myPreferences.robotPositiveSellCount=myPreferences.robotPositiveSellCount+1
                        myPreferences.robotTotalBuyCount=myPreferences.robotTotalBuyCount+1
                        myPreferences.save()
                else:
                    if isSellingAll(myTrade): 
                        myPreferences=Preferences.objects.all().first()
                        myPreferences.robotNegativeSellCount=myPreferences.robotNegativeSellCount+1
                        if isLast3SellsNegativeFor4h():
                            myPreferences.stopBuyingDateFor4h=datetime.now()
                        myPreferences.save()
                    else: 
                        myPreferences=Preferences.objects.all().first()
                        myPreferences.robotNegativeSellCount=myPreferences.robotNegativeSellCount+1
                        myPreferences.robotTotalBuyCount=myPreferences.robotTotalBuyCount+1
                        if isLast3SellsNegativeFor4h():
                            myPreferences.stopBuyingDateFor4h=datetime.now()
                        myPreferences.save()
        elif buyingStrategy == 'RSI_15m':
            indicatorResults=getIndicatorResults(coinForIndicator.name+coinForIndicator.preferredCompareCoinName,True)
            if buyOrSell=='BUY':
                myPreferences=Preferences.objects.all().first()
                myPreferences.robot15mTotalBuyCount=myPreferences.robot15mTotalBuyCount+1
                myPreferences.save()
            else:
                if isSellResultPositive:
                    if isSellingAll(myTrade): 
                        myPreferences=Preferences.objects.all().first()
                        myPreferences.robot15mPositiveSellCount=myPreferences.robot15mPositiveSellCount+1
                        myPreferences.save()
                    else: 
                        myPreferences=Preferences.objects.all().first()
                        myPreferences.robot15mPositiveSellCount=myPreferences.robot15mPositiveSellCount+1
                        myPreferences.robot15mTotalBuyCount=myPreferences.robot15mTotalBuyCount+1
                        myPreferences.save()
                else:
                    if isSellingAll(myTrade): 
                        myPreferences=Preferences.objects.all().first()
                        myPreferences.robot15mNegativeSellCount=myPreferences.robot15mNegativeSellCount+1
                        if isLast3SellsNegativeFor15m():
                            myPreferences.stopBuyingDateFor15m=datetime.now()
                        myPreferences.save()
                    else: 
                        myPreferences=Preferences.objects.all().first()
                        myPreferences.robot15mNegativeSellCount=myPreferences.robot15mNegativeSellCount+1
                        myPreferences.robot15mTotalBuyCount=myPreferences.robot15mTotalBuyCount+1
                        if isLast3SellsNegativeFor15m():
                            myPreferences.stopBuyingDateFor15m=datetime.now()
                        myPreferences.save()
        elif buyingStrategy == 'RSI_15m_WITHRealMargin':
            indicatorResults=getIndicatorResults(coinForIndicator.name+coinForIndicator.preferredCompareCoinName,True)
            if buyOrSell=='BUY':
                myPreferences=Preferences.objects.all().first()
                myPreferences.robot15mWITHRealMarginTotalBuyCount=myPreferences.robot15mWITHRealMarginTotalBuyCount+1
                myPreferences.save()
            else:
                if isSellResultPositive:
                    if isSellingAll(myTrade): 
                        myPreferences=Preferences.objects.all().first()
                        myPreferences.robot15mWITHRealMarginPositiveSellCount=myPreferences.robot15mWITHRealMarginPositiveSellCount+1
                        myPreferences.save()
                    else: 
                        myPreferences=Preferences.objects.all().first()
                        myPreferences.robot15mWITHRealMarginPositiveSellCount=myPreferences.robot15mWITHRealMarginPositiveSellCount+1
                        myPreferences.robot15mWITHRealMarginTotalBuyCount=myPreferences.robot15mWITHRealMarginTotalBuyCount+1
                        myPreferences.save()
                else:
                    if isSellingAll(myTrade): 
                        myPreferences=Preferences.objects.all().first()
                        myPreferences.robot15mWITHRealMarginNegativeSellCount=myPreferences.robot15mWITHRealMarginNegativeSellCount+1
                        if isLast3SellsNegativeFor15mWITHRealMargin():
                            myPreferences.stopBuyingDateFor15mWITHRealMargin=datetime.now()
                        myPreferences.save()
                    else: 
                        myPreferences=Preferences.objects.all().first()
                        myPreferences.robot15mWITHRealMarginNegativeSellCount=myPreferences.robot15mWITHRealMarginNegativeSellCount+1
                        myPreferences.robot15mWITHRealMarginTotalBuyCount=myPreferences.robot15mWITHRealMarginTotalBuyCount+1
                        if isLast3SellsNegativeFor15mWITHRealMargin():
                            myPreferences.stopBuyingDateFor15mWITHRealMargin=datetime.now()
                        myPreferences.save()
        elif buyingStrategy == 'RSI_15m_Slow':
            indicatorResults=getIndicatorResults(coinForIndicator.name+coinForIndicator.preferredCompareCoinName,True)
            if buyOrSell=='BUY':
                myPreferences=Preferences.objects.all().first()
                myPreferences.robot15mSlowTotalBuyCount=myPreferences.robot15mSlowTotalBuyCount+1
                myPreferences.save()
            else:
                if isSellResultPositive:
                    if isSellingAll(myTrade): 
                        myPreferences=Preferences.objects.all().first()
                        myPreferences.robot15mSlowPositiveSellCount=myPreferences.robot15mSlowPositiveSellCount+1
                        myPreferences.save()
                    else: 
                        myPreferences=Preferences.objects.all().first()
                        myPreferences.robot15mSlowPositiveSellCount=myPreferences.robot15mSlowPositiveSellCount+1
                        myPreferences.robot15mSlowTotalBuyCount=myPreferences.robot15mSlowTotalBuyCount+1
                        myPreferences.save()
                else:
                    if isSellingAll(myTrade): 
                        myPreferences=Preferences.objects.all().first()
                        myPreferences.robot15mSlowNegativeSellCount=myPreferences.robot15mSlowNegativeSellCount+1
                        if isLast3SellsNegativeFor15m():
                            myPreferences.stopBuyingDateFor15mSlow=datetime.now()
                        myPreferences.save()
                    else: 
                        myPreferences=Preferences.objects.all().first()
                        myPreferences.robot15mSlowNegativeSellCount=myPreferences.robot15mSlowNegativeSellCount+1
                        myPreferences.robot15mSlowTotalBuyCount=myPreferences.robot15mSlowTotalBuyCount+1
                        if isLast3SellsNegativeFor15m():
                            myPreferences.stopBuyingDateFor15mSlow=datetime.now()
                        myPreferences.save()
        elif buyingStrategy == 'RSI_1h':
            indicatorResults=getIndicatorResults(coinForIndicator.name+coinForIndicator.preferredCompareCoinName,True)
            if buyOrSell=='BUY':
                myPreferences=Preferences.objects.all().first()
                myPreferences.robot1hTotalBuyCount=myPreferences.robot1hTotalBuyCount+1
                myPreferences.save()
            else:
                if isSellResultPositive:
                    if isSellingAll(myTrade): 
                        myPreferences=Preferences.objects.all().first()
                        myPreferences.robot1hPositiveSellCount=myPreferences.robot1hPositiveSellCount+1
                        myPreferences.save()
                    else: 
                        myPreferences=Preferences.objects.all().first()
                        myPreferences.robot1hPositiveSellCount=myPreferences.robot1hPositiveSellCount+1
                        myPreferences.robot1hTotalBuyCount=myPreferences.robot1hTotalBuyCount+1
                        myPreferences.save()
                else:
                    if isSellingAll(myTrade): 
                        myPreferences=Preferences.objects.all().first()
                        myPreferences.robot1hNegativeSellCount=myPreferences.robot1hNegativeSellCount+1
                        if isLast3SellsNegativeFor1h():
                            myPreferences.stopBuyingDateFor1h=datetime.now()
                        myPreferences.save()
                    else: 
                        myPreferences=Preferences.objects.all().first()
                        myPreferences.robot1hNegativeSellCount=myPreferences.robot1hNegativeSellCount+1
                        myPreferences.robot1hTotalBuyCount=myPreferences.robot1hTotalBuyCount+1
                        if isLast3SellsNegativeFor1h():
                            myPreferences.stopBuyingDateFor1h=datetime.now()
                        myPreferences.save()
        tradeLog=TradeLog(processType=buyOrSell,coinName=firstCoinNameForBuyOrSellParameter,exchangeCoinName=secondCoinNameForBuyOrSellParameter,count=processQuantity,price=processPrice,passedDaysToSell=passedDaysToSell,profitLossPercentage=gainPercentage,gainUsdt=gainUsdt,buyedByRobot=buyedByRobot,indicatorResults=indicatorResults,strategy=buyingStrategy,passedHoursToSell=passedHoursToSell)
        tradeLog.save()
        if buyedByRobot is False and buyOrSell=='SELL': 
            addOrRemoveRobotUsingUsdt(float(processQuantity*processPrice))
    return process

def isSellingAll(myTrade):
    result = False
    if float(getTotalCountByTrade(myTrade)) < (float(myTrade.count)*1.1):#Yüzde 10 üzerinden daha fazla fark olduğuna göre tamamını satıyor
        result = True
    else : 
        result = False
    return result

def getTotalCountByTrade(myTrade):
    coinName=myTrade.coin.name
    exchangePairName = myTrade.exchangePair.name
    #totalCount=float(client.get_asset_balance(asset=coinName)['free'])
    totalCount=getRemainingAsset(coinName,exchangePairName,myTrade)
    return totalCount

def getOtherMainCoinToCompare(coin):
    otherCoin=''
    if (coin.endswith('USDT')):
        otherCoin = coin.replace("USDT", "BTC")
    elif (coin.endswith('BTC')):
        otherCoin = coin.replace("BTC", "USDT")
    #Eger bu cift borsada yoksa geriye bos dondurulur
    if otherCoin in marketPairsList:
        return otherCoin 
    else:
        return ''

def getIndicatorResults(activeCoinToCompare,isMarginCoin):
    RSI_15m=int(getRSI(activeCoinToCompare,'15m',5000))
    #Find other
    RSI_15m_other=RSI_1h_other=1
    otherCoinToCompare= getOtherMainCoinToCompare(activeCoinToCompare)
    if otherCoinToCompare!='':
        RSI_15m_other=int(getRSI(otherCoinToCompare,'15m',5000))
        RSI_1h_other=int(getRSI(otherCoinToCompare,'1h',5000))
    RSI_30m=int(getRSI(activeCoinToCompare,'30m',5000))
    RSI_1h=int(getRSI(activeCoinToCompare,'1h',5000))
    RSI_2h=int(getRSI(activeCoinToCompare,'2h',5000))
    RSI_4h=int(getRSI(activeCoinToCompare,'4h',5000))
    WilliamR_1d=int(getWilliamR(activeCoinToCompare,'1d',5000))
    resultText=''
    if isMarginCoin:
        btc_RSI_15m=int(getRSI('BTCUSDT','15m',5000))
        btc_RSI_15m_String=''
        if btc_RSI_15m>=50:
            btc_RSI_15m_String='<b class="red">',btc_RSI_15m,'</b>'
        else:
            btc_RSI_15m_String='<b class="green">',btc_RSI_15m,'</b>'
        resultText='<b class="blue">R15 ',activeCoinToCompare,':',RSI_15m,'R15 ',otherCoinToCompare,':',RSI_15m_other,'</b> R30:',RSI_30m,'R1h ',activeCoinToCompare,':',RSI_1h,'R1h ',otherCoinToCompare,':',RSI_1h_other,'<br>R2h:',RSI_2h,'R4h:',RSI_4h,'W1d:',WilliamR_1d,'<br><b>Btc/Usdt R15:</b>',btc_RSI_15m_String
    else :
        resultText='<b class="blue">R15 ',activeCoinToCompare,':',RSI_15m,'R15 ',otherCoinToCompare,':',RSI_15m_other,'</b> R30:',RSI_30m,'R1h ',activeCoinToCompare,':',RSI_1h,'R1h ',otherCoinToCompare,':',RSI_1h_other,'<br>R2h:',RSI_2h,'<b>R4h:</b><b class="blue">',RSI_4h,'</b>W1d:',WilliamR_1d
    return resultText

def actions(request):
    return render(request, 'trade/actions.html', actions_page_values(request))

def actions_page_values(request):
    myPreferences=Preferences.objects.all().first()
    coinList=Coin.objects.filter(isActive=True).order_by('name')
    tradeLogList=TradeLog.objects.all().order_by('-transactionDate')
    values={'myPreferences':myPreferences,'coinList':coinList,'tradeList':getAllTradeList(),'tradeLogList':tradeLogList}
    return values

def changePanicModeAction(request):
    myPreferences=Preferences.objects.all().first()
    if myPreferences.isPanicModeActive:
        panicModeDisableButton()
    else:
        panicModeActivateButton()
    return redirect("actions")

def buyWithFullAutomaticallyAction(request):
    firstCoin = request.POST['firstCoinBuy']
    secondCoin = 'USDT'
    finalQuantity = minimizeNumber(findQuantityByCurrentPriceAndTrustRateToBuy(firstCoin,secondCoin)) #Adeti otomatik bulmak için tespit
    buyWithMarketPriceByQuantityAction(firstCoin,secondCoin,finalQuantity,False,'Web_Manuel')
    return redirect("actions")

def addOrRemoveBudgetFromRobotAction(request):
    value = request.POST['addOrRemoveBudgetFromRobot']
    addOrRemoveRobotUsingUsdt(float(value))
    return redirect("actions")

def buyWithDolarValueAction(request):
    firstCoinBuyValueWithDolar = request.POST['firstCoinBuyValueWithDolar']
    firstCoin = request.POST['firstCoinBuyWithDolar']
    secondCoin = 'USDT'
    buyWithMarketPriceByTotalPriceAction(firstCoin,secondCoin,float(firstCoinBuyValueWithDolar),False,'Web_Manuel')
    return redirect("actions")

def sellAllByCoinAction(request):
    firstCoin = request.POST['firstCoinSell']
    secondCoin = 'USDT'
    sellAllForCoinAction(firstCoin,secondCoin,None)
    return redirect("actions")

def sellAllByTradeAction(request):
    activeTradeId = request.POST['tradeToSell']
    #print('secili:',activeTradeId)
    activeTrade = Trade.objects.filter(id=int(activeTradeId)).first()
    finalQuantity = minimizeNumber(findQuantityByTradeToSell(activeTrade))
    sellWithMarketPriceByQuantityAction(activeTrade.coin.name,activeTrade.exchangePair.name,finalQuantity,activeTrade)
    return redirect("actions")

def removeMaxLimitForRobotAsUsdtFromPrefAfterManuelBuy(removeFromRobotMaxLimit):
    myPreferences=Preferences.objects.all().first()
    myPreferences.maxLimitForRobotAsUsdt=myPreferences.maxLimitForRobotAsUsdt-removeFromRobotMaxLimit
    myPreferences.save()
    totalBalanceHistoryList=TotalBalanceHistory.objects.all()
    for item in totalBalanceHistoryList:
        item.totalRobot=item.totalRobot-float(removeFromRobotMaxLimit)
        item.save()

def chart(request):
    #Pie Chart - All Coins
    usedUsdtForManuelNewAsUsdt=float(getNewValuesOfUsedUsdtForManuelAsUsdt())#Manuel alınan ve spotta bekleyen coinlerin son hali
    usedUsdtForRobotAsUsdt=float(getNewValuesOfUsedUsdtForRobotAsUsdt())#robotun kullandığı coinlerin tutarı
    usedUsdtForMarginRobotAsUsdt=float(getNewValuesOfUsedUsdtForMarginRobotAsUsdt())
    usedUsdtForMarginBTCRobotAsUsdt=float(getNewValuesOfUsedUsdtForMarginBTCRobotAsUsdt())
    myFreeUsdt=float(client.get_asset_balance(asset='USDT')['free'])#spot ta bekleten robot için kullanılacak usdt tutarı
    robotTotalNow = usedUsdtForRobotAsUsdt + myFreeUsdt
    myNewTradeToEarn=getNewUsedTradeForEarn()
    myUsdtToEarn=getUsedUsdtForEarn()
    myNewTotalEarn=myUsdtToEarn+myNewTradeToEarn
    myNewOtherExchangeUsdt=getNewOtherExchangeUsdt()#Diger borsadaki birikimlerin toplamı
    allTotalNew=usedUsdtForRobotAsUsdt+usedUsdtForMarginRobotAsUsdt+myFreeUsdt+usedUsdtForManuelNewAsUsdt+myNewTotalEarn+myNewOtherExchangeUsdt#Toplamları
    tempChartTradeTotalCoinPercentages=getCommonTradeList()
    dictChart ={}
    for i in tempChartTradeTotalCoinPercentages:
        if dictChart.get(i.coin.name) is None:
            dictChart[i.coin.name]=i
        else :
            if i.coin.name=='OTHERS' or (i.coin.name=='USDT' and i.isDifferentExchange is True):
                if dictChart.get('OTHERS') is None:
                    dictChart['OTHERS']=i
                else :
                    existing = dictChart['OTHERS']
                    existing.coin=Coin.objects.get(name='OTHERS')
                    existing.price=existing.price+i.price
                    existing.temp_currentPrice=existing.temp_currentPrice+i.temp_currentPrice
                    existing.count=1
                    existing.temp_totalCurrentPrice=existing.temp_currentPrice*existing.count
                    existing.temp_ratioToTotalPercentage=(100*existing.temp_totalCurrentPrice)/allTotalNew
                    dictChart['OTHERS']=existing
            elif i.coin.name=='USDT' or i.coin.name=='OTHERS':
                existing = dictChart[i.coin.name]
                existing.price=existing.price+i.price
                existing.temp_currentPrice=existing.temp_currentPrice+i.temp_currentPrice
                existing.count=1
                existing.temp_totalCurrentPrice=existing.temp_currentPrice*existing.count
                existing.temp_ratioToTotalPercentage=(100*existing.temp_totalCurrentPrice)/allTotalNew
                dictChart[i.coin.name]=existing
            else :
                existing = dictChart[i.coin.name]
                existing.count=existing.count+i.count
                existing.temp_totalCurrentPrice=existing.temp_currentPrice*existing.count
                existing.temp_ratioToTotalPercentage=(100*existing.temp_totalCurrentPrice)/allTotalNew
                dictChart[i.coin.name]=existing
    chartTradeTotalCoinPercentages=[]
    for x in dictChart:
        chartTradeTotalCoinPercentages.append(dictChart[x])
    #Line Chart - Total Common Usdt,totalCommonTl,totalRobot,totalEarn,totalOtherExchanges
    chartTotalBalanceHistory=[]
    tempchartTotalBalanceHistory = TotalBalanceHistory.objects.all().order_by('transactionDate')
    for row in tempchartTotalBalanceHistory:
        chartTotalBalanceHistory.extend(list(TotalBalanceHistory.objects.filter(id=row.id)))
    values={'chartTradeTotalCoinPercentages':chartTradeTotalCoinPercentages,'chartTotalBalanceHistory':chartTotalBalanceHistory}
    return render(request, 'trade/chart.html', values)

def getIsMarginCoin(coinName):
    result = False
    marginCoinList = Coin.objects.filter(isMargin=True)
    for marginCoin in marginCoinList:
        if coinName == marginCoin.name:
            result = True
    return result

def getIsMarginBTCCoin(coinName):
    result = False
    marginCoinList = Coin.objects.filter(isMargin=True,name__startswith='BTC')
    for marginCoin in marginCoinList:
        if coinName == marginCoin.name:
            result = True
    return result

def getMaxLimit(myPreferences,isBtcHigherThan10PercentageFromEma):
    maxLimit=0
    if isBtcHigherThan10PercentageFromEma:
        maxLimit=myPreferences.maxLimitForRobotAsUsdt
    else:
        maxLimit=myPreferences.maxLimitForRobotAsUsdt/2
    return maxLimit

def getInfoFields():
    #info = client.get_isolated_margin_account()
    myPreferences=Preferences.objects.all().first()
    isStillCheap=getIsStillCheap()
    usedUsdtForRobotAsUsdt=float(getNewValuesOfUsedUsdtForRobotAsUsdt())#robotun kullandığı coinlerin tutarı
    usedUsdtForMarginRobotAsUsdt=float(getNewValuesOfUsedUsdtForMarginRobotAsUsdt())#robotun kullandığı coinlerin tutarı
    usedUsdtForMarginBTCRobotAsUsdt=float(getNewValuesOfUsedUsdtForMarginBTCRobotAsUsdt())
    usedUsdtForRobot15mAsUsdt=float(getNewValuesOfUsedUsdtForRobot15mAsUsdt())#robotun kullandığı coinlerin tutarı
    usedUsdtForRobot15mWITHRealMarginAsUsdt=float(getNewValuesOfUsedUsdtForRobot15mWITHRealMarginAsUsdt())#robotun kullandığı coinlerin tutarı
    usedUsdtForRobot15mSlowAsUsdt=float(getNewValuesOfUsedUsdtForRobot15mSlowAsUsdt())#robotun kullandığı coinlerin tutarı
    usedUsdtForRobot1hAsUsdt=float(getNewValuesOfUsedUsdtForRobot1hAsUsdt())#robotun kullandığı coinlerin tutarı
    myFreeUsdt=float(client.get_asset_balance(asset='USDT')['free'])#spot ta bekleten robot için kullanılacak usdt tutarı
    robotTotalLimit = myPreferences.maxLimitForRobotAsUsdt
    marginRobotTotalLimit = myPreferences.maxLimitForMarginAsUsdt
    marginBTCRobotTotalLimit = myPreferences.maxLimitForMarginBTCAsUsdt
    maxLimitForRobot15mAsUsdt = myPreferences.maxLimitForRobot15mAsUsdt
    maxLimitForRobot15mWITHRealMarginAsUsdt = myPreferences.maxLimitForRobot15mWITHRealMarginAsUsdt
    maxLimitForRobot15mSlowAsUsdt = myPreferences.maxLimitForRobot15mSlowAsUsdt
    maxLimitForRobot1hAsUsdt = myPreferences.maxLimitForRobot1hAsUsdt
    robotTotalNow = usedUsdtForRobotAsUsdt + myFreeUsdt
    robotResultHistoryAsUsdt = myPreferences.robotResultHistoryAsUsdt
    marginResultHistoryAsUsdt=myPreferences.marginResultHistoryAsUsdt
    marginBTCResultHistoryAsUsdt=myPreferences.marginBTCResultHistoryAsUsdt
    robot15mResultHistoryAsUsdt=myPreferences.robot15mResultHistoryAsUsdt
    robot15mWITHRealMarginResultHistoryAsUsdt=myPreferences.robot15mWITHRealMarginResultHistoryAsUsdt
    robot1hResultHistoryAsUsdt=myPreferences.robot1hResultHistoryAsUsdt
    robot15mSlowResultHistoryAsUsdt=myPreferences.robot15mSlowResultHistoryAsUsdt
    robotPercentageUSDT = getGainPercentage(robotTotalLimit,(robotTotalLimit+robotResultHistoryAsUsdt))
    marginRobotPercentageUSDT = getGainPercentage(marginRobotTotalLimit,(marginRobotTotalLimit+marginResultHistoryAsUsdt))
    marginBTCRobotPercentageUSDT = getGainPercentage(marginRobotTotalLimit,(marginRobotTotalLimit+marginBTCResultHistoryAsUsdt))
    robot15mPercentageUSDT = getGainPercentage(maxLimitForRobot15mAsUsdt,(maxLimitForRobot15mAsUsdt+robot15mResultHistoryAsUsdt))
    robot15mWITHRealMarginPercentageUSDT = getGainPercentage(maxLimitForRobot15mWITHRealMarginAsUsdt,(maxLimitForRobot15mWITHRealMarginAsUsdt+robot15mWITHRealMarginResultHistoryAsUsdt))
    robotGainPercentageUSDT = getGainPercentage(myPreferences.temp_startForRobotAsUsdt,(myPreferences.temp_startForRobotAsUsdt+robotResultHistoryAsUsdt))
    marginGainRobotPercentageUSDT = getGainPercentage(myPreferences.temp_startForMarginAsUsdt,(myPreferences.temp_startForMarginAsUsdt+marginResultHistoryAsUsdt))
    marginBTCGainRobotPercentageUSDT = getGainPercentage(myPreferences.temp_startForMarginBTCAsUsdt,(myPreferences.temp_startForMarginBTCAsUsdt+marginBTCResultHistoryAsUsdt))
    robot15mGainPercentageUSDT = getGainPercentage(myPreferences.temp_startForRobot15mAsUsdt,(myPreferences.temp_startForRobot15mAsUsdt+robot15mResultHistoryAsUsdt))
    robot15mWITHRealMarginGainPercentageUSDT = getGainPercentage(myPreferences.temp_startForRobot15mWITHRealMarginAsUsdt,(myPreferences.temp_startForRobot15mWITHRealMarginAsUsdt+robot15mWITHRealMarginResultHistoryAsUsdt))
    robot1hGainPercentageUSDT = getGainPercentage(myPreferences.temp_startForRobot1hAsUsdt,(myPreferences.temp_startForRobot1hAsUsdt+robot1hResultHistoryAsUsdt))
    robot15mSlowGainPercentageUSDT = getGainPercentage(myPreferences.temp_startForRobot15mSlowAsUsdt,(myPreferences.temp_startForRobot15mSlowAsUsdt+robot15mSlowResultHistoryAsUsdt))
    myUsdtToEarn=getUsedUsdtForEarn()
    myOldTradeToEarn=getOldUsedTradeForEarn()
    myNewTradeToEarn=getNewUsedTradeForEarn()
    myOldTotalEarn=myUsdtToEarn+myOldTradeToEarn
    myNewTotalEarn=myUsdtToEarn+myNewTradeToEarn
    tradeToEarnDiffUSDT=myNewTotalEarn-myOldTotalEarn
    tradeToEarnPercentageUSDT = getGainPercentage(myOldTotalEarn,myNewTotalEarn)
    usedUsdtForManuelNewAsUsdt=float(getNewValuesOfUsedUsdtForManuelAsUsdt())#Manuel alınan ve spotta bekleyen coinlerin son hali
    usedUsdtForManuelOldAsUsdt=float(getOldValuesOfUsedUsdtForManuelAsUsdt())#Manuel alınan ve spotta bekleyen coinlerin ilk hali
    manuelPercentageUSDT=getGainPercentage(usedUsdtForManuelOldAsUsdt,usedUsdtForManuelNewAsUsdt)
    manuelUSDTDiff=usedUsdtForManuelNewAsUsdt-usedUsdtForManuelOldAsUsdt
    myOldOtherExchangeUsdt=getOldOtherExchangeUsdt()#Diger borsadaki birikimlerin toplamı
    myNewOtherExchangeUsdt=getNewOtherExchangeUsdt()#Diger borsadaki birikimlerin toplamı
    otherExchangePercentageUSDT=getGainPercentage(myOldOtherExchangeUsdt,myNewOtherExchangeUsdt)
    otherExchangeUSDTDiff=myNewOtherExchangeUsdt-myOldOtherExchangeUsdt
    allTotalNew=usedUsdtForRobotAsUsdt+usedUsdtForRobot15mAsUsdt+usedUsdtForRobot15mWITHRealMarginAsUsdt+usedUsdtForRobot15mSlowAsUsdt+usedUsdtForRobot1hAsUsdt+usedUsdtForMarginRobotAsUsdt+myFreeUsdt+usedUsdtForManuelNewAsUsdt+myNewTotalEarn+myNewOtherExchangeUsdt#Toplamları
    commonTotalStartMoneyAsUSDT=myPreferences.commonTotalStartMoneyAsUSDT
    commonTotalStartMoneyAsTL=myPreferences.commonTotalStartMoneyAsTL
    btcusdt=getActivePrice('BTC','USDT')
    usdtl=getActivePrice('USDT','TRY')
    allTotalTLNew=allTotalNew*usdtl
    commonPercentageUSDT = getGainPercentage(commonTotalStartMoneyAsUSDT,allTotalNew)
    commonPercentageTL = getGainPercentage(commonTotalStartMoneyAsTL,allTotalTLNew)
    commonUSDTDiff=allTotalNew-commonTotalStartMoneyAsUSDT
    commonTLDiff=allTotalTLNew-commonTotalStartMoneyAsTL
    resettedDraftUsdtDiff=commonUSDTDiff-myPreferences.temp_draftUsdtDiffAction
    temp_draftUsdtDiffDateAction=myPreferences.temp_draftUsdtDiffDateAction
    lastRobotWorkingDate=(TotalBalanceHistory.objects.all().latest('transactionDate')).transactionDate
    activeMinRsi = getActiveMinRSI(myPreferences)
    lastEma50DayBTCPrice=getLastEma50DayBTCPrice()
    lastEma20DayBTCPrice=getLastEma20DayBTCPrice()
    lastEma20DayBTCPriceForBuy= lastEma20DayBTCPrice* 1.05
    lastEma20DayBTCPriceLower5Perc= lastEma20DayBTCPrice* 0.95
    lastEma20DayBTCPriceLower10Perc= lastEma20DayBTCPrice* 0.9
    isBtcHigherThan10PercentageFromEma = getIsBtcHigherThan10PercentageFromEma()
    isEmaHigherThanBTCPrice = getIsEmaHigherThanBTCPrice()
    isEmaHigherThanBTCPriceForFivePercPassed = getIsEmaHigherThanBTCPriceForFivePercPassed()
    is4hRobotActive = isStillCheap is True and myPreferences.isPanicModeActive is False and myPreferences.stopBuyingDateFor4h is None and (myPreferences.robotResultHistoryAsUsdt > myPreferences.lossLimitForRobot4h) and (myPreferences.isBuyingModeActive is True) and ((myPreferences.isEmaControlActiveForBuying is False) or (myPreferences.isEmaControlActiveForBuying is True and isEmaHigherThanBTCPrice==1))
    is15mRobotActive = isStillCheap is True and (myPreferences.robot15mResultHistoryAsUsdt > myPreferences.lossLimitForRobot15m) and isEmaHigherThanBTCPrice==1 and myPreferences.stopBuyingDateFor15m is None
    is15mWITHRealMarginRobotActive = isStillCheap is True and (myPreferences.robot15mWITHRealMarginResultHistoryAsUsdt > myPreferences.lossLimitForRobot15mWITHRealMargin) and isEmaHigherThanBTCPrice==1 and myPreferences.stopBuyingDateFor15mWITHRealMargin is None and (myPreferences.isRobot15mWITHRealMarginActive is True)
    is15mSlowRobotActive = isStillCheap is True and (myPreferences.robot15mSlowResultHistoryAsUsdt > myPreferences.lossLimitForRobot15mSlow) and isEmaHigherThanBTCPrice==1 and myPreferences.stopBuyingDateFor15mSlow is None
    isMarginRobotActive = isStillCheap is True and myPreferences.isMarginRobotActive and (myPreferences.marginResultHistoryAsUsdt > myPreferences.lossLimitForRobotMargin)  and myPreferences.stopBuyingDateForMargin is None and ((isEmaHigherThanBTCPrice==0 and myPreferences.isMarginRobotShortActive == True) or (isEmaHigherThanBTCPrice==1 and  myPreferences.isMarginRobotLongActive == True))
    is1hRobotActive = isStillCheap is True and (myPreferences.robot1hResultHistoryAsUsdt > myPreferences.lossLimitForRobot1h) and isEmaHigherThanBTCPrice==1 and myPreferences.stopBuyingDateFor1h is None
    activeMaxRsi = getActiveMaxRSI(myPreferences,isBtcHigherThan10PercentageFromEma)
    activeRsiFor15m = int(getRSI('BTCUSDT','15m',5000))
    activeRobotMaxLimit = getMaxLimit(myPreferences,isBtcHigherThan10PercentageFromEma)
    stopBuyingFinishFor4h = stopBuyingFinishFor15m = stopBuyingFinishFor15mSlow = stopBuyingFinishFor1h = stopBuyingFinishForMargin = stopBuyingFinishForMarginBTC = None
    if myPreferences.stopBuyingDateFor4h is not None : 
        stopBuyingFinishFor4h = myPreferences.stopBuyingDateFor4h + timedelta(hours=myPreferences.stopBuyingWaitingTime)
    if myPreferences.stopBuyingDateFor15m is not None : 
        stopBuyingFinishFor15m = myPreferences.stopBuyingDateFor15m + timedelta(hours=myPreferences.stopBuyingWaitingTime)
    if myPreferences.stopBuyingDateFor15mSlow is not None : 
        stopBuyingFinishFor15mSlow = myPreferences.stopBuyingDateFor15mSlow + timedelta(hours=myPreferences.stopBuyingWaitingTime)
    if myPreferences.stopBuyingDateFor1h is not None : 
        stopBuyingFinishFor1h = myPreferences.stopBuyingDateFor1h + timedelta(hours=myPreferences.stopBuyingWaitingTime)
    if myPreferences.stopBuyingDateForMargin is not None : 
        stopBuyingFinishForMargin = myPreferences.stopBuyingDateForMargin + timedelta(hours=myPreferences.stopBuyingWaitingTime)
    if myPreferences.stopBuyingDateForMarginBTC is not None : 
        stopBuyingFinishForMarginBTC = myPreferences.stopBuyingDateForMarginBTC + timedelta(hours=myPreferences.stopBuyingWaitingTimeMarginBTC)
    return {'marginResultHistoryAsUsdt':marginResultHistoryAsUsdt,"marginBTCResultHistoryAsUsdt":marginBTCResultHistoryAsUsdt,'robot15mResultHistoryAsUsdt':robot15mResultHistoryAsUsdt,'robot15mWITHRealMarginResultHistoryAsUsdt':robot15mWITHRealMarginResultHistoryAsUsdt,'robot15mSlowResultHistoryAsUsdt':robot15mSlowResultHistoryAsUsdt,'robot1hResultHistoryAsUsdt':robot1hResultHistoryAsUsdt,'usedUsdtForRobotAsUsdt':usedUsdtForRobotAsUsdt,'usedUsdtForRobot15mAsUsdt':usedUsdtForRobot15mAsUsdt,'usedUsdtForRobot15mWITHRealMarginAsUsdt':usedUsdtForRobot15mWITHRealMarginAsUsdt,'usedUsdtForRobot15mSlowAsUsdt':usedUsdtForRobot15mSlowAsUsdt,'usedUsdtForRobot1hAsUsdt':usedUsdtForRobot1hAsUsdt,'usedUsdtForMarginRobotAsUsdt':usedUsdtForMarginRobotAsUsdt,"usedUsdtForMarginBTCRobotAsUsdt":usedUsdtForMarginBTCRobotAsUsdt,'myFreeUsdt':myFreeUsdt,'robotTotalLimit':robotTotalLimit,'marginRobotTotalLimit':marginRobotTotalLimit,"marginBTCRobotTotalLimit":marginBTCRobotTotalLimit,'maxLimitForRobot15mAsUsdt':maxLimitForRobot15mAsUsdt,'maxLimitForRobot15mWITHRealMarginAsUsdt':maxLimitForRobot15mWITHRealMarginAsUsdt,'maxLimitForRobot15mSlowAsUsdt':maxLimitForRobot15mSlowAsUsdt,'maxLimitForRobot1hAsUsdt':maxLimitForRobot1hAsUsdt,'robotResultHistoryAsUsdt':robotResultHistoryAsUsdt,'robotPercentageUSDT':robotPercentageUSDT,'marginRobotPercentageUSDT':marginRobotPercentageUSDT,"marginBTCRobotPercentageUSDT":marginBTCRobotPercentageUSDT,'robot15mPercentageUSDT':robot15mPercentageUSDT,'robot15mWITHRealMarginPercentageUSDT':robot15mWITHRealMarginPercentageUSDT,'myUsdtToEarn':myUsdtToEarn,'usedUsdtForManuelOldAsUsdt':usedUsdtForManuelOldAsUsdt,'usedUsdtForManuelNewAsUsdt':usedUsdtForManuelNewAsUsdt,'manuelPercentageUSDT':manuelPercentageUSDT,'manuelUSDTDiff':manuelUSDTDiff,'myOldOtherExchangeUsdt':myOldOtherExchangeUsdt,'myNewOtherExchangeUsdt':myNewOtherExchangeUsdt,'otherExchangePercentageUSDT':otherExchangePercentageUSDT,'otherExchangeUSDTDiff':otherExchangeUSDTDiff,'allTotalNew':allTotalNew,'commonTotalStartMoneyAsUSDT':commonTotalStartMoneyAsUSDT,'commonPercentageUSDT':commonPercentageUSDT,'commonUSDTDiff':commonUSDTDiff,'allTotalTLNew':allTotalTLNew,'commonTLDiff':commonTLDiff,'commonTotalStartMoneyAsTL':commonTotalStartMoneyAsTL,'commonPercentageTL':commonPercentageTL,'usdtl':usdtl,'btcusdt':btcusdt,'myUsdtToEarn':myUsdtToEarn,'myOldTradeToEarn':myOldTradeToEarn,'myNewTradeToEarn':myNewTradeToEarn,'myOldTotalEarn':myOldTotalEarn,'myNewTotalEarn':myNewTotalEarn,'tradeToEarnDiffUSDT':tradeToEarnDiffUSDT,'tradeToEarnPercentageUSDT':tradeToEarnPercentageUSDT,'myPreferences':myPreferences,'lastEma20DayBTCPrice':lastEma20DayBTCPrice,'lastEma50DayBTCPrice':lastEma50DayBTCPrice,'lastEma20DayBTCPriceForBuy':lastEma20DayBTCPriceForBuy,'firstUsedUsdtForRobotAsUsdt':getUsedUsdtForRobotAsUsdt(),'firstUsedUsdtForRobot15mAsUsdt':getUsedUsdtForRobot15mAsUsdt(),'firstUsedUsdtForRobot15mWITHRealMarginAsUsdt':getUsedUsdtForRobot15mWITHRealMarginAsUsdt(),'firstUsedUsdtForRobot15mSlowAsUsdt':getUsedUsdtForRobot15mSlowAsUsdt(),'firstUsedUsdtForRobot1hAsUsdt':getUsedUsdtForRobot1hAsUsdt(), 'firstUsedUsdtForMarginRobotAsUsdt':getUsedUsdtForMarginRobotAsUsdt(),'firstUsedUsdtForMarginBTCRobotAsUsdt':getUsedUsdtForMarginBTCRobotAsUsdt(), 'firstUsedUsdtForMarginBTCRobotAsUsdt':getUsedUsdtForMarginBTCRobotAsUsdt(),'getUsedPercentageOfRobot':getUsedPercentageOfRobot(),'getUsedPercentageOfRobot15m':getUsedPercentageOfRobot15m(),'getUsedPercentageOfRobot15mWITHRealMargin':getUsedPercentageOfRobot15mWITHRealMargin(),'getUsedPercentageOfRobot15mSlow':getUsedPercentageOfRobot15mSlow(),'getUsedPercentageOfRobot1h':getUsedPercentageOfRobot1h(),'getUsedPercentageOfMarginRobot':getUsedPercentageOfMarginRobot(),'getUsedPercentageOfMarginBTCRobot':getUsedPercentageOfMarginBTCRobot(),'lastRobotWorkingDate':lastRobotWorkingDate,'activeMinRsi':activeMinRsi,'activeMaxRsi':activeMaxRsi,'activeRsiFor15m':activeRsiFor15m,'isBtcHigherThan10PercentageFromEma':isBtcHigherThan10PercentageFromEma,'robotTotalNow':robotTotalNow,'activeRobotMaxLimit':activeRobotMaxLimit,'resettedDraftUsdtDiff':resettedDraftUsdtDiff,'temp_draftUsdtDiffDateAction':temp_draftUsdtDiffDateAction,'is15mRobotActive':is15mRobotActive,'is15mWITHRealMarginRobotActive':is15mWITHRealMarginRobotActive,'is15mSlowRobotActive':is15mSlowRobotActive,'is1hRobotActive':is1hRobotActive,'is4hRobotActive':is4hRobotActive,'isMarginRobotActive':isMarginRobotActive,'robotGainPercentageUSDT':robotGainPercentageUSDT,'marginGainRobotPercentageUSDT':marginGainRobotPercentageUSDT,'marginBTCGainRobotPercentageUSDT':marginBTCGainRobotPercentageUSDT,'robot15mGainPercentageUSDT':robot15mGainPercentageUSDT,'robot15mWITHRealMarginGainPercentageUSDT':robot15mWITHRealMarginGainPercentageUSDT,'robot1hGainPercentageUSDT':robot1hGainPercentageUSDT,'robot15mSlowGainPercentageUSDT':robot15mSlowGainPercentageUSDT,'lastEma20DayBTCPriceLower5Perc':lastEma20DayBTCPriceLower5Perc,'lastEma20DayBTCPriceLower10Perc':lastEma20DayBTCPriceLower10Perc,'stopBuyingFinishFor4h':stopBuyingFinishFor4h,'stopBuyingFinishFor15m':stopBuyingFinishFor15m,'stopBuyingFinishFor15mSlow':stopBuyingFinishFor15mSlow,'stopBuyingFinishFor1h':stopBuyingFinishFor1h,'stopBuyingFinishForMargin':stopBuyingFinishForMargin,'stopBuyingFinishForMarginBTC':stopBuyingFinishForMarginBTC,'isStillCheap':isStillCheap}

def getIsBtcHigherThan10PercentageFromEma():
    btcusdt=getActivePrice('BTC','USDT')
    lastEma20DayBTCPrice=getLastEma20DayBTCPrice()
    isBtcHigherThan10PercentageFromEma = (10 < getGainPercentage(lastEma20DayBTCPrice,btcusdt))
    return isBtcHigherThan10PercentageFromEma

def getIsBtcLowerThan10PercentageFromEma():
    btcusdt=getActivePrice('BTC','USDT')
    lastEma20DayBTCPrice=getLastEma20DayBTCPrice()
    isBtcHigherThan10PercentageFromEma = (-10 >= getGainPercentage(lastEma20DayBTCPrice,btcusdt))
    return isBtcHigherThan10PercentageFromEma

def resetDraftUsdtDiffAction(request):
    infoFields=getInfoFields()
    myPreferences=Preferences.objects.all().first()
    myPreferences.temp_draftUsdtDiffAction=infoFields.get('commonUSDTDiff')
    myPreferences.temp_draftUsdtDiffDateAction=datetime.now() #timezone.now()
    myPreferences.save()
    return redirect("mainPage")
    
def mainPage(request):
    return render(request, 'trade/mainpage.html', getInfoFields())

def activeTrades(request):
    trades_list=getCommonTradeList()
    values={'tradeList': trades_list}
    return render(request, 'trade/index.html', values)

def getCommonTradeList():
    trades_list=[]
    usedUsdtForRobotAsUsdt=float(getNewValuesOfUsedUsdtForRobotAsUsdt())#robotun kullandığı coinlerin tutarı
    usedUsdtForRobot15mAsUsdt=float(getNewValuesOfUsedUsdtForRobot15mAsUsdt())
    usedUsdtForMarginRobotAsUsdt=float(getNewValuesOfUsedUsdtForMarginRobotAsUsdt())
    myFreeUsdt=float(client.get_asset_balance(asset='USDT')['free'])#spot ta bekleten robot için kullanılacak usdt tutarı
    robotTotalNow = usedUsdtForRobotAsUsdt + usedUsdtForRobot15mAsUsdt + myFreeUsdt
    myUsdtToEarn=getUsedUsdtForEarn()
    myNewTradeToEarn=getNewUsedTradeForEarn()
    myNewTotalEarn=myUsdtToEarn+myNewTradeToEarn
    usedUsdtForManuelNewAsUsdt=float(getNewValuesOfUsedUsdtForManuelAsUsdt())#Manuel alınan ve spotta bekleyen coinlerin son hali
    myNewOtherExchangeUsdt=getNewOtherExchangeUsdt()#Diger borsadaki birikimlerin toplamı
    allTotalNew=usedUsdtForRobotAsUsdt+usedUsdtForRobot15mAsUsdt+usedUsdtForMarginRobotAsUsdt+myFreeUsdt+usedUsdtForManuelNewAsUsdt+myNewTotalEarn+myNewOtherExchangeUsdt#Toplamları
    btcusdt=getActivePrice('BTC','USDT')
    myFreeUsdt=float(client.get_asset_balance(asset='USDT')['free'])#spot ta bekleten robot için kullanılacak usdt tutarı
    tempTradesList=Trade.objects.all().order_by('-transactionDate')
    for item in tempTradesList:
        if item.coin.name=='USDT' or item.coin.name=='OTHERS':#USDT olarak girilmiş farklı borsa birikimleri
            item.temp_totalCurrentPrice=item.count*item.temp_currentPrice
            item.temp_profitLossPercentage=getGainPercentage(item.price,item.temp_currentPrice)
            item.temp_differenceToBTCPercentage=getGainPercentage(item.firstPriceAgainstBtc,(item.temp_currentPrice/btcusdt))
            item.temp_profitLossTimes=item.temp_currentPrice/item.price
            item.temp_differenceTotalAsUSDT=item.temp_totalCurrentPrice-item.getTotalPrice()
            item.temp_ratioToTotalPercentage=(100*item.temp_totalCurrentPrice)/allTotalNew
            trades_list.append(item)
        else:
            item.temp_currentPrice=getActivePrice(item.coin.name,item.exchangePair.name)
            item.temp_totalCurrentPrice=item.count*item.temp_currentPrice
            item.temp_profitLossPercentage=getGainPercentage(item.price,item.temp_currentPrice)
            item.temp_differenceToBTCPercentage=getGainPercentage(item.firstPriceAgainstBtc,(item.temp_currentPrice/btcusdt))
            item.temp_profitLossTimes=item.temp_currentPrice/item.price
            item.temp_differenceTotalAsUSDT=item.temp_totalCurrentPrice-item.getTotalPrice()
            item.temp_ratioToTotalPercentage=(100*item.temp_totalCurrentPrice)/allTotalNew
            trades_list.append(item)
    trades_list.append(newUsdtItem(myFreeUsdt,allTotalNew,'False'))
    return trades_list

def newUsdtItem(price,allTotal,isPassiveInEarn):
    usdCoin = Coin.objects.get(name='USDT')    
    usdAsTrade = Trade(coin=usdCoin)
    usdAsTrade.isPassiveInEarn = isPassiveInEarn
    usdAsTrade.firstCount = 1
    usdAsTrade.count = 1
    usdAsTrade.price = price
    usdAsTrade.differentExchangeName = 'Binance'
    usdAsTrade.buyedByRobot = False
    usdAsTrade.temp_currentPrice = price
    if usdAsTrade.price == 0 :
        usdAsTrade.temp_profitLossTimes=usdAsTrade.temp_currentPrice
    else:
        usdAsTrade.temp_profitLossTimes=usdAsTrade.temp_currentPrice/usdAsTrade.price
    usdAsTrade.temp_totalCurrentPrice = usdAsTrade.count*usdAsTrade.temp_currentPrice
    usdAsTrade.temp_ratioToTotalPercentage = (100*usdAsTrade.temp_totalCurrentPrice)/allTotal
    return usdAsTrade

def buySelectedCoinsAfterPanicMode():
    coinsToBuyList = Coin.objects.filter(isBuyAutomaticallyAfterPanicMode=True)
    exchangePair="USDT"
    for activeCoin in coinsToBuyList:
        finalQuantity=minimizeNumber(findQuantityByCurrentPriceAndTrustRateToBuy(activeCoin.name,exchangePair))
        buyWithMarketPriceByQuantityAction(activeCoin.name,exchangePair,finalQuantity,False,'Specified_Priority_Purchases')
    myPreferences=Preferences.objects.all().first()
    myPreferences.isBuyAutomaticallyAfterPanicMode = False
    myPreferences.save()

def controlForAddBudgetToRobotAction(activeBtcUsdtPrice):
    global mailSubject
    myPreferences=Preferences.objects.all().first()
    if (activeBtcUsdtPrice > myPreferences.addBudgetToRobotWhenTargetToTopComes_BtcTargetArea and myPreferences.addBudgetToRobotWhenTargetToTopComes_BtcTargetArea >0) and myPreferences.addBudgetToRobotWhenTargetToTopComes_AddBudget>0:
        addOrRemoveRobotUsingUsdt(myPreferences.addBudgetToRobotWhenTargetToTopComes_AddBudget)
        myPreferences.addBudgetToRobotWhenTargetToTopComes_BtcTargetArea=0
        myPreferences.addBudgetToRobotWhenTargetToTopComes_AddBudget=0
        myPreferences.save()
        mailSubject = mailSubject , 'Otomatik robot bütçe arttırımı yapıldı(nereden eklediysen o trade den bu tutarı düşmeyi unutma) '#Elle manuel olarak yapılacak => nereden eklediysen o trade den bu tutarı düşmeyi unutma

def getLast6HoursUsedActive4hTradesCost():
    result=0
    date_from = (datetime.now() - timedelta(hours=6)).replace(tzinfo=None)
    tradeList = Trade.objects.filter(transactionDate__gte=date_from,isMargin=False,strategy='RSI_4h').exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS'))
    for trade in tradeList:
        result = result + trade.getTotalPrice()
    return result

def getLast6HoursUsedActive15mTradesCost():
    result=0
    date_from = (datetime.now() - timedelta(hours=6)).replace(tzinfo=None)
    tradeList = Trade.objects.filter(transactionDate__gte=date_from,isMargin=False,strategy='RSI_15m').exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS'))
    for trade in tradeList:
        result = result + trade.getTotalPrice()
    return result

def getLast6HoursUsedActive15mWITHRealMarginTradesCost():
    result=0
    date_from = (datetime.now() - timedelta(hours=6)).replace(tzinfo=None)
    tradeList = Trade.objects.filter(transactionDate__gte=date_from,isMargin=False,strategy='RSI_15m_WITHRealMargin').exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS'))
    for trade in tradeList:
        result = result + trade.getTotalPrice()
    return result

def getLast6HoursUsedActive15mSlowTradesCost():
    result=0
    date_from = (datetime.now() - timedelta(hours=6)).replace(tzinfo=None)
    tradeList = Trade.objects.filter(transactionDate__gte=date_from,isMargin=False,strategy='RSI_15m_Slow').exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS'))
    for trade in tradeList:
        result = result + trade.getTotalPrice()
    return result

def getLast6HoursUsedActive1hTradesCost():
    result=0
    date_from = (datetime.now() - timedelta(hours=6)).replace(tzinfo=None)
    tradeList = Trade.objects.filter(transactionDate__gte=date_from,isMargin=False,strategy='RSI_1h').exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS'))
    for trade in tradeList:
        result = result + trade.getTotalPrice()
    return result

def getLast6HoursUsedActiveMarginTradesCost():        
    result=0
    date_from = (datetime.now() - timedelta(hours=6)).replace(tzinfo=None)
    tradeList = Trade.objects.filter(transactionDate__gte=date_from,isMargin=True).exclude(coin=Coin.objects.get(name='USDT')).exclude(coin=Coin.objects.get(name='OTHERS'))
    for trade in tradeList:
        result = result + trade.getTotalPrice()
    return result

###################################################################################################################################################################5
import os
from celery import Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trade.settings')
app = Celery('trade')
app.config_from_object('django.conf:settings', namespace='CELERY')
CAR_BROKER_URL = 'redis://localhost:6379'
app.autodiscover_tasks()

# @app.task
# def run_robot_oldAndNotUsing():
#     timet.sleep(7)#celery taskları aynı anda başladığından lock olmaması için beklettim
#     myP=Preferences.objects.all().first()
#     if myP.temp_isRobotWorkingNow:
#         print('diğer robot çalıştığı için run_robot çalıştırılmadı')
#         return ''
#     else :
#         myP.temp_isRobotWorkingNow=True
#         myP.lastRobotWorkingDate=datetime.now() #timezone.now()
#         myP.save()
#         # msg = 'run_robot calisma saati:', datetime.today()
#         # msg = fixString(msg)
#         # print(msg)
#     if getIsBtcLowerThan10PercentageFromEma():
#         myPreferencesErr=Preferences.objects.all().first()
#         myPreferencesErr.temp_isRobotWorkingNow = False
#         myPreferencesErr.save()
#         return ''#while(True):
#     global mailSubject
#     global resultMail
#     global workTimeCounter
#     global boughtCoins
#     global soldCoins
#     global notBoughSignalComeButNoLimit
#     global nearlyBuyCoins
#     global nearlySellCoins
#     global boughtCoinsTotalUsdt
#     boughtCoinsTotalUsdt=0
#     isSellingOneStepIfDoesntPassEMAControlModeActive= isPanicModeActive=isExistFromPanicModeAutomaticallyActive=''
#     isBuyingModeActive=btcSellSignalResult=isSellingModeActive=isEmaControlActiveForBuying=''
#     resultMail=mailSubject=boughtCoins=soldCoins=notBoughSignalComeButNoLimit=nearlyBuyCoins=nearlySellCoins=''
#     sendMailAnyway=False
#     api_key='WGKjpwDd7w8fgFeCnIhtk1b0ctq2tfNCzAOiV7aLODqsT7z8ONyShR07ZZRnu9OQ'
#     api_secret='ViPzA8YB67RIP1BRYAcDXj6BotoBsQvVikFxdIKajR7L5i3TIGsm1AruuR6Gb4W0'
#     client=Client(api_key,api_secret)
#     isEmaHigherThanBTCPrice=getIsEmaHigherThanBTCPrice()
#     #isEmaHigherThanBTCPriceForFivePercPassed = getIsEmaHigherThanBTCPriceForFivePercPassed()
#     isControlForPanicModeAutomaticallyWorked(isEmaHigherThanBTCPrice) 
#     # infoFields=getInfoFields()
#     myPreferences=Preferences.objects.all().first()
#     isBuyingModeActive=myPreferences.isBuyingModeActive
#     isSellingModeActive=myPreferences.isSellingModeActive
#     isEmaControlActiveForBuying=myPreferences.isEmaControlActiveForBuying
#     isSellingOneStepIfDoesntPassEMAControlModeActive=myPreferences.isSellingOneStepIfDoesntPassEMAControlModeActive
#     coinTargetToCollect=myPreferences.coinTargetToCollect
#     isPanicModeActive=myPreferences.isPanicModeActive
#     minRSI=myPreferences.minRSI
#     midRSI=myPreferences.midRSI
#     maxRSI=myPreferences.maxRSI
#     williamR=myPreferences.williamR
#     isExistFromPanicModeAutomaticallyActive=myPreferences.isExistFromPanicModeAutomaticallyActive
#     isBuyAutomaticallyAfterPanicMode=myPreferences.isBuyAutomaticallyAfterPanicMode
#     coinList=Coin.objects.filter(openToBuy=True,isActive=True,isMargin=False)
#     resultMail=' Min RSI:',minRSI, ', Mid RSI:',midRSI,' Max RSI:',maxRSI,' WilliamR:',williamR,'<br>', resultMail
#     controlForAddBudgetToRobotAction(getActivePrice('BTC','USDT'))
#     isBtcHigherThan10PercentageFromEma = getIsBtcHigherThan10PercentageFromEma()
#     maxLimit=getMaxLimit(myPreferences,isBtcHigherThan10PercentageFromEma)
#     maxLimitToBuy=(myPreferences.maxLimitForRobotAsUsdt/4)-getLast6HoursUsedActive4hTradesCost() #Bir kerede herşeyi alıp bitirmesin diye son 6 saatte en fazla limitin 4'te 1'ini kullanabilir
#     isEmaLowerThanBTC10Perc = getIsEmaLowerThanBTC10Perc()
#     if isSellingModeActive is True :#Selling
#         resultMail= resultMail, '<br><br><b>SATIŞ KISMI :</b><br><br>'
#         if isEmaLowerThanBTC10Perc==1 and isSellingOneStepIfDoesntPassEMAControlModeActive is True: 
#                 resultMail= '<b>Ema kontrolu gecemedigi ve birer kademe satis secenegi acik oldugu icin satis yapilacak</b>',' <br>',resultMail
#                 sellOneStepFromAllPositiveCoinsButton()
#         else :
#             tradeList=getTradeList()
#             for activeTrade in tradeList:
#                 if activeTrade.isPassiveInEarn is False and (isTimeToSellForManuelTradesCalculatedByPowerOfTwo(activeTrade)  is True and getGainByTradeAsPercentage(activeTrade)>myPreferences.targetPercentageForSelling):
#                     resultMail=' <b>1.satis yontemine uydugu icin ',activeTrade.coin.name ,' satiliyor</b> <br>',resultMail
#                     finalQuantity=minimizeNumber(findQuantityByTradeToSell(activeTrade))
#                     sellResult=sellWithMarketPriceByQuantityAction(activeTrade.coin.name,activeTrade.exchangePair.name,finalQuantity,activeTrade)#print(activeCoin.name, " sell manuel result: ", sellResult)
#             tradeList=getTradeList()
#             for activeTrade in tradeList:
#                 if activeTrade.isPassiveInEarn is False and activeTrade.buyedByRobot is True:
#                     activeCoin=activeTrade.coin
#                     sellResult=sellSignal(activeCoin.name,activeCoin.preferredCompareCoinName,activeCoin.name,'USDT',activeTrade,isBtcHigherThan10PercentageFromEma)#print(activeCoin.name, " sell result: ", sellResult)
#     if isPanicModeActive is False and myPreferences.stopBuyingDateFor4h is None:#Buying and Others
#         if getIsStillCheap() is True and (myPreferences.robotResultHistoryAsUsdt > myPreferences.lossLimitForRobot4h) and (isBuyingModeActive is True) and ((isEmaControlActiveForBuying is False) or (isEmaControlActiveForBuying is True and isEmaHigherThanBTCPrice==1)):
#             resultMail= resultMail, '<br><br><b>ALIŞ KISMI :</b><br><br>'
#             if coinTargetToCollect=='BTC':
#                 btcResult=buySignal('BTC','USDT','BTC','USDT',maxLimit)#print('BTC','USDT', " buy result: ", btcResult)
#             for activeCoin in coinList:
#                 if maxLimitToBuy>boughtCoinsTotalUsdt:#print(activeCoin.name, " icin isleme baslaniyor ")
#                     buyResult=buySignal(activeCoin.name,activeCoin.preferredCompareCoinName,activeCoin.name,'USDT',maxLimit)#print(activeCoin.name, " buy result: ", buyResult)
#     elif isEmaHigherThanBTCPrice==1 and isExistFromPanicModeAutomaticallyActive is True:
#         panicModeDisableButton()
#         if isBuyAutomaticallyAfterPanicMode:
#             buySelectedCoinsAfterPanicMode()
#         resultMail=' <br>  <b>Ema kontrolunun duzelmesi sebebiyle panik durumundan cikildi. Alimalar tekrar baslayacak.</b> <br>',resultMail
#         mailSubject = mailSubject , 'Ema kontrolunun duzelmesi sebebiyle panik durumundan cikildi. Alimalar tekrar baslayacak.'
#         sendMailAnyway=True
#     else :
#         mailSubject = mailSubject , 'Panik durumu devam ediyor'
#         resultMail=' <br>  <b>Panik durumu devam ediyor</b>',resultMail
#     # infoFieldsForMail = '<b>Genel Durum USDT</b> => Başlangıç Toplam:',round(infoFields.get('commonTotalStartMoneyAsUSDT'),2),',Oto. Anlık Toplam:',round(infoFields.get('allTotalNew'),2) ,',Kar/Zarar:',round(infoFields.get('commonUSDTDiff'),2),',Kar/Zarar Oranı:%',round(infoFields.get('commonPercentageUSDT'),2),'<br><b>Genel Durum TL</b> => Başlangıç Toplam:',round(infoFields.get('commonTotalStartMoneyAsTL'),2),',Oto. Anlık Toplam:',round(infoFields.get('allTotalTLNew'),2) ,',Kar/Zarar:',round(infoFields.get('commonTLDiff'),2),',Kar/Zarar Oranı:%',round(infoFields.get('commonPercentageTL'),2),'<br><br><b>Dolar:',round(infoFields.get('usdtl'),2),',Btc:',round(infoFields.get('btcusdt'),2),',Ema:',round(infoFields.get('lastEma20DayBTCPrice'),2),',Ema %5 üzeri:',round(infoFields.get('lastEma20DayBTCPriceForBuy'),2),'</b><br><br><br><b>Satin alinanlar:</b><br> ',boughtCoins,' / <br><b>Satis yapilanlar:</b><br> ',soldCoins ,' / <br><b>Sinyal gelip alinamayan:</b><br>', notBoughSignalComeButNoLimit ,' / <br><b>Yaklaşanlar Alış:</b><br>', nearlyBuyCoins ,' / <br><b>Yaklaşanlar Satış:</b><br>',nearlySellCoins,'<br><br>'
#     # infoFieldsForMail = infoFieldsForMail , '<b>Çalışma Durumları</b> ' , '<br>Robot RSI_4h Çalışıyor:', infoFields.get('is4hRobotActive') , '<br>Robot RSI_15m Çalışıyor:',  infoFields.get('is15mRobotActive') , '<br>Robot Margin Çalışıyor:',  infoFields.get('isMarginRobotActive') 
#     # infoFieldsForMail = infoFieldsForMail , '<br><br><b>Detaylar</b> ' 
#     # infoFieldsForMail = infoFieldsForMail , '<br>Robot RSI_4h => Robot un kullandığı:',round(infoFields.get('usedUsdtForRobotAsUsdt'),2),',Bekleyen',round(infoFields.get('myFreeUsdt'),2),',Limit":',round(infoFields.get('robotTotalLimit'),2),',Kar/Zarar:',round(infoFields.get('robotResultHistoryAsUsdt'),2),',Kar/Zarar Oranı:%',round(infoFields.get('robotPercentageUSDT'),2)
#     # infoFieldsForMail = infoFieldsForMail , '<br>Robot RSI_15m => ','Kullanılan:', round(infoFields.get('usedUsdtForRobot15mAsUsdt'),2),'Kar/Zarar :', round(infoFields.get('robot15mResultHistoryAsUsdt'),2),'Limit :', round(infoFields.get('maxLimitForRobot15mAsUsdt'),2),'Kar/Zarar Oranı:', round(infoFields.get('robot15mPercentageUSDT'),2)
#     # infoFieldsForMail = infoFieldsForMail , '<br>Robot Margin => ', 'Kullanılan:', round(infoFields.get('usedUsdtForMarginRobotAsUsdt'),2),'Kar/Zarar :', round(infoFields.get('marginResultHistoryAsUsdt'),2),'Limit :', round(infoFields.get('marginRobotTotalLimit'),2),'Kar/Zarar Oranı:', round(infoFields.get('marginRobotPercentageUSDT'),2)
#     # infoFieldsForMail = infoFieldsForMail , '<br>Manuel => Manuel Alınanlar İlk Hali:',round(infoFields.get('usedUsdtForManuelOldAsUsdt'),2),',Manuel Alınanlar Son Hali:',round(infoFields.get('usedUsdtForManuelNewAsUsdt'),2),',Kar/Zarar Manuel:',round(infoFields.get('manuelUSDTDiff'),2),',Kar/Zarar Oranı:%',round(infoFields.get('manuelPercentageUSDT'),2)
#     # infoFieldsForMail = infoFieldsForMail , '<br>Kazan => Coin ler İlk Hali:',round(infoFields.get('myOldTradeToEarn'),2),',Coin ler Son Hali:',round(infoFields.get('myNewTradeToEarn'),2),',Kazan bölümünde bekleyen:',round(infoFields.get('myUsdtToEarn'),2),',Eski toplamı:',round(infoFields.get('myOldTotalEarn'),2),',Yeni toplamı:',round(infoFields.get('myNewTotalEarn'),2),',Kar/Zarar:',round(infoFields.get('tradeToEarnDiffUSDT'),2),',Kar/Zarar Oranı:%',round(infoFields.get('tradeToEarnPercentageUSDT'),2)
#     # resultMail = infoFieldsForMail , '<br><br>',resultMail 
#     mailSent=False
#     if workTimeCounter >= 8:
#         workTimeCounter=0
#     if len(boughtCoins)>0 or len(soldCoins)>0:#Alım & Satım
#         workTimeCounter=1
#         mailSubject = 'Alim/Satim Bilgilendirme ',mailSubject
#         resultMail = boughtCoins , '<br>' , soldCoins , '<br>' , resultMail
#         sendMail(fixString(mailSubject),fixString(resultMail))
#         mailSent=True
#     elif sendMailAnyway:
#         workTimeCounter=1
#         mailSubject='Bilgilendirme ',mailSubject
#         sendMail(fixString(mailSubject),fixString(resultMail))
#         mailSent=True
#     elif workTimeCounter == 0:
#         if len(notBoughSignalComeButNoLimit)>0:
#             workTimeCounter=1
#             mailSubject='Sinyal Geldi Fakat Islem Yapilamadi ',mailSubject
#             resultMail = notBoughSignalComeButNoLimit , '<br>' , resultMail
#             sendMail(fixString(mailSubject),fixString(resultMail))
#             mailSent=True
#         elif len(nearlyBuyCoins)>0 or len(nearlySellCoins)>0:
#             workTimeCounter=1
#             mailSubject='Alış veya Satış Sinyaline Yaklasan Var (referans 4 Saatlik RSI) ',mailSubject #resultMail = '<b>Alım Sinyaline Yaklasanların Listesi :</b> <br>' ,nearlyBuyCoins , '<br>' , '<b>Satış Sinyaline Yaklasanların Listesi :</b> <br>' ,nearlySellCoins , '<br>' , resultMail
#             sendMail(fixString(mailSubject),fixString(resultMail))
#             mailSent=True
#         else:#Standart saatlik mail
#             workTimeCounter=workTimeCounter+1
#             mailSubject = 'Standart Mail ',mailSubject
#             sendMail(fixString(mailSubject),fixString(resultMail))
#             mailSent=True
#     else:
#         workTimeCounter=workTimeCounter+1
#     processresult = 'run_robot islem tamamlandi: ', getStringFromDate(datetime.today()), 'boughtCoins:', boughtCoins," soldCoins:",soldCoins , ' Mail Gonderildi Mi?:',mailSent
#     processresult = fixString(processresult)
#     print(processresult)
#     myPref=Preferences.objects.all().first()
#     myPref.temp_isRobotWorkingNow = False
#     if (myPref.stopBuyingDateFor4h is not None) and (hourDiffNormal(myPref.stopBuyingDateFor4h,datetime.now())>myPref.stopBuyingWaitingTime):
#         myPref.stopBuyingDateFor4h = None
#     myPref.save()
#     return ''
#     #latestTotalBalanceHistoryTransactionDate=TotalBalanceHistory.objects.all().latest('transactionDate').transactionDate
#     #resultMail = latestTotalBalanceHistoryTransactionDate,resultMail
#     #newProcessLog=ProcessLog(processResult=processresult,processSubject=mailSubject,processDetails=resultMail)
#     #newProcessLog.save()
#     #timet.sleep(900)

@app.task
def run_robot_1h():
    # timet.sleep(1)#celery taskları aynı anda başladığından lock olmaması için beklettim
    # myP=Preferences.objects.all().first()
    # if myP.temp_isRobotWorkingNow:
    #     print('diğer robot çalıştığı için run_robot_1h çalıştırılmadı')
    #     return ''
    # else :
    #     myP.temp_isRobotWorkingNow=True
    #     myP.lastRobot1hWorkingDate=timezone.now()
    #     myP.save()
    #     msg = 'run_robot_1h calisma saati:', datetime.today()
    #     msg = fixString(msg)
    #     print(msg)
    myPreferencesErr=Preferences.objects.all().first()
    if getIsBtcLowerThan10PercentageFromEma():
        myPreferencesErr.temp_isRobotWorkingNow = False
        myPreferencesErr.save()
        return ''
    else:
        myPreferencesErr.lastRobot1hWorkingDate=datetime.now()
        myPreferencesErr.save()
    global mailSubject
    global resultMail
    global boughtCoins
    global soldCoins
    global nearlyBuyCoins
    global nearlySellCoins
    global boughtCoinsTotalUsdt
    boughtCoinsTotalUsdt=0
    mailSent=False
    resultMail=mailSubject=boughtCoins=soldCoins=nearlyBuyCoins=nearlySellCoins=''
    myPreferences=Preferences.objects.all().first()
    maxLimitToBuy=(myPreferences.maxLimitForRobot1hAsUsdt/4)-getLast6HoursUsedActive1hTradesCost() #Bir kerede herşeyi alıp bitirmesin diye son 6 saatte en fazla limitin 4'te 1'ini kullanabilir
    if myPreferences.isRobot1hActive:
        isEmaHigherThanBTCPrice=getIsEmaHigherThanBTCPrice()
        isEmaHigherThan4hBTCPrice=getIsEmaHigherThan4hBTCPrice()
        isEmaLowerThanBTC10Perc = getIsEmaLowerThanBTC10Perc()
        buysignal=sellsignal=''
        isSellAllWorked=False
        #Günlük EMA Kontrolüne göre yön değişikliği için gerekli satışlar yapılır.
        if myPreferences.isControlEmaForSellingPreviousRobot1hTrades:
            if isEmaLowerThanBTC10Perc==1:#Ema nın %10 altında düşerse eski tradeleri sat
                sellEverythingRobot1hAndBuyUsdt()
                isSellAllWorked=True
        #SELL
        tradeList=getTradeListForRobot1h()
        for activeTrade in tradeList:
            activeCoin=activeTrade.coin
            sellSignalForRobot1h(activeCoin.name,activeCoin.preferredCompareCoinName,activeCoin.name,'USDT',activeTrade)
        #BUY
        if getIsStillCheap() is True and (myPreferences.robot1hResultHistoryAsUsdt > myPreferences.lossLimitForRobot1h) and isEmaHigherThanBTCPrice==1 and isEmaHigherThan4hBTCPrice==1 and myPreferences.stopBuyingDateFor1h is None:
            coinList=Coin.objects.filter(openToBuy=True,isActive=True,isMargin=False,isUsableForRSI1h=True)
            for activeCoin in coinList:
                if maxLimitToBuy>boughtCoinsTotalUsdt:
                    buySignalForRobot1h(activeCoin.name,activeCoin.preferredCompareCoinName,activeCoin.name,'USDT')
        processresult = "run_robot_1h islem tamamlandi: ", getStringFromDate(datetime.today()), " boughtCoins:", boughtCoins," soldCoins:",soldCoins,"isSellAllWorked:",isSellAllWorked,'   Mail Gonderildi Mi?:',mailSent
        processresult = fixString(processresult)
        print(processresult)
    else:
        print('run_robot_1h çalışmıyor')
    myPreferencesEnd2=Preferences.objects.all().first()
    myPreferencesEnd2.temp_isRobotWorkingNow = False
    if (myPreferencesEnd2.stopBuyingDateFor1h is not None) and (hourDiff(myPreferencesEnd2.stopBuyingDateFor1h,datetime.now())>myPreferencesEnd2.stopBuyingWaitingTime):
        myPreferencesEnd2.stopBuyingDateFor1h = None
    myPreferencesEnd2.save()
    return ''

@app.task
def run_robot_15m_slow():
    #timet.sleep(5)#celery taskları aynı anda başladığından lock olmaması için beklettim
    # myP=Preferences.objects.all().first()
    # if myP.temp_isRobotWorkingNow:
    #     print('diğer robot çalıştığı için run_robot_15m_slow çalıştırılmadı')
    #     return ''
    # else :
    #     myP.temp_isRobotWorkingNow=True
    #     myP.lastRobot15mSlowWorkingDate=timezone.now()
    #     myP.save()
    #     msg = 'run_robot_15m_slow calisma saati:', datetime.today()
    #     msg = fixString(msg)
    #     print(msg) 
    myPreferencesErr=Preferences.objects.all().first()
    if getIsBtcLowerThan10PercentageFromEma():
        myPreferencesErr.temp_isRobotWorkingNow = False
        myPreferencesErr.save()
        return ''
    else:
        myPreferencesErr.lastRobot15mSlowWorkingDate=datetime.now()
        myPreferencesErr.save()
    global mailSubject
    global resultMail
    global boughtCoins
    global soldCoins
    global nearlyBuyCoins
    global nearlySellCoins
    global boughtCoinsTotalUsdt
    global workTimeDateForSavingTotalBalanceHistory
    boughtCoinsTotalUsdt=0
    mailSent=False
    resultMail=mailSubject=boughtCoins=soldCoins=nearlyBuyCoins=nearlySellCoins=''
    myPreferences=Preferences.objects.all().first()
    maxLimitToBuy=(myPreferences.maxLimitForRobot15mSlowAsUsdt/4)-getLast6HoursUsedActive15mSlowTradesCost() #Bir kerede herşeyi alıp bitirmesin diye son 6 saatte en fazla limitin 4'te 1'ini kullanabilir
    if myPreferences.isRobot15mSlowActive:
        isEmaHigherThanBTCPrice=getIsEmaHigherThanBTCPrice()
        isEmaHigherThan4hBTCPrice=getIsEmaHigherThan4hBTCPrice()
        isEmaLowerThanBTC10Perc = getIsEmaLowerThanBTC10Perc()
        buysignal=sellsignal=''
        isSellAllWorked=False
        #Günlük EMA Kontrolüne göre yön değişikliği için gerekli satışlar yapılır.
        if myPreferences.isControlEmaForSellingPreviousRobot15mSlowTrades:
            if isEmaLowerThanBTC10Perc==1:#Ema nın %10 altında düşerse eski tradeleri sat
                sellEverythingRobot15mSlowAndBuyUsdt()
                isSellAllWorked=True
        #SELL
        tradeList=getTradeListForRobot15mSlow()
        for activeTrade in tradeList:
            activeCoin=activeTrade.coin
            sellSignalForRobot15mSlow(activeCoin.name,activeCoin.preferredCompareCoinName,activeCoin.name,'USDT',activeTrade)
        #BUY
        if getIsStillCheap() is True and (myPreferences.robot15mSlowResultHistoryAsUsdt > myPreferences.lossLimitForRobot15mSlow) and isEmaHigherThanBTCPrice==1 and isEmaHigherThan4hBTCPrice==1 and myPreferences.stopBuyingDateFor15mSlow is None:
            coinList=Coin.objects.filter(openToBuy=True,isActive=True,isMargin=False,isUsableForRSI15m=True)
            print('maxLimitToBuy:',maxLimitToBuy,' boughtCoinsTotalUsdt:',boughtCoinsTotalUsdt)
            for activeCoin in coinList:
                if maxLimitToBuy>boughtCoinsTotalUsdt:
                    buySignalForRobot15mSlow(activeCoin.name,activeCoin.preferredCompareCoinName,activeCoin.name,'USDT')
        processresult = "run_robot_15m_slow islem tamamlandi: ", getStringFromDate(datetime.today()), " boughtCoins:", boughtCoins," soldCoins:",soldCoins,"isSellAllWorked:",isSellAllWorked,'   Mail Gonderildi Mi?:',mailSent
        processresult = fixString(processresult)
        print(processresult)
    else:
        print('run_robot_15m_slow çalışmıyor')
    myPreferencesEnd2=Preferences.objects.all().first()
    myPreferencesEnd2.temp_isRobotWorkingNow = False
    if (myPreferencesEnd2.stopBuyingDateFor15mSlow is not None) and (hourDiff(myPreferencesEnd2.stopBuyingDateFor15mSlow,datetime.now())>myPreferencesEnd2.stopBuyingWaitingTime):
        myPreferencesEnd2.stopBuyingDateFor15mSlow = None
    myPreferencesEnd2.save()
    return ''

@app.task
def run_robot_15m():
    #timet.sleep(3)#celery taskları aynı anda başladığından lock olmaması için beklettim
    #myP=Preferences.objects.all().first()
    # if myP.temp_isRobotWorkingNow:
    #     print('diğer robot çalıştığı için run_robot_15m çalıştırılmadı')
    #     return ''
    # else :
    #     myP.temp_isRobotWorkingNow=True
    #     myP.lastRobot15mWorkingDate=datetime.now() #timezone.now()
    #     myP.save()
    myPreferencesErr=Preferences.objects.all().first()
    isEmaHigherThanBTCPrice=getIsEmaHigherThanBTCPrice()
    isControlForEmaLowWarningStartDate(isEmaHigherThanBTCPrice)
    #Ema altındaysa alınmak üzere rsi değeri girilen değerleri temizle
    if myPreferencesErr.temp_emaLowWarningStartDate is not None:
        if isEmaHigherThanBTCPrice==0 and 1<hourDiff(myPreferencesErr.temp_emaLowWarningStartDate,datetime.now()):
            Coin.objects.all().update(moveRSI15mComeBackRSIValueForUsdt=0,moveRSI15mComeBackRSIValueForBtc=0,moveRSI15mWITHRealMarginComeBackRSIValueForUsdt=0,moveRSI15mWITHRealMarginComeBackRSIValueForBtc=0,moveRSI15mSlowComeBackRSIValueForUsdt=0,moveRSI15mSlowComeBackRSIValueForBtc=0,moveRSI1hComeBackRSIValueForUsdt=0,moveRSI1hComeBackRSIValueForBtc=0,moveRSIMarginBtcComeBackRSIValueForUsdt=0,moveRSIMarginLongComeBackRSIValueForUsdt=0)
    if getIsBtcLowerThan10PercentageFromEma():
        myPreferencesErr.temp_isRobotWorkingNow = False
        #Günlük EMA Kontrolüne göre yön değişikliği için gerekli satışlar yapılır.
        if myPreferencesErr.isControlEmaForSellingPreviousRobot15mTrades:
            #isSellAllWorked=True
            sellEverythingRobot15mAndBuyUsdt()
        myPreferencesErr.save()
        return ''
    else:
        myPreferencesErr.lastRobot15mWorkingDate=datetime.now()
        myPreferencesErr.save()
    global mailSubject
    global resultMail
    global boughtCoins
    global soldCoins
    global nearlyBuyCoins
    global nearlySellCoins
    global workTimeDateForRSI15m
    global boughtCoinsTotalUsdt
    global workTimeDateForSavingTotalBalanceHistory
    boughtCoinsTotalUsdt=0
    mailSent=False
    resultMail=mailSubject=boughtCoins=soldCoins=nearlyBuyCoins=nearlySellCoins=''
    myPreferences=Preferences.objects.all().first()
    maxLimitToBuy=(myPreferences.maxLimitForRobot15mAsUsdt/4)-getLast6HoursUsedActive15mTradesCost() #Bir kerede herşeyi alıp bitirmesin diye son 6 saatte en fazla limitin 4'te 1'ini kullanabilir
    if myPreferences.isRobot15mActive:
        #isEmaHigherThan4hBTCPrice=getIsEmaHigherThan4hBTCPrice()
        #isEmaHigherThanBTCPriceForFivePercPassed = getIsEmaHigherThanBTCPriceForFivePercPassed()
        #isEmaLowerThanBTC10Perc = getIsEmaLowerThanBTC10Perc()
        #print('run_robot_15m çalışıyor')
        buysignal=sellsignal=''
        #SELL
        tradeList=getTradeListForRobot15m()
        for activeTrade in tradeList:
            activeCoin=activeTrade.coin
            sellSignalForRobot15m(activeCoin.name,activeCoin.preferredCompareCoinName,activeCoin.name,'USDT',activeTrade)
        #BUY
        if getIsStillCheap() is True and (myPreferences.robot15mResultHistoryAsUsdt > myPreferences.lossLimitForRobot15m) and isEmaHigherThanBTCPrice==1 and myPreferences.stopBuyingDateFor15m is None:#and isEmaHigherThan4hBTCPrice==1
            coinList=Coin.objects.filter(openToBuy=True,isActive=True,isMargin=False,isUsableForRSI15m=True)
            for activeCoin in coinList:
                if maxLimitToBuy>boughtCoinsTotalUsdt:
                    buySignalForRobot15m(activeCoin.name,activeCoin.preferredCompareCoinName,activeCoin.name,'USDT')
        #MAIL
        resultMail = '<br>','run_robot_15m bir seferde alınabilecek max coi tutarı:',maxLimitToBuy,'alınan coin tutarı:',boughtCoinsTotalUsdt,'<b>run_robot_15m Satin alinanlar:</b><br> ',boughtCoins,' / <br><b>Satis yapilanlar:</b><br> ',soldCoins ,' / <br><b>Sinyal gelip alinamayan:</b><br>', notBoughSignalComeButNoLimit ,' / <br><b>Yaklaşanlar Alış:</b><br>', nearlyBuyCoins ,' / <br><b>Yaklaşanlar Satış:</b><br>',nearlySellCoins,'<br><br>',resultMail 
        if len(boughtCoins)>0 or len(soldCoins)>0:
            mailSubject = 'run_robot_15m Alim/Satim Bilgilendirme ',mailSubject
            resultMail = '<br>boughtCoins:',boughtCoins , '<br>soldCoins:' , soldCoins , '<br>' , resultMail
            sendMail(fixString(mailSubject),fixString(resultMail))
            mailSent=True
        elif len(nearlyBuyCoins)>0 or len(nearlySellCoins)>0:
            hours=hourDiff(workTimeDateForRSI15m,datetime.now())
            if hours>4:
                mailSubject='Alış veya Satış Sinyaline Yaklasan Var (referans 15 dakikalık RSI) ',mailSubject
                sendMail(fixString(mailSubject),fixString(resultMail))
                mailSent=True
                workTimeDateForRSI15m=datetime.now()
        processresult = "run_robot_15m islem tamamlandi: ", getStringFromDate(datetime.today()), " boughtCoins:", boughtCoins," soldCoins:",soldCoins,'   Mail Gonderildi Mi?:',mailSent
        processresult = fixString(processresult)
        print(processresult)
    else:
        print('run_robot_15m çalışmıyor')
    myPreferencesEnd2=Preferences.objects.all().first()
    myPreferencesEnd2.temp_isRobotWorkingNow = False
    if (myPreferencesEnd2.stopBuyingDateFor15m is not None) and (hourDiff(myPreferencesEnd2.stopBuyingDateFor15m,datetime.now())>myPreferencesEnd2.stopBuyingWaitingTime):
        myPreferencesEnd2.stopBuyingDateFor15m = None
    myPreferencesEnd2.save()
    hours=hourDiffNormal(workTimeDateForSavingTotalBalanceHistory,datetime.now())
    if hours>=4:
        infoFields=getInfoFields()
        newTotalBalanceHistory=TotalBalanceHistory(robotUsing=infoFields.get('usedUsdtForRobotAsUsdt'),freeUsdt=infoFields.get('myFreeUsdt'),manuelUsing=infoFields.get('usedUsdtForManuelNewAsUsdt'),totalCommonUsdt=infoFields.get('allTotalNew'),totalCommonTl=infoFields.get('allTotalTLNew'),totalRobot=infoFields.get('robotTotalNow'),totalEarn=infoFields.get('myNewTradeToEarn'),totalOtherExchanges=infoFields.get('myNewOtherExchangeUsdt'),btc=infoFields.get('btcusdt'),marginResultHistory=infoFields.get('marginResultHistoryAsUsdt'),marginBTCResultHistory=infoFields.get('marginBTCResultHistoryAsUsdt'),robot15mResultHistory=infoFields.get('robot15mResultHistoryAsUsdt'))
        newTotalBalanceHistory.save()
        workTimeDateForSavingTotalBalanceHistory=datetime.now()
    return ''

def maxLeverage(pair):
    returnValue = ""
    result = client.futures_coin_leverage_bracket()
    for x in result:
        if pair in x['symbol']:
            for bracket in x['brackets']:
                if bracket['bracket']==1:
                    returnValue = bracket["initialLeverage"]
                    #returnValue = x
    return returnValue
    # reback = maxLeverage("ADA")

def getActiveLeverage(pair):
    result = 1 
    activeMaxLeverage = maxLeverage(pair)
    if activeMaxLeverage>=10:
        result = 10 #max value 10 for now
    else :
        result = activeMaxLeverage
    return result

@app.task
def run_robot_15m_WITH_real_margin():
    myPreferencesErr=Preferences.objects.all().first()
    isEmaHigherThanBTCPrice=getIsEmaHigherThanBTCPrice()
    isControlForEmaLowWarningStartDate(isEmaHigherThanBTCPrice)
    #Ema altındaysa alınmak üzere rsi değeri girilen değerleri temizle
    if myPreferencesErr.temp_emaLowWarningStartDate is not None:
        if isEmaHigherThanBTCPrice==0 and 1<hourDiff(myPreferencesErr.temp_emaLowWarningStartDate,datetime.now()):
            Coin.objects.all().update(moveRSI15mComeBackRSIValueForUsdt=0,moveRSI15mComeBackRSIValueForBtc=0,moveRSI15mWITHRealMarginComeBackRSIValueForUsdt=0,moveRSI15mWITHRealMarginComeBackRSIValueForBtc=0,moveRSI15mSlowComeBackRSIValueForUsdt=0,moveRSI15mSlowComeBackRSIValueForBtc=0,moveRSI1hComeBackRSIValueForUsdt=0,moveRSI1hComeBackRSIValueForBtc=0,moveRSIMarginBtcComeBackRSIValueForUsdt=0,moveRSIMarginLongComeBackRSIValueForUsdt=0)
    if getIsBtcLowerThan10PercentageFromEma():
        myPreferencesErr.temp_isRobotWorkingNow = False
        #Günlük EMA Kontrolüne göre yön değişikliği için gerekli satışlar yapılır.
        if myPreferencesErr.isControlEmaForSellingPreviousRobot15mWITHRealMarginTrades:
            sellEverythingRobot15mWITHRealMarginAndBuyUsdt()
        myPreferencesErr.save()
        return ''
    else:
        myPreferencesErr.lastRobot15mWITHRealMarginWorkingDate=datetime.now()
        myPreferencesErr.save()
    global mailSubject
    global resultMail
    global boughtCoins
    global soldCoins
    global nearlyBuyCoins
    global nearlySellCoins
    global workTimeDateForRSI15mWITHRealMargin
    global boughtCoinsTotalUsdt
    global workTimeDateForSavingTotalBalanceHistory
    boughtCoinsTotalUsdt=0
    mailSent=False
    resultMail=mailSubject=boughtCoins=soldCoins=nearlyBuyCoins=nearlySellCoins=''
    myPreferences=Preferences.objects.all().first()
    maxLimitToBuy=(myPreferences.maxLimitForRobot15mWITHRealMarginAsUsdt/4)-getLast6HoursUsedActive15mWITHRealMarginTradesCost() #Bir kerede herşeyi alıp bitirmesin diye son 6 saatte en fazla limitin 4'te 1'ini kullanabilir
    if myPreferences.isRobot15mWITHRealMarginActive:
        buysignal=sellsignal=''
        #SELL
        tradeList=getTradeListForRobot15mWITHRealMargin()
        for activeTrade in tradeList:
            activeCoin=activeTrade.coin
            sellSignalForRobot15mWITHRealMargin(activeCoin.name,activeCoin.preferredCompareCoinName,activeCoin.name,'USDT',activeTrade)
        #BUY
        if getIsStillCheap() is True and (myPreferences.robot15mWITHRealMarginResultHistoryAsUsdt > myPreferences.lossLimitForRobot15mWITHRealMargin) and isEmaHigherThanBTCPrice==1 and myPreferences.stopBuyingDateFor15mWITHRealMargin is None:#and isEmaHigherThan4hBTCPrice==1
            coinList=Coin.objects.filter(openToBuy=True,isActive=True,isMargin=False,isUsableForRSI15m=True)
            for activeCoin in coinList:
                if maxLimitToBuy>boughtCoinsTotalUsdt:
                    buySignalForRobot15mWITHRealMargin(activeCoin.name,activeCoin.preferredCompareCoinName,activeCoin.name,'USDT')
        #MAIL
        resultMail = '<br>','run_robot_15m_WITHRealMargin bir seferde alınabilecek max coi tutarı:',maxLimitToBuy,'alınan coin tutarı:',boughtCoinsTotalUsdt,'<b>run_robot_15m_WITHRealMargin Satin alinanlar:</b><br> ',boughtCoins,' / <br><b>Satis yapilanlar:</b><br> ',soldCoins ,' / <br><b>Sinyal gelip alinamayan:</b><br>', notBoughSignalComeButNoLimit ,' / <br><b>Yaklaşanlar Alış:</b><br>', nearlyBuyCoins ,' / <br><b>Yaklaşanlar Satış:</b><br>',nearlySellCoins,'<br><br>',resultMail 
        if len(boughtCoins)>0 or len(soldCoins)>0:
            mailSubject = 'run_robot_15m_WITHRealMargin Alim/Satim Bilgilendirme ',mailSubject
            resultMail = '<br>boughtCoins:',boughtCoins , '<br>soldCoins:' , soldCoins , '<br>' , resultMail
            sendMail(fixString(mailSubject),fixString(resultMail))
            mailSent=True
        elif len(nearlyBuyCoins)>0 or len(nearlySellCoins)>0:
            hours=hourDiff(workTimeDateForRSI15mWITHRealMargin,datetime.now())
            if hours>4:
                mailSubject='Alış veya Satış Sinyaline Yaklasan Var (referans 15 dakikalık RSI) ',mailSubject
                sendMail(fixString(mailSubject),fixString(resultMail))
                mailSent=True
                workTimeDateForRSI15mWITHRealMargin=datetime.now()
        processresult = "run_robot_15m_WITHRealMargin islem tamamlandi: ", getStringFromDate(datetime.today()), " boughtCoins:", boughtCoins," soldCoins:",soldCoins,'   Mail Gonderildi Mi?:',mailSent
        processresult = fixString(processresult)
        print(processresult)
    else:
        print('run_robot_15m_WITHRealMargin çalışmıyor')
    myPreferencesEnd2=Preferences.objects.all().first()
    myPreferencesEnd2.temp_isRobotWorkingNow = False
    if (myPreferencesEnd2.stopBuyingDateFor15mWITHRealMargin is not None) and (hourDiff(myPreferencesEnd2.stopBuyingDateFor15mWITHRealMargin,datetime.now())>myPreferencesEnd2.stopBuyingWaitingTime):
        myPreferencesEnd2.stopBuyingDateFor15mWITHRealMargin = None
    myPreferencesEnd2.save()
    hours=hourDiffNormal(workTimeDateForSavingTotalBalanceHistory,datetime.now())
    if hours>=4:
        infoFields=getInfoFields()
        newTotalBalanceHistory=TotalBalanceHistory(robotUsing=infoFields.get('usedUsdtForRobotAsUsdt'),freeUsdt=infoFields.get('myFreeUsdt'),manuelUsing=infoFields.get('usedUsdtForManuelNewAsUsdt'),totalCommonUsdt=infoFields.get('allTotalNew'),totalCommonTl=infoFields.get('allTotalTLNew'),totalRobot=infoFields.get('robotTotalNow'),totalEarn=infoFields.get('myNewTradeToEarn'),totalOtherExchanges=infoFields.get('myNewOtherExchangeUsdt'),btc=infoFields.get('btcusdt'),marginResultHistory=infoFields.get('marginResultHistoryAsUsdt'),marginBTCResultHistory=infoFields.get('marginBTCResultHistoryAsUsdt'),robot15mResultHistory=infoFields.get('robot15mResultHistoryAsUsdt'))
        newTotalBalanceHistory.save()
        workTimeDateForSavingTotalBalanceHistory=datetime.now()
    return ''

@app.task
def run_margin_robot():
    #timet.sleep(2)#celery taskları aynı anda başladığından lock olmaması için beklettim
    # myP=Preferences.objects.all().first()
    # if myP.temp_isRobotWorkingNow:
    #     print('diğer robot çalıştığı için run_margin_robot çalıştırılmadı')
    #     #Eğer 5 dakikadır çalışmıyorsa kilit takılı kalmış demektir. Kilidi kaldır
    #     minutes=minutesDiff(myP.lastMarginRobotWorkingDate,datetime.now())
    #     if minutes>=5: 
    #         print('takıldığı saatler(son calisma/simdiki saat)',myP.lastMarginRobotWorkingDate,'  /  ',datetime.now())
    #         myP.temp_isRobotWorkingNow = False
    #         myP.save()
    #     return ''
    # else :
    #     myP.temp_isRobotWorkingNow=True
    #     myP.lastMarginRobotWorkingDate=datetime.now() #timezone.now()
    #     myP.save()
    myPreferencesErr=Preferences.objects.all().first()
    if getIsBtcLowerThan10PercentageFromEma():
        myPreferencesErr.temp_isRobotWorkingNow = False
        myPreferencesErr.save()
        return ''
    else : 
        myPreferencesErr.lastMarginRobotWorkingDate=datetime.now()
        myPreferencesErr.save()
    global mailSubject
    global resultMail
    global boughtCoins
    global soldCoins
    global nearlyBuyCoins
    global nearlySellCoins
    global workTimeDateForRSI15m
    global boughtCoinsTotalUsdt
    boughtCoinsTotalUsdt=0
    mailSent=False
    resultMail=mailSubject=boughtCoins=soldCoins=''
    myPreferences=Preferences.objects.all().first()
    if myPreferences.isMarginRobotActive:
        #btc_RSI_15m=int(getRSI('BTCUSDT','15m',5000))#Altcoin alırken btc rsi'ı 50'ın altındaysa longa izin ver, 50 üzerindeyse shorta izin ver
        maxLimitToBuy=(myPreferences.maxLimitForMarginAsUsdt/4)-getLast6HoursUsedActiveMarginTradesCost() #Bir kerede herşeyi alıp bitirmesin diye son 6 saatte en fazla limitin 4'te 1'ini kullanabilir
        #isEmaHigherThan4hBTCPrice=getIsEmaHigherThan4hBTCPrice()
        isEmaHigherThanBTCPrice=getIsEmaHigherThanBTCPrice()
        isEmaHigherThanBTCPriceForFivePercPassed = getIsEmaHigherThanBTCPriceForFivePercPassed()
        isEmaLowerThanBTC10Perc = getIsEmaLowerThanBTC10Perc()
        #print('run_margin_robot çalışıyor')
        buysignal_BTCDOWN=sellsignal_BTCDOWN=buysignal_BTCUP=sellsignal_BTCUP=''
        isSellAllWorked=False
        #Günlük EMA Kontrolüne göre yön değişikliği için gerekli satışlar yapılır.
        if myPreferences.isControlEmaForSellingPreviousMarginTrades:
            if isEmaHigherThanBTCPriceForFivePercPassed==1:#Ema yı %5 geçince eski shortları sat
                tradeList = getTradeListForMargin()
                for activeTradeBTCDown in tradeList:
                    if activeTradeBTCDown.coin.name.endswith('DOWN'):
                        sellAllForCoinAction(activeTradeBTCDown.coin.name,'USDT',activeTradeBTCDown)
                        isSellAllWorked=True
        #Başlangıç - Günlük EMA Kontrolüne göre long veya short alım kısımları çalışır
        #SELL
        tradeList = getTradeListForMargin()
        for activeTradeBTC in tradeList:
            if activeTradeBTC.coin.name.endswith('DOWN'):
                activeCoinForCompare=activeTradeBTC.coin.name.replace('DOWN', '')
                sellsignal_BTCDOWN=sellSignalForMarginShort(activeCoinForCompare,activeTradeBTC.exchangePair.name,activeTradeBTC.coin.name,'USDT',activeTradeBTC)
            elif activeTradeBTC.coin.name.endswith('UP'):
                # if activeTradeBTC.coin.name.startswith('BTC'):
                #     activeCoinForCompare=activeTradeBTC.coin.name.replace('UP', '')
                #     sellsignal_BTCUP=sellSignalForMarginLongForBtc(activeCoinForCompare,activeTradeBTC.exchangePair.name,activeTradeBTC.coin.name,'USDT',activeTradeBTC)
                # else:
                activeCoinForCompare=activeTradeBTC.coin.name.replace('UP', '')
                sellsignal_BTCUP=sellSignalForMarginLong(activeCoinForCompare,activeTradeBTC.exchangePair.name,activeTradeBTC.coin.name,'USDT',activeTradeBTC)
        #BUY
        coinList=Coin.objects.filter(openToBuy=True,isActive=True,isMargin=True).exclude(name__startswith='BTC')
        if (myPreferences.marginResultHistoryAsUsdt > myPreferences.lossLimitForRobotMargin)  and myPreferences.stopBuyingDateForMargin is None : 
            if isEmaHigherThanBTCPrice==0 and myPreferences.isMarginRobotShortActive == True:# isEmaHigherThan4hBTCPrice==0 # Ema altında açık ise short al
                for activeCoin in coinList:
                    if maxLimitToBuy>boughtCoinsTotalUsdt:
                        if isEmaLowerThanBTC10Perc!=1:
                            #btc ema dan %5 altınında üzerindeyse her türlü alım yap                    
                            if activeCoin.name.endswith('DOWN'):
                                activeCoinForCompare=activeCoin.name.replace('DOWN', '')
                                buysignal_BTCDOWN=buySignalForMarginShort(activeCoinForCompare,activeCoin.preferredCompareCoinName,activeCoin.name,'USDT')
            elif getIsStillCheap() is True and isEmaHigherThanBTCPrice==1 and  myPreferences.isMarginRobotLongActive == True: # and isEmaHigherThan4hBTCPrice==1 # Ema üzerinde açık ise long al
                for activeCoin in coinList:
                    if maxLimitToBuy>boughtCoinsTotalUsdt:
                        if activeCoin.name.endswith('UP'):
                            activeCoinForCompare=activeCoin.name.replace('UP', '')
                            buysignal_BTCUP=buySignalForMarginLong(activeCoinForCompare,activeCoin.preferredCompareCoinName,activeCoin.name,'USDT')
        #MAIL
        if len(boughtCoins)>0 or len(soldCoins)>0:
            mailSubject = 'Margin Alim/Satim Bilgilendirme ',mailSubject
            resultMail = '<br>Margin boughtCoins:',boughtCoins , '<br>soldCoins:' , soldCoins , '<br>' , resultMail
            sendMail(fixString(mailSubject),fixString(resultMail))
            mailSent=True
        processresult = "run_margin_robot islem tamamlandi: ", getStringFromDate(datetime.today()),"boughtCoins:", boughtCoins," soldCoins:",soldCoins, "isSellAllWorked:",isSellAllWorked, '   Mail Gonderildi Mi?:',mailSent
        processresult = fixString(processresult)
        print(processresult)
    else:
        print('run_margin_robot çalışmıyor')
    myPreferencesEnd2=Preferences.objects.all().first()
    myPreferencesEnd2.temp_isRobotWorkingNow = False
    if (myPreferencesEnd2.stopBuyingDateForMargin is not None) and (hourDiffNormal(myPreferencesEnd2.stopBuyingDateForMargin,datetime.now())>myPreferencesEnd2.stopBuyingWaitingTime):
        myPreferencesEnd2.stopBuyingDateForMargin = None
    myPreferencesEnd2.save()
    return ''

@app.task
def run_margin_BTC_robot():
    # timet.sleep(4)#celery taskları aynı anda başladığından lock olmaması için beklettim
    # myP=Preferences.objects.all().first()
    # if myP.temp_isRobotWorkingNow:
    #     print('diğer robot çalıştığı için run_margin_BTC_robot çalıştırılmadı')
    #     return ''
    # else :
    #     myP.temp_isRobotWorkingNow=True
    #     myP.lastMarginBTCRobotWorkingDate=datetime.now() #timezone.now()
    #     myP.save()
    global mailSubject
    global resultMail
    global boughtCoins
    global soldCoins
    global nearlyBuyCoins
    global nearlySellCoins
    global workTimeDateForRSI15m
    global boughtCoinsTotalUsdt
    boughtCoinsTotalUsdt=0
    mailSent=False
    resultMail=mailSubject=boughtCoins=soldCoins=''
    myPreferencesErr=Preferences.objects.all().first()
    myPreferencesErr.lastMarginBTCRobotWorkingDate=datetime.now()
    myPreferencesErr.save()
    myPreferences=Preferences.objects.all().first()
    if myPreferences.isMarginBTCRobotActive:
        buysignal_BTCDOWN=sellsignal_BTCDOWN=buysignal_BTCUP=sellsignal_BTCUP=''
        isSellAllWorked=False
        #Başlangıç - Günlük EMA Kontrolüne göre long veya short alım kısımları çalışır
        #SELL
        tradeList = getTradeListForMarginBTC()
        for activeTradeBTC in tradeList:
            activeCoinForCompare=activeTradeBTC.coin.name.replace('UP', '')
            sellsignal_BTCUP=sellSignalForMarginLongForBtc(activeCoinForCompare,activeTradeBTC.exchangePair.name,activeTradeBTC.coin.name,'USDT',activeTradeBTC)
        #BUY
        if (myPreferences.marginBTCResultHistoryAsUsdt > myPreferences.lossLimitForRobotMarginBTC)  and myPreferences.stopBuyingDateForMarginBTC is None : 
            if myPreferences.isMarginBTCRobotLongActive == True:
                activeCoin = Coin.objects.get(name='BTCUP')
                activeCoinForCompare=activeCoin.name.replace('UP', '')
                buysignal_BTCUP=buySignalForMarginLongForBtc(activeCoinForCompare,activeCoin.preferredCompareCoinName,activeCoin.name,'USDT')
        #MAIL
        if len(boughtCoins)>0 or len(soldCoins)>0:
            mailSubject = 'MarginBTC Alim/Satim Bilgilendirme ',mailSubject
            resultMail = '<br>MarginBTC boughtCoins:',boughtCoins , '<br>soldCoins:' , soldCoins , '<br>' , resultMail
            sendMail(fixString(mailSubject),fixString(resultMail))
            mailSent=True
        processresult = "run_margin_BTC_robot islem tamamlandi: ", getStringFromDate(datetime.today()),"boughtCoins:", boughtCoins," soldCoins:",soldCoins, "isSellAllWorked:",isSellAllWorked, '   Mail Gonderildi Mi?:',mailSent
        processresult = fixString(processresult)
        print(processresult)
    else:
        print('run_margin_BTC_robot çalışmıyor')
    myPreferencesEnd2=Preferences.objects.all().first()
    myPreferencesEnd2.temp_isRobotWorkingNow = False
    if (myPreferencesEnd2.stopBuyingDateForMarginBTC is not None) and (hourDiffNormal(myPreferencesEnd2.stopBuyingDateForMarginBTC,datetime.now())>myPreferencesEnd2.stopBuyingWaitingTimeMarginBTC):
        myPreferencesEnd2.stopBuyingDateForMarginBTC = None
    myPreferencesEnd2.save()
    return ''

@app.task
def run_robots_fast_group():
    myP=Preferences.objects.all().first()
    if myP.temp_isRobotWorkingNow:
        print('diğer robot çalıştığı için run_margin_robot çalıştırılmadı')
        #Eğer 5 dakikadır çalışmıyorsa kilit takılı kalmış demektir. Kilidi kaldır
        minutes=minutesDiff(myP.lastMarginRobotWorkingDate,datetime.now())
        if minutes>=5: 
            print('takıldığı saatler(son calisma/simdiki saat)',myP.lastMarginRobotWorkingDate,'  /  ',datetime.now())
            myP.temp_isRobotWorkingNow = False
            myP.save()
        return ''
    else :
        myP.temp_isRobotWorkingNow=True
        myP.lastMarginRobotWorkingDate=datetime.now() #timezone.now()
        myP.save()
    #run_robot_15m_WITH_real_margin()
    run_robot_15m()
    run_margin_robot()
    run_margin_BTC_robot()

@app.task
def run_robots_slow_group():
    timet.sleep(2)
    myP=Preferences.objects.all().first()
    if myP.temp_isRobotWorkingNow:
        print('diğer robot çalıştığı için run_robots_slow_group çalıştırılmadı')
        return ''
    run_robot_1h()
    run_robot_15m_slow()