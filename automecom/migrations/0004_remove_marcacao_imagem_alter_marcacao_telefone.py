# Generated by Django 5.1.3 on 2025-04-10 10:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('automecom', '0003_marcacao_imagem'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='marcacao',
            name='imagem',
        ),
        migrations.AlterField(
            model_name='marcacao',
            name='telefone',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
