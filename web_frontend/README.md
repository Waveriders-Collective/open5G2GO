# Open5G2GO Web Frontend

**React + TypeScript + Tailwind CSS**

Modern, responsive web interface for Open5GS 4G mobile core management with Waveriders branding.

---

## Features

✅ **3 Main Pages**
- Dashboard - System status, active connections, quick stats
- Subscribers - List all devices, add new subscribers, search/filter
- Network Config - PLMNID, DNNs, bandwidth configuration

✅ **Waveriders Branded Design**
- Color Palette: Green gradient + gray scale + yellow accents
- Typography: Instrument Sans Medium (body) & Bold (headers)
- Custom Tailwind theme with brand colors

✅ **Modern UX**
- Responsive design (mobile, tablet, desktop)
- Auto-refresh on dashboard (30s interval)
- Real-time API integration
- Loading states and error handling
- Interactive forms with validation

✅ **Type-Safe**
- TypeScript throughout
- Type-safe API client
- Pydantic-compatible types

---

## Quick Start

### Development Mode

```bash
# Navigate to frontend directory
cd web_frontend

# Install dependencies
npm install

# Start dev server (with proxy to backend)
npm run dev

# Access at http://localhost:3000
```

**Note**: The dev server proxies API requests to `http://localhost:8000` (backend must be running).

### Production Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

---

## Project Structure

```
web_frontend/
├── src/
│   ├── components/
│   │   ├── ui/              # Reusable UI components
│   │   │   ├── Button.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Badge.tsx
│   │   │   ├── Table.tsx
│   │   │   ├── LoadingSpinner.tsx
│   │   │   └── StatCard.tsx
│   │   ├── layout/          # Layout components
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── Layout.tsx
│   │   ├── dashboard/       # Dashboard-specific components
│   │   ├── subscribers/     # Subscriber components
│   │   │   └── AddSubscriberModal.tsx
│   │   └── network/         # Network config components
│   ├── pages/
│   │   ├── Dashboard.tsx    # Dashboard page
│   │   ├── Subscribers.tsx  # Subscribers list & management
│   │   └── NetworkConfig.tsx # Network configuration
│   ├── services/
│   │   └── api.ts           # API client (axios)
│   ├── types/
│   │   └── open5gs.ts       # TypeScript types
│   ├── styles/
│   │   └── index.css        # Global CSS + Tailwind
│   ├── App.tsx              # Main app component
│   └── main.tsx             # Entry point
├── index.html               # HTML template
├── package.json             # Dependencies & scripts
├── tsconfig.json            # TypeScript config
├── tailwind.config.js       # Tailwind theme (Waveriders colors)
├── vite.config.ts           # Vite build config
└── README.md                # This file
```

---

## Waveriders Brand Theme

### Color Palette

**Primary (Green Gradient):**
- Light: `#A8E6CF` - Backgrounds, subtle highlights
- Medium: `#4CAF50` - Primary actions, active states
- Deep: `#2E7D32` - Emphasis, headers

**Neutrals (Gray Scale):**
- Medium Gray: `#9E9E9E` - Secondary text, borders
- Dark Gray: `#616161` - Body text
- Charcoal: `#424242` - Headers, emphasis
- Black: `#212121` - Primary text, navigation

**Accents:**
- Deep Charcoal/Black: `#1A1A1A` - Backgrounds, footers
- Bright Yellow: `#FFD600` - Alerts, highlights, CTAs

### Typography

- **Body Text**: Instrument Sans Medium (400-500 weight)
- **Headers**: Instrument Sans Bold (700 weight)
- **Font Source**: Google Fonts

### Tailwind Configuration

The Waveriders theme is defined in `tailwind.config.js`:

```js
colors: {
  primary: {
    light: '#A8E6CF',
    DEFAULT: '#4CAF50',
    deep: '#2E7D32',
  },
  gray: {
    medium: '#9E9E9E',
    dark: '#616161',
    charcoal: '#424242',
    black: '#212121',
  },
  accent: {
    charcoal: '#1A1A1A',
    yellow: '#FFD600',
  },
}
```

---

## Pages Overview

### 1. Dashboard (`/`)

**Components:**
- **Stats Cards**: Provisioned, Registered, Connected, gNodeBs
- **System Health**: Core operational status, active connections
- **gNodeB List**: Connected cell towers
- **Active Connections Table**: Live device connections

**Auto-refresh**: Every 30 seconds

**Features:**
- Real-time system monitoring
- Health status indicators
- Color-coded badges (green = success, yellow = warning)

### 2. Subscribers (`/subscribers`)

**Components:**
- **Quick Stats**: Total subscribers, last updated, host
- **Search Bar**: Filter by name, IMSI, IP
- **Subscribers Table**: All provisioned devices
- **Add Subscriber Modal**: Provision new devices

**Features:**
- Client-side search/filter
- Add subscriber form with validation
- Service type badges
- Refresh button

**Add Subscriber Form Fields:**
- Device Number (1-999)
- Name Prefix (WR-VIDEO, WR-iVIDEO, WR-VIDEO-e)
- DNN (video, internet)
- IP Mode (old/new)

### 3. Network Config (`/network`)

**Components:**
- **Network Identity Card**: PLMNID, MCC/MNC, TAC, network name
- **DNNs Table**: DNN configurations with bandwidth
- **Configuration Details**: Read-only network information

