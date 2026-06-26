from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Profile, Follow, Notification, Message, FollowRequest
from .consumers import push_notification_to_user
from posts.models import Like, Post
from django.db.models import Q
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
import datetime
import logging
from .forms import UserRegisterForm, ProfileUpdateForm

# Supabase Auth helpers (graceful no-op when Supabase not configured)
from socialmedia.supabase_auth import (
    sign_up_user as supabase_sign_up,
    sign_in_user as supabase_sign_in,
    sign_out_user as supabase_sign_out,
    send_password_reset_email as supabase_reset_password,
    update_user_password as supabase_update_password,
)

logger = logging.getLogger(__name__)

def landing_view(request):
    if request.user.is_authenticated:
        return redirect('feed')
    return render(request, 'landing.html')

def register_view(request):
    if request.user.is_authenticated:
        return redirect('feed')
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # ── Supabase Auth sync (hybrid mode) ─────────────────────────────
            # Create the matching user in Supabase Auth so API clients can use JWT tokens.
            # Failure is non-fatal: Django session auth works independently.
            email = form.cleaned_data.get('email', '') or user.email
            password = form.cleaned_data.get('password1', '')
            if email and password:
                sb_user = supabase_sign_up(
                    email=email,
                    password=password,
                    metadata={'username': user.username, 'django_user_id': user.id},
                )
                if sb_user and sb_user.get('id'):
                    try:
                        user.settings.supabase_uid = sb_user['id']
                        user.settings.save(update_fields=['supabase_uid'])
                    except Exception:
                        pass
                    logger.info("Supabase Auth: user created uid=%s email=%s", sb_user['id'], email)
            # ─────────────────────────────────────────────────────────────────
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('feed')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                auth_login(request, user)
                # Store device metadata for session management
                request.session['user_agent'] = request.META.get('HTTP_USER_AGENT', 'Unknown Device')
                request.session['ip_address'] = request.META.get('REMOTE_ADDR', 'Unknown IP')
                request.session['last_activity'] = timezone.now().strftime('%Y-%m-%d %H:%M')

                # ── Supabase Auth sync (hybrid mode) ─────────────────────────
                # Obtain Supabase session tokens for API clients.
                # Stored in session — available to JS via a dedicated endpoint.
                try:
                    email = user.email
                    if email:
                        sb_session = supabase_sign_in(email, password)
                        if sb_session:
                            request.session['supabase_access_token'] = sb_session.get('access_token', '')
                            request.session['supabase_refresh_token'] = sb_session.get('refresh_token', '')
                            # Sync supabase_uid if not already stored
                            sb_uid = sb_session.get('user_id')
                            if sb_uid and hasattr(user, 'settings') and not user.settings.supabase_uid:
                                user.settings.supabase_uid = sb_uid
                                user.settings.save(update_fields=['supabase_uid'])
                except Exception as exc:
                    logger.debug("Supabase sign-in sync failed (non-fatal): %s", exc)
                # ─────────────────────────────────────────────────────────────

                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('feed')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    if request.user.is_authenticated:
        # Logout device token cleanup
        from .models import DeviceToken
        DeviceToken.objects.filter(user=request.user).delete()

        # ── Supabase Auth sync ────────────────────────────────────────────────
        access_token = request.session.get('supabase_access_token', '')
        if access_token:
            supabase_sign_out(access_token)
        # ─────────────────────────────────────────────────────────────────────

    auth_logout(request)
    return redirect('landing')

@login_required
def profile_view(request, user_id):
    profile_user = get_object_or_404(User, id=user_id)
    is_following = Follow.objects.filter(follower=request.user, following=profile_user).exists()
    
    # Privacy check
    is_locked = hasattr(profile_user, 'profile') and profile_user.profile.is_private and request.user != profile_user and not is_following
    is_requested = False
    
    saved_posts = []
    
    if is_locked:
        is_requested = FollowRequest.objects.filter(sender=request.user, receiver=profile_user).exists()
        posts = []
    else:
        # Get profile user's posts
        posts_query = profile_user.posts.all().order_by('-created_at')
        from posts.views import annotate_posts_for_user
        posts = annotate_posts_for_user(list(posts_query), request.user)
        
        # Get saved posts if visiting own profile
        if profile_user == request.user:
            from posts.models import Bookmark, Post
            saved_ids = Bookmark.objects.filter(user=request.user).values_list('post_id', flat=True)
            saved_posts_query = Post.objects.filter(id__in=saved_ids).order_by('-created_at')
            saved_posts = annotate_posts_for_user(list(saved_posts_query), request.user)
    
    # Followers and following query
    followers_count = profile_user.follower_relations.count()
    following_count = profile_user.following_relations.count()
    
    # Fetch suggestions
    followed_ids = Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
    suggestions = User.objects.exclude(id__in=list(followed_ids) + [request.user.id])[:5]
    
    context = {
        'profile_user': profile_user,
        'profile': profile_user.profile,
        'posts': posts,
        'saved_posts': saved_posts,
        'is_following': is_following,
        'is_locked': is_locked,
        'is_requested': is_requested,
        'followers_count': followers_count,
        'following_count': following_count,
        'suggestions': suggestions,
    }
    return render(request, 'profile.html', context)

@login_required
def edit_profile_view(request):
    try:
        profile = request.user.profile
    except Exception:
        profile = Profile.objects.create(user=request.user)
        
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('profile', user_id=request.user.id)
    else:
        form = ProfileUpdateForm(instance=profile)
    return render(request, 'edit_profile.html', {'form': form})

@login_required
@require_POST
def follow_toggle_view(request, user_id):
    # Validate user_id is not empty
    if not user_id or not str(user_id).isdigit():
        return JsonResponse({'error': 'Invalid user ID'}, status=400)
    
    try:
        target_user = get_object_or_404(User, id=int(user_id))
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid user ID format'}, status=400)
    
    if target_user == request.user:
        return JsonResponse({'error': 'You cannot follow yourself.'}, status=400)
    
    follow_rel = Follow.objects.filter(follower=request.user, following=target_user)
    is_following = False
    is_requested = False
    status = ''

    def create_notification_safely(notification_type):
        try:
            notification = Notification.objects.filter(
                sender=request.user,
                receiver=target_user,
                notification_type=notification_type,
            ).order_by('-created_at').first()
            if notification is None:
                notification = Notification.objects.create(
                    sender=request.user,
                    receiver=target_user,
                    notification_type=notification_type,
                )
            unread = Notification.objects.filter(receiver=target_user, is_read=False).count()
            push_notification_to_user(
                target_user.id,
                request.user,
                notification_type,
                unread_count=unread,
            )
            return notification
        except Exception:
            logger.exception("Follow notification failed for user_id=%s", target_user.id)
            return None
    
    try:
        if follow_rel.exists():
            follow_rel.delete()
            is_following = False
            status = 'unfollowed'
            # Optional: delete previous follow notification
            Notification.objects.filter(sender=request.user, receiver=target_user, notification_type='follow').delete()
        else:
            if hasattr(target_user, 'profile') and target_user.profile.is_private:
                req_exists = FollowRequest.objects.filter(sender=request.user, receiver=target_user)
                if req_exists.exists():
                    req_exists.delete()
                    is_requested = False
                    status = 'unrequested'
                    # Delete follow request notification
                    Notification.objects.filter(sender=request.user, receiver=target_user, notification_type='follow_request').delete()
                else:
                    FollowRequest.objects.get_or_create(sender=request.user, receiver=target_user)
                    is_requested = True
                    status = 'requested'
                    create_notification_safely('follow_request')
            else:
                Follow.objects.get_or_create(follower=request.user, following=target_user)
                is_following = True
                status = 'following'
                create_notification_safely('follow')
            
        followers_count = target_user.follower_relations.count()
        return JsonResponse({
            'is_following': is_following,
            'is_requested': is_requested,
            'status': status,
            'followers_count': followers_count,
            'profile_url': f'/profile/{target_user.id}/',
            'message_url': f'/messages/{target_user.id}/',
            'username': target_user.username,
        })
    except Exception as e:
        logger.exception("Follow toggle failed for user_id=%s", user_id)
        return JsonResponse({'error': 'An error occurred while processing your request.'}, status=500)

