# Joro — Agent Environment

Joro is the environment layer for setting up and adjusting the host an agent works on.

It owns host-level procedures, such as capturing, overriding, and restoring sleep and hibernate settings. Changes should preserve the original settings and provide a verified way to restore them.

## Boundaries

- Joro manages the host environment, not deployed services.
- Infra manages services and their infrastructure.
- Hermod manages repository workflows.
- Munnin manages agent memory contents.

## Status

This repository establishes Joro's home. Procedures have not yet been migrated or installed.
