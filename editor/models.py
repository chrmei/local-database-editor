from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from cryptography.fernet import Fernet
import base64
import hashlib


def _get_encryption_key():
    """Generate a consistent encryption key from Django SECRET_KEY."""
    secret = settings.SECRET_KEY.encode('utf-8')
    # Use SHA256 to get a 32-byte key, then base64 encode for Fernet
    key = hashlib.sha256(secret).digest()
    return base64.urlsafe_b64encode(key)


class EncryptedCharField(models.CharField):
    """A CharField that encrypts values before storing and decrypts when reading."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cipher = Fernet(_get_encryption_key())
    
    def from_db_value(self, value, expression, connection):
        """Decrypt value when reading from database."""
        if value is None:
            return value
        try:
            return self._cipher.decrypt(value.encode()).decode()
        except Exception:
            # If decryption fails, return as-is (for migration compatibility)
            return value
    
    def to_python(self, value):
        """Return value as-is (already decrypted by from_db_value)."""
        return value
    
    def get_prep_value(self, value):
        """Encrypt value before storing in database."""
        if value is None:
            return value
        return self._cipher.encrypt(value.encode()).decode()


class DatabaseConfig(models.Model):
    """User-specific database configuration."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='database_configs')
    name = models.CharField(max_length=255, help_text="Display name for this database")
    alias = models.CharField(max_length=100, help_text="Internal alias (auto-generated)")
    host = models.CharField(max_length=255)
    port = models.IntegerField(default=5432)
    database = models.CharField(max_length=255)
    schema = models.CharField(max_length=255, help_text="Schema name within the database")
    username = models.CharField(max_length=255)
    password = EncryptedCharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [['user', 'alias']]
        ordering = ['name']
        # Ensure unique database+schema combination per user
        constraints = [
            models.UniqueConstraint(fields=['user', 'database', 'schema'], name='unique_user_database_schema')
        ]
    
    def __str__(self):
        return f"{self.name} ({self.user.username})"
    
    def save(self, *args, **kwargs):
        """Generate unique alias if not set."""
        if not self.alias:
            if self.pk:
                # If pk exists but alias doesn't, generate from pk
                self.alias = f"user_{self.user_id}_db_{self.pk}"
            else:
                # For new objects, save first to get pk, then update alias
                super().save(*args, **kwargs)
                if not self.alias:
                    self.alias = f"user_{self.user_id}_db_{self.pk}"
                    super().save(update_fields=['alias'])
                return
        super().save(*args, **kwargs)
    
    def get_connection_config(self):
        """Return Django database connection config dict with all required Django settings."""
        from django.conf import settings
        return {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': self.database,
            'USER': self.username,
            'PASSWORD': self.password,  # Already decrypted by EncryptedCharField
            'HOST': self.host,
            'PORT': str(self.port),
            'OPTIONS': {'connect_timeout': 10},
            # Required Django database settings
            'ATOMIC_REQUESTS': False,  # Required by Django's connection handler
            'TIME_ZONE': getattr(settings, 'TIME_ZONE', None),  # Use Django's TIME_ZONE setting
            'AUTOCOMMIT': True,  # Standard PostgreSQL behavior
            'CONN_HEALTH_CHECKS': False,  # Connection health checks (Django 4.2+)
            'CONN_MAX_AGE': 0,  # Connection max age in seconds (0 = close after each request)
        }