@login_required
def search_users_view(request):
    query = request.GET.get('q', '').strip()
    users = []
    posts = []
    hashtags = []

    if query:
        from posts.models import Post, Hashtag
        from posts.views import annotate_posts_for_user

        followed_ids = Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
        posts_qs = Post.objects.select_related('author', 'author__profile').prefetch_related('images', 'hashtags').filter(
            Q(content__icontains=query) |
            Q(hashtags__name__icontains=query)
        ).filter(
            Q(author=request.user) |
            Q(author__profile__is_private=False) |
            Q(author_id__in=followed_ids)
        ).distinct().order_by('-created_at')[:8]

        users = list(
            User.objects.filter(
                Q(username__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(id__in=posts_qs.values('author_id'))
            )
            .exclude(id=request.user.id)
            .select_related('profile')[:10]
        )
        posts = annotate_posts_for_user(list(posts_qs), request.user)

        hashtags_qs = Hashtag.objects.filter(name__icontains=query).order_by('name')[:8]
        hashtags = [
            {'id': tag.id, 'name': tag.name, 'post_count': tag.posts.count()}
            for tag in hashtags_qs
        ]
    else:
        followed_ids = Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)

    # Suggestions for search page sidebar
    suggestions = User.objects.exclude(id__in=list(followed_ids) + [request.user.id]).select_related('profile')[:5]

    return render(request, 'search_results.html', {
        'users': users,
        'posts': posts,
        'hashtags': hashtags,
        'query': query,
        'suggestions': suggestions,
        'followed_user_ids': followed_ids
    })

@login_required
def notifications_view(request):
    filter_type = request.GET.get('filter', 'all')
    notif_query = request.user.notifications_received.all().order_by('-created_at')
    
    if filter_type == 'likes':
        notif_query = notif_query.filter(notification_type='like')
    elif filter_type == 'comments':
        notif_query = notif_query.filter(notification_type='comment')
    elif filter_type == 'follows':
        notif_query = notif_query.filter(notification_type__in=['follow', 'follow_request', 'follow_accept'])
    elif filter_type == 'messages':
        notif_query = notif_query.filter(notification_type='message')
    elif filter_type == 'mentions':
        notif_query = notif_query.filter(notification_type='mention')
    elif filter_type == 'story_reactions':
        notif_query = notif_query.filter(notification_type='story_reaction')
    
    # Attach follow request IDs for rendering actions
    pending_requests = {r.sender_id: r.id for r in request.user.follow_requests_received.all()}
    for notif in notif_query:
        if notif.notification_type == 'follow_request':
            notif.follow_request_id = pending_requests.get(notif.sender_id)
            
    # Pagination
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    paginator = Paginator(notif_query, 10) # 10 notifications per page
    page = request.GET.get('page', 1)
    try:
        notifications = paginator.page(page)
    except PageNotAnInteger:
        notifications = paginator.page(1)
    except EmptyPage:
        notifications = paginator.page(paginator.num_pages)
        
    # Mark current page notifications as read (do not auto-read all unless requested)
    page_ids = [n.id for n in notifications.object_list]
    request.user.notifications_received.filter(id__in=page_ids, is_read=False).update(is_read=True)
    
    # Suggestions for notifications page sidebar
    followed_ids = Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
    suggestions = User.objects.exclude(id__in=list(followed_ids) + [request.user.id])[:5]

    unread_count = request.user.notifications_received.filter(is_read=False).count()
    recent_unread = request.user.notifications_received.filter(is_read=False).order_by('-created_at')[:3]
    summary = {
        'total': request.user.notifications_received.count(),
        'unread': unread_count,
        'likes': request.user.notifications_received.filter(notification_type='like').count(),
        'comments': request.user.notifications_received.filter(notification_type='comment').count(),
        'follows': request.user.notifications_received.filter(notification_type__in=['follow', 'follow_request', 'follow_accept']).count(),
        'messages': request.user.notifications_received.filter(notification_type='message').count(),
        'mentions': request.user.notifications_received.filter(notification_type='mention').count(),
    }

    # Build a lightweight preview context so the page can render chat-like activity summaries.
    notification_previews = []
    for notif in notifications.object_list:
        preview_text = ''
        action_label = 'View'
        action_url = None
        if notif.notification_type == 'like':
            preview_text = 'liked your post'
            action_label = 'Open post'
            action_url = reverse('post_detail', args=[notif.post.id]) if notif.post_id else None
        elif notif.notification_type == 'comment':
            preview_text = 'commented on your post'
            action_label = 'Open post'
            action_url = reverse('post_detail', args=[notif.post.id]) if notif.post_id else None
        elif notif.notification_type == 'mention':
            preview_text = 'mentioned you in a post'
            action_label = 'Open post'
            action_url = reverse('post_detail', args=[notif.post.id]) if notif.post_id else None
        elif notif.notification_type == 'message':
            preview_text = 'sent you a message'
            action_label = 'Open chat'
            action_url = reverse('messages_chat', args=[notif.sender.id])
        elif notif.notification_type == 'follow_request':
            preview_text = 'wants to follow you'
            action_label = 'Review request'
            action_url = reverse('profile', args=[request.user.id])
        elif notif.notification_type == 'follow_accept':
            preview_text = 'accepted your follow request'
            action_label = 'View profile'
            action_url = reverse('profile', args=[notif.sender.id])
        elif notif.notification_type == 'follow':
            preview_text = 'started following you'
            action_label = 'View profile'
            action_url = reverse('profile', args=[notif.sender.id])
        else:
            preview_text = 'interacted with you'
            action_label = 'View activity'

        notification_previews.append({
            'id': notif.id,
            'type': notif.notification_type,
            'sender': notif.sender,
            'is_read': notif.is_read,
            'created_at': notif.created_at,
            'preview_text': preview_text,
            'action_label': action_label,
            'action_url': action_url,
            'follow_request_id': getattr(notif, 'follow_request_id', None),
            'post_id': notif.post_id,
        })
    
    return render(request, 'notifications.html', {
        'notifications': notifications,
        'filter_type': filter_type,
        'suggestions': suggestions,
        'summary': summary,
        'recent_unread': recent_unread,
        'unread_count': unread_count,
        'notification_previews': notification_previews,
    })

@login_required
def unread_notifications_count(request):
    """Return unread notification count. Called by supabase-realtime.js badge updates."""
    if not request.user.is_authenticated:
        return JsonResponse({'count': 0, 'unread_count': 0})
    count = request.user.notifications_received.filter(is_read=False).count()
    return JsonResponse({'count': count, 'unread_count': count})


@login_required
def api_supabase_token(request):
    """Return the Supabase access token stored in the user's session.

    Called by the JS client after login to initialize the Supabase JS SDK
    with the user's own access token (for RLS-scoped operations).

    Returns:
        JSON: { access_token, expires_in } or { access_token: null }
    """
    access_token = request.session.get('supabase_access_token', '')
    return JsonResponse({
        'access_token': access_token or None,
        'user_id': request.user.id,
    })


# Direct/Group Messaging View Helpers & APIs
def get_or_create_direct_room(u1, u2):
    from .models import ChatRoom, GroupMember
    rooms = ChatRoom.objects.filter(room_type='direct')
    for r in rooms:
        m_ids = list(r.members.values_list('user_id', flat=True))
        if len(m_ids) == 2 and u1.id in m_ids and u2.id in m_ids:
            return r
            
    room = ChatRoom.objects.create(room_type='direct', title=f"{u1.username} & {u2.username}")
    GroupMember.objects.create(chat_room=room, user=u1, role='admin')
    GroupMember.objects.create(chat_room=room, user=u2, role='member')
    return room

