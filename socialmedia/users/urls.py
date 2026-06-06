from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_view, name='landing'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/<int:user_id>/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),
    path('follow/<int:user_id>/', views.follow_toggle_view, name='follow_toggle'),
    path('search/', views.search_users_view, name='search_users'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/unread-count/', views.unread_notifications_count, name='unread_notifications_count'),
    # Direct & Group Messages
    path('messages/', views.messages_inbox_view, name='messages_inbox'),
    path('messages/<int:user_id>/', views.messages_chat_view, name='messages_chat'),
    path('messages/room/<int:room_id>/', views.messages_room_chat_view, name='messages_room_chat'),
    path('messages/room/send/<int:room_id>/', views.api_send_room_message, name='api_send_room_message'),
    path('messages/send/<int:user_id>/', views.api_send_message, name='api_send_message'),
    path('messages/fetch/<int:user_id>/', views.api_fetch_messages, name='api_fetch_messages'),
    path('messages/unread-count/', views.api_unread_messages_count, name='api_unread_messages_count'),
    # Group Management APIs
    path('messages/group/create/', views.api_create_group_room, name='api_create_group_room'),
    path('messages/group/members/<int:room_id>/', views.api_update_group_members, name='api_update_group_members'),
    path('messages/group/role/<int:room_id>/', views.api_update_group_role, name='api_update_group_role'),
    # Pin / Archive / Star / Export
    path('messages/room/pin/<int:room_id>/', views.api_toggle_pin_room, name='api_toggle_pin_room'),
    path('messages/room/archive/<int:room_id>/', views.api_toggle_archive_room, name='api_toggle_archive_room'),
    path('messages/star/<int:message_id>/', views.api_toggle_star_message, name='api_toggle_star_message'),
    path('messages/room/export/<int:room_id>/', views.export_chat_history, name='export_chat_history'),
    # Followers and Following Lists
    path('profile/<int:user_id>/followers/', views.followers_list_view, name='followers_list'),
    path('profile/<int:user_id>/following/', views.following_list_view, name='following_list'),
    # Follow Requests
    path('follow-request/accept/<int:req_id>/', views.accept_follow_request_view, name='accept_follow_request'),
    path('follow-request/decline/<int:req_id>/', views.decline_follow_request_view, name='decline_follow_request'),
    # Stories
    path('stories/create/', views.create_story_view, name='create_story'),
    path('stories/<int:story_id>/delete/', views.delete_story_view, name='delete_story'),
    path('profile/<int:user_id>/stories/', views.user_stories_view, name='user_stories'),
    # Push Notifications
    path('api/register_device_token/', views.api_register_device_token, name='api_register_device_token'),
    # Gemini AI APIs
    path('api/ai/caption/', views.api_ai_generate_caption, name='api_ai_generate_caption'),
    path('api/ai/chat/<int:room_id>/', views.api_ai_chat_helper, name='api_ai_chat_helper'),
    path('api/ai/moderate/', views.api_ai_moderation_scan, name='api_ai_moderation_scan'),
    # Phase 1 Additions
    path('verify-email/', views.verify_email_view, name='verify_email'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('reset-password/', views.reset_password_view, name='reset_password'),
    path('profile/sessions/', views.session_management_view, name='session_management'),
    path('profile/sessions/revoke/<str:session_key>/', views.api_revoke_session, name='api_revoke_session'),
    path('api/auth/token/', views.api_jwt_token_view, name='api_jwt_token'),
    path('profile/<int:user_id>/analytics/', views.profile_analytics_view, name='profile_analytics'),
    path('profile/request-verification/', views.request_profile_verification_view, name='request_profile_verification'),
    path('profile/projects/add/', views.add_project_view, name='add_project'),
    path('profile/achievements/add/', views.add_achievement_view, name='add_achievement'),
    path('profile/skills/add/', views.add_skill_view, name='add_skill'),
    path('profile/skills/remove/<int:skill_id>/', views.remove_skill_view, name='remove_skill'),


    # New URLs for calling, leaving groups, password change, notification reads, and admin verification
    path('messages/group/leave/<int:room_id>/', views.api_leave_group_room, name='api_leave_group_room'),
    path('settings/password/', views.change_password_view, name='change_password'),
    path('verification-dashboard/', views.admin_verification_dashboard_view, name='admin_verification_dashboard'),
    path('notifications/read/<int:notif_id>/', views.api_mark_notification_read, name='api_mark_notification_read'),
    path('notifications/read-all/', views.api_mark_all_notifications_read, name='api_mark_all_notifications_read'),
    path('api/calls/log/', views.api_log_call, name='api_log_call'),
]
