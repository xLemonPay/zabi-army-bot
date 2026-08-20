import asyncio

import bot as base
from role_panels import install as install_role_panels


install_role_panels(base)


if __name__ == "__main__":
    asyncio.run(base.main())
