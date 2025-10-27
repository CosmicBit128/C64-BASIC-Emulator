#version 400

in vec2 UV;
out vec4 fragColor;

// Uniforms
uniform sampler2D ScreenTexture; // "ScreenTexture": "0"
uniform sampler2D LastFrame;     // "LastFrame": "1"
uniform float Brightness;        // "Brightness": "1.20"
uniform float Contrast;          // "Contrast": "1.25"
uniform float Saturation;        // "Saturation": "1.25"
uniform float Tint;              // "Tint": "0.0"      (range -1..1)
uniform float Gamma;             // "Gamma": "1.0"
uniform float ScanlineShade;     // "ScanlineShade": "0.75" (0..1)
uniform float OddlinePhase;      // "OddlinePhase": "0.0"   (pixel rows phase offset)
uniform float OddlineOffset;     // "OddlineOffset": "0.0"  (0..1 intensity reduction for odd lines)
uniform float Curvature;
uniform vec2 WinRes;             // Render target size in pixels
uniform bool CRTEnable;


const float PI = 3.141592653589793;

// Convert color to luminance
float luma(vec3 c) {
    return dot(c, vec3(0.2126, 0.7152, 0.0722));
}

// Adjust saturation around luma
vec3 adjustSaturation(vec3 color, float sat) {
    float y = luma(color);
    return mix(vec3(y), color, sat);
}

// Barrel distortion
vec2 barrelDistort(vec2 uv, float strength) {
    vec2 cc = uv * 2.0 - 1.0; // -1..1
    float r2 = dot(cc, cc);
    // simple polynomial distortion
    cc *= 1.0 + strength * r2;
    return cc * 0.5 + 0.5;
}

void main() {
    // Define base color
    vec3 color = texture2D(ScreenTexture, UV).rgb;

    // Check if CRT effect is enabled
    if (CRTEnable) { // If yes, apply all of the effects
        // 1. Apply mild barrel curvature to emulate CRT glass
        vec2 uv = barrelDistort(UV, Curvature);
        //vec2 uv = UV;

        // If we sample outside the screen, return black (imitates bezel)
        if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) {
            fragColor = vec4(0.0);
            return;
        }

        // 2. Subpixel/phosphor triad sampling
        // compute pixel step in uv
        vec2 px = 1.0 / WinRes;
        // triad spacing (a small fraction of pixel width) - gives subpixel color separation
        float triad = px.x * 2.0; // 1.0 pixel width by default; you can reduce for stronger effect
        vec2 off = vec2(triad * 0.3, triad * 0.0);

        // Sample R/G/B at slightly offset horizontal positions (simulates phosphor triads)

        float r = texture2D(ScreenTexture, (uv-off)).r;
        float g = texture2D(ScreenTexture, uv).g;
        float b = texture2D(ScreenTexture, (uv+off)).b;
        color = vec3(r, g, b);

        // 3. Scanline pattern (sin-based for smooth shading)
        // Use pixel row position to compute a scanline factor. High frequency depending on vertical pixels.
        float rowPos = uv.y * WinRes.y + OddlinePhase;
        // base scanline wave (fast): sin with wavelength = 2 pixels -> strong lines
        float scanWave = sin(rowPos * PI);
        // Normalize to 0..1
        float scanNorm = 0.5 + 0.5 * scanWave;
        // Blend between full brightness and ScanlineShade according to the wave
        float scanFactor = mix(1.0, ScanlineShade, scanNorm);

        // 4. Odd-line effect (simulate interlaced/odd line dimming or phase)
        // Determine whether this row is odd or even
        float row = floor(rowPos);
        float isOdd = mod(row, 2.0); // 1 for odd rows, 0 for even rows
        // Apply odd-line offset multiplier (reduces brightness on odd lines)
        float oddMultiplier = 1.0 - isOdd * clamp(OddlineOffset, 0.0, 1.0);

        // Combined line shading
        color *= scanFactor * oddMultiplier;

        // 5. Tint — subtle color shift; positive Tint shifts toward red, negative toward blue
        // We'll do a simple chroma bias around green channel
        float tintStrength = clamp(Tint, -1.0, 1.0);
        color.r += tintStrength * 0.06; // tweak factor for subtlety
        color.b -= tintStrength * 0.04;

        // 6. Brightness & Contrast
        // Contrast around 0.5 mid-point, then multiply brightness
        color = (color - 0.5) * Contrast + 0.5;
        color *= Brightness;

        // 7. Saturation
        color = adjustSaturation(color, Saturation);

        // 8. Apply a mild vignette (darken edges like a CRT)
        vec2 centered = UV - 0.5;
        float vign = smoothstep(0.8, 0.2, length(centered) * 1.3); // 0..1 (1 center, 0 edges)
        // invert so center keeps color, edges darken
        color *= mix(0.9, 1.0, vign);

        // 9. Gamma correction (assume Gamma > 0)
        color = pow(clamp(color, 0.0, 1.0), vec3(1.0 / max(0.0001, Gamma)));
        // color = mix(color, texture2D(LastFrame, UV).rgb, 0.8);
    }

    fragColor = vec4(clamp(color, 0.0, 1.0), 1.0);
}
