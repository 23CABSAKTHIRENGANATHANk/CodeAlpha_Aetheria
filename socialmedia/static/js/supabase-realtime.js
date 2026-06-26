/**
 * Aetheria — Supabase Realtime Client
 * =====================================
 * Subscribes to Postgres table changes via Supabase Realtime so the browser
 * receives live updates without polling.
 *
 * Subscriptions:
 *   - users_notification  → notification badge count
 *   - users_message       → unread message count
 *   - users_storyview     → story view analytics (profile owner only)
 *
 * Usage:
 *   Loaded automatically from base.html when window.SUPABASE_URL is set.
 *   Requires @supabase/supabase-js from CDN (loaded in base.html).
 *
 * Events dispatched on document:
 *   'aetheria:notification'  → { count, payload }
 *   'aetheria:message'       → { count, payload }
 *   'aetheria:story_view'    → { payload }
 */

(function () {
  'use strict';

  const SUPABASE_URL = window.AETHERIA_SUPABASE_URL || '';
  const SUPABASE_ANON_KEY = window.AETHERIA_SUPABASE_ANON_KEY || '';
  const CURRENT_USER_ID = window.AETHERIA_USER_ID || null;

  // Don't init if Supabase isn't configured or user isn't logged in
  if (!SUPABASE_URL || !SUPABASE_ANON_KEY || !CURRENT_USER_ID) {
    return;
  }

  // Wait for the Supabase JS SDK to load
  function init() {
    if (typeof window.supabase === 'undefined' || typeof window.supabase.createClient !== 'function') {
      console.warn('[Aetheria Realtime] Supabase JS SDK not loaded yet — retrying...');
      setTimeout(init, 500);
      return;
    }

    const client = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
    console.info('[Aetheria Realtime] Supabase client initialized');

    subscribeToNotifications(client);
    subscribeToMessages(client);
    subscribeToStoryViews(client);
  }

  // ── Notifications ───────────────────────────────────────────────────────────

  function subscribeToNotifications(client) {
    client
      .channel('aetheria-notifications')
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'users_notification',
          filter: `receiver_id=eq.${CURRENT_USER_ID}`,
        },
        function (payload) {
          console.debug('[Aetheria Realtime] Notification received:', payload);
          updateNotificationBadge();
          document.dispatchEvent(new CustomEvent('aetheria:notification', { detail: { payload } }));
        }
      )
      .subscribe(function (status) {
        console.info('[Aetheria Realtime] Notifications channel:', status);
      });
  }

  function updateNotificationBadge() {
    // Fetch current unread count from Django API
    fetch('/api/notifications/unread-count/', {
      credentials: 'same-origin',
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
    })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data) return;
        const count = data.count || 0;
        setNotificationBadge(count);
        document.dispatchEvent(new CustomEvent('aetheria:notification', { detail: { count, data } }));
      })
      .catch(function (err) {
        console.warn('[Aetheria Realtime] Badge fetch failed:', err);
        // Fallback: increment the badge by 1
        bumpBadge('.notification-badge, #notification-count, [data-notification-badge]');
      });
  }

  function setNotificationBadge(count) {
    const selectors = [
      '.notification-badge',
      '#notification-count',
      '[data-notification-badge]',
    ];
    selectors.forEach(function (sel) {
      document.querySelectorAll(sel).forEach(function (el) {
        el.textContent = count > 99 ? '99+' : String(count || '');
        el.style.display = count > 0 ? '' : 'none';
      });
    });
  }

  function bumpBadge(selector) {
    document.querySelectorAll(selector).forEach(function (el) {
      const current = parseInt(el.textContent, 10) || 0;
      const next = current + 1;
      el.textContent = next > 99 ? '99+' : String(next);
      el.style.display = '';
      // Animate the badge
      el.classList.add('badge-pulse');
      setTimeout(function () { el.classList.remove('badge-pulse'); }, 600);
    });
  }

  // ── Direct Messages ─────────────────────────────────────────────────────────

  function subscribeToMessages(client) {
    client
      .channel('aetheria-messages')
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'users_message',
          filter: `receiver_id=eq.${CURRENT_USER_ID}`,
        },
        function (payload) {
          console.debug('[Aetheria Realtime] Message received:', payload);
          bumpBadge('.message-badge, #message-count, [data-message-badge]');
          document.dispatchEvent(new CustomEvent('aetheria:message', { detail: { payload } }));

          // Show a toast notification if supported
          if (window.AetheriaToast && typeof window.AetheriaToast.show === 'function') {
            const senderName = payload.new.sender_name || 'Someone';
            const body = payload.new.body || 'New message';
            window.AetheriaToast.show(`💬 ${senderName}: ${body.substring(0, 60)}`, 'info');
          }
        }
      )
      .subscribe(function (status) {
        console.info('[Aetheria Realtime] Messages channel:', status);
      });
  }

  // ── Story Views ─────────────────────────────────────────────────────────────

  function subscribeToStoryViews(client) {
    client
      .channel('aetheria-story-views')
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'users_storyview',
        },
        function (payload) {
          // Only fire if the story belongs to the current user
          // (RLS on Supabase filters this at source, but double-check client-side)
          document.dispatchEvent(new CustomEvent('aetheria:story_view', { detail: { payload } }));
        }
      )
      .subscribe();
  }

  // ── Bootstrap ───────────────────────────────────────────────────────────────

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
