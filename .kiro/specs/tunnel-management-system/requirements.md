# Requirements Document

## Introduction

The tunnel management system will extend Gemmit's capabilities by providing secure, shareable tunnels for local development environments. This system will enable users to expose their local development servers (frontend, backend, and full-stack applications) to the internet through human-readable subdomains, with optional paywall functionality for monetization.

The system consists of server-side infrastructure for tunnel provisioning and authentication, edge proxy for paywall enforcement, and client-side integration within the existing Gemmit Electron application.

## Requirements

### Requirement 1: Tunnel Name Generation and Reservation

**User Story:** As a developer, I want to get persistent, human-readable tunnel names for my projects, so that I can easily share and remember my development URLs.

#### Acceptance Criteria

1. WHEN a user requests tunnel names for a project THEN the system SHALL generate deterministic, collision-proof subdomain names using BIP39 wordlists and checksums
2. WHEN generating tunnel names THEN the system SHALL create three distinct tunnels per project: 'vibe' (port 8000), 'fe' (port 5002), and 'be' (port 5003)
3. WHEN a tunnel name is generated THEN it SHALL follow the format: `{role}-{5-words}-{checksum}.gemmit.org`
4. WHEN the same user requests tunnels for the same project THEN the system SHALL return the existing reserved names instead of generating new ones
5. WHEN generating names THEN the system SHALL ensure uniqueness through database constraints and retry logic with versioned seeds

### Requirement 2: Database Persistence and User Management

**User Story:** As a system administrator, I want tunnel reservations to be stored persistently with proper user and project relationships, so that the system can manage entitlements and billing.

#### Acceptance Criteria

1. WHEN the system starts THEN it SHALL have PostgreSQL tables for users, projects, and tunnels with proper foreign key relationships
2. WHEN a tunnel is created THEN it SHALL be associated with a specific user and project
3. WHEN storing tunnel data THEN the system SHALL track tunnel status ('active', 'trial', 'past_due', 'canceled', 'inactive')
4. WHEN querying tunnels THEN the system SHALL support efficient lookups by tunnel name through database indexing
5. WHEN a user or project is deleted THEN the system SHALL cascade delete associated tunnels

### Requirement 3: API Endpoints for Tunnel Management

**User Story:** As a Gemmit client application, I want REST API endpoints to reserve tunnels and check entitlements, so that I can integrate tunnel functionality seamlessly.

#### Acceptance Criteria

1. WHEN a POST request is made to `/api/tunnels/reserve` with userId and projectId THEN the system SHALL return or create three tunnel configurations
2. WHEN a GET request is made to `/entitlement/check` with a host header THEN the system SHALL validate tunnel access and return appropriate HTTP status codes
3. WHEN an entitlement check passes THEN the system SHALL return HTTP 204 with X-User-Id header
4. WHEN an entitlement check fails due to payment THEN the system SHALL return HTTP 402 (Payment Required)
5. WHEN an entitlement check fails due to inactive status THEN the system SHALL return HTTP 403 (Forbidden)

### Requirement 4: Stripe Integration for Payment Processing

**User Story:** As a business owner, I want to monetize tunnel usage through Stripe subscriptions, so that I can generate revenue while providing free trial access.

#### Acceptance Criteria

1. WHEN a Stripe webhook is received for subscription updates THEN the system SHALL update corresponding tunnel statuses
2. WHEN a subscription becomes active THEN the associated tunnel status SHALL be set to 'active'
3. WHEN a subscription is past due THEN the associated tunnel status SHALL be set to 'past_due'
4. WHEN a subscription is canceled THEN the associated tunnel status SHALL be set to 'canceled'
5. WHEN processing webhooks THEN the system SHALL verify Stripe signatures for security

### Requirement 5: Edge Proxy with Paywall Enforcement

**User Story:** As a system operator, I want an edge proxy that enforces payment requirements before allowing tunnel access, so that only authorized users can access paid tunnels.

#### Acceptance Criteria