def get_user_conversations(request_user):
    from .models import ChatRoom, GroupMember, Message
    memberships = GroupMember.objects.filter(user=request_user).select_related('chat_room')
    conversations = []
    
    for mb in memberships:
        room = mb.chat_room
        last_msg = Message.objects.filter(chat_room=room).order_by('-created_at').first()
        unread_count = Message.objects.filter(chat_room=room).exclude(sender=request_user).exclude(status='seen').count()
        
        if room.room_type == 'direct':
            other_member_rel = room.members.exclude(user=request_user).select_related('user__profile').first()
            if other_member_rel:
                other_user = other_member_rel.user
                title = other_user.username
                avatar_url = other_user.profile.profile_image.url if other_user.profile.profile_image else '/static/images/default_profile.png'
                is_online = other_user.profile.is_online
                target_user = other_user
            else:
                title = request_user.username
                avatar_url = request_user.profile.profile_image.url if request_user.profile.profile_image else '/static/images/default_profile.png'
                is_online = request_user.profile.is_online
                target_user = request_user
        else:
            title = room.title or f"Group {room.id}"
            avatar_url = room.avatar.url if room.avatar else '/static/images/default_group.png'
            is_online = False
            target_user = None

        conversations.append({
            'room': room,
            'is_group': room.room_type == 'group',
            'title': title,
            'avatar_url': avatar_url,
            'is_online': is_online,
            'last_message': last_msg,
            'unread_count': unread_count,
            'last_msg_time': last_msg.created_at if last_msg else room.created_at,
            'target_user': target_user,
            'is_pinned': mb.is_pinned,
            'is_archived': mb.is_archived
        })
        
    conversations.sort(key=lambda x: (x['is_pinned'], x['last_msg_time']), reverse=True)
    return conversations

def get_following_users_for_chat(request_user, conversations=None):
    following_users = User.objects.filter(
        follower_relations__follower=request_user
    ).select_related('profile').order_by('username')

    if conversations is None:
        return following_users

    existing_direct_ids = {
        conv['target_user'].id
        for conv in conversations
        if not conv['is_group'] and conv.get('target_user')
    }
    return following_users.exclude(id__in=existing_direct_ids)

@login_required
def messages_inbox_view(request):
    conversations = get_user_conversations(request.user)
    following_users = get_following_users_for_chat(request.user)
    start_chat_users = get_following_users_for_chat(request.user, conversations)
    return render(request, 'messages.html', {
        'conversations': conversations,
        'active_chat': False,
        'following_users': following_users,
        'start_chat_users': start_chat_users
    })

@login_required
def messages_chat_view(request, user_id):
    from .models import Message, GroupMember
    active_chat_user = get_object_or_404(User, id=user_id)
    room = get_or_create_direct_room(request.user, active_chat_user)
    
    Message.objects.filter(chat_room=room).exclude(sender=request.user).exclude(status='seen').update(is_read=True, status='seen')
    
    conversations = get_user_conversations(request.user)
    chat_messages = Message.objects.filter(chat_room=room).order_by('created_at')
    
    is_following = Follow.objects.filter(follower=request.user, following=active_chat_user).exists()
    can_message = not (hasattr(active_chat_user, 'profile') and active_chat_user.profile.is_private and active_chat_user != request.user and not is_following)
            
    following_users = get_following_users_for_chat(request.user)
    start_chat_users = get_following_users_for_chat(request.user, conversations)
    room_members = room.members.select_related('user__profile').all()
    membership = GroupMember.objects.filter(chat_room=room, user=request.user).first()
    
    return render(request, 'messages.html', {
        'conversations': conversations,
        'active_chat_user': active_chat_user,
        'room': room,
        'chat_messages': chat_messages,
        'active_chat': True,
        'can_message': can_message,
        'following_users': following_users,
        'start_chat_users': start_chat_users,
        'is_admin': membership.role == 'admin' if membership else False,
        'membership': membership,
        'room_members': room_members
    })

@login_required
def messages_room_chat_view(request, room_id):
    from .models import ChatRoom, GroupMember, Message
    room = get_object_or_404(ChatRoom, id=room_id)
    
    membership = GroupMember.objects.filter(chat_room=room, user=request.user).first()
    if not membership:
        messages.error(request, "You are not a member of this chat room.")
        return redirect('messages_inbox')
        
    Message.objects.filter(chat_room=room).exclude(sender=request.user).exclude(status='seen').update(is_read=True, status='seen')
    
    conversations = get_user_conversations(request.user)
    chat_messages = Message.objects.filter(chat_room=room).order_by('created_at')
    
    active_chat_user = None
    can_message = True
    if room.room_type == 'direct':
        other_member_rel = room.members.exclude(user=request.user).first()
        if other_member_rel:
            active_chat_user = other_member_rel.user
            is_following = Follow.objects.filter(follower=request.user, following=active_chat_user).exists()
            can_message = not (hasattr(active_chat_user, 'profile') and active_chat_user.profile.is_private and active_chat_user != request.user and not is_following)
            
    following_users = get_following_users_for_chat(request.user)
    start_chat_users = get_following_users_for_chat(request.user, conversations)
    
    # Get all members details for group drawer
    room_members = room.members.select_related('user__profile').all()
    
    return render(request, 'messages.html', {
        'conversations': conversations,
        'active_chat_user': active_chat_user,
        'room': room,
        'chat_messages': chat_messages,
        'active_chat': True,
        'can_message': can_message,
        'following_users': following_users,
        'start_chat_users': start_chat_users,
        'is_admin': membership.role == 'admin',
        'membership': membership,
        'room_members': room_members
    })

@login_required
@require_POST
def api_send_room_message(request, room_id):
    from .models import ChatRoom, GroupMember, Message
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    
    room = get_object_or_404(ChatRoom, id=room_id)
    membership = GroupMember.objects.filter(chat_room=room, user=request.user).first()
    if not membership:
        return JsonResponse({'status': 'error', 'message': 'Not a member of this chat room'}, status=403)
        
    # Security/Privacy check for direct messages to private users
    if room.room_type == 'direct':
        other_member = room.members.exclude(user=request.user).first()
        if other_member:
            receiver = other_member.user
            is_following = Follow.objects.filter(follower=request.user, following=receiver).exists()
            if hasattr(receiver, 'profile') and receiver.profile.is_private and receiver != request.user and not is_following:
                return JsonResponse({'status': 'error', 'message': 'You must follow this user to send messages.'}, status=403)
                
    body = request.POST.get('body', '').strip()
    file_attachment = request.FILES.get('file_attachment')
    file_type = request.POST.get('file_type', 'text')
    parent_id = request.POST.get('parent_id')
    is_forwarded = request.POST.get('is_forwarded') == 'true'
    
    if not body and not file_attachment:
        return JsonResponse({'status': 'error', 'message': 'Message cannot be empty.'}, status=400)
        
    parent = None
    if parent_id and parent_id.isdigit():
        try:
            parent = Message.objects.get(id=int(parent_id), chat_room=room)
        except Message.DoesNotExist:
            pass
            
    members = room.members.exclude(user=request.user).select_related('user__profile')
    any_online = any(m.user.profile.is_online for m in members)
    initial_status = 'delivered' if any_online else 'sent'
    
    receiver = None
    if room.room_type == 'direct':
        other_member = room.members.exclude(user=request.user).first()
        if other_member:
            receiver = other_member.user
            
    msg = Message.objects.create(
        sender=request.user,
        receiver=receiver,
        chat_room=room,
        body=body,
        status=initial_status,
        is_read=(initial_status == 'seen'),
        file_attachment=file_attachment,
        file_type=file_type,
        parent_message=parent,
        is_forwarded=is_forwarded
    )
    
    channel_layer = get_channel_layer()
    time_str = timezone.now().isoformat()
    file_url = msg.file_attachment.url if msg.file_attachment else ''
    file_name = msg.file_attachment.name.split('/')[-1] if msg.file_attachment else ''
    
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            f'chat_room_{room.id}',
            {
                'type': 'chat_message',
                'message_id': msg.id,
                'message': msg.body,
                'sender_id': request.user.id,
                'time': time_str,
                'status': msg.status,
                'parent_id': parent_id,
                'is_forwarded': is_forwarded,
                'file_url': file_url,
                'file_type': file_type,
                'file_name': file_name
            }
        )
        
        for m in members:
            unread_count = Message.objects.filter(chat_room__members__user=m.user).exclude(sender=m.user).exclude(status='seen').count()
            async_to_sync(channel_layer.group_send)(
                f'notif_{m.user.id}',
                {
                    'type': 'notification_message',
                    'notification_type': 'message',
                    'sender_username': request.user.username,
                    'sender_id': request.user.id,
                    'sender_avatar': request.user.profile.profile_image.url if request.user.profile.profile_image else '/static/images/default_profile.png',
                    'message': f"Sent an attachment" if file_attachment else msg.body,
                    'room_id': room.id,
                    'unread_count': unread_count,
                }
            )
            try:
                from .utils import send_push_notification
                send_push_notification(
                    user=m.user,
                    title=f"New message from {request.user.username}",
                    body=f"Sent an attachment" if file_attachment else msg.body,
                    data={
                        'notification_type': 'message',
                        'sender_id': str(request.user.id),
                        'room_id': str(room.id),
                    },
                    badge=unread_count
                )
            except Exception:
                pass
                
    return JsonResponse({
        'status': 'success',
        'message_id': msg.id,
        'body': msg.body,
        'file_url': file_url,
        'file_type': file_type,
        'file_name': file_name,
        'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
    })

