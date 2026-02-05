# Generated manually - add schema field to DatabaseConfig model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('editor', '0001_initial'),
    ]

    operations = [
        # Add schema field as nullable first
        migrations.AddField(
            model_name='databaseconfig',
            name='schema',
            field=models.CharField(help_text='Schema name within the database', max_length=255, null=True, blank=True),
        ),
        # Data migration: set 'public' as default for existing records
        migrations.RunPython(
            lambda apps, schema_editor: apps.get_model('editor', 'DatabaseConfig').objects.filter(schema__isnull=True).update(schema='public'),
            reverse_code=migrations.RunPython.noop,
        ),
        # Make schema field non-nullable
        migrations.AlterField(
            model_name='databaseconfig',
            name='schema',
            field=models.CharField(help_text='Schema name within the database', max_length=255),
        ),
        # Add unique constraint for user+database+schema combination
        migrations.AddConstraint(
            model_name='databaseconfig',
            constraint=models.UniqueConstraint(fields=['user', 'database', 'schema'], name='unique_user_database_schema'),
        ),
    ]
