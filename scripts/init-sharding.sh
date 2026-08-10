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

sleep 5

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
