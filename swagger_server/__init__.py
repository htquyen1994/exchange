#!/usr/bin/env python3

import connexion


app = connexion.App(__name__, specification_dir='./swagger/')