from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.contrib.auth.models import User
from .models import Profile, Follow, Notification, Message, FollowRequest
from posts.models import Like, Post
from django.db.models import Q
from django.utils import timezone
import datetime
from .forms import UserRegisterForm, ProfileUpdateForm

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
            form.save()
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
                return redirect('feed')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    auth_logout(request)
    return redirect('landing')

@login_required
def profile_view(request, user_id):
    profile_user = get_object_or_404(User, id=user_id)
    is_following = Follow.objects.filter(follower=request.user, following=profile_user).exists()
    
    # Privacy check
    is_locked = profile_user.profile.is_private and request.user != profile_user and not is_following
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
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            return redirect('profile', user_id=request.user.id)
    else:
        form = ProfileUpdateForm(instance=request.user.profile)
    return render(request, 'edit_profile.html', {'form': form})

@login_required
@require_POST
def follow_toggle_view(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    if target_user == request.user:
        return JsonResponse({'error': 'You cannot follow yourself.'}, status=400)
    
    follow_rel = Follow.objects.filter(follower=request.user, following=target_user)
    is_following = False
    is_requested = False
    status = ''
    
    if follow_rel.exists():
        follow_rel.delete()
        is_following = False
        status = 'unfollowed'
        # Optional: delete previous follow notification
        Notification.objects.filter(sender=request.user, receiver=target_user, notification_type='follow').delete()
    else:
        if target_user.profile.is_private:
            req_exists = FollowRequest.objects.filter(sender=request.user, receiver=target_user)
            if req_exists.exists():
                req_exists.delete()
                is_requested = False
                status = 'unrequested'
                # Delete follow request notification
                Notification.objects.filter(sender=request.user, receiver=target_user, notification_type='follow_request').delete()
            else:
                FollowRequest.objects.create(sender=request.user, receiver=target_user)
                is_requested = True
                status = 'requested'
                # Create follow request notification
                Notification.objects.create(
                    sender=request.user,
                    receiver=target_user,
                    notification_type='follow_request'
                )
        else:
            Follow.objects.create(follower=request.user, following=target_user)
            is_following = True
            status = 'following'
            # Send Notification
            Notification.objects.create(
                sender=request.user,
                receiver=target_user,
                notification_type='follow'
            )
        
    followers_count = target_user.follower_relations.count()
    return JsonResponse({
        'is_following': is_following,
        'is_requested': is_requested,
        'status': status,
        'followers_count': followers_count
    })

@login_required
def search_users_view(request):
    query = request.GET.get('q', '')
    results = []
    if query:
        results = User.objects.filter(username__icontains=query).exclude(id=request.user.id)
    
    # Suggestions for search page sidebar
    followed_ids = Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
    suggestions = User.objects.exclude(id__in=list(followed_ids) + [request.user.id])[:5]
    
    return render(request, 'search_results.html', {
        'results': results,
        'query': query,
        'suggestions': suggestions,
        'followed_user_ids': followed_ids
    })

@login_required
def notifications_view(request):
    notifications = request.user.notifications_received.all().order_by('-created_at')
    
    # Attach follow request IDs for rendering actions
    pending_requests = {r.sender_id: r.id for r in request.user.follow_requests_received.all()}
    for notif in notifications:
        if notif.notification_type == 'follow_request':
            notif.follow_request_id = pending_requests.get(notif.sender_id)
            
    # Mark all notifications as read when visiting notifications page
    request.user.notifications_received.filter(is_read=False).update(is_read=True)
    
    # Suggestions for notifications page sidebar
    followed_ids = Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
    suggestions = User.objects.exclude(id__in=list(followed_ids) + [request.user.id])[:5]
    
    return render(request, 'notifications.html', {
        'notifications': notifications,
        'suggestions': suggestions
    })

@login_required
def unread_notifications_count(request):
    count = request.user.notifications_received.filter(is_read=False).count()
    return JsonResponse({'unread_count': count})

# Direct Messaging View Helpers
def get_user_conversations(request_user):
    # Find all messages sent or received by this user
    messages = Message.objects.filter(Q(sender=request_user) | Q(receiver=request_user))
    conversed_user_ids = set()
    for msg in messages:
        if msg.sender != request_user:
            conversed_user_ids.add(msg.sender_id)
        if msg.receiver != request_user:
            conversed_user_ids.add(msg.receiver_id)
            
    # Include followed users to allow starting new conversations
    following_user_ids = Follow.objects.filter(follower=request_user).values_list('following_id', flat=True)
    all_target_user_ids = conversed_user_ids.union(set(following_user_ids))
    
    chat_users = User.objects.filter(id__in=all_target_user_ids).exclude(id=request_user.id)
    
    conversations = []
    for u in chat_users:
        last_msg = Message.objects.filter(
            (Q(sender=request_user) & Q(receiver=u)) | (Q(sender=u) & Q(receiver=request_user))
        ).order_by('-created_at').first()
        
        unread_count = Message.objects.filter(
            sender=u, receiver=request_user, is_read=False
        ).count()
        
        conversations.append({
            'user': u,
            'last_message': last_msg,
            'unread_count': unread_count,
            'last_msg_time': last_msg.created_at if last_msg else None
        })
        
    # Sort conversations: users with messages sorted by latest message, users with no messages sorted last
    # We use a default aware datetime for sorting none values
    default_date = timezone.make_aware(datetime.datetime.min + datetime.timedelta(days=365))
    conversations.sort(key=lambda x: x['last_msg_time'] or default_date, reverse=True)
    return conversations

@login_required
def messages_inbox_view(request):
    conversations = get_user_conversations(request.user)
    return render(request, 'messages.html', {
        'conversations': conversations,
        'active_chat': None
    })

@login_required
def messages_chat_view(request, user_id):
    active_chat_user = get_object_or_404(User, id=user_id)
    
    # Mark messages from active chat user as read
    Message.objects.filter(sender=active_chat_user, receiver=request.user, is_read=False).update(is_read=True)
    
    # Fetch inbox list
    conversations = get_user_conversations(request.user)
    
    # Fetch history
    chat_messages = Message.objects.filter(
        (Q(sender=request.user) & Q(receiver=active_chat_user)) | 
        (Q(sender=active_chat_user) & Q(receiver=request.user))
    ).order_by('created_at')
    
    # Messaging capability check (locked if target is private and not followed)
    is_following = Follow.objects.filter(follower=request.user, following=active_chat_user).exists()
    can_message = not (active_chat_user.profile.is_private and active_chat_user != request.user and not is_following)
    
    return render(request, 'messages.html', {
        'conversations': conversations,
        'active_chat_user': active_chat_user,
        'chat_messages': chat_messages,
        'active_chat': True,
        'can_message': can_message
    })

@login_required
@require_POST
def api_send_message(request, user_id):
    receiver = get_object_or_404(User, id=user_id)
    
    # Security check for private profile
    is_following = Follow.objects.filter(follower=request.user, following=receiver).exists()
    if receiver.profile.is_private and receiver != request.user and not is_following:
        return JsonResponse({'status': 'error', 'message': 'You must follow this user to send messages.'}, status=403)
        
    body = request.POST.get('body', '').strip()
    if not body:
        return JsonResponse({'status': 'error', 'message': 'Message body cannot be empty.'}, status=400)
        
    msg = Message.objects.create(
        sender=request.user,
        receiver=receiver,
        body=body
    )
    return JsonResponse({
        'status': 'success',
        'message_id': msg.id,
        'body': msg.body,
        'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
    })

@login_required
def api_fetch_messages(request, user_id):
    active_chat_user = get_object_or_404(User, id=user_id)
    since_str = request.GET.get('since', '')
    
    # Mark messages from active chat user as read
    Message.objects.filter(sender=active_chat_user, receiver=request.user, is_read=False).update(is_read=True)
    
    msgs_query = Message.objects.filter(
        sender=active_chat_user,
        receiver=request.user
    )
    
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
            'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
        
    return JsonResponse({
        'status': 'success',
        'messages': data,
        'timestamp': timezone.now().isoformat()
    })

@login_required
def api_unread_messages_count(request):
    count = Message.objects.filter(receiver=request.user, is_read=False).count()
    return JsonResponse({'unread_count': count})

@login_required
def followers_list_view(request, user_id):
    profile_user = get_object_or_404(User, id=user_id)
    
    # Gate check for private accounts
    is_following = Follow.objects.filter(follower=request.user, following=profile_user).exists()
    if profile_user.profile.is_private and profile_user != request.user and not is_following:
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
    if profile_user.profile.is_private and profile_user != request.user and not is_following:
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
    Notification.objects.create(
        sender=request.user,
        receiver=sender,
        notification_type='follow_accept'
    )
    
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

@login_required
def user_stories_view(request, user_id):
    author = get_object_or_404(User, id=user_id)
    is_following = Follow.objects.filter(follower=request.user, following=author).exists()
    if author.profile.is_private and author != request.user and not is_following:
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
            'image_url': s.image.url,
            'caption': s.caption,
            'created_at': s.created_at.strftime('%Y-%m-%d %H:%M'),
            'time_ago': s.created_at.strftime('%I:%M %p'),
            'author_username': author.username,
            'author_avatar': author.profile.profile_image.url if author.profile.profile_image else '/static/images/default_profile.png'
        })
    return JsonResponse({
        'status': 'success',
        'stories': data
    })

