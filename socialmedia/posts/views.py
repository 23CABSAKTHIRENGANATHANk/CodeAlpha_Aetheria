from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db import models
from django.contrib.auth.models import User
from .models import Post, Comment, Like, Hashtag, Bookmark, Reaction
from .forms import PostForm, CommentForm
from users.models import Follow, Notification, Story
from django.utils import timezone

def annotate_posts_for_user(posts, user):
    if not user.is_authenticated:
        return posts
    liked_post_ids = set(Like.objects.filter(user=user, post__in=posts).values_list('post_id', flat=True))
    bookmarked_post_ids = set(Bookmark.objects.filter(user=user, post__in=posts).values_list('post_id', flat=True))
    user_reactions = dict(Reaction.objects.filter(user=user, post__in=posts).values_list('post_id', 'reaction_type'))
    emoji_map = {
        'like':  '❤️',
        'love':  '😍',
        'laugh': '😂',
        'wow':   '😮',
        'sad':   '😢',
        'fire':  '🔥',
    }
    for post in posts:
        post.is_liked = post.id in liked_post_ids
        post.is_bookmarked = post.id in bookmarked_post_ids
        post.user_reaction_emoji = emoji_map.get(user_reactions.get(post.id))
    return posts

@login_required
def feed_view(request):
    feed_type = request.GET.get('feed', 'all')
    
    # 1. Fetch posts based on filter type
    if feed_type == 'following':
        followed_ids = Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
        posts = Post.objects.filter(
            models.Q(author_id__in=followed_ids) | models.Q(author=request.user)
        ).distinct().order_by('-created_at')
    else:
        followed_ids = Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
        posts = Post.objects.filter(
            models.Q(author=request.user) |
            models.Q(author__profile__is_private=False) |
            models.Q(author_id__in=followed_ids)
        ).distinct().order_by('-created_at')
        
    # Paginate posts (initial load page 1)
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    paginator = Paginator(posts, 5) # 5 posts per page
    page = request.GET.get('page', 1)
    try:
        posts_page = paginator.page(page)
    except PageNotAnInteger:
        posts_page = paginator.page(1)
    except EmptyPage:
        posts_page = paginator.page(paginator.num_pages)

    # Annotate page posts
    posts_page.object_list = annotate_posts_for_user(list(posts_page.object_list), request.user)

    # 2. Get active stories of users followed + self (not expired)
    now = timezone.now()
    active_stories = Story.objects.filter(
        models.Q(author_id__in=followed_ids) | models.Q(author=request.user),
        expires_at__gt=now
    ).select_related('author', 'author__profile').order_by('-created_at')

    # Group stories by author
    from collections import defaultdict
    stories_by_user = defaultdict(list)
    for story in active_stories:
        stories_by_user[story.author].append(story)

    user_stories_list = []
    for author, stories in stories_by_user.items():
        has_unviewed = False
        for s in stories:
            if request.user not in s.viewers.all():
                has_unviewed = True
                break
        user_stories_list.append({
            'user': author,
            'stories': stories,
            'has_unviewed': has_unviewed,
            'latest_story': stories[0]
        })

    # Sort stories: own story first, then followed users sorted by latest story creation
    my_story_group = None
    other_stories_groups = []
    for item in user_stories_list:
        if item['user'] == request.user:
            my_story_group = item
        else:
            other_stories_groups.append(item)
    
    other_stories_groups.sort(key=lambda x: x['latest_story'].created_at, reverse=True)
    final_stories = []
    if my_story_group:
        final_stories.append(my_story_group)
    final_stories.extend(other_stories_groups)

    # 3. Get follow suggestions (users not followed yet, excluding self)
    suggestions = User.objects.exclude(
        models.Q(id__in=list(followed_ids)) | models.Q(id=request.user.id)
    )[:5]
    
    # 4. Post creation form
    post_form = PostForm()
    
    context = {
        'posts': posts_page,
        'post_form': post_form,
        'suggestions': suggestions,
        'feed_type': feed_type,
        'user_stories': final_stories,
    }
    return render(request, 'feed.html', context)

