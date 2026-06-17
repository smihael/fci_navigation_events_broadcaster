# FCI Navigation Events Broadcaster

Broadcasts Franka Desk navigation button events from
`wss://192.168.1.1/desk/api/navigation/events` to ROS 2 `std_msgs/Bool`
topics.

The published button topics are:

- `navigation_events/circle`
- `navigation_events/cross`
- `navigation_events/check`
- `navigation_events/left`
- `navigation_events/right`
- `navigation_events/down`
- `navigation_events/up`

The topic namespace is configurable with the `topic_namespace` parameter. Each
topic uses transient-local durability with depth 1, so the last state is latched.
All buttons are initialized and published as `false`; after that, a button is
only published when its state changes.

## Dependencies

Runtime dependencies:

- `python3-requests`
- `python3-websocket`

`colcon build` does not install missing system Python packages. Install
dependencies before running the node:

```bash
cd [ros2_ws]
rosdep install --from-paths src --ignore-src -r -y
```

## Build

```bash
cd [ros2_ws]
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF
source install/setup.bash
```

## Run

```bash
ros2 launch fci_navigation_events_broadcaster navigation_events_broadcaster.launch.py
```

With a custom topic namespace:

```bash
ros2 launch fci_navigation_events_broadcaster navigation_events_broadcaster.launch.py \
  topic_namespace:=desk_nav
```

## Authentication

There are two authentication modes.

### Username and password

The node can log in to Desk using operator username and password.

```bash
ros2 launch fci_navigation_events_broadcaster navigation_events_broadcaster.launch.py \
  username:=admin \
  password:=your_password
```

### Reuse a browser authorization token

If you are already logged into Desk in a browser, copy the Desk `authorization`
cookie value from the browser developer tools and put it in an environment
variable before launching.

By default, the node reads `FRANKA_DESK_AUTHORIZATION`:

```bash
export FRANKA_DESK_AUTHORIZATION='paste_browser_authorization_cookie_value_here'

ros2 launch fci_navigation_events_broadcaster navigation_events_broadcaster.launch.py
```

To use a different environment variable name:

```bash
export MY_DESK_TOKEN='paste_browser_authorization_cookie_value_here'

ros2 launch fci_navigation_events_broadcaster navigation_events_broadcaster.launch.py \
  authorization_token_env:=MY_DESK_TOKEN
```

When an authorization token is provided, the node uses it directly and skips the
username/password login request.
