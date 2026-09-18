from django.urls import path
from .views import (
    GenerateUMLView,
    set_backupUML,
    get_backupUML,
    analyze_uml_image,
    generar_flutter,
    export_xmi,
    import_xmi,
)


urlpatterns = [
    path('chatbot/', GenerateUMLView.as_view(), name='generate-uml'),
    path("set_backup_uml/<uuid:room_id>/", set_backupUML, name="backup_uml-id"),
    path("get_backup_uml/<uuid:room_id>/", get_backupUML, name="backup_uml-id"),
    path("uml_from_image/", analyze_uml_image, name="uml-from-image"),

    path("generar_flutter/", generar_flutter, name="generar-flutter"),

    path("xmi/export/", export_xmi, name="xmi-export"),
    path("xmi/import/", import_xmi, name="xmi-import"),
]
