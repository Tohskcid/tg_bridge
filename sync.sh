#!/bin/bash
echo "🚀 Starting auto-sync to GitHub..."
git add .
git commit -m "Auto-update: $(date +'%Y-%m-%d %H:%M:%S')"
git push -u origin main --force
echo "✅ Sync complete!"
