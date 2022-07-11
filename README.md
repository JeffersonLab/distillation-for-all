# Distillation for all!

Distributed workflow for computing eigenvectors, propagators, and genprops with chroma.

## Goals

- Centralize options for computing eigenvectors, propagators, and genprops for all ensembles at JLab
- Flexibility to accommodate different name patters for eigenvectors, propagators, and genprops
- Cooperative computation among several facilities relaying on Globus and ssh access to JLab for coordination
- Robust by adaptiveness

## Architecture

- information system, KaoN: reads information from local and remote filesystems provides an
  coherent and detailed state of all objects.
  - `kaon.py`: engine
  - `ensembles.json`: description of ensembles and configuration for computing eigenvectors,
    propagators, and genprops

- workflow: details the objects that should be computed and probes the state of several objects
  and perform actions on them
  - `workflow.sh`

- actions: scripts to make promises, copying files between facilities, launch jobs, and validate
  the results...; all scripts are idempotent, calling them twice on the same object with the same
  state does not change the effect. For instance, the copying scripts will not ask to copy twice
  the same file if the script is called twice.


