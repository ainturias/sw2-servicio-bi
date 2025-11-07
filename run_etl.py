#!/usr/bin/env python3
"""
Script helper para ejecutar el ETL fácilmente.
Uso: python run_etl.py
"""

import sys
import os

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Ejecutar el ETL
if __name__ == "__main__":
    from app.etl import main
    main()

