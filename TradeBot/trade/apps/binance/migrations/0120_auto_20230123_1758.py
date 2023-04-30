# Generated by Django 3.0.6 on 2023-01-23 14:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('binance', '0119_auto_20230123_1743'),
    ]

    operations = [
        migrations.RenameField(
            model_name='preferences',
            old_name='isRobot15mWithRealMarginActive',
            new_name='isRobot15mWITHRealMarginActive',
        ),
        migrations.RenameField(
            model_name='preferences',
            old_name='maxLimitForRobot15mWithRealMarginAsUsdt',
            new_name='maxLimitForRobot15mWITHRealMarginAsUsdt',
        ),
        migrations.AlterField(
            model_name='preferences',
            name='robot15mWITHRealMarginNegativeSellCount',
            field=models.IntegerField(default=0, verbose_name='Robot RSI_15m_WITHRealMargin zararına satış sayısı'),
        ),
        migrations.AlterField(
            model_name='preferences',
            name='robot15mWITHRealMarginPositiveSellCount',
            field=models.IntegerField(default=0, verbose_name='Robot RSI_15m_WITHRealMargin karlı satış sayısı'),
        ),
        migrations.AlterField(
            model_name='preferences',
            name='robot15mWITHRealMarginTotalBuyCount',
            field=models.IntegerField(default=0, verbose_name='Robot RSI_15m_WITHRealMargin toplam alış sayısı'),
        ),
    ]