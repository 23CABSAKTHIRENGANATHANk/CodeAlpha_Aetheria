# Graph Report - e:\project\project\social media  (2026-06-05)

## Corpus Check
- Corpus is ~34,712 words - fits in a single context window. You may not need a graph.

## Summary
- 217 nodes · 367 edges · 26 communities (13 shown, 13 thin omitted)
- Extraction: 74% EXTRACTED · 26% INFERRED · 0% AMBIGUOUS · INFERRED: 95 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_User Data and Admin|User Data and Admin]]
- [[_COMMUNITY_Frontend Interactions|Frontend Interactions]]
- [[_COMMUNITY_Post Data and Admin|Post Data and Admin]]
- [[_COMMUNITY_User Views and API|User Views and API]]
- [[_COMMUNITY_Post Views and API|Post Views and API]]
- [[_COMMUNITY_PWA Manifest|PWA Manifest]]
- [[_COMMUNITY_Post Test Suite|Post Test Suite]]
- [[_COMMUNITY_App Configuration|App Configuration]]
- [[_COMMUNITY_URL Routing|URL Routing]]
- [[_COMMUNITY_Django Manage Script|Django Manage Script]]
- [[_COMMUNITY_Build Script|Build Script]]
- [[_COMMUNITY_Database Migrations|Database Migrations]]
- [[_COMMUNITY_Database Migrations|Database Migrations]]
- [[_COMMUNITY_Database Migrations|Database Migrations]]
- [[_COMMUNITY_Database Migrations|Database Migrations]]
- [[_COMMUNITY_Database Migrations|Database Migrations]]
- [[_COMMUNITY_ASGI Config|ASGI Config]]
- [[_COMMUNITY_Settings Config|Settings Config]]
- [[_COMMUNITY_WSGI Config|WSGI Config]]
- [[_COMMUNITY_Service Worker|Service Worker]]
- [[_COMMUNITY_Database Migrations|Database Migrations]]

## God Nodes (most connected - your core abstractions)
1. `Post` - 23 edges
2. `Story` - 18 edges
3. `UserAppTests` - 18 edges
4. `Profile` - 17 edges
5. `Comment` - 16 edges
6. `Like` - 13 edges
7. `Follow` - 13 edges
8. `Notification` - 13 edges
9. `Message` - 12 edges
10. `FollowRequest` - 12 edges

## Surprising Connections (you probably didn't know these)
- `UserAppTests` --uses--> `Post`  [INFERRED]
  users/tests.py → posts/models.py
- `profile_view()` --calls--> `annotate_posts_for_user()`  [EXTRACTED]
  users/views.py → posts/views.py
- `PostForm` --uses--> `Comment`  [INFERRED]
  posts/forms.py → posts/models.py
- `PostForm` --uses--> `Post`  [INFERRED]
  posts/forms.py → posts/models.py
- `PostAppTests` --uses--> `Post`  [INFERRED]
  posts/tests.py → posts/models.py

## Import Cycles
- None detected.

## Communities (26 total, 13 thin omitted)

### Community 0 - "User Data and Admin"
Cohesion: 0.09
Nodes (25): FollowAdmin, FollowRequestAdmin, MessageAdmin, NotificationAdmin, ProfileAdmin, StoryAdmin, Meta, Follow (+17 more)

### Community 1 - "Frontend Interactions"
Cohesion: 0.08
Nodes (18): activeStories, closeStoryViewer(), commentForm, csrfToken, handleStoryTap(), imagePreview, imagePreviewContainer, lastCheckedTime (+10 more)

### Community 2 - "Post Data and Admin"
Cohesion: 0.17
Nodes (17): BookmarkAdmin, CommentAdmin, HashtagAdmin, LikeAdmin, PostAdmin, ReactionAdmin, CommentForm, Meta (+9 more)

### Community 3 - "User Views and API"
Cohesion: 0.09
Nodes (10): UserCreationForm, ProfileUpdateForm, StoryForm, UserRegisterForm, create_story_view(), edit_profile_view(), get_user_conversations(), messages_chat_view() (+2 more)

### Community 4 - "Post Views and API"
Cohesion: 0.18
Nodes (10): PostForm, annotate_posts_for_user(), create_post_view(), explore_view(), feed_api_view(), feed_view(), hashtag_feed_view(), post_detail_view() (+2 more)

### Community 5 - "PWA Manifest"
Cohesion: 0.20
Nodes (9): background_color, description, display, icons, name, orientation, short_name, start_url (+1 more)

### Community 6 - "Post Test Suite"
Cohesion: 0.22
Nodes (5): PostAppTests, Test that a post is created and saved correctly., Test like creation and unique constraints., Test comments creation on posts., TestCase

### Community 7 - "App Configuration"
Cohesion: 0.40
Nodes (3): AppConfig, PostsConfig, UsersConfig

## Knowledge Gaps
- **30 isolated node(s):** `build.sh script`, `Migration`, `Migration`, `Meta`, `csrfToken` (+25 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **13 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `UserAppTests` connect `User Data and Admin` to `Post Data and Admin`, `Post Test Suite`?**
  _High betweenness centrality (0.108) - this node is a cross-community bridge._
- **Why does `Post` connect `Post Data and Admin` to `User Data and Admin`, `User Views and API`, `Post Views and API`, `Post Test Suite`?**
  _High betweenness centrality (0.103) - this node is a cross-community bridge._
- **Why does `PostAppTests` connect `Post Test Suite` to `Post Data and Admin`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `Post` (e.g. with `BookmarkAdmin` and `CommentAdmin`) actually correct?**
  _`Post` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `Story` (e.g. with `FollowAdmin` and `FollowRequestAdmin`) actually correct?**
  _`Story` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `UserAppTests` (e.g. with `Post` and `Follow`) actually correct?**
  _`UserAppTests` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `Profile` (e.g. with `FollowAdmin` and `FollowRequestAdmin`) actually correct?**
  _`Profile` has 11 INFERRED edges - model-reasoned connections that need verification._