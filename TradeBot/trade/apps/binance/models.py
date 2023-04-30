from django.db import models
from django.template.defaultfilters import slugify
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.shortcuts import reverse
from unidecode import unidecode
from django.template.defaultfilters import slugify
from ckeditor.fields import RichTextField
from django.contrib.auth import login,logout,authenticate
from django.db.models import Sum
from datetime import datetime, time
#import dateutil, datetime, pytz

MinimumBuyPrice_USDT = 6
MinimumBuyPrice_BTC = 0.0002 #20dolara denk geliyor

class Coin(models.Model):
    name = models.TextField(max_length=100, blank=False, null=True, verbose_name='Coin adı',help_text='Coin adı burada girilir.')  # CharField
    preferredCompareCoinName = models.TextField(max_length=100, blank=False, null=False, default='BTC', verbose_name='Karşılaştırılacak coin adı',help_text='Karşılaştırılacak coin adı borsada karşılığı olduğu sürece btc girilmesi tavsiye edilir.')  # CharField
    last15RSIUSDT = models.IntegerField(default=0, verbose_name='Son 15m rsi değeri USDT',help_text='Son 15m rsi değeri USDT')
    last15RSIBTC = models.IntegerField(default=0, verbose_name='Son 15m rsi değeri BTC',help_text='Son 15m rsi değeri BTC')
    trustRate = models.IntegerField(default=3) #en dandiklerine 3 verilir ve kalitesine göre arttırılır.
    openToBuy = models.BooleanField(null=False, default=True, verbose_name='Alıma açık mı?',help_text='Alıma açık olup olmamasına burada karar verilir.')
    creation_date = models.DateField(auto_now_add=True, auto_now=False)
    isActive = models.BooleanField(null=False, default=True, verbose_name='Aktif mi?',help_text='Aktif mi ?')
    isBuyAutomaticallyAfterPanicMode = models.BooleanField(null=False, default=False, verbose_name='Panik modundan çıkışta otomatik al',help_text='Panik modundan otomatik çıkış açıkken panik modundan çıkış aşamasında bu alanı kontrol eder ve işaretli ise otomatik olarak birer kademe alır.')
    isMargin = models.BooleanField(null=False, default=False, verbose_name='Kardıraçlı coin mi?')
    isUsableForRSI15m = models.BooleanField(null=False, default=False,verbose_name='RSI15 için uygun', help_text='RSI15 için uygun coin mi?')
    isUsableForRSI1h = models.BooleanField(null=False, default=False, verbose_name='RSI1h için uygun', help_text='RSI1h mantığıyla daha yavaş al/sat hedefleyen algoritma için uygun coin mi?')
    moveRSI15mComeBackRSIValueForUsdt = models.IntegerField(default=0, verbose_name='Kontrol RSI15mUSDT', help_text='RSI15m için RSI ın usdt karşısındaki değeri düştükten sonra x değer kadar yükseldiğinde satın alma siyali gelir.') 
    moveRSI15mComeBackRSIValueForBtc = models.IntegerField(default=0,verbose_name='Kontrol RSI15mBTC', help_text='RSI15m için RSI ın btc karşısındaki değeri düştükten sonra x değer kadar yükseldiğinde satın alma siyali gelir.') 
    moveRSI15mWITHRealMarginComeBackRSIValueForUsdt = models.IntegerField(default=0, verbose_name='Kontrol RSI15mUSDT WITHRealMargin', help_text='RSI15m WITHRealMargin için RSI ın usdt karşısındaki değeri düştükten sonra x değer kadar yükseldiğinde satın alma siyali gelir.') 
    moveRSI15mWITHRealMarginComeBackRSIValueForBtc = models.IntegerField(default=0,verbose_name='Kontrol RSI15mBTC WITHRealMargin', help_text='RSI15m WITHRealMargin için RSI ın btc karşısındaki değeri düştükten sonra x değer kadar yükseldiğinde satın alma siyali gelir.') 
    moveRSI15mSlowComeBackRSIValueForUsdt = models.IntegerField(default=0,verbose_name='Kontrol RSI15mSlowUSDT', help_text='RSI15mSlow için RSI ın usdt karşısındaki değeri düştükten sonra x değer kadar yükseldiğinde satın alma siyali gelir.') 
    moveRSI15mSlowComeBackRSIValueForBtc = models.IntegerField(default=0,verbose_name='Kontrol RSI15mSlowBTC', help_text='RSI15mSlow için RSI ın btc karşısındaki değeri düştükten sonra x değer kadar yükseldiğinde satın alma siyali gelir.') 
    moveRSI1hComeBackRSIValueForUsdt = models.IntegerField(default=0,verbose_name='Kontrol RSI1hUSDT', help_text='RSI1h için RSI ın usdt karşısındaki değeri düştükten sonra x değer kadar yükseldiğinde satın alma siyali gelir.') 
    moveRSI1hComeBackRSIValueForBtc = models.IntegerField(default=0,verbose_name='Kontrol RSI1hBTC', help_text='RSI1h için RSI ın btc karşısındaki değeri düştükten sonra x değer kadar yükseldiğinde satın alma siyali gelir.') 
    moveRSIMarginBtcComeBackRSIValueForUsdt = models.IntegerField(default=0,verbose_name='Kontrol RSIMarginBTC', help_text='RSIMarginBtc için RSI ın usdt karşısındaki değeri düştükten sonra x değer kadar yükseldiğinde satın alma siyali gelir.') 
    moveRSIMarginLongComeBackRSIValueForUsdt = models.IntegerField(default=0,verbose_name='Kontrol RSIMarginLongUSDT', help_text='RSIMarginLong için RSI ın usdt karşısındaki değeri düştükten sonra x değer kadar yükseldiğinde satın alma siyali gelir.') 

    def __str__(self):
        #return "%s , %s , %s , %s , %s" % (self.name, self.trustRate, self.openToBuy, self.creation_date, self.isActive)
        return "%s" % (self.name)

    def getBuyPriceAsUSDT(self):
        return self.trustRate * MinimumBuyPrice_USDT

    def getBuyPriceAsUSDTForRobot15m(self):
        return 150
        #return 30
        #trustRateFor15m = self.trustRate/2
        #if trustRateFor15m<2:
        #    trustRateFor15m=2
        #return trustRateFor15m * MinimumBuyPrice_USDT

    def getBuyPriceAsUSDTForRobot15mWITHRealMargin(self):
        return 50

    def getBuyPriceAsUSDTForRobot15mSlow(self):
        return 200

    def getBuyPriceAsUSDTForRobot1h(self):
        return 200
        #return 30
        #trustRateFor15m = self.trustRate/2
        #if trustRateFor15m<2:
        #    trustRateFor15m=2
        #return trustRateFor15m * MinimumBuyPrice_USDT    

    def getBuyPriceAsUSDTForRobotMarginBTC(self):
        return 300

    def getBuyPriceAsBTC(self):
        return self.trustRate * MinimumBuyPrice_BTC

    def getIsOpenToBuy(self):
        if self.openToBuy:
            return True
        else :
            return False

