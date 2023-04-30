# Generated by Django 3.0.6 on 2022-03-19 16:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('binance', '0074_auto_20220319_1900'),
    ]

    operations = [
        migrations.AddField(
            model_name='preferences',
            name='maxOpenTradeCountForRobot15m',
            field=models.IntegerField(default=2, help_text='RSI_15m işlem için aynı coin adet limiti', verbose_name='RSI_15m işlem için aynı coin adet limiti'),
        ),
        migrations.AlterField(
            model_name='preferences',
            name='maxOpenTradeCountForMargin',
            field=models.IntegerField(default=5, help_text='Margin_RSI_15m Long işlem için aynı coin adet limiti', verbose_name='Margin_RSI_15m Long işlem için aynı coin adet limiti'),
        ),
        migrations.AlterField(
            model_name='preferences',
            name='minRSIForLong',
            field=models.IntegerField(default=25, help_text='Margin_RSI_15m ve RSI_15m Long için Min RSI (Varsayılan değeri 20)', verbose_name='Margin_RSI_15m ve RSI_15m Long Min RSI'),
        ),
    ]