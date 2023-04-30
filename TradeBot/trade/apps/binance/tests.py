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








#MARGIN BUY
buyOrSell='BUY'
mySideEffectType="MARGIN_BUY"
buyingStrategy='RSI_15m_WITHRealMargin'
firstCoinNameForBuyOrSellParameter='COMP'
secondCoinNameForBuyOrSellParameter='USDT'
mySymbol=firstCoinNameForBuyOrSellParameter+secondCoinNameForBuyOrSellParameter
activePrice=getActivePrice(firstCoinNameForBuyOrSellParameter,secondCoinNameForBuyOrSellParameter)
usdtAmount=20
quantity=usdtAmount/activePrice
exhangeQuantity='{:0.0{}f}'.format(quantity, 6)
exchangeQuantity='{:0.0{}f}'.format(quantity, 6)

transferFromSpotToMargin = client.transfer_spot_to_margin(asset=secondCoinNameForBuyOrSellParameter,amount=usdtAmount) #spottan cross a usdt transfer et #1
maxBorrowAmount = client.get_max_margin_loan(asset=firstCoinNameForBuyOrSellParameter)["amount"] #2 kullanılabilecek max krediyi tespit et
maxBorrowAmount = '{:0.0{}f}'.format(maxBorrowAmount, 6)
marginLoanProcess = client.create_margin_loan(asset=firstCoinNameForBuyOrSellParameter, amount=maxBorrowAmount) #3 krediyi çek
#exhangeQuantity=exhangeQuantity[0:-2]
process = client.create_margin_order(symbol=mySymbol,side=buyOrSell,type='MARKET',quantity=exhangeQuantity,sideEffectType=mySideEffectType) #satın al


#MARGIN SELL
buyOrSell='SELL'
mySideEffectType="AUTO_REPAY"
repayAmount = client.get_margin_loan_details(asset=firstCoinNameForBuyOrSellParameter)['rows'][0]['principal'] #TODO Eskisi geliyor
repayResult = client.repay_margin_loan(asset=firstCoinNameForBuyOrSellParameter, amount=repayAmount) #KREDİYİ ÖDE
remainingCoinAmount = client.get_max_margin_transfer(asset=firstCoinNameForBuyOrSellParameter)["amount"]
remainingCoinAmount = '{:0.0{}f}'.format(float(remainingCoinAmount), 6)
#remainingCoinAmount=remainingCoinAmount[0:-2]
process = client.create_margin_order(symbol=mySymbol,side=buyOrSell,type='MARKET',quantity=remainingCoinAmount,sideEffectType=mySideEffectType) #satın al
transferFromMarginToSpotCount = float(client.get_max_margin_transfer(asset=secondCoinNameForBuyOrSellParameter)['amount']) #aktarılacak usdt miktarı tespit et
transferFromMarginToSpotProcess = client.transfer_margin_to_spot(asset=secondCoinNameForBuyOrSellParameter, amount=transferFromMarginToSpotCount) #miktarı cross dan spot a transfer et


#currentAmountPrepareToSell = float(client.get_max_margin_transfer(asset=firstCoinNameForBuyOrSellParameter)['amount'])
#client.get_margin_loan_details(asset=firstCoinNameForBuyOrSellParameter)
#client.get_all_margin_orders(symbol=mySymbol)[0]
