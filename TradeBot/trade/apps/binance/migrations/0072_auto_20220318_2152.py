# Generated by Django 3.0.6 on 2022-03-18 18:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('binance', '0071_preferences_temp_isrobotworkingnow'),
    ]

    operations = [
        migrations.AddField(
            model_name='preferences',
            name='robot15mResultHistoryAsUsdt',
            field=models.FloatField(default=0, help_text='Robot RSI_15m geçmişten bu yana alım satımlardan yapılan kar zarar durumu', verbose_name='Robot RSI_15m geçmişten bu yana alım satımlardan yapılan kar zarar durumu'),
        ),
        migrations.AlterField(
            model_name='preferences',
            name='cooldownAsHoursForNewBuyFromSameCoinBaseForMargin',
            field=models.IntegerField(default=12, help_text='Margin_RSI_15m ve RSI_15m Long için yeni alım yapmak için minimum (x * eldeki adet) kadar saat geçmeli', verbose_name='Margin_RSI_15m ve RSI_15m Long ve Short için taban cooldown saat sayisi'),
        ),
        migrations.AlterField(
            model_name='preferences',
            name='maxOpenTradeCountForMargin',
            field=models.IntegerField(default=5, help_text='Margin_RSI_15m ve RSI_15m Long işlem için aynı coin adet limiti', verbose_name='Margin_RSI_15m ve RSI_15m Long işlem için aynı coin adet limiti'),
        ),
        migrations.AlterField(
            model_name='preferences',
            name='maxRSIForLong',
            field=models.IntegerField(default=65, help_text='Margin_RSI_15m ve RSI_15m Long için Max RSI (Varsayılan değeri 65)', verbose_name='Margin_RSI_15m ve RSI_15m Long Max RSI'),
        ),
        migrations.AlterField(
            model_name='preferences',
            name='maxRSIForShort',
            field=models.IntegerField(default=70, help_text='Margin_RSI_15m Short için Max RSI (Varsayılan değeri 70)', verbose_name='Margin_RSI_15m Short Max RSI'),
        ),
        migrations.AlterField(
            model_name='preferences',
            name='minRSIForLong',
            field=models.IntegerField(default=20, help_text='Margin_RSI_15m ve RSI_15m Long için Min RSI (Varsayılan değeri 20)', verbose_name='Margin_RSI_15m ve RSI_15m Long Min RSI'),
        ),
        migrations.AlterField(
            model_name='preferences',
            name='minRSIForShort',
            field=models.IntegerField(default=30, help_text='Margin_RSI_15m Short için Min RSI (Varsayılan değeri 30)', verbose_name='Margin_RSI_15m Short Min RSI'),
        ),
        migrations.AlterField(
            model_name='preferences',
            name='robotResultHistoryAsUsdt',
            field=models.FloatField(default=0, help_text='Robot RSI_4h geçmişten bu yana alım satımlardan yapılan kar zarar durumu', verbose_name='Robot RSI_4h geçmişten bu yana alım satımlardan yapılan kar zarar durumu'),
        ),
        migrations.AlterField(
            model_name='preferences',
            name='stopPercentageForSellingForMargin',
            field=models.IntegerField(default=-10, help_text='Margin_RSI_15m ve RSI_15m Long için zarar kes yapılacak yüzdelik oran', verbose_name='Margin_RSI_15m ve RSI_15m Long için zarar kes yapılacak yüzdelik oran'),
        ),
        migrations.AlterField(
            model_name='preferences',
            name='targetPercentageForSellingForMargin',
            field=models.IntegerField(default=2, help_text='Margin_RSI_15m ve RSI_15m Long veya Short için Satış yapılırken minimum yüzde x kadar kar edilmiş olması gerekir', verbose_name='Margin_RSI_15m ve RSI_15m Long veya Short için Satış yapmak için beklenen min fark'),
        ),
    ]
