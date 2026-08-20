import asyncio

import bot as base
from role_panels import install as install_role_panels
from start_guide import install as install_start_guide
from verify_style import install as install_verify_style
from party_behavior import install as install_party_behavior


install_role_panels(base)
install_start_guide(base)
install_verify_style(base)
install_party_behavior(base)


if __name__ == "__main__":
    asyncio.run(base.main())
