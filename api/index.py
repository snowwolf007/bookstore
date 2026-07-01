"""Vercel ASGI 入口"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
os.chdir(os.path.join(os.path.dirname(__file__), "..", "backend"))

from app import app
from mangum import Mangum

handler = Mangum(app)
