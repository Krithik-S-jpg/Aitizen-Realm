shader_type canvas_item;
render_mode unshaded;

varying vec4 ground_color;

void vertex() {
	ground_color = COLOR;
}

void fragment() {
	vec4 detail = texture(TEXTURE, UV);
	COLOR = vec4(mix(ground_color.rgb, detail.rgb, ground_color.a * detail.a), 1.0);
}
