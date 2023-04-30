# Generated by Django 3.0.6 on 2022-03-19 16:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('binance', '0073_auto_20220319_0311'),
    ]

    operations = [
        migrations.AddField(
            model_name='preferences',
            name='isControlEmaForSellingPreviousRobot15mTrades',
            field=models.BooleanField(default=True, verbose_name='EMA nın %5 altındaysa elinde RSI_15m robot ile alınmış coinler varsa sat'),
        ),
        migrations.AddField(
            model_name='preferences',
            name='isRobot15mActive',
            field=models.BooleanField(default=False, help_text='Ema üzerindeyken alım ve satım yapan, ema nın %5 altındayken stop olan RSI_15m robot çalışıyor mu?', verbose_name='RSI_15m robotu açık mı?'),
        ),
        migrations.AddField(
            model_name='preferences',
            name='lastRobot15mWorkingDate',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Son RSI_15m robotun çalışma tarihi'),
        ),
        migrations.AlterField(
            model_name='trade',
            name='strategy',
            field=models.TextField(blank=True, default='', help_text='Örnek : Margin_RSI_15m , RSI_15m , RSI_4h , Specified_Priority_Purchases , Manuel_Webpage_Action', max_length=100, null=True, verbose_name='Alış ve Satış Stratejisi'),
        ),
    ]