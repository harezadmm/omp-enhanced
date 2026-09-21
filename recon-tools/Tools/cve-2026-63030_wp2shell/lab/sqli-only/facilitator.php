<?php
/**
 * wp2shell-lab — "facilitator" mu-plugin.  THIS IS NOT WORDPRESS CORE.
 *
 * It reproduces the *facilitating* precondition that GHSA-fpp7-x2x2-2mjf
 * (CVE-2026-60137) requires on WordPress >= 6.8: a plugin or theme that hands a
 * RAW request value to WP_Query's `author__not_in`. WordPress core's own REST
 * `author_exclude` coerces the value to an int array, so the standalone SQLi is
 * NOT reachable on default 6.8.x core — only through a sink like this one.
 *
 * On 6.9.0+ the batch route confusion (CVE-2026-63030) provides that sink for
 * free and unauthenticated; this file lets the 6.8.x "SQLi only" case be
 * demonstrated in isolation.
 *
 * Reachable unauthenticated at:
 *     /?wp2shell_faccheck=1&author_not_in=<payload>
 * Emits "ROWS:YES" when the query matched rows, "ROWS:NO" otherwise
 * (a boolean oracle), and honours time-based SLEEP() payloads too.
 */
add_action('init', function () {
    if (!isset($_GET['wp2shell_faccheck'])) {
        return;
    }
    // WordPress slashes superglobals; unslash to get the attacker's raw string.
    $raw = isset($_GET['author_not_in']) ? wp_unslash($_GET['author_not_in']) : '1';

    $q = new WP_Query(array(
        'author__not_in' => $raw,   // <-- raw string reaches the vulnerable sink
        'post_status'    => 'publish',
        'fields'         => 'ids',
        'no_found_rows'  => true,
    ));

    header('Content-Type: text/plain');
    echo ($q->post_count > 0) ? 'ROWS:YES' : 'ROWS:NO';
    exit;
});
