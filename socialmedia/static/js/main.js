// CSRF helper for Django POST requests
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Global Headers Configuration for AJAX
const csrfToken = getCookie('csrftoken');

// Theme Management
const themeToggleBtns = document.querySelectorAll('.theme-toggle-btn');
const themeIcon = document.getElementById('theme-toggle-icon');
const themeText = document.getElementById('theme-toggle-text');

function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    
    if (themeIcon) {
        if (theme === 'dark') {
            themeIcon.className = 'fas fa-sun';
            if (themeText) themeText.textContent = 'Light Mode';
        } else {
            themeIcon.className = 'fas fa-moon';
            if (themeText) themeText.textContent = 'Dark Mode';
        }
    }
}

// Initialize Theme
const savedTheme = localStorage.getItem('theme') || 'dark';
applyTheme(savedTheme);

if (themeToggleBtns.length > 0) {
    themeToggleBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const current = localStorage.getItem('theme') || 'dark';
            applyTheme(current === 'dark' ? 'light' : 'dark');
        });
    });
}

// AJAX Liking System
document.addEventListener('click', function(e) {
    const likeBtn = e.target.closest('.like-btn');
    if (likeBtn) {
        e.preventDefault();
        const postId = likeBtn.dataset.postId;
        
        fetch(`/like/${postId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) throw new Error('Network error');
            return response.json();
        })
        .then(data => {
            const countSpan = likeBtn.querySelector('.like-count');
            const heartIcon = likeBtn.querySelector('i');
            
            if (countSpan) countSpan.textContent = data.likes_count;
            
            if (data.liked) {
                likeBtn.classList.add('liked');
                heartIcon.className = 'fas fa-heart';
            } else {
                likeBtn.classList.remove('liked');
                heartIcon.className = 'far fa-heart';
            }
        })
        .catch(err => console.error('Error liking post:', err));
    }
});

// AJAX Follow System
document.addEventListener('click', function(e) {
    const followBtn = e.target.closest('.follow-toggle-btn');
    if (followBtn) {
        e.preventDefault();
        const userId = followBtn.dataset.userId;
        
        fetch(`/follow/${userId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) throw new Error('Network error');
            return response.json();
        })
        .then(data => {
            // Update all buttons targeting this user ID on the page (e.g. sidebar and profile view)
            const matchingButtons = document.querySelectorAll(`.follow-toggle-btn[data-user-id="${userId}"]`);
            matchingButtons.forEach(btn => {
                btn.classList.remove('following', 'requested');
                if (data.is_following) {
                    btn.classList.add('following');
                    btn.innerHTML = '<i class="fas fa-user-check" style="margin-right:0.3rem;font-size:0.8rem;"></i>Following';
                } else if (data.is_requested) {
                    btn.classList.add('requested');
                    btn.innerHTML = '<i class="fas fa-user-clock" style="margin-right:0.3rem;font-size:0.8rem;"></i>Requested';
                } else {
                    btn.innerHTML = '<i class="fas fa-user-plus" style="margin-right:0.3rem;font-size:0.8rem;"></i>Follow';
                }
            });
            
            // If we are on the profile page, update the follower count display
            const followerCountSpan = document.getElementById('profile-follower-count');
            if (followerCountSpan) {
                followerCountSpan.textContent = data.followers_count;
            }
        })
        .catch(err => console.error('Error toggling follow:', err));
    }
});