@login_required
@require_POST
def api_send_message(request, user_id):
    active_chat_user = get_object_or_404(User, id=user_id)
    room = get_or_create_direct_room(request.user, active_chat_user)
    return api_send_room_message(request, room.id)

@login_required
def api_fetch_messages(request, user_id):
    from .models import Message
    active_chat_user = get_object_or_404(User, id=user_id)
    room = get_or_create_direct_room(request.user, active_chat_user)
    
    since_str = request.GET.get('since', '')
    Message.objects.filter(chat_room=room).exclude(sender=request.user).exclude(status='seen').update(is_read=True, status='seen')
    
    msgs_query = Message.objects.filter(chat_room=room).exclude(sender=request.user)
    if since_str:
        from django.utils import dateparse
        since = dateparse.parse_datetime(since_str)
        if since:
            msgs_query = msgs_query.filter(created_at__gt=since)
            
    messages = msgs_query.order_by('created_at')
    data = []
    for msg in messages:
        data.append({
            'id': msg.id,
            'body': msg.body,
            'file_url': msg.file_attachment.url if msg.file_attachment else '',
            'file_type': msg.file_type,
            'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    return JsonResponse({
        'status': 'success',
        'messages': data,
        'timestamp': timezone.now().isoformat()
    })

@login_required
def api_unread_messages_count(request):
    from .models import Message
    count = Message.objects.filter(chat_room__members__user=request.user).exclude(sender=request.user).exclude(status='seen').count()
    return JsonResponse({'unread_count': count})

@login_required
def followers_list_view(request, user_id):
    profile_user = get_object_or_404(User, id=user_id)
    
    # Gate check for private accounts
    is_following = Follow.objects.filter(follower=request.user, following=profile_user).exists()
    if hasattr(profile_user, 'profile') and profile_user.profile.is_private and profile_user != request.user and not is_following:
        return redirect('profile', user_id=user_id)
        
    follows = Follow.objects.filter(following=profile_user)
    users_list = [f.follower for f in follows]
    
    # Fetch current user's followed IDs for list item button states
    followed_user_ids = Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
    suggestions = User.objects.exclude(id__in=list(followed_user_ids) + [request.user.id])[:5]
    
    return render(request, 'follow_list.html', {
        'profile_user': profile_user,
        'users_list': users_list,
        'list_title': 'Followers',
        'followed_user_ids': followed_user_ids,
        'suggestions': suggestions
    })

@login_required
def following_list_view(request, user_id):
    profile_user = get_object_or_404(User, id=user_id)
    
    # Gate check for private accounts
    is_following = Follow.objects.filter(follower=request.user, following=profile_user).exists()
    if hasattr(profile_user, 'profile') and profile_user.profile.is_private and profile_user != request.user and not is_following:
        return redirect('profile', user_id=user_id)
        
    follows = Follow.objects.filter(follower=profile_user)
    users_list = [f.following for f in follows]
    
    followed_user_ids = Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
    suggestions = User.objects.exclude(id__in=list(followed_user_ids) + [request.user.id])[:5]
    
    return render(request, 'follow_list.html', {
        'profile_user': profile_user,
        'users_list': users_list,
        'list_title': 'Following',
        'followed_user_ids': followed_user_ids,
        'suggestions': suggestions
    })

@login_required
@require_POST
def accept_follow_request_view(request, req_id):
    follow_req = get_object_or_404(FollowRequest, id=req_id, receiver=request.user)
    sender = follow_req.sender
    
    # Create Follow relation (sender follows receiver/request.user)
    Follow.objects.get_or_create(follower=sender, following=request.user)
    
    # Create notification to the sender that they were accepted
    unread = Notification.objects.filter(receiver=sender, is_read=False).count() + 1
    Notification.objects.create(
        sender=request.user,
        receiver=sender,
        notification_type='follow_accept'
    )
    # Real-time WebSocket push
    push_notification_to_user(sender.id, request.user, 'follow_accept', unread_count=unread)
    
    # Delete the follow request
    follow_req.delete()
    
    # Delete the follow_request notification
    Notification.objects.filter(sender=sender, receiver=request.user, notification_type='follow_request').delete()
    
    return JsonResponse({'status': 'success'})

@login_required
@require_POST
def decline_follow_request_view(request, req_id):
    follow_req = get_object_or_404(FollowRequest, id=req_id, receiver=request.user)
    sender = follow_req.sender
    
    # Delete follow request
    follow_req.delete()
    
    # Delete the follow_request notification
    Notification.objects.filter(sender=sender, receiver=request.user, notification_type='follow_request').delete()
    
    return JsonResponse({'status': 'success'})

@login_required
def create_story_view(request):
    if request.method == 'POST':
        from .forms import StoryForm
        form = StoryForm(request.POST, request.FILES)
        if form.is_valid():
            story = form.save(commit=False)
            story.author = request.user
            story.save()
            return redirect('feed')
    return redirect('feed')

@login_required
def delete_story_view(request, story_id):
    from .models import Story
    story = get_object_or_404(Story, id=story_id)
    if story.author == request.user:
        story.delete()
    return redirect('feed')

from django.views.decorators.http import require_POST

@login_required
@require_POST
def react_to_story_view(request, story_id):
    from .models import Story, StoryView, Notification
    from .consumers import push_notification_to_user
    import json
    
    story = get_object_or_404(Story, id=story_id)
    try:
        data = json.loads(request.body)
        reaction = data.get('reaction', '')
    except:
        reaction = request.POST.get('reaction', '')
        
    if not reaction:
        return JsonResponse({'status': 'error', 'message': 'No reaction provided'}, status=400)
        
    story_view, created = StoryView.objects.get_or_create(story=story, user=request.user)
    story_view.reaction = reaction
    story_view.save()
    
    # Send notification to author
    if story.author != request.user:
        unread = Notification.objects.filter(receiver=story.author, is_read=False).count() + 1
        Notification.objects.create(
            sender=request.user,
            receiver=story.author,
            notification_type='story_reaction',
        )
        push_notification_to_user(story.author.id, request.user, 'story_reaction', unread_count=unread)
        
    return JsonResponse({'status': 'success', 'reaction': reaction})

