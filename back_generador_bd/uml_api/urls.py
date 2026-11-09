from django.urls import path
from .auth_views import (
    auth_config,
    auth_me,
    auth_request_code,
    auth_verify,
    my_rooms_view,
    room_access_view,
    room_delete_view,
    room_invite,
    room_members_view,
    room_settings_view,
)
from .chat_views import chat_history, claim_suggestion, ia_chat, ia_provider_info, room_ia_provider
from .help_views import ia_help
from .views import (
    set_backupUML,
    get_backupUML,
    analyze_uml_image,
    analyze_uml_audio,
    generar_flutter,
    generar_todo,
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
    path("generar_todo/", generar_todo, name="generar-todo"),

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
    path("rooms/<str:room>/ia/provider/", room_ia_provider, name="room-ia-provider"),
    path("rooms/<str:room>/invite/", room_invite, name="room-invite"),
    path("rooms/", my_rooms_view, name="my-rooms"),
    path("rooms/<str:room>/", room_delete_view, name="room-delete"),
    path("rooms/<str:room>/access/", room_access_view, name="room-access"),
    path("rooms/<str:room>/settings/", room_settings_view, name="room-settings"),
    path("rooms/<str:room>/members/", room_members_view, name="room-members"),
    path("auth/config/", auth_config, name="auth-config"),
    path("auth/code/", auth_request_code, name="auth-code"),
    path("auth/verify/", auth_verify, name="auth-verify"),
    path("auth/me/", auth_me, name="auth-me"),
    path("ia/provider/", ia_provider_info, name="ia-provider"),
    path("ia/help/", ia_help, name="ia-help"),
]