class Trade(models.Model):
    coin = models.ForeignKey(Coin, null=True, on_delete=models.PROTECT, related_name='trade_coin', verbose_name='Coin adı',help_text='Coin adı burada girilir.') #SOL
    exchangePair = models.ForeignKey(Coin, null=True, on_delete=models.PROTECT, related_name='trade_exchangePair', verbose_name='Fiyat çifti',help_text='Fiyat çifti tercihen Usdt girilir.') #BTC , USDT
    firstCount = models.FloatField(default=0, verbose_name='Ilk alınan adet', help_text='Ilk alınan adet (Satışlardan önce). Satışlardan sonra güncellenmez.') 
    count = models.FloatField(default=0,verbose_name='Elde kalan mevcut adet', help_text='Elde kalan mevcut adet . Satışlardan sonra güncellenir.')
    price = models.FloatField(default=0,verbose_name='Alış fiyatı Usdt',help_text='Alış fiyatı Usdt olarak') #
    firstPriceAgainstBtc = models.FloatField(default=0,verbose_name='Alış fiyatı Btc',help_text='Alış fiyat Btc karşılığı olarak')
    buyedByRobot = models.BooleanField(null=False, default=True, verbose_name='Robot mu aldı?',help_text='Robot tarafından mı alındı?')
    howManyTimesSold = models.IntegerField(default=0,verbose_name='Satılma sayısı',help_text='Kaç defa satıldı?')
    transactionDate = models.DateTimeField(default=datetime.now, blank=True,verbose_name='Alış Tarihi',help_text='Alımın yapıldığı tarih otomatik olarak alım yapıldığında girilir')
    lastSellDate = models.DateTimeField(null=True, blank=True,verbose_name='Son satış tarihi',help_text='Satış yapıldığında tarih girilir')
    isPassiveInEarn =  models.BooleanField(null=False, default=False, verbose_name='Kazan bölümünde mi?',help_text='Kazan bölümünde mi ? (Eğer öyle ise satış yapılmaz sadece görüntülenir.)')
    isDifferentExchange = models.BooleanField(null=False, default=False, verbose_name='Farklı Borsada Mı?',help_text='Farklı Borsada Mı (Borsada bulunan tutar USDT olarak girilir)?')
    differentExchangeName = models.TextField(max_length=1000, default='Binance', blank=False, null=True, verbose_name='Farklı Borsanın Adı' ,help_text='Varsayılan olarak Binance girilir fakat farklı borsada ise o borsanın adı girilir')
    indicatorResults = models.TextField(max_length=1000, default='', blank=True, null=True, verbose_name='Son çalıştığındaki indicatorlerin durumları' ,help_text='Son çalıştığında alınan indicatorlerin güncel durumları tutulur.(Alım modu açık ise her çalışmada güncellenir.)')
    isMargin = models.BooleanField(null=False, default=False, verbose_name='Kaldıraçlı mı alındı?',help_text='Kaldıraçlı mı alındı?')
    strategy = models.TextField(max_length=100, default='', blank=True, null=True, verbose_name='Alış ve Satış Stratejisi',help_text='Örnek : Margin_RSI_15m , RSI_15m , RSI_4h , Specified_Priority_Purchases , Manuel_Webpage_Action , Manuel_Entered')
    stopLossLastTriggeredPercentage = models.FloatField(default=0,verbose_name='StopLoss tetiklenme yüzdesi',help_text='StopLoss tetiklendikten sonraki en yüksek kar seviyesi yüzdesi')
    temp_currentPrice = models.FloatField(default=0,verbose_name='Şimdiki Fiyatı Usdt',help_text='Şimdiki Fiyatı Usdt - Veritabanına yazılmaz anlık olarak çekilir') 
    temp_totalCurrentPrice = models.FloatField(default=0,verbose_name='Mevcut toplam fiyatı',help_text='Mevcut toplam fiyatı - Veritabanına yazılmaz, gerektiğinde anlık olarak getActivePrice*count şeklinde kullanılır ')
    temp_profitLossPercentage = models.FloatField(default=0,verbose_name='Mevcut yüzdelik kar/zarar USDT',help_text='Mevcut yüzdelik kar/zarar USDT - Veritabanına yazılmaz anlık olarak çekilir') 
    temp_differenceToBTCPercentage = models.FloatField(default=0,verbose_name='Mevcut yüzdelik kar/zarar BTC',help_text='Mevcut yüzdelik kar/zarar BTC - Veritabanına yazılmaz anlık olarak çekilir') 
    temp_profitLossTimes = models.FloatField(default=0,verbose_name='Mevcut kaç katı kar/zarar',help_text='Mevcut kaç katı kar/zarar - Veritabanına yazılmaz anlık olarak çekilir') 
    temp_differenceTotalAsUSDT = models.FloatField(default=0,verbose_name='Kar/Zarar farkı USDT',help_text='Kar/Zarar farkının usdt olarak tutulduğu alan - Veritabanına yazılmaz anlık olarak çekilir') 
    temp_ratioToTotalPercentage = models.FloatField(default=0,verbose_name='Toplam mal varlığına oranı',help_text='Toplam mal varlığındaki kapladığı yüzdelik yer - Veritabanına yazılmaz anlık olarak çekilir') 
    
    def __str__(self):
        return "%s" % (self.coin)

    def getDetails(self):
        return "Coin adı : %s , Fiyat çifti : %s , Ilk alınan adet : %s , Elde kalan mevcut adet : %s ,Alış fiyatı Usdt : %s, Alış fiyatı Btc : %s , Robot mu aldı? : %s , Satılma sayısı : %s , Alış Tarihi : %s , Son satış tarihi : %s , Kazan bölümünde mi? : %s , Farklı Borsada Mı? : %s , Farklı Borsanın Adı : %s , Son çalıştığındaki indicatorlerin durumları : %s " % (self.coin, self.exchangePair, self.firstCount, self.count, self.price, self.firstPriceAgainstBtc, self.buyedByRobot, self.howManyTimesSold,self.transactionDate,self.lastSellDate,self.isPassiveInEarn,self.isDifferentExchange,self.differentExchangeName,self.indicatorResults)

    def getFirstBuyTotalPrice(self): # Ilk alımdaki toplam maliyet
        return self.firstCount * self.price
    
    def getTotalPrice(self):
        return self.count * self.price

    def getMinimumBuyPrice_USDT():
        return MinimumBuyPrice_USDT

    def getMinimumBuyPrice_BTC():
        return MinimumBuyPrice_BTC

    def getDatePassed(self):
        return abs((datetime.now() - self.transactionDate.replace(tzinfo=None)).days)    

    def getHourPassed(self):
        activeDateDiff = self.getDatePassed()
        activeHourDiff = abs((datetime.now().replace(tzinfo=None) - self.transactionDate.replace(tzinfo=None)).seconds)/(60*60)
        result = (activeHourDiff + (activeDateDiff*24)) -3 #3 saat fark olduğundan dolayı sonunda çıkarttım
        if result<0:
            result=0
        return result

    def getSellPercentage(self):
        result = 0
        if self.buyedByRobot : #robot ile alındıysa ilk 2 satışta yarısını, 3. satışta geri kalanını satıyor
            if self.howManyTimesSold==2 : 
                result = 100 
            else : 
                result = 50
        else : #manuel alımda ilk satışta yarısını, diğer satışlarda %10'unu satıyor
            if self.howManyTimesSold==0 : 
                result = 50
            else :
                result = 10    
        return result

class TotalBalanceHistory(models.Model):
    robotUsing = models.FloatField(default=0,verbose_name='Robot kullanıyor', help_text='Robotun aktif olarak kullandığı toplam tutar') 
    freeUsdt = models.FloatField(default=0,verbose_name='Bekleyen Usdt',help_text='Boşta bekleten Usdt (Spot taki Free duran usdt miktarından bulunur. Robotun mevcut toplam parası hesaplanırken burası ile robotun kullanıdığı toplanır. ') 
    manuelUsing = models.FloatField(default=0,verbose_name='Manuel Alınanlar Son Hali',help_text='Manuel Alınanlar Son Halinin toplam Usdt değeri') 
    transactionDate = models.DateTimeField(default=datetime.now, blank=True,verbose_name='İşlem tarihi',help_text='İşlemin kayıt tarihi')
    totalCommonUsdt = models.FloatField(default=0,verbose_name='Genel Durum USDT - Oto. Anlık Toplam', help_text='Genel Durum USDT - Oto. Anlık Toplam') 
    totalCommonTl = models.FloatField(default=0,verbose_name='Genel Durum TL - Oto. Anlık Toplam TL:', help_text='Genel Durum TL - Oto. Anlık Toplam TL:') 
    totalRobot = models.FloatField(default=0,verbose_name='Robot Son durum', help_text='Robot Son durum') 
    totalEarn = models.FloatField(default=0,verbose_name='Kazan -Yeni toplam', help_text='Kazan -Yeni toplam') 
    totalOtherExchanges = models.FloatField(default=0,verbose_name='Diğer - Diğer Borsalar Son Hali', help_text='Diğer - Diğer Borsalar Son Hali') 
    btc = models.FloatField(default=0,verbose_name='Btc', help_text='Btc son durum') 
    robotResultHistory = models.FloatField(default=0,verbose_name='Robot Trade Kar/Zarar', help_text='Robot tradelerin toplamdaki kar zarar olarak son durum') 
    marginResultHistory = models.FloatField(default=0,verbose_name='Margin Trade Kar/Zarar', help_text='Margin tradelerin toplamdaki kar zarar olarak son durum') 
    marginBTCResultHistory = models.FloatField(default=0,verbose_name='MarginBTC Trade Kar/Zarar', help_text='MarginBTC tradelerin toplamdaki kar zarar olarak son durum') 
    robot15mResultHistory = models.FloatField(default=0,verbose_name='Robot Trade Kar/Zarar', help_text='Robot RSI_15m tradelerin toplamdaki kar zarar olarak son durum') 
    
    def __str__(self):
        return "%s" % (self.robotUsing)

    def getDetails(self):
        return "Robot kullanıyor : %s , Robot bekleyen Usdt Bütçesi : %s , Manuel kullanılan Usdt : %s , İşlem tarihi : %s , Robot Toplam Bütçesi : %s , Robot ve Manuel Alımların toplamı : %s " % (self.robotUsing, self.freeUsdt, self.manuelUsing , self.transactionDate,self.getRobotTotal(),self.getCommonTotal())

