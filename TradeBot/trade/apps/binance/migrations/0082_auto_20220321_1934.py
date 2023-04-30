# Generated by Django 3.0.6 on 2022-03-21 16:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('binance', '0081_auto_20220320_2331'),
    ]

    operations = [
        migrations.AddField(
            model_name='preferences',
            name='temp_draftUsdtDiffAction',
            field=models.FloatField(default=0, verbose_name='Takip Usdt'),
        ),
        migrations.AlterField(
            model_name='coin',
            name='trustRate',
            field=models.IntegerField(default=3),
        ),
    ]
