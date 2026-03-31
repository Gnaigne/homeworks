# EASM Frontend - React Demo

Modern React frontend for External Attack Surface Management (EASM) platform.

## 🚀 Features

- ✅ **Asset Management** - CRUD operations for domains, IPs, and services
- ✅ **Passive Scanning** - DNS, WHOIS, subdomain enumeration
- ✅ **Active Scanning** - Port and SSL scanning (with warnings)
- ✅ **Real-time Updates** - Auto-refreshing scan status
- ✅ **Results Visualization** - View DNS records, subdomains, WHOIS data
- ✅ **Responsive Design** - Works on desktop and mobile
- ✅ **Modern UI** - Clean interface with Lucide icons

## 📋 Prerequisites

- Node.js 18+ installed
- Backend API running on `http://localhost:8080`

## 🛠️ Installation

```bash
# Navigate to frontend directory
cd d:\Projects\cmc-intern-program\app\session6-testing\frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The application will be available at: **http://localhost:3000**

## 📁 Project Structure

```
frontend/
├── public/                 # Static assets
├── src/
│   ├── pages/             # Page components
│   │   ├── Dashboard.jsx  # Dashboard with stats
│   │   ├── Assets.jsx     # Asset management (CRUD)
│   │   ├── Scanning.jsx   # Scan operations
│   │   └── Results.jsx    # Results visualization
│   ├── services/          # API integration
│   │   └── api.js         # axios client & API methods
│   ├── App.jsx            # Main app component with routing
│   ├── App.css            # App-specific styles
│   ├── index.css          # Global styles & utilities
│   └── main.jsx           # App entry point
├── index.html             # HTML template
├── vite.config.js         # Vite configuration
└── package.json           # Dependencies & scripts
```

## 🎨 Pages Overview

### 1. Dashboard (`/`)

- System health status
- Asset statistics
- Quick start guide
- Feature overview (passive vs active scans)

### 2. Assets (`/assets`)

- View all assets with pagination
- Filter by type (domain, ip, service)
- Filter by status (active, inactive)
- Search assets
- Create, edit, delete assets
- Inline validation

### 3. Scanning (`/scanning`)

- Select asset to scan
- Choose scan type (passive/active)
- Start scans with one click
- View recent scan jobs
- Auto-refresh scan status (5s polling)
- Active scan warnings

### 4. Results (`/results`)

- View all results for an asset
- Filter by result type:
  - All results
  - DNS records only
  - Subdomains only
  - WHOIS information
- Detailed result tables

## 🔌 API Integration

The frontend communicates with the backend API via:

**Base URL:** `/api` (proxied to `http://localhost:8080` by Vite)

**Key Services:**

- `assetsAPI` - Asset CRUD operations
- `scanningAPI` - Scan operations & job management
- `resultsAPI` - Result retrieval

**Example API Call:**

```javascript
import { assetsAPI } from "./services/api";

// List assets with filters
const data = await assetsAPI.list({
  page: 1,
  page_size: 20,
  type: "domain",
  status: "active",
});
```

## 🎯 Key Features

### Asset Management

```javascript
// Create asset
await assetsAPI.create({
  name: "example.com",
  type: "domain",
});

// Update asset
await assetsAPI.update(assetId, {
  status: "inactive",
});

// Delete asset
await assetsAPI.delete(assetId);
```

### Scanning Operations

```javascript
// Start scan
const job = await scanningAPI.startScan(assetId, "dns");

// Check status
const status = await scanningAPI.getJob(job.id);

// Get results
const results = await scanningAPI.getResults(job.id);
```

### Result Retrieval

```javascript
// Get all results
const all = await resultsAPI.getAll(assetId);

// Get specific results
const dns = await resultsAPI.getDNS(assetId);
const subdomains = await resultsAPI.getSubdomains(assetId);
const whois = await resultsAPI.getWHOIS(assetId);
```

## 🎨 Styling

**CSS Framework:** Custom CSS with CSS variables

**Key Features:**

- CSS variables for theming
- Responsive grid system
- Utility classes
- Component-based styles
- Dark mode ready (variables can be swapped)

**Example:**

```css
:root {
  --color-primary: #3b82f6;
  --color-success: #10b981;
  --spacing-md: 1rem;
}

.btn-primary {
  background-color: var(--color-primary);
  padding: var(--spacing-md);
}
```

