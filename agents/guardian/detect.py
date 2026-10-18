"""Guardian step 1: detect unhealthy pods.

Read-only: only runs `kubectl get`. Never changes anything in the cluster.

Usage:
    python detect.py               # namespace veloce
    python detect.py other-ns
"""

import json
import subprocess
import sys
from dataclasses import dataclass

RESTART_LIMIT = 3
