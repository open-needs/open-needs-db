import importlib
import logging
from sqladmin import Admin, ModelView

from open_needs_server.extensions.base import ONSExtension
from open_needs_server.database import engine
from open_needs_server.config import settings
from open_needs_server.version import VERSION

from open_needs_server.extensions.organization.models import OrganizationModel

log = logging.getLogger(__name__)

import types


class OnsAdminExtension(ONSExtension):
    """Extension for loading SqlAlchemyAdmin"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.version = VERSION

        self.admin = Admin(self.ons_app, engine)

        for admin_model in self._get_models():
            self.admin.add_view(admin_model)

    def _get_models(self):
        models = []
        for admin_conf in settings.admin:
            model_str = settings.admin[admin_conf]["model"]

            try:
                module_str, class_str = model_str.split(":")
                module = importlib.import_module(module_str)
                clazz = getattr(module, class_str)
            except Exception as e:
                raise OnsAdminExtension(
                    f'Problems loading model "model_str". Cause: {e}'
                )

            columns = settings.admin[admin_conf].get("columns", ["id"])
            name = settings.admin[admin_conf].get("name", model_str)
            name_plural = settings.admin[admin_conf].get("name_plural", f"{name}s")
            icon = settings.admin[admin_conf].get("icon", "fa-solid fa-user")

            clazz_columns = [getattr(clazz, x) for x in columns]

            new_class = types.new_class(
                name=f"{class_str}Admin",
                bases=(ModelView,),
                kwds={"model": clazz},
                exec_body=lambda ns: ns.update(
                    {
                        "column_list": clazz_columns,
                        "name": name,
                        "name_plural": name_plural,
                        "icon": icon,
                    }
                ),
            )

            models.append(new_class)

        return models


class OnsAdminException(BaseException):
    """Any kind of Exception in he ONS Admin Extension"""
