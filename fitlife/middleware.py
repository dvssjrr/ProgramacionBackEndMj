"""Aísla sesiones de pestañas mediante prefijos de URL y cookies propias."""

import re
import uuid

from django.conf import settings
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.urls import set_script_prefix


TAB_PATH = re.compile(r"^/sesion/([0-9a-f]{32})(/.*|)$")


class TabSessionMiddleware:
    """Asigna una sesión a cada URL de pestaña sin cambiar las credenciales."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, "TAB_SESSION_ISOLATION", False):
            return self.get_response(request)

        match = TAB_PATH.match(request.path_info)
        if not match:
            if request.path_info.startswith(("/static/", "/.well-known/")):
                return self.get_response(request)
            if request.method not in {"GET", "HEAD"}:
                return HttpResponseBadRequest("Abre esta página desde una pestaña de FitLife.")
            tab_id = uuid.uuid4().hex
            return HttpResponseRedirect(f"/sesion/{tab_id}{request.get_full_path()}")

        tab_id, path_info = match.groups()
        prefix = f"/sesion/{tab_id}"
        request.META["SCRIPT_NAME"] = prefix
        request.META["PATH_INFO"] = path_info or "/"
        request.path_info = path_info or "/"
        request.path = f"{prefix}{request.path_info}"
        request.fitlife_tab_id = tab_id

        # Django usa nombres estándar; se mapean a cookies únicas de esta pestaña.
        request.COOKIES = request.COOKIES.copy()
        session_cookie = settings.SESSION_COOKIE_NAME
        csrf_cookie = settings.CSRF_COOKIE_NAME
        session_name = f"{session_cookie}_{tab_id}"
        csrf_name = f"{csrf_cookie}_{tab_id}"
        request.COOKIES.pop(session_cookie, None)
        request.COOKIES.pop(csrf_cookie, None)
        if session_name in request.COOKIES:
            request.COOKIES[session_cookie] = request.COOKIES[session_name]
        if csrf_name in request.COOKIES:
            request.COOKIES[csrf_cookie] = request.COOKIES[csrf_name]

        previous_prefix = settings.FORCE_SCRIPT_NAME
        set_script_prefix(f"{prefix}/")
        try:
            response = self.get_response(request)
        finally:
            set_script_prefix(previous_prefix or "/")

        self._rename_cookie(response, session_cookie, session_name)
        self._rename_cookie(response, csrf_cookie, csrf_name)
        return response

    @staticmethod
    def _rename_cookie(response, old_name, new_name):
        """Renombra la cookie estándar conservando sus atributos de seguridad."""
        morsel = response.cookies.get(old_name)
        if morsel is None:
            return
        value = morsel.value
        coded_value = morsel.coded_value
        attributes = dict(morsel.items())
        del response.cookies[old_name]
        response.cookies[new_name] = value
        new_morsel = response.cookies[new_name]
        new_morsel.set(new_name, value, coded_value)
        for key, attribute in attributes.items():
            new_morsel[key] = attribute
