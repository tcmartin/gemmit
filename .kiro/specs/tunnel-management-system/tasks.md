# Implementation Plan

- [ ] 1. Create tunnel API client module

  - Create `desktop/src/tunnelApi.js` with reserveTunnels function
  - Implement HTTP client to call external provisioning API
  - Add error handling for network failures and API responses
  - _Requirements: 7.1_

- [ ] 2. Implement frpc process manager

  - Create `desktop/src/tunnelManager.js` for frpc process control
  - Implement buildFrpcIni function to generate configuration files
  - Add runFrpc function to spawn frpc processes using existing patterns
  - Integrate with existing process cleanup using tree-kill
  - _Requirements: 7.2, 7.3, 9.1, 9.4_

- [ ] 3. Build local reverse proxy

  - Create `desktop/src/proxy.js` HTTP server on port 8080
  - Route /api/alt/_ to backend (:5003), /api/_ to vibe (:8000), /\* to frontend (:5002)
  - Add WebSocket upgrade support for vibe app
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ] 4. Bundle frpc binaries for distribution

  - Download frpc binaries for macOS (Intel/ARM), Windows, and Linux
  - Add binaries to `desktop/resources/bin/` directory
  - Implement platform-specific binary path resolution in tunnelManager
  - _Requirements: 7.2, 7.3_

- [ ] 5. Integrate tunnel management into Electron main process

  - Add tunnel startup/shutdown to main.js lifecycle
  - Integrate tunnel process tracking with existing backend process management
  - Handle graceful shutdown of tunnel processes on app exit
  - _Requirements: 7.4, 7.5, 9.2, 9.3_

- [ ] 6. Add tunnel controls to chat interface

  - Add tunnel start/stop buttons to existing topbar in chat.html
  - Display tunnel URLs and status in chat interface
  - Integrate tunnel commands with existing WebSocket communication
  - _Requirements: 7.4_

- [ ] 7. Implement tunnel configuration and settings

  - Add tunnel API endpoint configuration to existing settings system
  - Store tunnel credentials securely using existing patterns
  - Add user/project ID configuration for tunnel reservation
  - _Requirements: 7.1, 10.3_

- [ ] 8. Add error handling and user feedback
  - Handle frpc process failures with user-friendly messages
  - Add fallback for missing frpc binaries
  - Handle API failures and network connectivity issues
  - _Requirements: 9.3, 10.2, 10.4_
