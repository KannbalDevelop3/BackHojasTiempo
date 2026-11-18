import re
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from django.conf import settings
from api.models import AuditLog  # ajusta al nombre real de tu app

class AuditMiddleware(MiddlewareMixin):

    ID_PATTERN = re.compile(r'/(\d+)(?:/|$)')

    def process_response(self, request, response):
        try:
            prefix = getattr(settings, "AUDIT_PREFIX", "/api/")
            if not request.path.startswith(prefix):
                return response

            if request.method not in ["POST", "PUT", "PATCH", "DELETE"]:
                return response

            usuario = getattr(request, "user", None)
            if usuario and not usuario.is_authenticated:
                usuario = None

            match = self.ID_PATTERN.search(request.path)
            id_obj = match.group(1) if match else None

            AuditLog.objects.create(
                usuario=usuario,
                metodo=request.method,
                endpoint=request.path,
                id_obj=id_obj,
                exito=(200 <= response.status_code < 300),
                ip_addr=(request.META.get("REMOTE_ADDR") or request.META.get("HTTP_X_FORWARDED_FOR")),
                user_agent=request.META.get("HTTP_USER_AGENT"),
                fecha=timezone.now(),
            )
        except Exception as e:
            print(f"[AuditMiddleware] Error registrando auditoría: {e}")

        return response