class Preferences(models.Model):
    maxLimitForRobotAsUsdt = models.FloatField(default=0,verbose_name='Robot bütçe',help_text='Robotun kullanacağı maksimum usdt tutarı') 
    maxLimitForMarginAsUsdt = models.FloatField(default=50,verbose_name='Margin Bütçe',help_text='Margin Long robotun kullanacağı maksimum usdt tutarı') 
    maxLimitForMarginBTCAsUsdt = models.FloatField(default=100,verbose_name='Margin Bütçe',help_text='MarginBTC robotun kullanacağı maksimum usdt tutarı') 
    maxLimitForRobot15mAsUsdt = models.FloatField(default=0,verbose_name='Robot RSI_15m bütçe',help_text='RSI_15m Robotun kullanacağı maksimum usdt tutarı') 
    maxLimitForRobot15mWITHRealMarginAsUsdt = models.FloatField(default=200,verbose_name='Robot RSI_15m_WITHRealMargin bütçe',help_text='RSI_15m_WITHRealMargin Robotun kullanacağı maksimum usdt tutarı') 
    maxLimitForRobot15mSlowAsUsdt = models.FloatField(default=400,verbose_name='Robot RSI_15m_Slow bütçe',help_text='RSI_15m_Slow Robotun kullanacağı maksimum usdt tutarı') 
    maxLimitForRobot1hAsUsdt = models.FloatField(default=400,verbose_name='Robot RSI_1h bütçe',help_text='RSI_1h Robotun kullanacağı maksimum usdt tutarı') 
    robotResultHistoryAsUsdt = models.FloatField(default=0,verbose_name='Robot RSI_4h geçmişten bu yana alım satımlardan yapılan kar zarar durumu',help_text='Robot RSI_4h geçmişten bu yana alım satımlardan yapılan kar zarar durumu') 
    marginResultHistoryAsUsdt = models.FloatField(default=0,verbose_name='Margin geçmişten bu yana alım satımlardan yapılan kar zarar durumu',help_text='Margin geçmişten bu yana alım satımlardan yapılan kar zarar durumu') 
    marginBTCResultHistoryAsUsdt = models.FloatField(default=0,verbose_name='MarginBTC geçmişten bu yana alım satımlardan yapılan kar zarar durumu',help_text='MarginBTC geçmişten bu yana alım satımlardan yapılan kar zarar durumu') 
    robot15mResultHistoryAsUsdt = models.FloatField(default=0,verbose_name='Robot RSI_15m geçmişten bu yana alım satımlardan yapılan kar zarar durumu',help_text='Robot RSI_15m geçmişten bu yana alım satımlardan yapılan kar zarar durumu')
    robot15mWITHRealMarginResultHistoryAsUsdt = models.FloatField(default=0,verbose_name='Robot RSI_15m geçmişten bu yana alım satımlardan yapılan kar zarar durumu',help_text='Robot RSI_15m geçmişten bu yana alım satımlardan yapılan kar zarar durumu')
    robot15mSlowResultHistoryAsUsdt = models.FloatField(default=0,verbose_name='Robot RSI_15mSlow geçmişten bu yana alım satımlardan yapılan kar zarar durumu',help_text='Robot RSI_15mSlow geçmişten bu yana alım satımlardan yapılan kar zarar durumu')
    robot1hResultHistoryAsUsdt = models.FloatField(default=0,verbose_name='Robot RSI_1h geçmişten bu yana alım satımlardan yapılan kar zarar durumu',help_text='Robot RSI_1h geçmişten bu yana alım satımlardan yapılan kar zarar durumu')
    maxOpenTradeCountForSameCoin = models.IntegerField(default=2,verbose_name='Aynı coin adet limiti',help_text='Aynı coinden en fazla kaç adet açık trade bulundurabilir ?' )
    isEmaControlActiveForBuying = models.BooleanField(null=False, default=True, verbose_name='Ema kontrolü açık mı? (Alım yaparken)',help_text='Alım yaparken Ema kontrolü aktif mi ?(Varsayılan olarak BTC nin 20 günlük ortalama üzerinde olması şartı aranır)')
    isBuyingModeActive =  models.BooleanField(null=False, default=True, verbose_name='Alış modu açık mı? ',help_text='Fırsat bulduğunda coin alışı yapsın mı?')
    isSellingModeActive =  models.BooleanField(null=False, default=True, verbose_name='Satış modu açık mı? ',help_text='Fırsat bulduğunda coin satışı yapsın mı?')
    isFlexWhileBuying = models.BooleanField(null=False, default=True, verbose_name='Satış yaparken esnesin mi?(Alım esnemesi iptal edildi)',help_text='Robot kullanılan : <25 => minRSI:+10 || <50 => minRSI:+6 & maxRSI+5 || <65 => minRSI:+4 || <75 => minRSI:+2 || >90 => minRSI:-2 , >95 => minRSI:-5 || >70 => maxRSI-5 || >85 => maxRSI-10 || minRSI normal değer : 65 ile 90 arası ve maxRSI normal değer : 50 ile 70 arası')
    coinTargetToCollect = models.ForeignKey(Coin, null=True, on_delete=models.PROTECT, related_name='preferences_coinTargetToCollect', verbose_name='Biriktirilecek para birimi',help_text='Biriktirilmesi istenen para birimini seçiniz.') #BTC , USDT
    isSellingOneStepIfDoesntPassEMAControlModeActive =  models.BooleanField(null=False, default=True, verbose_name='EMA kontrolünden geçmediyse artıda olan tradelerin yarısını satsın mı?',help_text='Varsayılan olarak BTC nin 20 günlük ortalamanın altında kalması durumunda satış yapar')
    isControlForPanicMode = models.BooleanField(null=False, default=True, verbose_name='Panik moduna otomatik giriş kontrolü açık mı?',help_text='Bu özellik açıldıysa btc son 24 saatte %10 ve üzerinde düşüş yaparsa ve Ema aşağıda olursa (Ema 20 günlük ortalama altında ise) panik modu devreye girer tüm pozisyonları kapatıp usdt ye dönülür .  ') 
    isPanicModeActive = models.BooleanField(null=False, default=True, verbose_name='Panik modu şuan açık mı?',help_text='Panik modu şuan açık mı?  (Panik modu açıldığında Alış ve satış modları kapalı ya çekilir ve kapatıldığında diğerleri açılır)')
    isExistFromPanicModeAutomaticallyActive = models.BooleanField(null=False, default=True, verbose_name='Panik modundan otomatik çıkış açık mı? ',help_text='Bu seçenek seçili ve Ema kontrolü pozitif kapanırsa panik modundan otomatik olarak çıkış yapılır ') 
    isBuyAutomaticallyAfterPanicMode = models.BooleanField(null=False, default=True, verbose_name='Panik modundan çıkışta otomatik coin al. (aldıktan sonra false yapılacaktır.)',help_text='Panik modundan otomatik çıkış açıkken panik modundan çıkış aşamasında bu alanı kontrol eder ve işaretli ise otomatik olarak birer kademe alır. Alım yaptıktan sonra bu alanı false yapar.)')
    cooldownForNewBuyFromSameCoin = models.IntegerField(default=1,verbose_name='Aynı coinin alımı için geçmesi gereken gün',help_text='Yeni alım yapmak için minimum x gün geçmeli')
    cooldownForNewSellFromSameCoin = models.IntegerField(default=1,verbose_name='Aynı coinin satışı için geçmesi gereken gün',help_text='Yeni satış yapmak için minimum x gün geçmeli') 
    targetPercentageForBuying = models.FloatField(default=3,verbose_name='Alış yapmak için beklenen min fark' ,help_text='Aynı coinden alım yapılırken yeni fiyatın önceki alım fiyatından minimum yüzde x kadar ucuz olması gerekir') #Alış yapmak için beklenen min fark
    targetPercentageForSelling = models.FloatField(default=0.75, verbose_name='Satış yapmak için beklenen min fark',help_text='Satış yapılırken minimum yüzde x kadar kar edilmiş olması gerekir') #Satış yapmak için beklenen min fark
    minRSI = models.IntegerField(default=20 ,verbose_name='Min RSI',help_text='Min RSI (Varsayılan değeri 20)') #Min RSI değeri #Daha fazla alım için 30 yapılıp test edilecek
    midRSI = models.IntegerField(default=50 ,verbose_name='Mid RSI',help_text='Mid RSI (Varsayılan değeri 50)') #Orta RSI değeri
    maxRSI = models.IntegerField(default=80 ,verbose_name='Max RSI',help_text='Max RSI (Varsayılan değeri 80)') #Max RSI değeri
    minRSIFor15mWITHRealMargin = models.IntegerField(default=20 ,verbose_name='Min RSI WITH Real Margin',help_text='Min RSI  WITH Real Margin (Varsayılan değeri 20)') #Min RSI değeri #Daha fazla alım için 30 yapılıp test edilecek
    maxRSIFor15mWITHRealMargin = models.IntegerField(default=40 ,verbose_name='Max RSI WITH Real Margin',help_text='Max RSI  WITH Real Margin (Varsayılan değeri 80)') #Max RSI değeri
    minRSIForRobot1h = models.IntegerField(default=30 ,verbose_name='RSI_1h Min RSI',help_text='RSI_1h için Min RSI (Varsayılan değeri 20)') 
    maxRSIForRobot1h = models.IntegerField(default=60 ,verbose_name='RSI_1h Max RSI',help_text='RSI_1h için Max RSI (Varsayılan değeri 65)') 
    minRSIForLong = models.IntegerField(default=25 ,verbose_name='Margin_RSI_15m ve RSI_15m Long Min RSI',help_text='Margin_RSI_15m ve RSI_15m Long için Min RSI (Varsayılan değeri 20)') 
    maxRSIForLong = models.IntegerField(default=60 ,verbose_name='Margin_RSI_15m ve RSI_15m Long Max RSI',help_text='Margin_RSI_15m ve RSI_15m Long için Max RSI (Varsayılan değeri 65)') 
    minRSIFor15mSlow = models.IntegerField(default=15 ,verbose_name='RSI_15m_Slow Min RSI',help_text='RSI_15m_Slow için Min RSI (Varsayılan değeri 20)') 
    maxRSIFor15mSlow = models.IntegerField(default=60 ,verbose_name='RSI_15m_Slow Max RSI',help_text='RSI_15m_Slow için Max RSI (Varsayılan değeri 65)') 
    minRSIFor1hSlow = models.IntegerField(default=25 ,verbose_name='RSI_15m_Slow Min RSI 1h için',help_text='RSI_15m_Slow için Min RSI 1h için (Varsayılan değeri 20)') 
    maxRSIFor1hSlow = models.IntegerField(default=55 ,verbose_name='RSI_15m_Slow Max RSI 1h için',help_text='RSI_15m_Slow için Max RSI 1h için (Varsayılan değeri 65)') 
    minRSIForLongForBTC = models.IntegerField(default=25 ,verbose_name='Margin_BTC Min RSI',help_text='Margin_BTC için Min RSI (Varsayılan değeri 20)') 
    maxRSIForLongForBTC = models.IntegerField(default=45 ,verbose_name='Margin_BTC Max RSI',help_text='Margin_BTC için Max RSI (Varsayılan değeri 65)') 
    minRSIForShort = models.IntegerField(default=30 ,verbose_name='Margin_RSI_15m Short Min RSI',help_text='Margin_RSI_15m Short için Min RSI (Varsayılan değeri 30)') 
    maxRSIForShort = models.IntegerField(default=70 ,verbose_name='Margin_RSI_15m Short Max RSI',help_text='Margin_RSI_15m Short için Max RSI (Varsayılan değeri 70)') 
    williamR = models.IntegerField(default=-50 ,verbose_name='WilliamR',help_text='WilliamR (Varsayılan değeri -50)') #WilliamR değeri
    commonTotalStartMoneyAsUSDT = models.FloatField(default=0,verbose_name='Başlangıç Toplam USDT',help_text='Toplam yatırılan paranın usdt olarak karşılığı') 
    commonTotalStartMoneyAsTL = models.FloatField(default=0,verbose_name='Başlangıç Toplam TL',help_text='Toplam yatırılan paranın tl olarak karşılığı') 
    addBudgetToRobotWhenTargetToTopComes_BtcTargetArea = models.FloatField(default=0,verbose_name='Bütçe btc üst hedefi',help_text='Aksiyonun tetiklenmesi için Btc nin üzerine çıkması gereken değer') #ileride düşüş için de yapılabilir
    addBudgetToRobotWhenTargetToTopComes_AddBudget = models.FloatField(default=0,verbose_name='Bütçe üst hedefte eklenecek tutar',help_text='Btc üst hedef aksiyonu tetiklendiğinde eklenecek miktar') 
    lastRobotWorkingDate = models.DateTimeField(null=True, blank=True,verbose_name='Son robotun çalışma tarihi')
    lastMarginRobotWorkingDate = models.DateTimeField(null=True, blank=True,verbose_name='Son margin robotun çalışma tarihi')
    lastMarginBTCRobotWorkingDate = models.DateTimeField(null=True, blank=True,verbose_name='Son marginBTC robotun çalışma tarihi')
    temp_emaLowWarningStartDate = models.DateTimeField(null=True, blank=True,verbose_name='Ema uyarı başlama tarihi',help_text='Ema nın ortalama altına ilk düştüğü tarih.(Eğer ema üzerine çıkılırsa bu tarhi boşaltılır.)')
    isMarginRobotActive = models.BooleanField(null=False, default=False, verbose_name='Margin robotu açık mı?',help_text='Ema üzerindeyken long açıp, ema altındayken short açan marginli robot çalışıyor mu?')
    isMarginBTCRobotActive = models.BooleanField(null=False, default=False, verbose_name='MarginBTC robotu açık mı?',help_text='Btc ye bakıp long short açan robot çalışıyor mu?')
    isMarginRobotShortActive = models.BooleanField(null=False, default=True, verbose_name='Margin robotu short alım açık mı?',help_text='Margin Robot açık olduğunda bu seçenekte açık ise Ema altındayken short açan marginli robot çalışıyor mu?')
    isMarginRobotLongActive = models.BooleanField(null=False, default=True, verbose_name='Margin robotu long alım açık mı?',help_text='Margin Robot açık olduğunda bu seçenekte açık ise Ema üzerindeyken long açan marginli robot çalışıyor mu?')
    isMarginBTCRobotLongActive = models.BooleanField(null=False, default=True, verbose_name='MarginBTC robotu long alım açık mı?',help_text='MarginBTC Robot açık olduğunda bu seçenekte açık ise Ema üzerindeyken long açan marginli robot çalışıyor mu?')
    maxOpenTradeCountForMargin = models.IntegerField(default=5,verbose_name='Margin_RSI_15m Long işlem için aynı coin adet limiti',help_text='Margin_RSI_15m Long işlem için aynı coin adet limiti' )
    maxOpenTradeCountForMarginBTC = models.IntegerField(default=2,verbose_name='MarginBTC Long işlem için aynı coin adet limiti',help_text='MarginBTC Long işlem için aynı coin adet limiti' )
    cooldownAsHoursForNewBuyFromSameCoinBaseForRsi15Slow = models.IntegerField(default=12,verbose_name='Margin_RSI_15m ve RSI_15m Long ve Short için taban cooldown saat sayisi',help_text='Margin_RSI_15m ve RSI_15m Long için yeni alım yapmak için minimum (x * eldeki adet) kadar saat geçmeli')
    cooldownAsHoursForNewBuyFromSameCoinBaseForMargin = models.IntegerField(default=12,verbose_name='Margin_RSI_15m ve RSI_15m Long ve Short için taban cooldown saat sayisi',help_text='Margin_RSI_15m ve RSI_15m Long için yeni alım yapmak için minimum (x * eldeki adet) kadar saat geçmeli')
    cooldownAsHoursForNewBuyFromSameCoinBaseForMarginBTC = models.IntegerField(default=6,verbose_name='MarginBTC için taban cooldown saat sayisi',help_text='MarginBTC yeni alım yapmak için minimum x kadar saat geçmeli')
    cooldownAsHoursForNewBuyFromSameCoinBaseFor1h = models.IntegerField(default=6,verbose_name='RSI_1h için taban cooldown saat sayisi',help_text='RSI_1h için yeni alım yapmak için minimum (x * eldeki adet) kadar saat geçmeli')
    targetPercentageForLongSellingForMargin = models.FloatField(default=0.75, verbose_name='Margin Long için Satış yapmak için beklenen min fark')
    targetPercentageForLongSellingForMarginBTC = models.FloatField(default=0.75, verbose_name='MarginBTC Long için Satış yapmak için beklenen min fark')
    targetPercentageForShortSellingForMargin = models.FloatField(default=0.75, verbose_name='Margin Short için Satış yapmak için beklenen min fark')
    stopPercentageForSellingForMargin = models.FloatField(default=-0.75, verbose_name='Margin_RSI_15m Long ve Short için zarar kes(stop) yapılacak yüzdelik oran') 
    stopPercentageForSellingForMarginBTC = models.FloatField(default=-1, verbose_name='Margin_BTC için zarar kes(stop) yapılacak yüzdelik oran') 
    targetPercentageForSellingForRobotBTC = models.FloatField(default=0.7, verbose_name='Margin_BTC için Satış yapmak için beklenen min kar farkı',help_text='Margin_BTC için satış yapılırken minimum yüzde x kadar kar edilmiş olması gerekir') 
    limitPercentageForSellingForMargin = models.FloatField(default=3, verbose_name='Margin_RSI_15m Long ve Short için kar satışı yapılacak yüzdelik oran') 
    isControlEmaForSellingPreviousMarginTrades = models.BooleanField(null=False, default=False, verbose_name='EMA üzerindeyse elinde BTCDOWN varsa sat',help_text='EMA üzerindeyse elinde BTCDOWN varsa sat')
    robotTotalBuyCount = models.IntegerField(default=-0, verbose_name='Robot RSI_4h toplam alış sayısı') 
    robotPositiveSellCount = models.IntegerField(default=0, verbose_name='Robot RSI_4h karlı satış sayısı') 
    robotNegativeSellCount = models.IntegerField(default=0, verbose_name='Robot RSI_4h zararına satış sayısı') 
    marginRobotTotalBuyCount = models.IntegerField(default=0, verbose_name='Margin_RSI_15m robot toplam alış sayısı') 
    marginRobotPositiveSellCount = models.IntegerField(default=0, verbose_name='Margin_RSI_15m robot karlı satış sayısı') 
    marginRobotNegativeSellCount = models.IntegerField(default=0, verbose_name='Margin_RSI_15m robot zararına satış sayısı') 
    marginBTCRobotTotalBuyCount = models.IntegerField(default=0, verbose_name='MarginBTC robot toplam alış sayısı') 
    marginBTCRobotPositiveSellCount = models.IntegerField(default=0, verbose_name='MarginBTC robot karlı satış sayısı') 
    marginBTCRobotNegativeSellCount = models.IntegerField(default=0, verbose_name='MarginBTC robot zararına satış sayısı') 
    isRobot15mActive = models.BooleanField(null=False, default=False, verbose_name='RSI_15m robotu açık mı?',help_text='Ema üzerindeyken alım ve satım yapan, ema nın %5 altındayken stop olan RSI_15m robot çalışıyor mu?')
    isRobot15mWITHRealMarginActive = models.BooleanField(null=False, default=False, verbose_name='RSI_15m_WITHRealMargin robotu açık mı?',help_text='Ema üzerindeyken alım ve satım yapan, ema nın %5 altındayken stop olan RSI_15m_WITHRealMargin robot çalışıyor mu?')
    isRobot15mSlowActive = models.BooleanField(null=False, default=False, verbose_name='RSI_15m_Slow robotu açık mı?',help_text='Ema üzerindeyken alım ve satım yapan, ema nın %5 altındayken stop olan RSI_15m_Slow robot çalışıyor mu?')
    isRobot1hActive = models.BooleanField(null=False, default=False, verbose_name='RSI_1h robotu açık mı?',help_text='Ema üzerindeyken alım ve satım yapan, ema nın %5 altındayken stop olan RSI_1h robot çalışıyor mu?')
    robot15mTotalBuyCount = models.IntegerField(default=-0, verbose_name='Robot RSI_15m toplam alış sayısı') 
    robot15mPositiveSellCount = models.IntegerField(default=0, verbose_name='Robot RSI_15m karlı satış sayısı') 
    robot15mNegativeSellCount = models.IntegerField(default=0, verbose_name='Robot RSI_15m zararına satış sayısı') 
    robot15mWITHRealMarginTotalBuyCount = models.IntegerField(default=1, verbose_name='Robot RSI_15m_WITHRealMargin toplam alış sayısı') 
    robot15mWITHRealMarginPositiveSellCount = models.IntegerField(default=1, verbose_name='Robot RSI_15m_WITHRealMargin karlı satış sayısı') 
    robot15mWITHRealMarginNegativeSellCount = models.IntegerField(default=0, verbose_name='Robot RSI_15m_WITHRealMargin zararına satış sayısı') 
    robot15mSlowTotalBuyCount = models.IntegerField(default=-0, verbose_name='Robot RSI_15m_Slow toplam alış sayısı') 
    robot15mSlowPositiveSellCount = models.IntegerField(default=0, verbose_name='Robot RSI_15m_Slow karlı satış sayısı') 
    robot15mSlowNegativeSellCount = models.IntegerField(default=0, verbose_name='Robot RSI_15m_Slow zararına satış sayısı') 
    robot1hTotalBuyCount = models.IntegerField(default=-0, verbose_name='Robot RSI_1h toplam alış sayısı') 
    robot1hPositiveSellCount = models.IntegerField(default=0, verbose_name='Robot RSI_1h karlı satış sayısı') 
    robot1hNegativeSellCount = models.IntegerField(default=0, verbose_name='Robot RSI_1h zararına satış sayısı') 
    isControlEmaForSellingPreviousRobot15mTrades = models.BooleanField(null=False, default=True, verbose_name='EMA nın %5 altındaysa elinde RSI_15m robot ile alınmış coinler varsa sat')
    isControlEmaForSellingPreviousRobot15mWITHRealMarginTrades = models.BooleanField(null=False, default=True, verbose_name='EMA nın %5 altındaysa elinde RSI_15m_WITHRealMargin robot ile alınmış coinler varsa sat')
    isControlEmaForSellingPreviousRobot15mSlowTrades = models.BooleanField(null=False, default=True, verbose_name='EMA nın %5 altındaysa elinde RSI_15m_Slow robot ile alınmış coinler varsa sat')
    isControlEmaForSellingPreviousRobot1hTrades = models.BooleanField(null=False, default=True, verbose_name='EMA nın %5 altındaysa elinde RSI_1h robot ile alınmış coinler varsa sat')
    maxOpenTradeCountForRobot15m = models.IntegerField(default=2,verbose_name='RSI_15m işlem için aynı coin adet limiti',help_text='RSI_15m işlem için aynı coin adet limiti' )
    maxOpenTradeCountForRobot15mSlow = models.IntegerField(default=2,verbose_name='RSI_15mSlow işlem için aynı coin adet limiti',help_text='RSI_15mSlow işlem için aynı coin adet limiti' )
    maxOpenTradeCountForRobot1h = models.IntegerField(default=2,verbose_name='RSI_1h işlem için aynı coin adet limiti',help_text='RSI_1h işlem için aynı coin adet limiti' )
    stopPercentageForSellingForRobot15m = models.FloatField(default=-0.75, verbose_name='RSI_15m için zarar kes(stop) yapılacak yüzdelik oran',help_text='RSI_15m için zarar kes(stop) yapılacak yüzdelik oran') 
    stopPercentageForSellingForRobot15mSlow = models.FloatField(default=-0.75, verbose_name='RSI_15m_Slow için zarar kes(stop) yapılacak yüzdelik oran',help_text='RSI_15m_Slow için zarar kes(stop) yapılacak yüzdelik oran') 
    stopPercentageForSellingForRobot1h = models.FloatField(default=-10, verbose_name='RSI_1h için zarar kes(stop) yapılacak yüzdelik oran',help_text='RSI_1h için zarar kes(stop) yapılacak yüzdelik oran') 
    limitPercentageForSellingForRobot15m = models.FloatField(default=3, verbose_name='RSI_15m için kar satışı yapılacak yüzdelik oran') 
    targetPercentageForSellingForRobot15m = models.FloatField(default=0.75, verbose_name='RSI_15m için Satış yapmak için beklenen min kar farkı',help_text='RSI_15m için satış yapılırken minimum yüzde x kadar kar edilmiş olması gerekir') 
    targetPercentageForSellingForRobot15mSlow = models.FloatField(default=0.75, verbose_name='RSI_15m_Slow için Satış yapmak için beklenen min kar farkı',help_text='RSI_15m_Slow için satış yapılırken minimum yüzde x kadar kar edilmiş olması gerekir') 
    targetPercentageForSellingForRobot1h = models.FloatField(default=10, verbose_name='RSI_1h için Satış yapmak için beklenen min kar farkı',help_text='RSI_1h için satış yapılırken minimum yüzde x kadar kar edilmiş olması gerekir') 
    lastRobot15mWorkingDate = models.DateTimeField(null=True, blank=True,verbose_name='Son RSI_15m robotun çalışma tarihi')
    lastRobot15mWITHRealMarginWorkingDate = models.DateTimeField(null=True, blank=True,verbose_name='Son RSI_15m_WITHRealMargin robotun çalışma tarihi')
    lastRobot15mSlowWorkingDate = models.DateTimeField(null=True, blank=True,verbose_name='Son RSI_15m_Slow robotun çalışma tarihi')
    lastRobot1hWorkingDate = models.DateTimeField(null=True, blank=True,verbose_name='Son RSI_1h robotun çalışma tarihi')
    lossLimitForRobot4h = models.FloatField(default=-100,verbose_name='Robot RSI_4h zarar limiti',help_text='Robotun bu zarar altına geldiğinde komple çalışmayacak. İstenirse sonradan arttırılabilir.') 
    lossLimitForRobot15m = models.FloatField(default=-100,verbose_name='Robot RSI_15m zarar limiti',help_text='Robotun bu zarar altına geldiğinde komple çalışmayacak. İstenirse sonradan arttırılabilir.') 
    lossLimitForRobot15mWITHRealMargin = models.FloatField(default=-100,verbose_name='Robot RSI_15m_WITHRealMargin zarar limiti',help_text='Robotun bu zarar altına geldiğinde komple çalışmayacak. İstenirse sonradan arttırılabilir.') 
    lossLimitForRobot15mSlow = models.FloatField(default=-100,verbose_name='Robot RSI_15mSlow zarar limiti',help_text='Robotun bu zarar altına geldiğinde komple çalışmayacak. İstenirse sonradan arttırılabilir.') 
    lossLimitForRobot1h = models.FloatField(default=-100,verbose_name='Robot RSI_1h zarar limiti',help_text='Robotun bu zarar altına geldiğinde komple çalışmayacak. İstenirse sonradan arttırılabilir.') 
    lossLimitForRobotMargin = models.FloatField(default=-100,verbose_name='Robot Margin zarar limiti',help_text='Robotun bu zarar altına geldiğinde komple çalışmayacak. İstenirse sonradan arttırılabilir.') 
    lossLimitForRobotMarginBTC = models.FloatField(default=-100,verbose_name='MarginBTC robot Margin zarar limiti',help_text='MarginBTC robotun bu zarar altına geldiğinde komple çalışmayacak. İstenirse sonradan arttırılabilir.') 
    stopBuyingDateForMargin = models.DateTimeField(null=True, blank=True,verbose_name='Margin alış durduruşunun başlama tarihi (Değiştirilmez)',help_text='Margin peş peşe 3 tane zararına satış yapıldığı zaman bu tarih alanını doldur ve 12 saat boyunca başka alım yapma. 12 saat sonra bu alanı boşaltıp tekrar alımlara devam et.')
    stopBuyingDateForMarginBTC = models.DateTimeField(null=True, blank=True,verbose_name='MarginBTC alış durduruşunun başlama tarihi (Değiştirilmez)',help_text='MarginBTC 1 tane zararına satış yapıldığı zaman bu tarih alanını doldur ve 6 saat boyunca başka alım yapma. 6 saat sonra bu alanı boşaltıp tekrar alımlara devam et.')
    stopBuyingDateFor4h = models.DateTimeField(null=True, blank=True,verbose_name='Robot4h alış durduruşunun başlama tarihi (Değiştirilmez)',help_text='Robot4h peş peşe 3 tane zararına satış yapıldığı zaman bu tarih alanını doldur ve 12 saat boyunca başka alım yapma. 12 saat sonra bu alanı boşaltıp tekrar alımlara devam et.')
    stopBuyingDateFor15m = models.DateTimeField(null=True, blank=True,verbose_name='Robot15m alış durduruşunun başlama tarihi (Değiştirilmez)',help_text='Robot15m peş peşe 3 tane zararına satış yapıldığı zaman bu tarih alanını doldur ve 12 saat boyunca başka alım yapma. 12 saat sonra bu alanı boşaltıp tekrar alımlara devam et.')
    stopBuyingDateFor15mWITHRealMargin = models.DateTimeField(null=True, blank=True,verbose_name='Robot15mWihRealMargin alış durduruşunun başlama tarihi (Değiştirilmez)',help_text='Robot15mWihRealMargin peş peşe 3 tane zararına satış yapıldığı zaman bu tarih alanını doldur ve 12 saat boyunca başka alım yapma. 12 saat sonra bu alanı boşaltıp tekrar alımlara devam et.')
    stopBuyingDateFor15mSlow = models.DateTimeField(null=True, blank=True,verbose_name='Robot15mSlow alış durduruşunun başlama tarihi (Değiştirilmez)',help_text='Robot15mSlow peş peşe 3 tane zararına satış yapıldığı zaman bu tarih alanını doldur ve 12 saat boyunca başka alım yapma. 12 saat sonra bu alanı boşaltıp tekrar alımlara devam et.')
    stopBuyingDateFor1h = models.DateTimeField(null=True, blank=True,verbose_name='Robot1h alış durduruşunun başlama tarihi (Değiştirilmez)',help_text='Robot1h peş peşe 3 tane zararına satış yapıldığı zaman bu tarih alanını doldur ve 12 saat boyunca başka alım yapma. 12 saat sonra bu alanı boşaltıp tekrar alımlara devam et.')
    stopBuyingWaitingTime = models.IntegerField(default=12, verbose_name='Robotlarda alış dondurulduktan sonra tekrar alıma geçmesi için beklemesi gereken saat sayısı') 
    stopBuyingWaitingTimeMarginBTC = models.IntegerField(default=6, verbose_name='MarginBRC robotunda alış dondurulduktan sonra tekrar alıma geçmesi için beklemesi gereken saat sayısı') 
    waitHoursAfterNegativeSell = models.FloatField(default=3.0, verbose_name='Negatif satıştan sonra yeni alış yapabilmek için beklemesi gereken saat sayısı') 
    stopLossTriggerStartPercentage = models.FloatField(default=4,verbose_name='StopLoss başlama yüzdesi',help_text='Örneğin %4 kar ettikten sonra tetiklenir') 
    stopLossTriggerStopPercentage = models.FloatField(default=1,verbose_name='StopLoss kaybı durdurma yüzdesi',help_text='Örneğin tetiklendikten sonra %1 kaybettiğinde çalışır') 
    stopLossTriggerStartPercentageMarginBTC = models.FloatField(default=2.5,verbose_name='MarginBTC StopLoss başlama yüzdesi',help_text='Örneğin %4 kar ettikten sonra tetiklenir') 
    stopLossTriggerStopPercentageMarginBTC = models.FloatField(default=0.75,verbose_name='MarginBTC StopLoss kaybı durdurma yüzdesi',help_text='Örneğin tetiklendikten sonra %1 kaybettiğinde çalışır') 
    temp_draftUsdtDiffAction = models.FloatField(default=0,verbose_name='Takip Usdt') 
    temp_draftUsdtDiffDateAction = models.DateTimeField(null=True, blank=True,verbose_name='Takip Usdt Resetlenme Zamanı')
    temp_startForRobotAsUsdt = models.FloatField(default=500,verbose_name='Robot RSI_4h başlangıç bütçesi (Değiştirilmez)') 
    temp_startForRobot15mAsUsdt = models.FloatField(default=500,verbose_name='Robot RSI_15m başlangıç bütçesi (Değiştirilmez)') 
    temp_startForRobot15mWITHRealMarginAsUsdt = models.FloatField(default=500,verbose_name='Robot RSI_15m_WITHRealMargin başlangıç bütçesi (Değiştirilmez)') 
    temp_startForRobot15mSlowAsUsdt = models.FloatField(default=500,verbose_name='Robot RSI_15m_Slow başlangıç bütçesi (Değiştirilmez)') 
    temp_startForRobot1hAsUsdt = models.FloatField(default=500,verbose_name='Robot RSI_1h başlangıç bütçesi (Değiştirilmez)') 
    temp_startForMarginAsUsdt = models.FloatField(default=500,verbose_name='Robot Margin başlangıç bütçesi (Değiştirilmez)') 
    temp_startForMarginBTCAsUsdt = models.FloatField(default=500,verbose_name='Robot Margin başlangıç bütçesi (Değiştirilmez)') 
    givenLimitHoursForRobot15mThenTryToSell = models.FloatField(default=2, verbose_name='robot15m Verilen saat kadar sat sinyali beklenecek, satılamazsa sürenin sonuna gelindiğinde trade 0.1 kar ve üzerindeyse hemen satılacak') 
    givenLimitHoursForRobot15mSlowThenTryToSell = models.FloatField(default=36, verbose_name='robot15mSlow Verilen saat kadar sat sinyali beklenecek, satılamazsa sürenin sonuna gelindiğinde trade 0.1 kar ve üzerindeyse hemen satılacak') 
    givenLimitHoursForRobot1hThenTryToSell = models.FloatField(default=72, verbose_name='robot1h Verilen saat kadar sat sinyali beklenecek, satılamazsa sürenin sonuna gelindiğinde trade 0.1 kar ve üzerindeyse hemen satılacak') 
    givenLimitHoursForRobotMarginThenTryToSell = models.FloatField(default=2, verbose_name='robotmargin Verilen saat kadar sat sinyali beklenecek, satılamazsa sürenin sonuna gelindiğinde trade 0.1 kar ve üzerindeyse hemen satılacak') 
    moveRSIComeBackPercentage = models.IntegerField(default=5,verbose_name='RSI ın usdt karşısındaki değeri düştükten sonra x değer kadar yükseldiğinde satın alma siyali gelir.') 
    temp_isRobotWorkingNow = models.BooleanField(null=False, default=False, verbose_name='Bu Alan Manuel Değiştirilmez ! (Robot Şuan Çalışıyor Mu?)')

    def __str__(self):
        return "%s" % (self.maxLimitForRobotAsUsdt)

    def getDetails(self):
        return "Robot bütçe : %s , Aynı coin adet limiti : %s , Ema kontrolü (Alım yaparken) : %s , Alış modu açık mı? : %s , Satış modu açık mı? : %s , Biriktirilecek para birimi : %s , EMA kontrolünden geçmediyse artıda olan tradelerin yarısını satsın mı? : %s , Panik moduna otomatik giriş kontrolü açık mı? : %s , Panik modu şuan açık mı? : %s , Panik modundan otomatik çıkış açık mı? : %s , Aynı coinin alımı için geçmesi gereken gün : %s , Aynı coinin satışı için geçmesi gereken gün : %s , Min RSI : %s , Mid RSI : %s , Max RSI : %s , WilliamR : %s , Başlangıç Toplam USDT : %s , Başlangıç Toplam TL : %s" % (self.maxLimitForRobotAsUsdt,self.maxOpenTradeCountForSameCoin,self.isEmaControlActiveForBuying,self.isBuyingModeActive,self.isSellingModeActive,self.coinTargetToCollect,self.isSellingOneStepIfDoesntPassEMAControlModeActive,self.isControlForPanicMode,self.isPanicModeActive,self.isExistFromPanicModeAutomaticallyActive,self.cooldownForNewBuyFromSameCoin,self.cooldownForNewSellFromSameCoin,self.minRSI,self.midRSI,self.maxRSI,self.williamR,self.commonTotalStartMoneyAsUSDT,self.commonTotalStartMoneyAsTL)

    def getRobotNotSoldYetCount(self):
        return self.robotTotalBuyCount - (self.robotPositiveSellCount+self.robotNegativeSellCount)

    def getMarginRobotNotSoldYetCount(self):
        return self.marginRobotTotalBuyCount - (self.marginRobotPositiveSellCount+self.marginRobotNegativeSellCount)
    
    def getMarginBTCRobotNotSoldYetCount(self):
        return self.marginBTCRobotTotalBuyCount - (self.marginBTCRobotPositiveSellCount+self.marginBTCRobotNegativeSellCount)
    
    def getRobot15mNotSoldYetCount(self):
        return self.robot15mTotalBuyCount - (self.robot15mPositiveSellCount+self.robot15mNegativeSellCount)

    def getRobot15mWITHRealMarginNotSoldYetCount(self):
        return self.robot15mWITHRealMarginTotalBuyCount - (self.robot15mWITHRealMarginPositiveSellCount+self.robot15mWITHRealMarginNegativeSellCount)
    
    def getRobot15mSlowNotSoldYetCount(self):
        return self.robot15mSlowTotalBuyCount - (self.robot15mSlowPositiveSellCount+self.robot15mSlowNegativeSellCount)
    
    def getRobot1hNotSoldYetCount(self):
        return self.robot1hTotalBuyCount - (self.robot1hPositiveSellCount+self.robot1hNegativeSellCount)

    def getRobot4hSuccessRate(self):
        return (self.robotPositiveSellCount * 100) / (self.robotPositiveSellCount+self.robotNegativeSellCount)

    def getRobot15mSuccessRate(self):
        return (self.robot15mPositiveSellCount * 100) / (self.robot15mPositiveSellCount+self.robot15mNegativeSellCount)

    def getRobot15mWITHRealMarginSuccessRate(self):
        return (self.robot15mWITHRealMarginPositiveSellCount * 100) / (self.robot15mWITHRealMarginPositiveSellCount+self.robot15mWITHRealMarginNegativeSellCount)
    
    def getRobot15mSlowSuccessRate(self):
        return (self.robot15mSlowPositiveSellCount * 100) / (self.robot15mSlowPositiveSellCount+self.robot15mSlowNegativeSellCount)
    
    def getRobot1hSuccessRate(self):
        return (self.robot1hPositiveSellCount * 100) / (self.robot1hPositiveSellCount+self.robot1hNegativeSellCount)

    def getRobotMarginSuccessRate(self):
        return (self.marginRobotPositiveSellCount * 100) / (self.marginRobotPositiveSellCount+self.marginRobotNegativeSellCount)
    
    def getRobotMarginBTCSuccessRate(self):
        return (self.marginBTCRobotPositiveSellCount * 100) / (self.marginBTCRobotPositiveSellCount+self.marginBTCRobotNegativeSellCount)

