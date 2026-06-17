from setuptools import setup

package_name = "fci_navigation_events_broadcaster"

setup(
    name=package_name,
    version="0.0.1",
    packages=[package_name],
    data_files=[
        (
            "share/ament_index/resource_index/packages",
            [f"resource/{package_name}"],
        ),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", ["launch/navigation_events_broadcaster.launch.py"]),
    ],
    install_requires=["requests", "setuptools", "websocket-client"],
    zip_safe=True,
    maintainer="Mihael Simonic",
    maintainer_email="smihael@gmail.com",
    description="Broadcast Franka Desk navigation button websocket events to ROS 2 topics.",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "navigation_events_broadcaster = "
            "fci_navigation_events_broadcaster.navigation_events_broadcaster:main",
        ],
    },
)
