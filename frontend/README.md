# chakravyuh Frontend

> Next.js 15 + React 19 frontend for the chakravyuh threat modeling platform.

## 🚀 Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend runs on: **http://localhost:3000**

## 📦 Tech Stack

- **Framework**: Next.js 15.5.4 (App Router)
- **React**: 19.0.0
- **Styling**: TailwindCSS 3.4
- **UI Components**: shadcn/ui
- **AI Integration**: Google Genkit
- **Icons**: Lucide React

## 🏗️ Project Structure

```
frontend/
├── src/
│   ├── app/              # Next.js App Router
│   │   ├── page.tsx      # Home page
│   │   ├── layout.tsx    # Root layout
│   │   └── globals.css   # Global styles
│   ├── components/       # React components
│   │   ├── erd-upload.tsx       # ERD document upload
│   │   ├── chat-interface.tsx   # Q&A chat
│   │   └── ui/                  # shadcn/ui components
│   ├── ai/               # AI/Genkit flows
│   │   └── flows/        # Threat modeling flows
│   └── hooks/            # Custom React hooks
├── package.json
├── next.config.ts
├── tailwind.config.ts
└── tsconfig.json
```

## 🔧 Configuration

### API Endpoint

Backend API is expected at: **http://localhost:8000**

If you need to change this, update the endpoints in:
- `src/components/erd-upload.tsx`
- `src/components/chat-interface.tsx`

### Environment Variables

Create `.env.local` (optional):

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 📱 Features

### 1. ERD Document Upload
- Drag & drop or file picker
- Supports PDF, JSON, TXT
- Real-time processing status
- Multi-document support

### 2. Security Analysis Chat
- Context-aware Q&A
- Threat modeling queries
- Markdown rendering
- Query caching (30s)

### 3. UI Features
- Responsive design
- Dark mode support
- Loading states
- Toast notifications
- Progress indicators

## 🛠️ Development

### Available Scripts

```bash
npm run dev          # Start dev server (localhost:3000)
npm run build        # Production build
npm run start        # Start production server
npm run lint         # Run ESLint
```

### Adding New Components

```bash
# Using shadcn/ui CLI
npx shadcn@latest add [component-name]
```

### Development Tips

1. **Hot Reload**: Changes auto-reload with Turbopack
2. **API Calls**: Check browser console for cache HIT/MISS logs
3. **Debugging**: Use React DevTools
4. **Type Checking**: TypeScript strict mode enabled

## 📊 Performance

- **Query Caching**: 30-second TTL for identical queries
- **Optimized Rendering**: React 19 with automatic memoization
- **Fast Refresh**: Turbopack for instant updates
- **Code Splitting**: Automatic with Next.js

## 🧪 Testing

```bash
npm run test         # Run tests (if configured)
npm run test:watch   # Watch mode
```

## 🚀 Production Build

```bash
# Build for production
npm run build

# Preview production build locally
npm run start
```

Build output goes to `.next/` folder.

## 📝 Component Documentation

### ERD Upload (`erd-upload.tsx`)

Handles document upload and processing:
- File validation
- Upload to backend `/api/save-original-erd`
- Processing via `/api/process-erd`
- Status tracking

### Chat Interface (`chat-interface.tsx`)

Interactive Q&A interface:
- Message history
- Markdown rendering
- Error handling
- Query caching

## 🔗 Backend Integration

Frontend communicates with backend via REST API:

- `GET /health` - Health check
- `POST /api/save-original-erd` - Save ERD file
- `POST /api/process-erd` - Process ERD
- `GET /api/bulk-insert-erd-status` - Check status
- `GET /ask` - Q&A endpoint
- `GET /metrics` - Performance metrics

## 🆘 Troubleshooting

### "Failed to fetch" errors
- Ensure backend is running on port 8000
- Check CORS settings in backend
- Try `127.0.0.1` instead of `localhost`

### Build errors
```bash
rm -rf .next node_modules package-lock.json
npm install
npm run dev
```

### Type errors
```bash
npm run build  # TypeScript will show all errors
```

---

**Frontend Version**: 1.0.0  
**Last Updated**: February 3, 2026
