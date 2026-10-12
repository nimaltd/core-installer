"""
The shared core of the installers: stm32-installer, zephyr-installer.

It fetches a library from GitHub, a zip or a folder, reads its installer.yml,
installs what it needs first, copies its files and keeps what the user wrote
between USER CODE markers. What a project looks like, and how a library is
registered with it, comes from the installer through target.use().

Kept in its own repository, github.com/nimaltd/core-installer, and built into
each installer's wheel, so an installer still installs from one file with no
internet.
"""