// AJAX Comment Submission
const commentForm = document.getElementById('ajax-comment-form');
if (commentForm) {
    commentForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const postId = this.dataset.postId;
        const formData = new FormData(this);
        
        fetch(`/comment/${postId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken
            },
            body: formData
        })
        .then(response => {
            if (!response.ok) throw new Error('Network error');
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                // Clear input
                const commentInput = commentForm.querySelector('.comment-input-field');
                commentInput.value = '';
                
                // Add new comment to DOM list
                const commentsList = document.getElementById('comments-list');
                const emptyMessage = document.getElementById('empty-comments-message');
                
                if (emptyMessage) emptyMessage.remove();
                
                const commentHtml = `
                    <div class="comment-item">
                        <div class="user-avatar-container" style="width: 32px; height: 32px;">
                            <img src="${data.profile_image}" class="user-avatar" alt="${data.author}">
                        </div>
                        <div class="comment-body">
                            <div class="comment-author-row">
                                <a href="/profile/${data.author_id}/" class="comment-author-name">${data.author}</a>
                                <span class="comment-time">${data.created_at}</span>
                            </div>
                            <div class="comment-text">${escapeHtml(data.comment)}</div>
                        </div>
                    </div>
                `;
                
                if (commentsList) {
                    commentsList.insertAdjacentHTML('beforeend', commentHtml);
                }
                
                // Update comment counter in detail header
                const commentCounterSpan = document.getElementById('post-comment-counter');
                if (commentCounterSpan) {
                    const count = parseInt(commentCounterSpan.textContent) || 0;
                    commentCounterSpan.textContent = count + 1;
                }
            } else {
                alert('Failed to send comment.');
            }
        })
        .catch(err => console.error('Error posting comment:', err));
    });
}

// Unread Notifications Polling / Checker
function checkUnreadNotifications() {
    const badge = document.getElementById('nav-notifications-badge');
    if (!badge) return; // Only run if notifications badge element is present (user logged in)
    
    fetch('/notifications/unread-count/')
    .then(response => {
        if (response.ok) return response.json();
    })
    .then(data => {
        if (data && data.unread_count > 0) {
            badge.textContent = data.unread_count;
            badge.style.display = 'block';
        } else {
            badge.style.display = 'none';
        }
    })
    .catch(err => console.error('Error fetching unread notification count:', err));
}

// Initial check and set interval for notifications (every 30 seconds)
if (document.getElementById('nav-notifications-badge')) {
    checkUnreadNotifications();
    setInterval(checkUnreadNotifications, 30000);
}

// Utility function to escape HTML string to avoid XSS injections
function escapeHtml(unsafe) {
    return unsafe
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}

// Post Creation Form: Preview upload image dynamically
const postImageInput = document.getElementById('post-image-input');
const imagePreviewContainer = document.getElementById('image-preview-container');
const imagePreview = document.getElementById('image-preview');
const removePreviewBtn = document.getElementById('image-preview-remove');

if (postImageInput && imagePreviewContainer && imagePreview) {
    postImageInput.addEventListener('change', function() {
        const file = this.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                imagePreview.src = e.target.result;
                imagePreviewContainer.style.display = 'block';
            };
            reader.readAsDataURL(file);
        }
    });
}

if (removePreviewBtn && postImageInput && imagePreviewContainer) {
    removePreviewBtn.addEventListener('click', function() {
        postImageInput.value = '';
        imagePreviewContainer.style.display = 'none';
    });
}

// Real-time post checker (for feed page)
let lastCheckedTime = new Date().toISOString();

function checkNewPosts() {
    const feedContainer = document.querySelector('.feed-posts-list');
    if (!feedContainer) return;
    
    fetch(`/check-new/?since=${encodeURIComponent(lastCheckedTime)}`)
    .then(response => {
        if (response.ok) return response.json();
    })
    .then(data => {
        if (data && data.new_posts) {
            showNewPostsToast();
        }
    })
    .catch(err => console.error('Error checking for new posts:', err));
}

function showNewPostsToast() {
    if (document.getElementById('new-posts-toast')) return;
    
    const toast = document.createElement('div');
    toast.id = 'new-posts-toast';
    toast.className = 'toast-notification glass-panel';
    toast.style.cssText = `
        position: fixed;
        top: 1.5rem;
        left: 50%;
        transform: translateX(-50%);
        z-index: 9999;
        padding: 0.75rem 1.5rem;
        display: flex;
        align-items: center;
        gap: 0.65rem;
        border: 1px solid rgba(124,58,237,0.3);
        box-shadow: 0 10px 40px rgba(124,58,237,0.25);
        cursor: pointer;
        animation: slideDown 0.4s cubic-bezier(0.16,1,0.3,1);
        white-space: nowrap;
        font-size: 0.9rem;
        font-weight: 600;
        color: var(--text-primary);
        background: var(--glass-bg);
        backdrop-filter: blur(20px);
        border-radius: 14px;
    `;
    
    toast.innerHTML = `
        <span style="font-size:1.1rem;">✨</span>
        <span>New posts available — <u style="cursor:pointer;">click to refresh</u></span>
    `;
    
    toast.addEventListener('click', () => {
        window.location.reload();
    });
    
    document.body.appendChild(toast);
    
    // Auto-dismiss after 8 seconds
    setTimeout(() => {
        if (toast.parentNode) {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.4s ease';
            setTimeout(() => toast.remove(), 400);
        }
    }, 8000);
}

// Start polling checker every 10 seconds if on feed page
if (document.querySelector('.feed-posts-list')) {
    // Check every 10 seconds
    setInterval(checkNewPosts, 10000);
}

// Unread Messages Count Polling / Checker
function checkUnreadMessages() {
    const badge = document.getElementById('nav-messages-badge');
    if (!badge) return; // Only run if badge element is present (user logged in)
    
    fetch('/messages/unread-count/')
    .then(response => {
        if (response.ok) return response.json();
    })
    .then(data => {
        if (data && data.unread_count > 0) {
            badge.textContent = data.unread_count;
            badge.style.display = 'block';
        } else {
            badge.style.display = 'none';
        }
    })
    .catch(err => console.error('Error fetching unread message count:', err));
}

// Initial check and set interval for messages (every 10 seconds)
if (document.getElementById('nav-messages-badge')) {
    checkUnreadMessages();
    setInterval(checkUnreadMessages, 10000);
}

// AJAX Follow Request Accept/Decline
document.addEventListener('click', function(e) {
    const acceptBtn = e.target.closest('.accept-request-btn');
    const declineBtn = e.target.closest('.decline-request-btn');
    
    if (acceptBtn || declineBtn) {
        e.preventDefault();
        const btn = acceptBtn || declineBtn;
        const requestId = btn.dataset.requestId;
        const action = acceptBtn ? 'accept' : 'decline';
        
        fetch(`/follow-request/${action}/${requestId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) throw new Error('Network error');
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                const actionsDiv = document.getElementById(`actions-${requestId}`);
                const statusSpan = document.getElementById(`status-${requestId}`);
                
                if (actionsDiv && statusSpan) {
                    actionsDiv.style.display = 'none';
                    statusSpan.style.display = 'block';
                    if (action === 'accept') {
                        statusSpan.style.color = 'var(--accent-success)';
                        statusSpan.innerHTML = '<i class="fas fa-check-circle"></i> Request Accepted';
                    } else {
                        statusSpan.style.color = 'var(--text-secondary)';
                        statusSpan.innerHTML = '<i class="fas fa-times-circle"></i> Request Declined';
                    }
                }
            }
        })
        .catch(err => console.error('Error handling follow request:', err));
    }
});


