# Risk Assessment: Decision & Notification Infrastructure (O-002)
Scope: Full notification system (backend persistence + real-time delivery + frontend UI) | Horizon: Initial implementation + first 3 months

## Risk Register

| # | Risk | P | I | V | D | R | Composite | Category |
|---|------|---|---|---|---|---|-----------|----------|
| 1 | Notification flood under concurrent workflows | 4 | 3 | 4 | 3 | 2 | 21 | Technical |
| 2 | WebSocket reconnection gap loses notifications | 3 | 4 | 5 | 4 | 1 | 22 | Technical |
| 3 | Cross-project notification blind spot | 3 | 3 | 2 | 3 | 2 | 16 | Knowledge |
| 4 | Notification entity file lock contention | 2 | 2 | 3 | 2 | 1 | 10 | Technical |
| 5 | UI re-render storm from rapid notifications | 3 | 2 | 4 | 3 | 1 | 14 | Technical |
| 6 | Notification type proliferation | 2 | 2 | 1 | 2 | 2 | 9 | Temporal |
| 7 | Split notification state (server vs client) | 2 | 3 | 2 | 4 | 2 | 14 | Dependency |
| 8 | Stale notification after entity resolved | 3 | 2 | 2 | 3 | 1 | 12 | Technical |

## Top 5 Risks (by composite score)

### 1. WebSocket Reconnection Gap - Composite: 22
**Description**: When WebSocket disconnects (network issues, tab sleep, page reload), notifications emitted during the gap are lost. User sees stale notification state on reconnect.
**Why it ranks high**: High velocity (instant loss on disconnect, V=5), poor detectability (user may not notice disconnect, D=4), but easy to reverse (fetch catches up, R=1).
**Mitigation**: On WebSocket reconnect, immediately fetch GET /notifications?status=UNREAD&since={lastEventTimestamp}. Server-side persistence (notifications.json) ensures nothing is lost. Already have similar pattern - SWR revalidates on reconnect.

### 2. Notification Flood Under Concurrent Workflows - Composite: 21
**Description**: Three concurrent workflows each generating 5-10 events per step. At 3 steps per minute, that is 15-30 notifications/minute. UI becomes unusable with constant popups/toasts.
**Why it ranks high**: High probability (concurrent workflows is KR-3 requirement, P=4), fast onset (V=4), moderately hard to detect early (D=3).
**Mitigation**: Server-side notification batching - group notifications from same workflow/step. Frontend throttling - wsDispatcher already has 300ms debounce for SWR, apply similar to notifications. Priority queue - show HIGH severity immediately, batch LOW.

### 3. Cross-Project Notification Blind Spot - Composite: 16
**Description**: User views project A in browser. Workflow running on project B emits blocking decision. No mechanism to notify the user since WebSocket is per-project.
**Why it ranks high**: Medium probability (multi-project use is planned, P=3), medium impact (blocking decision waits until user checks, I=3), but hard to detect (D=3).
**Mitigation**: Two options: (a) global WebSocket channel for cross-project notifications, (b) periodic polling of unread count across projects from NotificationCenter. Option (b) is simpler and fits current architecture.

### 4. UI Re-render Storm - Composite: 14
**Description**: Rapid notification state updates cause excessive React re-renders. Each notification update triggers notificationStore subscribers, toast additions, activity feed updates, and SWR revalidation.
**Why it ranks high**: Fast velocity (V=4), medium probability under concurrency.
**Mitigation**: Batch state updates in wsDispatcher - collect notifications for 200ms then apply as single batch. Use React.memo on notification list items. Already have precedent: toast debounce at 500ms.

### 5. Split Notification State - Composite: 14
**Description**: Server stores notifications.json, client stores notification state in Zustand + localStorage (dismissals). If they diverge, user sees inconsistent state - dismissed notifications reappear, or new notifications invisible.
**Why it ranks high**: Detectability is poor (D=4) - user may not realize state is inconsistent.
**Mitigation**: Server is source of truth. Client read state syncs via PATCH /notifications/{id} (mark read/dismissed). On reconnect, fetch full unread list. Remove localStorage dismissal in favor of server-side status.

## Risk Interactions

| Risk A | Risk B | Interaction | Cascade? |
|--------|--------|-------------|----------|
| Notification flood (1) | UI re-render storm (5) | Flood amplifies re-renders - more notifications = more state updates | YES |
| Notification flood (1) | File lock contention (4) | High volume writes increase lock wait times | YES |
| WS reconnection gap (2) | Split state (7) | Reconnection makes state divergence worse | YES |
| Stale notification (8) | Split state (7) | Stale notifications are a form of state divergence | Shared root |
| Cross-project blind spot (3) | WS reconnection gap (2) | Both cause missed notifications but through different mechanisms | No cascade |

## Mitigations + Cobra Effect Check

| Mitigation | Fixes | Could Cause/Amplify | Cobra? |
|------------|-------|---------------------|--------|
| Server-side persistence | WS gap (2), Split state (7) | File lock contention (4) - more writes | Minor - existing lock pattern handles this |
| Notification batching | Flood (1), Re-render storm (5) | Delayed notification delivery (latency) | No - batching window is 200-300ms, acceptable |
| Fetch-on-reconnect | WS gap (2) | Temporary load spike after reconnect | No - single fetch, bounded result set |
| Cross-project polling | Blind spot (3) | Additional API load from polling | Minor - once per 30-60s, lightweight endpoint |
| Server as truth for read state | Split state (7) | More API calls for dismiss/read | No - PATCH is lightweight |

## Uncertainties (distinct from risks)

1. **Actual notification volume** - Cannot predict exact volume under real concurrent workflows until O-001 (Workflow Engine) is built. Estimated 10-30 notifications per workflow run based on step count.
2. **User behavior with notifications** - Will users respond immediately to blocking decisions or batch-process them? Affects priority queue design.
3. **Cross-project workflow frequency** - How often will users have concurrent workflows across different projects? Affects cross-project notification priority.

## Not Assessed
- Security risks (notification content injection, unauthorized access to notifications)
- Performance impact on existing WebSocket throughput
- Redis memory pressure from notification events
- Browser tab/window management with multiple project tabs
- Accessibility risks (screen reader support for real-time notifications)