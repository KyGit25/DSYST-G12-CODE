#!/bin/bash
set -euo pipefail

wait_for() {
  local host="$1"
  local port="$2"
  until mongosh --host "$host" --port "$port" --eval 'db.adminCommand({ ping: 1 })' >/dev/null 2>&1; do
    echo "Waiting for $host:$port..."
    sleep 2
  done
}

wait_for configsvr 27019
wait_for shard1 27018
wait_for shard2 27018

# NOTE: we do NOT wait_for mongos here. A mongos process cannot answer
# requests until the config server replica set below is initiated, so
# waiting for it this early would just hang forever.

# each block below is wrapped in try/catch so re-running this script
# (e.g. after `docker compose up` on an already-set-up cluster) does not
# fail just because the step was already done before.

mongosh --host configsvr --port 27019 --quiet <<'EOF'
try {
  rs.initiate({
    _id: 'configReplSet',
    configsvr: true,
    members: [{ _id: 0, host: 'configsvr:27019' }]
  })
} catch (err) {
  print("configsvr replica set already set up: " + err)
}
EOF

mongosh --host shard1 --port 27018 --quiet <<'EOF'
try {
  rs.initiate({
    _id: 'shard1ReplSet',
    members: [{ _id: 0, host: 'shard1:27018' }]
  })
} catch (err) {
  print("shard1 replica set already set up: " + err)
}
EOF

mongosh --host shard2 --port 27018 --quiet <<'EOF'
try {
  rs.initiate({
    _id: 'shard2ReplSet',
    members: [{ _id: 0, host: 'shard2:27018' }]
  })
} catch (err) {
  print("shard2 replica set already set up: " + err)
}
EOF

# give the replica sets a moment to elect a primary before mongos talks to them
sleep 5

# now that the config server replica set is initiated, mongos can start
# answering requests, so it is safe to wait for it here
wait_for mongos 27017

mongosh --host mongos --port 27017 --quiet <<'EOF'
try {
  sh.addShard('shard1ReplSet/shard1:27018')
  sh.addShard('shard2ReplSet/shard2:27018')
  sh.enableSharding('minisplunk')
  sh.shardCollection('minisplunk.logs', { _id: 'hashed' })
} catch (err) {
  print("sharding already set up: " + err)
}
EOF
