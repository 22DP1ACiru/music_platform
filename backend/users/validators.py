import re # For regex-based checks
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _ # For translatable messages

class UppercaseValidator:
    def validate(self, password, user=None):
        if not re.search(r'[A-Z]', password):
            raise ValidationError(
                _("Password must contain at least 1 uppercase letter."),
                code='password_no_upper',
            )

    def get_help_text(self):
        return _("Password must contain at least 1 uppercase letter.")

class NumberValidator:
    def validate(self, password, user=None):
        if not re.search(r'[0-9]', password):
            raise ValidationError(
                _("Password must contain at least 1 number."),
                code='password_no_number',
            )

    def get_help_text(self):
        return _("Password must contain at least 1 number.")

class SymbolValidator:
    def validate(self, password, user=None):
        # Includes common symbols. Adjust regex [!@#$%^&*()_+-=[]{};':"\\|,.<>/?~`] as needed.
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?~`]', password):
            raise ValidationError(
                _("Password must contain at least 1 non-alphanumeric character (symbol)."),
                code='password_no_symbol',
            )

    def get_help_text(self):
        return _("Password must contain at least 1 non-alphanumeric character (symbol).")