from django.urls import path
from .chat_views import chat_history, claim_suggestion, ia_chat, ia_provider_info
from .help_views import ia_help
from .views import (
    set_backupUML,
    get_backupUML,
    analyze_uml_image,
    analyze_uml_audio,
    generar_flutter,
    export_xmi,
    import_xmi,
    get_room_activity,
)


urlpatterns = [
    path("set_backup_uml/<uuid:room_id>/", set_backupUML, name="backup_uml-id"),
    path("get_backup_uml/<uuid:room_id>/", get_backupUML, name="backup_uml-id"),
    path("uml_from_image/", analyze_uml_image, name="uml-from-image"),
    path("uml_from_audio/", analyze_uml_audio, name="uml-from-audio"),

    path("generar_flutter/", generar_flutter, name="generar-flutter"),

    path("xmi/export/", export_xmi, name="xmi-export"),
    path("xmi/import/", import_xmi, name="xmi-import"),
    path("rooms/<str:room>/activity/", get_room_activity, name="room-activity"),
    path("rooms/<str:room>/chat/", chat_history, name="room-chat-history"),
    path("rooms/<str:room>/ia/chat/", ia_chat, name="room-ia-chat"),
    path(
        "rooms/<str:room>/activity/<int:event_id>/apply/<int:index>/",
        claim_suggestion,
        name="room-claim-suggestion",
    ),
    path("ia/provider/", ia_provider_info, name="ia-provider"),
    path("ia/help/", ia_help, name="ia-help"),
]