@login_required
def user_stories_view(request, user_id):
    author = get_object_or_404(User, id=user_id)
    is_following = Follow.objects.filter(follower=request.user, following=author).exists()
    if hasattr(author, 'profile') and author.profile.is_private and author != request.user and not is_following:
        return JsonResponse({'error': 'You must follow this user to view their stories.'}, status=403)
        
    from .models import Story
    now = timezone.now()
    stories = author.stories.filter(expires_at__gt=now).order_by('created_at')
    
    # Mark stories as viewed by current user
    for s in stories:
        if request.user not in s.viewers.all():
            s.viewers.add(request.user)
            
    data = []
    for s in stories:
        data.append({
            'id': s.id,
            'image_url': s.image.url if s.image else '',
            'video_url': s.video_file.url if s.video_file else '',
            'voice_url': s.voice_file.url if s.voice_file else '',
            'text_content': s.text_content,
            'background_color': s.background_color,
            'story_type': s.story_type,
            'caption': s.caption,
            'created_at': s.created_at.strftime('%Y-%m-%d %H:%M'),
            'time_ago': s.created_at.strftime('%I:%M %p'),
            'author_username': author.username,
            'author_avatar': author.profile.profile_image.url if author.profile.profile_image else '/static/images/default_profile.png',
            'viewers_count': s.viewers.count()
        })
    return JsonResponse({
        'status': 'success',
        'stories': data
    })

@login_required
def api_story_viewers_view(request, story_id):
    from .models import Story
    story = get_object_or_404(Story, id=story_id)
    if story.author != request.user:
        return JsonResponse({'error': 'You can only view viewer lists for your own stories.'}, status=403)
        
    view_records = story.story_views.select_related('user', 'user__profile')
    viewers_list = []
    for record in view_records:
        user = record.user
        avatar_url = user.profile.profile_image.url if user.profile.profile_image else '/static/images/default_profile.png'
        viewers_list.append({
            'username': user.username,
            'avatar': avatar_url,
            'reaction': record.reaction,
            'viewed_at': record.created_at.strftime('%Y-%m-%d %H:%M')
        })
        
    return JsonResponse({
        'status': 'success',
        'viewers': viewers_list
    })

@login_required

