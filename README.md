# Docker Swarm Update Monitor

I use Jenkins to deploy a few things into a Docker Swarm cluster, and the main problem with my set up is that there is no way to tell the docker client to wait until the deploy completes before exiting. This script will poll the Docker daemon, and wait until all services have completed their update (successfully or not) and tell you about it

## Usage

```
docker stack deploy ...
docker run --rm -ti insertjokehere/docker_update_monitor:latest <name of stack>
```

Exit code 0 means everything completed OK, exit code 1 means something failed

## One-Shot services

Docker Swarm doesn't have the concept of one-off task to be run in the cluster in the same way that Kubernetes does, but it has enough of the primitives that we can fake it.

* Set the `deploy.restart_policy.condition` property of your compose file to `none` so Swarm doesn't attempt to restart your service when it exits
* Add a `monitor_hint` label with the value of `oneshot` to your service so the update monitor knows that it should wait until your service has exited
* Run `docker_update_monitor` as normal

```
docker stack deploy -c examples/oneshot.yaml oneshot
docker run --rm -ti insertjokehere/docker_update_monitor:latest oneshot
```
