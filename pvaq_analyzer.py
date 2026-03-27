#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Legacy entry name: *pvaq_analyzer.py*

Same as ORVIX_PRO_v24.py — starts Orvix Lite (orvix.entry.main).
Keep this file if old scripts or docs still call `python pvaq_analyzer.py`.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from orvix.entry import main

if __name__ == "__main__":
    main()
