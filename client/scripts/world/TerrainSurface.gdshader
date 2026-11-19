shader_type canvas_item;
render_mode unshaded;

varying vec4 ground_color;
varying vec2 ground_position;

void vertex() {
	ground_color = COLOR;
	ground_position = VERTEX;
}

void fragment() {
	vec4 detail = texture(TEXTURE, UV);
	// World-space variation crosses tile boundaries, with no extra texture fetch.
	float patch = sin(ground_position.x * 0.012 + sin(ground_position.y * 0.009)) * sin(ground_position.y * 0.018);
	vec3 surface = mix(ground_color.rgb, detail.rgb, ground_color.a * detail.a);
	COLOR = vec4(surface * (1.0 + patch * 0.035), 1.0);
}
