from django import forms
from .models import DatabaseConfig
from .db_manager import test_database_connection


class DatabaseConfigForm(forms.ModelForm):
    """Form for creating and editing database configurations."""
    
    class Meta:
        model = DatabaseConfig
        fields = ['name', 'host', 'port', 'database', 'schema', 'username', 'password']
        widgets = {
            'password': forms.PasswordInput(render_value=True),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'host': forms.TextInput(attrs={'class': 'form-control'}),
            'port': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 65535}),
            'database': forms.TextInput(attrs={'class': 'form-control'}),
            'schema': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'public'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # If editing, don't show password field unless user wants to change it
        if self.instance and self.instance.pk:
            self.fields['password'].required = False
            self.fields['password'].help_text = "Leave blank to keep existing password"
    
    def clean_port(self):
        """Validate port is in valid range."""
        port = self.cleaned_data.get('port')
        if port is not None:
            if port < 1 or port > 65535:
                raise forms.ValidationError("Port must be between 1 and 65535")
        return port
    
    def clean_schema(self):
        """Validate schema name."""
        schema = self.cleaned_data.get('schema', '').strip()
        if not schema:
            raise forms.ValidationError("Schema name is required")
        
        # Check for valid PostgreSQL identifier
        if not schema.replace('_', '').replace('-', '').isalnum():
            raise forms.ValidationError("Schema name can only contain letters, numbers, underscores, and hyphens")
        
        # Check for reserved names
        system_schemas = {'pg_catalog', 'information_schema', 'pg_toast'}
        if schema.lower() in system_schemas or schema.lower().startswith('pg_'):
            raise forms.ValidationError(f"Cannot use system schema '{schema}'")
        
        return schema
    
    def clean(self):
        """Validate connection and ensure unique database+schema per user."""
        cleaned_data = super().clean()
        
        # Check for unique name per user
        name = cleaned_data.get('name')
        if name and self.user:
            qs = DatabaseConfig.objects.filter(user=self.user, name=name)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError({'name': 'You already have a database with this name.'})
        
        # Check for unique database+schema combination per user
        database = cleaned_data.get('database')
        schema = cleaned_data.get('schema')
        if database and schema and self.user:
            qs = DatabaseConfig.objects.filter(user=self.user, database=database, schema=schema)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError({
                    'schema': f'You already have a connection to database "{database}" with schema "{schema}".'
                })
        
        # Test connection - always test for new records, or if password provided, or if connection details changed
        password = cleaned_data.get('password')
        is_new = not (self.instance and self.instance.pk)
        
        # Determine which password to use for testing
        if password:
            test_password = password
        elif not is_new:
            # Editing without password change - use existing password
            test_password = self.instance.password
        else:
            # New record without password
            test_password = None
        
        # Test connection if we have a password and all required fields
        if test_password:
            host = cleaned_data.get('host')
            port = cleaned_data.get('port')
            database = cleaned_data.get('database')
            schema = cleaned_data.get('schema')
            username = cleaned_data.get('username')
            
            if all([host, port, database, username, schema]):
                # Test connection and verify schema exists in one call
                success, error = test_database_connection(host, port, database, username, test_password, schema=schema)
                if not success:
                    # Check if error is schema-related
                    if 'does not exist' in error.lower() and 'schema' in error.lower():
                        raise forms.ValidationError({'schema': error})
                    else:
                        raise forms.ValidationError(f"Connection test failed: {error}")
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save the form, handling password updates."""
        password = self.cleaned_data.get('password')
        password_provided = password and password.strip()
        is_new = not (self.instance and self.instance.pk)
        
        # Remove password from cleaned_data if not provided and editing
        # This prevents Django from overwriting the existing password with empty string
        if not is_new and not password_provided:
            self.cleaned_data.pop('password', None)
        
        instance = super().save(commit=False)
        instance.user = self.user
        
        # Handle password explicitly
        if password_provided:
            instance.password = password
        elif is_new:
            raise forms.ValidationError("Password is required for new databases")
        # If editing and no password provided, password attribute is not set, so existing value is preserved
        
        if commit:
            # If editing without password change, exclude password from update_fields
            if not is_new and not password_provided:
                instance.save(update_fields=[f for f in self.Meta.fields if f != 'password'] + ['user', 'updated_at'])
            else:
                instance.save()
        
        return instance
