# GRAPHQL & WEBSOCKET

> Level: GOD TIER — introspection, batching, depth bypass, authorization bypass, handshake manipulation, CSWSH
> Extracted from CORE.md — load on-demand when GraphQL / WebSocket tasks arrive.

## GraphQL
- **Introspection**: full schema dump, field enumeration, mutation discovery
- **Batching**: query batching rate limit bypass, alias-based brute force
- **Depth**: circular reference DoS, depth limit bypass
- **Authorization**: field-level access control, directive manipulation
- **Injection**: GraphQL-specific SQLi/NoSQLi, variable injection, operation name manipulation
- **Subscription**: real-time event eavesdropping, connection exhaustion
- **Error Leakage**: stack traces, schema validation bypass

## WebSocket
- **Handshake**: origin bypass, subprotocol injection, upgrade token abuse
- **Message Injection**: frame manipulation, payload tampering, fragmentation abuse
- **Auth**: token replay, session hijacking, cookie theft
- **DoS**: connection flooding, large frame abuse, close frame manipulation
- **CSWSH**: cookie-based auth leak, cross-origin connection
