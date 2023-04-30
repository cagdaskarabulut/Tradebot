# Generated by Django 3.0.6 on 2023-01-24 10:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('binance', '0122_auto_20230124_1131'),
    ]

    operations = [
        migrations.AddField(
            model_name='coin',
            name='moveRSI15mWITHRealMarginComeBackRSIValueForBtc',
            field=models.IntegerField(default=0, help_text='RSI15m WITHRealMargin için RSI ın btc karşısındaki değeri düştükten sonra x değer kadar yükseldiğinde satın alma siyali gelir.', verbose_name='Kontrol RSI15mBTC WITHRealMargin'),
        ),
        migrations.AddField(
            model_name='coin',
            name='moveRSI15mWITHRealMarginComeBackRSIValueForUsdt',
            field=models.IntegerField(default=0, help_text='RSI15m WITHRealMargin için RSI ın usdt karşısındaki değeri düştükten sonra x değer kadar yükseldiğinde satın alma siyali gelir.', verbose_name='Kontrol RSI15mUSDT WITHRealMargin'),
        ),
    ]