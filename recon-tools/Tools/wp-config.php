<?php
/**
 * The base configuration for WordPress
 *
 * The wp-config.php creation script uses this file during the
 * installation. You don't have to use the web site, you can
 * copy this file to "wp-config.php" and fill in the values.
 *
 * This file contains the following configurations:
 *
 * * MySQL settings
 * * Secret keys
 * * Database table prefix
 * * ABSPATH
 *
 * @link https://codex.wordpress.org/Editing_wp-config.php
 *
 * @package WordPress
 */

// ** MySQL settings - You can get this info from your web host ** //
/** The name of the database for WordPress */
define('DB_NAME', '3gproxy');

/** MySQL database username */
define('DB_USER', '3gproxy');

/** MySQL database password */
define('DB_PASSWORD', 'UyA5RKTdaaXrJ76v');

/** MySQL hostname */
define('DB_HOST', 'localhost');

/** Database Charset to use in creating database tables. */
define('DB_CHARSET', 'utf8mb4');

/** The Database Collate type. Don't change this if in doubt. */
define('DB_COLLATE', '');

/**#@+
 * Authentication Unique Keys and Salts.
 *
 * Change these to different unique phrases!
 * You can generate these using the {@link https://api.wordpress.org/secret-key/1.1/salt/ WordPress.org secret-key service}
 * You can change these at any point in time to invalidate all existing cookies. This will force all users to have to log in again.
 *
 * @since 2.6.0
 */
define('AUTH_KEY',         '$(^TSsh]]::)Okq)]f( ECz6MrZ4Y[m{At}oLlRO+A[Q9xb1W)0}`T#)ID+[Y~Di');
define('SECURE_AUTH_KEY',  'Yjjh]8C*&6)ijCpmK%FT0*`s^E!?w!1k1rL[Y-,&)7,zr.d=?+&2xzeYaY^U>Xy7');
define('LOGGED_IN_KEY',    '9EM>H!{0O5tk_i!%`SgN^AdHU}Y`afKH_N?(m1t SLl[c?INRTQY(yXb{{|=mqVI');
define('NONCE_KEY',        'n$1L3RBT{^6y{VHNM HEnkVY}WpvFeav;hS,+3Lu%7A:Tz~}^^^*AFRS;daVmB;}');
define('AUTH_SALT',        'RI-JO.ZQhS%wTTMTRU|qtG;h^z}arw, >fkst~P/ }YpCR}n[cwZ*K% 2X~^obLD');
define('SECURE_AUTH_SALT', 'Q/K2>Ps`_q2ehh S{@|XPyPT|=O>mO7BVWlVbu-{2)Iy<BLf2~)SpnM.!IvlmH0j');
define('LOGGED_IN_SALT',   'LF!~[ay38sg%O,cGffp_#dd,Qex[$T&JIfoY5&v#HHpQ}EWo+/=%T|*qdgEff.!D');
define('NONCE_SALT',       'xAB-~]q(=i2x[;}+C?-gK88q lohkb^{aM[rn{?rh>Kij+wjvxVPq[&X%)?ty5lH');

/**#@-*/

/**
 * WordPress Database Table prefix.
 *
 * You can have multiple installations in one database if you give each
 * a unique prefix. Only numbers, letters, and underscores please!
 */
$table_prefix  = 'wp_';

/**
 * For developers: WordPress debugging mode.
 *
 * Change this to true to enable the display of notices during development.
 * It is strongly recommended that plugin and theme developers use WP_DEBUG
 * in their development environments.
 *
 * For information on other constants that can be used for debugging,
 * visit the Codex.
 *
 * @link https://codex.wordpress.org/Debugging_in_WordPress
 */
define('WP_DEBUG', false);

/* That's all, stop editing! Happy blogging. */

/** Absolute path to the WordPress directory. */
if ( !defined('ABSPATH') )
	define('ABSPATH', dirname(__FILE__) . '/');

/** Sets up WordPress vars and included files. */
require_once(ABSPATH . 'wp-settings.php');

define( 'FS_METHOD', 'direct' );