## 🔧 Configuration

### Proxy Configuration (vite.config.js)

```javascript
export default defineConfig({
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: "http://localhost:8080",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
```

This allows frontend to call `/api/assets` which proxies to `http://localhost:8080/assets`

## 🚦 Running the Full Stack

### 1. Start Backend

```bash
cd d:\Projects\cmc-intern-program\app\session6-testing
go run cmd/server/main.go
```

Backend runs on: `http://localhost:8080`

### 2. Start Frontend

```bash
cd d:\Projects\cmc-intern-program\app\session6-testing\frontend
npm run dev
```

Frontend runs on: `http://localhost:3000`

### 3. Access Application

Open browser: **http://localhost:3000**

## 📦 Build for Production

```bash
# Build production bundle
npm run build

# Preview production build
npm run preview
```

Build output goes to `dist/` directory.

## 🧪 Testing Workflow

### 1. Create Assets

1. Go to **Assets** page
2. Click "Add Asset"
3. Enter domain (e.g., `example.com`)
4. Select type: `domain`
5. Click "Add Asset"

### 2. Run Scans

1. Go to **Scanning** page
2. Select the asset you created
3. Choose scan type (start with `dns` for passive scan)
4. Click "Start Scan"
5. Watch real-time status updates

### 3. View Results

1. Go to **Results** page
2. Select your asset
3. Choose result type
4. View detailed data:
   - DNS records (A, AAAA, MX, etc.)
   - Subdomains discovered
   - WHOIS information

## ⚠️ Active Scanning Warnings

The UI displays warnings when selecting active scan types:

```javascript
if (!scanType.passive) {
  const confirmed = window.confirm(
    "⚠️ WARNING: Active scan requires authorization...",
  );
  if (!confirmed) return;
}
```

**Active Scans:**

- 🔴 Port Scanning
- 🔴 SSL/TLS Probing

**Legal Notice:** Only scan systems you own or have explicit permission to test.

## 🎓 Educational Features

### Real-time Updates

- Scan jobs auto-refresh every 5 seconds
- Live status indication (pending → running → completed)

### User Experience

- Loading states on all async operations
- Error handling with user-friendly messages
- Success notifications
- Empty states with helpful messages
- Responsive pagination

### Code Quality

- Modern React hooks (useState, useEffect)
- Clean component structure
- Reusable API service layer
- CSS variables for theming
- Semantic HTML

## 🐛 Troubleshooting

### Issue: Frontend can't connect to backend

**Solution:**

- Ensure backend is running on port 8080
- Check Vite proxy configuration
- Check browser console for CORS errors

### Issue: Assets not loading

**Solution:**

- Check backend API is accessible
- Verify database is running
- Check browser network tab for errors

### Issue: Scans not starting

**Solution:**

- Ensure asset is "active" status
- Check backend logs for errors
- Verify scan service is initialized

### Issue: npm install fails

**Solution:**

```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and package-lock.json
rm -rf node_modules package-lock.json

# Reinstall
npm install
```

## 📚 Technologies Used

- **React 18** - UI framework
- **React Router 6** - Client-side routing
- **Axios** - HTTP client
- **Lucide React** - Icon library
- **Vite** - Build tool & dev server
- **CSS Variables** - Styling system

## 🔜 Future Enhancements

- [ ] WebSocket for real-time scan updates
- [ ] Dark mode toggle
- [ ] Export results to CSV/JSON
- [ ] Advanced filtering and search
- [ ] Scan scheduling
- [ ] Result comparison over time
- [ ] Asset grouping/tagging
- [ ] Multi-select bulk operations
- [ ] Dashboard charts and graphs
- [ ] Notification system

## 📖 Documentation

- **API Documentation:** `../api.yml` (OpenAPI 3.0 spec)
- **Backend README:** `../README.md`
- **Testing Guide:** `../TESTING_GUIDE.md`

## 🤝 Contributing

This is an educational project for CMC Intern Program.

**Session 6 Focus:** Testing & Quality Assurance

## 📝 License

Educational project - CMC Intern Program 2026

---

**Happy Scanning! 🔍**

For questions or issues, refer to the main project documentation or ask your instructor.