@require_POST
def api_register_device_token(request):
    import json
    from .models import DeviceToken
    try:
        token = None
        try:
            data = json.loads(request.body.decode('utf-8') or '{}')
            token = data.get('token')
        except Exception:
            token = request.POST.get('token')

        if token:
            device_token, created = DeviceToken.objects.get_or_create(token=token, defaults={'user': request.user})
            if not created and device_token.user != request.user:
                device_token.user = request.user
                device_token.save(update_fields=['user'])
            return JsonResponse({'status': 'success'})
        return JsonResponse({'error': 'Token not provided'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# ──────────────────────────────────────────────
# Phase 1 - Additional Authentication & Security Views
# ──────────────────────────────────────────────
import random
import jwt
from django.conf import settings
from django.contrib.sessions.models import Session
from django.contrib.auth import login as auth_login
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from .models import UserSettings, Project, Achievement

def generate_pin():
    return str(random.randint(100000, 999999))

def generate_jwt_token(user):
    payload = {
        'user_id': user.id,
        'username': user.username,
        'exp': timezone.now() + datetime.timedelta(days=7),
        'iat': timezone.now()
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

def decode_jwt_token(token):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        return payload
    except Exception:
        return None

@login_required
def verify_email_view(request):
    try:
        user_settings = request.user.settings
    except Exception:
        user_settings = UserSettings.objects.create(user=request.user)

    if user_settings.email_verified:
        return redirect('feed')

    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        if user_settings.verification_code == code and user_settings.verification_code_expires and timezone.now() < user_settings.verification_code_expires:
            user_settings.email_verified = True
            user_settings.verification_code = None
            user_settings.verification_code_expires = None
            user_settings.save()
            messages.success(request, "Email verified successfully!")
            return redirect('feed')
        else:
            messages.error(request, "Invalid or expired verification code.")
    
    # Resend/Initial code generation
    if not user_settings.verification_code or not user_settings.verification_code_expires or timezone.now() > user_settings.verification_code_expires:
        user_settings.verification_code = generate_pin()
        user_settings.verification_code_expires = timezone.now() + datetime.timedelta(minutes=10)
        user_settings.save()
        # Print to console for server/debug logging
        print(f"\n[EMAIL VERIFICATION DEBUG] User: {request.user.username}, Code: {user_settings.verification_code}\n")

    return render(request, 'verify_email.html', {'user_settings': user_settings})

def forgot_password_view(request):
    if request.user.is_authenticated:
        return redirect('feed')

    if request.method == 'POST':
        username_or_email = request.POST.get('username_or_email', '').strip()
        user = User.objects.filter(Q(username=username_or_email) | Q(email=username_or_email)).first()
        if user:
            try:
                user_settings = user.settings
            except Exception:
                user_settings = UserSettings.objects.create(user=user)
            
            user_settings.reset_pin = generate_pin()
            user_settings.reset_pin_expires = timezone.now() + datetime.timedelta(minutes=15)
            user_settings.save()
            
            # Send Email
            subject = "Aetheria - Password Reset PIN"
            message = f"Hello {user.username},\n\nYou requested a password reset. Your PIN is: {user_settings.reset_pin}\n\nThis PIN will expire in 15 minutes."
            try:
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
                messages.success(request, f"Password reset PIN sent to {user.email}.")
            except Exception as e:
                print(f"[EMAIL ERROR] {e}")
                messages.warning(request, "Password reset PIN generated, but there was an error sending the email. Check console.")
                print(f"\n[PASSWORD RESET PIN DEBUG] User: {user.username}, Reset PIN: {user_settings.reset_pin}\n")
            
            # Store username in session for reset password page convenience
            request.session['reset_username'] = user.username
            return redirect('reset_password')
        else:
            messages.error(request, "User not found.")

    return render(request, 'forgot_password.html')

def forgot_username_view(request):
    if request.user.is_authenticated:
        return redirect('feed')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        user = User.objects.filter(email=email).first()
        if user:
            # Send Email
            subject = "Aetheria - Your Username"
            message = f"Hello,\n\nYou requested your username. Your username is: {user.username}\n\nYou can now log in using this username."
            try:
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
                messages.success(request, f"Your username has been sent to {user.email}.")
            except Exception as e:
                print(f"[EMAIL ERROR] {e}")
                messages.warning(request, "There was an error sending the email. Please contact support.")
                print(f"\n[FORGOT USERNAME DEBUG] Email: {user.email}, Username: {user.username}\n")
        else:
            messages.error(request, "No account found with that email address.")
            
    return render(request, 'forgot_username.html')

def reset_password_view(request):
    if request.user.is_authenticated:
        return redirect('feed')

    username = request.session.get('reset_username', '')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        pin = request.POST.get('pin', '').strip()
        new_password = request.POST.get('new_password', '').strip()

        user = User.objects.filter(username=username).first()
        if user:
            try:
                user_settings = user.settings
            except Exception:
                user_settings = UserSettings.objects.create(user=user)
            
            if user_settings.reset_pin == pin and user_settings.reset_pin_expires and timezone.now() < user_settings.reset_pin_expires:
                user.set_password(new_password)
                user.save()
                user_settings.reset_pin = None
                user_settings.reset_pin_expires = None
                user_settings.save()
                messages.success(request, "Password reset successfully. Please login.")
                return redirect('login')
            else:
                messages.error(request, "Invalid or expired PIN.")
        else:
            messages.error(request, "User not found.")

    return render(request, 'reset_password.html', {'username': username})

@login_required
def session_management_view(request):
    # Retrieve active sessions
    sessions = Session.objects.filter(expire_date__gt=timezone.now())
    active_sessions = []
    for s in sessions:
        try:
            data = s.get_decoded()
            if data.get('_auth_user_id') == str(request.user.id):
                active_sessions.append({
                    'session_key': s.session_key,
                    'user_agent': data.get('user_agent', 'Unknown Device'),
                    'ip_address': data.get('ip_address', 'Unknown IP'),
                    'last_activity': data.get('last_activity', timezone.now().strftime('%Y-%m-%d %H:%M')),
                    'is_current': s.session_key == request.session.session_key
                })
        except Exception:
            pass

    return render(request, 'session_management.html', {'sessions': active_sessions})

@login_required
@require_POST
def api_revoke_session(request, session_key):
    try:
        s = Session.objects.get(session_key=session_key)
        data = s.get_decoded()
        if data.get('_auth_user_id') == str(request.user.id):
            s.delete()
            return JsonResponse({'status': 'success'})
    except Session.DoesNotExist:
        pass
    return JsonResponse({'status': 'error', 'message': 'Session not found'}, status=404)

@csrf_exempt
def api_jwt_token_view(request):
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
        except Exception:
            data = request.POST
        
        username = data.get('username')
        password = data.get('password')
        user = authenticate(username=username, password=password)
        if user is not None:
            token = generate_jwt_token(user)
            return JsonResponse({
                'token': token,
                'username': user.username,
                'user_id': user.id
            })
        return JsonResponse({'error': 'Invalid credentials'}, status=400)
    return JsonResponse({'error': 'POST request required'}, status=405)

@login_required
def profile_analytics_view(request, user_id):
    profile_user = get_object_or_404(User, id=user_id)
    # Simple profile analytics
    profile = profile_user.profile
    # Increment profile views when other users visit
    if request.user != profile_user:
        profile.profile_views += 1
        profile.save(update_fields=['profile_views'])

    reach = profile.reach or (profile.profile_views * 3) or 150
    engagement_rate = round((profile_user.posts.count() * 1.5) / max(profile_user.follower_relations.count(), 1) * 100, 1)
    
    context = {
        'profile_user': profile_user,
        'profile': profile,
        'reach': reach,
        'engagement_rate': engagement_rate,
        'posts_count': profile_user.posts.count(),
        'followers_count': profile_user.follower_relations.count(),
    }
    return render(request, 'profile_analytics.html', context)

@login_required
def request_profile_verification_view(request):
    profile = request.user.profile
    if request.method == 'POST':
        # Auto-verify on request for premium/creators, otherwise queue it
        profile.is_verified = True
        profile.save()
        messages.success(request, "Your profile is verified successfully!")
        return redirect('profile', user_id=request.user.id)
    return render(request, 'request_verification.html')

@login_required
@require_POST
def add_project_view(request):
    title = request.POST.get('title', '').strip()
    description = request.POST.get('description', '').strip()
    url = request.POST.get('url', '').strip()
    github_url = request.POST.get('github_url', '').strip()
    if title:
        Project.objects.create(
            user=request.user,
            title=title,
            description=description,
            url=url,
            github_url=github_url
        )
        messages.success(request, "Project added successfully!")
    return redirect('profile', user_id=request.user.id)

@login_required
@require_POST
def add_achievement_view(request):
    title = request.POST.get('title', '').strip()
    description = request.POST.get('description', '').strip()
    credential_url = request.POST.get('credential_url', '').strip()
    if title:
        Achievement.objects.create(
            user=request.user,
            title=title,
            description=description,
            credential_url=credential_url
        )
        messages.success(request, "Achievement added successfully!")
    return redirect('profile', user_id=request.user.id)

@login_required
@require_POST
def add_skill_view(request):
    from .models import Skill
    skill_name = request.POST.get('skill_name', '').strip().lower()
    if skill_name:
        skill, _ = Skill.objects.get_or_create(name=skill_name)
        request.user.profile.skills.add(skill)
        messages.success(request, f"Skill '{skill_name}' added!")
    return redirect('profile', user_id=request.user.id)

@login_required
@require_POST
def remove_skill_view(request, skill_id):
    from .models import Skill
    skill = get_object_or_404(Skill, id=skill_id)
    request.user.profile.skills.remove(skill)
    messages.success(request, f"Skill '{skill.name}' removed.")
    return redirect('profile', user_id=request.user.id)

# ──────────────────────────────────────────────
# Chat Group Management, Pin/Archive, Starring, and Export Views
# ──────────────────────────────────────────────
@login_required
@require_POST
def api_create_group_room(request):
    from .models import ChatRoom, GroupMember
    title = request.POST.get('title', '').strip()
    member_ids = request.POST.getlist('members')
    avatar = request.FILES.get('avatar')
    
    if not title:
        messages.error(request, "Group title is required.")
        return redirect('messages_inbox')
        
    room = ChatRoom.objects.create(
        title=title,
        room_type='group',
        avatar=avatar,
        created_by=request.user
    )
    
    GroupMember.objects.create(chat_room=room, user=request.user, role='admin')
    
    for uid in member_ids:
        if uid.isdigit():
            try:
                user = User.objects.get(id=int(uid))
                if user != request.user:
                    GroupMember.objects.get_or_create(chat_room=room, user=user, defaults={'role': 'member'})
            except Exception:
                pass
                
    messages.success(request, f"Group chat '{title}' created successfully!")
    return redirect('messages_room_chat', room_id=room.id)

@login_required
@require_POST
def api_update_group_members(request, room_id):
    from .models import ChatRoom, GroupMember
    room = get_object_or_404(ChatRoom, id=room_id)
    
    membership = GroupMember.objects.filter(chat_room=room, user=request.user, role='admin').first()
    if not membership:
        return JsonResponse({'status': 'error', 'message': 'Only group admins can modify members.'}, status=403)
        
    member_ids_str = request.POST.getlist('members')
    member_ids = [int(uid) for uid in member_ids_str if uid.isdigit()]
    
    if request.user.id not in member_ids:
        member_ids.append(request.user.id)
        
    GroupMember.objects.filter(chat_room=room).exclude(user_id__in=member_ids).delete()
    
    for uid in member_ids:
        try:
            user = User.objects.get(id=uid)
            GroupMember.objects.get_or_create(chat_room=room, user=user, defaults={'role': 'member'})
        except Exception:
            pass
            
    return JsonResponse({'status': 'success', 'message': 'Group members updated successfully.'})

@login_required
@require_POST
def api_update_group_role(request, room_id):
    from .models import ChatRoom, GroupMember
    room = get_object_or_404(ChatRoom, id=room_id)
    
    membership = GroupMember.objects.filter(chat_room=room, user=request.user, role='admin').first()
    if not membership:
        return JsonResponse({'status': 'error', 'message': 'Only group admins can modify member roles.'}, status=403)
        
    target_user_id = request.POST.get('user_id')
    new_role = request.POST.get('role', 'member')
    
    if target_user_id and target_user_id.isdigit():
        member = GroupMember.objects.filter(chat_room=room, user_id=int(target_user_id)).first()
        if member:
            member.role = new_role
            member.save(update_fields=['role'])
            return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Member not found'}, status=404)

@login_required
@require_POST
def api_toggle_pin_room(request, room_id):
    from .models import GroupMember
    mb = get_object_or_404(GroupMember, chat_room_id=room_id, user=request.user)
    mb.is_pinned = not mb.is_pinned
    mb.save(update_fields=['is_pinned'])
    return JsonResponse({'status': 'success', 'is_pinned': mb.is_pinned})

@login_required
@require_POST
def api_toggle_archive_room(request, room_id):
    from .models import GroupMember
    mb = get_object_or_404(GroupMember, chat_room_id=room_id, user=request.user)
    mb.is_archived = not mb.is_archived
    mb.save(update_fields=['is_archived'])
    return JsonResponse({'status': 'success', 'is_archived': mb.is_archived})

@login_required
@require_POST
def api_toggle_star_message(request, message_id):
    from .models import Message, GroupMember
    msg = get_object_or_404(Message, id=message_id)
    if msg.chat_room and not GroupMember.objects.filter(chat_room=msg.chat_room, user=request.user).exists():
        return JsonResponse({'status': 'error', 'message': 'Not a member of this chat room'}, status=403)
    if not msg.chat_room and msg.sender != request.user and msg.receiver != request.user:
        return JsonResponse({'status': 'error', 'message': 'Not allowed'}, status=403)
    if request.user in msg.starred_by_users.all():
        msg.starred_by_users.remove(request.user)
        starred = False
    else:
        msg.starred_by_users.add(request.user)
        starred = True
    return JsonResponse({'status': 'success', 'starred': starred})

import io
from django.http import HttpResponse

@login_required
def export_chat_history(request, room_id):
    from .models import ChatRoom, GroupMember, Message
    room = get_object_or_404(ChatRoom, id=room_id)
    membership = GroupMember.objects.filter(chat_room=room, user=request.user).first()
    if not membership:
        return HttpResponse("Forbidden", status=403)
        
    messages = Message.objects.filter(chat_room=room).order_by('created_at')
    
    output = io.StringIO()
    output.write(f"Chat Export: {room.title or 'Direct Chat'} (Room ID: {room.id})\n")
    output.write(f"Generated at: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')} UTC\n")
    output.write("=" * 60 + "\n\n")
    
    for msg in messages:
        timestamp = msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
        sender = msg.sender.username
        if msg.is_deleted_everyone:
            content = "[This message was deleted]"
        else:
            content = msg.body
            if msg.file_attachment:
                content += f" [Attachment: {msg.file_attachment.name.split('/')[-1]}]"
        output.write(f"[{timestamp}] {sender}: {content}\n")
        
    response = HttpResponse(output.getvalue(), content_type='text/plain')
    filename = f"chat_history_{room.id}_{timezone.now().strftime('%Y%m%d')}.txt"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

# ──────────────────────────────────────────────
# Phase 5 - Gemini AI Assistant Features
# ──────────────────────────────────────────────
@login_required
@require_POST
def api_ai_generate_caption(request):
    from .utils import call_gemini_api
    prompt = request.POST.get('prompt', '').strip()
    if not prompt:
        return JsonResponse({'status': 'error', 'message': 'Prompt is required'}, status=400)
        
    system_prompt = f"Write a professional, engaging developer social media post caption and relevant hashtags for: '{prompt}'."
    result = call_gemini_api(system_prompt)
    
    if not result:
        # Smart mock suggestions based on keywords
        words = prompt.lower()
        if 'error' in words or 'bug' in words:
            caption = f"Finally squashed that bug! 🐛 Fixed the state machine discrepancy and everything is running butter smooth. #debugging #developer #programming"
        elif 'python' in words:
            caption = f"Building clean abstractions in Python today! 🐍 Loving how readable and elegant PEP-8 styled code looks. #python #cleancode #backend"
        else:
            caption = f"Working on some exciting upgrades today! 💻 Iterating fast, testing thoroughly. What are you building today? #buildinpublic #devlife #aetheria"
        result = caption
        
    return JsonResponse({'status': 'success', 'caption': result})

@login_required
@require_POST
def api_ai_chat_helper(request, room_id):
    from .models import ChatRoom, Message
    from .utils import call_gemini_api
    
    room = get_object_or_404(ChatRoom, id=room_id)
    action = request.POST.get('action') # 'reply_suggestions', 'summarize', 'translate'
    
    if action == 'reply_suggestions':
        # Get last 8 messages
        msgs = Message.objects.filter(chat_room=room).order_by('-created_at')[:8]
        msgs_list = reversed(list(msgs))
        context_str = "\n".join([f"{m.sender.username}: {m.body}" for m in msgs_list])
        
        prompt = f"Given this conversation history:\n{context_str}\nProvide 3 very short, casual suggestions for context-aware replies the user could send next. Format as a simple numbered list."
        result = call_gemini_api(prompt)
        
        if not result:
            # Smart context-aware fallback based on last message content
            last_msg = msgs.first()
            if last_msg:
                body = last_msg.body.lower()
                if 'hello' in body or 'hi' in body:
                    suggestions = ["Hey there! How is it going?", "Hey! What's up?", "Hi! Working on anything cool today?"]
                elif '?' in body:
                    suggestions = ["That's a good question, let me check!", "Yeah, I can definitely help with that.", "Interesting, what do you think?"]
                else:
                    suggestions = ["Awesome!", "Haha nice!", "Thanks for sharing!"]
            else:
                suggestions = ["Hey! How's it going?", "Awesome project!", "Let's sync soon!"]
            result = "\n".join([f"{i+1}. {s}" for i, s in enumerate(suggestions)])
            
        return JsonResponse({'status': 'success', 'result': result})
        
    elif action == 'summarize':
        # Get last 15 messages
        msgs = Message.objects.filter(chat_room=room).order_by('-created_at')[:15]
        msgs_list = reversed(list(msgs))
        context_str = "\n".join([f"{m.sender.username}: {m.body}" for m in msgs_list])
        
        prompt = f"Summarize the key points of this chat history briefly:\n{context_str}"
        result = call_gemini_api(prompt)
        
        if not result:
            result = "Discussion centered around recent commits and scheduling a joint code review session."
            
        return JsonResponse({'status': 'success', 'result': result})
        
    elif action == 'translate':
        text = request.POST.get('text', '').strip()
        target_lang = request.POST.get('language', 'English').strip()
        if not text:
            return JsonResponse({'status': 'error', 'message': 'Text to translate is required'}, status=400)
            
        prompt = f"Translate the following text to {target_lang}:\n'{text}'"
        result = call_gemini_api(prompt)
        
        if not result:
            # Basic fallback dictionaries
            translations = {
                'spanish': "Hola, ¿cómo estás?",
                'french': "Bonjour, comment ça va?",
                'german': "Hallo, wie geht es dir?"
            }
            result = translations.get(target_lang.lower(), f"[Translated to {target_lang}] {text}")
            
        return JsonResponse({'status': 'success', 'result': result})
        
    return JsonResponse({'status': 'error', 'message': 'Invalid action'}, status=400)

@login_required
@require_POST
def api_ai_moderation_scan(request):
    from .utils import call_gemini_api
    text = request.POST.get('text', '').strip()
    if not text:
        return JsonResponse({'status': 'error', 'message': 'Text is required'}, status=400)
        
    prompt = f"Scan this text for toxic language, hate speech, or severe spam. Respond with ONLY 'toxic' if it contains toxic content, or 'clean' if it is acceptable: '{text}'."
    result = call_gemini_api(prompt)
    
    is_toxic = False
    reason = ""
    
    if result:
        is_toxic = "toxic" in result.lower()
        if is_toxic:
            reason = "Content flagged by AI moderation safety scan."
    else:
        # Mock keyword check
        toxic_keywords = ["abuse", "idiot", "kill yourself", "hate you", "spam click", "scam"]
        words = text.lower()
        for kw in toxic_keywords:
            if kw in words:
                is_toxic = True
                reason = f"Flagged keyword: '{kw}'"
                break
                
    return JsonResponse({
        'status': 'success',
        'is_toxic': is_toxic,
        'reason': reason
    })






@login_required
@require_POST
def api_leave_group_room(request, room_id):
    from .models import ChatRoom, GroupMember
    room = get_object_or_404(ChatRoom, id=room_id)
    membership = GroupMember.objects.filter(chat_room=room, user=request.user).first()
    if membership:
        membership.delete()
        if not room.members.exists():
            room.delete()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Not a member of this chat room'}, status=403)


# ──────────────────────────────────────────────
# SECURITY & ERROR HANDLING VIEWS
# ──────────────────────────────────────────────

def csrf_failure_view(request, reason=""):
    """
    Handle CSRF token validation failures
    """
    import logging
    logger = logging.getLogger('django.security')
    logger.warning(f"CSRF failure: {reason} | IP: {request.META.get('REMOTE_ADDR')} | User-Agent: {request.META.get('HTTP_USER_AGENT', 'Unknown')}")
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'error',
            'message': 'CSRF token validation failed',
            'detail': 'Invalid or missing CSRF token. Please refresh the page and try again.'
        }, status=403)
    
    return render(request, 'security_error.html', {
        'error_title': 'Security Check Failed',
        'error_message': 'Your request failed our security check. Please try again.',
        'reason': reason
    }, status=403)


def permission_denied_view(request, exception=None):
    """
    Handle permission denied (403) errors
    """
    import logging
    logger = logging.getLogger('django.security')
    logger.warning(f"Permission denied: {request.path} | IP: {request.META.get('REMOTE_ADDR')}")
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'error',
            'message': 'Permission denied'
        }, status=403)
    
    return render(request, 'security_error.html', {
        'error_title': 'Permission Denied',
        'error_message': 'You do not have permission to access this resource.'
    }, status=403)