@login_required
def create_post_view(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            post.sync_hashtags() # Automatically parse and link hashtags
            return redirect('feed')
    return redirect('feed')

@login_required
def post_detail_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
    # Privacy check
    author = post.author
    is_following = Follow.objects.filter(follower=request.user, following=author).exists()
    if author.profile.is_private and author != request.user and not is_following:
        return redirect('profile', user_id=author.id)
        
    comments = post.comments.all().order_by('created_at')
    comment_form = CommentForm()
    
    # Annotate post for bookmarks/reactions
    annotate_posts_for_user([post], request.user)
    
    # Suggestions for the sidebar
    followed_ids = Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
    suggestions = User.objects.exclude(
        models.Q(id__in=list(followed_ids)) | models.Q(id=request.user.id)
    )[:5]
    
    context = {
        'post': post,
        'comments': comments,
        'comment_form': comment_form,
        'suggestions': suggestions
    }
    return render(request, 'post_detail.html', context)

@login_required
def delete_post_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if post.author == request.user:
        post.delete()
    return redirect('feed')

@login_required
@require_POST
def like_toggle_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
    # Privacy check
    is_following = Follow.objects.filter(follower=request.user, following=post.author).exists()
    if post.author.profile.is_private and post.author != request.user and not is_following:
        return JsonResponse({'error': 'You must follow this user to interact with this post.'}, status=403)
        
    like_rel = Like.objects.filter(post=post, user=request.user)
    
    if like_rel.exists():
        like_rel.delete()
        liked = False
    else:
        Like.objects.create(post=post, user=request.user)
        liked = True
        
        # Trigger notification to post author (if not liking own post)
        if post.author != request.user:
            Notification.objects.create(
                sender=request.user,
                receiver=post.author,
                notification_type='like',
                post=post
            )
            
    likes_count = post.likes.count()
    return JsonResponse({
        'liked': liked,
        'likes_count': likes_count
    })

@login_required
@require_POST
def add_comment_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
    # Privacy check
    is_following = Follow.objects.filter(follower=request.user, following=post.author).exists()
    if post.author.profile.is_private and post.author != request.user and not is_following:
        return JsonResponse({'error': 'You must follow this user to interact with this post.'}, status=403)
        
    form = CommentForm(request.POST)
    
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()
        
        # Trigger notification to post author (if not commenting on own post)
        if post.author != request.user:
            Notification.objects.create(
                sender=request.user,
                receiver=post.author,
                notification_type='comment',
                post=post
            )
            
        # Get comment author profile pic
        profile_image_url = '/static/images/default_profile.png'
        if hasattr(request.user, 'profile') and request.user.profile.profile_image:
            profile_image_url = request.user.profile.profile_image.url
            
        return JsonResponse({
            'status': 'success',
            'comment': comment.comment,
            'author': request.user.username,
            'author_id': request.user.id,
            'profile_image': profile_image_url,
            'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M')
        })
        
    return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

from django.utils import dateparse

@login_required
def check_new_posts(request):
    since_str = request.GET.get('since', '')
    if not since_str:
        return JsonResponse({'new_posts': False})
    
    # Parse ISO 8601 timestamp sent from JavaScript
    since = dateparse.parse_datetime(since_str)
    if not since:
        return JsonResponse({'new_posts': False})
        
    # Check if there are posts by other users newer than the timestamp (respecting privacy settings)
    followed_ids = Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
    new_posts_exist = Post.objects.filter(created_at__gt=since).exclude(author=request.user).filter(
        models.Q(author__profile__is_private=False) | models.Q(author_id__in=followed_ids)
    ).exists()
    return JsonResponse({'new_posts': new_posts_exist})

@login_required
def feed_api_view(request):
    feed_type = request.GET.get('feed', 'all')
    page = request.GET.get('page', 1)
    
    if feed_type == 'following':
        followed_ids = Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
        posts = Post.objects.filter(
            models.Q(author_id__in=followed_ids) | models.Q(author=request.user)
        ).distinct().order_by('-created_at')
    else:
        followed_ids = Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
        posts = Post.objects.filter(
            models.Q(author=request.user) |
            models.Q(author__profile__is_private=False) |
            models.Q(author_id__in=followed_ids)
        ).distinct().order_by('-created_at')
        
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    from django.template.loader import render_to_string
    
    paginator = Paginator(posts, 5)
    try:
        posts_page = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        return JsonResponse({'html': '', 'has_next': False})
        
    posts_page.object_list = annotate_posts_for_user(list(posts_page.object_list), request.user)
    
    html = ""
    for post in posts_page.object_list:
        html += render_to_string('post_card.html', {'post': post}, request=request)
        
    return JsonResponse({
        'html': html,
        'has_next': posts_page.has_next()
    })