class ProcessLog(models.Model):
    processResult = models.TextField(max_length=100, blank=False, null=True, verbose_name='Islem Durumu',help_text='Islem Durumu')
    processDate = models.DateTimeField(default=datetime.now, blank=True,verbose_name='Islem Tarihi',help_text='Islem Tarihi')
    processSubject = models.TextField(max_length=100, blank=False, null=True, verbose_name='Islem Basligi',help_text='Islem Basligi')
    processDetails = models.TextField(max_length=100000, blank=False, null=True, verbose_name='Islem Detayi',help_text='Islem Detayi')
    
    def __str__(self):
        return "%s" % (self.processResult)
    
    def getDetails(self):
        return "Islem Durumu : %s , İşlem Tarihi : %s , Islem Basligi : %s , Islem Detayi : %s " % (self.processResult,self.processDate,self.processSubject,self.processDetails)

class TradeLog(models.Model):
    processType = models.TextField(max_length=5, blank=False, null=True, verbose_name='İşlem Tipi',help_text='Buy Sell')  # CharField
    coinName = models.TextField(max_length=100, blank=False, null=True, verbose_name='Coin adı',help_text='Coin adı burada girilir.')  # CharField
    exchangeCoinName = models.TextField(max_length=100, blank=False, null=True, verbose_name='Fiyat Çifti')  # CharField
    count = models.FloatField(default=0,verbose_name='Adet')
    price = models.FloatField(default=0,verbose_name='Fiyat Usdt',help_text='Fiyat Usdt olarak') #
    transactionDate = models.DateTimeField(default=datetime.now, blank=True,verbose_name='İşlem Tarihi')
    passedDaysToSell = models.IntegerField(default=0, verbose_name='Kaç günde satıldı?') 
    passedHoursToSell = models.IntegerField(default=0, verbose_name='Kaç saatte satıldı?') 
    profitLossPercentage = models.FloatField(default=0,verbose_name='Kar/zarar USDT üzerinden Yüzdelik olarak',help_text='İşlem sonucunda yapılmış olan yüzdelik kar/zarar USDT') 
    gainUsdt = models.FloatField(default=0,verbose_name='Kar/Zarar USDT olarak')
    buyedByRobot = models.BooleanField(null=False, default=False, verbose_name='Robot mu işlemi yaptı?',help_text='Robot mu işlemi yaptı?')
    indicatorResults = models.TextField(max_length=1000, default='', blank=True, null=True, verbose_name='İşlem sırasındaki indikatör değerleri')
    strategy = models.TextField(max_length=100, default='', blank=True, null=True, verbose_name='Alış ve Satış Stratejisi',help_text='Örnek : Margin_RSI_15m , RSI_15m , RSI_4h , Specified_Priority_Purchases , Manuel_Webpage_Action , Manuel_Entered')

    def __str__(self):
        return "%s" % (self.coinName)

    def getTotalPrice(self):
        return self.count * self.price

    def fontColorAccordingtoProcessType(self):
        if self.processType=='BUY':
            return 'green'
        else:
            return 'red'

