#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Orvix Lite — launcher.
Main code lives in the orvix/ package; this file runs the app as a single program.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from orvix.entry import main

if __name__ == "__main__":
    main()
