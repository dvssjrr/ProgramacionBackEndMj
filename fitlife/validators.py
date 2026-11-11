"""Validaciones de seguridad específicas para las contraseñas de FitLife."""

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class FitLifePasswordComplexityValidator:
    """Exige minúsculas, mayúsculas, números y símbolos en cada contraseña."""

    def validate(self, password, user=None):
        requirements = (
            (any(character.islower() for character in password), _("al menos una letra minúscula")),
            (any(character.isupper() for character in password), _("al menos una letra mayúscula")),
            (any(character.isdigit() for character in password), _("al menos un número")),
            (any(not character.isalnum() for character in password), _("al menos un símbolo")),
        )
        missing = [description for valid, description in requirements if not valid]
        if missing:
            raise ValidationError(
                _("La contraseña debe incluir: %(requirements)s."),
                code="password_complexity",
                params={"requirements": ", ".join(missing)},
            )

    def get_help_text(self):
        return _("Incluye al menos una minúscula, una mayúscula, un número y un símbolo.")
