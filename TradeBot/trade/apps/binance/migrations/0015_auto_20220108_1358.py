# Generated by Django 3.0.6 on 2022-01-08 13:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('binance', '0014_auto_20220107_0929'),
    ]

    operations = [
        migrations.AddField(
            model_name='preferences',
            name='maxRSI',
            field=models.IntegerField(default=80),
        ),
        migrations.AddField(
            model_name='preferences',
            name='midRSI',
            field=models.IntegerField(default=50),
        ),
        migrations.AddField(
            model_name='preferences',
            name='minRSI',
            field=models.IntegerField(default=20),
        ),
        migrations.AddField(
            model_name='preferences',
            name='williamR',
            field=models.IntegerField(default=-50),
        ),
    ]