from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ticketing', '0002_cart_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='is_published',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='event',
            name='is_published',
            field=models.BooleanField(default=True),
        ),
    ]
