# Generated by Django 3.0.6 on 2022-01-22 14:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('binance', '0029_trade_indicatorresults'),
    ]

    operations = [
        migrations.AlterField(
            model_name='coin',
            name='isActive',
            field=models.BooleanField(default=True, help_text='Aktif mi ?', verbose_name='Aktif mi?'),
        ),
        migrations.AlterField(
            model_name='coin',
            name='name',
            field=models.TextField(help_text='Coin adı burada girilir.', max_length=100, null=True, verbose_name='Coin adı'),
        ),
        migrations.AlterField(
            model_name='coin',
            name='openToBuy',
            field=models.BooleanField(default=True, help_text='Alıma açık olup olmamasına burada karar verilir.', verbose_name='Alıma açık mı?'),
        ),
        migrations.AlterField(
            model_name='coin',
            name='preferredCompareCoinName',
            field=models.TextField(default='BTC', help_text='Karşılaştırılacak coin adı burada girilir.', max_length=100, verbose_name='Karşılaştırılacak coin adı'),
        ),
        migrations.AlterField(
            model_name='preferences',
            name='coinTargetToCollect',
            field=models.ForeignKey(help_text='Biriktirilmesi istenen para birimini seçiniz.', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='preferences_coinTargetToCollect', to='binance.Coin', verbose_name='Biriktirilecek para birimi'),
        ),
        migrations.AlterField(
            model_name='preferences',
            name='commonTotalStartMoneyAsTL',
            field=models.FloatField(default=0, help_text='Toplam yatırılan paranın tl olarak karşılığı', verbose_name='Başlangıç Toplam TL'),
        ),
        migrations.AlterField(
            model_name='preferences',
            name='commonTotalStartMoneyAsUSDT',
            field=models.FloatField(default=0, help_text='Toplam yatırılan paranın usdt olarak karşılığı', verbose_name='Başlangıç Toplam USDT'),
        ),
        migrations.AlterField(
            model_name='preferences',
            name='cooldownForNewBuyFromSameCoin',
            field=models.IntegerField(default=3, help_text='Yeni alım yapmak için minimum x gün geçmeli', verbose_name='Aynı coinin alımı için geçmesi gereken gün'),
        ),
        migrations.AlterField(
            model_name='preferences',
            name='cooldownForNewSellFromSameCoin',
            field=models.IntegerField(default=3, help_text='Yeni satış yapmak için minimum x gün geçmeli', verbose_name='Aynı coinin satışı için geçmesi gereken gün'),
        ),
        migrations.AlterField(
            model_name='preferences',
            name='isBuyingModeActive',
            field=models.BooleanField(default=True, help_text='Fırsat bulduğunda coin alışı yapsın mı?', verbose_name='Alış modu açık mı? '),
        ),
        migrations.AlterField(
            model_name='preferences',
            name='isControlForPanicMode',
            field=models.BooleanField(default=True, help_text='Bu özellik açıldıysa btc son 24 saatte %10 ve üzerinde düşüş yaparsa ve Ema aşağıda olursa (Ema 20 günlük ortalama altında ise) panik modu devreye girer tüm pozisyonları kapatıp usdt ye dönülür .  ', verbose_name='Panik moduna otomatik giriş kontrolü açık mı?'),
        ),
        migrations.AlterField(
            model_name='preferences',
            name='isEmaControlActiveForBuying',
            field=models.BooleanField(default=True, help_text='Alım yaparken Ema kontrolü aktif mi ?(Varsayılan olarak BTC nin 20 günlük ortalama üzerinde olması şartı aranır)', verbose_name='Ema kontrolü (Alım yaparken)'),
        ),
        migrations.AlterField(
            model_name='preferences',
            name='isPanicModeActive',
            field=models.BooleanField(default=True, help_text='Panik modu şuan açık mı?  (Panik modu açıldığında Alış ve satış modları kapalı ya çekilir ve kapatıldığında diğerleri açılır)', verbose_name='Panik modu şuan açık mı? '),
        ),
        migrations.AlterField(
            model_name='preferences',
            name='isSellingModeActive',
            field=models.BooleanField(default=True, help_text='Fırsat bulduğunda coin satışı yapsın mı?', verbose_name='Satış modu açık mı? '),
        ),
        migrations.AlterField(
            model_name='preferences',
            name='isSellingOneStepIfDoesntPassEMAControlModeActive',
            field=models.BooleanField(default=True, help_text='Varsayılan olarak BTC nin 20 günlük ortalamanın altında kalması durumunda satış yapar', verbose_name='EMA kontrolünden geçmediyse artıda olan tradelerin yarısını satsın mı?'),
        ),
        migrations.AlterField(
            model_name='preferences',
            name='maxLimitForRobotAsUsdt',
            field=models.FloatField(default=0, help_text='Robotun kullanacağı maksimum usdt tutarı', verbose_name='Robot bütçe'),
        ),
        migrations.AlterField(
            model_name='preferences',
            name='maxOpenTradeCountForSameCoin',
            field=models.IntegerField(default=2, help_text='Aynı coinden en fazla kaç adet açık trade bulundurabilir ?', verbose_name='Aynı coin adet limiti'),
        ),
        migrations.AlterField(
            model_name='preferences',
            name='maxRSI',
            field=models.IntegerField(default=80, help_text='Max RSI (Varsayılan değeri 80)', verbose_name='Max RSI'),
        ),
        migrations.AlterField(
            model_name='preferences',
            name='midRSI',
            field=models.IntegerField(default=50, help_text='Mid RSI (Varsayılan değeri 50)', verbose_name='Mid RSI'),
        ),
        migrations.AlterField(
            model_name='preferences',
            name='minRSI',
            field=models.IntegerField(default=20, help_text='Min RSI (Varsayılan değeri 20)', verbose_name='Min RSI'),
        ),
        migrations.AlterField(
            model_name='preferences',
            name='targetPercentageForBuying',
            field=models.IntegerField(default=5, help_text='Aynı coinden alım yapılırken yeni fiyatın önceki alım fiyatından minimum yüzde x kadar ucuz olması gerekir', verbose_name='Alış yapmak için beklenen min fark'),
        ),
        migrations.AlterField(
            model_name='preferences',
            name='targetPercentageForSelling',
            field=models.IntegerField(default=5, help_text='Satış yapılırken minimum yüzde x kadar kar edilmiş olması gerekir', verbose_name='Satış yapmak için beklenen min fark'),
        ),
        migrations.AlterField(
            model_name='preferences',
            name='williamR',
            field=models.IntegerField(default=-50, help_text='WilliamR (Varsayılan değeri -50)', verbose_name='WilliamR'),
        ),
    ]
