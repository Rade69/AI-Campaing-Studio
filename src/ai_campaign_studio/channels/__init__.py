"""Channel / Platform / Format registry (P0.13).

Data-driven ``Channel -> Platform -> Format`` model. Platforms are defined in
``resources/platforms/*.yaml``, not as Python enums, so the registry stays
extensible without touching the Campaign Engine.
"""
