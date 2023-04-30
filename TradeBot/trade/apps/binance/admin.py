from django.contrib import admin
from .models import Coin,Trade,Preferences,TotalBalanceHistory,ProcessLog,TradeLog

#Sadece bu şekilde de yazılabilir ama o zaman sadece bir kolon görünür
#admin.site.register(Trade)

class CoinAdmin(admin.ModelAdmin):
    list_display = ('id','name', 'preferredCompareCoinName', 'last15RSIUSDT', 'last15RSIBTC','isUsableForRSI15m','isUsableForRSI1h', 'openToBuy', 'trustRate','creation_date','isActive','isBuyAutomaticallyAfterPanicMode','isMargin','isUsableForRSI15m','isUsableForRSI1h','moveRSI15mComeBackRSIValueForUsdt','moveRSI15mComeBackRSIValueForBtc','moveRSI15mWITHRealMarginComeBackRSIValueForUsdt','moveRSI15mWITHRealMarginComeBackRSIValueForBtc','moveRSI15mSlowComeBackRSIValueForUsdt','moveRSI15mSlowComeBackRSIValueForBtc','moveRSI1hComeBackRSIValueForUsdt','moveRSI1hComeBackRSIValueForBtc','moveRSIMarginBtcComeBackRSIValueForUsdt','moveRSIMarginLongComeBackRSIValueForUsdt')
admin.site.register(Coin, CoinAdmin)

class TradeAdmin(admin.ModelAdmin):
    list_display = ('id','coin', 'exchangePair','firstCount', 'count','price','firstPriceAgainstBtc','isPassiveInEarn','buyedByRobot','howManyTimesSold','transactionDate','lastSellDate','getFirstBuyTotalPrice','getTotalPrice','isDifferentExchange','differentExchangeName','isMargin','strategy')
admin.site.register(Trade, TradeAdmin)

class PreferencesAdmin(admin.ModelAdmin):
    list_display = ('id','maxLimitForRobotAsUsdt','maxLimitForMarginAsUsdt','maxLimitForRobot15mAsUsdt', 'maxOpenTradeCountForSameCoin', 'isEmaControlActiveForBuying','isBuyingModeActive','isSellingModeActive','isFlexWhileBuying','coinTargetToCollect','isSellingOneStepIfDoesntPassEMAControlModeActive','isControlForPanicMode','isPanicModeActive','isExistFromPanicModeAutomaticallyActive','isBuyAutomaticallyAfterPanicMode','cooldownForNewBuyFromSameCoin','cooldownForNewSellFromSameCoin','targetPercentageForBuying','targetPercentageForSelling','minRSI','midRSI','maxRSI','williamR','commonTotalStartMoneyAsUSDT','commonTotalStartMoneyAsTL','addBudgetToRobotWhenTargetToTopComes_BtcTargetArea','addBudgetToRobotWhenTargetToTopComes_AddBudget')
admin.site.register(Preferences, PreferencesAdmin)

class TotalBalanceHistoryAdmin(admin.ModelAdmin):
    list_display = ('id','robotResultHistory','robot15mResultHistory','marginResultHistory','robotUsing', 'freeUsdt','manuelUsing', 'transactionDate', 'totalCommonUsdt','totalCommonTl','totalRobot','totalEarn','totalOtherExchanges','btc','marginResultHistory')
admin.site.register(TotalBalanceHistory, TotalBalanceHistoryAdmin)

class ProcessLogAdmin(admin.ModelAdmin):
    list_display = ('id','processResult', 'processDate', 'processSubject')
admin.site.register(ProcessLog, ProcessLogAdmin)

class TradeLogAdmin(admin.ModelAdmin):
    list_display = ('id','processType','coinName', 'exchangeCoinName','count','price','getTotalPrice','gainUsdt','profitLossPercentage','buyedByRobot','transactionDate')
admin.site.register(TradeLog, TradeLogAdmin)