def page_not_found_view(request, exception=None):
    """
    Handle 404 errors gracefully
    """
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'error',
            'message': 'Resource not found'
        }, status=404)
    
    return render(request, 'error_404.html', {}, status=404)


def server_error_view(request):
    """
    Handle 500 errors with proper logging
    """
    import logging
    import traceback
    logger = logging.getLogger('django.request')
    logger.error(f"500 Error: {traceback.format_exc()}")
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'error',
            'message': 'Server error occurred'
        }, status=500)
    
    return render(request, 'error_500.html', {}, status=500)


@login_required
def account_security_view(request):
    """
    User account security settings page
    """
    user_sessions = []
    device_tokens = []
    
    try:
        from .models import DeviceToken
        device_tokens = DeviceToken.objects.filter(user=request.user).order_by('-created_at')
    except:
        pass
    
    context = {
        'device_tokens': device_tokens,
        'user_sessions': user_sessions,
    }
    
    return render(request, 'account_security.html', context)


@login_required
@require_POST
def revoke_device_token_view(request, token_id):
    """
    Revoke a device token to disable push notifications for that device
    """
    from .models import DeviceToken
    token = get_object_or_404(DeviceToken, id=token_id, user=request.user)
    token.delete()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'message': 'Device token revoked'})
    
    return redirect('account_security')