/* ===================================================
   NEW ENHANCED FEATURES logic
   =================================================== */

// --- Stories viewer state ---
let activeStories = [];
let currentStoryIndex = 0;
let storyTimer = null;
let storyProgressInterval = null;
let currentProgressPercent = 0;
const STORY_DURATION = 5000;

function openStoryUploadModal() {
    const modal = document.getElementById('story-upload-modal');
    if (modal) modal.style.display = 'flex';
}

function closeStoryUploadModal() {
    const modal = document.getElementById('story-upload-modal');
    if (modal) modal.style.display = 'none';
}

function viewStories(userId) {
    fetch(`/profile/${userId}/stories/`)
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success' && data.stories.length > 0) {
            activeStories = data.stories;
            currentStoryIndex = 0;
            showStory(currentStoryIndex);
            
            const ring = document.querySelector(`.story-item-container[onclick="viewStories(${userId})"] .story-avatar-ring`);
            if (ring) {
                ring.classList.remove('unviewed');
                ring.classList.add('viewed');
            }
        }
    })
    .catch(err => console.error('Error fetching stories:', err));
}

function showStory(index) {
    if (index < 0 || index >= activeStories.length) {
        closeStoryViewer();
        return;
    }
    currentStoryIndex = index;
    const story = activeStories[index];
    
    const modal = document.getElementById('story-viewer-modal');
    const avatar = document.getElementById('story-viewer-avatar');
    const username = document.getElementById('story-viewer-username');
    const time = document.getElementById('story-viewer-time');
    const image = document.getElementById('story-viewer-img');
    const caption = document.getElementById('story-viewer-caption');
    const captionContainer = document.getElementById('story-viewer-caption-container');
    const deleteBtn = document.getElementById('story-delete-btn');
    
    if (modal) modal.style.display = 'flex';
    if (avatar) avatar.src = story.author_avatar;
    if (username) username.textContent = story.author_username;
    if (time) time.textContent = story.time_ago;
    if (image) image.src = story.image_url;
    
    if (story.caption) {
        if (caption) caption.textContent = story.caption;
        if (captionContainer) captionContainer.style.display = 'block';
    } else {
        if (captionContainer) captionContainer.style.display = 'none';
    }
    
    // Toggle delete button visibility based on ownership
    const currentUsernameSummary = document.querySelector('.user-profile-summary .user-name');
    const currentUsername = currentUsernameSummary ? currentUsernameSummary.textContent.trim() : '';
    if (deleteBtn) {
        if (story.author_username === currentUsername) {
            deleteBtn.href = `/stories/${story.id}/delete/`;
            deleteBtn.style.display = 'block';
        } else {
            deleteBtn.style.display = 'none';
        }
    }
    
    setupProgressBars();
    startStoryTimer();
}

