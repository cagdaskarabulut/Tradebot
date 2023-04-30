# Generated by Django 3.0.6 on 2022-03-29 08:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('binance', '0085_auto_20220329_1042'),
    ]

    operations = [
        migrations.AddField(
            model_name='preferences',
            name='lossLimitForRobot15m',
            field=models.FloatField(default=-100, help_text='Robotun bu zarar altına geldiğinde komple çalışmayacak. İstenirse sonradan arttırılabilir.', verbose_name='Robot RSI_15m zarar limiti'),
        ),
        migrations.AddField(
            model_name='preferences',
            name='lossLimitForRobot4h',
            field=models.FloatField(default=-100, help_text='Robotun bu zarar altına geldiğinde komple çalışmayacak. İstenirse sonradan arttırılabilir.', verbose_name='Robot RSI_4h zarar limiti'),
        ),
        migrations.AddField(
            model_name='preferences',
            name='lossLimitForRobotMargin',
            field=models.FloatField(default=-100, help_text='Robotun bu zarar altına geldiğinde komple çalışmayacak. İstenirse sonradan arttırılabilir.', verbose_name='Robot Margin zarar limiti'),
        ),
    ]