@login_required
@require_POST
def bookmark_toggle_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    is_following = Follow.objects.filter(follower=request.user, following=post.author).exists()
    if post.author.profile.is_private and post.author != request.user and not is_following:
        return JsonResponse({'error': 'You must follow this user to interact with this post.'}, status=403)
        
    bookmark_rel = Bookmark.objects.filter(post=post, user=request.user)
    
    if bookmark_rel.exists():
        bookmark_rel.delete()
        bookmarked = False
    else:
        Bookmark.objects.create(post=post, user=request.user)
        bookmarked = True
        
    return JsonResponse({
        'bookmarked': bookmarked,
    })

@login_required
@require_POST
def react_to_post_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    is_following = Follow.objects.filter(follower=request.user, following=post.author).exists()
    if post.author.profile.is_private and post.author != request.user and not is_following:
        return JsonResponse({'error': 'You must follow this user to interact with this post.'}, status=403)
        
    reaction_type = request.POST.get('reaction_type')
    valid_types = [choice[0] for choice in Reaction.REACTION_CHOICES]
    if reaction_type not in valid_types:
        return JsonResponse({'error': 'Invalid reaction type.'}, status=400)
        
    reaction, created = Reaction.objects.get_or_create(
        post=post, user=request.user,
        defaults={'reaction_type': reaction_type}
    )
    
    if not created:
        if reaction.reaction_type == reaction_type:
            reaction.delete()
            reaction_type = None
        else:
            reaction.reaction_type = reaction_type
            reaction.save()
            
    if reaction_type and post.author != request.user:
        Notification.objects.create(
            sender=request.user,
            receiver=post.author,
            notification_type='like',
            post=post
        )
        
    counts = post.get_reaction_counts()
    
    emoji_map = {
        'like':  '❤️',
        'love':  '😍',
        'laugh': '😂',
        'wow':   '😮',
        'sad':   '😢',
        'fire':  '🔥',
    }
    
    return JsonResponse({
        'reaction_type': reaction_type,
        'reaction_emoji': emoji_map.get(reaction_type, ''),
        'reaction_counts': counts,
    })

@login_required
def hashtag_feed_view(request, tag):
    hashtag = get_object_or_404(Hashtag, name=tag.lower())
    followed_ids = Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
    posts = hashtag.posts.filter(
        models.Q(author=request.user) |
        models.Q(author__profile__is_private=False) |
        models.Q(author_id__in=followed_ids)
    ).distinct().order_by('-created_at')
    
    posts = annotate_posts_for_user(list(posts), request.user)
    
    context = {
        'hashtag': hashtag,
        'posts': posts,
    }
    return render(request, 'hashtag_feed.html', context)

@login_required
def explore_view(request):
    from django.db.models import Count
    trending_hashtags = Hashtag.objects.annotate(
        post_count=Count('posts')
    ).order_by('-post_count')[:10]
    
    followed_ids = Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
    popular_posts = Post.objects.filter(
        models.Q(author=request.user) |
        models.Q(author__profile__is_private=False) |
        models.Q(author_id__in=followed_ids)
    ).annotate(
        engagement=Count('likes', distinct=True) + Count('reactions', distinct=True)
    ).exclude(image='').order_by('-engagement', '-created_at')[:12]
    
    if not popular_posts.exists():
        popular_posts = Post.objects.filter(
            models.Q(author=request.user) |
            models.Q(author__profile__is_private=False) |
            models.Q(author_id__in=followed_ids)
        ).annotate(
            engagement=Count('likes', distinct=True) + Count('reactions', distinct=True)
        ).order_by('-engagement', '-created_at')[:12]
        
    popular_posts = annotate_posts_for_user(list(popular_posts), request.user)
    
    suggestions = User.objects.exclude(
        models.Q(id__in=list(followed_ids)) | models.Q(id=request.user.id)
    )[:6]
    
    context = {
        'trending_hashtags': trending_hashtags,
        'popular_posts': popular_posts,
        'suggestions': suggestions,
    }
    return render(request, 'explore.html', context)

@login_required
def search_posts_view(request):
    query = request.GET.get('q', '').strip()
    posts = []
    if query:
        followed_ids = Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
        posts = Post.objects.filter(
            models.Q(content__icontains=query)
        ).filter(
            models.Q(author=request.user) |
            models.Q(author__profile__is_private=False) |
            models.Q(author_id__in=followed_ids)
        ).distinct().order_by('-created_at')
        
        posts = annotate_posts_for_user(list(posts), request.user)
        
    context = {
        'query': query,
        'posts': posts,
    }
    return render(request, 'search_posts.html', context)

