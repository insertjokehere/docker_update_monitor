# Docker Swarm Update Monitor

I use Jenkins to deploy a few things into a Docker Swarm cluster, and the main problem with my set up is that there is no way to tell the docker client to wait until the deploy completes before exiting. This script will poll the Docker daemon, and wait until all services have completed their update (successfully or not) and tell you about it

## Usage

```
docker stack deploy ...
docker run --rm -ti insertjokehere/docker_update_monitor:latest <name of stack>
```

Exit code 0 means everything completed OK, exit code 1 means something failed