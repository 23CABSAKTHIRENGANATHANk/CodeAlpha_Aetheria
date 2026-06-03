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
    # Direct Messages (DMs)
    path('messages/', views.messages_inbox_view, name='messages_inbox'),
    path('messages/<int:user_id>/', views.messages_chat_view, name='messages_chat'),
    path('messages/send/<int:user_id>/', views.api_send_message, name='api_send_message'),
    path('messages/fetch/<int:user_id>/', views.api_fetch_messages, name='api_fetch_messages'),
    path('messages/unread-count/', views.api_unread_messages_count, name='api_unread_messages_count'),
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
]
