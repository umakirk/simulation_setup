#!/usr/bin/env python3
import math
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
from visualization_msgs.msg import Marker
from geometry_msgs.msg import Point


def generate_regular_polygon(num_sides, side_length, center=(0.0, 0.0), rotation_offset=0.0):
    """Regular polygon centered at `center`, vertex-aligned so the shape closes cleanly."""
    # circumradius from side length
    radius = side_length / (2 * math.sin(math.pi / num_sides))
    cx, cy = center
    points = []
    for i in range(num_sides + 1):  # +1 closes the loop
        angle = 2 * math.pi * i / num_sides + rotation_offset
        points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return points


def generate_circle(radius, center=(0.0, 0.0), num_points=36):
    cx, cy = center
    return [
        (cx + radius * math.cos(2 * math.pi * i / num_points),
         cy + radius * math.sin(2 * math.pi * i / num_points))
        for i in range(num_points + 1)
    ]


def generate_custom_path(waypoints):
    return waypoints


class PathMarkerPublisher(Node):
    def __init__(self):
        super().__init__('path_marker_publisher')

        # ---- Parameters (settable from CLI/launch, no code edits needed) ----
        self.declare_parameter('shape', 'octagon')     # 'octagon', 'circle', 'custom'
        self.declare_parameter('side_length', 1.75)     # used by polygon shapes
        self.declare_parameter('radius', 1.5)            # used by circle
        self.declare_parameter('center_x', 0.0)
        self.declare_parameter('center_y', 0.0)

        self.waypoints = self._build_path()

        qos = QoSProfile(depth=1,
                          reliability=ReliabilityPolicy.RELIABLE,
                          durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.pub = self.create_publisher(Marker, 'reference_path', qos)
        self.timer = self.create_timer(1.0, self.publish_marker)

    def _build_path(self):
        shape = self.get_parameter('shape').value
        center = (self.get_parameter('center_x').value, self.get_parameter('center_y').value)

        if shape == 'octagon':
            side = self.get_parameter('side_length').value
            return generate_regular_polygon(8, side, center=center, rotation_offset=math.pi / 8)
        elif shape == 'circle':
            radius = self.get_parameter('radius').value
            return generate_circle(radius, center=center)

        elif shape == 'hexagon':
            side = self.get_parameter('side_length').value
            return generate_regular_polygon(6, side, center=center, rotation_offset=math.pi / 6)
        
        elif shape == 'square':
            side = self.get_parameter('side_length').value
            return generate_regular_polygon(4, side, center=center, rotation_offset=math.pi / 4)
                
        elif shape == 'custom':
            return generate_custom_path([
                (0.0, 0.0), (1.0, 0.0), (1.0, 1.0),
                (2.0, 1.0), (2.0, -0.5), (3.0, -0.5),
            ])
        else:
            self.get_logger().warn(f"Unknown shape '{shape}', defaulting to octagon")
            return generate_regular_polygon(8, 1.75, center=center)

    def publish_marker(self):
        marker = Marker()
        marker.header.frame_id = 'odom'   # MUST match your RViz Fixed Frame
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.ns = 'reference_path'
        marker.id = 0
        marker.type = Marker.LINE_STRIP
        marker.action = Marker.ADD

        marker.scale.x = 0.05
        marker.color.r = 1.0
        marker.color.g = 0.0
        marker.color.b = 0.0
        marker.color.a = 1.0
        marker.pose.orientation.w = 1.0

        for x, y in self.waypoints:
            p = Point()
            p.x, p.y, p.z = x, y, 0.01
            marker.points.append(p)

        self.pub.publish(marker)


def main():
    rclpy.init()
    node = PathMarkerPublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()