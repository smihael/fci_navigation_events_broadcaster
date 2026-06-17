from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    host = LaunchConfiguration("host")
    topic_namespace = LaunchConfiguration("topic_namespace")
    username = LaunchConfiguration("username")
    password = LaunchConfiguration("password")
    authorization_token_env = LaunchConfiguration("authorization_token_env")

    return LaunchDescription(
        [
            DeclareLaunchArgument("host", default_value="192.168.1.1"),
            DeclareLaunchArgument("topic_namespace", default_value="navigation_events"),
            DeclareLaunchArgument("username", default_value=""),
            DeclareLaunchArgument("password", default_value=""),
            DeclareLaunchArgument(
                "authorization_token_env",
                default_value="FRANKA_DESK_AUTHORIZATION",
            ),
            Node(
                package="fci_navigation_events_broadcaster",
                executable="navigation_events_broadcaster",
                name="navigation_events_broadcaster",
                parameters=[
                    {
                        "host": host,
                        "topic_namespace": topic_namespace,
                        "username": username,
                        "password": password,
                        "authorization_token_env": authorization_token_env,
                    }
                ],
                output="screen",
            ),
        ]
    )