function setupProgressBars() {
    const container = document.getElementById('story-progress-container');
    if (!container) return;
    container.innerHTML = '';
    
    for (let i = 0; i < activeStories.length; i++) {
        const bar = document.createElement('div');
        bar.className = 'story-progress-bar';
        const fill = document.createElement('div');
        fill.className = 'story-progress-fill';
        
        if (i < currentStoryIndex) {
            fill.style.width = '100%';
        } else if (i > currentStoryIndex) {
            fill.style.width = '0%';
        }
        
        bar.appendChild(fill);
        container.appendChild(bar);
    }
}

function startStoryTimer() {
    clearInterval(storyProgressInterval);
    clearTimeout(storyTimer);
    
    currentProgressPercent = 0;
    const fills = document.querySelectorAll('.story-progress-fill');
    const activeFill = fills[currentStoryIndex];
    
    const intervalMs = 50;
    const step = (intervalMs / STORY_DURATION) * 100;
    
    storyProgressInterval = setInterval(() => {
        currentProgressPercent += step;
        if (currentProgressPercent >= 100) {
            currentProgressPercent = 100;
            clearInterval(storyProgressInterval);
        }
        if (activeFill) activeFill.style.width = `${currentProgressPercent}%`;
    }, intervalMs);
    
    storyTimer = setTimeout(() => {
        nextStory();
    }, STORY_DURATION);
}

function nextStory() {
    if (currentStoryIndex < activeStories.length - 1) {
        showStory(currentStoryIndex + 1);
    } else {
        closeStoryViewer();
    }
}

function prevStory() {
    if (currentStoryIndex > 0) {
        showStory(currentStoryIndex - 1);
    } else {
        showStory(0);
    }
}

function closeStoryViewer() {
    const modal = document.getElementById('story-viewer-modal');
    if (modal) modal.style.display = 'none';
    clearInterval(storyProgressInterval);
    clearTimeout(storyTimer);
}

function handleStoryTap(event) {
    const rect = event.currentTarget.getBoundingClientRect();
    const clickX = event.clientX - rect.left;
    const width = rect.width;
    
    if (clickX < width / 3) {
        prevStory();
    } else {
        nextStory();
    }
}

// --- Profile tab switcher ---
function switchProfileTab(tabName) {
    const tabs = document.querySelectorAll('.profile-tab-btn');
    const contents = document.querySelectorAll('.profile-tab-content');
    
    tabs.forEach(tab => {
        tab.classList.remove('active');
        tab.style.borderBottom = '3px solid transparent';
        tab.style.color = 'var(--text-secondary)';
    });
    
    contents.forEach(content => {
        content.style.display = 'none';
    });
    
    const activeTab = document.getElementById(`tab-btn-${tabName}`);
    const activeContent = document.getElementById(`profile-${tabName}-content`);
    
    if (activeTab && activeContent) {
        activeTab.classList.add('active');
        activeTab.style.borderBottom = '3px solid var(--accent)';
        activeTab.style.color = 'var(--text-primary)';
        activeContent.style.display = 'block';
    }
}

