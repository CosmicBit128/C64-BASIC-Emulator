#version 400

in vec2 UV;
out vec4 fragColor;

uniform sampler2D Glyph;
uniform vec3 Palette[2];
uniform int Screen[1000];
uniform ivec2 WinRes;
uniform ivec2 Margin;

void main() {
    const ivec2 SCR_SIZE = ivec2(40, 25);

    // pixel coords
    ivec2 pix_pos = ivec2(WinRes * UV);

    // border check
    if (pix_pos.x < Margin.x || pix_pos.x >= WinRes.x - Margin.x ||
        pix_pos.y < Margin.y || pix_pos.y >= WinRes.y - Margin.y) 
    {
        fragColor = vec4(Palette[1], 1.0);
        return;
    }

    // character area coords
    ivec2 screen_res = WinRes - 2 * Margin;
    vec2 scr_pos = vec2(pix_pos - Margin);

    // float division!
    vec2 char_size = vec2(screen_res) / vec2(SCR_SIZE);

    // Which character?
    ivec2 pos = ivec2(scr_pos / char_size);
    int index = (pos.x*SCR_SIZE.y) + (SCR_SIZE.y-pos.y-1);
    int ch = Screen[index];

    int gx = ch % 16;
    int gy = ch / 16;

    vec2 atlas_char_size = vec2(8.0);
    vec2 glyph_offset = vec2(gx, gy) * atlas_char_size;
    vec2 pixel_in_char = mod(scr_pos, char_size);
    pixel_in_char.y = -pixel_in_char.y;

    // Scale scr_pos pixel to atlas pixels
    glyph_offset.y += 7;
    vec2 atlas_pixel = glyph_offset + (pixel_in_char * (atlas_char_size / char_size));

    vec2 atlas_size = vec2(textureSize(Glyph, 0));
    vec2 atlas_uv = atlas_pixel / atlas_size;

    // Flip Y if needed
    atlas_uv.y = 1.0-atlas_uv.y;
    // fragColor = vec4(atlas_uv, 0.0, 1.0);
    // return;

    float c = texture(Glyph, atlas_uv).r;

    fragColor = vec4(Palette[c <= 0.5 ? 1 : 0], 1.0);
}
