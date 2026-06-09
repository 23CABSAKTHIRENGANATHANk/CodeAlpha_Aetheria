#!/usr/bin/env python
"""
Performance Testing and Debugging Script for Aetheria
Analyzes database queries, cache hit rates, and identifies N+1 problems
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'socialmedia.settings')
django.setup()

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.core.cache import cache
from django.contrib.auth.models import User
from posts.models import Post
from users.models import Follow, Story
from django.utils import timezone
import json
from datetime import timedelta

def print_section(title):
    print(f"\n{'='*70}")
    print(f" {title}")
    print(f"{'='*70}")

def analyze_feed_queries():
    """Analyze query count for feed view"""
    print_section("FEED VIEW QUERY ANALYSIS")
    
    try:
        # Get a test user
        user = User.objects.first()
        if not user:
            print("❌ No users found in database. Create a test user first.")
            return
        
        print(f"\n📊 Analyzing queries for user: {user.username}")
        
        # Test feed view queries
        with CaptureQueriesContext(connection) as context:
            # Simulate feed_view logic
            followed_ids = list(Follow.objects.filter(follower=user).values_list('following_id', flat=True))
            
            # Get posts
            posts = Post.objects.filter(
                author_id__in=followed_ids
            ).select_related('author', 'author__profile')[:5]
            
            # Access data to trigger queries
            for post in posts:
                _ = post.author.username
                _ = post.author.profile.bio
            
            print(f"\n✓ Total Queries: {len(context)}")
            print(f"✓ Query Breakdown:")
            
            # Group queries by type
            query_types = {}
            for query in context:
                sql = query['sql']
                # Extract table name from SQL
                if 'FROM' in sql:
                    table = sql.split('FROM')[1].split()[0]
                    query_types[table] = query_types.get(table, 0) + 1
            
            for table, count in sorted(query_types.items()):
                print(f"  - {table}: {count}")
            
            # Show execution time
            total_time = sum(q['time'] for q in context)
            print(f"\n⏱️  Total Query Time: {total_time:.3f}s")
            
            if len(context) > 10:
                print(f"⚠️  WARNING: {len(context)} queries detected. Consider using select_related/prefetch_related")
            else:
                print(f"✅ Query count is optimized!")
                
    except Exception as e:
        print(f"❌ Error during analysis: {e}")

def check_cache_configuration():
    """Verify Redis/cache is properly configured"""
    print_section("CACHE CONFIGURATION CHECK")
    
    try:
        # Test cache operations
        test_key = 'aetheria:test_key'
        test_value = 'test_value_12345'
        
        # Set
        cache.set(test_key, test_value, 60)
        print("✓ Cache SET operation successful")
        
        # Get
        retrieved = cache.get(test_key)
        if retrieved == test_value:
            print("✓ Cache GET operation successful")
            print(f"✓ Cache backend: {cache.__class__.__name__}")
        else:
            print("❌ Cache GET returned unexpected value")
        
        # Cleanup
        cache.delete(test_key)
        
        # Test stats
        if hasattr(cache, 'get_stats'):
            stats = cache.get_stats()
            print(f"\n📊 Cache Statistics:")
            for key, value in stats.items():
                print(f"  - {key}: {value}")
        
    except Exception as e:
        print(f"❌ Cache error: {e}")

def analyze_database_indexes():
    """Check if all recommended indexes exist"""
    print_section("DATABASE INDEX ANALYSIS")
    
    try:
        from django.db import connection
        cursor = connection.cursor()
        
        # PostgreSQL specific queries
        if connection.vendor == 'postgresql':
            # Get all indexes
            cursor.execute("""
                SELECT schemaname, tablename, indexname 
                FROM pg_indexes 
                WHERE schemaname = 'public'
                ORDER BY tablename, indexname
            """)
            
            indexes = cursor.fetchall()
            print(f"\n✓ Total Indexes: {len(indexes)}")
            
            # Expected indexes for critical tables
            expected_tables = ['posts_post', 'users_user', 'posts_like', 'users_message']
            
            for table in expected_tables:
                table_indexes = [idx for idx in indexes if idx[1] == table]
                print(f"\n  {table}: {len(table_indexes)} indexes")
                for schema, table_name, idx_name in table_indexes[:5]:  # Show first 5
                    print(f"    - {idx_name}")
            
        else:
            print("⚠️  Not a PostgreSQL database. Skipping index analysis.")
            
    except Exception as e:
        print(f"❌ Error analyzing indexes: {e}")

def analyze_story_queries():
    """Analyze story fetching queries"""
    print_section("STORY QUERY ANALYSIS")
    
    try:
        user = User.objects.first()
        if not user:
            print("❌ No users found.")
            return
        
        with CaptureQueriesContext(connection) as context:
            now = timezone.now()
            
            # Old approach (N+1 problem)
            stories_old = Story.objects.filter(
                expires_at__gt=now
            ).select_related('author', 'author__profile')
            
            print(f"✓ Stories query: {len(context)} queries")
            
            # Check if viewer access causes additional queries
            old_count = len(context)
            
            for story in list(stories_old)[:3]:
                _ = list(story.viewers.all())  # This might cause N queries
            
            print(f"✓ After accessing viewers: {len(context)} queries")
            print(f"⚠️  Additional queries from viewer access: {len(context) - old_count}")
            
            # Optimized approach would use prefetch_related
            if len(context) - old_count > 0:
                print("\n💡 TIP: Use prefetch_related('viewers') to optimize viewer access")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def generate_performance_report():
    """Generate comprehensive performance report"""
    print_section("AETHERIA PERFORMANCE REPORT")
    
    try:
        # Database stats
        cursor = connection.cursor()
        
        if connection.vendor == 'postgresql':
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            """)
            
            print("\n📊 Database Table Sizes:")
            results = cursor.fetchall()
            for schema, table, size in results[:10]:
                print(f"  {table}: {size}")
            
            # Row counts
            print("\n📊 Record Counts:")
            tables_to_count = ['posts_post', 'posts_comment', 'users_user', 'posts_like']
            
            for table in tables_to_count:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  {table}: {count:,} records")
        
        print(f"\n✅ Performance report generated")
        
    except Exception as e:
        print(f"❌ Error generating report: {e}")

def show_query_stats(context):
    """Display detailed query statistics"""
    print("\n📈 Query Statistics:")
    print(f"  Total queries: {len(context)}")
    
    # Sort by execution time
    sorted_queries = sorted(context, key=lambda x: x['time'], reverse=True)
    
    print("\n  Top 5 slowest queries:")
    for i, query in enumerate(sorted_queries[:5], 1):
        print(f"    {i}. {query['time']:.3f}s - {query['sql'][:60]}...")

def main():
    """Run all performance analyses"""
    print("\n" + "="*70)
    print(" AETHERIA PERFORMANCE ANALYZER v1.0")
    print("="*70)
    print("\nRunning comprehensive performance diagnostics...\n")
    
    # Run analyses
    check_cache_configuration()
    analyze_database_indexes()
    analyze_feed_queries()
    analyze_story_queries()
    generate_performance_report()
    
    print("\n" + "="*70)
    print(" ANALYSIS COMPLETE")
    print("="*70)
    print("\n📋 Next Steps:")
    print("  1. Run: python manage.py create_database_indexes")
    print("  2. Monitor with: DEBUG=True python manage.py runserver (with django-debug-toolbar)")
    print("  3. Load test with: locust -f locustfile.py -u 100 -r 10")
    print("\n")

if __name__ == '__main__':
    main()