// --- AJAX Reactions ---
document.addEventListener('click', function(e) {
    const emojiBtn = e.target.closest('.reaction-emoji-btn');
    if (emojiBtn) {
        e.preventDefault();
        const postId = emojiBtn.dataset.postId;
        const reactionType = emojiBtn.dataset.reaction;
        
        const formData = new FormData();
        formData.append('reaction_type', reactionType);
        
        fetch(`/react/${postId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken
            },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            
            const postCard = document.getElementById(`post-${postId}`);
            if (postCard) {
                const currentReactionSpan = postCard.querySelector('.current-user-reaction');
                if (currentReactionSpan) {
                    if (data.reaction_emoji) {
                        currentReactionSpan.innerHTML = data.reaction_emoji;
                    } else {
                        currentReactionSpan.innerHTML = '<i class="far fa-smile"></i>';
                    }
                }
                
                const summaryDiv = postCard.querySelector('.post-reactions-summary');
                if (summaryDiv) {
                    summaryDiv.innerHTML = '';
                    const counts = data.reaction_counts;
                    let hasReactions = false;
                    for (const [emoji, count] of Object.entries(counts)) {
                        hasReactions = true;
                        summaryDiv.insertAdjacentHTML('beforeend', `
                            <span class="reaction-summary-badge" title="${count} user(s)">
                                ${emoji} <span class="badge-count">${count}</span>
                            </span>
                        `);
                    }
                    summaryDiv.style.display = hasReactions ? 'flex' : 'none';
                }
            }
        })
        .catch(err => console.error('Error reacting:', err));
    }
});

// --- AJAX Bookmarks ---
document.addEventListener('click', function(e) {
    const bookmarkBtn = e.target.closest('.bookmark-btn');
    if (bookmarkBtn) {
        e.preventDefault();
        const postId = bookmarkBtn.dataset.postId;
        
        fetch(`/bookmark/${postId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            
            const icon = bookmarkBtn.querySelector('i');
            if (data.bookmarked) {
                bookmarkBtn.classList.add('bookmarked');
                icon.className = 'fas fa-bookmark';
            } else {
                bookmarkBtn.classList.remove('bookmarked');
                icon.className = 'far fa-bookmark';
            }
        })
        .catch(err => console.error('Error bookmarking:', err));
    }
});

// --- Share post (clipboard copy) ---
document.addEventListener('click', function(e) {
    const shareBtn = e.target.closest('.share-post-btn');
    if (shareBtn) {
        e.preventDefault();
        const postUrl = shareBtn.dataset.postUrl;
        navigator.clipboard.writeText(postUrl).then(() => {
            showToastMessage('📋 Link copied to clipboard!');
        }).catch(err => {
            console.error('Failed to copy link: ', err);
        });
    }
});

function showToastMessage(msg) {
    const toast = document.createElement('div');
    toast.className = 'toast-notification glass-panel';
    toast.style.cssText = `
        position: fixed; top: 1.5rem; left: 50%; transform: translateX(-50%);
        z-index: 9999; padding: 0.75rem 1.5rem; display: flex; align-items: center;
        gap: 0.65rem; border: 1px solid rgba(124,58,237,0.3);
        box-shadow: 0 10px 40px rgba(124,58,237,0.25);
        color: var(--text-primary); background: var(--glass-bg); backdrop-filter: blur(20px);
        border-radius: 14px; animation: slideDown 0.4s cubic-bezier(0.16,1,0.3,1);
    `;
    toast.innerHTML = `<span>✨</span><span>${msg}</span>`;
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.4s ease';
        setTimeout(() => toast.remove(), 400);
    }, 3500);
}

// --- Infinite Scroll ---
document.addEventListener('DOMContentLoaded', function() {
    const sentinel = document.getElementById('feed-infinite-scroll-sentinel');
    const loader = document.getElementById('feed-infinite-scroll-loader');
    const postsList = document.querySelector('.feed-posts-list');
    
    if (!sentinel || !postsList) return;
    
    let nextPage = 2;
    let isFetching = false;
    let hasMore = true;
    
    const urlParams = new URLSearchParams(window.location.search);
    const feedType = urlParams.get('feed') || 'all';
    
    const observer = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting && !isFetching && hasMore) {
            loadMorePosts();
        }
    }, {
        rootMargin: '150px'
    });
    
    observer.observe(sentinel);
    
    function loadMorePosts() {
        isFetching = true;
        loader.style.display = 'flex';
        
        fetch(`/feed/api/?feed=${feedType}&page=${nextPage}`)
        .then(res => {
            if (!res.ok) throw new Error('Failed to fetch page');
            return res.json();
        })
        .then(data => {
            isFetching = false;
            loader.style.display = 'none';
            
            if (data.html && data.html.trim() !== '') {
                postsList.insertAdjacentHTML('beforeend', data.html);
                nextPage++;
                hasMore = data.has_next;
            } else {
                hasMore = false;
            }
            
            if (!hasMore) {
                observer.unobserve(sentinel);
                sentinel.remove();
            }
        })
        .catch(err => {
            console.error('Error fetching pagination:', err);
            isFetching = false;
            loader.style.display = 'none';
        });
    }
});