#class MainPageValues():


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    job = models.CharField(max_length=100, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    image = models.ImageField(upload_to='images/User', verbose_name='image',null=True, blank=True, help_text='Photo of user')
    
    def __str__(self):
        return "%s" % (self.user)

    def get_image_url(self):
        if self.image:
            return self.image.url
        else:
            return "images/rsm1.png"
        
    @receiver(post_save, sender=User)
    def create_user_profile(sender, instance, created, **kwargs):
        if created:
            Profile.objects.create(user=instance)

    @receiver(post_save, sender=User)
    def save_user_profile(sender, instance, **kwargs):
        instance.profile.save()
        
class News(models.Model):#ESKI
    title = models.TextField(max_length=100, blank=False, null=True, verbose_name='Başlık Giriniz.',help_text='Başlık Bilgisi Burada Girilir.')  # CharField
    #content = models.TextField(max_length=10000,blank=True, null=True,verbose_name='İçerik Giriniz.', help_text='İçerik Burada Girilir.')
    content = RichTextField(max_length=10000, blank=True, null=True,verbose_name='İçerik Giriniz.', help_text='İçerik Burada Girilir.')
    slug = models.SlugField(null=True, unique=True, editable=False)
    creation_date = models.DateField(auto_now_add=True, auto_now=False)
    creator_user = models.ForeignKey(Profile, on_delete=models.PROTECT, related_name=u"creator_user")
    image = models.ImageField(upload_to='images/News', verbose_name='image',null=True, blank=True, help_text='Photo of news')
    image_is_fit_to_screen = models.BooleanField(null=False, default=False, verbose_name='Resmi çerçeveye sığdır.',help_text='Resimin çerçeveye sığdırılması için işaretleyiniz, orjinal boyutunda kullanmak için işaretlemeyiniz.')
    show_count = models.IntegerField(default=0)
    is_published = models.BooleanField(null=False, default=True, verbose_name='Yayınlansın',help_text='Haberin canlı ortamda yayınlanıp yayınlanmaması için seçim yapılır.')
    class Meta:
        ordering = ['id']
        verbose_name_plural = 'News'

    def __str__(self):
        return "%s" % (self.title)

    def get_absolute_url(self):
        return reverse("news_detail", kwargs={"slug": self.slug})

    def get_image_url(self):
        if self.image:
            return self.image.url
        else:
            return None

    def get_profile_image_url(self):
        if self.creator_user.get_image_url:
            return self.creator_user.image.url
        else:
            return None
        
    def get_unique_slug(self):
        count = 0
        slug = slugify(unidecode(self.title))
        new_slug = slug
        while News.objects.filter(slug=new_slug).exists():
            count += 1
            new_slug = "%s-%s" % (slug, count)
        slug = new_slug
        return slug

    def save(self, *args, **kwargs):
        if self.id is None:
            self.slug = self.get_unique_slug()
        else:
            news = News.objects.get(slug=self.slug)
            if news.title != self.title:
                self.slug = self.get_unique_slug()
        super(News, self).save(*args, **kwargs)


    def get_news_comment(self):
        # haber e ait tüm yorumların listesi
        return self.comment.all().order_by('-id')

    def get_comment_list_count(self):
        return self.get_news_comment().count()

    def get_is_news_comment_class(self):
        if self.get_comment_list_count() > 0:
            return 'font-color-blue'
        else:
            return ''

    def get_news_comment_count_by_user(self, activeUser):
        return self.comment.filter(title=activeUser).count()

    def get_news_like(self):
        # haber e ait tüm yorumların listesi
        return self.like_news.all().order_by('-id')

    def get_news_like_count(self):
        return self.get_news_like().count()

    def get_is_news_liked_class(self):
        if self.get_news_like_count() > 0:
            return 'font-color-red'
        else:
            return ''

    def get_is_news_seen_count_class(self):
        if self.show_count > 0:
            return 'font-color-yellow'
        else:
            return ''

            

class Announcement(models.Model):#ESKI
    title = models.TextField(max_length=30, blank=False, null=True,
                             verbose_name='Başlık Giriniz.', help_text='Başlık Bilgisi Burada Girilir.')
    content = models.TextField(max_length=10000, blank=True, null=True, verbose_name='İçerik Detaylarını İsterseniz Bu Alandan Girebilirsiniz.',
                               help_text='İçerik Detaylarını İsterseniz Bu Alandan Girilir.')
    slug = models.SlugField(null=True, unique=True, editable=False)
    creation_date = models.DateField(auto_now_add=True, auto_now=False)
    creator_user = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name=u"announce_created_by")
    image = models.ImageField(upload_to='images/Announcement',
                              verbose_name='resim', null=True, blank=True, help_text='kapak foto')
    like_count = models.IntegerField(default=0)
    show_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return "%s" % (self.title)

    def get_absolute_url(self):
        return reverse("announcement_detail", kwargs={"pk": self.pk})

    def get_image_url(self):
        if self.image:
            return self.image.url
        else:
            return None

    def get_profile_image_url(self):
        if self.creator_user.get_image_url:
            return self.creator_user.image.url
        else:
            return None
        
    def get_unique_slug(self):
        count = 0
        slug = slugify(unidecode(self.title))
        new_slug = slug
        while Announcement.objects.filter(slug=new_slug).exists():
            count += 1
            new_slug = "%s-%s" % (slug, count)
        slug = new_slug
        return slug

    def save(self, *args, **kwargs):
        if self.id is None:
            self.slug = self.get_unique_slug()
        else:
            announcement = Announcement.objects.get(slug=self.slug)
            if announcement.title != self.title:
                self.slug = self.get_unique_slug()
        super(Announcement, self).save(*args, **kwargs)


class Comment(models.Model):#ESKI
    news = models.ForeignKey(News, null=True, on_delete=models.PROTECT, related_name='comment')
    creator_user = models.ForeignKey(Profile, on_delete=models.PROTECT, null=True,related_name=u"comment_created_by")
    creation_date = models.DateField(auto_now_add=True, auto_now=False)
    content = RichTextField(max_length=10000, blank=False, null=True,verbose_name='Enter Comment', help_text='Please enter comment')
    
    class Meta:
        ordering = ['id']

    def __unicode__(self):
        return self.id

    def __str__(self):
        return "%s-%s" % (self.news, self.news.creator_user)
    

class LikeNews(models.Model):#ESKI
    user = models.ForeignKey(User, null=True, default=1, related_name='like_news',on_delete=models.PROTECT)
    news = models.ForeignKey(News, null=True, related_name='like_news',on_delete=models.PROTECT)

    class Meta:
        verbose_name_plural = 'Beğenilen Haberler'

    def __str__(self):
        return "%s %s" % (self.user, self.news)


    