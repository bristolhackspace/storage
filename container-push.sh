#!/bin/bash

CONTAINER_CMD=$(which podman || which docker)

$CONTAINER_CMD tag localhost/storage:latest registry.bristolhackspace.org/storage:latest

$CONTAINER_CMD push registry.bristolhackspace.org/storage:latest