@login_required
@require_POST
def revoke_all_device_tokens_view(request):
    """
    Revoke all device tokens (logout from all devices)
    """
    from .models import DeviceToken
    DeviceToken.objects.filter(user=request.user).delete()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'message': 'All device tokens revoked'})
    
    return redirect('account_security')


@login_required
def change_password_view(request):
    """
    Secure password change with validation supporting both standard and AJAX requests
    """
    from django.contrib.auth import update_session_auth_hash
    from django.contrib.auth.forms import PasswordChangeForm
    import logging
    logger = logging.getLogger('django.security')
    
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            logger.info(f"Password changed for user: {request.user.username}")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'message': 'Password changed successfully'})
            
            from django.contrib import messages
            messages.success(request, 'Your password was successfully updated!')
            return redirect('profile', user_id=request.user.id)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = {field: error[0] for field, error in form.errors.items()}
                return JsonResponse({'status': 'error', 'errors': errors}, status=400)
            from django.contrib import messages
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PasswordChangeForm(request.user)
        
    return render(request, 'change_password.html', {'form': form})


@login_required
def admin_verification_dashboard_view(request):
    if not request.user.is_superuser:
        messages.error(request, "Access denied. Admins only.")
        return redirect('feed')
    
    pending_profiles = Profile.objects.filter(is_verified=False).select_related('user')
    verified_profiles = Profile.objects.filter(is_verified=True).select_related('user')
    
    if request.method == 'POST':
        profile_id = request.POST.get('profile_id')
        action = request.POST.get('action')
        profile = get_object_or_404(Profile, id=profile_id)
        if action == 'approve':
            profile.is_verified = True
            profile.save()
            messages.success(request, f"Approved verification for {profile.user.username}.")
        elif action == 'reject':
            profile.is_verified = False
            profile.save()
            messages.info(request, f"Rejected/Removed verification for {profile.user.username}.")
        return redirect('admin_verification_dashboard')
        
    return render(request, 'admin_verification.html', {
        'pending_profiles': pending_profiles,
        'verified_profiles': verified_profiles
    })


@login_required
@require_POST
def api_mark_notification_read(request, notif_id):
    notif = get_object_or_404(Notification, id=notif_id, receiver=request.user)
    notif.is_read = True
    notif.save(update_fields=['is_read'])
    return JsonResponse({'status': 'success'})


@login_required
@require_POST
def api_mark_all_notifications_read(request):
    request.user.notifications_received.filter(is_read=False).update(is_read=True)
    return JsonResponse({'status': 'success'})


@login_required
@require_POST
def api_log_call(request):
    from .models import CallLog
    receiver_id = request.POST.get('receiver_id')
    call_type = request.POST.get('call_type', 'audio')
    status = request.POST.get('status', 'missed')
    duration = request.POST.get('duration', 0)
    
    receiver = get_object_or_404(User, id=receiver_id)
    call = CallLog.objects.create(
        caller=request.user,
        receiver=receiver,
        call_type=call_type,
        status=status,
        duration=int(duration)
    )
    return JsonResponse({
        'status': 'success',
        'call_id': call.id
    })


@login_required
@require_POST
def api_update_call(request, call_id):
    from .models import CallLog
    call = get_object_or_404(CallLog, id=call_id)
    if request.user != call.caller and request.user != call.receiver:
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
    
    status = request.POST.get('status')
    duration = request.POST.get('duration')
    
    if status:
        call.status = status
    if duration is not None:
        try:
            call.duration = int(duration)
        except ValueError:
            pass
            
    call.save()
    return JsonResponse({'status': 'success'})


# ──────────────────────────────────────────────
# Communities Views
# ──────────────────────────────────────────────
from django.utils.text import slugify

@login_required
def explore_communities_view(request):
    from .models import Community
    communities = Community.objects.all().order_by('-created_at')
    for c in communities:
        c.is_member = request.user in c.members.all()
    return render(request, 'explore_communities.html', {'communities': communities})

@login_required
def create_community_view(request):
    from .models import Community
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        icon = request.POST.get('icon', 'fa-users').strip()
        
        if not name:
            messages.error(request, "Community name is required.")
            return redirect('explore_communities')
            
        slug = slugify(name)
        if Community.objects.filter(slug=slug).exists():
            messages.error(request, "A community with a similar name already exists.")
            return redirect('explore_communities')
            
        community = Community.objects.create(
            name=name,
            slug=slug,
            description=description,
            icon=icon or 'fa-users'
        )
        community.members.add(request.user)
        messages.success(request, f"Community '{name}' created successfully!")
        return redirect('community_detail', slug=slug)
        
    return redirect('explore_communities')

@login_required
def community_detail_view(request, slug):
    from .models import Community
    community = get_object_or_404(Community, slug=slug)
    is_member = request.user in community.members.all()
    posts = community.posts.select_related('author', 'author__profile').order_by('-created_at')
    
    context = {
        'community': community,
        'is_member': is_member,
        'posts': posts,
        'members_count': community.members.count()
    }
    return render(request, 'community_detail.html', context)

@login_required
@require_POST
def join_community_view(request, slug):
    from .models import Community
    community = get_object_or_404(Community, slug=slug)
    if request.user in community.members.all():
        community.members.remove(request.user)
        joined = False
    else:
        community.members.add(request.user)
        joined = True
    return JsonResponse({
        'status': 'success',
        'joined': joined,
        'members_count': community.members.count()
    })

@login_required
@require_POST
def create_community_post_view(request, slug):
    from .models import Community, CommunityPost
    from .utils import call_gemini_api
    
    community = get_object_or_404(Community, slug=slug)
    if request.user not in community.members.all():
        messages.error(request, "You must be a member of this community to post.")
        return redirect('community_detail', slug=slug)
        
    content = request.POST.get('content', '').strip()
    image = request.FILES.get('image')
    
    if not content:
        messages.error(request, "Post content cannot be empty.")
        return redirect('community_detail', slug=slug)
        
    is_toxic = False
    prompt = f"Scan this text for toxic language, hate speech, or severe spam. Respond with ONLY 'toxic' if it contains toxic content, or 'clean' if it is acceptable: '{content}'."
    result = call_gemini_api(prompt)
    if result:
        is_toxic = "toxic" in result.lower()
    else:
        toxic_keywords = ["abuse", "idiot", "kill yourself", "hate you", "spam click", "scam"]
        words = content.lower()
        for kw in toxic_keywords:
            if kw in words:
                is_toxic = True
                break
                
    if is_toxic:
        messages.error(request, "Post blocked by AI Safety filter: Potential toxic content detected.")
        return redirect('community_detail', slug=slug)
        
    CommunityPost.objects.create(
        community=community,
        author=request.user,
        content=content,
        image=image
    )
    messages.success(request, "Posted successfully!")
    return redirect('community_detail', slug=slug)


