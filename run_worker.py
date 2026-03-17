import asyncio

try:
    import uvloop
    uvloop.install()
except ImportError:
    pass

asyncio.set_event_loop(asyncio.new_event_loop())

from arq.cli import cli

if __name__ == "__main__":
    cli()
