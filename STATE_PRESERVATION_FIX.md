# State Preservation Fix - Dashboard & Chat Views

## Problem
Previously, switching between Chat and Dashboard views would cause the Dashboard to reload and lose all its state (WebSocket connections, fetched data, scroll position, etc.). This happened because the components were being conditionally rendered with ternary operators, causing them to unmount and remount on each switch.

## Solution
Changed from **conditional rendering** to **visibility toggling** using CSS classes. Now all views remain mounted in the DOM, but only the active one is visible.

### Before (Conditional Rendering)
```tsx
{currentView === 'chat' ? (
  <ChatLayout user={auth.user} onLogout={auth.logout} />
) : currentView === 'dashboard' ? (
  <Dashboard onStockSelect={handleStockSelect} />
) : (
  <StockDetail symbol={selectedStock} onBack={handleBackToDashboard} />
)}
```

**Problem:** Components unmount when view changes, losing all state.

### After (Visibility Toggling)
```tsx
<div className={currentView === 'chat' ? '' : 'hidden'}>
  <ChatLayout user={auth.user} onLogout={auth.logout} />
</div>
<div className={currentView === 'dashboard' ? '' : 'hidden'}>
  <Dashboard onStockSelect={handleStockSelect} />
</div>
<div className={currentView === 'stock-detail' ? '' : 'hidden'}>
  <StockDetail symbol={selectedStock} onBack={handleBackToDashboard} />
</div>
```

**Solution:** Components stay mounted, only visibility changes via Tailwind's `hidden` class.

## Benefits

### 1. **State Preservation**
- ✅ Dashboard keeps all fetched data when switching to Chat
- ✅ WebSocket connection remains active
- ✅ Scroll positions preserved
- ✅ User input in forms retained
- ✅ No unnecessary re-fetching of data

### 2. **Performance Improvements**
- ✅ Faster switching between views (no remounting overhead)
- ✅ No repeated API calls
- ✅ No re-establishing WebSocket connections
- ✅ Smoother user experience

### 3. **Better UX**
- ✅ Instant view switching
- ✅ Dashboard data stays fresh
- ✅ No loading spinners when returning to Dashboard
- ✅ Maintains context across views

## Trade-offs

### Memory Usage
**Consideration:** All views are kept in memory simultaneously.

**Impact:** Minimal in this case because:
- Only 3 views total (Chat, Dashboard, StockDetail)
- Modern browsers handle this easily
- User benefits far outweigh minimal memory cost

### Initial Load
**Consideration:** All components mount on first render.

**Mitigation:** 
- Components are lightweight initially
- Data fetching happens lazily
- WebSocket only connects when needed

## Technical Details

### CSS Class Used
```css
.hidden {
  display: none;
}
```

This Tailwind utility completely removes elements from the layout flow while keeping them in the DOM tree.

### Alternative Approaches Considered

1. **React Context State Management** ❌
   - More complex
   - Requires significant refactoring
   - Overkill for 3 views

2. **React Router with Keep-Alive** ❌
   - Adds dependency
   - More boilerplate
   - Not standard in React

3. **Visibility Toggle (CHOSEN)** ✅
   - Simple and effective
   - No new dependencies
   - Works immediately
   - Easy to understand and maintain

## Testing

To verify the fix works:

1. **Navigate to Dashboard**
   - Wait for data to load
   - Note the stock prices and news

2. **Switch to Chat**
   - Send a message
   - Verify chat works

3. **Switch back to Dashboard**
   - ✅ Data should be the same (not reloaded)
   - ✅ WebSocket should still be connected
   - ✅ No loading spinners
   - ✅ Instant switch

## Future Enhancements

If needed, could add:

1. **Lazy Mounting**
   ```tsx
   {hasVisited.dashboard && (
     <div className={currentView === 'dashboard' ? '' : 'hidden'}>
       <Dashboard />
     </div>
   )}
   ```

2. **Active View Detection**
   ```tsx
   <Dashboard 
     isActive={currentView === 'dashboard'}
     onStockSelect={handleStockSelect}
   />
   ```
   Component could pause WebSocket when not active to save resources.

3. **Memory Management**
   Could implement view unloading after long periods of inactivity.

## Files Modified

- `frontend/src/App.tsx` - Changed view rendering logic

## Compatibility

- ✅ Works with all modern browsers
- ✅ No breaking changes
- ✅ Maintains existing functionality
- ✅ TypeScript types intact