1. WHEN a request is made to any *.gemmit.org subdomain THEN the edge proxy SHALL check entitlements before forwarding to frps
2. WHEN entitlement check returns 401, 402, or 403 THEN the proxy SHALL redirect to a paywall page
3. WHEN entitlement check passes THEN the proxy SHALL forward the request to the frps server with preserved headers
4. WHEN using Nginx THEN the system SHALL use auth_request module for entitlement checking
5. WHEN using Caddy THEN the system SHALL use forward_auth directive for entitlement checking

### Requirement 6: frps Server Configuration

**User Story:** As a system administrator, I want a properly configured frps server that handles multiple client connections, so that tunnels can be established reliably.

#### Acceptance Criteria

1. WHEN frps is deployed THEN it SHALL listen on port 7000 for client connections
2. WHEN frps is configured THEN it SHALL serve HTTP tunnels on port 8081 and HTTPS tunnels on port 8443
3. WHEN frps receives client connections THEN it SHALL validate them using a shared token
4. WHEN frps is running THEN it SHALL support subdomain-based routing for *.gemmit.org
5. WHEN frps starts THEN it SHALL run as a systemd service with automatic restart capability

### Requirement 7: Electron Application Tunnel Integration

**User Story:** As a Gemmit user, I want tunnel functionality built directly into the Electron application, so that I can start and manage tunnels seamlessly within my existing development workflow.

#### Acceptance Criteria

1. WHEN a user requests tunnels THEN the Gemmit Electron app SHALL call the reservation API and store tunnel configurations locally
2. WHEN tunnel configurations are received THEN the Electron main process SHALL generate frpc.ini files with appropriate settings
3. WHEN starting tunnels THEN the Electron app SHALL spawn and manage frpc processes directly using Node.js child_process
4. WHEN tunnels are active THEN the Electron app SHALL display tunnel status and shareable URLs in the UI
5. WHEN the Electron application closes THEN it SHALL properly terminate all managed tunnel processes

### Requirement 8: Local Development Proxy

**User Story:** As a developer, I want a local reverse proxy that routes requests to different services, so that I can maintain same-origin policies while developing.

#### Acceptance Criteria

1. WHEN the local proxy starts THEN it SHALL listen on port 8080 for incoming requests
2. WHEN a request path starts with '/api/alt/' THEN the proxy SHALL route to the backend service (port 5003)
3. WHEN a request path starts with '/api/' THEN the proxy SHALL route to the vibe service (port 8000)
4. WHEN a request doesn't match API patterns THEN the proxy SHALL route to the frontend service (port 5002)
5. WHEN handling WebSocket connections THEN the proxy SHALL properly upgrade and route WebSocket traffic

### Requirement 9: Electron Process Management and Cleanup

**User Story:** As a Gemmit user, I want the Electron application to manage tunnel processes reliably with proper cleanup, so that I don't have orphaned processes or resource leaks.

#### Acceptance Criteria

1. WHEN tunnel processes are started THEN the Electron main process SHALL track them using the existing process management patterns (similar to backend process handling)
2. WHEN the Electron application shuts down THEN all tunnel processes SHALL be terminated gracefully using the existing cleanup mechanisms
3. WHEN a tunnel process crashes THEN the Electron app SHALL detect the failure and provide user feedback through the existing UI
4. WHEN stopping tunnels THEN the Electron app SHALL use the existing tree-kill library for proper process termination
5. WHEN managing tunnel processes THEN the Electron app SHALL leverage existing cross-platform process handling code

### Requirement 10: Security and Abuse Prevention

**User Story:** As a system operator, I want security measures to prevent abuse and ensure system stability, so that the service remains available for legitimate users.

#### Acceptance Criteria

1. WHEN implementing rate limiting THEN the edge proxy SHALL limit requests per host to prevent abuse
2. WHEN storing sensitive data THEN the system SHALL use environment variables for tokens and secrets
3. WHEN validating webhooks THEN the system SHALL verify Stripe signatures to prevent spoofing
4. WHEN handling user input THEN the system SHALL sanitize and validate all parameters
5. WHEN logging activities THEN the system SHALL avoid logging sensitive information like tokens or user data