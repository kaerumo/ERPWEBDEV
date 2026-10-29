# webdev-ERP

ERP for DLSU-D ITPC.

Features:
Structure and design

- 4 pages: Login, Dashboard, Inventory, Officers, with a shared sidebar and one stylesheet
- Responsive layout (the sidebar becomes a top bar on phones and fits down to 320px)
- Nav icons, hover effects, page and modal animations, and a reduced-motion setting

Access

- Login with two accounts (admin and member), with an error on bad credentials
- Role-based access: admins get Add, Update qty, Toggle status, Delete and Reset demo data; members can only view
- Log Out clears the role

Data and logic

- Data saved in localStorage, so it persists across pages and refreshes
- Live dashboard stats (total items, low stock alerts, active officers) with animated counters
- Recent Activity log on the dashboard
- Search plus dropdown filters on Inventory and Officers
- Sortable columns (ascending and descending)
- Empty-state message when nothing matches
- Add forms with validation (required fields, non-negative whole-number quantity, no duplicate names)
- Click-to-view detail modal (closes with X, backdrop click or Esc)
- Update quantity, which changes Low Stock automatically
- Toggle officer status
- Confirm-before-delete
- Toast notifications
- Active nav highlighting
- Reset demo data button
- Names you type in are escaped, so they can't break the page

(Added Sept 28, 2026)

Design

- Colors sampled from the ITPC Facebook page (crimson #b62021, maroon, charcoal #262729, steel gray). All live in `:root` at the top of style.css.
- Fonts: Chakra Petch (angular/italic, closest free match to the banner lettering) + Barlow (body).
- Login: comic-panel red background, red glow that follows the mouse, brushed-steel "ITPC" wordmark, 2026/2027 red tags.

New features

- Login guard (pages redirect to login if not signed in)
- Show/Hide password, demo-account fill buttons, shake on wrong password
- User card in sidebar (name + role)

Dashboard:

- 4th stat (total units), stock-level bars, officers-per-committee bars, colored activity feed, personal greeting, quick-add buttons
- Edit for items and officers (same form as Add)
- Styled confirm dialog replaces browser confirm()/prompt()
- Undo after delete
- Export CSV (exports what's currently filtered)
- "Showing X of Y" counter, "/" shortcut to search
- Stock meter bars in the inventory table; initials avatars for officers
- Modal focus handling (Tab stays inside, focus returns on close)

Fixes:

- css/ and js/ paths in the HTML didn't match the flat file layout
- Dashboard could be opened without logging in
- Native prompt()/confirm() dialogs replaced
- Duplicate-name check no longer blocks saving an item you're editing
- Rebranded CSITPC -> ITPC (storage keys now itpc\_\*)

(Added Sept 29, 2026)

Events and dashboard

- Events page with a month calendar (colored dots per event type, click a day to filter), plus add/edit/delete for admins and view-only for members
- Dashboard widgets: Upcoming events and Low stock alerts

Backup and report

- Dashboard > Backup & reports: "Download backup" saves everything (inventory, officers, events, activity) as a .json file, so data survives clearing the browser or switching devices
- "Restore from backup" validates the file first (wrong app, bad quantities, duplicate ids are rejected and nothing changes), asks for confirmation, then replaces the current data. Admin only. Older backups without events still restore
- "Print report" opens report.html: a light-themed summary (stats, low stock, inventory, officers, upcoming events) for Print / Save as PDF

Change log

- Every add, edit and delete on Inventory, Officers and Events is recorded with the user, role, exact date/time and the before/after value of each changed field (the full history is kept, up to 1,000 entries; the Dashboard's Recent activity still shows just the last 10)
- Change log page: search, filter by module, action, person and date range, and export what is shown as CSV
- Restores and demo-data resets are logged too. The log is included in backups; Reset demo data clears it
- Visible to everyone (read-only). It lives in the browser like the rest of the data, so it is a demo audit trail. Tampering with saved data is now detected and logged (see Security below), but it is still not a server-grade audit trail

(Added Oct 4, 2026)

Security

The app has no server, so these measures stop casual tampering (DevTools one-liners, hand-edited Local Storage). They cannot stop someone who rewrites the JavaScript itself.

- New file `js/auth.js` holds all security code. It must be loaded BEFORE `js/main.js` on every page, including the login page
- No plain-text passwords: accounts are stored as salted PBKDF2-SHA256 hashes (600,000 iterations)
- Login lockout: 5 free wrong attempts, then a lock of 30 s that doubles each time up to 15 min. It survives a page refresh and shows a live countdown
- Signed sessions: the role is looked up from the account list and never read from browser storage, so `sessionStorage.setItem("userRole", "admin")` no longer works
- Session expiry: auto log-out after 15 min of inactivity (with a warning 1 min before) and never longer than 8 h. The login page explains why you were logged out
- Sealed storage: every saved list (inventory, officers, events, activity, change log) carries an HMAC seal and a mirror copy. If a value is edited in DevTools, the app restores the last verified copy, or resets the list and keeps the modified copy aside as `itpc_quarantine_*`
- Integrity alerts: when tampering is detected, a red banner appears on the page and an "Integrity alert" entry is written to the Change log (filterable by action)
- One shared set of validation rules is used when loading data, before saving and when restoring a backup, so bad data is rejected even if the form is bypassed
- Admin actions are checked in code, not just hidden with CSS: `saveData()` and `requireAdmin()` refuse changes from a member
- Signed backups: "Download backup" asks for a passphrase (10+ characters) and signs the file. "Restore" asks for the same passphrase and rejects the file if anything was changed after download. The backup now includes the change log. Backups made before signing existed can still be restored (controlled by `ALLOW_UNSIGNED_BACKUPS` in `auth.js`)
- Change log CSV export neutralizes spreadsheet formulas (cells starting with = + - @)

Setup after cloning

1. Open the site on `localhost` or HTTPS (the browser's crypto API is not available otherwise)
2. Create a hash for each account: press F12, open the Console and run the hashing snippet. It asks for the password in a prompt and prints a `salt` and `hash`. Paste them into the matching account in `js/auth.js`. Use a different password for each account and keep them somewhere safe, they cannot be recovered from the hash
3. Make sure every HTML page loads `js/auth.js` before `js/main.js`

Known limits (no server)

- Deleting `itpc_devkey` in DevTools makes the next load count as a first run, so existing data is accepted once and re-sealed
- Someone who reads the device key from Local Storage can forge a session seal. Real protection against this needs a backend
- Passwords and the sealing key are only as safe as the browser they run in
