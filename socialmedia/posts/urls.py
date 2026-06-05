from django.urls import path
from . import views

urlpatterns = [
    path('feed/', views.feed_view, name='feed'),
    path('create-post/', views.create_post_view, name='create_post'),
    path('post/<int:post_id>/', views.post_detail_view, name='post_detail'),
    path('delete-post/<int:post_id>/', views.delete_post_view, name='delete_post'),
    path('edit-post/<int:post_id>/', views.edit_post_view, name='edit_post'),
    path('like/<int:post_id>/', views.like_toggle_view, name='like_toggle'),
    path('comment/<int:post_id>/', views.add_comment_view, name='add_comment'),
    path('check-new/', views.check_new_posts, name='check_new_posts'),
    path('bookmark/<int:post_id>/', views.bookmark_toggle_view, name='bookmark_toggle'),
    path('react/<int:post_id>/', views.react_to_post_view, name='react_to_post'),
    path('hashtag/<str:tag>/', views.hashtag_feed_view, name='hashtag_feed'),
    path('explore/', views.explore_view, name='explore'),
    path('search-posts/', views.search_posts_view, name='search_posts'),
    path('feed/api/', views.feed_api_view, name='feed_api'),
]
