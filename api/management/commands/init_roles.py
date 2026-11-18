# api/management/commands/init_roles.py
import json
from pathlib import Path
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.apps import apps

class Command(BaseCommand):
    help = "Crea/actualiza grupos y permisos desde roles_config.json (idempotente)."

    def add_arguments(self, parser):
        parser.add_argument("--file", type=str, default="api/roles_lite.json")

    def handle(self, *args, **opts):
        file_path = Path(opts["file"])
        data = json.loads(file_path.read_text(encoding="utf-8"))
        for g in data.get("groups", []):
            group, _ = Group.objects.get_or_create(name=g["name"])
            perms_to_set = []
            for block in g.get("permissions", []):
                app_label = block["app"]
                model_name = block["model"]
                codenames = block["codenames"]

                # modelo
                try:
                    model = apps.get_model(app_label, model_name)
                except LookupError:
                    self.stderr.write(self.style.WARNING(f"{app_label}.{model_name} no encontrado"))
                    continue

                ct = ContentType.objects.get_for_model(model)
                for code in codenames:
                    try:
                        perm = Permission.objects.get(content_type=ct, codename=code)
                        perms_to_set.append(perm)
                    except Permission.DoesNotExist:
                        self.stderr.write(self.style.WARNING(
                            f"Permiso faltante: {app_label}.{model._meta.model_name}:{code} (¿migrate?)."
                        ))
            group.permissions.set(list({p.id: p for p in perms_to_set}.values()))
        self.stdout.write(self.style.SUCCESS("Roles/permisos sincronizados"))
