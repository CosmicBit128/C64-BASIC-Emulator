#version 400

layout (location=0) in vec2 Position;
out vec2 UV;

void main() {
    UV = Position*.5+.5;
    gl_Position = vec4(Position, 0.0, 1.0);
}