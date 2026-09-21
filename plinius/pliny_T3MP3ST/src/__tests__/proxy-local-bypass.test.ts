import { afterEach, describe, expect, it } from 'vitest';
import { createServer, type Server } from 'node:http';
import { configureProxy, fetchBypassingProxy } from '../net/proxy.js';

let server: Server | undefined;

afterEach(async () => {
  configureProxy(null);
  if (server) {
    await new Promise<void>((resolve, reject) => server!.close(error => error ? reject(error) : resolve()));
    server = undefined;
  }
});

describe('local-model proxy bypass', () => {
  it('uses a direct dispatcher while the attack-traffic SOCKS proxy is enabled', async () => {
    server = createServer((_request, response) => {
      response.writeHead(200, { 'content-type': 'application/json' });
      response.end('{"ok":true}');
    });
    await new Promise<void>(resolve => server!.listen(0, '127.0.0.1', resolve));
    const address = server.address();
    if (!address || typeof address === 'string') throw new Error('test server did not bind');

    // Nothing listens here. A request inheriting the global proxy would fail.
    const status = configureProxy('socks5://127.0.0.1:1');
    expect(status.enabled).toBe(true);

    const response = await fetchBypassingProxy(`http://127.0.0.1:${address.port}/model`);
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ ok: true });
  });
});
