from django import forms


class CreateSchemaForm(forms.Form):
    """Form for creating a new schema."""
    name = forms.CharField(
        max_length=63,  # PostgreSQL identifier limit
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'schema_name'}),
        help_text="Schema name (alphanumeric and underscores only)"
    )
    
    def clean_name(self):
        """Validate schema name."""
        name = self.cleaned_data.get('name', '').strip()
        
        if not name:
            raise forms.ValidationError("Schema name cannot be empty")
        
        # Check for valid PostgreSQL identifier
        if not name.replace('_', '').isalnum():
            raise forms.ValidationError("Schema name can only contain letters, numbers, and underscores")
        
        # Check for reserved names
        system_schemas = {'pg_catalog', 'information_schema', 'pg_toast'}
        if name.lower() in system_schemas or name.lower().startswith('pg_'):
            raise forms.ValidationError(f"Cannot create system schema '{name}'")
        
        return name