**Features:**
- Read-only display
- Formatted bandwidth display
- Network identity breakdown

---

## API Integration

### API Client

The frontend uses a typed API client (`src/services/api.ts`) that wraps axios:

```typescript
import { api } from './services/api';

// List subscribers
const subscribers = await api.listSubscribers();

// Add subscriber
const result = await api.addSubscriber({
  device_number: 18,
  name_prefix: 'WR-VIDEO',
  dnn: 'video',
  ip_mode: 'old',
});
```

### Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/subscribers` | GET | List all subscribers |
| `/api/v1/status` | GET | System health dashboard |
| `/api/v1/connections` | GET | Active device connections |
| `/api/v1/config` | GET | Network configuration |
| `/api/v1/subscribers` | POST | Add new subscriber |
| `/api/v1/health` | GET | API health check |

### Type Safety

All API responses have TypeScript types defined in `src/types/open5gs.ts`:

```typescript
interface ListSubscribersResponse {
  host: string;
  timestamp: string;
  total: number;
  subscribers: Subscriber[];
}
```

---

## Development

### Prerequisites

- Node.js 18+ and npm
- Backend API running at `http://localhost:8080`

### Install Dependencies

```bash
npm install
```

### Run Dev Server

```bash
npm run dev
```

Access at `http://localhost:3000`. The dev server proxies `/api` requests to the backend at `http://localhost:8000`.

### Build for Production

```bash
npm run build
```

Output goes to `dist/` directory.

### Lint Code

```bash
npm run lint
```

---

## Docker Deployment

### Build Frontend Container

```bash
# From project root
docker build -f Dockerfile.frontend -t open5g2go-frontend .
```

### Run Full Stack with Docker Compose

```bash
# From project root
docker-compose up -d
```

Access the frontend at `http://localhost` (port 80).

The nginx server inside the frontend container:
- Serves the React SPA from `/usr/share/nginx/html`
- Proxies `/api/*` requests to the backend container
- Handles SPA routing (all routes → `index.html`)

---

## Environment Variables

The frontend uses the backend's configuration. No frontend-specific environment variables are needed.

**Backend API URL:**
- Development: `http://localhost:8000` (via Vite proxy)
- Production: `/api` (via nginx proxy)

---

## Customization

### Change Colors

Edit `tailwind.config.js`:

```js
theme: {
  extend: {
    colors: {
      primary: {
        light: '#YOUR_COLOR',
        DEFAULT: '#YOUR_COLOR',
        deep: '#YOUR_COLOR',
      },
    },
  },
}
```

### Add New Pages

1. Create page component in `src/pages/`
2. Add route in `src/App.tsx`:
   ```tsx
   <Route path="/new-page" element={<NewPage />} />
   ```
3. Add navigation item in `src/components/layout/Sidebar.tsx`

### Add New Components

1. Create component in appropriate directory:
   - `src/components/ui/` - Reusable UI components
   - `src/components/layout/` - Layout components
   - `src/components/[feature]/` - Feature-specific components

2. Export from `index.ts` if needed

---

## Performance

### Optimizations Applied

✅ **Code Splitting**: Vite automatically splits code by route
✅ **Tree Shaking**: Unused code removed in production build
✅ **Minification**: CSS and JS minified
✅ **Gzip Compression**: Enabled in nginx
✅ **Static Asset Caching**: 1-year cache for immutable assets
✅ **Lazy Loading**: Components loaded on demand

### Bundle Size

Typical production build:
- Main JS bundle: ~150KB (gzipped)
- CSS: ~10KB (gzipped)
- Vendor chunks: ~200KB (gzipped)

### Performance Tips

- Keep `node_modules` up to date
- Use `npm run build` for production (not dev server)
- Enable HTTP/2 in production nginx
- Use CDN for static assets if needed

---

## Troubleshooting

### API Requests Fail

**Problem**: `Network Error` or `CORS error` in browser console

**Solutions:**
1. Ensure backend is running at `http://localhost:8000`
2. Check Vite proxy config in `vite.config.ts`
3. Check CORS settings in backend (`web_backend/config.py`)

### Build Fails

**Problem**: TypeScript errors or missing dependencies

**Solutions:**
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Check TypeScript config
npx tsc --noEmit
```

### Styling Issues

**Problem**: Tailwind classes not working

**Solutions:**
1. Check `tailwind.config.js` content paths
2. Ensure `@tailwind` directives are in `src/styles/index.css`
3. Clear browser cache

### Docker Build Fails

**Problem**: Frontend Docker build fails

**Solutions:**
```bash
# Build with verbose output
docker build -f Dockerfile.frontend -t open5g2go-frontend . --progress=plain

# Check node_modules are excluded from context
cat .dockerignore
```

---

## Browser Support

✅ Chrome 90+
✅ Firefox 88+
✅ Safari 14+
✅ Edge 90+

**Note**: IE11 is not supported (uses modern ES6+ features)

---

## License

Copyright © 2025 Waveriders Collective Inc. Licensed under AGPLv3.

---

## Next Steps

### Potential Enhancements

- [ ] WebSocket support for real-time updates
- [ ] User authentication (JWT)
- [ ] Role-based access control
- [ ] Edit/delete subscriber functionality
- [ ] Connection history charts
- [ ] Export data to CSV
- [ ] Dark mode toggle
- [ ] Mobile app (React Native)

---

**Built with ❤️ by Waveriders**
