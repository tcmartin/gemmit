# macOS Installation Help

## "Gemmit is damaged and can't be opened" Error

This error occurs because the app is not signed with an Apple Developer certificate. Here are the solutions:

### Method 1: Remove Quarantine (Recommended)
1. Open Terminal
2. Navigate to where you downloaded the app
3. Run this command:
   ```bash
   sudo xattr -rd com.apple.quarantine /Applications/gemmit.app
   ```
4. Enter your password when prompted
5. Try opening the app again

### Method 2: System Preferences Override
1. Try to open the app (it will fail)
2. Go to **System Preferences** → **Security & Privacy** → **General**
3. You should see a message about "gemmit was blocked"
4. Click **"Open Anyway"**
5. Confirm when prompted

### Method 3: Right-Click Method
1. Right-click on the gemmit.app in Applications
2. Select **"Open"** from the context menu
3. Click **"Open"** in the dialog that appears

### Method 4: Command Line Override
```bash
# Remove all extended attributes
sudo xattr -c /Applications/gemmit.app

# Or specifically remove quarantine
sudo xattr -d com.apple.quarantine /Applications/gemmit.app
```

## Why This Happens
- The app is not signed with an Apple Developer certificate ($99/year)
- macOS Gatekeeper blocks unsigned apps by default
- This is a security feature, but safe to bypass for trusted apps

## Future Versions
We're working on getting proper Apple Developer signing for future releases to eliminate this issue.