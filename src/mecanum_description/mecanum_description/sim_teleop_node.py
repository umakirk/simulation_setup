import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TransformStamped, Twist
import tf2_ros
import math


class SimTeleopNode(Node):
    def __init__(self):
        super().__init__('sim_teleop_node')

        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)

        # Simulated position state (X, Y, Theta)
        self.x = 0.0
        self.y = 0.0
        self.th = 0.0

        # Velocities now come from /cmd_vel (published by handle_serial_bridge.py)
        # instead of being hardcoded here.
        self.vx = 0.0
        self.vy = 0.0
        self.vth = 0.0

        # Watchdog: if no /cmd_vel message arrives for this long, treat it as
        # "handle released / bridge disconnected" and zero the velocity rather
        # than coasting forever on the last command received.
        self.cmd_vel_timeout = 0.5  # seconds
        self.last_cmd_vel_time = None

        self.cmd_vel_sub = self.create_subscription(
            Twist, 'cmd_vel', self.cmd_vel_callback, 10
        )

        self.dt = 0.05  # 20 Hz
        self.timer = self.create_timer(self.dt, self.update_simulation)
        self.get_logger().info("Mecanum Simulation Node Initialized. Waiting for /cmd_vel...")

    def cmd_vel_callback(self, msg: Twist):
        self.vx = msg.linear.x
        self.vy = msg.linear.y
        self.vth = msg.angular.z
        self.last_cmd_vel_time = self.get_clock().now()

    def update_simulation(self):
        # Watchdog check: zero velocity if commands have gone stale
        if self.last_cmd_vel_time is not None:
            age = (self.get_clock().now() - self.last_cmd_vel_time).nanoseconds * 1e-9
            if age > self.cmd_vel_timeout:
                self.vx = 0.0
                self.vy = 0.0
                self.vth = 0.0

        # Translate velocities relative to the robot's current heading orientation
        delta_x = (self.vx * math.cos(self.th) - self.vy * math.sin(self.th)) * self.dt
        delta_y = (self.vx * math.sin(self.th) + self.vy * math.cos(self.th)) * self.dt
        delta_th = self.vth * self.dt

        self.x += delta_x
        self.y += delta_y
        self.th += delta_th

        # Broadcast the new position to the transform tree (TF)
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = 'odom'          # Fixed world center
        t.child_frame_id = 'robot_location'  # Moving robot center

        t.transform.translation.x = self.x
        t.transform.translation.y = self.y
        t.transform.translation.z = 0.0

        t.transform.rotation.x = 0.0
        t.transform.rotation.y = 0.0
        t.transform.rotation.z = math.sin(self.th / 2.0)
        t.transform.rotation.w = math.cos(self.th / 2.0)

        self.tf_broadcaster.sendTransform(t)


def main(args=None):
    rclpy.init(args=args)
    node = SimTeleopNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()