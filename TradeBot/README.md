Tradingview ve Python sinyal stratejisi
_______________________________________________________________
22102022-Kararlar
-sat verdiginde eger alim saatini x saat gecmemisse alt limite baksin eger gecmisse satsın ama eğer x saatini geçmişse kar orani 0.1'den buyukse alt bir limit beklemesin sat sinyaline bakmadan direk satsin cunku uzun surede zarar ediyor (x değeri marginlerde 2 saat, altcoinlerde 3 saat)
-sat i 60 dan 50 ye cek 
-kar icin beklenen alt limiti tüm robotlarda 1 e cek
-zarar icin stop u tüm robotlarda 1 e cek


SON GUNCELLEME - 20.10.2022 :  Yeni MarginBTC robotu
________________________
Alış
İf(son satışı zarar yapmamış ise 
  || zararına satış yapmışsa ve üzerine 6 saat geçmiş ise) 
    && 15dk-rsi da 25 altında al ise
    && aynı pozisyonda daha önceden 1 den fazla alınmamışsa yani aynı anda max 2 Trade olsn 
    

Satış
15dk-rsi da 50 üzerinde sat ama Robot sat verince satması için min %1 kar yapmış olması lazım

Robot %1 zararda stop olacak ve satacak

Robot %2.5 kar yapmışsa trailing başlatıp %0.5 ilk düştüğü anda satacak 


SON GUNCELLEME - 14.09.2022 : 
btc fiyatına göre ema 20 günlüğün fiyatı ema 50 günlük fiyatının altındaysa 
ve mevcut btc fiyatı ema 50 nin üzerine çıktıysa alış yapma


_______________________________________________________________
SON GUNCELLEME - 20.07.2022 : 

Robot15m ve RobotMargin için;
Yapılan : 4saatlik emanın üzerinde olursa satın al
İleride yapılabilecek : 1Günlük Ema kontrolüne ek olarak Btc 1Günlük rsi ı 40 den az ise alımlara izin ver

_______________________________________________________________

SON GUNCELLEME - 16.08.2022 : 
Robotlar 1günlük ema üzerinde alım yapacak, 1günlük ema'nın %10 altına düştüğünde stop olacak

_______________________________________________________________
SON GUNCELLEME - 20.07.2022 : 

+Margin için short alımı kapatıldı. (Önceden yapılmıştı)
+RSI_15_Robot'da ve margin_robot_long'da alım yaparken coinin hem btc hem de usdt karşısındaki değerine bakacak ve alım yapmak için bunlardan birisi min_rsi değeri altındayken diğerinin de rsi'ının 50 altında olması koşulu aranacak, satış yaparken de aynı şekilde hem btc hemde usdt ye bakacak
+%4 kar ettikten sonra tetiklenen ve %1 kaybedişinde satış yapar stoploss trigger i eklenip margin ve rsi15 robotlarına eklendi
_______________________________________________________________


YÜKLÜ => python 3.7.9 

Robot1 - RSI_4h:
+ALIŞ;
Altcoin/btc 30,60,120 lıklardan 1 tanesi ve 240 dk lık grafikte 20 altında ise  (yeni hali sadece 4 sa kontrol ediliyor)
ve hepsi 50 altında ise (yeni hali 30,1sa,4sa lik kontrol edilip 50 altında) 
ve btc/usdt wlliamR günlükte -50'den küçük ise al ,  
+SATIŞ;
Altcoin/btc 15,30,60,120 lıklardan 1 tanesi ve 240 dk lık grafikte 75 üzerinde ise  
ve hepsi 50 üzerinde ise 
Ve btc/usdt kar %2 üzerindeyse sat

Robot2 - RSI_15m:
ALIŞ; 15dk'ik Rsi 25'in altındaysa VE Btc Ema üzerindeyse al,  
SATIŞ; 15dk'ik Rsi 65'in üzerinde ise ve btc/usdt kar %2 üzerindeyse sat

Robot3 - Btc Margin 

ALIŞ; ema20d üzerindeyken sadece long, altındayken hem long hem short işlem açılır. Altcoin/btc 15dk'ik Rsi 25'in altındaysa al,  
SATIŞ; Altcoin/btc 15dk'ik Rsi 65'in üzerinde ise ve btc/usdt kar %2 üzerindeyse sat



Satış Modları : 
2 farklı satış stratejisi var.
1-) Hem manuel hem Rsi4h robotla alınanlar için uygulanan strateji olarak 2 katında yarısını ve sonraki 2 katlarında %10'u satılır. Minimum tutar a gelindiyse tamamı satılır
2-) Rsi15m ve Margin robotlarıyla alınanlarda sinyal gelmesi durumunda tamamı satılır.
Satış durumlarında Robot sinyali ile satış durumunda üzerinden 2 gün geçmeden tekrar satış yapılmaz

 Alış son onay : al sinyali verdiyse para birimi en son ne zaman alındı diye bakılır. son alımdan sonra 3 günden az süre geçtiyse veya Eğer son alım olduysa veya fark yukarı veya aşağı yönlü %5 ten az ise alınmayacak 

Satılan altcoinler ile usdt alınır. coinTargetToCollectbtc  seçili ise Btc için sinyal geldiğinde de kenardaki biriken usdt ile btc alınır.


Alım yaparken cd kontrolü yap. ilk alımda 1gün cd , 2.cide 2 , 3.cüde 3, 4cüde 4 gün cd ile geçtiğini kontrol et (cd gün sayısı = mevcut trade adeti * 2 )

