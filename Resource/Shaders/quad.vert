#version 430 core

in struct VERTEX_ARRAY
{
    layout(location=0) vec3 position;
    layout(location=1) vec4 color;
    layout(location=2) vec3 normal;
    layout(location=3) vec3 tangent;
    layout(location=4) vec2 texcoord;
} vertex;


void main() {
    gl_Position = vec4(vertex.position.xy, 0.0, 0.0);
}